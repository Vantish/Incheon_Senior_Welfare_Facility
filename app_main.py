import streamlit as st
from app_chatbot_mj import run_chatbot_app
from app_home import run_home
from app_map import run_map
from app_chatbot_JS import run_chatbot
from define import set_sidebar_background # 사용자 정의 배경 함수 유지


# --- 📌 Python 로직: st.markdown과 if st.button 사용 ---
def create_sidebar_item(label, page_name, svg_path_d, current_page):
    
    is_active = current_page == page_name
    button_class = "sidebar-visual-item-active" if is_active else "sidebar-visual-item"

    # 1. 시각적 요소 (st.markdown) 렌더링
    st.sidebar.markdown(f"""
        <div class='{button_class}'>
            <svg xmlns="http://www.w3.org/2000/svg"
                viewBox="0 -960 960 960"
                width="40px"
                height="40px"
                style="fill:white; margin-right:10px; vertical-align:middle;">
                <path d="{svg_path_d}"/>
            </svg>
            {label}
        </div>
    """, unsafe_allow_html=True)
    
    # 2. 기능적 요소 (st.button) 렌더링 (CSS가 겹치게 함)
    if st.sidebar.button(
        label=" ",  # 빈 문자열
        key=f"sidebar_btn_{page_name}",
    ):
        st.session_state.page = page_name
        st.rerun() # 상태 변경 후 즉시 페이지 전환

    st.sidebar.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)


