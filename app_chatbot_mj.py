import streamlit as st
from google import genai
from app_around_leisure_restaurant import around_restaurant
from app_location import run_location
import pandas as pd

df = pd.read_csv('./data/인천식당_카테고리_수정.csv',encoding='euc-kr')

st.set_page_config(page_title="Gemini Chat", page_icon="🤖")

LLM_MODEL = "gemini-2.5-flash"  # 모델명 지정


def _init_session():
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "안녕하세요! 무엇을 도와드릴까요?"}
        ]


def _get_client():
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


def _generate_reply(client, model, prompt):
    response = client.models.generate_content(
        model=model,
        contents=prompt,
    )
    return getattr(response, "text", str(response))


def main():
    _init_session()

    st.title("사용자 근처의 식당을 추천해드립니다")
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

    # 사이드바: 위치 입력(도로명 주소)을 받아 세션에 저장
    with st.sidebar.expander('내 위치(도로명 주소) 입력'):
        loc = run_location()
        if loc is not None:
            st.session_state['user_location'] = loc
            st.success('위치가 저장되었습니다. 메인 창에서 질문해 주세요.')

    user_input = st.chat_input("여기에 입력해주세요 ")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})

        # 간단한 음식/식당 추천 의도 판단
        def looks_like_food_request(text: str) -> bool:
            t = text.lower()
            food_keywords = ['치킨','한식','중식','짜장','짬뽕','피자','초밥','일식','족발','보쌈','칼국수','분식','햄버거','카페','커피','식당','맛집']
            if '추천' in t or '먹고' in t or '먹고싶' in t:
                return True
            for kw in food_keywords:
                if kw in t:
                    return True
            return False

        if looks_like_food_request(user_input):
            user_loc = st.session_state.get('user_location')
            if not user_loc:
                assistant_text = '맛집 추천을 위해 사이드바에서 도로명 주소를 입력하고 입력 버튼을 눌러 위치를 저장해 주세요.'
                st.session_state.messages.append({"role": "assistant", "content": assistant_text})
                st.rerun()

            # user_loc expected [lat, lon, address, selected_type]
            latlon = (user_loc[0], user_loc[1])
            df_rec = around_restaurant(latlon)
            if df_rec is None or df_rec.empty:
                assistant_text = '해당 위치 주변에서 추천할 만한 식당을 찾지 못했습니다.'
                st.session_state.messages.append({"role": "assistant", "content": assistant_text})
                st.rerun()

            # build context list from df_rec (limit to 20 rows)
            lines = []
            for i, row in df_rec.head(20).iterrows():
                name = row.get('상호','')
                addr = row.get('도로명 주소','')
                dist = row.get('거리(km)')
                dist_text = f"{dist:.2f}km" if pd.notna(dist) else ''
                lines.append(f"[{i+1}] {name} / {addr} / {dist_text}")

            context_text = "\n".join(lines)

            # instruct LLM to answer using only this list
            system_instruction = (
                "아래 제공된 식당 목록 정보만을 참고하여 사용자 질문에 답변하세요.\n"
                "목록에 없는 정보는 추측하지 말고 '목록에 없습니다'라고 응답하세요.\n"
            )
            prompt = system_instruction + "\n식당 목록:\n" + context_text + "\n\n질문: " + user_input

            with st.spinner('추천 기반으로 응답 생성 중...'):
                try:
                    reply_text = _generate_reply(client, LLM_MODEL, prompt)
                except Exception as e:
                    reply_text = f'응답 생성 중 오류가 발생했습니다: {e}'

            st.session_state.messages.append({"role": "assistant", "content": reply_text})
            st.rerun()

        system_instruction = (
            "당신은 어르신(노년층)을 대상으로 상냥하고 친절한 말투로 응답하는 상담 도우미입니다. "
            "존댓말을 사용하고, 천천히, 친절하게 설명하세요. 어려운 용어는 쉬운 말로 풀어 설명하고, "
            "한 번에 한 가지 정보를 제공하며 배려심 있고 공손한 표현을 사용하세요."
            "답변할때 어르신 보다는 사용자님 을 쓰되 친근하게 대답해주세요."
            "검색 지역은 '인천' 으로 한정합니다"
        )
        conversation_text = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
        prompt = system_instruction + "\n\n" + conversation_text

        with st.spinner("응답 생성 중..."):
            try:
                reply_text = _generate_reply(client, LLM_MODEL, prompt)
            except Exception as e:
                reply_text = f"오류가 발생했습니다: {e}"

        st.session_state.messages.append({"role": "assistant", "content": reply_text})
        st.rerun()


if __name__ == '__main__':
    main()