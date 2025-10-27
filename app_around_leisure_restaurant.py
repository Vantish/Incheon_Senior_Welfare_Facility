import pandas as pd
import streamlit as st
from app_location import run_location
from geopy.distance import geodesic
from define import _find_lat_lon_cols, _ensure_coord_aliases, _standardize_restaurant_columns, _standardize_leisure_columns


# app_location 부분에서 입력받은 사용자의 위치정보를 통해
# 계산된 시설의 위치정보(facilities_location)를 활용하여
# 시설에서 가장 가까운 식당 / 여가시설을 20개씩 반환합니다.


# 맛집/시설 데이터
맛집_df = pd.read_csv('./data/인천광역시 식당 현황.csv', encoding='euc-kr')
시설_df = pd.read_csv('./data/인천광역시 시설 현황.csv', encoding='CP949')


# helper utilities are provided by define.py: _find_lat_lon_cols, _ensure_coord_aliases,
# _standardize_restaurant_columns, _standardize_leisure_columns


def around_restaurant(facilities_location):
	"""Given facilities_location=(lat, lon), return top-20 nearest restaurants as DataFrame.

	Returned DataFrame includes at least: '상호', '도로명 주소', '거리(km)', 'lat', 'lon' and many coordinate aliases.
	"""
	if facilities_location is None:
		return pd.DataFrame()
	try:
		base_lat = float(facilities_location[0])
		base_lon = float(facilities_location[1])
	except Exception:
		return pd.DataFrame()

	if 맛집_df is None or 맛집_df.empty:
		return pd.DataFrame()

	df = _standardize_restaurant_columns(맛집_df)
	lat_col, lon_col = _find_lat_lon_cols(df)
	if lat_col is None or lon_col is None:
		# try common guesses
		if 'lat' in df.columns and 'lon' in df.columns:
			lat_col, lon_col = 'lat', 'lon'
		else:
			return pd.DataFrame()

	df = _ensure_coord_aliases(df, lat_col, lon_col)

	# compute distances
	def _safe_dist(r):
		a = r['lat']
		b = r['lon']
		if pd.isna(a) or pd.isna(b):
			return pd.NA
		try:
			return geodesic((base_lat, base_lon), (float(a), float(b))).km
		except Exception:
			return pd.NA

	df['거리(km)'] = df.apply(_safe_dist, axis=1)

	res = df.dropna(subset=['거리(km)']).sort_values('거리(km)').head(20).copy()

	# ensure required columns exist
	for c in ['상호', '도로명 주소', 'lat', 'lon']:
		if c not in res.columns:
			res[c] = pd.NA

	# Keep commonly used columns plus aliases so app_map can find lat/lon by different names
	keep = ['상호', '도로명 주소', '거리(km)', 'lat', 'lon', '위도', '경도', 'latitude', 'longitude', 'lot']
	present = [c for c in keep if c in res.columns]
	return res[present]


def around_leisure(facilities_location):
	"""Given facilities_location=(lat, lon), return top-20 nearest leisure facilities as DataFrame.

	Returned DataFrame includes at least: '이름' (or '시설명'), '도로명 주소', '시설분류', '거리(km)', 'lat', 'lon' and coordinate aliases.
	"""
	if facilities_location is None:
		return pd.DataFrame()
	try:
		base_lat = float(facilities_location[0])
		base_lon = float(facilities_location[1])
	except Exception:
		return pd.DataFrame()

	if 시설_df is None or 시설_df.empty:
		return pd.DataFrame()

	df = _standardize_leisure_columns(시설_df)
	lat_col, lon_col = _find_lat_lon_cols(df)
	if lat_col is None or lon_col is None:
		if 'lat' in df.columns and 'lon' in df.columns:
			lat_col, lon_col = 'lat', 'lon'
		else:
			return pd.DataFrame()

	df = _ensure_coord_aliases(df, lat_col, lon_col)

	def _safe_dist(r):
		a = r['lat']
		b = r['lon']
		if pd.isna(a) or pd.isna(b):
			return pd.NA
		try:
			return geodesic((base_lat, base_lon), (float(a), float(b))).km
		except Exception:
			return pd.NA

	df['거리(km)'] = df.apply(_safe_dist, axis=1)

	res = df.dropna(subset=['거리(km)']).sort_values('거리(km)').head(20).copy()

	# ensure required columns
	for c in ['이름', '도로명 주소', '시설분류', 'lat', 'lon']:
		if c not in res.columns:
			res[c] = pd.NA

	keep = ['이름', '시설명', '도로명 주소', '시설분류', '종류', '거리(km)', 'lat', 'lon', '위도', '경도', 'latitude', 'longitude']
	present = [c for c in keep if c in res.columns]
	return res[present]


# If run directly, quick demo via streamlit UI hook (keeps backward compatibility)
if __name__ == '__main__':
	st.title("내 위치 기반 주변 맛집/여가시설 추천")
	location_info = run_location()
	if location_info:
		lat, lon, addr, sel = location_info
		st.write("위치:", lat, lon)
		st.write("주변 맛집:")
		st.dataframe(around_restaurant((lat, lon)))
		st.write("주변 여가시설:")
		st.dataframe(around_leisure((lat, lon)))
	else:
		st.info("app_location.py의 run_location()이 위치를 반환해야 합니다.")


	
    

	
    

    



    




