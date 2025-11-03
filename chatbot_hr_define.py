import os
import streamlit as st
import google.generativeai as genai
from pathlib import Path

# Chroma/Embedding/LLM 관련 라이브러리 (load_vectorstore, make_rag_chain 구현에 필요)
import chromadb
from langchain_community.vectorstores import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnablePassthrough

# 상수: chroma DB 위치, embedding/LLM 모델
CHROMA_DIR = './chroma_db'
EMBED_MODEL = "text-embedding-004"
LLM_MODEL = "gemini-2.5-flash"

# chatbot_hr에서 반복적으로 사용되는 긴 UI 블록(예: 예시 질문 팝오버)을
# 별도의 함수로 분리하여 코드 가독성을 높입니다.
# 주의: 내부 동작(입력값, 세션키 사용, post_user_and_respond 호출 등)은
# 변경하지 않습니다. 단지 UI 블록을 호출 가능한 함수로 옮깁니다.


# --- 모듈 레벨 헬퍼 함수들 ---
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


def ask_rag(question):
    try:
        vectordb = load_vectorstore()
        chain = make_rag_chain(vectordb)
        result = chain.invoke({"question": question})
        return result
    except Exception as e:
        print(f"ask_rag error: {e}")
        return None


# -----------------------------
# app_testchatbot에서 사용하던 헬퍼 함수들 (원본 동작 그대로 복사)
# -----------------------------

def format_docs(docs):
    """
    검색된 Document 객체 리스트를 LLM 프롬프트에 넣기 좋은
    단일 문자열(context)과 출처 문자열(source)로 포맷팅합니다.
    """
    context_parts = []
    source_names = set() # 중복 출처 제거용
    
    for i, doc in enumerate(docs, 1):
        # page_content 포맷팅 (내용)
        content = doc.page_content.strip()
        context_parts.append(f"[{i}] {content}")
        
        # metadata 포맷팅 (출처)
        source = doc.metadata.get("source", "N/A")
        # 파일 경로에서 파일명만 추출 (예: ./data/file.pdf -> file.pdf)
        source_name = Path(source).name
        source_names.add(source_name)

    # 최종 문자열 생성
    context_str = "\n\n".join(context_parts)
    source_str = ", ".join(source_names) # 출처 파일명들을 콤마로 연결
    
    # context와 source를 튜플로 반환
    return (context_str, source_str)


def add_source_to_answer(result):
    """
    LLM의 답변(answer)과 포맷팅된 출처(source)를 결합하여
    최종 사용자 답변 문자열을 생성합니다.
    """
    answer = result["answer"]
    source = result["source"]
    
    if source and source != "N/A":
        return f"{answer}\n\n---\n**출처:** {source}"
    else:
        return answer


@st.cache_resource
def load_vectorstore():
    """
    Streamlit 앱 실행 시 단 한 번만 ChromaDB를 로드합니다.
    (원본 동작을 그대로 유지합니다.)
    """
    embeddings = GoogleGenerativeAIEmbeddings(model=EMBED_MODEL)
    db_path = Path(CHROMA_DIR)

    if not db_path.exists() or not (db_path / "chroma.sqlite3").exists():
        st.error(f"'{CHROMA_DIR}' 폴더 또는 'chroma.sqlite3' 파일을 찾을 수 없습니다.")
        st.error("Colab에서 'chroma_db'를 빌드한 후, 압축 해제하여 VScode 프로젝트 폴더에 올바르게 복사했는지 확인하세요.")
        st.stop()

    try:
        # ChromaDB 클라이언트에 직접 연결하여 진단 시작
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        
        # 1. 컬렉션 목록 확인
        collections = client.list_collections()
        if not collections:
            st.error(f"'{CHROMA_DIR}' DB는 로드되었으나, 안에 컬렉션이 없습니다.")
            st.error("Colab DB 빌드 중 오류가 있었을 수 있습니다. Colab에서 DB를 다시 빌드하세요.")
            st.stop()

        # 2. 'langchain' (기본값) 컬렉션 가져오기
        try:
            collection = client.get_collection(name="langchain")
        except Exception as e:
            st.error(f"DB에서 'langchain' 컬렉션을 찾는 중 오류: {e}")
            st.error(f"사용 가능한 컬렉션: {[c.name for c in collections]}")
            st.error("Colab의 chromadb 버전(1.3.0)과 로컬 VScode의 chromadb 버전(1.3.0)이 동일한지 확인하세요.")
            st.stop()

        # 3. 문서 개수 확인
        count = collection.count()
        if count == 0:
            st.warning(f"'{CHROMA_DIR}' DB는 로드되었으나, 'langchain' 컬렉션 안에 문서가 0개입니다.")
            st.warning("Colab에서 DB가 정상적으로 빌드되었는지, 'chroma_db' 폴더가 올바르게 복사/압축 해제되었는지 다시 확인하세요.")
            st.stop()
        
        # 터미널(콘솔)에 성공 로그 출력
        print(f"\n--- [DB 진단 성공] ---")
        print(f"'{CHROMA_DIR}' DB 로드 성공.")
        print(f"컬렉션 '{collection.name}'에서 {count}개의 문서를 찾았습니다.")
        print(f"----------------------\n")

        # 4. LangChain VectorStore 객체로 래핑
        vectordb = Chroma(
            client=client,
            collection_name="langchain",
            embedding_function=embeddings,
        )
        return vectordb

    except Exception as e:
        st.error(f"DB 문서 개수 확인 중 심각한 오류 발생: {e}")
        st.error("ChromaDB 파일이 손상되었을 수 있습니다. Colab에서 DB를 다시 빌드하고 VScode의 `chromadb` 버전을 (1.3.0) 통일하세요.")
        st.stop()


