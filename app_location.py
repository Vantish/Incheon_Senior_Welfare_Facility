import streamlit as st
import pandas as pd
import folium
from geopy.geocoders import Nominatim
from streamlit_folium import folium_static


# 이 부분의 기능은 사용자의 위치를 찍는 부분입니다.
# 도로명 주소를 입력하면 지도에 해당 위치가 표시되는 기능을 구현할 예정입니다.
# 또한 사용자가 이용하고 싶은 시설의 분류 역시도 선택합니다.
# 입력한 값을 리턴값으로 넣어서 메인에서 받습니다.

df = pd.read_csv('./data/인천광역시_노인복지시설 현황.csv', encoding='EUC-KR')

def run_location():
    # 해당 부분에 사용자의 위도, 경도, 도로명 주소, 이용하고싶은 시설 분류가 담긴 리스트로 반환
   
    st.title('내 위치 주변 시설 찾기')
    
    user_address =df['도로명 주소']
    user_location = st.text_input('도로명 주소를 입력해주세요.', user_address)

    facility_types = df['시설 유형'].unique().tolist()
    selected_facility = st.selectbox('이용하고 싶은 시설 분류를 선택해주세요.', facility_types)

    if user_location and selected_facility:
        return user_location, selected_facility
    
    # 주소를 위경도로 변환
    geolocator = Nominatim(user_agent="facility_mapper")
    location = geolocator.geocode(user_location)

    if location:
        lat, lon = location.latitude, location.longitude

        # 필터링: 선택한 시설 유형
        filtered_df = df[df['시설유형'] == selected_facility]

        # 지도 생성
        m = folium.Map(location=[lat, lon], zoom_start=13)

        # 사용자 위치 마커
        folium.Marker([lat, lon], tooltip='입력 주소 위치', icon=folium.Icon(color='red')).add_to(m)

        # 시설 마커 표시
        for _, row in filtered_df.iterrows():
            folium.Marker(
                [row['lat'], row['lon']],
                tooltip=row['시설명'],
                icon=folium.Icon(color='green')
            ).add_to(m)

        # 지도 출력
        folium_static(m)
    else:
        st.error("주소를 알 수 없습니다.")


 