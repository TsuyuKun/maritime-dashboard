import streamlit as st
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import folium
from streamlit_folium import folium_static
import PIL.Image
from io import BytesIO

# --- 1. CONFIG ---
st.set_page_config(page_title="Maritime FlightDoc Pro", layout="wide")

st.markdown("""
    <style>
        .block-container { padding: 0rem; background-color: #000000; }
        #MainMenu, footer, header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
@st.cache_data
def get_radar_overlay(file_path):
    try:
        ds = xr.open_dataset(file_path)
        ds_clipped = ds.sel(lat=slice(-6.5, -5.5), lon=slice(105.0, 107.0))
        lon, lat = ds_clipped.lon.values, ds_clipped.lat.values
        speed = np.sqrt(ds_clipped.u.isel(time=0).values**2 + ds_clipped.v.isel(time=0).values**2)
        fig, ax = plt.subplots(figsize=(10, 10))
        fig.subplots_adjust(0,0,1,1); ax.axis('off')
        ax.imshow(speed, extent=[lon.min(), lon.max(), lat.min(), lat.max()], 
                   origin='lower', cmap='turbo', alpha=0.6, interpolation='bilinear')
        buf = BytesIO(); plt.savefig(buf, format='png', transparent=True, dpi=150); plt.close(fig)
        return buf, [float(lat.min()), float(lon.min()), float(lat.max()), float(lon.max())]
    except: return None, None

# --- 3. MOCK DATA ---
ships_data = [
    {
        "name": "KMP_SEBUKU", "lat": -5.89, "lon": 105.82, "course": 115,
        "dest_pos": [-5.93, 106.00],
        "timeline": [
            {"pos": [-5.90, 105.86], "icon": "🌧️"},
            {"pos": [-5.93, 106.00], "icon": "☀️"}
        ]
    },
    {
        "name": "MT_OCEAN_PRIDE", "lat": -6.10, "lon": 105.80, "course": 210,
        "dest_pos": [-6.50, 105.50],
        "timeline": [
            {"pos": [-6.10, 105.80], "icon": "☀️"},
            {"pos": [-6.
