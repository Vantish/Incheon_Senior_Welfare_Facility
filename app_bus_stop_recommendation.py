import pandas as pd
import matplotlib.pyplot as plt
from sklearn.neighbors import NearestNeighbors
from geopy.geocoders import Nominatim
from geopy.distance import distance
from geopy.distance import geodesic



# 사용자 위치정보(user_location)와 해당 정보를 바탕으로 계산된 시설의 위치정보(facilities_location)를 입력받은 후
# 사용자 근처 가장 가까운 정류장 5개와 시설에서 가장 가까운 정류장 5개를 딕셔너리 형태로 반환합니다.
# 반환 정보 = 'user_nearby' and 'facility_nearby'

bus_stops_df = pd.read_csv('./data/버스정류장.csv')


def bus_stop_recommendation(user_location, facilities_location, n_neighbors=10):

    user_stops, facility_stops = [], []

    # --- 컬럼명 탐색 ---
    cols = bus_stops_df.columns.tolist()
    lat_col = next((c for c in cols if '위도' in c.lower() or 'latitude' in c.lower() or 'lat' == c.lower()), None)
    lon_col = next((c for c in cols if '경도' in c.lower() or 'longitude' in c.lower() or 'lon' == c.lower() or 'lng' == c.lower()), None)
    정류장명 = next((c for c in cols if any(term in c.lower() for term in ['정류소명', '정류장명', '정류소 명', '정류장 명'])), None)
    행정동명 = next((c for c in cols if any(term in c.lower() for term in ['행정동명', '행정동 명', '동이름'])), None)

    if (lat_col is None) or (lon_col is None):
        st.error(f'위도/경도 컬럼을 찾을 수 없습니다. 현재 컬럼: {", ".join(cols)}')
        return None
    if 정류장명 is None:
        st.warning('정류장명 컬럼을 찾을 수 없습니다. 대체값을 사용합니다.')
        정류장명 = cols[0]
    if 행정동명 is None:
        st.warning('행정동명 컬럼을 찾을 수 없습니다. 대체값을 사용합니다.')
        행정동명 = cols[0]

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
                    'dist_fac_m': int(dist * 1000)
                }
                facility_stops.append(stop_info)

        except Exception as e:
            st.error(f'시설 위치 추천 오류: {str(e)}')
            facility_stops = []

    # --- DataFrame 생성과 컬럼 정렬 ---
    user_columns = ['lat', 'lon', '정류장명', '행정동명', 'dist_user_m']
    fac_columns = ['lat', 'lon', '정류장명', '행정동명', 'dist_fac_m']

    user_df = pd.DataFrame(user_stops, columns=user_columns)
    fac_df = pd.DataFrame(facility_stops, columns=fac_columns)

    return {'user_nearby': user_df, 'facility_nearby': fac_df}

