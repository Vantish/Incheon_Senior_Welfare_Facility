import streamlit as st
from app_chatbot_mj import run_chatbot_app
from app_home import run_home
from app_map import run_map
from app_chatbot_JS import run_chatbot
from define import set_sidebar_background


# 메인에서는 각 함수를 돌립니다.


def main():

    # 사이드바 배경 설정
    set_sidebar_background("./data/sb_bg.png")

    # 버튼 스타일 정의
    st.sidebar.markdown("""
    <a href="?page=home" class="sidebar-button">
        <svg xmlns="http://www.w3.org/2000/svg"
            viewBox="0 -960 960 960"
            width="40px"
            height="40px"
            style="fill:#ffffff; margin-right:10px; vertical-align:middle;">
        <path d="M240-200h120v-240h240v240h120v-360L480-740 240-560v360Zm-80 80v-480l320-240 320 240v480H520v-240h-80v240H160Zm320-350Z"/>
        </svg>
        홈
    </a>
    
    <div class="sidebar-divider"></div>

    <a href="?page=location" class="sidebar-button">
        <svg xmlns="http://www.w3.org/2000/svg"
            viewBox="0 -960 960 960"
            width="40px"
            height="40px"
            style="fill:#ffffff; vertical-align:middle; margin-right:10px;">
        <path d="M480-80q-106 0-173-33.5T240-200q0-24 14.5-44.5T295-280l63 59q-9 4-19.5 9T322-200q13 16 60 28t98 12q51 0 98.5-12t60.5-28q-7-8-18-13t-21-9l62-60q28 16 43 36.5t15 45.5q0 53-67 86.5T480-80Zm1-220q99-73 149-146.5T680-594q0-102-65-154t-135-52q-70 0-135 52t-65 154q0 67 49 139.5T481-300Zm-1 100Q339-304 269.5-402T200-594q0-71 25.5-124.5T291-808q40-36 90-54t99-18q49 0 99 18t90 54q40 36 65.5 89.5T760-594q0 94-69.5 192T480-200Zm0-320q33 0 56.5-23.5T560-600q0-33-23.5-56.5T480-680q-33 0-56.5 23.5T400-600q0 33 23.5 56.5T480-520Zm0-80Z"/>
        </svg>
        사용자 위치 입력
    </a>
                        
    <div class="sidebar-divider"></div>

    <a href="?page=chatbot" class="sidebar-button">
        <svg xmlns="http://www.w3.org/2000/svg"
            viewBox="0 -960 960 960"
            width="40px"
            height="40px"
            style="fill:#ffffff; vertical-align:middle; margin-right:10px;">
        <path d="M440-120v-80h320v-284q0-117-81.5-198.5T480-764q-117 0-198.5 81.5T200-484v244h-40q-33 0-56.5-23.5T80-320v-80q0-21 10.5-39.5T120-469l3-53q8-68 39.5-126t79-101q47.5-43 109-67T480-840q68 0 129 24t109 66.5Q766-707 797-649t40 126l3 52q19 9 29.5 27t10.5 38v92q0 20-10.5 38T840-249v49q0 33-23.5 56.5T760-120H440Zm-80-280q-17 0-28.5-11.5T320-440q0-17 11.5-28.5T360-480q17 0 28.5 11.5T400-440q0 17-11.5 28.5T360-400Zm240 0q-17 0-28.5-11.5T560-440q0-17 11.5-28.5T600-480q17 0 28.5 11.5T640-440q0 17-11.5 28.5T600-400Zm-359-62q-7-106 64-182t177-76q89 0 156.5 56.5T720-519q-91-1-167.5-49T435-698q-16 80-67.5 142.5T241-462Z"/>
        </svg>
        챗봇
    </a>
    """, unsafe_allow_html=True)

    st.markdown("""
    <style>
    .sidebar-button {
        display: block;
        width: 100%;
        padding: 12px 20px;
        margin: 4px;
        font-size: 20px;
        font-weight: bold !important;
        color: white !important;
        text-align: left !important;
        text-decoration: none !important;
        background-color: transparent;
        border: none;
        transition: background-color 0.3s ease, color 0.3s ease;
    }
    .sidebar-button:hover {
        background-color: rgba(255, 255, 255, 0.3);
        border-radius: 12px;
    }
    .sidebar-divider {
    border-bottom: 1px solid rgba(255,255,255,0.3);
    }
    </style>
    """, unsafe_allow_html=True)



    # 초기 페이지 설정
    if "page" not in st.session_state:
        st.session_state.page = "홈"

    # 페이지 라우팅
    if st.session_state.page == "홈":
        run_home()
    elif st.session_state.page == "사용자 위치 입력":
        run_map()
    elif st.session_state.page == "챗봇":
        pass
    

    # menu_list = ['홈', '사용자 위치 입력', '챗봇']
    # menu_select = st.sidebar.selectbox('메뉴', menu_list)
    # set_sidebar_background("./data/sb_bg.png")

    # if menu_select == menu_list[0]:
    #     run_home()
    # elif menu_select == menu_list[1]:
    #     run_map()
    # elif menu_select == menu_list[2]:
    #     pass


if __name__ == '__main__':
    main()