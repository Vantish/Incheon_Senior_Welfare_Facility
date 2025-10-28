# app_chatbot.py (검진 일정, 건강 팁, 준비 방법 상세 반영)
import streamlit as st
import pandas as pd
from transformers import T5Tokenizer, T5ForConditionalGeneration
import sys
import re

print("Python path:", sys.executable)
print("Installed packages:", sys.modules.keys())

@st.cache_resource
def load_model():
    try:
        tokenizer = T5Tokenizer.from_pretrained("google/flan-t5-base")
        model = T5ForConditionalGeneration.from_pretrained("google/flan-t5-base")
        print("Model loaded successfully")
        return tokenizer, model
    except Exception as e:
        print(f"Model load error: {e}")
        raise

@st.cache_data
def load_data():
    try:
        df = pd.read_csv("./data/국민건강보험공단_건강검진정보_2024.csv", encoding="cp949", nrows=10000)
        df_nosun = df[df['연령대코드(5세단위)'] >= 13]  # 65세 이상
        if '시도코드' in df:
            df_nosun = df_nosun[df_nosun['시도코드'] == 31]  # 인천
        avg_blood_pressure = df_nosun['수축기혈압'].mean()
        avg_blood_sugar = df_nosun['식전혈당(공복혈당)'].mean()
        return {
            "location": "인천",
            "age_group": "65세 이상",
            "year": "2024",
            "blood_pressure": f"{avg_blood_pressure:.0f}mmHg",
            "blood_sugar": f"{avg_blood_sugar:.0f}mg/dL",
            "inspection": "2년마다 무료",
            "schedule": "2025년 홀수년도생",
            "reservation": "incheon.kahp.or.kr",
            "phone": "032-456-7890",
            "institution": "인천광역시 건강관리협회"
        }
    except Exception as e:
        return {
            "location": "인천",
            "age_group": "65세 이상",
            "year": "2024",
            "blood_pressure": "130mmHg",
            "blood_sugar": "100mg/dL",
            "inspection": "2년마다 무료",
            "schedule": "2025년 홀수년도생",
            "reservation": "incheon.kahp.or.kr",
            "phone": "032-456-7890",
            "institution": "인천광역시 건강관리협회"
        }

def make_prompt(user_q, data):
    # 연령과 성별 추출
    age = re.search(r'\d+', user_q)
    gender = re.search(r'남성|여성', user_q)
    age_str = f"{age.group(0)}세" if age else "65세 이상"
    gender_str = gender.group(0) if gender else "모두"
    
    prompt = f"당신은 {data['institution']}에서 운영하는 인천 {data['age_group']} 노인을 위한 검진 도우미입니다. 아래 데이터를 기반으로 질문에 구체적이고 자연스러운 한국어로 2문장 이상으로 응답하세요.\n"
    prompt += f"데이터: {data['location']} {data['age_group']} ({data['year']} 기준), 혈압: {data['blood_pressure']}, 혈당: {data['blood_sugar']}, 검진: {data['inspection']}, 일정: {data['schedule']}, 예약: {data['reservation']}, 전화: {data['phone']}, 기관: {data['institution']}\n"
    prompt += f"질문: {user_q}\n"
    if "검진일정" in user_q:
        prompt += f"응답에는 받을 수 있는 검진 종류(기본검진, 위암/대장암 선별검진, 치매 검진 등), {age_str} {gender_str}이 포함되는지, 일정(2025년 1월~12월), 예약 가능한 기관명({data['institution']})과 전화번호({data['phone']})를 포함하세요."
    elif "건강 팁" in user_q:
        prompt += f"응답에는 {age_str} {gender_str}에 맞춘 구체적인 건강 팁(예: 고혈압 관리, 전립선/유방 건강, 운동, 영양)을 포함하세요."
    elif "준비 방법" in user_q:
        prompt += f"응답에는 {age_str} {gender_str}을 위한 검진 준비 방법(기본검진, 위암/대장암 선별검진, 치매 검진 등에 따른 금식 시간, 약물 조정, 준비물)을 상세히 포함하세요."
    else:
        prompt += f"응답에는 {data['institution']}에 대한 간략한 설명과 {data['reservation']}, {data['phone']}를 포함하세요."
    prompt += "반복이나 불필요한 숫자 반복을 피하고, 자연스러운 문장으로 마무리하세요."
    return prompt

st.set_page_config(page_title="인천 노인 검진 AI", page_icon="🩺")
st.title("🩺 인천 노인 무료 검진 AI (로컬)")
st.caption("검진 문의 (e.g., '70 세 남성 검진일정?', '건강 팁?', '준비 방법?')")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

try:
    tokenizer, model = load_model()
    if prompt := st.chat_input("질문..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("생성 중..."):
                data = load_data()
                full_prompt = make_prompt(prompt, data)
                inputs = tokenizer(full_prompt, return_tensors="pt", max_length=512, truncation=True)
                outputs = model.generate(**inputs, max_new_tokens=250, temperature=0.7)  # 토큰 증가
                answer = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
                # 불필요한 반복 제거
                answer = " ".join(dict.fromkeys(answer.split()))
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
except Exception as e:
    st.error(f"오류: {e}")

with st.sidebar:
    st.header("⚙️ 설정")
    st.write("- CSV: [다운로드](https://www.data.go.kr/data/15007122/fileData.do)")
    if st.button("초기화"):
        st.session_state.messages = []
        st.rerun()