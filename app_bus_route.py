import streamlit as st
import numpy as np
import pandas as pd

from app_bus_stop_recommendation import bus_stop_recommendation

# bus_stop_recommendation() 에서 반환받은 정류장 리스트를 이용해서
# 해당 정류장을 지나가는 노선을 찾을겁니다.
# 찾은 후 '정류장 명' : 버스번호 형식의 딕셔너리로 반환할 예정입니다.

def check_bus_route(bus_dic):
    # 안전한 noop 반환 (사용자/시설 정류장 목록을 그대로 키로 돌려주는 최소 스펙)
    if bus_dic is None:
        return {}
    if isinstance(bus_dic, dict):
        return {k: (v['정류장명'].astype(str).tolist() if hasattr(v, 'columns') and '정류장명' in v.columns else []) for k, v in bus_dic.items()}
    return {}