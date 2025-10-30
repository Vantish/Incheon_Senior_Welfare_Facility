import streamlit as st
import google.generativeai as genai
import pandas as pd

# 데이터 파일 불러오기
health_institutions = pd.read_csv('./data/인천광역시_건강검진기관.csv', encoding='cp949', sep='\t')
health_check_data = pd.read_csv('./data/국민건강보험공단_건강검진정보_2024.csv', encoding="cp949")

def calculate_bmi(weight, height):
    """BMI를 계산해서 소수점 둘째 자리까지 알려드리는 함수입니다."""
    height_m = height / 100
    bmi = weight / (height_m ** 2)
    return round(bmi, 2)

def get_bmi_category(bmi):
    """BMI를 바탕으로 건강 상태를 알려드립니다."""
    if bmi < 18.5:
        return "저체중"
    elif 18.5 <= bmi < 23:
        return "정상"
    elif 23 <= bmi < 25:
        return "과체중"
    elif 25 <= bmi < 30:
        return "비만"
    else:
        return "고도비만"

def get_health_tip(bmi, bp_sys, bp_dia, fbs, waist, gender):
    """건강 정보를 바탕으로 맞춤형 건강 팁을 따뜻하게 드립니다."""
    tips = []
    bmi_category = get_bmi_category(bmi)
    if bmi_category == "저체중":
        tips.append("체중이 조금 적으신 편이에요. 영양이 풍부한 음식을 골고루 드시고, 단백질이 많은 두부나 닭가슴살 같은 음식을 챙겨 드시면 건강에 좋아요.")
    elif bmi_category in ["비만", "고도비만"]:
        tips.append("체중을 조금 관리하시면 더 건강해지실 거예요. 채소 위주의 식사를 하시고, 산책처럼 가벼운 운동을 시작해 보시는 건 어떨까요? 천천히 하셔도 충분해요!")
    else:
        tips.append("지금 체중은 건강한 상태예요! 꾸준히 밥을 잘 챙겨 드시고, 가끔 몸을 움직이시면 좋아요.")
    if bp_sys >= 140 or bp_dia >= 90:
        tips.append("혈압이 조금 높으신 편이에요. 짠 음식을 조금 줄이시고, 마음을 편안히 가지시면 좋아요. 가벼운 산책도 혈압 관리에 큰 도움이 됩니다.")
    else:
        tips.append("혈압이 건강한 상태예요! 지금처럼 규칙적인 생활을 유지하시면 더 건강해지실 거예요.")
    if fbs >= 126:
        tips.append("식전혈당이 조금 높으신 것 같아요. 병원에서 정기적으로 검진받으시고, 단 음식이나 흰 쌀밥을 조금 줄여보시면 좋아요. 걱정 마세요, 조금씩 바꾸시면 됩니다!")
    elif 100 <= fbs < 126:
        tips.append("혈당이 약간 높은 편이에요. 매일 10분 정도 걷기 운동을 하시고, 채소 위주의 식사를 해보시면 좋아질 거예요.")
    else:
        tips.append("혈당이 건강한 상태예요! 지금처럼 꾸준히 관리하시면 걱정 없으실 거예요.")
    if (gender == "남성" and waist >= 90) or (gender == "여성" and waist >= 85):
        tips.append("허리둘레가 조금 넓으신 편이에요. 가벼운 유산소 운동이나 복부 운동을 해보시면 건강에 좋아요. 천천히 시작하셔도 괜찮아요!")
    else:
        tips.append("허리둘레가 건강한 범위예요! 꾸준히 운동하시면서 지금 상태를 유지해 보세요.")
    final_tip = "건강은 하루아침에 바뀌는 게 아니에요. 작은 습관부터 천천히 바꿔가시면서, 꾸준히 건강을 챙기시면 분명 더 건강해지실 거예요. 항상 응원합니다!"
    tips.append(final_tip)
    return "\n\n".join(tips)

