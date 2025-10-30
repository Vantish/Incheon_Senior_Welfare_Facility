import streamlit as st
from google import genai
from app_around_leisure_restaurant import around_restaurant
from app_location import run_location
import pandas as pd

LLM_MODEL = "gemini-2.5-flash"


def _init_session():
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "안녕하세요! 무엇을 도와드릴까요?"}
        ]


def _get_client():
    api_key = st.secrets.get("GEMINI_API_KEY_mj")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


def _generate_reply(client, model, prompt):
    response = client.models.generate_content(
        model=model,
        contents=prompt,
    )
    return getattr(response, "text", str(response))


# 간단한 음식/식당 추천 의도 판단 함수
def looks_like_food_request(text: str) -> bool:
    t = text.lower()
    food_keywords = ['치킨', '한식', '중식', '짜장', '짬뽕', '피자', '초밥', '일식', '족발', '보쌈', '칼국수', '분식', '햄버거', '카페', '커피', '식당', '맛집']
    if '추천' in t or '먹고' in t or '먹고싶' in t:
        return True
    for kw in food_keywords:
        if kw in t:
            return True
    return False


def run_chatbot_app():
    _init_session()

    st.subheader("사용자 근처의 식당을 추천해드립니다")
    st.subheader("찾아보고 싶은 식당 또는 음식을 말씀해주세요 :")

    client = _get_client()
    if client is None:
        st.error("GEMINI_API_KEY가 설정되어 있지 않습니다. Streamlit secrets에 GEMINI_API_KEY를 추가하세요.")
        st.info("설정 예: .streamlit/secrets.toml 에 `GEMINI_API_KEY = \"your_api_key\"` 추가")
        return

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.chat_message("user").write(msg["content"])
        else:
            st.chat_message("assistant").write(msg["content"])

    loc = st.session_state.get("user_location", None)
    if not loc:
        st.warning("2번 파일에서 위치를 먼저 입력해주세요.")

    with st.expander('검색창 입니다', expanded=True):
        user_input = st.chat_input("=>여기에 입력해주세요 ")
        if user_input:
            st.session_state.messages = [
                {"role": "assistant", "content": "안녕하세요! 무엇을 도와드릴까요?"}
            ]
            st.session_state.messages.append({"role": "user", "content": user_input})

            if looks_like_food_request(user_input):
                user_loc = st.session_state.get('user_location')
                if not user_loc:
                    st.session_state.messages.append({"role": "assistant", "content": assistant_text})

                latlon = (user_loc[0], user_loc[1])
                df_rec = around_restaurant(latlon)
                if df_rec is None or df_rec.empty:
                    assistant_text = '해당 위치 주변에서 추천할 만한 식당을 찾지 못했습니다.'
                    st.session_state.messages.append({"role": "assistant", "content": assistant_text})

                lines = []
                for i, row in df_rec.head(20).iterrows():
                    name = row.get('상호', '')
                    addr = row.get('도로명 주소', '')
                    dist = row.get('거리(km)')
                    dist_text = f"{dist:.2f}km" if pd.notna(dist) else ''
                    lines.append(f"[{i + 1}] {name} / {addr} / {dist_text}")

                context_text = "\n".join(lines)

                system_instruction = (
                    "아래 제공된 식당 목록 정보만을 참고하여 사용자 질문에 답변하세요.\n"
                    "목록에 없는 정보는 추측하지 말고 '목록에 없습니다'라고 응답하세요.\n"
                    "식당의 주소는 식당 목록에서 찾아서 알려주세요.\n"
                    "사용자가 음식이름을 입력했을 때 식당명과 식당 설명을 이용해서 같은 음식 이름이 들어간 곳을 추천해주세요.\n"
                    "식당의 주소를 식당 목록에서 찾고 인터넷에서 검색해서 달라진 부분이 있다면 알려주세요.\n"
                    "중복된 내용이 있다면 한번만 출력 해주세요\n"
                )
                prompt = system_instruction + "\n식당 목록:\n" + context_text + "\n\n질문: " + user_input

                with st.spinner('추천 기반으로 응답 생성 중...'):
                    try:
                        reply_text = _generate_reply(client, LLM_MODEL, prompt)
                    except Exception as e:
                        reply_text = f'응답 생성 중 오류가 발생했습니다: {e}'

                st.session_state.messages.append({"role": "assistant", "content": reply_text})

        else:
            system_instruction = (
                "당신은 어르신(노년층)을 대상으로 상냥하고 친절한 말투로 응답하는 상담 도우미입니다. "
                "존댓말을 사용하고, 천천히, 친절하게 설명하세요. 어려운 용어는 쉬운 말로 풀어 설명하고, "
                "한 번에 한 가지 정보를 제공하며 배려심 있고 공손한 표현을 사용하세요."
                "답변할때 어르신 보다는 사용자님 을 쓰되 친근하게 대답해주세요."
                "검색 지역은 '인천' 으로 한정합니다"
                "모르는건 모른다고 답하세요"
                "식당의 주소를 식당 목록에서 찾고 인터넷에서 검색해서 달라진 부분이 있다면 알려주세요.\n"
            )
            conversation_text = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
            prompt = system_instruction + "\n\n" + conversation_text

            with st.spinner("응답 생성 중..."):
                try:
                    reply_text = _generate_reply(client, LLM_MODEL, prompt)
                except Exception as e:
                    reply_text = f"오류가 발생했습니다: {e}"

            st.session_state.messages.append({"role": "assistant", "content": reply_text})



if __name__ == '__main__':
    run_chatbot_app()