# --- 🎨 CSS 수정 (버튼 위치 및 크기 강제 일치) ---
def apply_custom_css():
    st.markdown("""
    <style>
    /* 1. 사이드바 배경 */
    [data-testid="stSidebar"] {
        background-color: transparent !important; 
    }
    
    /* 2. 시각적 요소 (st.markdown) */
    .sidebar-visual-item, .sidebar-visual-item-active {
        display: flex; 
        align-items: center; 
        width: 100%;
        
        /* 🚨 (A) 시각적 들여쓰기: 이 값을 기준으로 모든 것이 정렬됩니다. */
        padding: 12px 20px; 
        
        font-size: 20px;
        font-weight: bold !important;
        color: white !important;
        background-color: transparent;
        transition: background-color 0.3s ease;
        border-radius: 12px;
        
        /* (B) 시각적 높이: 64px */
        height: 64px; 
        margin-bottom: 10px;
        
        box-sizing: border-box; 
    }
    .sidebar-visual-item-active {
        background-color: rgba(255, 255, 255, 0.2); 
    }

    /* 3. 기능적 버튼 (st.button)의 래퍼(div) */
    div.stButton {
        /* 이 래퍼는 시각적 요소와 겹치게 됩니다. */
        margin: 0 !important;
        padding: 0 !important; 
        width: 100%;
        
        /* 🚨 (B) + margin-bottom = 74px 위로 이동 */
        margin-top: -74px !important; 
        
        position: relative; 
        z-index: 100;
        
        /* 🚨 버튼이 위치를 벗어나는 것을 막기 위해, 래퍼의 좌우 마진을 없앱니다. */
        margin-left: 0 !important;
        margin-right: 0 !important;
    }

    /* 4. 실제 버튼 (<button>) */
    div.stButton > button {
        background-color: rgba(0, 0, 0, 0.001) !important; 
        border: none !important;
        color: transparent !important; 
        box-shadow: none !important;
        
        width: 100%;
        height: 64px;
        
        /* 🚨 (A) 시각적 패딩과 동일하게 설정하여 크기를 맞춥니다. */
        padding: 12px 20px !important; 
        margin: 0 !important;
        
        box-sizing: border-box; /* 패딩이 크기를 벗어나지 않도록 유지 */
        
        cursor: pointer;
        
        /* 🚨 버튼이 왼쪽으로 붙어 튀어나가는 것을 방지 */
        left: 0 !important;
    }

    /* 5. 호버 효과 */
    div.stButton > button:hover {
        background-color: rgba(255, 255, 255, 0.3) !important;
        padding: 12px 20px !important;
        margin: 0 !important; 
        border-radius: 12px; 
    }
    
    /* 6. 사이드바 내부의 stMarkdown 기본 패딩 제거 (시각적 요소가 왼쪽 끝에서 시작하도록) */
    /* 이 설정이 마크다운의 시작점을 결정하고, 버튼이 이 시작점에 맞춰집니다. */
    div[data-testid="stSidebar"] div.stMarkdown {
        padding-left: 0px !important;
        padding-right: 0px !important;
    }
    
    .sidebar-divider {
        border-bottom: 1px solid rgba(255,255,255,0.3);
        margin: 10px 0px; 
        position: relative;
        z-index: 50; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- 🚀 메인 함수 ---
def main():
    st.set_page_config(layout="wide")
    
    set_sidebar_background("./data/sb_bg.png")

    # CSS 적용
    apply_custom_css()

    if "page" not in st.session_state:
        st.session_state.page = "홈"
    
    current_page = st.session_state.page

    # 사이드바 아이템 생성
    create_sidebar_item(
        "홈", "홈",
        "M240-200h120v-240h240v240h120v-360L480-740 240-560v360Zm-80 80v-480l320-240 320 240v480H520v-240h-80v240H160Zm320-350Z",
        current_page
    )

    create_sidebar_item(
        "시니어 시설 추천 받기", "시니어 시설 추천 받기",
        "M480-80q-106 0-173-33.5T240-200q0-24 14.5-44.5T295-280l63 59q-9 4-19.5 9T322-200q13 16 60 28t98 12q51 0 98.5-12t60.5-28q-7-8-18-13t-21-9l62-60q28 16 43 36.5t15 45.5q0 53-67 86.5T480-80Zm1-220q99-73 149-146.5T680-594q0-102-65-154t-135-52q-70 0-135 52t-65 154q0 67 49 139.5T481-300Zm-1 100Q339-304 269.5-402T200-594q0-71 25.5-124.5T291-808q40-36 90-54t99-18q49 0 99 18t90 54q40 36 65.5 89.5T760-594q0 94-69.5 192T480-200Zm0-320q33 0 56.5-23.5T560-600q0-33-23.5-56.5T480-680q-33 0-56.5 23.5T400-600q0 33 23.5 56.5T480-520Zm0-80Z",
        current_page
    )

    create_sidebar_item(
        "나만의 건강 상담사", "나만의 건강 상담사",
        "M440-120v-80h320v-284q0-117-81.5-198.5T480-764q-117 0-198.5 81.5T200-484v244h-40q-33 0-56.5-23.5T80-320v-80q0-21 10.5-39.5T120-469l3-53q8-68 39.5-126t79-101q47.5-43 109-67T480-840q68 0 129 24t109 66.5Q766-707 797-649t40 126l3 52q19 9 29.5 27t10.5 38v92q0 20-10.5 38T840-249v49q0 33-23.5 56.5T760-120H440Zm-80-280q-17 0-28.5-11.5T320-440q0-17 11.5-28.5T360-480q17 0 28.5 11.5T400-440q0 17-11.5 28.5T360-400Zm240 0q-17 0-28.5-11.5T560-440q0-17 11.5-28.5T600-480q17 0 28.5 11.5T640-440q0 17-11.5 28.5T600-400Zm-359-62q-7-106 64-182t177-76q89 0 156.5 56.5T720-519q-91-1-167.5-49T435-698q-16 80-67.5 142.5T241-462Z",
        current_page
    )


    # --- 페이지 라우팅 ---
    if st.session_state.page == "홈":
        run_home()
    elif st.session_state.page == "시니어 시설 추천 받기":
        run_map()
    elif st.session_state.page == "나만의 건강 상담사":
        run_chatbot()
    

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