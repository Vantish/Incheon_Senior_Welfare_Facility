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