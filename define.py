import numpy as np
import pandas as pd
import folium
from streamlit.components.v1 import html as st_html
import math
from html import escape

# 그래프 캐시 파일 이름
GRAPH_CACHE_PATH = './incheon_graph.pkl'

import os
import pickle

try:
    import osmnx as ox
    import networkx as nx
    _OSM = True
except Exception:
    _OSM = False

def _haversine_m(a, b):
    """두 지점(a, b)의 직선 거리(m)를 반환합니다. 입력은 (lat, lon)."""
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    R = 6371000.0
    hav = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(hav))


def find_nearest_facilities(user_location, facilities_df: pd.DataFrame, return_count: int = 5, 
                            candidate_prefilter: int = 20, graph_cache_path: str = './incheon_graph.pkl') -> pd.DataFrame:
    """
    사용자의 위치와 시설 데이터프레임을 받아 가장 가까운 시설들을 반환합니다.

    - 동작 흐름:
      1) facilities_df에서 위도/경도 컬럼(lat, lon 또는 lot 등)을 자동으로 판별합니다.
      2) 직선거리(straight_dist_m)를 계산하여 candidate_prefilter 수만큼 후보를 추립니다.
      3) 캐시된 osmnx 그래프(graph_cache_path)가 존재하고 osmnx가 설치되어 있으면
         해당 그래프를 사용해 사용자->후보 간 도로기반 거리(road_dist_m)를 계산합니다.
      4) 도로거리 계산 실패 시 road_dist_m은 straight_dist_m으로 대체됩니다.
      5) road_dist_m 기준으로 오름차순 정렬한 데이터프레임을 반환합니다.

    주의: 이 함수는 UI(예: streamlit)를 직접 사용하지 않으며, 실패 시 예외를 잡아
    가능한 직선거리 기반으로 안전하게 동작합니다.
    """
    if user_location is None or facilities_df is None:
        raise ValueError('user_location과 facilities_df는 None이 될 수 없습니다.')

    # 입력 검증
    try:
        ulat = float(user_location[0])
        ulon = float(user_location[1])
    except Exception:
        raise ValueError('user_location은 (lat, lon) 형태여야 합니다.')

    df = facilities_df.copy()

    # lat/lon 컬럼 자동 판별
    cols = [c for c in df.columns]
    lat_col = next((c for c in cols if 'lat' in c.lower() or '위도' in c), None)
    lon_col = next((c for c in cols if 'lon' in c.lower() or 'lot' in c.lower() or '경도' in c), None)
    if lat_col is None or lon_col is None:
        raise ValueError('facilities_df에 lat/lon 컬럼이 없습니다. 파일 컬럼: ' + ','.join(cols))

    df = df.dropna(subset=[lat_col, lon_col]).copy()
    df[lat_col] = df[lat_col].astype(float)
    df[lon_col] = df[lon_col].astype(float)

    if df.shape[0] == 0:
        return df

    # 직선거리 계산
    df['straight_dist_m'] = df.apply(lambda r: _haversine_m((ulat, ulon), (r[lat_col], r[lon_col])), axis=1)

    # 후보 프리필터: 직선거리 기준으로 가장 가까운 candidate_prefilter개
    candidate_n = min(candidate_prefilter, len(df))
    candidates = df.nsmallest(candidate_n, 'straight_dist_m').copy()

    # 도로 기반 거리 계산 시도 (캐시된 그래프가 있으면 사용)
    road_results = None
    if _OSM:
        try:
            if os.path.exists(graph_cache_path):
                with open(graph_cache_path, 'rb') as fh:
                    G = pickle.load(fh)
                # nearest nodes for user and candidates
                user_node = ox.nearest_nodes(G, ulon, ulat)
                cand_nodes = ox.nearest_nodes(G, candidates[lon_col].tolist(), candidates[lat_col].tolist())
                lengths = []
                for n in cand_nodes:
                    try:
                        d = nx.shortest_path_length(G, user_node, n, weight='length')
                        lengths.append(d)
                    except Exception:
                        lengths.append(float('inf'))
                candidates['road_dist_m'] = lengths
                road_results = candidates
        except Exception:
            road_results = None

    # 도로 거리가 계산되지 않았다면 직선거리로 대체
    if road_results is None:
        candidates['road_dist_m'] = candidates['straight_dist_m']
        road_results = candidates

    # road_dist_m 기준으로 정렬하고 return_count개 반환
    road_results_sorted = road_results.sort_values('road_dist_m', ascending=True).reset_index(drop=True)
    return road_results_sorted.head(return_count if return_count is not None else len(road_results_sorted))


def make_popup(text, width=240):
    """Create a folium.Popup with safe escaping and simple line-wrapping.

    Returns a folium.Popup ready to add to a map.
    """
    s = str(text)
    if '<br>' in s:
        parts = s.split('<br>')
        escaped = '<br>'.join(escape(p) for p in parts)
    else:
        escaped = escape(s).replace('\n', '<br>')
    html = f"""<div style='max-width:{width}px; white-space:normal; word-wrap:break-word; font-size:13px; line-height:1.2;'>{escaped}</div>"""
    height = 50 + max(0, (len(escaped) - width) // 3)
    return folium.Popup(folium.IFrame(html=html, width=width+20, height=height), max_width=width+20)


def draw_route_on_map(fmap, ulat, ulon, target_lat, target_lon, graph_cache_path: str = GRAPH_CACHE_PATH):
    """Try to draw a road-based route on fmap using cached osmnx graph.

    If osmnx/graph not available or routing fails, draws a straight line instead.
    Returns True if road-based route was drawn, False if straight-line fallback used (or nothing drawn).
    """
    # prefer using installed osmnx if available
    if _OSM:
        try:
            G = None
            if os.path.exists(graph_cache_path):
                with open(graph_cache_path, 'rb') as fh:
                    G = pickle.load(fh)
            if G is not None:
                try:
                    user_node = ox.nearest_nodes(G, ulon, ulat)
                    target_node = ox.nearest_nodes(G, target_lon, target_lat)
                    route = nx.shortest_path(G, user_node, target_node, weight='length')
                    # try node coords first
                    try:
                        coords = [(float(G.nodes[n]['y']), float(G.nodes[n]['x'])) for n in route]
                        folium.PolyLine(locations=coords, color='green', weight=4, opacity=0.8).add_to(fmap)
                        return True
                    except Exception:
                        # fall back to edge geometry if present
                        edge_geoms = []
                        for u, v in zip(route[:-1], route[1:]):
                            data = G.get_edge_data(u, v)
                            if data is None:
                                continue
                            first = next(iter(data.values()))
                            geom = first.get('geometry')
                            if geom is not None:
                                try:
                                    pts = [(pt[1], pt[0]) for pt in geom.coords]
                                    edge_geoms.extend(pts)
                                except Exception:
                                    pass
                        if edge_geoms:
                            folium.PolyLine(locations=edge_geoms, color='green', weight=4, opacity=0.8).add_to(fmap)
                            return True
                except Exception:
                    # routing failed
                    pass
        except Exception:
            pass

    # fallback: straight line
    try:
        folium.PolyLine(locations=[[ulat, ulon], [target_lat, target_lon]], color='green').add_to(fmap)
    except Exception:
        return False
    return False


def _find_lat_lon_cols(df):
    """Return (lat_col, lon_col) names if found, else (None, None). Tries common variations."""
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


def _ensure_coord_aliases(df, src_lat, src_lon):
    """Create standardized coordinate columns and common aliases. Returns a copy."""
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