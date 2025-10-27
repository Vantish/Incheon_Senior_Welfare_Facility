import pandas as pd
import streamlit as st
import os
from app_location import run_location
from geopy.distance import geodesic
import folium
import streamlit.components.v1 as components
from html import escape





# app_location 부분에서 입력받은 사용자의 위치정보를 통해
# 계산된 시설의 위치정보(facilities_location)를 활용하여
# 시설에서 가장 가까운 식당 / 여가시설을 20개씩 반환합니다.


def _load_csv(path, encodings=("euc-kr", "cp949", "utf-8")):
	"""Try multiple encodings and return a DataFrame or empty DataFrame on failure."""
	if not os.path.exists(path):
		return pd.DataFrame()
	for enc in encodings:
		try:
			return pd.read_csv(path, encoding=enc, on_bad_lines='skip')
		except Exception:
			continue
	return pd.DataFrame()


# 데이터 로드 (상대 경로 사용)
맛집_df = _load_csv("./data/인천광역시 식당 현황.csv")
시설_df = _load_csv("./data/인천광역시 시설 현황.csv")


def _find_lat_lon_cols(df):
	"""Return (lat_col, lon_col) names if found, else (None, None). Tries common variations."""
	if df is None or df.shape[0] == 0:
		return None, None
	cols = list(df.columns)
	low = [c.lower() for c in cols]
	# candidates
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
	# try exact matches '위도' '경도'
	if lat_col is None and '위도' in cols:
		lat_col = '위도'
	if lon_col is None and '경도' in cols:
		lon_col = '경도'
	return lat_col, lon_col


def _ensure_coord_aliases(df, src_lat, src_lon):
	"""Create standardized coordinate columns and many common aliases so other modules can find them.

	Always returns a copy.
	"""
	df = df.copy()
	# numeric conversion
	try:
		df['lat'] = pd.to_numeric(df[src_lat].astype(str).str.replace(',', '').str.strip(), errors='coerce')
	except Exception:
		df['lat'] = pd.NA
	try:
		df['lon'] = pd.to_numeric(df[src_lon].astype(str).str.replace(',', '').str.strip(), errors='coerce')
	except Exception:
		df['lon'] = pd.NA
	# aliases
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
	st.title("테스트: 위치 기반 시설 추천 (단독 실행)")
	location_info = run_location()
	if location_info:
		lat, lon, addr, sel = location_info
		st.write("위치:", lat, lon)
		st.write("근처 맛집(예):")
		st.dataframe(around_restaurant((lat, lon)))
		st.write("근처 여가시설(예):")
		st.dataframe(around_leisure((lat, lon)))
	else:
		st.info("app_location.py의 run_location()이 위치를 반환해야 합니다.")


def _make_popup_html(text, width=240):
	s = str(text)
	if '<br>' in s:
		parts = s.split('<br>')
		escaped = '<br>'.join(escape(p) for p in parts)
	else:
		escaped = escape(s).replace('\n', '<br>')
	html = f"""<div style='max-width:{width}px; white-space:normal; word-wrap:break-word; font-size:13px; line-height:1.2;'>{escaped}</div>"""
	height = 50 + max(0, (len(escaped) - width) // 3)
	return folium.Popup(folium.IFrame(html=html, width=width+20, height=height), max_width=width+20)


def show_nearby_map(facilities_location, show_restaurant=True, show_leisure=True, zoom_start=14, map_height=600):
	"""Create a folium map centered at facilities_location and add markers for nearby restaurants and leisure facilities.

	Returns the HTML representation embedded into Streamlit.
	"""
	if facilities_location is None:
		st.warning('시설 위치가 지정되지 않았습니다.')
		return
	try:
		base_lat = float(facilities_location[0])
		base_lon = float(facilities_location[1])
	except Exception:
		st.warning('facilities_location 형식이 잘못되었습니다. (lat, lon)을 전달하세요.')
		return

	fmap = folium.Map(location=[base_lat, base_lon], zoom_start=zoom_start)

	# 사용자/시설 중심 마커
	folium.Marker([base_lat, base_lon], popup=_make_popup_html('시설 위치'), icon=folium.Icon(color='red')).add_to(fmap)

	# add restaurants
	if show_restaurant:
		try:
			r_df = around_restaurant(facilities_location)
			if isinstance(r_df, pd.DataFrame) and not r_df.empty:
				for _, r in r_df.iterrows():
					try:
						rlat = float(r.get('lat') if 'lat' in r else r.get('위도', r.get('latitude')))
						rlon = float(r.get('lon') if 'lon' in r else r.get('경도', r.get('longitude', r.get('lot'))))
					except Exception:
						continue
					name = r.get('상호', r.get('식당명', '맛집'))
					addr = r.get('도로명 주소', '')
					dist = r.get('거리(km)', None)
					popup_text = name
					if addr and not pd.isna(addr):
						popup_text += f"<br>{addr}"
					if dist and not pd.isna(dist):
						popup_text += f"<br>{float(dist):.2f} km"
					folium.CircleMarker([rlat, rlon], radius=4, color='orange', popup=_make_popup_html(popup_text)).add_to(fmap)
		except Exception as e:
			st.warning('맛집 표시 중 오류: ' + str(e))

	# add leisure facilities
	if show_leisure:
		try:
			l_df = around_leisure(facilities_location)
			if isinstance(l_df, pd.DataFrame) and not l_df.empty:
				for _, r in l_df.iterrows():
					try:
						rlat = float(r.get('lat') if 'lat' in r else r.get('위도', r.get('latitude')))
						rlon = float(r.get('lon') if 'lon' in r else r.get('경도', r.get('longitude', r.get('lot'))))
					except Exception:
						continue
					name = r.get('이름', r.get('시설명', '여가시설'))
					addr = r.get('도로명 주소', '')
					typ = r.get('시설분류', r.get('종류', ''))
					dist = r.get('거리(km)', None)
					popup_text = name
					if typ and not pd.isna(typ):
						popup_text += f"<br>{typ}"
					if addr and not pd.isna(addr):
						popup_text += f"<br>{addr}"
					if dist and not pd.isna(dist):
						popup_text += f"<br>{float(dist):.2f} km"
					folium.CircleMarker([rlat, rlon], radius=4, color='purple', popup=_make_popup_html(popup_text)).add_to(fmap)
		except Exception as e:
			st.warning('여가시설 표시 중 오류: ' + str(e))

	# legend (simple)
	legend_html = '''
	 <div style="position: fixed; bottom: 50px; left: 50px; width:140px; height:80px; z-index:9999; font-size:12px;">
	  <div style="background:white; padding:6px; border:1px solid grey;">
		<b>범례</b><br>
		<i style="background:orange; width:10px; height:10px; display:inline-block; margin-right:6px;"></i>맛집<br>
		<i style="background:purple; width:10px; height:10px; display:inline-block; margin-right:6px;"></i>여가시설
	  </div>
	 </div>
	'''
	fmap.get_root().html.add_child(folium.Element(legend_html))

	fmap_html = fmap._repr_html_()
	components.html(fmap_html, height=map_height)
	
    

	
    

    



    




