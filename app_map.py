import streamlit as st
from app_bus_stop_recommendation import bus_stop_recommendation
from app_bus_route import check_bus_route
from app_around_leisure_restaurant import around_leisure
from app_around_leisure_restaurant import around_restaurant

# 가장 복잡한 파트입니다.
# 만약 유저 위치가 입력받지 않았다면 에러 문구를
# 입력 받았다면 기능을 동작합니다.
# 먼저 사용자의 위치와 시설 분류를 기반으로 가장 가까운 시설을 추천합니다.
# 이후 거리를 계산하여 가장 가까운 시설을 찾습니다.
# 만약 사용자가 근처 맛집이나 가는 버스를 알고싶다면 멀티셀렉트를 이용하여 해당 기능을 지도에 표시합니다.
# 이후 각각의 부분에서 받아온 함수를 상황에 맞게 동작시켜서 정보를 받은 후, 해당 정보를 출력합니다.


def run_map(user_location = None):
    st.subheader('위치 기반 추천')
    st.text('\n')

    if user_location == None:
        st.error('사용자의 위치가 지정되지 않았습니다. 다시 지정해주세요.')
    else:
        select_list = ['맛집', '여가시설', '정류장']
        selection = st.multiselect('추가적으로 사용하실 정보를 입력해주세요.', select_list)
        if select_list[0] in selection:
            temp_restaurant = around_restaurant(user_location)
            pass
        if select_list[1] in selection:
            temp_leisure = around_leisure(user_location)
            pass
        if select_list[2] in selection:
            temp_bus_stop = bus_stop_recommendation(user_location)

            temp_bus = check_bus_route(temp_bus_stop)
            
            pass
    