import streamlit as st
from google import genai
import pandas as pd

# 데이터 파일 불러오기
health_institutions = pd.read_csv('./data/인천광역시_건강검진기관.csv', encoding='utf-8')
health_check_data = pd.read_csv('./data/국민건강보험공단_건강검진정보_2024.csv', encoding="cp949")

def main():
    st.title("🏥 인천 노인 건강 도우미 챗봇")
    st.write("고령층을 위한 건강검진·관리 안내 챗봇입니다.")

    # Gemini 클라이언트 초기화
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

    # 세션 상태에서 채팅 기록 초기화
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "user_address" not in st.session_state:
        st.session_state.user_address = ""
    if "user_age" not in st.session_state:
        st.session_state.user_age = 0
    if "user_gender" not in st.session_state:
        st.session_state.user_gender = "남성"
    
    # 저장된 채팅 기록 화면에 표시
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 사용자 입력 필드
    user_input = st.chat_input("질문을 입력하세요...")

    # 예시 질문 버튼 표시
    st.write("아래의 버튼을 클릭하여 질문을 선택하세요:")
    col1, col2, col3 = st.columns(3)

    # 주소, 나이, 성별 입력 필드
    st.session_state.user_address = st.text_input("주소를 입력하세요 (예: 인천광역시 서구 서곶로 284):", value=st.session_state.user_address)

    # 10단위 나이 선택
    age_options = [i for i in range(40, 121, 10)]
    # 인덱스가 범위를 벗어나는 경우 0으로 초기화
    age_index = min(st.session_state.user_age // 10, len(age_options) - 1)
    st.session_state.user_age = st.selectbox("나이대를 선택하세요", options=age_options, index=age_index)

    st.session_state.user_gender = st.selectbox("성별을 선택하세요", ["남성", "여성"], index=0 if st.session_state.user_gender == "남성" else 1)

    with col1:
        if st.button("검진기관 안내", key="guidance"):
            user_address = st.session_state.user_address
            user_age = st.session_state.user_age
            user_gender = st.session_state.user_gender

            if user_address:
                nearby_institutions = health_institutions[health_institutions['주소'].str.contains(user_address)]
                if nearby_institutions.empty:
                    response_message = "해당 주소에 가까운 검진 기관이 없습니다."
                else:
                    response_message = "가까운 검진 기관 목록입니다:"
                    for index, row in nearby_institutions.iterrows():
                        services = []
                        if row['위암'] == 'O':
                            services.append("위암 검진")
                        if row['간암'] == 'O':
                            services.append("간암 검진")
                        if row['대장암'] == 'O':
                            services.append("대장암 검진")
                        if row['유방암'] == 'O':
                            services.append("유방암 검진")
                        if row['자궁경부암'] == 'O':
                            services.append("자궁경부암 검진")
                        if row['폐암'] == 'O':
                            services.append("폐암 검진")
                        if row['구강검진'] == 'O':
                            services.append("구강검진")
                        
                        service_str = ', '.join(services) if services else "검진을 실시하지 않습니다."
                        response_message += f"\n- {row['검진기관명']} | 전화: {row['전화번호']} | 제공 검진: {service_str}"

                # 나이와 성별에 따른 검진 주기 안내
                recommended_tests = []
                if user_age >= 65:
                    recommended_tests.append("매년 건강 검진")
                if user_gender == "여성":
                    if user_age >= 40:
                        recommended_tests.append("유방암 검진 (2년마다)")
                    if user_age >= 20:
                        recommended_tests.append("자궁경부암 검진 (3년마다)")
                if user_gender == "남성":
                    if user_age >= 50:
                        recommended_tests.append("대장암 검진 (5년마다)")

                # 검진 주기 안내
                if recommended_tests:
                    response_message += "\n추천 검진 목록 및 주기:"
                    for test in recommended_tests:
                        response_message += f"\n- {test}"

                st.chat_message("assistant").markdown(response_message)

    with col2:
        if st.button("건강관리 팁", key="tips"):
            st.chat_message("assistant").markdown("다음은 건강 관리 팁을 제공하기 위한 정보 입력입니다.")
            # 건강 관리 정보 입력 받기
            height = st.number_input("신장 (cm)", min_value=100, max_value=250, step=1)
            weight = st.number_input("체중 (kg)", min_value=30, max_value=200, step=1)
            waist = st.number_input("허리둘레 (cm)", min_value=50, max_value=150, step=1)
            systolic_bp = st.number_input("수축기 혈압", min_value=50, max_value=200, step=1)
            diastolic_bp = st.number_input("이완기 혈압", min_value=30, max_value=130, step=1)
            fasting_blood_sugar = st.number_input("식전혈당 (mg/dL)", min_value=50, max_value=300, step=1)
            if st.button("팁 요청"):
                st.chat_message("assistant").markdown("입력하신 정보를 기반으로 건강 관리 팁을 제공합니다.")
                st.chat_message("assistant").markdown("정확한 건강 관리를 위해서는 병원을 방문하여 의사에게 상담 받으시기 바랍니다.")

    with col3:
        if st.button("검진 준비방법", key="preparation"):
            st.chat_message("assistant").markdown("다음은 검진에 대한 대표 질문 예시입니다:")
            st.markdown("1. 검진을 받기 전에 어떤 준비가 필요한가요?")
            st.markdown("2. 검진 후에 결과는 언제 알 수 있나요?")
            st.markdown("3. 검진을 받는 과정은 어떻게 진행되나요?")

    # 사용자가 입력했을 때 실행
    if user_input:
        # 사용자 메시지를 채팅 기록에 추가
        st.session_state.messages.append({"role": "user", "content": user_input})
        # 사용자 메시지를 화면에 표시
        with st.chat_message("user"):
            st.markdown(user_input)
        # Gemini API에서 응답 받기
        with st.chat_message("assistant"):
            with st.spinner("생각 중..."):
                # 사용자 질문에 대한 응답 요청
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[f"어르신들 대상의 서비스니까 친절하고 살갑게 대답해줘, "
                              f"그리고 대답은 알기 쉬운 용어를 써서 말해줘. "
                              f"유저 질문이 노인 복지 관련 내용이 아니면 노인 복지 내용만 질문 하도록 해줘. "
                              f"질문: {user_input}"]
                )
                assistant_message = response.text
                st.markdown(assistant_message)
                # AI 응답을 채팅 기록에 추가
                st.session_state.messages.append({"role": "assistant", "content": assistant_message})

if __name__ == "__main__":
    main()