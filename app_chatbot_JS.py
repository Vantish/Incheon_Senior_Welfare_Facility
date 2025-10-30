import os
from pathlib import Path
import streamlit as st
from google import genai
from google.genai import types

from define import (
    load_allowed_corpus,
    build_tfidf_index,
    retrieve_tfidf_contexts,
    build_system_prompt,
)


DATA_DIR = Path(__file__).parent.joinpath('data')


@st.cache_data(show_spinner=False)
def _load_and_index():
    docs = load_allowed_corpus(str(DATA_DIR))
    if not docs:
        return None
    idx = build_tfidf_index(docs)
    return idx


def _parse_genai_response(resp):
    # SDK 응답 형식이 버전마다 달라서 안전하게 추출
    try:
        if resp is None:
            return ''
        if hasattr(resp, 'candidates') and len(resp.candidates) > 0:
            c = resp.candidates[0]
            # 후보의 content가 문자열일 수 있음
            if hasattr(c, 'content'):
                if isinstance(c.content, str):
                    return c.content
                try:
                    return str(c.content)
                except Exception:
                    return str(c)
        if hasattr(resp, 'text'):
            return resp.text
        return str(resp)
    except Exception:
        return str(resp)


def run_chatbot():
    st.set_page_config(page_title='노인건강 챗봇', layout='wide')
    st.title('노인 건강·복지 챗봇')

    # 사이드바 설정
    with st.sidebar:
        st.header('설정')
        show_sources = st.checkbox('출처 보이기', value=True)

    user_age = st.number_input('나이 입력 (선택)', min_value=0, max_value=120, value=0, step=1)
    health_info = st.text_area('건강 관련 정보(선택): 예) 당뇨, 고혈압 등', height=80)
    query = st.text_input('질문을 입력하세요')

    st.info('자료는 data 폴더의 지정된 파일에서만 검색하여 답변합니다.')

    # 코퍼스 로드 및 인덱스 빌드 (캐시)
    idx = _load_and_index()
    if idx is None:
        st.warning('데이터 폴더에 허용된 자료가 없습니다. data/ 폴더를 확인해 주세요.')

    if st.button('질문하기'):
        if not query or query.strip() == '':
            st.warning('질문을 입력해 주세요.')
            return

        # 검색(상위 문서 추출)
        contexts = []
        if idx is not None:
            try:
                contexts = retrieve_tfidf_contexts(idx, query, top_k=5)
            except Exception:
                contexts = []

        if not contexts:
            # 최소한 도큐먼트 샘플이라도 제공
            docs = load_allowed_corpus(str(DATA_DIR))
            if docs:
                contexts = docs[:3]

        # 프롬프트 구성
        system_prompt = build_system_prompt()
        ctx_blocks = []
        for c in contexts:
            src = c.get('source') if isinstance(c, dict) else getattr(c, 'source', '')
            text = c.get('text') if isinstance(c, dict) else getattr(c, 'text', '')
            snippet = (text or '')[:1200]
            ctx_blocks.append(f"[출처: {src}]\n{snippet}")
        ctx_text = "\n\n".join(ctx_blocks)

        user_ctx = ''
        if user_age and user_age > 0:
            user_ctx += f"사용자 나이: {user_age}\n"
        if health_info and health_info.strip():
            user_ctx += f"사용자 건강정보: {health_info}\n"

        prompt_body = system_prompt + "\n\n" + "참고문서:\n" + ctx_text + "\n\n" + user_ctx + "질문: " + query + "\n\n" + "(출처를 명시하고, 문서에 없는 정보는 추가하지 마세요.)"

        # Gemini 호출: secrets 또는 환경변수에서 API 키 사용
        api_key = None
        try:
            api_key = st.secrets.get('google_api_key')
        except Exception:
            api_key = None
        if not api_key:
            api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
        if api_key:
            os.environ['GEMINI_API_KEY'] = api_key

        # 생성
        try:
            client = genai.Client()
            gen_resp = client.models.generate_content(
                model='gemini-2.5-flash-lite',
                config=types.GenerateContentConfig(system_instruction=system_prompt),
                contents=prompt_body,
            )
            answer = _parse_genai_response(gen_resp)
            st.subheader('답변')
            st.write(answer)

            if show_sources:
                st.subheader('출처')
                srcs = [c.get('source') for c in contexts if c.get('source')]
                st.write(list(dict.fromkeys([s for s in srcs if s])))
        except Exception as e:
            # Gemini 호출 실패 시 폴백: 로컬 컨텍스트 합치기
            parts = []
            for c in contexts:
                src = c.get('source') if isinstance(c, dict) else getattr(c, 'source', '')
                text = c.get('text') if isinstance(c, dict) else getattr(c, 'text', '')
                parts.append(f"[출처: {src}]\n" + (text or '')[:1500])
            fallback = "\n\n".join(parts)
            st.subheader('답변 (로컬 요약)')
            st.write(fallback)
            if show_sources:
                st.subheader('출처')
                srcs = [c.get('source') for c in contexts if c.get('source')]
                st.write(list(dict.fromkeys([s for s in srcs if s])))
    