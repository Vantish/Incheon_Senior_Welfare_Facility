import streamlit as st
import pandas as pd
import os
from app_location import run_location
from geopy.distance import geodesic


# app_location 부분에서 입력받은 사용자의 위치정보를 통해
# 계산된 시설의 위치정보(facilities_location)를 활용하여
# 시설에서 가장 가까운 식당 / 여가시설을 20개씩 반환합니다.

# 맛집 추천 함수
def around_restaurant(facilities_location):
    lat, lon = facilities_location
    
    # lat/lon 칼럼 찾기
    cols = [c for c in 맛집_df.columns]
    lat_col = next((c for c in cols if 'lat' in c.lower()), None)
    lon_col = next((c for c in cols if 'lon' in c.lower() or 'lot' in c.lower()), None)
    
    if lat_col is None or lon_col is None:
        return pd.DataFrame()  # 빈 데이터프레임 반환
    
    # 거리 계산
    맛집_df['거리(km)'] = 맛집_df.apply(
        lambda row: geodesic((lat, lon), (row[lat_col], row[lon_col])).km if pd.notnull(row[lat_col]) and pd.notnull(row[lon_col]) else None,
        axis=1
    )

    # 가까운 순으로 정렬 후 상위 20개
    result = 맛집_df.dropna(subset=['거리(km)']).sort_values('거리(km)').head(20)
    
    # 지도 표시를 위한 lat/lon 칼럼 추가
    result['lat'] = result[lat_col]
    result['lon'] = result[lon_col]
    
    # 필요한 컬럼만 반환 (상호 = 식당명)
    cols_to_return = ['상호', '도로명 주소', '거리(km)', 'lat', 'lon']
    renamed_cols = {
        '상호': '식당명',
        '도로명 주소': '도로명 주소'
    }
    
    return result[cols_to_return].rename(columns=renamed_cols)


# 여가시설 추천 함수
def around_leisure(facilities_location):
    lat, lon = facilities_location
    
    # lat/lon 칼럼 찾기
    cols = [c for c in 시설_df.columns]
    lat_col = next((c for c in cols if 'lat' in c.lower()), None)
    lon_col = next((c for c in cols if 'lon' in c.lower() or 'lot' in c.lower()), None)
    
    if lat_col is None or lon_col is None:
        return pd.DataFrame()  # 빈 데이터프레임 반환

    # 거리 계산
    시설_df['거리(km)'] = 시설_df.apply(
        lambda row: geodesic((lat, lon), (row[lat_col], row[lon_col])).km if pd.notnull(row[lat_col]) and pd.notnull(row[lon_col]) else None,
        axis=1
    )

    result = 시설_df.dropna(subset=['거리(km)']).sort_values('거리(km)').head(20)
    
    # 지도 표시를 위한 lat/lon 칼럼 추가
    result['lat'] = result[lat_col]
    result['lon'] = result[lon_col]
    
    # 필요한 컬럼만 반환 (이름 = 시설명)
    cols_to_return = ['이름', '도로명 주소', '시설분류', '거리(km)', 'lat', 'lon']
    renamed_cols = {
        '이름': '시설명',
        '시설분류': '종류'
    }
    
    return result[cols_to_return].rename(columns=renamed_cols)

# 노인복지시설 데이터
df = pd.read_csv('./data/인천광역시_노인복지시설_현황.csv', encoding='euc-kr')

# 맛집/시설 데이터
맛집_df = pd.read_csv(
    './data/인천광역시 식당 현황.csv',
    encoding='euc-kr',
    on_bad_lines='skip'
)

시설_df = pd.read_csv(
    './data/인천광역시 시설 현황.csv',
    encoding='CP949'
)


st.title("위치 기반 시설 추천")

location_info = run_location()

if location_info:
    lat, lon, address, selected_type = location_info

    st.success(f"선택한 주소: {address}")
    st.write(f"위도: {lat}, 경도: {lon}")
    st.write(f"선택한 시설유형: {selected_type}")

    # 예: 이 위치에서 가까운 맛집/여가시설 추천 함수 호출
    restaurant_df = around_restaurant((lat, lon))
    leisure_df = around_leisure((lat, lon))

    st.markdown("#### 근처 맛집")
    st.dataframe(restaurant_df)

    st.markdown("#### 근처 여가시설")
    st.dataframe(leisure_df)
else:
    st.info("위치 정보를 입력하고 '입력' 버튼을 눌러주세요.")


# 맛집 추천 함수
def around_restaurant(facilities_location):
    lat, lon = facilities_location

    # 거리 계산
    맛집_df['거리(km)'] = 맛집_df.apply(
        lambda row: geodesic((lat, lon), (row['lat'], row['lot'])).km if pd.notnull(row['lat']) and pd.notnull(row['lot']) else None,
        axis=1
    )

    # 가까운 순으로 정렬 후 상위 20개
    result = 맛집_df.dropna(subset=['거리(km)']).sort_values('거리(km)').head(20)

    # 필요한 컬럼만 반환
    return result[['식당명', '도로명 주소', '거리(km)']]


# 여가시설 추천 함수
def around_leisure(facilities_location):
    lat, lon = facilities_location

    시설_df['거리(km)'] = 시설_df.apply(
        lambda row: geodesic((lat, lon), (row['lat'], row['lon'])).km if pd.notnull(row['lat']) and pd.notnull(row['lon']) else None,
        axis=1
    )

    result = 시설_df.dropna(subset=['거리(km)']).sort_values('거리(km)').head(20)

    return result[['시설명', '도로명 주소', '종류', '거리(km)']]
    




