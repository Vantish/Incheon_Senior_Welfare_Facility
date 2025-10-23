import streamlit as st
import pandas as pd
import requests




# 이 부분의 기능은 사용자의 위치를 찍는 부분입니다.
# 도로명 주소를 입력하면 지도에 해당 위치가 표시되는 기능을 구현할 예정입니다.
# 또한 사용자가 이용하고 싶은 시설의 분류 역시도 선택합니다.
# 입력한 값을 리턴값으로 넣어서 메인에서 받습니다.
# 지도 없이 , 사용자 도로명 주소 입력 => 위도, 경도 , 도로명 주소 받아서 리스트로
# 시설유형 선택 => 리스트로 

df= pd.read_csv('./data/인천광역시_노인복지시설_현황.csv',encoding='euc-kr')


def run_location():
    # 해당 부분에 사용자의 위도, 경도, 도로명 주소, 이용하고싶은 시설 분류가 담긴 데이터프레임을 반환

    address = st.text_input("주소를 입력하세요")

    def get_lat_lon(address):
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": address,
            "format": "json",
            "limit": 1,
            "addressdetails": 0,
        }
        headers = {"User-Agent": "MyApp/1.0 (your_email@example.com)"}
        response = requests.get(url, params=params,headers=headers)
       
        if response.status_code == 200 and response.json():
            result = response.json()[0]
            return float(result["lat"]), float(result["lon"])
        else:
            return None, None

    # 먼저 시설 유형 선택 UI는 항상 노출
    facility_types = df['시설유형'].dropna().unique()
    selected_type = st.selectbox('시설유형을 선택하세요', facility_types)
    st.write(f"선택한 시설유형: {selected_type}")

    # 주소가 비어 있으면 None 반환 (app_map에서 체크)
    if not address:
        st.info('주소를 입력하면 해당 위치를 찾아 추천을 제공합니다.')
        return None

    lat, lon = get_lat_lon(address)

    # 지오코딩 실패 시 None 반환
    if lat is None or lon is None:
        st.error("주소를 찾을 수 없습니다.")
        return None

    # 성공적으로 찾은 경우 위도/경도 표시 후 반환
    st.success(f"위도: {lat}, 경도: {lon}")

    lis = [lat, lon, address, selected_type]  # 위도, 경도, 주소, 선택한 시설유형
    return lis





    


   