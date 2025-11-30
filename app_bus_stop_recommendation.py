import pandas as pd
import matplotlib.pyplot as plt
from sklearn.neighbors import NearestNeighbors
import streamlit as st
import numpy as np
import requests
import xmltodict
import os





# 사용자 위치정보(user_location)와 해당 정보를 바탕으로 계산된 시설의 위치정보(facilities_location)를 입력받은 후
# 사용자 근처 가장 가까운 정류장 5개와 시설에서 가장 가까운 정류장 5개를 딕셔너리 형태로 반환합니다.
# 반환 정보 = 'user_nearby' and 'facility_nearby'

data_path = os.path.join('data', 'bus stop.csv')
bus_stops_df = pd.read_csv(data_path)


def bus_stop_recommendation(user_location, facilities_location, n_neighbors=10):

    user_stops, facility_stops = [], []

    # --- 컬럼명 탐색 ---
    cols = bus_stops_df.columns.tolist()
    lat_col = next((c for c in cols if '위도' in c.lower() or 'latitude' in c.lower() or 'lat' == c.lower()), None)
    lon_col = next((c for c in cols if '경도' in c.lower() or 'longitude' in c.lower() or 'lon' == c.lower() or 'lng' == c.lower()), None)
    정류장명 = next((c for c in cols if any(term in c.lower() for term in ['정류소명', '정류장명', '정류소 명', '정류장 명'])), None)
    행정동명 = next((c for c in cols if any(term in c.lower() for term in ['행정동명', '행정동 명', '동이름'])), None)
    정류소아이디 = next((c for c in cols if any(term in c.lower() for term in ['정류장 id', '정류장ID', '정류소아이디', '정류소 아이디'])), None)
    정류소번호 = next((c for c in cols if any(term in c.lower() for term in ['정류소번호', '번호', '정류소 번호', 'stop number', 'stop_no'])), None)

    if (lat_col is None) or (lon_col is None):
        st.error(f'위도/경도 컬럼을 찾을 수 없습니다. 현재 컬럼: {", ".join(cols)}')
        return None


    # --- 결측치 정리 ---
    bus_stops_df_clean = bus_stops_df.dropna(subset=[lat_col, lon_col])

    # --- 사용자 위치 추천 ---
    if user_location and len(user_location) >= 2:
        ulat, ulon = float(user_location[0]), float(user_location[1])

        try:
            bus_stops_location = bus_stops_df_clean[[lat_col, lon_col]].to_numpy()

            locations_rad = np.radians(bus_stops_location)

            nbrs = NearestNeighbors(n_neighbors=n_neighbors, metric='haversine')
            nbrs.fit(locations_rad)

            user_loc_rad = np.radians([[ulat, ulon]])

            distances, indices = nbrs.kneighbors(user_loc_rad)

            distances_km = distances[0] * 6371

            for idx, dist in zip(indices[0], distances_km):
                bus_stop = bus_stops_df_clean.iloc[idx]
                stop_info = {
                    'lat': float(bus_stop[lat_col]),
                    'lon': float(bus_stop[lon_col]),
                    '정류장명': bus_stop[정류장명],
                    '행정동명': bus_stop[행정동명],
                    '정류장ID': bus_stop[정류소아이디],
                    '정류소번호': str(bus_stop[정류소번호]).split('.')[0] if 정류소번호 else '',
                    'dist_user_m': int(dist * 1000)
                }
                user_stops.append(stop_info)
        except Exception as e:
            st.error(f'사용자 위치 추천 오류: {str(e)}')
            user_stops = []

   # --- 시설 유형 위치 추천 ---
    if facilities_location and len(facilities_location) >= 2:
        fac_lat, fac_lon = float(facilities_location[0]), float(facilities_location[1])

        try:
            bus_stops_location = bus_stops_df_clean[[lat_col, lon_col]].to_numpy()

            locations_rad = np.radians(bus_stops_location)

            nbrs = NearestNeighbors(n_neighbors=n_neighbors, metric='haversine')
            nbrs.fit(locations_rad)

            facilities_loc_rad = np.radians([[fac_lat, fac_lon]])

            distances, indices = nbrs.kneighbors(facilities_loc_rad)

            distances_km = distances[0] * 6371

            for idx, dist in zip(indices[0], distances_km):

                bus_stop = bus_stops_df_clean.iloc[idx]
                stop_info = {
                    'lat': float(bus_stop[lat_col]),
                    'lon': float(bus_stop[lon_col]),
                    '정류장명': bus_stop[정류장명],
                    '행정동명': bus_stop[행정동명],
                    '정류장ID': bus_stop[정류소아이디],
                    '정류소번호':str(bus_stop[정류소번호]).split('.')[0] if 정류소번호 else '',
                    'dist_fac_m': int(dist * 1000)
                }
                facility_stops.append(stop_info)

        except Exception as e:
            st.error(f'시설 위치 추천 오류: {str(e)}')
            facility_stops = []

    # --- DataFrame 생성과 컬럼 정렬 ---
    user_columns = ['lat', 'lon', '정류장명', '행정동명','정류장ID','정류소번호', 'dist_user_m']
    fac_columns = ['lat', 'lon', '정류장명', '행정동명','정류장ID','정류소번호', 'dist_fac_m']

    user_df = pd.DataFrame(user_stops, columns=user_columns)
    fac_df = pd.DataFrame(facility_stops, columns=fac_columns)

    return {'user_nearby': user_df, 'facility_nearby': fac_df}


API_KEY = st.secrets.get("INCHEON_BUS_API_KEY")

# 노선ID-노선명 매핑 테이블 로딩 (한 번만 로드)
route_df = pd.read_csv('data\incheon bus route.csv', dtype=str,encoding='euc-kr')
route_dict = dict(zip(route_df['노선아이디'].str.strip(), route_df['노선명'].str.strip()))

def get_bus_arrival_info(stop_info):
    bstop_id = stop_info.get('정류장ID') if isinstance(stop_info, dict) else stop_info['정류장ID']

    url = "http://apis.data.go.kr/6280000/busArrivalService/getAllRouteBusArrivalList"
    params = {
        'serviceKey': API_KEY,
        'pageNo': '1',
        'numOfRows': '10',
        'bstopId': bstop_id
    }
    resp = requests.get(url, params=params)

    if resp.status_code != 200:
        st.error(f"API 요청 실패: 상태 코드 {resp.status_code}")
        return None

    try:
        data_dict = xmltodict.parse(resp.content.decode('utf-8'))
    except Exception as e:
        st.error(f"XML 파싱 오류: {e}")
        st.write("원본 응답 내용:", resp.text)
        return None

    try:
        msg_body = data_dict.get('ServiceResult', {}).get('msgBody', {})
        items = msg_body.get('itemList', None)

        if not items:
            st.info("도착 예정인 버스가 없습니다.")
            return None

        if isinstance(items, dict):
            items = [items]

        # 노선ID -> 노선명 변환 적용
        for item in items:
            route_id = item.get('ROUTEID', '').strip()
            item['ROUTEID'] = route_dict.get(route_id, route_id)  # 매핑 없으면 기존 ID 유지

        return items

    except (KeyError, TypeError) as e:
        st.error(f"도착 정보 형식 오류: {e}")
        st.write("원본 응답 구조:", data_dict)
        return None
    
    



