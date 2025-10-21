import streamlit as st
from app_home import run_home
from app_map import run_map
from app_location import run_location



def main():
    st.markdown(
    "<h1 style='text-align: center;'>인천광역시 노인복지시설<br>위치기반 추천 앱</h1>",
    unsafe_allow_html=True)

    menu_list = ['홈', '위치 작성', '추천']
    menu_select = st.sidebar.selectbox('메뉴', menu_list)

    if menu_select == menu_list[0]:
        run_home()
    elif menu_select == menu_list[1]:
        run_map()
    elif menu_select == menu_list[2]:
        run_location()



if __name__ == '__main__':
    main()