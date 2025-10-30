import streamlit as st
from google import genai
from app_around_leisure_restaurant import around_restaurant
import pandas as pd

LLM_MODEL = "gemini-2.5-flash"

def looks_like_food_request(text: str) -> bool:
    t = text.lower()
    food_keywords = ['치킨', '한식', '중식', '짜장', '짬뽕', '피자', '초밥', '일식',
                     '족발', '보쌈', '칼국수', '분식', '햄버거', '카페', '커피', '식당',
                     '맛집', '양식', '파스타', '디저트', '베이커리', '빵집']
    if '추천' in t or '먹고' in t or '먹고싶' in t or '알려줘' in t:
        return True
    for kw in food_keywords:
        if kw in t:
            return True
    return False

def _get_client():
    api_key = st.secrets.get("GEMINI_API_KEY_mj")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)

def _generate_reply(client, model, prompt):
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
        )
        return getattr(response, "text", str(response))
    except Exception as e:
        print(f"Error: {e}")
        return "죄송합니다. 일시적 오류입니다. 잠시 후 다시 시도해주세요."

# Gemini API 스트리밍 함수
def stream_gemini_response(client, model, prompt):
    response_stream = client.models.generate_content_stream(model=model, contents=prompt)
    full_response = ""
    placeholder = st.empty()  # 텍스트 보여줄 자리
    for chunk in response_stream:
        if chunk.text is not None:
            full_response += chunk.text
        placeholder.markdown(full_response)  # 부분 텍스트 실시간 업데이트
    return full_response

# 추천 함수
def generate_food_recommendation(client, user_input, user_loc):
    latlon = (user_loc[0], user_loc[1])
    df_rec = around_restaurant(latlon)

    if df_rec is None or df_rec.empty:
        return '해당 위치 주변에서 추천할 만한 식당을 찾지 못했습니다.'

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
        "식당의 주소는 식당 목록에서 찾아서 알려주세요.\n"
        "식당의 주소를 물어 봤을 때, 목록에서 찾거나 인터넷 검색 후 알려드릴지 물어봐 주세요.\n"
        "목록에 없는 식당이나 음식이 검색되면 인터넷으로 추가 검색 여부를 문의하세요.\n"
        "사용자 질문이 끝나기 전에 더 궁금한 점이 있는지 다시 질문 유도하세요."
        "검색이 늦어진다면 '검색이 늦어지고 있습니다'라고 말해줘.\n "
        "건물 주소나 이름을 입력하면 '건물 위주 검색은 아직 준비 중 입니다'라고 말해주세요.\n"
    )
    prompt = system_instruction + "\n식당 목록:\n" + context_text + "\n\n질문: " + user_input

    # 스트리밍 호출
    reply = stream_gemini_response(st.session_state.client, LLM_MODEL, prompt)

    return reply

# 일반 답변 함수 (스트리밍 적용 없음)
def stream_general_reply(client, messages):
    system_instruction = (
        "당신은 어르신(노년층)을 대상으로 상냥하고 친절한 말투로 응답하는 상담 도우미입니다. "
        "존댓말을 사용하고, 천천히, 친절하게 설명하세요. 어려운 용어는 쉬운 말로 풀어 설명하고, "
        "한 번에 한 가지 정보를 제공하며 배려심 있고 공손한 표현을 사용하세요."
        "답변할때 어르신 보다는 사용자님 을 쓰되 친근하게 대답해주세요."
        "검색 지역은 '인천' 으로 한정합니다"
        "모르는건 모른다고 답하세요"
        "식당의 주소를 식당 목록에서 찾고 인터넷에서 검색해서 달라진 부분이 있다면 알려주세요."
        "추천 목록에 없는 식당이나 음식을 물어볼때는 최근 검색한 식당 위치 기준으로 답변하세요."
        "건물 주소나 이름을 입력하면 '건물 위주 검색은 아직 준비 중 입니다'라고 말해주세요."
    )
    conversation_text = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
    prompt = system_instruction + "\n\n" + conversation_text

    response_stream = client.models.generate_content_stream(model=LLM_MODEL, contents=prompt)

    full_text = ""
    placeholder = st.empty()
    for chunk in response_stream:
        full_text += chunk.text
        placeholder.markdown(full_text)

    return full_text

def run_chatbot_app():
    st.markdown(
    "<h3 style='color: orange;'>사용자 근처의 식당을 추천해주는 AI💻</h3>", 
    unsafe_allow_html=True
)
    st.text("📍 찾아보고 싶은 식당 또는 음식을 말씀해주세요 : 예) 여기 근처 중식당 찾아줘")

    # 위치 변경 시 메시지 초기화
    prev_loc = st.session_state.get("prev_user_location")
    current_loc = st.session_state.get("user_location")
    if current_loc != prev_loc:
        st.session_state.messages = [
            {"role": "assistant", "content": "안녕하세요! 무엇을 도와드릴까요?"}
        ]
        st.session_state["prev_user_location"] = current_loc

    # 클라이언트 초기화
    client = _get_client()
    if not client:
        st.error("GEMINI_API_KEY가 설정되어 있지 않습니다.")
        return
    st.session_state.client = client  # 글로벌 저장 (필요시)

    # UI 출력
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.chat_message("user").write(msg["content"])
        else:
            st.chat_message("assistant").write(msg["content"])

    # 위치 미입력 시 경고
    if not st.session_state.get("user_location"):
        st.warning("2번 파일에서 위치를 먼저 입력하세요.")

    # 사용자 입력 받기
    with st.expander('검색창 입니다', expanded=True):
        user_input = st.chat_input("=>여기에 입력하세요")
        if user_input and user_input.strip() != "":
            st.session_state.messages.append({"role": "user", "content": user_input})
            if looks_like_food_request(user_input):
                user_loc = st.session_state.get('user_location')
                if not user_loc:
                    st.session_state.messages.append({"role": "assistant", "content": "먼저 위치를 입력하세요."})
                    return
                reply = generate_food_recommendation(st.session_state.client, user_input, user_loc)
                st.session_state.messages.append({"role": "assistant", "content": reply})
            else:
                reply = stream_general_reply(st.session_state.client, st.session_state.messages)
                st.session_state.messages.append({"role": "assistant", "content": reply})

if __name__ == '__main__':
    run_chatbot_app()
