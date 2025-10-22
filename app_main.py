import streamlit as st
from app_home import run_home
from app_map import run_map
from app_location import run_location

# 메인에서는 각 함수를 돌립니다.
# 이때 app_location 부분에서 받아온 사용자 정보를 다음 세션으로 넘기기 위해
# st.session_state 를 사용하여 전역변수처럼 저장합니다.
# 이후 해당 입력값을 app_map 에 넘깁니다.


def main():
    st.markdown(
    "<h1 style='text-align: center;'>인천광역시 노인복지시설<br>위치기반 추천 앱</h1>",
    unsafe_allow_html=True)

    menu_list = ['홈', '위치 작성', '추천']
    menu_select = st.sidebar.selectbox('메뉴', menu_list)

    if menu_select == menu_list[0]:
        run_home()
    elif menu_select == menu_list[1]:
        user_location = run_location()
        if user_location:
            st.session_state['user_location'] = user_location
            st.success("위치가 저장되었습니다.")
    elif menu_select == menu_list[2]:
        run_map(st.session_state.get('user_location'))



if __name__ == '__main__':
    main()