@st.cache_resource
def make_rag_chain(_vectordb):
    """
    벡터DB(retriever)와 LLM을 결합해 RAG 체인을 생성합니다.
    - 어르신 친화형 말투 및 정책자료 기반 응답 강화
    - 검색 다양성 확보 (mmr + k=10)
    """
    retriever = _vectordb.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 10}
    )

    # --------------------------------------------
    # 🌿 개선된 system prompt
    # --------------------------------------------
    system_prompt = """
당신은 한국어로 답하는 노인 건강 및 복지 전문 어시스턴트입니다.

[역할]
- 노인복지 관련 제도, 시설, 급여, 장기요양, 지원금 등과 관련된 질문에 답합니다.
- 모든 답변은 검색된 근거(맥락)에 기반해야 합니다.

[규칙]
- 반드시 제공된 근거(맥락)에 기반하여 간결하고 정확하게 답하세요.
- 숫자, 제도명, 기관명 등은 원문 표현을 유지하세요.
- 모르면 모른다고 답하고, 추측하지 마세요.
- 사용자는 주로 어르신이나 복지시설 종사자입니다.
- 항상 상냥하고 이해하기 쉬운 존댓말로 답하세요.
- 사용자를 '사용자님'이라 부르세요.
- 복지·건강 이외의 질문은 부드럽게 거절하세요.

[말투 지침]
- 짧고 따뜻한 문장으로 설명합니다.
- 한 문단에 한 가지 내용만 전달합니다.
- 어려운 행정용어가 나오면 괄호로 풀어서 설명합니다.
- 예: “사용자님, 이 제도는 만 65세 이상 어르신께서 신청하실 수 있습니다.”
"""

    # --------------------------------------------
    # 💬 프롬프트 템플릿 (검색 결과 + 질문 결합)
    # --------------------------------------------
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        (
            "human",
            "질문: {question}\n\n"
            "아래는 검색된 정책자료 일부입니다. 이 내용을 참고하여 사용자님께 이해하기 쉽게 설명해주세요.\n\n"
            "{context}\n\n"
            "출처를 아는 경우, 마지막에 '참고: 기관명 또는 자료명'을 붙여주세요."
        ),
    ])

    # --------------------------------------------
    # 🤖 LLM 초기화
    # --------------------------------------------
    llm = ChatGoogleGenerativeAI(
        model=LLM_MODEL,
        temperature=0.2  # 낮을수록 사실 기반
    )

    # --------------------------------------------
    # 🧩 체인 구성 (retriever → formatter → prompt → llm)
    # --------------------------------------------
    # retriever가 문서를 가져와 (context, source) 튜플로 변환
    retrieval_chain = RunnableLambda(
        lambda x: format_docs(retriever.invoke(x["question"]))
    )

    # context + source + question 매핑
    formatting_chain = RunnableLambda(
        lambda tup: {"context": tup[0], "source": tup[1], "question": tup[2]}
    )

    # LLM 응답 + 출처 정보 합침
    prompt_chain = {
        "answer": prompt | llm | StrOutputParser(),
        "source": lambda x: x["source"]
    }

    final_chain = (
        {
            "result": retrieval_chain,
            "question": lambda x: x["question"]
        }
        | RunnableLambda(lambda x: formatting_chain.invoke((x["result"][0], x["result"][1], x["question"])))
        | prompt_chain
        | RunnableLambda(add_source_to_answer)
    )

    return final_chain


