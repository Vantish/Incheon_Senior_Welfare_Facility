import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode
from app_bus_stop_recommendation import bus_stop_recommendation
from app_bus_route import check_bus_route
from app_around_leisure_restaurant import around_leisure
from app_around_leisure_restaurant import around_restaurant
from app_location import run_location
from define import find_nearest_facilities, make_popup, draw_route_on_map, to_pylist, normalize_routes_output, extract_stop_list, _haversine_m

from app_chatbot_mj import run_chatbot_app
import numpy as np
import pandas as pd
import folium
from streamlit.components.v1 import html as st_html
import math
from html import escape

# 도로 기반 라우팅에 사용되는 선택적(무거운) 의존성
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

import os
import pickle


# 거리 계산 및 도로 기반 최단 시설 선택 유틸리티 함수
#
# 함수: find_nearest_facilities
# 입력:
# - user_location: (lat, lon) 튜플 또는 리스트
# - facilities_df: 위도/경도 컬럼을 가진 pandas.DataFrame
# - return_count: 최종 반환할 상위 시설 개수 (기본 5)
# - candidate_prefilter: 도로 거리 계산 전 직선거리로 미리 뽑아둘 후보 수 (기본 20)
# - graph_cache_path: osmnx 그래프 피클 파일 경로 (있으면 도로 기반 계산 시도)
#
# 반환:
# - pandas.DataFrame: 원본 컬럼에 'straight_dist_m'과 'road_dist_m' 컬럼을 추가한 후
#   road_dist_m 오름차순으로 정렬된 데이터프레임 (최소 return_count개 반환)
#
# 함수는 osmnx가 설치되어 있고 graph_cache_path에 캐시가 존재하면 도로 기반 경로 길이를
# 계산하려 시도합니다. 실패하거나 osmnx가 없으면 straight_dist_m을 road_dist_m으로 사용합니다.



