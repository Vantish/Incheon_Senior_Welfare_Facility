import streamlit as st
from app_bus_stop_recommendation import bus_stop_recommendation


def run_map():
    st.subheader('위치 기반 추천')
    st.text('\n')
    if st.button('버스 추천'):
        bus_stop_recommendation()
        pass
    