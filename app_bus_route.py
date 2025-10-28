import os
from typing import List, Dict, Any, Tuple
import pandas as pd
from define import load_busroute_csv, build_busroute_index, extract_stop_list


# 모듈 레벨 캐시: CSV를 매번 읽지 않도록 유지
_BUS_ROUTE_CACHE = {
    'stop_to_routes': None,
    'route_to_stops': None,
    'loaded_path': None,
}


# extract_stop_list has been moved to define.py and is imported above.


def _ensure_bus_index(path: str = './data/버스노선.csv'):
    """CSV를 한 번 로드하고 stop_to_routes, route_to_stops를 캐싱합니다."""
    global _BUS_ROUTE_CACHE
    path = path or './data/버스노선.csv'
    if _BUS_ROUTE_CACHE['loaded_path'] == path and _BUS_ROUTE_CACHE['stop_to_routes'] is not None:
        return _BUS_ROUTE_CACHE['stop_to_routes'], _BUS_ROUTE_CACHE['route_to_stops']
    df = load_busroute_csv(path)
    stop_to_routes, route_to_stops = build_busroute_index(df)
    _BUS_ROUTE_CACHE['stop_to_routes'] = stop_to_routes
    _BUS_ROUTE_CACHE['route_to_stops'] = route_to_stops
    _BUS_ROUTE_CACHE['loaded_path'] = path
    return stop_to_routes, route_to_stops


def check_bus_route(bus_dic: Dict[str, Any], busroute_csv_path: str = './data/버스노선.csv') -> Dict[str, Any]:
    """주요 함수: 사용자/시설 근처 정류장 목록에서 CSV 기반으로 교차되는 노선(직통)을 찾음.

    - bus_dic: {'user_nearby': df_or_list, 'facility_nearby': df_or_list} 형식 권장
    - busroute_csv_path: 버스노선 CSV 경로(상대 경로 허용)
    """
    stop_to_routes, route_to_stops = _ensure_bus_index(busroute_csv_path)

    user_obj = None
    fac_obj = None
    if isinstance(bus_dic, dict):
        user_obj = bus_dic.get('user_nearby') or bus_dic.get('user') or bus_dic.get('user_stops')
        fac_obj = bus_dic.get('facility_nearby') or bus_dic.get('facility') or bus_dic.get('facility_stops')
    else:
        # 유연성: 만약 dict가 아니라면 첫 인자로 간주
        user_obj = bus_dic

    user_stops = extract_stop_list(user_obj)
    fac_stops = extract_stop_list(fac_obj)

    user_map = {}
    fac_map = {}

    # 사용자 정류장별로 해당 노선 목록을 만든다
    for name, sid in user_stops:
        sidk = str(sid).strip()
        if sidk == '' or sidk is None:
            user_map[name or sidk] = []
        else:
            routes = list(stop_to_routes.get(sidk, []))
            user_map[name or sidk] = routes

    for name, sid in fac_stops:
        sidk = str(sid).strip()
        if sidk == '' or sidk is None:
            fac_map[name or sidk] = []
        else:
            routes = list(stop_to_routes.get(sidk, []))
            fac_map[name or sidk] = routes

    # 전체 사용자/시설의 노선 집합
    user_routes_union = set(r for routes in user_map.values() for r in routes)
    fac_routes_union = set(r for routes in fac_map.values() for r in routes)

    direct_routes = sorted(list(user_routes_union.intersection(fac_routes_union)))

    direct_connections = []
    for uname, uroutes in user_map.items():
        for fname, froutes in fac_map.items():
            inter = set(uroutes).intersection(froutes)
            for r in inter:
                direct_connections.append({'route': r, 'user_stop': uname, 'facility_stop': fname})

    # 사용자 요청에 맞춘 반환 형식: 한국어 키로 간단한 dict 반환
    # { '사용자 근처': {정류장명: [버스번호,...]}, '시설 근처': {정류장명: [버스번호,...]} }
    return {
        '사용자 근처': user_map,
        '시설 근처': fac_map,
        # 참고용으로 직통 노선/연결 정보도 포함(필요시 app에서 사용 가능)
        'direct_routes': direct_routes,
        'direct_connections': direct_connections,
    }
