import streamlit as st

# 홈 파트에서는 해당 앱을 만들게된 배경, 대략적인 기능 등
# 기획서에 작성된 내용을 기반으로 웹 대시보드를 작성하시면 됩니다.

def run_home():
    # 페이지 기본 설정
    st.set_page_config(page_title="인천 맞춤 노인 돌봄 서비스", layout="wide")

    # 상단 이미지 및 제목
    # st.image("data/home_tit.png", use_container_width=True)
    st.markdown("<h1 style='text-align:left;'>인천 맞춤 노인 돌봄 서비스</h1>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:20px; text-align:left; color:gray; margin-top:0;'>위치 기반으로 시설, 맛집, 여가시설, 버스 정보를 한눈에 확인하세요.</p>", unsafe_allow_html=True)
    
    # 탭 구성 (사용자용: 홈 / 주요 기능 / 사용법)
    tab1, tab2, tab3 = st.tabs(["홈", "주요 기능", "사용법"])
    
    # 탭 폰트 크기 조정 CSS
    st.markdown("""
    <style>
    /* 탭 버튼 텍스트 크기 조정 */
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 20px;
        font-weight: 500;
    }
    /* 탭 버튼 자체 높이 조정 */
    .stTabs [data-baseweb="tab-list"] button {
        padding: 32px 24px;
    }
    </style>
    """, unsafe_allow_html=True)

    # 탭 1: 홈
    with tab1:
        st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
        st.markdown("### 나의 소중한 부모님의 행복을 함께 생각하는 보호자 여러분을 위한 인천 맞춤 돌봄 서비스")
        st.markdown("""
        이 웹 앱은 인천 시민, 특히 **노년층**을 위한 생활 편의 정보를 통합 제공하기 위해 기획되었습니다.  
        복지, 교통, 문화, 맛집 등 다양한 정보를 한눈에 확인하고, 위치 기반으로 필요한 정보를 쉽게 찾을 수 있도록 구성했습니다.
        """)
        
        # CSS 스타일 추가
        st.markdown("""
        <style>
        .target-container {
            display: flex;
            gap: 15px;
            margin-top: 20px;
            flex-wrap: wrap;
        }
        .target-box {
            background-color: #f9f9f9;
            border: 1px solid #e0e0e0;
            border-radius: 12px;
            padding: 40px 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            flex: 1;
            min-width: 200px;
            transition: all 0.3s ease;
        }
        .target-box:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            transform: translateY(-10px);
        }
        .target-icon {
            margin-bottom: 24px;
        }
        .target-text {
            font-size: 20px;
            font-weight: 600;
            color: #333333;
            text-align: center;
            line-height: 1.4;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown("<h4 style='color:#333333; font-size:24px; margin-top:30px;'>주요 대상</h4>", unsafe_allow_html=True)
        

        # 한 줄에 4개의 박스
        st.markdown("""
        <div class="target-container">
            <div class="target-box">
                <div class="target-icon"><img src="https://cdn-icons-png.flaticon.com/128/12556/12556753.png" width="64px"></div>
                <div class="target-text">시설 이용자의<br>보호자</div>
            </div>
            <div class="target-box">
                <div class="target-icon"><img src="https://cdn-icons-png.flaticon.com/128/12556/12556745.png" width="64px"></div>
                <div class="target-text">인천 지역 거주<br>어르신</div>
            </div>
            <div class="target-box">
                <div class="target-icon"><img src="https://cdn-icons-png.flaticon.com/128/12556/12556793.png" width="64px"></div>
                <div class="target-text">지역 복지사 및<br>행정 담당자</div>
            </div>
            <div class="target-box">
                <div class="target-icon"><img src="https://cdn-icons-png.flaticon.com/128/12556/12556768.png" width="64px"></div>
                <div class="target-text">생활 정보가 필요한<br>일반 시민</div>
            </div>
        </div>
        """, unsafe_allow_html=True)


    # 탭 2: 주요 기능
    with tab2:
        st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
        st.markdown("### 주요 기능 소개")
        st.markdown("""
        이 서비스는 노년층의 편리한 생활을 위해 다양한 정보를 제공합니다.  
        아래 기능들을 통해 필요한 정보를 쉽게 찾아보세요.
        """)
        
        # 구분선 추가
        st.markdown("<hr style='border: 1px solid #e0e0e0; margin: 30px 0;'>", unsafe_allow_html=True)
        
        # CSS 스타일
        st.markdown("""
        <style>
        .feature-container {
            display: flex;
            gap: 15px;
            margin-top: 20px;
            flex-wrap: wrap;
        }
        .feature-box {
            background-color: #f9f9f9;
            border: 1px solid #e0e0e0;
            border-radius: 12px;
            padding: 40px 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            flex: 1;
            min-width: 200px;
            transition: all 0.3s ease;
        }
        .feature-box:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            transform: translateY(-10px);
        }
        .feature-icon {
            margin-bottom: 24px;
        }
        .feature-title {
            font-size: 20px;
            font-weight: 700;
            color: #333333;
            margin-bottom: 8px;
            text-align: center;
        }
        .feature-desc {
            font-size: 18px;
            color: #666666;
            line-height: 1.5;
            text-align: center;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown("<h4 style='color:#333333; font-size:24px; margin-top:10px;'>제공 기능</h4>", unsafe_allow_html=True)
        
        # 한 줄에 4개 박스
        st.markdown("""
        <div class="feature-container">
            <div class="feature-box">
                <div class="feature-icon"><img src="https://cdn-icons-png.flaticon.com/128/11370/11370430.png" width="64px"></div>
                <div class="feature-title">노인복지시설 정보</div>
                <div class="feature-desc">위치, 시설 유형 별<br>확인 가능</div>
            </div>
            <div class="feature-box">
                <div class="feature-icon"><img src="https://cdn-icons-png.flaticon.com/128/8740/8740492.png" width="64px"></div>
                <div class="feature-title">맛집 추천</div>
                <div class="feature-desc">사용자 위치 기반의<br>인기 맛집 리스트 제공</div>
            </div>
            <div class="feature-box">
                <div class="feature-icon"><img src="https://cdn-icons-png.flaticon.com/128/11370/11370452.png" width="64px"></div>
                <div class="feature-title">문화·체육시설 안내</div>
                <div class="feature-desc">공원내 체육시설<br>정보 제공</div>
            </div>
            <div class="feature-box">
                <div class="feature-icon"><img src="https://cdn-icons-png.flaticon.com/128/1523/1523481.png" width="64px"></div>
                <div class="feature-title">버스 정류장 및 노선 정보</div>
                <div class="feature-desc">주변 정류장 위치,<br>버스 노선 조회</div>
            </div>
        </div>
        """, unsafe_allow_html=True)


    # 탭 3: 사용법 (노년층을 고려한 쉬운 문장, 큰 글씨)
    with tab3:
        st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align:left; font-size:28px; color:#333333;'>간단한 사용법</h2>", unsafe_allow_html=True)
        st.markdown("<p style='font-size:18px; color:#666666; margin-bottom:30px;'>아래 순서대로 따라하시면 쉽게 이용하실 수 있습니다.</p>", unsafe_allow_html=True)
        
        # CSS 스타일
        st.markdown("""
        <style>
        .step-container {
            margin-bottom: 25px;
        }
        .step-box {
            border: 1px solid #e0e0e0;
            border-radius: 16px;
            padding: 30px;
            display: flex;
            align-items: center;
            gap: 25px;
            transition: all 0.3s ease;
        }
        .step-box:hover {
            transform: translateY(-5px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
        }
        .step-number {
            background-color: #e0590f;
            color: #ffffff;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            font-weight: 700;
            flex-shrink: 0;
        }
        .step-content {
            flex: 1;
        }
        .step-title {
            font-size: 20px;
            font-weight: 700;
            color: #202020;
            margin-bottom: 8px;
        }
        .step-desc {
            font-size: 18px;
            color: #202020;
            line-height: 1.6;
        }
        .step-icon {
            width: 50px;
            height: 50px;
            flex-shrink: 0;
        }
        .tip-box {
            background-color: #fff8e1;
            border-left: 5px solid #ffc107;
            border-radius: 8px;
            padding: 25px;
            margin-bottom: 40px;
        }
        .tip-title {
            font-size: 22px;
            font-weight: 700;
            color: #f57c00;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .tip-content {
            font-size: 18px;
            color: #5d4037;
            line-height: 1.7;
        }
        </style>
        """, unsafe_allow_html=True)

        # 팁 박스
        st.markdown("""
        <div class="tip-box">
            <div class="tip-title">
                <img src="https://cdn-icons-png.flaticon.com/128/5013/5013521.png" width="48px">
                도움말
            </div>
            <div class="tip-content">
                • 글씨가 작으면 브라우저의 확대 기능을 이용하세요<br>
                • 큰 글씨와 간단한 버튼으로 구성되어 있으니 천천히 하나씩 눌러보세요<br>
                • 궁금한 점이 있으면 언제든지 주변 가족이나 담당자에게 문의하세요
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 1단계
        st.markdown("""
        <div class="step-container">
            <div class="step-box">
                <div class="step-number">1</div>
                <img class="step-icon" src="https://cdn-icons-png.flaticon.com/128/11817/11817745.png">
                <div class="step-content">
                    <div class="step-title">왼쪽 메뉴에서 '사용자 위치 입력' 선택</div>
                    <div class="step-desc">화면 왼쪽에 있는 메뉴에서 '사용자 위치 입력' 버튼을 눌러주세요.</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 2단계
        st.markdown("""
        <div class="step-container">
            <div class="step-box">
                <div class="step-number">2</div>
                <img class="step-icon" src="https://cdn-icons-png.flaticon.com/128/3434/3434958.png">
                <div class="step-content">
                    <div class="step-title">주소 입력하기</div>
                    <div class="step-desc">본인의 위치 또는 확인하고 싶은 주소를 입력해주세요.</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 3단계
        st.markdown("""
        <div class="step-container">
            <div class="step-box">
                <div class="step-number">3</div>
                <img class="step-icon" src="https://cdn-icons-png.flaticon.com/128/854/854878.png">
                <div class="step-content">
                    <div class="step-title">지도에서 시설 확인</div>
                    <div class="step-desc">지도에 나타난 추천 시설을 확인하세요. 오른쪽 목록에서 시설을 선택하면 상세 위치가 표시됩니다.</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 4단계
        st.markdown("""
        <div class="step-container">
            <div class="step-box">
                <div class="step-number">4</div>
                <img class="step-icon" src="https://cdn-icons-png.flaticon.com/128/1523/1523481.png">
                <div class="step-content">
                    <div class="step-title">버스 정보 확인</div>
                    <div class="step-desc">'정류장'을 선택하면 근처 버스 정류장과 노선을 확인할 수 있습니다.</div>
                </div>
            </div>
        </div>
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
    """)



    
