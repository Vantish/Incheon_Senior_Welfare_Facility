import streamlit as st
from app_bus_stop_recommendation import bus_stop_recommendation
from app_bus_route import check_bus_route
from app_around_leisure_restaurant import around_leisure
from app_around_leisure_restaurant import around_restaurant
from app_location import run_location

import numpy as np
import pandas as pd
import folium
from streamlit.components.v1 import html as st_html
import math
from html import escape

# optional heavy dependency for road-based routing
try:
    import osmnx as ox
    import networkx as nx
    OSMNX_AVAILABLE = True
except Exception:
    OSMNX_AVAILABLE = False

# 그래프 캐시 파일 이름
GRAPH_CACHE_PATH = './incheon_graph.pkl'

# 가장 복잡한 파트입니다.
# 만약 유저 위치가 입력받지 않았다면 에러 문구를
# 입력 받았다면 기능을 동작합니다.
# 먼저 사용자의 위치와 시설 분류를 기반으로 가장 가까운 시설을 추천합니다.
# 이후 거리를 계산하여 가장 가까운 시설을 찾습니다.
# 만약 사용자가 근처 맛집이나 가는 버스를 알고싶다면 멀티셀렉트를 이용하여 해당 기능을 지도에 표시합니다.
# 이후 각각의 부분에서 받아온 함수를 상황에 맞게 동작시켜서 정보를 받은 후, 해당 정보를 출력합니다.


