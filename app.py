import streamlit as st
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import folium
from streamlit_folium import folium_static
import PIL.Image
from io import BytesIO

# --- 1. CONFIG & PERFORMANCE TUNING ---
st.set_page_config(page_title="Maritime FlightDoc Pro", layout="wide")

# CSS Minimalis
st.markdown("""
    <style>
        .block-container { padding: 0rem; background-color: #000000; }
        #MainMenu, footer, header {visibility: hidden;}
        /* Sidebar diperkecil agar tidak mengganggu */
        section[data-testid="stSidebar"] { width: 250px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CACHED ENGINE ---
@st.cache_resource # Gunakan cache_resource untuk objek berat
def get_radar_layer(file_path):
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

# --- 3. DATA & STATE ---
ships = [
    {
        "name": "KMP SEBUKU", "lat": -5.89, "lon": 105.82, "speed": "10.8 kn", "course": "115", 
        "dest": "MERAK", "dest_pos": [-5.93, 106.00],
        "timeline": [{"time": "10:30", "pos": [-5.90, 105.86], "cond": "🌧️ Hujan"}, {"time": "11:15", "pos": [-5.93, 106.00], "cond": "☀️ Cerah"}]
    },
    {
        "name": "MT OCEAN PRIDE", "lat": -6.10, "lon": 105.80, "speed": "14.2 kn", "course": "210", 
        "dest": "AUSTRALIA", "dest_pos": [-6.50, 105.50],
        "timeline": [{"time": "Now", "pos": [-6.10, 105.80], "cond": "☀️ Cerah"}, {"time": "+30m", "pos": [-6.25, 105.70], "cond": "⛅ Berawan"}]
    }
]

# --- 4. UI SELECTION (Untuk Snappy Transition) ---
with st.sidebar:
    st.write("### 🚢 Fleet Monitor")
    active_vessel = st.radio("Focus Vessel:", ["None"] + [s['name'] for s in ships], index=0)

# --- 5. RENDER MAP ---
img_buf, bounds = get_radar_layer("CODAR_BADA_2025_04_12_1400-1744466400.nc")
m = folium.Map(location=[-6.0, 105.9], zoom_start=11, tiles="CartoDB dark_matter")

if img_buf:
    folium.raster_layers.ImageOverlay(np.array(PIL.Image.open(img_buf)), bounds=[[bounds[0], bounds[1]], [bounds[2], bounds[3]]], opacity=0.6).add_to(m)

for s in ships:
    is_active = (active_vessel == s['name'])
    
    # Rute
    line_color = "#00f2ff" if is_active else "#3498db"
    folium.PolyLine(locations=[[s['lat'], s['lon']], s['dest_pos']], color=line_color, weight=5 if is_active else 2, opacity=0.7).add_to(m)
    
    # Waypoints
    if is_active:
        for wp in s['timeline']:
            folium.Marker(location=wp['pos'], icon=folium.DivIcon(html=f'<div style="background:white; border-radius:4px; padding:2px; border:1px solid cyan; text-align:center; width:30px;">{wp["cond"].split()[0]}</div>')).add_to(m)

    # Marker
    folium.Marker(
        location=[s['lat'], s['lon']],
        icon=folium.DivIcon(html=f'<div style="transform:rotate({s["course"]}deg); color:{"#00f2ff" if is_active else "#FF4B4B"}; font-size:24px;">➤</div>')
    ).add_to(m)

folium_static(m, width=1550, height=900)
