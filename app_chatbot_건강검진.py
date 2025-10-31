import streamlit as st
import google.generativeai as genai
import pandas as pd
import fitz  # PyMuPDF
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# 데이터 및 PDF 전처리 함수 생략(기존과 동일)
health_institutions = pd.read_csv('./data/인천광역시_건강검진기관.csv', encoding='cp949', sep='\t')
health_pdf_paths= ['./data/★+2023년도+노인실태조사+보고서(최종본)★.pdf']
pdf_paths = ['./data/2025+노인보건복지사업안내(1권).pdf', './data/2025+노인보건복지사업안내(2권).pdf']



def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    return full_text

def preprocess_multiple_pdfs(pdf_paths):
    all_text = ""
    for path in pdf_paths:
        all_text += extract_text_from_pdf(path) + "\n"
    processed_text = all_text.replace('\n', ' ').replace('\r', '').strip()
    sentences = processed_text.split('. ')
    return sentences

pdf_sentences = preprocess_multiple_pdfs(pdf_paths)


def search_in_pdf_welfare_similarity(user_input, sentences=pdf_sentences, top_k=5):
    vectorizer = TfidfVectorizer().fit(sentences + [user_input])
    sen_vec = vectorizer.transform(sentences)
    query_vec = vectorizer.transform([user_input])
    cosine_sim = cosine_similarity(query_vec, sen_vec).flatten()
    top_idx = np.argsort(cosine_sim)[::-1][:top_k]
    results = [sentences[i] for i in top_idx if cosine_sim[i] > 0.1]
    if results:
        return '\n'.join(results)
    return None

health_pdf_sentences = preprocess_multiple_pdfs(health_pdf_paths)

def search_in_pdf_health_similarity(user_input, sentences=health_pdf_sentences, top_k=5):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np

    vectorizer = TfidfVectorizer().fit(sentences + [user_input])
    sen_vec = vectorizer.transform(sentences)
    query_vec = vectorizer.transform([user_input])
    cosine_sim = cosine_similarity(query_vec, sen_vec).flatten()
    top_idx = np.argsort(cosine_sim)[::-1][:top_k]
    results = [sentences[i] for i in top_idx if cosine_sim[i] > 0.1]

    if results:
        return '\n'.join(results)
    return None




def search_in_csv(user_input, df):
    matched = df[df.apply(lambda row: user_input.lower() in row.astype(str).str.cat(sep=' ').lower(), axis=1)]
    if not matched.empty:
        return matched.head(5).to_string(index=False)
    return None

def calculate_bmi(weight, height):
    if height <= 0:
        return None
    height_m = height / 100
    bmi = weight / (height_m ** 2)
    return round(bmi, 2)

def generate_response(prompt):
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"챗봇 응답 생성 중 오류가 발생했습니다: {str(e)}"

def run_chatbot_2():
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY_mj"])
    except KeyError:
        st.error("API 키가 설정되지 않았습니다. secrets.toml 파일을 확인해 주세요.")
        return

    st.title("🏥 나만을 위한 맞춤형 건강·복지 챗봇")

    user_age = st.number_input('나이를 입력해 주세요', min_value=5, max_value=120, value=50)
    user_health_conditions = st.text_input('본인의 건강 정보를 입력해 주세요 : 예) 고혈압, 당뇨, 비만 등')
    question_type = st.selectbox("문의 유형을 선택해 주세요", options=["건강 관련", "복지 관련"])
    user_input = st.text_area("궁금한 점을 입력해 주세요")


        # 상태 초기화 (새 질문 시)
    if "welfare_search_triggered" not in st.session_state:
        st.session_state["welfare_search_triggered"] = False
    if "health_search_triggered" not in st.session_state:
        st.session_state["health_search_triggered"] = False


    if st.button('실행하기'):
        combined_query = user_input
        if user_health_conditions.strip():
            combined_query += " " + user_health_conditions.strip()
        combined_query += f" 나이: {user_age}세"



        if question_type == "복지 관련":
            welfare_answer = search_in_pdf_welfare_similarity(combined_query)
            if welfare_answer:
                # AI에게 PDF 문장 자연스러운 재작성 요청
                prompt = f"""
                아래는 복지 관련 PDF에서 찾은 자료입니다.
                이를 사용자가 이해하기 쉽도록 자연스러운 문장으로 다시 작성해 주세요.
                모르는 내용이나 없는 정보는 포함하지 말고 정확한 내용만 전달해 주세요.

                원문:
                {welfare_answer}

                다시 작성한 답변:
                """
                with st.spinner("답변 생성 중입니다..."):
                    answer = generate_response(prompt)
                st.markdown(answer)
                st.session_state["welfare_search_triggered"] = False
            else:
                st.markdown("복지 관련 문의지만 참고할 자료가 부족합니다. 추가 검색을 원하시나요?")

        elif question_type == "건강 관련":
            health_pdf_answer = search_in_pdf_health_similarity(combined_query)
            if health_pdf_answer:
                prompt = f"""
                아래는 건강 관련 PDF에서 찾은 자료입니다.
                이를 사용자가 이해하기 쉽도록 자연스러운 문장으로 다시 작성해 주세요.
                모르는 내용이나 없는 정보는 포함하지 말고 정확한 내용만 전달해 주세요.
                사용자 질문을 받고 pdf에서 찾은 뒤 관련 정보와 같이 정리해서 이해하기 쉽게 말해주세요.

                원문:
                {health_pdf_answer}

                다시 작성한 답변:
                """
            with st.spinner("답변 생성 중입니다..."):
                answer = generate_response(prompt)
                st.markdown(answer)
                st.session_state["health_search_triggered"] = False
        else:
            st.markdown("건강 관련 문의지만 참고할 자료가 부족합니다. 추가 검색을 원하시나요?")



                
