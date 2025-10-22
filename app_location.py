import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim


# 이 부분의 기능은 사용자의 위치를 찍는 부분입니다.
# 도로명 주소를 입력하면 지도에 해당 위치가 표시되는 기능을 구현할 예정입니다.
# 또한 사용자가 이용하고 싶은 시설의 분류 역시도 선택합니다.
# 입력한 값을 리턴값으로 넣어서 메인에서 받습니다.

df = pd.read_csv('./data/인천광역시_노인복지시설_현황.csv')


def run_location():
    # 해당 부분에 사용자의 위도, 경도, 도로명 주소, 이용하고싶은 시설 분류가 담긴 데이터프레임을 반환
    
    st.title('위치 및 시설 유형 검색')

    address = st.text_input("주소를 입력하세요:")
    facility_types = df['시설유형'].unique()
    selected_type = st.selectbox("시설 유형을 선택하세요 (선택 안 할 경우 기본값):", options=['선택 안 함'] + list(facility_types))

# 메인이랑 연결되면서 화면출력 맨 밑에 에러부분생김
    location = None
    if address:
        geolocator = Nominatim(user_agent="myGeocoder")
        location = geolocator.geocode(address)
    if not location:
        st.error("해당 주소를 찾을 수 없습니다.")

    # 지도 초기 위치 설정: 주소 위치 우선, 없으면 시설 위치 중 첫 번째 우선
    if location:
        map_center = [location.latitude, location.longitude]
        zoom_start = 16
    elif selected_type != '선택 안 함':
        filtered_df = df[df['시설유형'] == selected_type]
        if not filtered_df.empty:
            map_center = [filtered_df.iloc[0]['lat'], filtered_df.iloc[0]['lon']]
            zoom_start = 13
        else:
            map_center = [37.4563, 126.7052]  # 인천시 중심 좌표 기본값(예시)
            zoom_start = 11
    else:
        map_center = [37.4563, 126.7052]  # 인천시 중심 좌표 기본값(예시)
        zoom_start = 11

    m = folium.Map(location=map_center, zoom_start=zoom_start)

    # 주소가 입력된 경우 빨간 마커 추가
    if location:
        folium.Marker(
            [location.latitude, location.longitude],
            popup='내 위치',
            icon=folium.Icon(color='red')
        ).add_to(m)

    # 시설유형이 선택된 경우 파란 마커 추가
    if selected_type != '선택 안 함':
        filtered_df = df[df['시설유형'] == selected_type]
        if filtered_df.empty:
            st.write("선택한 시설 유형의 데이터가 없습니다.")
        else:
            for idx, row in filtered_df.iterrows():
                folium.Marker(
                    location=[row['lat'], row['lon']],
                    popup=f"{row['시설명']}",
                    icon=folium.Icon(color='blue')
                ).add_to(m)

            # 시설표도 표시
            st.dataframe(filtered_df[['시설명', '도로명 주소', '구군']])

    # folium 지도 표시
    st_folium(m, width=700, height=500)

    
    lis = [location.latitude, location.longitude, selected_type]
    return lis