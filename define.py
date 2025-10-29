import numpy as np
import pandas as pd
import folium
from streamlit.components.v1 import html as st_html
import streamlit as st
import math
from datetime import datetime
from html import escape
import requests
import xml.etree.ElementTree as ET

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

import base64

def set_sidebar_background(image_path):
    # 로컬 이미지 파일을 base64로 읽기
    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()
    
    # CSS로 사이드바 배경 설정
    st.markdown(
        f"""
        <style>
        [data-testid="stSidebar"] {{
            background-image: url("data:image/jpg;base64,{encoded}");
            background-size: cover;
            background-position: center;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
    
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
    직선 거리와 도로 거리를 10km(10,000m)로 제한

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

    # 직선거리 계산 및 10km 제한
    df['straight_dist_m'] = df.apply(lambda r: _haversine_m((ulat, ulon), (r[lat_col], r[lon_col])), axis=1)
    df = df[df['straight_dist_m'] <= 10000]  # 10km 이내로 제한
    if df.shape[0] == 0:
        return pd.DataFrame(columns=df.columns)  # 빈 데이터프레임 반환

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
                # 도로 거리 10km 제한
                candidates = candidates[candidates['road_dist_m'] <= 10000]
                road_results = candidates
        except Exception:
            road_results = None

    # 도로 거리가 계산되지 않았다면 직선거리로 대체
    if road_results is None:
        candidates['road_dist_m'] = candidates['straight_dist_m']
        candidates = candidates[candidates['road_dist_m'] <= 10000]  # 직선 거리로 대체 시에도 10km 제한
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

# ----------------------------------------------------------------------------------
# 로컬 CSV 기반 버스 노선 유틸
# - 원본 CSV: ./data/버스노선.csv (사용자가 제공)
# - 핵심 목적: 정류소 ID(예: '정류소 번호')로 노선 목록을 조회하고,
#   노선 -> 정류장 순서(있다면)도 인덱싱하여 경로 탐색을 단순화합니다.
# 사용 예시:
#   df = load_busroute_csv()
#   stop_to_routes, route_to_stops = build_busroute_index(df)
# ----------------------------------------------------------------------------------


def load_busroute_csv(path: str = './data/버스노선.csv') -> pd.DataFrame:
    """CSV 파일을 읽어 DataFrame으로 반환합니다. 실패 시 빈 DataFrame 반환."""
    try:
        df = pd.read_csv(path, dtype=str)
        df.columns = [c.strip() for c in df.columns]
        return df
    except Exception:
        return pd.DataFrame()


def build_busroute_index(df: pd.DataFrame):
    """DataFrame에서 두 인덱스 생성:
    - stop_to_routes: {정류소ID: set(노선번호,...)}
    - route_to_stops: {노선번호: [정류소ID, ...]}

    컬럼 자동 감지는 다음 후보 이름들을 확인합니다.
    """
    stop_id_cols = ['정류소 번호', '정류소번호', '정류소_id', 'arsId', '정류장ID', '정류소아이디', '정류장 id']
    route_no_cols = ['노선번호', '버스번호', 'route', 'routeNo', '노선']
    seq_cols = ['순번', '정류장순번', 'stop_seq', 'seq', '순서', '정류소순번']

    cols = [c for c in df.columns]
    stop_col = next((c for c in cols if c in stop_id_cols or any(k in c for k in stop_id_cols)), None)
    route_col = next((c for c in cols if c in route_no_cols or any(k in c for k in route_no_cols)), None)
    seq_col = next((c for c in cols if c in seq_cols or any(k in c for k in seq_cols)), None)

    stop_to_routes = {}
    route_to_stops = {}

    if df is None or df.empty or stop_col is None or route_col is None:
        return stop_to_routes, route_to_stops

    # normalize strings
    df2 = df.copy()
    df2[stop_col] = df2[stop_col].astype(str).str.strip()
    df2[route_col] = df2[route_col].astype(str).str.strip()

    # group by route to build ordered stop lists when seq_col exists
    if seq_col and seq_col in df2.columns:
        try:
            df2[seq_col] = pd.to_numeric(df2[seq_col], errors='coerce')
        except Exception:
            df2[seq_col] = None

    for _, row in df2.iterrows():
        sid = row.get(stop_col)
        rno = row.get(route_col)
        if pd.isna(sid) or pd.isna(rno):
            continue
        sid = str(sid).strip()
        rno = str(rno).strip()
        stop_to_routes.setdefault(sid, set()).add(rno)
        route_to_stops.setdefault(rno, []).append((row.get(seq_col) if seq_col in row.index else None, sid))

    # 정렬: seq가 있으면 seq 기준 정렬 후 sid 리스트로 변환
    for rno, seq_sid_list in list(route_to_stops.items()):
        # seq_sid_list: list of (seq, sid)
        if any(x[0] is not None for x in seq_sid_list):
            seq_sorted = sorted([x for x in seq_sid_list if x[0] is not None], key=lambda t: (t[0] if t[0] is not None else 1e9))
            sids = [sid for _, sid in seq_sorted]
        else:
            # seq 정보 없으면 입력 순서를 유지한 sid만
            sids = [sid for _, sid in seq_sid_list]
        route_to_stops[rno] = sids

    return stop_to_routes, route_to_stops


# 유틸: 다양한 자료형을 안전하게 파이썬 리스트로 변환
def to_pylist(x):
    """pandas/numpy/list/tuple/set/단일값 등을 안전하게 python list로 변환합니다.

    - DataFrame -> records (list of dict)
    - Series / ndarray -> list
    - list/tuple/set -> list
    - None -> []
    - 그 외 단일값 -> [value]
    """
    try:
        if isinstance(x, pd.DataFrame):
            return x.to_dict(orient='records')
    except Exception:
        pass
    try:
        if isinstance(x, (pd.Series, np.ndarray)):
            return list(x)
    except Exception:
        pass
    if isinstance(x, (list, tuple, set)):
        return list(x)
    if x is None:
        return []
    return [x]


def extract_stop_list(obj) -> list:
    """입력으로 주어지는 정류장 객체에서 (name, stop_id) 튜플 리스트를 반환.
    - obj가 DataFrame이면 컬럼 후보를 찾아 추출
    - obj가 list/tuple이면 항목별로 처리
    """
    out = []
    if obj is None:
        return out
    # DataFrame 처리
    if isinstance(obj, pd.DataFrame):
        cols = list(obj.columns)
        id_candidates = ['정류소 번호', '정류소번호', '정류장ID', '정류소아이디', 'arsId', 'id', 'ID']
        name_candidates = ['정류소명', '정류장명', '정류소 명', '정류장 명', '정류소']
        id_col = next((c for c in cols if c in id_candidates or any(k in c for k in id_candidates)), None)
        name_col = next((c for c in cols if c in name_candidates or any(k in c for k in name_candidates)), None)
        for _, r in obj.iterrows():
            sid = None
            name = None
            if id_col and id_col in r.index:
                sid = r[id_col]
            # fallback key names
            if sid is None:
                for k in id_candidates:
                    if k in r.index:
                        sid = r[k]
                        break
            if name_col and name_col in r.index:
                name = r[name_col]
            if name is None:
                for k in name_candidates:
                    if k in r.index:
                        name = r[k]
                        break
            out.append((str(name) if name is not None else '', str(sid) if sid is not None else ''))
        return out

    # list / tuple 처리
    if isinstance(obj, (list, tuple)):
        for it in obj:
            if isinstance(it, (list, tuple)) and len(it) >= 2:
                out.append((str(it[0]), str(it[1])))
            else:
                out.append((str(it), ''))
        return out

    # 단일 값
    out.append((str(obj), ''))
    return out


def normalize_routes_output(routes_obj) -> dict:
    """Normalize various possible outputs from check_bus_route into a strict dict of plain Python types.

    Returned schema:
      {
        '사용자 근처': { '<stop>': ['route1','route2', ...], ... },
        '시설 근처': { '<stop>': ['route1', ...], ... },
        'direct_routes': ['routeA', ...],
        'direct_connections': [ {'route':r, 'user_stop':u, 'facility_stop':f}, ... ]
      }

    This function accepts dict-like inputs or other types and will coercively convert
    DataFrame / Series / ndarray / list / tuple / set into lists of strings where
    appropriate. The goal is to make the consumer code free from pandas objects so
    boolean checks like `if x:` won't accidentally evaluate a DataFrame.
    """
    out = {'사용자 근처': {}, '시설 근처': {}, 'direct_routes': [], 'direct_connections': []}

    if not isinstance(routes_obj, dict):
        return out

    # helper to coerce a value into list of route-strings
    def _to_route_strings(v):
        items = to_pylist(v)
        result = []
        for it in items:
            if it is None:
                continue
            try:
                if isinstance(it, (pd.DataFrame, pd.Series)):
                    recs = it.to_dict(orient='records') if isinstance(it, pd.DataFrame) else list(it)
                    for r in to_pylist(recs):
                        s = str(r).strip()
                        if s:
                            result.append(s)
                    continue
            except Exception:
                pass

            if isinstance(it, dict):
                found = None
                for key in ('노선번호', '버스번호', 'route', 'routeNo', '노선'):
                    if key in it and it[key] is not None and str(it[key]).strip() != '':
                        found = str(it[key]).strip()
                        break
                if found is not None:
                    result.append(found)
                else:
                    s = str(it).strip()
                    if s:
                        result.append(s)
            else:
                s = str(it).strip()
                if s:
                    result.append(s)
        return result

    # 사용자 근처 / 시설 근처 - allow English fallback keys
    user_keys = ('사용자 근처', 'user', 'user_nearby', 'user_stops')
    fac_keys = ('시설 근처', 'facility', 'facility_nearby', 'facility_stops')

    user_src = None
    fac_src = None
    for k in user_keys:
        if k in routes_obj:
            user_src = routes_obj.get(k)
            break
    for k in fac_keys:
        if k in routes_obj:
            fac_src = routes_obj.get(k)
            break

    if isinstance(user_src, dict):
        for stop, v in user_src.items():
            out['사용자 근처'][str(stop)] = _to_route_strings(v)

    if isinstance(fac_src, dict):
        for stop, v in fac_src.items():
            out['시설 근처'][str(stop)] = _to_route_strings(v)

    # direct_routes
    direct = routes_obj.get('direct_routes') or routes_obj.get('direct') or []
    out['direct_routes'] = [str(x).strip() for x in to_pylist(direct) if str(x).strip()]

    # direct_connections: ensure each dict has string fields
    dc = to_pylist(routes_obj.get('direct_connections', []))
    normalized_dc = []
    for item in dc:
        if not isinstance(item, dict):
            continue
        r = str(item.get('route') or item.get('노선') or '').strip()
        u = str(item.get('user_stop') or item.get('사용자 근처') or '').strip()
        f = str(item.get('facility_stop') or item.get('시설 근처') or '').strip()
        normalized_dc.append({'route': r, 'user_stop': u, 'facility_stop': f})
    out['direct_connections'] = normalized_dc

    return out
