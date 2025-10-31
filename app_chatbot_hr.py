import streamlit as st
import google.generativeai as genai
import pandas as pd
import re
import os
import tempfile
from PIL import Image
import pytesseract
from pdf2image import convert_from_path

# === PDF 텍스트 추출 함수 (OCR 포함) ===
def extract_text_from_pdf(path: str) -> str:
    """PDF에서 텍스트를 추출합니다. pypdf 우선, 실패하면 OCR."""
    if not os.path.exists(path):
        return ""
    
    try:
        from pypdf import PdfReader
    except Exception:
        try:
            import PyPDF2
            PdfReader = PyPDF2.PdfReader
        except Exception:
            return ""

    try:
        reader = PdfReader(path)
        parts = []
        for p in reader.pages:
            try:
                t = p.extract_text() or ''
            except Exception:
                t = ''
            if t:
                parts.append(t)
        text = '\n\n'.join(parts)
        if len(text.strip()) > 500:
            return text
    except Exception:
        pass

    # OCR 강제 추출
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            images = convert_from_path(path, dpi=200, output_folder=temp_dir, fmt="png")
            ocr_text = ""
            for img in images:
                ocr_text += pytesseract.image_to_string(img, lang='kor') + "\n\n"
            return ocr_text
    except Exception as e:
        st.warning(f"OCR 실패 ({os.path.basename(path)}): {e}")
        return ""

# === PDF 캐시 (한 번만 읽기) ===
@st.cache_data
def load_pdf_texts():
    pdf1_text = extract_text_from_pdf("./data/2025+노인보건복지사업안내(1권).pdf")
    pdf2_text = extract_text_from_pdf("./data/2025+노인보건복지사업안내(2권).pdf")
    return pdf1_text + "\n\n" + pdf2_text

PDF_FULL_TEXT = load_pdf_texts()

# === PDF에서 질문에 맞는 답변 찾기 (정확도 UP) ===
def search_pdf_for_answer(question: str) -> str:
    if not PDF_FULL_TEXT.strip():
        return "**PDF를 불러올 수 없습니다.** 관리자에게 문의해 주세요."
    
    # 긴 점선 정규화
    normalized_text = re.sub(r'·{3,}', '···', PDF_FULL_TEXT)
    
    # 키워드 추출
    keywords = re.findall(r'[가-힣]{2,}', question)
    if not keywords:
        return "**질문에 키워드가 없습니다.**"

    # 목차 매칭 (정확한 패턴)
    title_pattern = re.compile(
        r'^(\d+[-\d]*)\s*[·\.]+\s*([가-힣\s\(\)·]+?)\s*[·\.]+\s*(\d+)$',
        re.MULTILINE
    )
    matches = title_pattern.finditer(normalized_text)

    best_match = None
    best_score = 0

    for match in matches:
        section_num = match.group(1).strip()
        title = match.group(2).strip()
        page_num = match.group(3).strip()

        score = sum(kw in title for kw in keywords)
        if score > best_score:
            best_score = score
            best_match = (section_num, title, page_num)

    if not best_match:
        return "**PDF에 해당 내용이 없습니다.**"

    section_num, title, page_num = best_match

    # 내용 추출
    lines = normalized_text.split('\n')
    start_idx = None
    end_idx = None

    for i, line in enumerate(lines):
        if section_num in line and title[:10] in line:
            start_idx = i + 1
        elif start_idx is not None and re.match(r'^\d+[-\d]*[\s·\.]', line.strip()):
            end_idx = i
            break

    if start_idx is None:
        return "**섹션 내용을 찾을 수 없습니다.**"

    if end_idx is None:
        end_idx = len(lines)

    content_lines = lines[start_idx:end_idx]
    content = '\n'.join([line.strip() for line in content_lines if line.strip() and len(line.strip()) > 5])
    content = re.sub(r'\n{3,}', '\n\n', content)
    content = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', content)

    if len(content) > 1500:
        content = content[:1500] + "\n\n...(이하 생략)"

    return f"**{title}** (페이지 {page_num})\n\n{content}"

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
        tips.append("체중을 조금 관리하시면 더 건강해지실 거예요. 채소 위주의 식사를 하시고, 산책처럼 가벼운 운동을 시작해 보시는 건 어떨까요? 천천히 하셔도 충분해요!")
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

