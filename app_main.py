import streamlit as st
from app_home import run_home
from app_map import run_map
from app_chatbot_hr import run_chatbot_hhr
from app_news import run_news
from define import set_sidebar_background 

# --- 🚀 메인 함수 ---
def main():
    st.set_page_config(layout="wide")
    
    set_sidebar_background("./data/sb_bg.png")  # 사이드바 배경 이미지

    with st.sidebar:
        # 🔹 버튼 배경만 자연스럽게 blending 되도록 CSS 수정
        st.markdown("""
            <style>
            section[data-testid="stSidebar"] button[kind="secondary"] {
                background-color: rgba(255,255,255,0.1) !important; /* 투명한 흰색 */
                color: white !important;
                border: none !important;
                box-shadow: none !important;
                border-radius: 8px !important;
                transition: background-color 0.3s ease-in-out;
            }

            section[data-testid="stSidebar"] button[kind="secondary"]:hover {
                background-color: rgba(255,255,255,0.25) !important;
            }

            /* 버튼 간격을 약간 주어 자연스럽게 정렬 */
            section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div {
                margin-bottom: 4px;
            }
            </style>
        """, unsafe_allow_html=True)

        # 🔹 페이지 버튼
        if st.button("홈", key="home", use_container_width=True):
            st.session_state.page = "홈"
        if st.button("시니어 시설 추천 받기", key="map", use_container_width=True):
            st.session_state.page = "시니어 시설 추천 받기"
        if st.button("시니어 건강 상담사", key="chatbot", use_container_width=True):
            st.session_state.page = "시니어 건강 상담사"

    # 🔹 페이지 내용
    if "page" not in st.session_state:
        st.session_state.page = "홈"

    if st.session_state.page == "홈":
        run_home()
    elif st.session_state.page == "시니어 시설 추천 받기":
        run_map()
    elif st.session_state.page == "시니어 건강 상담사":
        run_chatbot_hhr()


    # menu_list = ['홈', '시니어 시설 추천 받기', '건강 상담사']
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