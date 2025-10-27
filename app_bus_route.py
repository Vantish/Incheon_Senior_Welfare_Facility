import os
import time
import requests
import xml.etree.ElementTree as ET
from html import unescape
import streamlit as st
from datetime import datetime

# API 키 소스 우선순위:
# 1) Streamlit secrets (st.secrets['INCHEON_BUS_API_KEY'])
# 2) 환경변수 INCHEON_BUS_API_KEY
# 3) 하드코딩된 DEFAULT (개발용; 실제 운영시에는 secrets 사용 권장)
DEFAULT_API_KEY = os.environ.get('INCHEON_BUS_API_KEY', None)


def _get_api_key_from_secrets():
    try:
        # Streamlit의 secrets를 사용(주로 배포환경에서 사용)
        if hasattr(st, 'secrets') and isinstance(st.secrets, dict) and 'INCHEON_BUS_API_KEY' in st.secrets:
            return st.secrets['INCHEON_BUS_API_KEY']
    except Exception:
        pass
    return None


def _extract_routes_from_json(obj, collector):
    # 재귀적으로 JSON 구조에서 노선명을 추출
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() in ('rtnm', 'rtNm'.lower(), 'plainno', 'ratename', 'route', 'routeno', 'busroutenm'):
                try:
                    collector.add(str(v))
                except Exception:
                    pass
            else:
                _extract_routes_from_json(v, collector)
    elif isinstance(obj, list):
        for item in obj:
            _extract_routes_from_json(item, collector)


def _extract_routes_from_xml(root):
    tags = ['rtNm', 'plainNo', 'routeNo', 'busRouteNm', 'routeno']
    found = set()
    for t in tags:
        for el in root.findall('.//{}'.format(t)):
            if el is not None and el.text:
                found.add(el.text.strip())
    # fallback: 모든 <item> 내부 텍스트에서 숫자+문자 패턴을 조금 추출
    return found


def _try_endpoint_get_routes(endpoint_name, base_url, params, headers=None, timeout=8):
    try:
        resp = requests.get(base_url, params=params, headers=headers, timeout=timeout)
        if resp.status_code != 200:
            return None, f'HTTP {resp.status_code} from {endpoint_name}'
        content_type = resp.headers.get('Content-Type', '')
        text = resp.text
        # try json
        try:
            j = resp.json()
            collector = set()
            _extract_routes_from_json(j, collector)
            return list(collector), None
        except Exception:
            pass
        # try xml
        try:
            root = ET.fromstring(text)
            found = _extract_routes_from_xml(root)
            return list(found), None
        except Exception as e:
            return None, f'파싱 실패: {str(e)}'
    except Exception as e:
        return None, str(e)


