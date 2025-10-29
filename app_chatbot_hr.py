# health_chatbot_t5_streamlit.py

import streamlit as st
from transformers import T5Tokenizer, T5ForConditionalGeneration
import pandas as pd
import re

# -----------------------------
# 데이터 로드
# -----------------------------
@st.cache_data
def load_data():
    health_df = pd.read_csv("./data/국민건강보험공단_건강검진정보_2024.CSV", encoding="cp949", nrows=100000)
    hosp_df = pd.read_csv("./data/incheon_health_check_centers.csv", encoding="utf-8-sig")
    return health_df, hosp_df

health_df, hosp_df = load_data()

# -----------------------------
# 모델 로드
# -----------------------------
@st.cache_resource
def load_model():
    tokenizer = T5Tokenizer.from_pretrained("KETI-AIR/ke-t5-base")
    model = T5ForConditionalGeneration.from_pretrained("KETI-AIR/ke-t5-base")
    return tokenizer, model

tokenizer, model = load_model()

# -----------------------------
# 헬퍼 함수
# -----------------------------
def is_garbled(text: str) -> bool:
    if not text or len(text) < 10:
        return True
    if re.search(r'(.{2,6})\1{3,}', text):
        return True
    hangul = sum(1 for c in text if '\uac00' <= c <= '\ud7a3')
    if len(text) > 0 and (hangul / len(text)) < 0.5:
        return True
    return False

def fallback_schedule(age, gender):
    exams = ["기본 건강검진"]
    if age >= 40: exams.append("위암 검진")
    if age >= 50: exams.append("대장암 검진")
    if age >= 66: exams.append("치매 조기검진")
    if gender == "여성" and age >= 40: exams.append("유방암 검진")
    if gender == "남성" and age >= 50: exams.append("전립선 검진")

    return f"{age}세 {gender}은(는) {', '.join(exams)} 대상입니다. 혈압과 혈당을 관리하고, 검진 전날은 금식하세요."

def nearby_hospitals():
    text = "📍 인근 검진기관:\n"
    for _, r in hosp_df.head(3).iterrows():
        text += f"- {r.get('name','기관')} ({r.get('phone','전화번호')})\n"
    return text.strip()

def generate_answer(prompt, age=None, gender=None):
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
    outputs = model.generate(**inputs, max_new_tokens=120, num_beams=2, no_repeat_ngram_size=3)
    text = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()

    if is_garbled(text):
        return fallback_schedule(age, gender) + "\n\n" + nearby_hospitals()
    else:
        return text + "\n\n" + nearby_hospitals()

# -----------------------------
# Streamlit 챗봇 UI
# -----------------------------
st.set_page_config(page_title="인천 노인 건강 도우미", layout="centered")
st.title("🏥 인천 노인 건강 도우미 챗봇")
st.write("고령층을 위한 건강검진·관리 안내 챗봇입니다.")

if "messages" not in st.session_state:
    st.session_state["messages"] = []

# 챗 메시지 표시
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 입력 형태 선택
mode = st.radio("원하시는 정보를 선택하세요 👇", ["검진 일정", "건강관리 팁", "검진 준비방법"], horizontal=True)

age_input = st.text_input("나이 (예: 70)")
gender_input = st.selectbox("성별", ["남성", "여성", "모름"], index=0)

user_input = st.text_area("질문을 입력하세요 (예: 70세 남성의 건강관리)", "")

if st.button("답변 받기"):
    if not user_input.strip():
        st.warning("질문을 입력해주세요.")
    else:
        # 사용자 메시지 저장
        st.session_state["messages"].append({"role": "user", "content": user_input})

        age = int(re.search(r'(\d{2,3})', age_input).group(1)) if re.search(r'\d', age_input) else 0
        gender = gender_input if gender_input != "모름" else "성별 정보 없음"

        if mode == "검진 일정":
            prompt = f"{age}세 {gender}이(가) 받을 수 있는 건강검진 항목과 검진 주기를 알려주세요."
        elif mode == "건강관리 팁":
            prompt = f"{age}세 {gender}에게 추천할 생활습관 개선이나 건강관리 팁을 2문장으로 알려주세요."
        elif mode == "검진 준비방법":
            prompt = f"{age}세 {gender}이(가) 건강검진을 받기 전 준비해야 할 사항을 간단히 알려주세요."
        else:
            prompt = user_input

        answer = generate_answer(prompt, age, gender)
        st.session_state["messages"].append({"role": "assistant", "content": answer})
        st.rerun()
