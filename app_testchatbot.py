import os
import streamlit as st
from pathlib import Path

# (!!!) [추가] ChromaDB 클라이언트를 직접 임포트합니다 (진단용)
import chromadb

from langchain_community.vectorstores import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnablePassthrough

CHROMA_DIR = './chroma_db'
EMBED_MODEL = "text-embedding-004" 
LLM_MODEL = "gemini-2.5-flash" 

# --- [시작] Streamlit 앱 설정 ---
st.set_page_config(
    page_title="어르신 복지 챗봇",
    page_icon="👵",
    layout="centered",
)
st.title("👵 어르신 건강복지 챗봇")

# --- [수정] API 키 로드 및 OS 환경변수 설정 ---
# secrets.toml에서 API 키를 로드합니다.
api_key = st.secrets.get("GOOGLE_API_KEY")

if api_key:
    # LangChain 및 Google 라이브러리가 읽을 수 있도록 OS 환경변수에 설정
    os.environ["GOOGLE_API_KEY"] = api_key
else:
    # API 키가 없는 경우 사용자에게 명확히 알리고 앱 중지
    st.error("Google API 키를 .streamlit/secrets.toml 파일에 설정해주세요.")
    st.stop()


# --- [수정] 헬퍼 함수 (Pickle 오류 방지를 위해 Top-level로 이동) ---

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

# -----------------------------
# 1. DB 로드 전용 함수 (캐싱 적용 및 진단 코드 강화)
# -----------------------------
@st.cache_resource
def load_vectorstore():
    """
    Streamlit 앱 실행 시 단 한 번만 ChromaDB를 로드합니다.
    (!!!) DB 손상 여부를 진단하는 코드가 포함되어 있습니다. (!!!)
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
        # (Chroma.from_documents는 기본적으로 'langchain' 컬렉션을 사용합니다)
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
        # (진단이 끝났으므로, LangChain이 사용할 수 있도록 객체를 생성)
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


# -----------------------------
# 2. RAG 체인 생성 함수 (캐싱 적용)
# -----------------------------
@st.cache_resource
def make_rag_chain(_vectordb): # _vectordb 인자를 받아 캐시가 인식하도록 함
    """
    DB 로더(retriever)와 LLM을 묶어 RAG 체인을 생성합니다.
    """
    # (!!!) [최종 수정] 
    # 1. k=10 으로 검색 범위 확장
    # 2. search_type="mmr" 로 설정하여 검색 결과의 '다양성' 확보
    retriever = _vectordb.as_retriever(
        search_type="mmr", 
        search_kwargs={"k": 10}
    )

    system_prompt = """당신은 한국어로 답하는 노인 건강 및 복지 전문 어시스턴트입니다.
다음 규칙을 지키세요:
- 가능한 한 제공된 근거(맥락)에 기반하여 간결/정확하게 답하세요.
- 숫자/제도명 등은 원문 표현을 최대한 보존하세요.
- 모르면 모른다고 말하세요. (추측 금지)
- 당신이 상대하는 사용자는 연령대가 높은 노인분들이나 노인복지 종사자이니 최대한 상냥하고 친절하게 답하세요.
- 사용자를 호칭할 때 '사용자님' 이라고 정중하게 부르세요.
- 사용자가 건강이나 복지 관련 질문이 아닌 다른 질문을 할 경우 부드럽게 거절하세요.
"""

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "질문: {question}\n\n다음은 검색된 문서 조각입니다:\n{context}"),
        ]
    )

    llm = ChatGoogleGenerativeAI(
        model=LLM_MODEL,
        temperature=0.2, # 답변의 창의성 조절 (낮을수록 사실 기반)
    )

    # --- [수정] LCEL 체인 (Pickle, | 연산자 오류 해결) ---

    # 1. retriever가 질문(question)을 받아 문서를 검색하고,
    #    검색된 문서를 format_docs 함수로 포맷팅하여 (context, source) 튜플 생성
    retrieval_chain = RunnableLambda(
        lambda x: format_docs(retriever.invoke(x["question"]))
    )
    
    # 2. (context, source) 튜플을 받아 LLM 프롬프트에 필요한 형식으로 매핑
    formatting_chain = RunnableLambda(
        lambda tup: {"context": tup[0], "source": tup[1], "question": tup[2]}
    )

    # 3. LLM이 (context, question)을 받아 답변(answer) 생성
    prompt_chain = {
        "answer": prompt | llm | StrOutputParser(),
        "source": lambda x: x["source"] # source는 그대로 통과
    }
    
    # 4. 최종적으로 (answer, source)를 받아 add_source_to_answer로 합침
    final_chain = (
        {
            "result": retrieval_chain, # (context, source) 튜플 생성
            "question": lambda x: x["question"] # 원본 질문 통과
        }
        | RunnableLambda(lambda x: formatting_chain.invoke((x["result"][0], x["result"][1], x["question"])))
        | prompt_chain
        | RunnableLambda(add_source_to_answer)
    )
    
    return final_chain


def run_chatbot():
    """메인 챗봇 실행 로직"""

    # --- [수정] 앱 시작 시 리소스 로드 (캐시 사용) ---
    try:
        # 캐시된 함수를 호출하여 DB와 체인을 로드
        vectordb = load_vectorstore()
        chain = make_rag_chain(vectordb)
    except Exception as e:
        # 로딩 실패 시 앱 중단
        st.error(f"챗봇 로딩 중 오류 발생: {e}")
        st.stop()

    # --- [수정] 채팅 기록 초기화 ---
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # --- [수정] 채팅 기록 표시 ---
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # --- [수정] 사용자 입력 및 챗봇 응답 처리 ---
    user_question = st.chat_input("궁금하신 점을 말씀해 주세요 ! ")
    
    if user_question:
        # 1. 사용자 메시지 저장 및 표시
        st.session_state.messages.append({"role": "user", "content": user_question})
        with st.chat_message("user"):
            st.markdown(user_question)

        # 2. 어시스턴트 응답 생성
        with st.chat_message("assistant"):
            with st.spinner("답변을 생각 중입니다..."):
                try:
                    # RAG 체인 호출
                    answer = chain.invoke({"question": user_question})
                except Exception as e:
                    answer = f"답변을 생성하는 중 오류가 발생했습니다: {e}"

                # 3. 어시스턴트 메시지 저장 및 표시
                st.session_state.messages.append({"role": "assistant", "content": answer})
                st.markdown(answer)

if __name__ == '__main__':
    run_chatbot()

