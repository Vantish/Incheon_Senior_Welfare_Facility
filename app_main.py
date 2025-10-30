import streamlit as st
from app_chatbot_hr import run_chatbot_hhr
from app_chatbot_mj import run_chatbot_app
from app_home import run_home
from app_map import run_map
from app_chatbot_JS import run_chatbot
from define import set_sidebar_background


# --- 📌 핵심 수정: st.container를 사용하여 각 아이템을 래핑하고 겹치기 ---
# --- 📌 create_sidebar_item (컨테이너 제거, if st.button 사용) ---
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
    
    # 2. 기능적 요소 (st.button) 렌더링
    # (CSS가 이 버튼을 시각적 요소 위로 끌어올릴 것입니다)
    if st.sidebar.button(
        label=" ",  # 빈 문자열
        key=f"sidebar_btn_{page_name}",
    ):
        st.session_state.page = page_name
        st.rerun() 

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
        
        /* 🚨 1. width: 100% 를 제거합니다. */
        /* width: 100%; */ 
        
        height: 64px; /* 높이는 유지 */
        
        /* 🚨 2. padding을 0으로 설정합니다. */
        padding: 0 !important; 
        margin: 0 !important;
        
        /* 🚨 3. left: 0 과 right: 0 을 추가합니다. */
        /* 이것이 버튼을 양쪽 끝으로 강제로 늘려줍니다. */
        left: 0px !important;
        right: 0px !important;
        
        box-sizing: border-box; 
        cursor: pointer;
        
        /* left: 0 !important; (중복이므로 하나는 제거) */
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