import os
import streamlit as st
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain.schema import Document
from langchain_community.document_loaders import CSVLoader
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

pdf_path = ['./2025+노인보건복지사업안내(1권).pdf', './2025+노인보건복지사업안내(2권).pdf', 
            './★+2023년도+노인실태조사+보고서(최종본)★.pdf', '국민건강보험공단_건강검진정보_2024.CSV',
            './data/인천광역시_건강검진기관.csv' ]
CHROMA_DIR = './chroma_db'
EMBED_MODEL = "text-embedding-004" 
LLM_MODEL = "gemini-2.5-flash" 

os.environ["GOOGLE_API_KEY"] = st.secrets.get("GOOGLE_API_KEY")

# -----------------------------
# 1) 로더 & 청크 분할
# -----------------------------
def load_and_split(pdf_path: str | list):
    """
    입력으로 문자열(단일 파일 경로) 또는 파일 경로의 리스트를 받습니다.
    - PDF 파일: PyPDFLoader로 페이지 단위로 읽어들입니다.
    - CSV 파일: CSVLoader로 각 행(row)을 하나의 Document로 만듭니다.
    - TXT 파일: 전체를 하나의 Document로 만듭니다.
    알 수 없는 확장자는 경고하고 건너뜁니다.
    반환은 splitter로 분할된 Document 조각 리스트입니다.
    """

    # 입력을 일관되게 리스트로 처리
    paths = pdf_path if isinstance(pdf_path, (list, tuple)) else [pdf_path]
    docs = []
    for p in paths:
        p = str(p)
        suffix = Path(p).suffix.lower()
        if suffix == ".pdf":
            loader = PyPDFLoader(p)
            docs.extend(loader.load())
        elif suffix == ".csv":
            # CSV는 행 단위 Document 생성: CSVLoader 사용 권장
            try:
                try:
                    loader = CSVLoader(p, encoding="utf-8")
                    docs.extend(loader.load())
                except Exception:
                    # 로컬 Windows 인코딩 시도
                    loader = CSVLoader(p, encoding="cp949")
                    docs.extend(loader.load())
            except Exception:
                # CSVLoader를 사용할 수 없으면 안전하게 파일을 읽어 하나의 Document로 처리
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        text = f.read()
                except Exception:
                    with open(p, "r", encoding="cp949", errors="ignore") as f:
                        text = f.read()
                docs.append(Document(page_content=text, metadata={"source": p}))
        elif suffix == ".txt":
            # TXT는 전체를 하나의 Document로 취급
            try:
                with open(p, "r", encoding="utf-8") as f:
                    text = f.read()
            except Exception:
                with open(p, "r", encoding="cp949", errors="ignore") as f:
                    text = f.read()
            docs.append(Document(page_content=text, metadata={"source": p}))
        else:
            # 알 수 없는 확장자: 안전하게 건너뜀(오류 발생 가능성 방지)
            try:
                st.warning(f"Skipping unsupported file type (skipped): {p}")
            except Exception:
                print(f"Skipping unsupported file type: {p}")
            continue

    # 한국어/서식 문서 안정적 분할 설정 (기존 설정 유지)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        separators=["\n\n", "\n", " ", ""],
    )
    splits = splitter.split_documents(docs)
    return splits

# -----------------------------
# 2) 임베딩 & 벡터DB
# -----------------------------
def build_or_load_vectorstore(chunks):
    embeddings = GoogleGenerativeAIEmbeddings(model=EMBED_MODEL)
    if Path(CHROMA_DIR).exists():
        vectordb = Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)
    else:
        vectordb = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=CHROMA_DIR,
        )
    return vectordb

# -----------------------------
# 3) RAG 체인 (LangChain Expression Language)
# -----------------------------
def make_rag_chain(vectordb):
    retriever = vectordb.as_retriever(search_kwargs={"k": 5})

    system_prompt = """당신은 한국어로 답하는 노인 건강 및 복지 전문 어시스턴트입니다.
다음 규칙을 지키세요:
- 가능한 한 PDF / CSV 근거(맥락)에 기반하여 간결/정확하게 답하세요.
- 숫자/제도명 등은 원문 표현을 최대한 보존하세요.
- 모르면 모른다고 말하세요.
- 마지막에 출처로 참고한 파일명을 한줄로 말하세요.
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
        temperature=0.2,
        # 필요 시 안전 설정/토큰 한도 등 추가:
        # safety_settings={...},
    )

    def format_docs(docs):
        out = []
        for i, d in enumerate(docs, 1):
            meta = d.metadata or {}
            page = meta.get("page", "N/A")
            out.append(f"[{i}] (p.{page}) {d.page_content.strip()[:800]}")  # 미리보기 제한
        return "\n\n".join(out)

    # LCEL로 RAG 파이프라인 구성
    retriever_step = {"context": lambda x: format_docs(retriever.get_relevant_documents(x["question"])), "question": lambda x: x["question"]}
    chain = retriever_step | prompt | llm | StrOutputParser()
    return chain

def run_chatbot():
    pass




if __name__ == '__main__':
    run_chatbot()