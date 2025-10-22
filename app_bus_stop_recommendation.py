import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import folium
from sklearn.neighbors import NearestNeighbors
from streamlit_folium import st_folium


from app_bus_route import check_bus_route


def bus_stop_recommendation():
    bus_list = check_bus_route()
    if bus_list is not None:
        pass
    else:
        df = pd.read_csv('./data/버스정류장.csv')

        # 인천 중심 좌표
        incheon_center = [37.456255, 126.705206]
        st.write('지도에서 자신의 위치를 클릭하세요.')

        # 기본 지도 생성
        m = folium.Map(location=incheon_center, zoom_start=11)

        # 지도 클릭 시 사용자 위치 선택 가능
        user_data = st_folium(m, width=700, height=500)

        user_location = None
        if user_data and user_data['last_clicked']:
            user_location = (
                user_data['last_clicked']['lat'],
                user_data['last_clicked']['lng']
            )
            st.success(f'선택된 위치: {user_location}')

        if user_location and st.button('가장 가까운 정류장 찾기'):
            locations = df[['위도', '경도']].to_numpy()
            locations_rad = np.radians(locations)
            nbrs = NearestNeighbors(n_neighbors=5, metric='haversine')
            nbrs.fit(locations_rad)
            user_loc_rad = np.radians([user_location])

            distances, indices = nbrs.kneighbors(user_loc_rad)
            distances_km = distances[0] * 6371  # 거리(km)

            st.subheader('가장 가까운 5개 정류장')
            for i, (idx, dist) in enumerate(zip(indices[0], distances_km), start=1):
                facility = df.iloc[idx]
                st.write(f"{i}. {facility['정류소 명']} (ID: {facility['정류소아이디']}) - 거리: {dist:.2f} km")

                folium.Marker(
                    location=[facility['위도'], facility['경도']],
                    popup=f"{facility['정류소 명']} ({dist:.2f} km)",
                    icon=folium.Icon(color='blue')
                ).add_to(m)

            # 사용자 위치 마커
            folium.Marker(
                location=user_location,
                popup='내 위치',
                icon=folium.Icon(color='red')
            ).add_to(m)

            st_folium(m, width=700, height=500)


if __name__ == '__main__':
    bus_stop_recommendation()