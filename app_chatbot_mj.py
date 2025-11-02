import streamlit as st
import google.generativeai as genai
from app_around_leisure_restaurant import around_restaurant
import pandas as pd

LLM_MODEL = "gemini-2.5-flash"

def _get_client():
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key:
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(LLM_MODEL)

def _generate_reply(client, contents):
    response = client.generate_content(
        contents=contents
    )
    return getattr(response, "text", str(response))

def looks_like_food_request(text: str) -> bool:
    t = text.lower()
    food_keywords = ['치킨', '한식', '중식', '짜장', '짬뽕', '피자', '초밥', '일식', 
                     '족발', '보쌈', '칼국수', '분식', '햄버거', '카페', '커피', '식당', 
                     '맛집', '양식', '파스타', '디저트', '베이커리', '빵집', '삼겹살', '갈비',
                     '케이크', '면요리', '면류', '밥류', '국물', '탕', '찌개', '고기']
    if '추천' in t or '먹고' in t or '먹고싶' in t or '알려줘' in t or '찾아줘' in t or '찾고싶' in t:
        return True
    for kw in food_keywords:
        if kw in t:
            return True
    return False

def run_chatbot_app():
    prev_loc = st.session_state.get("prev_user_location")
    current_loc = st.session_state.get("user_location")

    st.subheader("사용자 근처의 식당을 추천해드립니다")
    st.text("찾아보고 싶은 식당 또는 음식을 말씀해주세요 : 예) 내 위치 근처 식당 추천해줘")

    if current_loc != prev_loc:
        st.session_state.messages = [
            {"role": "assistant", "content": "안녕하세요! 무엇을 도와드릴까요?"}
        ]
        st.session_state["prev_user_location"] = current_loc

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

    with st.expander('검색창 입니다', expanded=True):
        user_input = st.chat_input("=>여기에 입력해주세요 ")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})

        if looks_like_food_request(user_input):
            user_loc = st.session_state.get('user_location')
            if not user_loc:
                st.session_state.messages.append({"role": "assistant", "content": "위치를 먼저 입력해주세요."})
            else:
                latlon = (user_loc[0], user_loc[1])
                df_rec = around_restaurant(latlon)
                if df_rec is None or df_rec.empty:
                    assistant_text = '해당 위치 주변에서 추천할 만한 식당을 찾지 못했습니다.'
                    st.session_state.messages.append({"role": "assistant", "content": assistant_text})
                else:
                    lines = []
                    for i, row in df_rec.head(20).iterrows():
                        name = row.get('상호', '')
                        addr = row.get('도로명 주소', '')
                        dist = row.get('거리(km)')
                        dist_text = f"{dist:.2f}km" if pd.notna(dist) else ''
                        lines.append(f"[{i+1}] {name} / {addr} / {dist_text}")

                    context_text = "\n".join(lines)

                    system_instruction = (
                        "제공된 식당 추천 목록 정보 위주로 참고하여 사용자 질문에 답변하세요.\n"
                        "중복된 내용이 있다면 한번만 출력 해주세요\n"
                        "추천 목록에 없는 정보는 추측하지 말고 '추천 목록에 없습니다'라고 응답하세요.\n"
                        "사용자가 음식이름을 입력했을 때 식당명과 식당 설명을 이용해서 같은 음식 이름이 들어간 곳 위주로 추천해주세요.\n"
                        "식당의 주소는 식당 추천 목록에서 찾아서 알려주세요.\n"
                        "식당의 주소를 물어 봤을 때, 추천 목록에서 찾거나 검색 후 알려드릴지 물어봐 주세요.\n"
                        "목록에 없는 식당이나 음식, 주소가 검색되면 gemini이가 자체적으로 검색 해서 알려주되, 입력된 사용자위치의 근처 5km 반경 안에서만 알려주세요.\n"
                        "사용자 질문이 끝나기 전에 더 궁금한 점이 있는지 다시 질문 유도하세요."
                        "검색이 늦어진다면 '검색이 늦어지고 있습니다'라고 말해줘.\n"
                        "건물 주소나 이름을 입력하면 '건물 위주 검색은 아직 준비 중 입니다'라고 말해주세요.\n"
                        "추천된 식당이 어떤 음식을 파는 식당인지 물어보면 찾아서 알려주세요"
                        "거짓말하지 않고,없는 답변을 만들어내지 마세요"
                    )
                    prompt = system_instruction + "\n식당 목록:\n" + context_text + "\n\n질문: " + user_input

                    with st.spinner('추천 기반으로 응답 생성 중...'):
                        try:
                            reply_text = _generate_reply(client, prompt)
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
                "식당의 주소를 식당 목록에서 찾고 gemini가 찾아보고 달라진 부분이 있다면 알려주세요."
                "추천 목록에 없는 식당이나 음식은 찾아서 최근 정보를 알려주세요"
                "거짓말하지 않고, 없는 답변을 만들어내지 마세요"
            )
            conversation_text = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
            prompt = system_instruction + "\n\n" + conversation_text

            with st.spinner("검색 응답 생성 중..."):
                try:
                    reply_text = _generate_reply(client, prompt)
                except Exception as e:
                    reply_text = f"오류가 발생했습니다: {e}"

            st.session_state.messages.append({"role": "assistant", "content": reply_text})

        st.rerun()


if __name__ == '__main__':
    run_chatbot_app()
