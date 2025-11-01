# 다른코드는 절대 건들지말고 너가 건드릴수잇는건 pdf, 노인일자리, 지원금및혜택, 여가문화활동, 긴급지원 코드만 건드릴수있어 다른 코드 건들지마

import streamlit as st
import google.generativeai as genai
import pandas as pd
import PyPDF2
import re
import os
from pypdf import PdfReader

# 데이터 파일 불러오기
health_institutions = pd.read_csv('./data/인천광역시_건강검진기관.csv', encoding='cp949', sep='\t')
health_check_data = pd.read_csv('./data/국민건강보험공단_건강검진정보_2024.csv', encoding="cp949")

def calculate_bmi(weight, height):
    height_m = height / 100
    bmi = weight / (height_m ** 2)
    return round(bmi, 2)

def get_bmi_category(bmi):
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
    tips = []
    bmi_category = get_bmi_category(bmi)
    if bmi_category == "저체중":
        tips.append("체중이 조금 적으신 편이에요. 영양이 풍부한 음식을 골고루 드시고, 단백질이 많은 두부나 닭가슴살 같은 음식을 챙겨 드시면 건강에 좋아요.")
    elif bmi_category == "과체중":
        tips.append("조금만 더 가벼워지면 몸이 훨씬 편해질 거예요. 밥 먹을 때 채소를 먼저 드시고, 걷기부터 시작해 보세요.")
    elif bmi_category in ["비만", "고도비만"]:
        tips.append("체중을 조금씩 줄이면 병원 갈 일도 줄어들어요. 밥 먹기 전 물 한 잔, 식사 후 10분 산책, 이 두 가지만 해보세요.")
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

# --- RAG(CHROMA) 통합: app_testchatbot의 캐시된 벡터스토어/체인을 사용 ---
# app_testchatbot.py에 정의된 load_vectorstore, make_rag_chain를 재사용합니다.
from app_testchatbot import load_vectorstore, make_rag_chain


# RAG 체인에 질문을 보내고 답변을 받아오는 간단한 헬퍼
def ask_rag(question):
    try:
        # 캐시된 리소스에서 불러오기 (app_testchatbot에서 @st.cache_resource 적용되어 있음)
        vectordb = load_vectorstore()
        chain = make_rag_chain(vectordb)
        result = chain.invoke({"question": question})
        # chain.invoke는 보통 문자열을 반환
        return result
    except Exception as e:
        # 호출 실패 시 None 반환 (상위 코드에서 Gemini로 폴백 가능)
        print(f"ask_rag error: {e}")
        return None


