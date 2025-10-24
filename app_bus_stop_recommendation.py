import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.neighbors import NearestNeighbors
from geopy.geocoders import Nominatim
from geopy.distance import distance
from geopy.distance import geodesic
from app_location import run_location

# 사용자 위치정보(user_location)와 해당 정보를 바탕으로 계산된 시설의 위치정보(facilities_location)를 입력받은 후
# 사용자 근처 가장 가까운 정류장 5개와 시설에서 가장 가까운 정류장 5개를 딕셔너리 형태로 반환합니다.
# 반환 정보 = 'user_nearby' and 'facility_nearby'

bus_stops_df = pd.read_csv('./data/버스정류장.csv')


def bus_stop_recommendation(user_location, facilities_location):

    if user_location :
        lat =user_location[0]
        lon = user_location[1]
    else : 
        return None
    
    

    return
