import pandas as pd
import streamlit as st
from app_location import run_location
from geopy.distance import geodesic


# app_location 부분에서 입력받은 사용자의 위치정보를 통해
# 계산된 시설의 위치정보(facilities_location)를 활용하여
# 시설에서 가장 가까운 식당 / 여가시설을 20개씩 반환합니다.


# 이 코드는 인천광역시의 맛집과 여가시설 데이터를 기반으로 
# 사용자의 현재 위치에서 가까운 장소를 추천해주는 화면입니다. 

# 인천광역시의 식당 및 시설 정보를 CSV 파일에서 불러옵니다.
# 각각 다른 인코딩(euc-kr, CP949)을 사용해 한글 데이터를 안정적으로 읽습니다.

# 맛집/시설 데이터
맛집_df = pd.read_csv('./data/인천광역시 식당 현황.csv', encoding='euc-kr')
시설_df = pd.read_csv('./data/인천광역시 시설 현황.csv', encoding='CP949')

# 좌표 컬럼 자동 탐색
# 데이터프레임에서 위도/경도 컬럼명을 자동으로 찾아냅니다.
# 다양한 이름(예: 'lat', '위도', 'latitude', 'lon', '경도', 'longitude')을 고려하여 유연하게 처리합니다.

def _find_lat_lon_cols(df):
	"""이름이 발견되면 (lat_col, lon_col) 값을 반환하고, 그렇지 않으면 (None, None) 값을 반환합니다. """
	if df is None or df.shape[0] == 0:
		return None, None
	cols = list(df.columns)
	low = [c.lower() for c in cols]
	
	lat_candidates = ['lat', '위도', 'latitude']
	lon_candidates = ['lon', 'lot', '경도', 'longitude', 'lng']
	lat_col = None
	lon_col = None
	for i, c in enumerate(low):
		if lat_col is None and any(k in c for k in lat_candidates):
			lat_col = cols[i]
		if lon_col is None and any(k in c for k in lon_candidates):
			lon_col = cols[i]
		if lat_col and lon_col:
			break
		
	if lat_col is None and '위도' in cols:
		lat_col = '위도'
	if lon_col is None and '경도' in cols:
		lon_col = '경도'
	return lat_col, lon_col


# 좌표 표준화 및 별칭 생성
# 위도/경도 값을 숫자로 변환하고, 다양한 별칭 컬럼을 추가합니다.
# 예: 'lat', '위도', 'latitude', 'LAT', 'Lat' 등
# 다른 모듈에서 좌표를 쉽게 찾을 수 있도록 도와줍니다.

def _ensure_coord_aliases(df, src_lat, src_lon):
	"""Create standardized coordinate columns and many common aliases so other modules can find them.

	Always returns a copy.
	"""
	df = df.copy()
	
	try:
		df['lat'] = pd.to_numeric(df[src_lat].astype(str).str.replace(',', '').str.strip(), errors='coerce')
	except Exception:
		df['lat'] = pd.NA
	try:
		df['lon'] = pd.to_numeric(df[src_lon].astype(str).str.replace(',', '').str.strip(), errors='coerce')
	except Exception:
		df['lon'] = pd.NA
	
	aliases_lat = ['위도', 'latitude', 'LAT', 'Lat']
	aliases_lon = ['경도', 'longitude', 'LON', 'Lon', 'lot']
	for a in aliases_lat:
		if a not in df.columns:
			df[a] = df['lat']
	for a in aliases_lon:
		if a not in df.columns:
			df[a] = df['lon']
	return df


def _pick_first_column(df, candidates):
	for c in candidates:
		if c in df.columns:
			return c
	return None


# 컬럼명 표준화
# 식당 데이터에서 상호명과 주소 컬럼을 '상호', '도로명 주소'로 통일합니다.

def _standardize_restaurant_columns(df):
	df = df.copy()
	name_candidates = ['상호', '상호명', '업소명', '식당명', '업체명', '사업장명']
	addr_candidates = ['도로명 주소', '도로명주소', '주소', '소재지', '지번주소']
	name_col = _pick_first_column(df, name_candidates)
	if name_col and '상호' not in df.columns:
		df['상호'] = df[name_col]
	addr_col = _pick_first_column(df, addr_candidates)
	if addr_col and '도로명 주소' not in df.columns:
		df['도로명 주소'] = df[addr_col]
	return df

# 컬럼명 표준화
# 시설 데이터에서 이름, 주소, 시설분류 컬럼을 '이름', '도로명 주소', '시설분류'로 통일합니다.

def _standardize_leisure_columns(df):
	df = df.copy()
	name_candidates = ['이름', '시설명', '명칭']
	addr_candidates = ['도로명 주소', '도로명주소', '주소', '위치']
	type_candidates = ['시설분류', '종류', '구분']
	name_col = _pick_first_column(df, name_candidates)
	if name_col and '이름' not in df.columns:
		df['이름'] = df[name_col]
	addr_col = _pick_first_column(df, addr_candidates)
	if addr_col and '도로명 주소' not in df.columns:
		df['도로명 주소'] = df[addr_col]
	type_col = _pick_first_column(df, type_candidates)
	if type_col and '시설분류' not in df.columns:
		df['시설분류'] = df[type_col]
	return df

# 주변 맛집 추천
# 사용자의 위치 (lat, lon)을 기준으로 가장 가까운 20개 맛집을 반환합니다.
# 거리 계산은 geopy.distance.geodesic을 사용하여 실제 지리적 거리(km)를 측정합니다.
# 반환되는 데이터프레임에는 다음 컬럼이 포함됩니다
# '상호', '도로명 주소', '거리(km)', 'lat', 'lon' 및 좌표 별칭들

def around_restaurant(facilities_location):
	
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

	for c in ['상호', '도로명 주소', 'lat', 'lon']:
		if c not in res.columns:
			res[c] = pd.NA

	keep = ['상호', '도로명 주소', '거리(km)', 'lat', 'lon', '위도', '경도', 'latitude', 'longitude', 'lot']
	present = [c for c in keep if c in res.columns]
	return res[present]


# 주변 여가시설 추천
# 맛집과 동일한 방식으로 가장 가까운 20개 여가시설을 추천합니다.
# 반환 컬럼은 '이름', '도로명 주소', '시설분류', '거리(km)', 'lat', 'lon' 등

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

	for c in ['이름', '도로명 주소', '시설분류', 'lat', 'lon']:
		if c not in res.columns:
			res[c] = pd.NA

	keep = ['이름', '시설명', '도로명 주소', '시설분류', '종류', '거리(km)', 'lat', 'lon', '위도', '경도', 'latitude', 'longitude']
	present = [c for c in keep if c in res.columns]
	return res[present]


# run_location() 함수로 사용자 위치를 받아오고, 해당 위치 기반으로 맛집과 여가시설을 추천합니다.

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


	
    

	
    

    



    




