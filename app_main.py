import streamlit as st
from app_chatbot_mj import run_chatbot_app
from app_home import run_home
from app_map import run_map
from app_chatbot_JS import run_chatbot
from define import set_sidebar_background


# 메인에서는 각 함수를 돌립니다.


def main():

    menu_list = ['홈', '사용자 위치 입력', '챗봇','챗봇2']
    menu_select = st.sidebar.selectbox('메뉴', menu_list)
    set_sidebar_background("./data/sb_bg.png")

    if menu_select == menu_list[0]:
        run_home()
    elif menu_select == menu_list[1]:
        run_map()
    elif menu_select == menu_list[2]:
        run_chatbot()
    elif menu_select == menu_list[3]:
        run_chatbot_app()



if __name__ == '__main__':
    main()