def run_chatbot_hhr():
    st.title("인천 노인을 위한 도우미 챗봇")
    st.write("건강검진과 복지 정보를 안내드리는 챗봇입니다. 궁금하신 점을 편하게 물어보세요!")

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
            if st.button("내 근처 검진기관 찾기"):
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

    # 건강관리 정보
    with st.expander("건강관리 정보", expanded=False):
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
            st.markdown("**맞춤 건강 팁**")
            st.markdown("**맞춤 건강 정보**")
            st.markdown(health_tip)

    # 검진준비 안내
    with st.expander("검진준비 안내", expanded=False):
        st.markdown("검진 준비에 대해 궁금하신 점을 아래에서 검색해보세요.")
        st.markdown("- 건강검진 전 금식은 어떻게 해야 하나요?")
        st.markdown("- 검진 당일 어떤 옷을 입는 게 좋나요?")
        st.markdown("- 약을 복용 중인데 검진 전 어떻게 해야 하나요?")
        st.markdown("- 검진을 받기 위해 필요한 서류는 무엇인가요?")
        st.markdown("- 검진 후 결과는 언제 알 수 있나요?")

    # 복지 프로그램 안내 (PDF 목차 기반 질문만)
    welfare_sections = [
        ("노인일자리 안내 질문", "노인일자리 관련 궁금하신 점을 아래에서 검색해보세요"),
        ("지원금 및 혜택 안내 질문", "지원금 및 혜택 관련 궁금하신 점을 아래에서 검색해보세요!"),
        ("여가·문화활동 안내 질문", "여가·문화활동 관련 궁금하신 점을 아래에서 검색해보세요!"),
        ("긴급지원·상담 안내 질문", "긴급지원·상담 관련 궁금하신 점을 아래에서 검색해보세요!")
    ]

    for title, intro in welfare_sections:
        with st.expander(title, expanded=False):
            st.markdown(intro)

            questions = []
            if "노인일자리" in title:
                questions = [
                    "- 노인일자리 및 사회활동 지원사업은 무엇인가요?",        # 2-1, p.43
                    "- 노인자원봉사 활성화 사업은 어떻게 운영되나요?",        # 2-2, p.62
                    "- 경로당 운영은 어떤 방식인가요?",                       # 2-3, p.70
                    "- 노인복지관 설치·운영은 어떻게 되나요?",               # 2-4, p.118
                    "- 노인교실은 어떤 프로그램이 있나요?"                    # 2-5, p.133
                ]
            elif "지원금" in title:
                questions = [
                    "- 노인지원시설 기능보강 사업은 어떤 혜택인가요?",        # 7-4, p.127
                    "- 노인복지시설 기능보강 사업은 어떤 내용인가요?",        # 7-5, p.207
                    "- 노인장기요양보험제도 사업은 무엇인가요?",             # 7-6, p.284
                    "- 장기요양기관 설치 및 운영기준은 어떻게 되나요?",       # 7-7, p.287
                    "- 장기요양급여비용의 지급에 관한 기준은?"               # 7-8, p.444
                ]
            elif "여가" in title:
                questions = [
                    "- 노인종합복지서비스 사업은 어떤 내용인가요?",            # 3-1, p.139
                    "- 독거노인·장애인 응급안전안심서비스는 어떻게 신청하나요?", # 3-2, p.148
                    "- 독거노인 공동생활 홈 서비스는 어떤가요?",             # 3-3, p.152
                    "- 노인요양시설 설치 및 운영은 어떻게 되나요?",           # 3-4, p.161
                    "- 학대피해 노인 전용쉼터 운영은 어떻게 되나요?"          # 3-5, p.199
                ]
            elif "긴급지원" in title:
                questions = [
                    "- 치매관리사업의 현황은 어떤가요?",                       # 6-1, p.317
                    "- 중장·광역 치매안심센터 운영은 어떻게 되나요?",         # 6-2, p.322
                    "- 치매안심병원 및 공립요양병원 사업은 어떤가요?",         # 6-3, p.329
                    "- 실종치매환자의 발생예방 및 조기 사법은?",             # 6-4, p.330
                    "- 치매공공후견사업은 무엇인가요?",                       # 6-5, p.331
                    "- 노인학대예방사업은 어떻게 운영되나요?",                 # 6-6, p.332
                    "- 노인 보호전문기관 수술 지원은?",                       # 6-7, p.347
                    "- 노인 긴급전화 운영은 어떻게 되나요?"                   # 6-8, p.357
                ]

            for q in questions:
                if st.button(q, key=f"btn_{title}_{q}"):
                    with st.spinner("PDF에서 정보를 찾고 있어요..."):
                        pdf_answer = search_pdf_for_answer(q)
                    
                    st.markdown("**PDF 안내서에서 찾은 내용입니다:**")
                    st.markdown(pdf_answer)

    # 사용자 입력 처리 (챗봇 - PDF 우선, 없으면 안내)
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("PDF에서 정보를 찾고 있어요..."):
                pdf_answer = search_pdf_for_answer(user_input)
            st.markdown(pdf_answer)
            st.session_state.messages.append({"role": "assistant", "content": pdf_answer})

if __name__ == "__main__":
    run_chatbot_hhr()

    # 다른코드는 절대 건들지말고 너가 건드릴수잇는건 pdf, 노인일자리, 지원금및혜택, 여가문화활동, 긴급지원 코드만 건드릴수있어 다른 코드 건들지마.