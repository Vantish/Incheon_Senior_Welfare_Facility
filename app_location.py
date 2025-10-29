import streamlit as st
import pandas as pd
import requests




# 이 부분의 기능은 사용자의 위치를 찍는 부분입니다.
# 도로명 주소를 입력하면 지도에 해당 위치가 표시되는 기능을 구현할 예정입니다.
# 또한 사용자가 이용하고 싶은 시설의 분류 역시도 선택합니다.
# 입력한 값을 리턴값으로 넣어서 메인에서 받습니다.
# 지도 없이 , 사용자 도로명 주소 입력 => 위도, 경도 , 도로명 주소 받아서 리스트로
# 시설유형 선택 => 리스트로 

df= pd.read_csv('./data/인천광역시_노인복지시설_현황_최종.csv',encoding='euc-kr')


def run_location():
    # 해당 부분에 사용자의 위도, 경도, 도로명 주소, 이용하고싶은 시설 분류가 담긴 데이터프레임을 반환

    address = st.text_input("도로명 주소를 입력하세요 : (예 : 인천 서구 서곶로 284)")

    # kakao api도 상세 주소, 건물명 만으로는 검색 x 
    def get_lat_lon_kakao(address):
        url = "https://dapi.kakao.com/v2/local/search/address.json"
        headers = {"Authorization": "KakaoAK 61643eab4a108d8576a883813e67dafc"}  # 중괄호 제거
        params = {"query": address}
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
                data = response.json()
                if data.get("documents"):
                    top_result = data["documents"][0]
                    lat = float(top_result["y"])
                    lon = float(top_result["x"])
                return lat, lon
        return None, None
          

    lat, lon = get_lat_lon_kakao(address)


    # 2. 주소가 입력된 경우에만 시설유형 선택 UI 표시
    if address:
        facility_types = df['시설유형'].dropna().unique()
        selected_type = st.selectbox('시설유형을 선택하세요', facility_types)
    else:
        st.write('주소를 입력해주세요')
    

    # 주소가 비어 있으면 None 반환 (app_map에서 체크)
    if not address:
        st.info('주소를 입력하면 해당 위치를 찾아 추천을 제공합니다.')
        return None

    # 지오코딩 실패 시 None 반환
    if lat is None or lon is None:
        st.error("주소를 찾을 수 없습니다.")
        return None
        

    lis = [lat, lon, address, selected_type]  # 위도, 경도, 주소, 선택한 시설유형
    if st.button('입력'):
        st.session_state['user_location'] = lis
        return lis
    return None