def run_chatbot_hhr():
    st.title("🏥 인천 노인을 위한 도우미 챗봇")
    st.write("건강검진과 복지 정보를 따뜻하게 안내드리는 챗봇입니다. 궁금하신 점을 편하게 물어보세요!")

    # Gemini 클라이언트 초기화
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    except KeyError:
        st.error("Gemini API 키가 설정되지 않았어요. secrets.toml 파일을 확인하거나 관리자에게 문의해 주세요.")
        return

    # 세션 상태 초기화
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "user_address" not in st.session_state:
        st.session_state.user_address = ""
    if "user_age" not in st.session_state:
        st.session_state.user_age = 50
    if "user_gender" not in st.session_state:
        st.session_state.user_gender = "남성"
    if "bmi" not in st.session_state:
        st.session_state.bmi = 0
    if "bp_sys" not in st.session_state:
        st.session_state.bp_sys = 120
    if "bp_dia" not in st.session_state:
        st.session_state.bp_dia = 80
    if "fbs" not in st.session_state:
        st.session_state.fbs = 90
    if "waist" not in st.session_state:
        st.session_state.waist = 80
    if "search_triggered" not in st.session_state:
        st.session_state.search_triggered = False

    # 저장된 채팅 기록 표시
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 사용자 입력 필드 (챗봇용)
    user_input = st.chat_input("궁금하신 점을 말씀해 주세요...")

    # 검진기관 안내
    with st.expander("검진기관 안내", expanded=False):
        st.markdown("궁금하신 검진기관 정보를 확인하려면 주소를 입력하고 검색 버튼을 눌러 주세요.")
        col1, col2 = st.columns([4, 1])
        with col1:
            st.session_state.user_address = st.text_input("주소를 입력해 주세요 (예: 인천광역시 서구 서곶로):", value=st.session_state.user_address, key="address_input")
        with col2:
            if st.button("🔍 내 근처 검진기관 찾기"):
                st.session_state.search_triggered = True
        st.session_state.user_age = st.number_input("나이를 입력해 주세요", min_value=50, max_value=120, value=st.session_state.user_age, key="age_input_institution")
        st.session_state.user_gender = st.selectbox("성별을 선택해 주세요", ["남성", "여성"], index=0 if st.session_state.user_gender == "남성" else 1, key="gender_input_institution")
        
        if st.session_state.search_triggered and st.session_state.user_address:
            nearby_institutions = health_institutions[health_institutions['주소'].str.contains(st.session_state.user_address, na=False)]
            if st.session_state.user_gender == "남성":
                nearby_institutions = nearby_institutions[~nearby_institutions['검진기관명'].str.contains("산부인과", na=False)]
            if nearby_institutions.empty:
                st.markdown("입력하신 주소 근처에 적합한 검진 기관이 없어요. 다른 주소를 입력해 보시거나, 더 넓은 지역으로 검색해 드릴까요?")
            else:
                st.markdown("**근처 검진 기관 목록입니다**")
                for index, row in nearby_institutions.iterrows():
                    services = []
                    if row['위암'] == 'O':
                        services.append("위암 검진")
                    if row['간암'] == 'O':
                        services.append("간암 검진")
                    if row['대장암'] == 'O':
                        services.append("대장암 검진")
                    if row['구강검진'] == 'O':
                        services.append("구강검진")
                    if st.session_state.user_gender == "여성":
                        if row['유방암'] == 'O':
                            services.append("유방암 검진")
                        if row['자궁경부암'] == 'O':
                            services.append("자궁경부암 검진")
                    service_str = ', '.join(services) if services else "일반검진"
                    st.markdown(f"- {row['검진기관명']} | 주소: {row['주소']} | 전화: {row['전화번호']} | 제공 검진: {service_str}")
        elif st.session_state.search_triggered and not st.session_state.user_address:
            st.markdown("주소를 입력해 주시면 근처 검진 기관을 찾아드릴게요!")

    # 건강관리 팁
    with st.expander("건강관리 팁", expanded=False):
        st.markdown("건강 정보를 입력하시면 맞춤형 건강 팁을 드릴게요!")
        weight = st.number_input("체중(kg)을 입력해 주세요", min_value=30.0, max_value=200.0, value=70.0, key="weight_input")
        height = st.number_input("키(cm)를 입력해 주세요", min_value=100.0, max_value=250.0, value=170.0, key="height_input")
        bp_sys = st.number_input("수축기 혈압(mmHg)을 입력해 주세요", min_value=50, max_value=250, value=st.session_state.bp_sys, key="bp_sys_input")
        bp_dia = st.number_input("이완기 혈압(mmHg)을 입력해 주세요", min_value=30, max_value=150, value=st.session_state.bp_dia, key="bp_dia_input")
        fbs = st.number_input("식전혈당(mg/dL)을 입력해 주세요", min_value=50, max_value=400, value=st.session_state.fbs, key="fbs_input")
        waist = st.number_input("허리둘레(cm)를 입력해 주세요", min_value=50, max_value=150, value=st.session_state.waist, key="waist_input")
        gender = st.selectbox("성별을 선택해 주세요", ["남성", "여성"], index=0 if st.session_state.user_gender == "남성" else 1, key="gender_input_health")
        if weight and height:
            bmi = calculate_bmi(weight, height)
            st.markdown(f"**BMI**: {bmi} ({get_bmi_category(bmi)})")
            health_tip = get_health_tip(bmi, bp_sys, bp_dia, fbs, waist, gender)
            st.markdown("**맞춤 건강 팁**")
            st.markdown(health_tip)

    # 검진준비 안내
    with st.expander("검진준비 안내", expanded=False):
        st.markdown("검진 준비에 대해 궁금하신 점을 아래에서 확인해 보세요.")
        st.markdown("- 건강검진 전 금식은 어떻게 해야 하나요?")
        st.markdown("- 검진 당일 어떤 옷을 입는 게 좋나요?")
        st.markdown("- 약을 복용 중인데 검진 전 어떻게 해야 하나요?")
        st.markdown("- 검진을 받기 위해 필요한 서류는 무엇인가요?")
        st.markdown("- 검진 후 결과는 언제 알 수 있나요?")

    # 복지 프로그램 안내 (Gemini 연결)
    with st.expander("복지 프로그램 안내", expanded=False):
        st.markdown("복지 관련 궁금한 점을 아래 항목별로 선택해서 물어보세요 😊")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "💰 지원금 및 혜택", 
        "🏠 복지시설 및 서비스", 
        "🧓 돌봄·요양", 
        "🎨 여가·문화활동", 
        "📞 긴급지원·상담"
    ])

    # 각 탭마다 질문 입력창과 Gemini 호출 기능 연결
    with tab1:
        st.subheader("💰 지원금 및 혜택")
        welfare_q1 = st.text_input("지원금 관련 질문을 입력해 주세요", key="welfare_benefit")
        if welfare_q1:
            with st.spinner("복지 정보를 불러오는 중입니다..."):
                model = genai.GenerativeModel("gemini-1.5-flash-latest")
                prompt = f"""
                당신은 인천시 노인복지 도우미 챗봇입니다.
                노인에게 지급되는 각종 복지 지원금, 연금, 감면제도에 대해 
                친절하고 따뜻한 존댓말로 알기 쉽게 설명해 주세요.
                질문: {welfare_q1}
                """
                answer = model.generate_content(prompt)
                st.markdown(answer.text)

    with tab2:
        st.subheader("🏠 복지시설 및 서비스")
        welfare_q2 = st.text_input("시설이나 복지서비스에 대해 궁금한 점을 입력해 주세요", key="welfare_service")
        if welfare_q2:
            with st.spinner("복지시설 정보를 찾는 중입니다..."):
                model = genai.GenerativeModel("gemini-1.5-flash-latest")
                prompt = f"""
                당신은 인천시 노인복지 안내 챗봇입니다.
                복지관, 경로당, 요양원, 재가복지센터 등 노인시설과 복지서비스 정보를 설명해 주세요.
                질문: {welfare_q2}
                """
                answer = model.generate_content(prompt)
                st.markdown(answer.text)

    with tab3:
        st.subheader("🧓 돌봄·요양")
        welfare_q3 = st.text_input("돌봄서비스나 요양 관련 질문을 입력해 주세요", key="welfare_care")
        if welfare_q3:
            with st.spinner("돌봄 서비스 정보를 불러오는 중입니다..."):
                model = genai.GenerativeModel("gemini-1.5-flash-latest")
                prompt = f"""
                당신은 인천시 노인 돌봄 도우미 챗봇입니다.
                방문요양, 노인맞춤돌봄서비스, 요양보호사 지원제도 등에 대해
                따뜻하고 공손하게 설명해 주세요.
                질문: {welfare_q3}
                """
                answer = model.generate_content(prompt)
                st.markdown(answer.text)

    with tab4:
        st.subheader("🎨 여가·문화활동")
        welfare_q4 = st.text_input("여가·취미·문화활동 관련 질문을 입력해 주세요", key="welfare_culture")
        if welfare_q4:
            with st.spinner("여가 프로그램 정보를 불러오는 중입니다..."):
                model = genai.GenerativeModel("gemini-1.5-flash-latest")
                prompt = f"""
                당신은 노인 여가복지 도우미 챗봇입니다.
                복지관 프로그램, 문화강좌, 건강체조, 취미활동 등을 안내해 주세요.
                질문: {welfare_q4}
                """
                answer = model.generate_content(prompt)
                st.markdown(answer.text)

    with tab5:
        st.subheader("📞 긴급지원·상담")
        welfare_q5 = st.text_input("긴급지원이나 상담 관련 질문을 입력해 주세요", key="welfare_emergency")
        if welfare_q5:
            with st.spinner("관련 정보를 불러오는 중입니다..."):
                model = genai.GenerativeModel("gemini-1.5-flash-latest")
                prompt = f"""
                당신은 인천시 노인 복지 상담 도우미입니다.
                긴급생계지원, 상담센터, 노인학대 신고, 위기상담 등 도움받을 수 있는 방법을 안내해 주세요.
                질문: {welfare_q5}
                """
                answer = model.generate_content(prompt)
                st.markdown(answer.text)

    # 사용자 입력 처리 (챗봇)
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
        
        with st.chat_message("assistant"):
            with st.spinner("잠시만 기다려 주세요..."):
                try:
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    prompt = f"""
                    노인분들께 서비스를 드리는 챗봇이니 친절하고 따뜻하게, 존댓말로 답변하되 사용자를 지칭하는 말은 빼주세요.
                    쉬운 용어를 사용해서 알기 쉽게 설명해 주세요.
                    질문이 건강검진이나 인천광역시 노인 복지와 관련된 내용이면 정확한 정보를 바탕으로 답변해 주세요.
                    질문이 건강검진이나 복지와 무관하면 건강검진 및 복지 관련 질문만 답하도록 안내해 주세요.
                    질문: {user_input}
                    """
                    response = model.generate_content(prompt)
                    assistant_message = response.text
                    st.markdown(assistant_message)
                    st.session_state.messages.append({"role": "assistant", "content": assistant_message})
                except Exception as e:
                    st.error(f"챗봇 응답 생성 중 오류가 발생했어요: {str(e)}. 다시 시도해 주세요!")

if __name__ == "__main__":
    run_chatbot_hhr()