def run_map():
    st.subheader('위치 기반 추천')
    st.text('\n')
    user_location = run_location()
    # user_location은 리스트 형태를 기대합니다:
    # [위도, 경도, 도로명 주소, 이용하고 싶은 시설 분류]
    if user_location is None:
        st.error('사용자의 위치가 지정되지 않았습니다. app_location 에서 위치 정보를 전달해주세요.')
        return
    else:
        # 읽어오기 (euc-kr 인코딩)
        노인복지시설_df = pd.read_csv('./data/인천광역시_노인복지시설 현황.csv', encoding = 'euc-kr')
        st.write('데이터프레임 상위 5개')
        st.dataframe(노인복지시설_df.head())

        # lat/lon 컬럼 인식 (파일 구조에 따라 컬럼명이 'lat','lon' 등으로 되어 있음)
        cols = [c for c in 노인복지시설_df.columns]
        lat_col = next((c for c in cols if 'lat' in c.lower()), None)
        lon_col = next((c for c in cols if 'lon' in c.lower() or 'lot' in c.lower()), None)
        if lat_col is None or lon_col is None:
            st.error('데이터에 lat/lon 컬럼이 없습니다. 파일 컬럼: ' + ','.join(cols))
            return

        # app_location에서 전달한 user_location 리스트를 사용
        # 형식: [lat, lon, 도로명주소, 선택한_시설_분류]
        try:
            ulat = float(user_location[0])
            ulon = float(user_location[1])
        except Exception:
            st.error('전달된 사용자 위치 정보 형식이 잘못되었습니다. [lat, lon, ...] 형식을 전달하세요.')
            return

        # 사용자가 선택한 시설 분류는 인덱스 3에 위치
        selected_type = None
        if isinstance(user_location, (list, tuple)) and len(user_location) > 3:
            selected_type = user_location[3]

        # 컬럼명이 명확하면 고정 (요청대로 '시설유형' 사용)
        type_col = '시설유형' if '시설유형' in 노인복지시설_df.columns else None
        if type_col is None:
            # 만약 없으면 첫 번째 컬럼으로 대체(안전장치)
            st.warning("'시설유형' 컬럼이 없어 자동으로 첫 번째 컬럼을 사용합니다.")
            type_col = 노인복지시설_df.columns[0]

        # 후보 필터링: 사용자가 지정한 분류가 있으면 그 기준으로 필터
        if selected_type and selected_type != '전체':
            candidates = 노인복지시설_df[노인복지시설_df[type_col] == selected_type].copy()
        else:
            candidates = 노인복지시설_df.copy()

        # lat/lon 결측 제거
        candidates = candidates.dropna(subset=[lat_col, lon_col])
        candidates[lat_col] = candidates[lat_col].astype(float)
        candidates[lon_col] = candidates[lon_col].astype(float)

        if candidates.shape[0] == 0:
            st.error('선택된 유형의 시설이 없습니다.')
            return

        # haversine 거리 계산
        def haversine(a, b):
            # a, b: (lat, lon) in degrees
            lat1, lon1 = math.radians(a[0]), math.radians(a[1])
            lat2, lon2 = math.radians(b[0]), math.radians(b[1])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            R = 6371000.0
            hav = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
            return 2*R*math.asin(math.sqrt(hav))

        # 직선거리 기준으로 상위 후보 k개만 추림 (속도 개선)
        k = min(20, len(candidates))
        candidates['straight_dist_m'] = candidates.apply(lambda r: haversine((ulat, ulon), (r[lat_col], r[lon_col])), axis=1)
        top_candidates = candidates.nsmallest(k, 'straight_dist_m').copy()

        # 도로기반 거리 계산 (osmnx 사용). 실패 시 직선거리로 대체
        use_road = OSMNX_AVAILABLE
        G = None
        # 그래프가 캐시되어 있는지 확인 후 로드
        if use_road:
            try:
                import os
                import pickle
                if os.path.exists(GRAPH_CACHE_PATH):
                    with open(GRAPH_CACHE_PATH, 'rb') as fh:
                        G = pickle.load(fh)
                        st.info('캐시된 OSMnx 그래프를 불러왔습니다. 로딩이 빠릅니다.')
                else:
                    # 사용자가 그래프를 미리 생성하도록 버튼 제공
                    if st.button('인천 도로 그래프 생성 및 저장 (처음 한 번만 필요)'):
                        try:
                            with st.spinner('OSM 데이터 다운로드 및 그래프 생성 중... (몇 분 소요될 수 있음)'):
                                G = ox.graph_from_place('Incheon, South Korea', network_type='drive')
                                with open(GRAPH_CACHE_PATH, 'wb') as fh:
                                    pickle.dump(G, fh)
                                st.success('그래프 생성 및 저장이 완료되었습니다.')
                        except Exception as e:
                            st.error('그래프 생성에 실패했습니다: ' + str(e))
                            G = None
            except Exception:
                G = None
        road_results = None
        if not OSMNX_AVAILABLE:
            st.warning('osmnx/networkx 패키지가 설치되어 있지 않아 도로 기반 경로 계산을 건너뜁니다. straight-line fallback 사용')
        if use_road and G is not None:
            try:
                # 그래프는 사용자 위치 중심 반경 15km
                # 이미 G가 캐시된 경우엔 그대로 사용하고, 아니라면 그래프를 해당 지점 중심으로 다운로드 시도
                if G is None:
                    G = ox.graph_from_point((ulat, ulon), dist=15000, network_type='drive')
                # nearest nodes for user and candidates
                user_node = ox.nearest_nodes(G, ulon, ulat)
                cand_nodes = ox.nearest_nodes(G, top_candidates[lon_col].tolist(), top_candidates[lat_col].tolist())
                lengths = []
                for n in cand_nodes:
                    try:
                        d = nx.shortest_path_length(G, user_node, n, weight='length')
                        lengths.append(d)
                    except Exception:
                        lengths.append(float('inf'))
                top_candidates['road_dist_m'] = lengths
                road_results = top_candidates
            except Exception as e:
                st.warning('도로 기반 거리 계산에 실패했습니다. 직선거리로 대체합니다. 오류: ' + str(e))
                use_road = False

        if not use_road or road_results is None:
            # fallback: straight_dist_m 에 기반
            top_candidates['road_dist_m'] = top_candidates['straight_dist_m']
            road_results = top_candidates

        # 최종 최소 행 선택
        best = road_results.nsmallest(1, 'road_dist_m').iloc[0]

        # folium map 생성
        fmap = folium.Map(location=[ulat, ulon], zoom_start=14)
        # popup을 HTML로 만들어 가로 표시와 자동 줄바꿈을 적용
        def make_popup(text, width=240):
            # text에 '<br>'이 포함되어 있으면 적절히 분리해 각 부분을 escape 후 다시 합칩니다.
            s = str(text)
            if '<br>' in s:
                parts = s.split('<br>')
                escaped = '<br>'.join(escape(p) for p in parts)
            else:
                escaped = escape(s).replace('\n', '<br>')
            html = f"""<div style='max-width:{width}px; white-space:normal; word-wrap:break-word; font-size:13px; line-height:1.2;'>{escaped}</div>"""
            # iframe 높이를 텍스트 길이에 따라 약간 조절
            height = 50 + max(0, (len(escaped) - width) // 3)
            return folium.Popup(folium.IFrame(html=html, width=width+20, height=height), max_width=width+20)

        folium.Marker([ulat, ulon], popup=make_popup('사용자 위치'), icon=folium.Icon(color='blue')).add_to(fmap)
        best_title = str(best.get(type_col, '시설')) + '<br>' + str(best.get(노인복지시설_df.columns[0], '이름'))
        folium.Marker([best[lat_col], best[lon_col]], popup=make_popup(best_title), icon=folium.Icon(color='red')).add_to(fmap)

        # 경로 polyline (osmnx 사용 시)
        if use_road:
            try:
                # 경로 노드들 가져와서 선으로 그림
                target_node = ox.nearest_nodes(G, best[lon_col], best[lat_col])
                route = nx.shortest_path(G, user_node, target_node, weight='length')
                route_geom = ox.plot_route_folium(G, route, route_map=fmap, color='green')
            except Exception:
                pass
        else:
            # 직선으로 연결
            folium.PolyLine(locations=[[ulat, ulon], [best[lat_col], best[lon_col]]], color='green').add_to(fmap)

        # 추가 정보 (맛집 / 여가시설 / 정류장) 표시: 기존 함수들이 반환하면 지도에 마커를 추가
        select_list = ['맛집', '여가시설', '정류장']
        selection = st.multiselect('추가적으로 사용하실 정보를 입력해주세요.', select_list)
        facilities_location = (best[lat_col], best[lon_col])

        if '맛집' in selection:
            temp_restaurant = around_restaurant(facilities_location)
            if isinstance(temp_restaurant, pd.DataFrame) and not temp_restaurant.empty:
                for _, r in temp_restaurant.head(20).iterrows():
                    if lat_col in r and lon_col in r:
                        label = r.get('상호', '맛집')
                        # 식당명 + (가능하면 주소/설명)
                        extra = ''
                        for c in ['주소','도로명주소','소재지','상세주소']:
                            if c in r and pd.notna(r[c]):
                                extra = r[c]
                                break
                        popup_text = label if not extra else f"{label}<br>{extra}"
                        folium.CircleMarker([r[lat_col], r[lon_col]], radius=4, color='orange', popup=make_popup(popup_text)).add_to(fmap)
        if '여가시설' in selection:
            temp_leisure = around_leisure(facilities_location)
            if isinstance(temp_leisure, pd.DataFrame) and not temp_leisure.empty:
                for _, r in temp_leisure.head(20).iterrows():
                    if lat_col in r and lon_col in r:
                        label = r.get('이름', '여가')
                        extra = ''
                        for c in ['주소','위치','설명']:
                            if c in r and pd.notna(r[c]):
                                extra = r[c]
                                break
                        popup_text = label if not extra else f"{label}<br>{extra}"
                        folium.CircleMarker([r[lat_col], r[lon_col]], radius=4, color='purple', popup=make_popup(popup_text)).add_to(fmap)
        if '정류장' in selection:
            temp_bus_stop = None
            try:
                temp_bus_stop = bus_stop_recommendation((ulat, ulon), facilities_location)
            except Exception as e:
                st.warning('정류장 추천 모듈 호출 중 오류가 발생했습니다: ' + str(e))

            # 예상 반환: dict with 'user_nearby' and 'facility_nearby'
            if not isinstance(temp_bus_stop, dict):
                st.warning('정류장 정보를 불러오지 못했습니다. 모듈이 placeholder 상태일 수 있습니다.')
                user_df = None
                fac_df = None
            else:
                user_df = temp_bus_stop.get('user_nearby')
                fac_df = temp_bus_stop.get('facility_nearby')

            # 지도에 다른 색으로 표시 (존재 여부 체크)
            if user_df is not None and hasattr(user_df, 'iterrows') and not user_df.empty:
                for _, r in user_df.iterrows():
                    try:
                        folium.CircleMarker([float(r['lat']), float(r['lon'])], radius=4, color='cadetblue', popup=make_popup(f"{r.get('정류장명','정류장')}<br>{int(r.get('dist_user_m',0))}m", width=200)).add_to(fmap)
                    except Exception:
                        continue
            if fac_df is not None and hasattr(fac_df, 'iterrows') and not fac_df.empty:
                for _, r in fac_df.iterrows():
                    try:
                        folium.CircleMarker([float(r['lat']), float(r['lon'])], radius=4, color='darkblue', popup=make_popup(f"{r.get('정류장명','정류장')}<br>{int(r.get('dist_fac_m',0))}m", width=200)).add_to(fmap)
                    except Exception:
                        continue

            # 사이드바에 목록 표시 및 버스 노선 조회 버튼
            with st.sidebar.expander('근처 정류장(사용자 / 시설) 목록'):
                st.write('사용자 근처 정류장')
                if user_df is not None and hasattr(user_df, 'head'):
                    try:
                        st.dataframe(user_df[['정류장명','행정동명','dist_user_m']].rename(columns={'dist_user_m':'거리(m)'}))
                    except Exception:
                        st.write('사용자 근처 정류장 정보를 표시할 수 없습니다.')
                else:
                    st.write('사용자 근처 정류장 정보가 없습니다.')

                st.write('시설 근처 정류장')
                if fac_df is not None and hasattr(fac_df, 'head'):
                    try:
                        st.dataframe(fac_df[['정류장명','행정동명','dist_fac_m']].rename(columns={'dist_fac_m':'거리(m)'}))
                    except Exception:
                        st.write('시설 근처 정류장 정보를 표시할 수 없습니다.')
                else:
                    st.write('시설 근처 정류장 정보가 없습니다.')

                # 버스 노선 데이터가 준비되어 있다면 check_bus_route 호출
                if st.button('해당 정류장들로 가는 버스 노선 조회'):
                    try:
                        routes = check_bus_route({'user': user_df, 'facility': fac_df})
                        if routes:
                            st.write('조회된 노선:')
                            st.json(routes)
                        else:
                            st.info('버스 노선 데이터가 없거나 해당 정류장에 대한 노선 정보를 찾을 수 없습니다.')
                    except Exception as e:
                        st.error('버스 노선 조회 중 오류: ' + str(e))

        # 지도 출력
        fmap_html = fmap._repr_html_()
        st_html(fmap_html, height=600)
    