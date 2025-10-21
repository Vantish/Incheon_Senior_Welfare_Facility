import streamlit as st
import numpy as np
import pandas as pd

from app_bus_route import check_bus_route


def bus_stop_recommendation():
    bus_list = check_bus_route()
    if bus_list is not None:
        pass
    else:
        pass