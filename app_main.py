import streamlit as st
from app_home import run_home
from app_map import run_map
from define import set_sidebar_background



# 메인에서는 각 함수를 돌립니다.


def main():

    menu_list = ['홈', '사용자 위치 입력', '챗봇']
    menu_select = st.sidebar.selectbox('메뉴', menu_list)
    set_sidebar_background("./data/sb_bg.png")

    if menu_select == menu_list[0]:
        run_home()
    elif menu_select == menu_list[1]:
        run_map()
    elif menu_select == menu_list[2]:
        pass



if __name__ == '__main__':
    main()