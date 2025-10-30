import streamlit as st
from google import genai
import pandas as pd

# 데이터 파일 불러오기
health_institutions = pd.read_csv('./data/인천광역시_건강검진기관.csv', encoding='cp949',sep='\t')
health_check_data = pd.read_csv('./data/국민건강보험공단_건강검진정보_2024.csv', encoding="cp949")

def main():
    st.title("🏥 인천 노인을 위한 도우미 챗봇")
    st.write("고령층을 위한 건강검진·관리·복지 안내 챗봇입니다.")

    # Gemini 클라이언트 초기화
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    
    # 세션 상태에서 채팅 기록 초기화
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "user_address" not in st.session_state:
        st.session_state.user_address = ""
    if "user_age" not in st.session_state:
        st.session_state.user_age = 50  # 초기값을 50으로 설정
    if "user_gender" not in st.session_state:
        st.session_state.user_gender = "남성"

    # 저장된 채팅 기록 화면에 표시
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 사용자 입력 필드
    user_input = st.chat_input("질문을 입력하세요...")

    # 주소, 나이, 성별 입력 필드
    st.session_state.user_address = st.text_input("주소를 입력하세요 (예: 인천광역시 서구 서곶로(도로명주소)):", value=st.session_state.user_address)
    st.session_state.user_age = st.number_input("나이를 입력하세요", min_value=50, max_value=120, value=st.session_state.user_age)
    st.session_state.user_gender = st.selectbox("성별을 선택하세요", ["남성", "여성"], index=0 if st.session_state.user_gender == "남성" else 1)

    # 고정된 검진기관 안내 예시 질문
    with st.expander("검진기관 안내 질문 보기", expanded=True):
        st.markdown("아래의 질문을 클릭하면 관련 정보를 입력할 수 있습니다.")
        st.markdown("1. 가까운 검진 기관은 어디인가요?")
        st.markdown("2. 검진을 받기 위해 필요한 서류는 무엇인가요?")
        st.markdown("3. 검진 후 결과는 언제 알 수 있나요?")
    
    # 검진기관 안내 로직
    if st.session_state.user_address:
        nearby_institutions = health_institutions[health_institutions['주소'].str.contains(st.session_state.user_address)]
        if nearby_institutions.empty:
            st.chat_message("assistant").markdown("해당 주소에 가까운 검진 기관이 없습니다.")
        else:
            st.chat_message("assistant").markdown("가까운 검진 기관 목록입니다:")
            for index, row in nearby_institutions.iterrows():
                services = []
                if row['위암'] == 'O':
                    services.append("위암 검진")
                if row['간암'] == 'O':
                    services.append("간암 검진")
                if row['대장암'] == 'O':
                    services.append("대장암 검진")
                if st.session_state.user_gender == "여성":
                    if row['유방암'] == 'O':
                        services.append("유방암 검진")
                    if row['자궁경부암'] == 'O':
                        services.append("자궁경부암 검진")
                if row['구강검진'] == 'O':
                    services.append("구강검진")
                service_str = ', '.join(services) if services else "병원으로 문의하세요"
                st.chat_message("assistant").markdown(f"- {row['검진기관명']} | 주소: {row['주소']} | 전화: {row['전화번호']} | 제공 검진: {service_str}")

    # 건강관리 팁 예시 질문
    with st.expander("건강관리 팁 질문 보기", expanded=True):
        st.chat_message("assistant").markdown("다음은 건강 관리 팁을 제공하기 위한 정보 입력입니다.")
    
    # 사용자 입력에 따른 응답 처리
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # Gemini API에서 응답 받기
        with st.chat_message("assistant"):
            with st.spinner("생각 중..."):
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[f"어르신들 대상의 서비스니까 친절하고 살갑게 대답해주지만 어르신이라는 존칭은 빼줘. "
                              f"그리고 대답은 알기 쉬운 용어를 써서 말해줘. "
                              f"유저 질문이 노인 복지 관련 내용이 아니면 노인 복지 내용만 질문 하도록 해줘. "
                              f"질문: {user_input}"]
                )
                assistant_message = response.text
                st.markdown(assistant_message)
                st.session_state.messages.append({"role": "assistant", "content": assistant_message})

if __name__ == "__main__":
    main()