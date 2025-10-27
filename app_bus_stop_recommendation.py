import streamlit as st
import numpy as np
import pandas as pd




# 사용자 위치정보(user_location)와 해당 정보를 바탕으로 계산된 시설의 위치정보(facilities_location)를 입력받은 후
# 사용자 근처 가장 가까운 정류장 5개와 시설에서 가장 가까운 정류장 5개를 딕셔너리 형태로 반환합니다.
# 반환 정보 = 'user_nearby' and 'facility_nearby'

bus_stops_df = pd.read_csv('./data/버스정류장.csv')


def bus_stop_recommendation(user_location, facilities_location, find_nearest_facilities, bus_stops_df):

    user_stops, facility_stops = [], []

    # --- 컬럼명 탐색 ---
    cols = bus_stops_df.columns.tolist()
    lat_col = next((c for c in cols if '위도' in c.lower() or 'latitude' in c.lower() or 'lat' == c.lower()), None)
    lon_col = next((c for c in cols if '경도' in c.lower() or 'longitude' in c.lower() or 'lon' == c.lower() or 'lng' == c.lower()), None)
    정류장명 = next((c for c in cols if any(term in c.lower() for term in ['정류소명', '정류장명', '정류소 명', '정류장 명'])), None)
    행정동명 = next((c for c in cols if any(term in c.lower() for term in ['행정동명', '행정동 명', '동이름'])), None)

    if (lat_col is None) or (lon_col is None):
        raise ValueError(f'위도/경도 컬럼을 찾을 수 없습니다. 현재 컬럼: {", ".join(cols)}')


    # --- 사용자 위치 추천 ---
    if user_location and len(user_location) >= 2:

        try:
            # find_nearest_facilities 함수 호출, 도로 기반 거리 계산 수행
            nearest_user_stops = find_nearest_facilities(user_location, bus_stops_df, return_count=5)

            # 필요한 컬럼만 추출해 리스트 생성
            for _, row in nearest_user_stops.iterrows():
                user_stops.append({
                    'lat': row[lat_col],
                    'lon': row[lon_col],
                    '정류장명': row[정류장명],
                    '행정동명': row[행정동명],
                    'dist_road_m': int(row['road_dist_m']),
                    'dist_straight_m': int(row['straight_dist_m']),
                })
        except Exception as e:
            raise RuntimeError(f'사용자 위치 추천 오류: {str(e)}')

   # --- 시설 유형 위치 추천 ---
    if facilities_location and len(facilities_location) >= 2:

        try:
            nearest_fac_stops = find_nearest_facilities(facilities_location, bus_stops_df, return_count=5)
        
            for _, row in nearest_fac_stops.iterrows():
                facility_stops.append({
                    'lat': row[lat_col],
                    'lon': row[lon_col],
                    '정류장명': row[정류장명],
                    '행정동명': row[행정동명],
                    'dist_road_m': int(row['road_dist_m']),
                    'dist_straight_m': int(row['straight_dist_m']),
                })
        except Exception as e:
            raise RuntimeError(f'시설 위치 추천 오류: {str(e)}')


    # --- DataFrame 생성과 컬럼 정렬 ---
    user_columns = ['lat', 'lon', '정류장명', '행정동명', 'dist_road_m', 'dist_straight_m']
    fac_columns = ['lat', 'lon', '정류장명', '행정동명', 'dist_road_m', 'dist_straight_m']

    user_df = pd.DataFrame(user_stops, columns=user_columns)
    fac_df = pd.DataFrame(facility_stops, columns=fac_columns)

    return {'user_nearby': user_df, 'facility_nearby': fac_df}

