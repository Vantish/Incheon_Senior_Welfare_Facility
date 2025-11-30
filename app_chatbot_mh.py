import os
import streamlit as st
import pandas as pd
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier

# 1. 데이터 로딩
@st.cache_data
def load_data():
    data_path = os.path.join('data', 'leisure location.csv')
    facilities = pd.read_csv(data_path, dtype=str, encoding='euc-kr')
    data_path = os.path.join('data', 'restaurant category.csv')
    restaurants = pd.read_csv(data_path, dtype=str, encoding='euc-kr')

    facilities = facilities[['시설명', '시설분류', '도로명 주소', 'lat', 'lon']].dropna()
    restaurants = restaurants[['식당명', '행정구역', '도로명 주소', 'lat', 'lon']].dropna()
    restaurants['시설분류'] = '식당'
    restaurants.rename(columns={'식당명': '시설명'}, inplace=True)

    combined = pd.concat([facilities, restaurants], ignore_index=True)
    return combined

data = load_data()

# 2. 모델 준비
le_type = LabelEncoder()
data['시설분류_encoded'] = le_type.fit_transform(data['시설분류'])

X = data[['시설분류_encoded', 'lat', 'lon']]
y = data['시설명']

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# 3. 챗봇 UI
st.title("인천 챗봇 추천 시스템")
st.markdown("원하는 시설 유형과 위치를 말해주세요. 예: `식당`, `배드민턴장`, `게이트볼장` 등")

# 대화 상태 저장
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# 사용자 입력
user_input = st.chat_input("예: 근처 식당 추천해줘")

if user_input:
    st.session_state.chat_history.append(("user", user_input))

    # 간단한 파싱 (시설분류 추출)
    import re
    match = re.search(r"(식당|맛집|공원|축구장|배드민턴장|게이트볼장|농구장|풋살장|야외운동기구|인라인스케이트장|족구장|다목적구장|국궁장|다목적운동장|테니스장|운동장|소운동장|야구장|X-게임장)", user_input)
    if match:
        facility_type = match.group(1)
        lat, lon = 37.5, 126.7  # 인천 중심 좌표 예시

        if facility_type not in le_type.classes_:
            response = f"❌ '{facility_type}'은(는) 데이터에 없는 시설 유형이에요. 가능한 유형: {list(le_type.classes_)}"
        else:
            user_type = le_type.transform([facility_type])[0]
            user_input_df = pd.DataFrame([[user_type, lat, lon]], columns=['시설분류_encoded', 'lat', 'lon'])
            user_input_scaled = scaler.transform(user_input_df)

            # KNN 추천
            knn = KNeighborsClassifier(n_neighbors=5)
            knn.fit(X_scaled, y)
            knn_indices = knn.kneighbors(user_input_scaled, return_distance=False)[0]
            knn_results = data.iloc[knn_indices][['시설명', '시설분류', '도로명 주소']]

            # 결정 트리 추천
            tree = DecisionTreeClassifier(max_depth=5)
            tree.fit(X, y)
            tree_prediction = tree.predict(user_input_df)

            # 응답 구성
            response = f"문의사항에 대한 내용을 안내해드릴게요\n"
            for _, row in knn_results.iterrows():
                response += f"- {row['시설명']} ({row['시설분류']}) @ {row['도로명 주소']}\n"

            response += f"\n추천: **{tree_prediction[0]}**"
    else:
        response = "시설 유형을 인식하지 못했어요. 예: `식당`, `축구장`, `체육시설` 등으로 입력해주세요."

    st.session_state.chat_history.append(("bot", response))


def render_message(speaker, message, avatar_url):
    if speaker == "user":
        bubble_color = "#e0f7fa"
        align = "right"
    else:
        bubble_color = "#fdebdf"
        align = "left"

    st.markdown(
        f"""
        <div style="display: flex; justify-content: {align}; margin-bottom: 10px;">
            <img src="{avatar_url}" style="width: 40px; height: 40px; border-radius: 50%; margin: 5px;" />
            <div style="background-color: {bubble_color}; padding: 10px 15px; border-radius: 15px; max-width: 70%; font-size: 16px;">
                {message}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )




# 대화 출력
for speaker, message in st.session_state.chat_history:
    if speaker == "user":
        render_message("user", message, "https://cdn-icons-png.flaticon.com/128/16683/16683419.png")
    else:
        render_message("bot", message, "https://cdn-icons-png.flaticon.com/128/6819/6819658.png")