# 질문을 문서 내용에 맞춰 재매핑한 뒤 다시 RAG로 시도하는 헬퍼
def ask_with_fallback(topic_query, user_display_question=None):
    """주제(또는 키워드)로 RAG에 질의하고, 결과가 없으면 보유한 문서 주제에 맞춰
    질의를 재구성해 다시 시도합니다. 최종 실패 시 Gemini로 폴백합니다.

    - topic_query: RAG에 직접 보낼 기본 쿼리(문서 키워드)
    - user_display_question: 사용자가 보는 질문 문구(로그/폴백용)
    반환: 문자열(답변)
    """
    # If a list of candidates is provided, try them in order first
    if isinstance(topic_query, (list, tuple)):
        for candidate in topic_query:
            if not candidate:
                continue
            res = ask_rag(candidate)
            if res:
                # debug log
                try:
                    if "debug_logs" not in st.session_state:
                        st.session_state["debug_logs"] = []
                    st.session_state["debug_logs"].append({"method": "candidate", "candidate": candidate})
                except Exception:
                    pass
                print(f"ask_with_fallback: candidate succeeded: {candidate}")
                return res
        # fall through to using the first candidate as primary for mappings
        primary = topic_query[0] if topic_query else ""
    else:
        # 1) 먼저 직접 시도
        res = ask_rag(topic_query)
        if res:
            return res
        primary = topic_query

    # 2) 문서에 존재할 가능성이 높은 토픽으로 재매핑 (간단한 키워드 맵)
    fallback_map = {
        # 정책/재정 관련 문서 키워드
        "건강보험료 지원 - 저소득 노인": "국고보조금 정산",
        "의료비 지원 - 대상 및 금액": "장기요양기관 운영 및 급여비용 부담",
        "노인일자리 및 사회활동 지원사업 - 지원금": "시설 운영비 지출",
        "노인일자리 및 사회활동 지원사업": "노인복지시설 기준",
        "노인일자리 참여 자격": "노인복지시설 기준",
        "공익형 일자리 신청 방법": "노인일자리 및 사회활동 지원사업",
        "방문요양서비스 신청 방법": "장기요양기관 운영 및 급여비용 부담",
        "장기요양보험 등급판정 방법": "장기요양기관 운영 및 급여비용 부담",
        "노인학대 신고 방법": "노인학대 예방 교육",
        "학대피해노인 전용쉼터 이용 방법": "학대피해노인 보호",
        "노인교실 프로그램 안내": "여가문화 활동 및 프로그램 운영",
        "경로당 운영 참여 방법": "여가문화 활동 및 프로그램 운영",
    }

    # 추가 매핑: UI에서 사용하는 q 문자열들을 PDF 내 존재하는 섹션/문구로 재매핑
    # (추출 스크립트 결과 기반 추천 매핑)
    fallback_map.update({
        # 노인일자리 관련
        "노인일자리 및 사회활동 지원사업 주요 유형 및 설명": "노인복지 일반현황",
        "노인일자리 참여 자격 및 신청 절차 안내": "노인복지 일반현황",
        "노인일자리 활동의 급여 및 수당 지급 방식 안내": "사업별 지원기준단가",

        # 지원금/혜택 관련
        "노인복지 수당 및 지원금의 종류와 지급 기준 안내": "지원 대상 및 범위",
        "저소득층 대상 의료비 및 지원 제도 운영 방식과 신청 기준 안내": "지원 대상 및 범위",
        "저소득 노인 대상 건강보험료 지원 프로그램의 주요 내용 및 신청 절차": "지원 대상 및 범위",

        # 돌봄·요양 관련
        "방문요양 서비스의 제공 범위 및 신청 방법(장기요양 관련) 안내": "장기요양기관 운영 및 급여비용 부담",
        "장기요양보험 등급 판정 절차 및 등급 기준 안내": "장기요양인정신청",

        # 여가·문화활동 관련
        "2025년 문화강좌 및 여가프로그램의 개요, 신청방법 및 일정 안내": "프로그램 운영",
        "경로당 프로그램 참여 방법 및 운영시간(운영 안내)": "프로그램 운영",

        # 긴급지원·상담 관련
        "노인학대 신고 절차 및 긴급보호 서비스 이용 방법 안내": "긴급복지의료지원",
        "학대피해 노인 보호(쉼터) 이용 자격 및 연락처 안내": "학대피해노인 보호",
    })

    # Try mapping based on primary candidate or the original string
    alt = fallback_map.get(primary)
    if alt:
        res2 = ask_rag(alt)
        if res2:
            try:
                if "debug_logs" not in st.session_state:
                    st.session_state["debug_logs"] = []
                st.session_state["debug_logs"].append({"method": "fallback_map", "candidate": alt})
            except Exception:
                pass
            print(f"ask_with_fallback: fallback_map succeeded: {alt}")
            # 문서 기반의 관련 주제로 재질의한 결과를 그대로 반환
            return res2

    # 3) 키워드 맵에 없으면 간단 키워드 추출(예: 중요한 명사로 재시도)
    try:
        # 아주 간단한 추출: 한국어 공백 분할 후 명사처럼 보이는 단어 우선 사용
        parts = topic_query.split()
        for p in parts:
            if len(p) >= 2:
                res3 = ask_rag(p)
                if res3:
                    try:
                        if "debug_logs" not in st.session_state:
                            st.session_state["debug_logs"] = []
                        st.session_state["debug_logs"].append({"method": "keyword", "candidate": p})
                    except Exception:
                        pass
                    print(f"ask_with_fallback: keyword succeeded: {p}")
                    return res3
    except Exception:
        pass

    # 4) 최후 폴백: Gemini에게 원래(또는 표시용) 질문으로 물어본다
    if user_display_question:
        return gemini_answer(user_display_question)
    return gemini_answer(topic_query)
    
