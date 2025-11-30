# 다른코드는 절대 건들지말고 너가 건드릴수잇는건 pdf, 노인일자리, 지원금및혜택, 여가문화활동, 긴급지원 코드만 건드릴수있어 다른 코드 건들지마

import streamlit as st
import google.generativeai as genai
import pandas as pd
import PyPDF2
import re
import os
from pypdf import PdfReader

# 데이터 파일 불러오기
data_path = os.path.join('data', 'incheon health institutions.csv')
health_institutions = pd.read_csv(data_path, dtype=str, encoding='cp949', sep='\t')
data_path = os.path.join('data', 'health check data.csv')
health_check_data = pd.read_csv(data_path, dtype=str, encoding="cp949")

# --- RAG(CHROMA) 통합: app_testchatbot의 캐시된 벡터스토어/체인을 사용 ---
# app_testchatbot.py에 정의된 load_vectorstore, make_rag_chain를 재사용합니다.
from chatbot_hr_define import (
    render_example_popover,
    calculate_bmi,
    get_bmi_category,
    get_health_tip,
    ask_rag,
    ask_with_fallback,
    gemini_answer,
    post_user_and_respond,
)

# --- 메인 함수 ---
def run_chatbot_hhr():
    st.title("시니어 건강 / 지원 정책 챗봇")
    st.write("🔔건강검진과 복지 정보를 안내드리는 챗봇입니다. 궁금하신 점을 편하게 물어보세요!")

    # 헬퍼 함수들은 `chatbot_hr_define.py`로 이동했습니다.

    # --- 1. Gemini 및 세션 상태 초기화 ---
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

    
    # --- 2. [수정] 채팅 기록 표시 영역 ---
    chat_container = st.container(height=600) # 높이는 원하시는 대로 조절하세요
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    
    # --- 3. 예시 질문 팝오버 렌더링 (별도 모듈로 분리) ---
    # 긴 UI 블록을 `chatbot_hr_define.render_example_popover`로 분리하여
    # app 파일을 간결하게 유지합니다. 내부 동작(입력값, 세션키 등)은
    # 원본과 동일하게 동작하도록 콜백과 데이터프레임을 전달합니다.
    render_example_popover(post_user_and_respond, health_institutions, calculate_bmi, get_bmi_category, get_health_tip)
    
    # --- 4. [수정] 하단 고정 채팅 입력창 ---
    # (이 로직은 이미 실시간 응답을 지원하므로 수정이 필요 없습니다)
    
    if prompt := st.chat_input("다른 궁금하신 점을 말씀해 주세요 !"):
        
        # 1. 사용자 질문을 채팅 기록에 추가
        st.session_state.messages.append({"role": "user", "content": prompt})

        # 2. 채팅 기록 컨테이너에 사용자 질문을 *즉시* 표시
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)

        # 3. RAG + LLM 답변 생성 (기존 로직 재활용)
        try:
            with st.spinner("잠시만 기다려 주세요..."):
                answer = ask_with_fallback(prompt, prompt) 
            
            # 4. 챗봇 답변을 채팅 기록에 추가
            st.session_state.messages.append({"role": "assistant", "content": answer})
            
            # 5. 채팅 기록 컨테이너에 챗봇 답변을 *즉시* 표시
            with chat_container:
                with st.chat_message("assistant"):
                    st.markdown(answer)
            
        except Exception as e:
            error_message = f"챗봇 응답 생성 중 오류가 발생했어요: {str(e)}."
            st.session_state.messages.append({"role": "assistant", "content": error_message})
            with chat_container:
                with st.chat_message("assistant"):
                    st.markdown(error_message)


if __name__ == "__main__":
    run_chatbot_hhr()