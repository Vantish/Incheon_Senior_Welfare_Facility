import streamlit as st

# 홈 파트에서는 해당 앱을 만들게된 배경, 대략적인 기능 등
# 기획서에 작성된 내용을 기반으로 웹 대시보드를 작성하시면 됩니다.

def run_home():
    # 페이지 기본 설정
    st.set_page_config(page_title="인천 맞춤 노인 돌봄 서비스", layout="wide")

    # 상단 이미지 및 제목
    st.image("data/home_tit.png", use_container_width=True)
    #st.markdown("<h1 style='text-align:center; margin-bottom: 0.3rem;'>인천 맞춤 노인 돌봄 서비스</h1>", unsafe_allow_html=True)
    #st.markdown("<p style='text-align:center; color:gray; margin-top:0;'>위치 기반으로 시설, 맛집, 여가시설, 버스 정보를 한눈에 확인하세요.</p>", unsafe_allow_html=True)
    
    # 탭 구성 (사용자용: 홈 / 주요 기능 / 사용법)
    tab1, tab2, tab3 = st.tabs(["홈", "주요 기능", "사용법"])

    # 탭 1: 홈
    with tab1:
        st.markdown("### 나의 소중한 부모님의 행복을 함께 생각하는 보호자 여러분을 위한 인천 맞춤 돌봄 서비스")
        st.markdown("""
        이 웹 앱은 인천 시민, 특히 **노년층**을 위한 생활 편의 정보를 통합 제공하기 위해 기획되었습니다.  
        복지, 교통, 문화, 맛집 등 다양한 정보를 한눈에 확인하고, 위치 기반으로 필요한 정보를 쉽게 찾을 수 있도록 구성했습니다.
        
        **주요 대상**:
        - 시설 이용자의 보호자
        - 인천 지역 거주 어르신
        - 지역 복지사 및 행정 담당자  
        - 생활 정보가 필요한 일반 시민
        """)

    # 탭 2: 주요 기능
    with tab2:
        st.markdown("### 주요 기능 소개")
        # 간단한 카드 스타일 열
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("- **노인복지시설 정보**: 위치, 시설 유형 별 확인 가능")
            st.markdown("- **맛집 추천**: 사용자 위치 기반의 인기 맛집 리스트 제공")
        with c2:
            st.markdown("- **문화·체육시설 안내**: 공원내 체육시설 정보 제공")
            st.markdown("- **버스 정류장 및 노선 정보**: 주변 정류장 위치, 버스 노선 조회")

    # 탭 3: 사용법 (노년층을 고려한 쉬운 문장, 큰 글씨)
    with tab3:
        st.markdown("<h2 style='text-align:left; font-size:22px;'>간단한 사용법</h2>", unsafe_allow_html=True)
        st.markdown("""
- 1단계: 왼쪽 메뉴에서 '위치 작성'을 선택하세요.
- 2단계: 화면에서 본인의 위치(또는 확인하려는 주소)를 입력하세요.
- 3단계: 나타난 지도에서 추천 시설을 확인하세요. 오른쪽 목록에서 시설을 택하면 상세 위치가 표시됩니다.
- 4단계: '정류장'을 선택하면 근처 버스 정류장과 노선을 확인할 수 있습니다.
- 도움말: 글씨가 작으면 브라우저의 확대 기능을 이용하세요(예: Ctrl + +).

팁: 큰 글씨와 간단한 버튼으로 구성해 두었으니 천천히 하나씩 눌러 보세요.
""", unsafe_allow_html=True)

    # # 탭 3: 기획 배경
    # with tab3:
    #     st.markdown("## 🎯 기획 배경")
    #     st.markdown("""
    #     - 📈 **고령화 사회 대응**: 노년층의 정보 접근성 향상 필요  
    #     - 🧭 **지역 정보 통합 부족**: 흩어진 정보를 한 곳에서 확인할 수 있는 플랫폼 필요  
    #     - 🚍 **교통·문화 접근성 개선**: 실시간 정보 제공을 통한 생활 편의성 향상  
    #     """)

    # 하단 개발자 정보
    st.markdown("---")
    st.markdown("""
    **지역**: 인천광역시  
    **기술 스택**: Python, Streamlit, OpenAPI
    """)

    