def run_map():
    """메인 Streamlit 진입점: 지도, 근처 시설 및 추가 오버레이를 표시합니다."""
    st.subheader('내 위치 찾기🔎')
    st.text('\n')

    # 1) 사용자 위치 획득
    user_location = run_location()
    if 'user_location' in st.session_state:
        user_location = st.session_state['user_location']

    if user_location is None:
        st.error('사용자의 위치가 지정되지 않았습니다.')
        return

    try:
        ulat = float(user_location[0])
        ulon = float(user_location[1])
    except Exception:
        st.error('전달된 사용자 위치 정보 형식이 잘못되었습니다. [lat, lon, ...] 형식을 전달하세요.')
        return

    # 2) 시설 데이터 로드 및 필터링
    data_path = os.path.join('data', '인천광역시_노인복지시설_현황.csv')
    노인복지시설_df = pd.read_csv(data_path, dtype=str, encoding='euc-kr')
    cols = [c for c in 노인복지시설_df.columns]
    lat_col = next((c for c in cols if 'lat' in c.lower()), None)
    lon_col = next((c for c in cols if 'lon' in c.lower() or 'lot' in c.lower()), None)
    if lat_col is None or lon_col is None:
        st.error('데이터에 lat/lon 컬럼이 없습니다. 파일 컬럼: ' + ','.join(cols))
        return

    selected_type = None
    if isinstance(user_location, (list, tuple)) and len(user_location) > 3:
        selected_type = user_location[3]

    type_col = '시설유형' if '시설유형' in 노인복지시설_df.columns else 노인복지시설_df.columns[0]
    if '시설유형' not in 노인복지시설_df.columns:
        st.warning("'시설유형' 컬럼이 없어 자동으로 첫 번째 컬럼을 사용합니다.")

    if selected_type and selected_type != '전체':
        candidates = 노인복지시설_df[노인복지시설_df[type_col] == selected_type].copy()
    else:
        candidates = 노인복지시설_df.copy()

    candidates = candidates.dropna(subset=[lat_col, lon_col])
    candidates[lat_col] = candidates[lat_col].astype(float)
    candidates[lon_col] = candidates[lon_col].astype(float)
    if candidates.shape[0] == 0:
        st.error('선택된 유형의 시설이 없습니다.')
        return
    
 # 3) 직선 거리 10km로 필터링
    candidates['straight_dist_m'] = candidates.apply(
        lambda row: _haversine_m((ulat, ulon), (row[lat_col], row[lon_col])), axis=1
    )
    candidates = candidates[candidates['straight_dist_m'] <= 10000]
    if candidates.shape[0] == 0:
        st.error('직선 거리 10km 이내의 시설이 없습니다.')
        return

    # 4) 거리 계산 및 최적 시설 선택
    road_results = find_nearest_facilities((ulat, ulon), candidates, return_count=5, candidate_prefilter=10, graph_cache_path=GRAPH_CACHE_PATH)
    if road_results is None or road_results.shape[0] == 0:
        st.error('10km 이내의 시설이 없습니다.')
        return


    # 5) 도로 거리 10km로 필터링
    if 'road_dist_m' in road_results.columns:
        road_results = road_results[road_results['road_dist_m'] <= 10000]
        if road_results.shape[0] == 0:
            st.error('도로 거리 10km 이내의 시설이 없습니다.')
            return
        
    best = road_results.iloc[0] if not road_results.empty else None
    best5 = road_results.head(5)
    best5['거리'] = best5['road_dist_m'].apply(lambda d: f"{d:.1f} m" if d < 1000 else f"{d/1000:.2f} km")
    st.write('\n')
    st.write('시설명을 선택 하시면 경로가 갱신됩니다.🚌💨💨')
    gb = GridOptionsBuilder.from_dataframe(best5)
    gb.configure_columns(['straight_dist_m', 'road_dist_m', 'lat', 'lon'], hide=True)
    gb.configure_default_column(editable=False, sortable=True, filter=True)
    gb.configure_selection(selection_mode='single')
    gb.configure_grid_options(domLayout='autoHeight')
    grid_options = gb.build()

    # 레이아웃: 상단에 후보 목록(왼쪽)과 선택된 시설 카드(오른쪽)을 배치하고
    # 그 아래 전체 너비로 지도를 표시합니다.
    top_left, top_right = st.columns([3, 1])

    # 왼쪽: 후보 목록(Grid)
    with top_left:
        st.markdown('### 가까운 시설 5개 (10km 이내)')
        # 동적 높이: 행 수에 따라 그리드 높이를 자동 조절합니다.
        # 기본: 80px + 40px * rows, 최대 450px
        try:
            rows = len(best5) if hasattr(best5, '__len__') else 1
        except Exception:
            rows = 1
        grid_height = min(450, 80 + 40 * max(1, rows))

        grid_response = AgGrid(
            best5,
            gridOptions=grid_options,
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            fit_columns_on_grid_load=True,
            theme='streamlit',
            height=grid_height,
        )
        selected_rows = grid_response.get('selected_rows', [])

    # 선택값 정리 및 기본값 결정
    if selected_rows is None:
        selected_rows = []
    if isinstance(selected_rows, pd.DataFrame):
        selected_rows = selected_rows.to_dict(orient='records')
    if len(selected_rows) > 0:
        best = selected_rows[0]
    else:
        best = road_results.iloc[0].to_dict()

    # 오른쪽: 선택된 시설 카드
    with top_right:
        st.markdown('### 📌선택된 시설')
        st.write('\n')
        st.write('\n')
        try:
            name = best.get(노인복지시설_df.columns[0], '')
            kind = best.get(type_col, '')
            dist = best.get('road_dist_m') or best.get('straight_dist_m') or ''
            if isinstance(dist, (int, float)):
                dist_str = f"{dist:.1f} m" if dist < 1000 else f"{dist/1000:.2f} km"
            else:
                dist_str = str(dist)
            st.markdown(f"- 이름: **{name}**\n- 유형: {kind}\n- 거리: {dist_str}")
        except Exception:
            st.write('선택 정보를 표시할 수 없습니다.')

  # 6) 기본 지도 생성 및 표시
    fmap = folium.Map(location=[ulat, ulon], zoom_start=14)  # 1km에 맞게 확대
    try:
        st.session_state['fmap'] = fmap
    except Exception:
        pass


    # 사용자 위치 마커
    folium.Marker(
        [ulat, ulon],
        popup=make_popup('사용자 위치'),
        icon=folium.Icon(color='blue', icon='user', prefix='fa')
    ).add_to(fmap)


    # 5개 시설 모두 마커 표시
    for _, row in best5.iterrows():
        title = str(row.get(노인복지시설_df.columns[0], '이름'))+ '<br>' +str(row.get(type_col, '시설'))
        folium.Marker(
            [row[lat_col], row[lon_col]],
            popup=make_popup(title),
            icon=folium.Icon(color='red', icon='flag')
        ).add_to(fmap)


    # 5) 경로 그리기 (osmnx 그래프가 있으면 시도, 없으면 직선 폴백)
    draw_route_on_map(fmap, ulat, ulon, best[lat_col], best[lon_col], graph_cache_path=GRAPH_CACHE_PATH)

    # 6) 부가 정보(맛집/여가시설/정류장) 표시
    try:
        fmap = st.session_state.get('fmap', fmap)
    except Exception:
        pass

    select_list = ['맛집', '여가시설', '정류장']
    selection = st.multiselect('추가적으로 사용하실 정보를 입력해주세요.', select_list)
    facilities_location = (best[lat_col], best[lon_col])
    try:
        st.session_state['facilities_location'] = facilities_location
    except Exception:
        pass
    facilities_location = st.session_state.get('facilities_location', facilities_location)

    user_df = None
    fac_df = None


    # 맛집 마커
    if '맛집' in selection:
        try:
            temp_restaurant = around_restaurant(facilities_location)
            if isinstance(temp_restaurant, pd.DataFrame) and not temp_restaurant.empty:
                for _, r in temp_restaurant.head(20).iterrows():
                    try:
                        latv = float(r.get(lat_col, r.get('lat')))
                        lonv = float(r.get(lon_col, r.get('lon')))
                        label = r.get('상호', '맛집')
                        extra = ''
                        for c in ['주소','도로명 주소','소재지','상세주소']:
                            if c in r and pd.notna(r[c]):
                                extra = r[c]
                                break
                        popup_text = label if not extra else f"{label}<br>{extra}"
                        # 눈에 띄는 마커로 변경
                        folium.Marker(
                            [latv, lonv],
                            popup=make_popup(popup_text),
                            icon=folium.Icon(color='orange', icon='cutlery', prefix='fa')
                        ).add_to(fmap)
                    except Exception:
                        continue
        except Exception:
            st.warning('맛집 정보를 불러오는 중 오류가 발생했습니다.')


    # 여가시설 마커
    if '여가시설' in selection:
        try:
            temp_leisure = around_leisure(facilities_location)
            if isinstance(temp_leisure, pd.DataFrame) and not temp_leisure.empty:
                for _, r in temp_leisure.head(20).iterrows():
                    try:
                        latv = float(r.get(lat_col, r.get('lat')))
                        lonv = float(r.get(lon_col, r.get('lon')))
                        label = r.get('이름', '여가')
                        extra = ''
                        for c in ['주소','위치','설명','도로명 주소','시설분류']:
                            if c in r and pd.notna(r[c]):
                                extra = r[c]
                                break
                        popup_text = label if not extra else f"{label}<br>{extra}"
                        # 눈에 띄는 마커로 변경
                        folium.Marker(
                            [latv, lonv],
                            popup=make_popup(popup_text),
                            icon=folium.Icon(color='purple', icon='star', prefix='fa')
                        ).add_to(fmap)
                    except Exception:
                        continue
        except Exception:
            st.warning('여가시설 정보를 불러오는 중 오류가 발생했습니다.')

        
    # 정류장 마커 및 테이블 준비
    bus_request = False
    if '정류장' in selection:
        bus_request = True
        try:
            temp_bus_stop = bus_stop_recommendation((ulat,ulon), facilities_location)
        except Exception as e:
            st.warning('정류장 추천 모듈 호출 중 오류가 발생했습니다: ' + str(e))
            temp_bus_stop = None

        if isinstance(temp_bus_stop, dict):
            user_df = temp_bus_stop.get('user_nearby')
            fac_df = temp_bus_stop.get('facility_nearby')
            # 지도에 그리기
            try:
                if user_df is not None and hasattr(user_df, 'iterrows') and not user_df.empty:
                    for _, r in user_df.iterrows():
                        try:
                            folium.Marker(
                                [float(r['lat']), float(r['lon'])],
                                popup=make_popup(f"{r.get('정류장명','정류장')}<br>정류장 번호:  {str(r.get('정류소번호', 'N/A')).split('.')[0]}<br>{int(r.get('dist_user_m',0))}m", width=200),
                                icon=folium.Icon(color='green', icon='bus', prefix='fa')
                            ).add_to(fmap)
                        except Exception:
                            continue
                if fac_df is not None and hasattr(fac_df, 'iterrows') and not fac_df.empty:
                    for _, r in fac_df.iterrows():
                        try:
                            folium.Marker(
                                [float(r['lat']), float(r['lon'])],
                                popup=make_popup(f"{r.get('정류장명','정류장')}<br>정류장 번호:  {str(r.get('정류소번호', 'N/A')).split('.')[0]}<br>{int(r.get('dist_fac_m',0))}m", width=200),
                                icon=folium.Icon(color='darkgreen', icon='bus', prefix='fa')
                            ).add_to(fmap)
                        except Exception:
                            continue
            except Exception:
                st.warning('정류장 마커 표시 중 오류가 발생했습니다.')
        else:
            st.warning('정류장 정보를 불러오지 못했습니다. 모듈이 placeholder 상태일 수 있습니다.')

    # 7) 지도 렌더링 및 테이블/버튼 표시
    fmap_html = fmap._repr_html_()
    # 전체 너비로 지도를 표시합니다 (데이터프레임/선택카드 아래).
    st.markdown('### 지도🗺️')
    st_html(fmap_html, height=680)

    if '맛집' in selection:
        run_chatbot_app()

    if bus_request:
        st.markdown('### 근처 정류장 (사용자 / 시설)')

        with st.expander('사용자 근처 정류장'):
            if user_df is not None and hasattr(user_df, 'head') and not user_df.empty:
                try:
                    selected_stop = st.selectbox('정류장 선택', user_df['정류장명'].tolist())
                    st.dataframe(
                        user_df[['정류장명', '행정동명', '정류소번호', 'dist_user_m']]
                        .rename(columns={'dist_user_m': '거리(m)'})
                    )

                    selected_row = user_df[user_df['정류장명'] == selected_stop].iloc[0]

                    from app_bus_stop_recommendation import get_bus_arrival_info
                    arrival_info = get_bus_arrival_info(selected_row)  # 정류장 행 자체 전달

                    if arrival_info:
                        st.markdown('#### 선택한 정류장의 버스 도착 정보')

                        rows = []
                        stop_no = str(selected_row.get('정류소번호', 'N/A')).split('.')[0]

                        for bus in arrival_info:
                            arrival_sec = bus.get('ARRIVALESTIMATETIME')
                            arrival_min = int(arrival_sec) // 60 if arrival_sec and arrival_sec.isdigit() else 'N/A'
                            route_id = bus.get('ROUTEID', 'N/A')

                            row = {
                                '정류소번호': stop_no,
                                '노선번호': route_id,
                                '이전 정류소명': bus.get('LATEST_STOP_NAME', 'N/A'),
                                '도착예정 시간(분)': arrival_min
                            }
                            rows.append(row)
                        st.table(rows)
                    else:
                        st.write('선택한 정류장의 도착 정보를 불러올 수 없습니다.')
                except Exception as e:
                    st.write(f'사용자 근처 정류장 정보 표시 중 오류 발생: {e}')
            else:
                st.write('사용자 근처 정류장 정보가 없습니다.')


        with st.expander('시설 근처 정류장'):
            if fac_df is not None and hasattr(fac_df, 'head') and not fac_df.empty:
                try:
                    selected_stop_fac = st.selectbox('시설 근처 정류장 선택', fac_df['정류장명'].tolist())
                    st.dataframe(
                        fac_df[['정류장명', '행정동명', '정류소번호', 'dist_fac_m']]
                        .rename(columns={'dist_fac_m': '거리(m)'})
                    )

                    selected_row_fac = fac_df[fac_df['정류장명'] == selected_stop_fac].iloc[0]

                    from app_bus_stop_recommendation import get_bus_arrival_info
                    arrival_info_fac = get_bus_arrival_info(selected_row_fac)

                    if arrival_info_fac:
                        st.markdown('#### 선택한 시설 근처 정류장의 버스 도착 정보')

                        rows = []
                        stop_no = str(selected_row_fac.get('정류소번호', 'N/A')).split('.')[0]

                        for bus in arrival_info_fac:
                            arrival_sec = bus.get('ARRIVALESTIMATETIME')
                            arrival_min = int(arrival_sec) // 60 if arrival_sec and arrival_sec.isdigit() else 'N/A'
                            route_id = bus.get('ROUTEID', 'N/A')

                            row = {
                                '정류소번호': stop_no,
                                '노선번호': route_id,
                                '이전 정류소명': bus.get('LATEST_STOP_NAME', 'N/A'),
                                '도착예정 시간(분)': arrival_min
                            }
                            rows.append(row)
                        st.table(rows)
                    else:
                        st.write('선택한 시설 근처 정류장의 도착 정보를 불러올 수 없습니다.')
                except Exception:
                    st.write('시설 근처 정류장 정보를 표시할 수 없습니다.')
            else:
                st.write('시설 근처 정류장 정보가 없습니다.')



        # if st.button('해당 정류장들로 가는 버스 노선 조회'):
        #     # 간단한 CSV 기반 매칭 결과를 표 형태로 보여줍니다.
        #     # 반환값 예시(개념):
        #     # {
        #     #   'user': {정류장키: [노선,...], ...},
        #     #   'facility': {...},
        #     #   'direct_routes': ['노선A',...],
        #     #   'direct_connections': [{'route':r,'user_stop':u,'facility_stop':f}, ...]
        #     # }
        #     try:
        #         # check_bus_route를 호출하기 전에 user/fac DataFrame을 간단한 정류장 리스트로 변환합니다.
        #         user_stops_input = extract_stop_list(user_df) if user_df is not None else []
        #         fac_stops_input = extract_stop_list(fac_df) if fac_df is not None else []

        #         routes = check_bus_route({'user': user_stops_input, 'facility': fac_stops_input})
        #         # 모든 값을 평범한 파이썬 타입(예: 문자열 리스트)으로 정규화합니다.
        #         routes = normalize_routes_output(routes)
        #         import pandas as _pd

        #         # 값을 문자열 리스트로 강제 변환합니다 (추가 방어적 정규화)
        #         raw_user_side = routes.get('사용자 근처', {})
        #         raw_fac_side = routes.get('시설 근처', {})
        #         user_side = {str(k): [str(x).strip() for x in to_pylist(v) if str(x).strip()] for k, v in raw_user_side.items()} if isinstance(raw_user_side, dict) else {}
        #         fac_side = {str(k): [str(x).strip() for x in to_pylist(v) if str(x).strip()] for k, v in raw_fac_side.items()} if isinstance(raw_fac_side, dict) else {}

        #         # 정류장->버스 목록을 버스->정류장 집합으로 뒤집기
        #         merged = {}
        #         for stop, buslist in user_side.items():
        #             for b in to_pylist(buslist):
        #                 rno = str(b).strip()
        #                 if rno == '':
        #                     continue
        #                 merged.setdefault(rno, {'사용자 근처 정류소': set(), '시설 근처 정류소': set()})
        #                 merged[rno]['사용자 근처 정류소'].add(str(stop))

        #         for stop, buslist in fac_side.items():
        #             for b in to_pylist(buslist):
        #                 rno = str(b).strip()
        #                 if rno == '':
        #                     continue
        #                 merged.setdefault(rno, {'사용자 근처 정류소': set(), '시설 근처 정류소': set()})
        #                 merged[rno]['시설 근처 정류소'].add(str(stop))

        #         if len(merged) > 0:
        #             # merged는 이미 버스번호 -> {'사용자 근처 정류소': set(...), '시설 근처 정류소': set(...)} 형태입니다.
        #             rows = []
        #             for rno, cols in merged.items():
        #                 u = ', '.join(sorted(cols['사용자 근처 정류소'])) if cols['사용자 근처 정류소'] else ''
        #                 f = ', '.join(sorted(cols['시설 근처 정류소'])) if cols['시설 근처 정류소'] else ''
        #                 rows.append({'버스번호': rno, '사용자 근처 정류소': u, '시설 근처 정류소': f})

        #             df_routes = _pd.DataFrame(rows).set_index('버스번호')
        #             st.dataframe(df_routes)
        #         else:
        #             # direct_routes(간단 리스트)로만 존재하는 경우를 처리
        #             direct = to_pylist(routes.get('direct_routes', [])) if isinstance(routes, dict) else []
        #             if len(direct) > 0:
        #                 df_routes = _pd.DataFrame({'버스번호': direct, '사용자 근처 정류소': [''] * len(direct), '시설 근처 정류소': [''] * len(direct)}).set_index('버스번호')
        #                 st.dataframe(df_routes)
        #             else:
        #                 st.info('직통 노선 정보를 찾을 수 없습니다.')
        #     except Exception as e:
        #         st.error('버스 노선 조회 중 오류: ' + str(e))
    