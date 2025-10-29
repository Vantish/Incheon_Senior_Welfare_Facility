import streamlit as st
from app_home import run_home
from app_map import run_map
from define import set_sidebar_background



# 메인에서는 각 함수를 돌립니다.


def main():

    menu_list = ['홈', '위치 작성']
    menu_select = st.sidebar.selectbox('메뉴', menu_list)
    set_sidebar_background("./data/20678.jpg")

    if menu_select == menu_list[0]:
        run_home()
    elif menu_select == menu_list[1]:
        run_map()



if __name__ == '__main__':
    main()