# --- Gemini 폴백 함수 ---
def gemini_answer(question):
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""
        노인분들께 서비스하는 챗봇이니, 따뜻하고 친절한 존댓말로 답변해 주세요.
        사용자를 지칭하는 말은 빼고, 쉬운 말로 설명해 주세요.
        질문: {question}
        """
        response = model.generate_content(prompt)
        return response.text
    except:
        return "죄송해요, 지금은 답변을 드릴 수 없어요. 조금 뒤에 다시 시도해 주세요."


# 버튼 클릭 시 사용자 표시 라벨은 채팅에 남기고, 내부적으로는 mapped_q를 RAG/Gemini에 요청하는 헬퍼
def post_user_and_respond(user_label, mapped_q, use_gemini=False):
    # 사용자에게 보이는 질문 라벨을 채팅에 남깁니다.
    st.session_state.messages.append({"role": "user", "content": user_label})
    try:
        with st.spinner("잠시만 기다려 주세요..."):
            ans = None
            success_step = None
            success_candidate = None
            if not use_gemini:
                # 1) 우선 사용자가 본래 입력한 질문(라벨)으로 바로 벡터검색 시도
                try:
                    ans = ask_rag(user_label)
                    if ans:
                        success_step = "user_label"
                        success_candidate = user_label
                except Exception:
                    ans = None

                # Prepare candidates: allow mapped_q to be a string or list
                if isinstance(mapped_q, (list, tuple)):
                    candidates = [c for c in mapped_q if c]
                elif mapped_q:
                    candidates = [mapped_q]
                else:
                    candidates = []

                # 2) 결합 쿼리: 문서 키 + 원문 질문 (검색 성능 향상을 위해) -> try each candidate
                if not ans and candidates:
                    for c in candidates:
                        try:
                            combined = f"{c} {user_label}"
                            ans = ask_rag(combined)
                            if ans:
                                success_step = "combined"
                                success_candidate = c
                                break
                        except Exception:
                            ans = None

                # 3) 그 다음 문서-친화적 키로 검색 (각 후보 순차)
                if not ans and candidates:
                    for c in candidates:
                        try:
                            ans = ask_rag(c)
                            if ans:
                                success_step = "candidate"
                                success_candidate = c
                                break
                        except Exception:
                            ans = None

                # 4) 그래도 없으면 기존의 폴백 로직(ask_with_fallback)을 사용 (ask_with_fallback는 리스트 대응됨)
                if not ans:
                    # ask_with_fallback will also log internally; record that we reached fallback
                    try:
                        if "debug_logs" not in st.session_state:
                            st.session_state["debug_logs"] = []
                        st.session_state["debug_logs"].append({"method": "pre_ask_with_fallback", "candidates": candidates or [user_label]})
                    except Exception:
                        pass
                    ans = ask_with_fallback(candidates or user_label, user_label)
                    success_step = success_step or "ask_with_fallback"
                    success_candidate = success_candidate or (candidates[0] if candidates else user_label)
            else:
                # Gemini 직접 호출: 사용자 질문을 그대로 보냄
                ans = gemini_answer(user_label)
                success_step = "gemini"
                success_candidate = user_label
        # record debug trace for this request
        try:
            if "debug_logs" not in st.session_state:
                st.session_state["debug_logs"] = []
            st.session_state["debug_logs"].append({"user_label": user_label, "success_step": success_step, "success_candidate": success_candidate})
        except Exception:
            pass
        print(f"post_user_and_respond: user_label={user_label} success_step={success_step} success_candidate={success_candidate}")
        st.session_state.messages.append({"role": "assistant", "content": ans})
    except Exception as e:
        st.session_state.messages.append({"role": "assistant", "content": "죄송해요, 답변 생성 중 오류가 발생했습니다."})

# --- 메인 함수 ---
def run_chatbot_hhr():
    st.title("👵🧓 인천 노인을 위한 도우미 챗봇")
    st.write("🔔건강검진과 복지 정보를 안내드리는 챗봇입니다. 궁금하신 점을 편하게 물어보세요!")

    # Gemini 초기화
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    except KeyError:
        st.error("Gemini API 키가 설정되지 않았어요. secrets.toml 파일을 확인하거나 관리자에게 문의해 주세요.")
        return
    
    # (PDF 직접 로드 제거) RAG 체인은 버튼/입력 시 ask_rag()로 호출합니다.

    # 세션 상태 초기화
    if "messages" not in st.session_state:
        st.session_state.messages = []
    # 사용자가 입력창에 채우는 값의 실제 위젯 키는 'composer_input'입니다.
    # 버튼 핸들러와 폼이 같은 키를 공유하도록 초기화합니다.
    if "composer_input" not in st.session_state:
        st.session_state["composer_input"] = ""
    # 위젯 전용 세션 키는 직접 설정하지 않습니다. 대신 'composer_input'을 소스 오브 트루스으로 사용합니다.
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

    # --- 여기까지가 모든 선택지/설정 UI입니다. 채팅(대화창)을 먼저 표시합니다. ---
    # 채팅을 표시할 자리(플레이스홀더)를 먼저 만듭니다. 이 컨테이너는 예시 질문들 위에
    # 렌더링되며, 이후 예시 질문들이 나오고 마지막에 입력창이 위치합니다.
    chat_container = st.container()

    # --- 검진기관 안내 ---
    with st.expander("🏥 검진기관 안내", expanded=False):
        st.markdown("궁금하신 검진기관 정보를 확인하려면 주소를 입력하고 검색 버튼을 눌러 주세요.")
        col1, col2 = st.columns([4, 1])
        with col1:
            st.session_state.user_address = st.text_input("주소를 입력해 주세요 (예: 인천광역시 서구 서곶로):", value=st.session_state.user_address, key="address_input")
        with col2:
            if st.button("🔍내 근처 검진기관 찾기"):
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
                st.markdown("**🏥근처 검진 기관 목록입니다**")
                for index, row in nearby_institutions.iterrows():
                    services = []
                    if row['위암'] == 'O': services.append("위암 검진")
                    if row['간암'] == 'O': services.append("간암 검진")
                    if row['대장암'] == 'O': services.append("대장암 검진")
                    if row['구강검진'] == 'O': services.append("구강검진")
                    if st.session_state.user_gender == "여성":
                        if row['유방암'] == 'O': services.append("유방암 검진")
                        if row['자궁경부암'] == 'O': services.append("자궁경부암 검진")
                    service_str = ', '.join(services) if services else "일반검진"
                    st.markdown(f"- {row['검진기관명']} | 주소: {row['주소']} | 전화: {row['전화번호']} | 제공 검진: {service_str}")
        elif st.session_state.search_triggered and not st.session_state.user_address:
            st.markdown("🔍주소를 입력해 주시면 근처 검진 기관을 찾아드릴게요!")

    # --- 건강관리 정보 ---
    with st.expander("🌈건강관리 정보", expanded=False):
        st.markdown("건강 정보를 입력하시면 맞춤형 건강 정보를 드릴게요!")
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
            st.markdown("**맞춤 건강 정보**")
            st.markdown(health_tip)

       # --- 검진준비 안내 (Gemini 답변 + 한 줄씩 배치) ---
    with st.expander("📌검진준비 안내 질문", expanded=False):
        st.markdown("아래 질문 중 하나를 클릭하시면 자세히 알려드려요!")
        
        if st.button("건강검진 전 금식은 어떻게 해야 하나요?"): 
            q = "건강검진 전 금식 방법"
            st.session_state.messages.append({"role": "user", "content": q})
            with st.spinner("잠시만 기다려 주세요..."):
                a = gemini_answer(q)
            st.session_state.messages.append({"role": "assistant", "content": a})
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("검진 당일 어떤 옷을 입는 게 좋나요?"):
            q = "건강검진 당일 옷차림"
            st.session_state.messages.append({"role": "user", "content": q})
            with st.spinner("잠시만 기다려 주세요..."):
                a = gemini_answer(q)
            st.session_state.messages.append({"role": "assistant", "content": a})
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("약을 복용 중인데 검진 전 어떻게 해야 하나요?"):
            q = "건강검진 전 약 복용 방법"
            st.session_state.messages.append({"role": "user", "content": q})
            with st.spinner("잠시만 기다려 주세요..."):
                a = gemini_answer(q)
            st.session_state.messages.append({"role": "assistant", "content": a})
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("검진을 받기 위해 필요한 서류는 무엇인가요?"):
            q = "건강검진 필요 서류"
            st.session_state.messages.append({"role": "user", "content": q})
            with st.spinner("잠시만 기다려 주세요..."):
                a = gemini_answer(q)
            st.session_state.messages.append({"role": "assistant", "content": a})
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("검진 후 결과는 언제 알 수 있나요?"):
            q = "건강검진 결과 확인 시기"
            st.session_state.messages.append({"role": "user", "content": q})
            with st.spinner("잠시만 기다려 주세요..."):
                a = gemini_answer(q)
            st.session_state.messages.append({"role": "assistant", "content": a})

        # --- 노인일자리 안내 ---
    with st.expander("☀️노인일자리 안내 질문", expanded=False):
        st.markdown("아래를 클릭하시면 자세히 알려드려요!")
        label = "노인일자리 및 사회활동 지원사업: 주요 유형과 개요"
        if st.button(label):
            post_user_and_respond(label, ["노인복지 일반현황", "노인일자리 및 사회활동 지원사업"])
        st.markdown("<br>", unsafe_allow_html=True)
        label = "노인일자리 참여 자격 및 신청 절차 안내"
        if st.button(label):
            post_user_and_respond(label, ["노인복지 일반현황", "노인일자리 참여 자격"])
        st.markdown("<br>", unsafe_allow_html=True)
        label = "노인일자리 활동 급여·수당 지급 방식 안내"
        if st.button(label):
            post_user_and_respond(label, ["사업별 지원기준단가", "급여 지급 방식"])

    # --- 지원금 및 혜택 ---
    with st.expander("🌻지원금 및 혜택 안내 질문", expanded=False):
        label = "노인복지 수당·지원금 종류 및 지급기준 안내"
        if st.button(label):
            post_user_and_respond(label, ["지원 대상 및 범위", "지원 대상 및 범위 안내", "저소득 지원"])

        label = "저소득·의료비 지원 제도 운영 방식 및 신청 기준"
        if st.button(label):
            post_user_and_respond(label, ["지원 대상 및 범위", "의료비 지원", "저소득 지원"])
        st.markdown("<br>", unsafe_allow_html=True)
        
        label = "저소득 노인 건강보험료 지원 프로그램 안내"
        if st.button(label):
            post_user_and_respond(label, ["지원 대상 및 범위", "건강보험료 지원"])

    # --- 돌봄·요양 ---
    with st.expander("🕊️돌봄·요양 안내 질문", expanded=False):
        label = "방문요양 서비스 제공 범위 및 신청 방법 안내"
        if st.button(label):
            post_user_and_respond(label, ["장기요양기관 운영 및 급여비용 부담", "방문요양 서비스 제공 범위"])
        st.markdown("<br>", unsafe_allow_html=True)
        label = "장기요양보험 등급 판정 절차 및 등급 기준"
        if st.button(label):
            post_user_and_respond(label, ["장기요양인정신청", "장기요양보험 등급판정"])

    # --- 여가·문화활동 ---
    with st.expander("🧩여가·문화활동 안내 질문", expanded=False):
        label = "2025년 문화강좌·여가프로그램 개요 및 신청방법"
        if st.button(label):
            post_user_and_respond(label, ["프로그램 운영", "여가문화 활동 및 프로그램 운영"])
        st.markdown("<br>", unsafe_allow_html=True)
        
        label = "경로당 프로그램 참여 방법 및 운영시간 안내"
        if st.button(label):
            post_user_and_respond(label, ["프로그램 운영", "경로당 프로그램 운영"])

    # --- 긴급지원·상담 ---
    with st.expander("🆘 긴급지원·상담 안내 질문", expanded=False):
        label = "노인학대 신고 절차 및 긴급보호(응급지원) 서비스 안내"
        if st.button(label):
            post_user_and_respond(label, ["긴급복지의료지원", "긴급지원", "응급지원"])
        st.markdown("<br>", unsafe_allow_html=True)
        label = "학대피해 노인 쉼터 이용 자격 및 연락처 안내"
        if st.button(label):
            post_user_and_respond(label, ["학대피해노인 보호", "학대피해노인 쉼터", "학대피해 보호"])

    # (chat_container was moved earlier to appear before the example questions)

    # --- 사용자 입력 폼 (페이지 하단에 렌더링되도록 컨테이너 생성 후 배치) ---
    with st.form("chat_form", clear_on_submit=False):
        composer_val = st.text_input("다른 궁금하신 점을 말씀해 주세요 ! ", value=st.session_state.get("composer_input", ""), key="composer_widget")
        submitted = st.form_submit_button("전송")
    user_input = None
    if submitted:
        composer_val = st.session_state.get("composer_widget", "")
        if composer_val:
            user_input = composer_val
            # 전송 후 입력창 상태 초기화 (widget-backed 키는 직접 수정하지 않습니다)
            st.session_state["composer_input"] = ""

    # --- 챗봇 입력 처리 ---
    if user_input:
        # 사용자가 직접 입력한 경우: 메시지 기록만 추가하고, 답변은 세션 스토어에 저장합니다.
        st.session_state.messages.append({"role": "user", "content": user_input})
        try:
            with st.spinner("잠시만 기다려 주세요..."):
                answer = ask_with_fallback(user_input, user_input)
            st.session_state.messages.append({"role": "assistant", "content": answer})
        except Exception as e:
            st.error(f"챗봇 응답 생성 중 오류가 발생했어요: {str(e)}. 다시 시도해 주세요!")

    # --- 채팅 기록을 플레이스홀더에 렌더링합니다 (페이지 하단에 위치) ---
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"]) 

if __name__ == "__main__":
    run_chatbot_hhr()