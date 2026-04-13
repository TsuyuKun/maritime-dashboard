import streamlit as st
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import folium
from streamlit_folium import st_folium
import PIL.Image
from io import BytesIO

# --- 1. CONFIG & PERFORMANCE ---
st.set_page_config(page_title="Maritime FlightDoc Pro", layout="wide")

st.markdown("""
    <style>
        .block-container { padding: 0rem; background-color: #000000; }
        #MainMenu, footer, header {visibility: hidden;}
        section[data-testid="stSidebar"] {display: none;}
    </style>
    """, unsafe_allow_html=True)

if 'active_vessel' not in st.session_state:
    st.session_state.active_vessel = None

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
ships = [
    {
        "name": "KMP SEBUKU", "lat": -5.89, "lon": 105.82, "speed": "10.8 kn", "course": "115", 
        "dest": "MERAK", "dest_pos": [-5.93, 106.00],
        "timeline": [
            {"time": "10:30", "pos": [-5.90, 105.86], "cond": "🌧️ Hujan"},
            {"time": "11:15", "pos": [-5.93, 106.00], "cond": "☀️ Cerah"}
        ]
    },
    {
        "name": "MT OCEAN PRIDE", "lat": -6.10, "lon": 105.80, "speed": "14.2 kn", "course": "210", 
        "dest": "AUSTRALIA", "dest_pos": [-6.50, 105.50],
        "timeline": [
            {"time": "Now", "pos": [-6.10, 105.80], "cond": "☀️ Cerah"},
            {"time": "+30m", "pos": [-6.25, 105.70], "cond": "⛅ Berawan"}
        ]
    }
]

# --- 4. MAP RENDER ---
img_buf, bounds = get_radar_overlay("CODAR_BADA_2025_04_12_1400-1744466400.nc")
m = folium.Map(location=[-6.0, 105.9], zoom_start=11, tiles="CartoDB dark_matter")

if img_buf:
    folium.raster_layers.ImageOverlay(np.array(PIL.Image.open(img_buf)), bounds=[[bounds[0], bounds[1]], [bounds[2], bounds[3]]], opacity=0.6).add_to(m)

for s in ships:
    is_active = (st.session_state.active_vessel == s['name'])
    
    # Rute
    line_color = "#00f2ff" if is_active else "#3498db"
    folium.PolyLine(locations=[[s['lat'], s['lon']], s['dest_pos']], color=line_color, weight=5 if is_active else 2, opacity=0.7).add_to(m)
    
    # Waypoints HANYA JIKA AKTIF
    if is_active:
        for wp in s['timeline']:
            folium.Marker(
                location=wp['pos'],
                icon=folium.DivIcon(html=f"""
                    <div style="background:white; border-radius:4px; padding:2px; border:2px solid cyan; text-align:center; width:30px; box-shadow: 2px 2px 5px rgba(0,0,0,0.5);">
                        <span style="font-size:14px;">{wp['cond'].split()[0]}</span>
                    </div>""")
            ).add_to(m)

    # Marker Kapal
    folium.Marker(
        location=[s['lat'], s['lon']],
        tooltip=s['name'], # Tooltip ini yang ditangkap sebagai ID klik
        icon=folium.DivIcon(html=f'<div style="transform:rotate({s["course"]}deg); color:{"#00f2ff" if is_active else "#FF4B4B"}; font-size:26px;">➤</div>')
    ).add_to(m)

# Tampilkan Peta
# Gunakan st_folium dan tangkap outputnya
output = st_folium(m, width=1550, height=900, key="vessel_map")

# Logika Deteksi Klik
if output.get("last_object_clicked_tooltip"):
    clicked_name = output["last_object_clicked_tooltip"]
    if clicked_name != st.session_state.active_vessel:
        st.session_state.active_vessel = clicked_name
        st.rerun()