def check_bus_route(bus_dic, api_key=None):
    """
    bus_dic: {'user': DataFrame or list, 'facility': DataFrame or list}

    반환: {'user': {정류장명: [버스번호,...], ...}, 'facility': {...}} 또는 빈 dict

    동작:
    - 입력에서 가능한 정류장 식별자(정류소아이디, 정류소 번호, 정류장명)를 추출합니다.
    - 여러 후보 OpenAPI 엔드포인트(우선 Incheon 공공데이터 포털 예상 엔드포인트)를 순차 시도하여
      정류장을 지나는 노선 목록을 조회합니다. 실패해도 예외를 잡아 빈 결과를 반환합니다.
    """
    if bus_dic is None:
        return {}

    # 우선 st.secrets에 API 키가 있으면 사용, 없으면 인자로 준 키, 그 다음 환경변수/DEFAULT 사용
    key = api_key or _get_api_key_from_secrets() or DEFAULT_API_KEY

    # 수집 결과 포맷
    out = {'user': {}, 'facility': {}}

    # helper: DataFrame 또는 list에서 (name, id) 쌍 추출
    def _iter_stops(obj):
        stops = []
        if obj is None:
            return stops
        # pandas DataFrame like
        try:
            cols = getattr(obj, 'columns', None)
            if cols is not None:
                for _, r in obj.iterrows():
                    name = None
                    sid = None
                    for c in ('정류소아이디', '정류소 아이디', '정류소아이', '정류소번호', '정류소 번호', '정류장id', 'id'):
                        if c in r.index:
                            sid = r[c]
                            break
                    for c in ('정류소 명', '정류소명', '정류장명', '정류소', '정류소 명'):
                        if c in r.index:
                            name = r[c]
                            break
                    stops.append((str(name) if name is not None else None, sid))
                return stops
        except Exception:
            pass
        # list/tuple of strings
        if isinstance(obj, (list, tuple)):
            for it in obj:
                if isinstance(it, (list, tuple)) and len(it) >= 2:
                    stops.append((str(it[0]), it[1]))
                else:
                    stops.append((str(it), None))
        return stops

    # 엔드포인트 후보들 (정류장 -> 노선 조회에 유용한 후보들을 우선 포함)
    # 일부 공공데이터 API는 서비스명/경로가 다르므로 여러 후보를 순차 시도합니다.
    ENDPOINTS = [
        # 인천/일반 정류장 기반 노선조회(널리 사용되는 이름)
        ('getSttnAcctoThrghRouteList', 'http://apis.data.go.kr/1613000/BusSttnInfoInqireService/getSttnAcctoThrghRouteList'),
        ('getSttnAcctoThrghRouteList_https', 'https://apis.data.go.kr/1613000/BusSttnInfoInqireService/getSttnAcctoThrghRouteList'),
        # 국토교통부(버스 노선) 관련 엔드포인트 후보들
        ('MOLIT_getRouteInfoList', 'https://apis.data.go.kr/1613000/BusRoute/getRouteInfoList'),
        ('MOLIT_getRouteInfoItem', 'https://apis.data.go.kr/1613000/BusRoute/getRouteInfoItem'),
        ('MOLIT_getBusRouteList', 'https://apis.data.go.kr/1613000/BusRoute/getBusRouteList'),
    ]

    def _build_param_candidates(ename, base, sid, name, key):
        """Return a list of candidate param dicts to try for given endpoint.

        This centralizes the heuristics for different API styles.
        """
        param_candidates = []
        if 'sttn' in ename.lower() or 'sttn' in base.lower() or 'station' in ename.lower():
            if sid is not None and str(sid) != '':
                param_candidates.extend([
                    {'serviceKey': key, 'arsId': sid, '_type': 'json'},
                    {'serviceKey': key, 'sttnId': sid, '_type': 'json'},
                    {'ServiceKey': key, 'arsId': sid},
                    {'ServiceKey': key, 'sttnId': sid},
                ])
            if name is not None and name != 'None':
                param_candidates.extend([
                    {'serviceKey': key, 'sttnNm': name, '_type': 'json'},
                    {'ServiceKey': key, 'sttnNm': name},
                ])
            param_candidates = [dict(p, **({'dataType': 'JSON'} if '_type' not in p else {})) for p in param_candidates]
        else:
            if sid is not None and str(sid) != '':
                param_candidates.extend([
                    {'serviceKey': key, 'rte_id': sid, 'dataType': 'JSON'},
                    {'serviceKey': key, 'routeId': sid, 'dataType': 'JSON'},
                    {'ServiceKey': key, 'rte_id': sid},
                ])
            if name is not None and name != 'None':
                param_candidates.append({'serviceKey': key, 'routeNo': name, 'dataType': 'JSON'})
        return param_candidates

    for side in ('user', 'facility'):
        stops = _iter_stops(bus_dic.get(side) if isinstance(bus_dic, dict) else None)
        for name, sid in stops:
            # skip None name
            stop_key = name or str(sid or '')
            routes = []
            errors = []
            if sid is None and (name is None or name == 'None'):
                out[side][stop_key] = []
                continue
            # try endpoints
            for ename, base in ENDPOINTS:
                # 시도할 파라미터 후보 목록 생성
                param_candidates = _build_param_candidates(ename, base, sid, name, key)

                # 시도
                tried_any = False
                for params in param_candidates:
                    tried_any = True
                    vals, err = _try_endpoint_get_routes(ename, base, params)
                    if err:
                        # 저장해두고 다음 후보 시도
                        errors.append(f'{ename}:{err}')
                        time.sleep(0.05)
                        continue
                    if vals:
                        routes = vals
                        break

                # 후보가 전혀 생성되지 않았다면, 기본 호출 한번 시도
                if not tried_any:
                    # 기본 형태: 정류장 id/name을 arsId로 전달 시도
                    params = {'serviceKey': key, 'arsId': sid if sid is not None else name, '_type': 'json'}
                    vals, err = _try_endpoint_get_routes(ename, base, params)
                    if err:
                        errors.append(f'{ename}:{err}')
                    elif vals:
                        routes = vals

                if routes:
                    break
                # small pause between tries
                time.sleep(0.1)

            out[side][stop_key] = list(dict.fromkeys([str(r) for r in (routes or [])]))

    return out