def ask_with_fallback(topic_query, user_display_question=None):
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
        primary = topic_query[0] if topic_query else ""
    else:
        # 1) 먼저 직접 시도
        res = ask_rag(topic_query)
        if res:
            return res
        primary = topic_query

    # 2) 문서에 존재할 가능성이 높은 토픽으로 재매핑 (간단한 키워드 맵)
    fallback_map = {
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


def post_user_and_respond(user_label, mapped_q, use_gemini=False):
    # 사용자에게 보이는 질문 라벨을 채팅에 남깁니다.
    if "messages" not in st.session_state:
        st.session_state.messages = []
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


def render_example_popover(post_user_and_respond, health_institutions, calculate_bmi, get_bmi_category, get_health_tip):
    """예시 질문 팝오버 전체를 렌더링합니다.

    인자로 필요한 콜백과 데이터프레임을 받습니다:
    - post_user_and_respond: 버튼 클릭 시 호출되는 콜백(원본 함수를 전달)
    - health_institutions: 검진기관 데이터프레임
    - calculate_bmi, get_bmi_category, get_health_tip: 건강관련 계산/문구 함수

    함수 내부는 원본 코드와 동일하게 동작합니다.
    """
    with st.popover("👇 예시 질문 보기"):
        st.markdown("궁금한 질문을 눌러보세요. 팝업 바깥쪽을 누르면 닫힙니다.")

        # --- 검진기관 안내 ---
        with st.expander("🏥 국가 건강 검진 기관 안내", expanded=False):
            st.markdown("궁금하신 검진기관 정보를 확인하려면 주소를 입력하고 검색 버튼을 눌러 주세요.")
            col1, col2 = st.columns([4, 1])
            with col1:
                st.session_state.user_address = st.text_input("주소를 입력해 주세요 (예: 인천광역시 서구 서곶로):", value=st.session_state.get('user_address', ''), key="address_input_popover")
            with col2:
                if st.button("🔍내 근처 검진기관 찾기"):
                    st.session_state.search_triggered = True
                    st.rerun()  # 즉시 새로고침
            st.session_state.user_age = st.number_input("나이를 입력해 주세요", min_value=20, max_value=120, value=st.session_state.get('user_age', 50), key="age_input_popover")
            st.session_state.user_gender = st.selectbox("성별을 선택해 주세요", ["남성", "여성"], index=0 if st.session_state.get('user_gender', '남성') == "남성" else 1, key="gender_input_popover")

            if st.session_state.get('search_triggered') and st.session_state.get('user_address'):
                # (검진기관 검색 결과 로직...)
                nearby_institutions = health_institutions[health_institutions['주소'].str.contains(st.session_state.user_address, na=False)]
                if st.session_state.user_gender == "남성":
                    nearby_institutions = nearby_institutions[~nearby_institutions['검진기관명'].str.contains("산부인과", na=False)]
                if nearby_institutions.empty:
                    st.markdown("입력하신 주소 근처에 적합한 검진 기관이 없어요.")
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
            elif st.session_state.get('search_triggered') and not st.session_state.get('user_address'):
                st.markdown("🔍주소를 입력해 주시면 근처 검진 기관을 찾아드릴게요!")

        # --- 건강관리 정보 ---
        with st.expander("🌈건강관리 정보", expanded=False):
            st.markdown("건강 정보를 입력하시면 맞춤형 건강 정보를 드릴게요!")
            weight = st.number_input("체중(kg)을 입력해 주세요", min_value=30.0, max_value=200.0, value=70.0, key="weight_input_popover")
            height = st.number_input("키(cm)를 입력해 주세요", min_value=100.0, max_value=250.0, value=170.0, key="height_input_popover")
            bp_sys = st.number_input("수축기 혈압(mmHg)을 입력해 주세요", min_value=50, max_value=250, value=st.session_state.get('bp_sys', 120), key="bp_sys_input_popover")
            bp_dia = st.number_input("이완기 혈압(mmHg)을 입력해 주세요", min_value=30, max_value=150, value=st.session_state.get('bp_dia', 80), key="bp_dia_input_popover")
            fbs = st.number_input("식전혈당(mg/dL)을 입력해 주세요", min_value=50, max_value=400, value=st.session_state.get('fbs', 90), key="fbs_input_popover")
            waist = st.number_input("허리둘레(cm)를 입력해 주세요", min_value=50, max_value=150, value=st.session_state.get('waist', 80), key="waist_input_popover")
            gender = st.selectbox("성별을 선택해 주세요", ["남성", "여성"], index=0 if st.session_state.get('user_gender','남성') == "남성" else 1, key="gender_input_popover_health")
            if weight and height:
                bmi = calculate_bmi(weight, height)
                st.markdown(f"**BMI**: {bmi} ({get_bmi_category(bmi)})")
                health_tip = get_health_tip(bmi, bp_sys, bp_dia, fbs, waist, gender)
                st.markdown("**맞춤 건강 정보**")
                st.markdown(health_tip)

        # --- 검진준비 안내 (Gemini 답변) ---
        with st.expander("📌검진준비 안내 질문", expanded=False):
            st.markdown("아래 질문 중 하나를 클릭하시면 자세히 알려드려요!")

            if st.button("건강검진 전 금식은 어떻게 해야 하나요?"):
                post_user_and_respond("건강검진 전 금식은 어떻게 해야 하나요?", "건강검진 전 금식 방법", use_gemini=True)
                st.rerun()  # 즉시 새로고침
            st.markdown("<br>", unsafe_allow_html=True)

            if st.button("검진 당일 어떤 옷을 입는 게 좋나요?"):
                post_user_and_respond("검진 당일 어떤 옷을 입는 게 좋나요?", "건강검진 당일 옷차림", use_gemini=True)
                st.rerun()  # 즉시 새로고침
            st.markdown("<br>", unsafe_allow_html=True)

            if st.button("약을 복용 중인데 검진 전 어떻게 해야 하나요?"):
                post_user_and_respond("약을 복용 중인데 검진 전 어떻게 해야 하나요?", "건강검진 전 약 복용 방법", use_gemini=True)
                st.rerun()  # 즉시 새로고침
            st.markdown("<br>", unsafe_allow_html=True)

            if st.button("검진을 받기 위해 필요한 서류는 무엇인가요?"):
                post_user_and_respond("검진을 받기 위해 필요한 서류는 무엇인가요?", "건강검진 필요 서류", use_gemini=True)
                st.rerun()  # 즉시 새로고침
            st.markdown("<br>", unsafe_allow_html=True)

            if st.button("검진 후 결과는 언제 알 수 있나요?"):
                post_user_and_respond("검진 후 결과는 언제 알 수 있나요?", "건강검진 결과 확인 시기", use_gemini=True)
                st.rerun()  # 즉시 새로고침

        # --- 노인복지 및 주요 서비스 (LLM 질의에 맞춘 항목) ---
        with st.expander("🧾 노인복지 주요 안내", expanded=False):
            st.markdown("제가 안내할 수 있는 주요 주제들을 눌러보세요. 각 항목은 제가 가진 자료를 바탕으로 자세히 설명해 드립니다.")

            label = "노인복지 제도 전반: 제공되는 주요 복지 서비스와 제도는 무엇인가요?"
            if st.button(label):
                post_user_and_respond(label, ["노인복지 제도", "노인복지 서비스 종류", "복지 정책 안내"])
                st.rerun()  # 즉시 새로고침
            st.markdown("<br>", unsafe_allow_html=True)

            label = "노인 주거 지원: 공공임대주택·주거지원 및 신청절차 안내"
            if st.button(label):
                post_user_and_respond(label, ["노인 주거 지원", "공공임대주택 신청", "주거복지 지원"])
                st.rerun()  # 즉시 새로고침
            st.markdown("<br>", unsafe_allow_html=True)

            label = "노인장기요양보험: 급여 종류(방문요양·시설급여 등) 및 신청 방법"
            if st.button(label):
                post_user_and_respond(label, ["장기요양보험", "방문요양", "시설급여", "장기요양 신청 절차"])
                st.rerun()  # 즉시 새로고침
            st.markdown("<br>", unsafe_allow_html=True)

            label = "노인일자리 지원사업: 참여 유형·자격·신청처 안내"
            if st.button(label):
                post_user_and_respond(label, ["노인일자리 지원사업", "공익형 사회서비스형 시장형", "노인일자리 참여 자격"])
                st.rerun()  # 즉시 새로고침

        # --- 주요 급여·지원 안내 ---
        with st.expander("💰 기초연금·지원금 안내", expanded=False):
            st.markdown("기초연금, 수당, 의료비 지원 등 주요 지원제도에 대해 안내합니다.")
            label = "기초연금: 신청 방법·지급 방식·감액 기준 안내"
            if st.button(label):
                post_user_and_respond(label, ["기초연금 신청", "기초연금 감액 기준"])
                st.rerun()  # 즉시 새로고침
            st.markdown("<br>", unsafe_allow_html=True)

        # --- 돌봄·요양 안내 ---
        with st.expander("🕊️ 노인맞춤돌봄·요양 안내", expanded=False):
            label = "노인맞춤돌봄서비스: 제공 항목(안전·사회참여·생활교육)과 이용방법 안내"
            if st.button(label):
                post_user_and_respond(label, ["노인맞춤돌봄서비스", "돌봄 서비스 종류", "긴급 돌봄"])
                st.rerun()  # 즉시 새로고침
            st.markdown("<br>", unsafe_allow_html=True)
