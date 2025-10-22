import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import folium
from sklearn.neighbors import NearestNeighbors


# 기존에는 버스 정보를 받아서 정류장을 찾는 형태였는데
# 반대가 더 합리적일거 같다는 생각이 들었습니다.
# 때문에 사용자 위치정보(user_location)과 
# 해당 정보를 바탕으로 계산된 시설의 위치정보(facilities_location)를 입력받은 후
# 사용자 근처 가장 가까운 정류장 5개와 시설에서 가장 가까운 정류장 5개를 딕셔너리 형태로 반환합니다.

def bus_stop_recommendation(user_location, facilities_location):
    return

