import streamlit as st
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import folium
from streamlit_folium import st_folium
import PIL.Image
from io import BytesIO

# --- 1. CONFIG: CLEAN FULLSCREEN ---
st.set_page_config(page_title="Maritime FlightDoc Pro", layout="wide")

st.markdown("""
    <style>
        /* Menghilangkan semua elemen Streamlit agar peta benar-backar bersih */
        .block-container { padding: 0rem; background-color: #000000; }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        section[data-testid="stSidebar"] {display: none;}
    </style>
    """, unsafe_allow_html=True)

# Inisialisasi state untuk tracking klik
if 'active_vessel' not in st.session_state:
    st.session_state.active_vessel = None

# --- 2. DATA ENGINE ---
@st.cache_data
def load_radar_minimal(file_path):
    try:
        ds = xr.open_dataset(file_path)
        ds_clipped = ds.sel(lat=slice(-6.5, -5.5), lon=slice(105.0, 107.0))
        lon, lat = ds_clipped.lon.values, ds_clipped.lat.values
        speed = np.sqrt(ds_clipped.u.isel(time=0).values**2 + ds_clipped.v.isel(time=0).values**2)
        fig, ax = plt.subplots(figsize=(15, 15))
        fig.subplots_adjust(left=0, right=1, bottom=0, top=1); ax.axis('off')
        ax.imshow(speed, extent=[lon.min(), lon.max(), lat.min(), lat.max()], 
                   origin='lower', cmap='turbo', alpha=0.6, interpolation='bilinear')
        buf = BytesIO(); plt.savefig(buf, format='png', transparent=True, dpi=200); plt.close(fig)
        return buf, [float(lat.min()), float(lon.min()), float(lat.max()), float(lon.max())]
    except: return None, None

# --- 3. MOCK DATA ---
ships = [
    {
        "name": "KMP SEBUKU", "type": "Ferry", "lat": -5.89, "lon": 105.82, 
        "speed": "10.8 kn", "course": "115", "eta": "11:15 UTC", "dest": "MERAK", "dest_pos": [-5.93, 106.00],
        "past_track": [[-5.87, 105.77], [-5.88, 105.79], [-5.89, 105.82]],
        "timeline": [
            {"time": "10:30", "pos": [-5.90, 105.86], "cond": "🌧️ Hujan"},
            {"time": "10:45", "pos": [-5.91, 105.91], "cond": "☁️ Tebal"},
            {"time": "11:00", "pos": [-5.92, 105.96], "cond": "⛅ Berawan"},
            {"time": "11:15", "pos": [-5.93, 106.00], "cond": "☀️ Cerah"}
        ]
    },
    {
        "name": "MT OCEAN PRIDE", "type": "Tanker", "lat": -6.10, "lon": 105.80, 
        "speed": "14.2 kn", "course": "210", "eta": "14:00 UTC", "dest": "AUSTRALIA", "dest_pos": [-6.50, 105.50],
        "past_track": [[-5.80, 105.95], [-6.10, 105.80]],
        "timeline": [
            {"time": "Now", "pos": [-6.10, 105.80], "cond": "☀️ Cerah"},
            {"time": "+30m", "pos": [-6.25, 105.70], "cond": "⛅ Berawan"}
        ]
    }
]

# --- 4. MAP RENDER ---
img_buf, bounds = load_radar_minimal("CODAR_BADA_2025_04_12_1400-1744466400.nc")
m = folium.Map(location=[-6.0, 105.9], zoom_start=11, tiles="CartoDB dark_matter", zoom_control=True)

if img_buf:
    folium.raster_layers.ImageOverlay(np.array(PIL.Image.open(img_buf)), 
                                     bounds=[[bounds[0], bounds[1]], [bounds[2], bounds[3]]], opacity=0.6).add_to(m)

for s in ships:
    is_active = (st.session_state.active_vessel == s['name'])
    
    # Lintasan dasar
    folium.PolyLine(locations=s['past_track'], color="#e67e22", weight=2, opacity=0.4).add_to(m)
    line_color = "#00f2ff" if is_active else "#3498db"
    folium.PolyLine(locations=[[s['lat'], s['lon']], s['dest_pos']], color=line_color, weight=4 if is_active else 2, opacity=0.7).add_to(m)
    
    # Waypoints Cuaca: Muncul HANYA jika kapal diklik
    if is_active:
        for wp in s['timeline']:
            folium.Marker(
                location=wp['pos'],
                icon=folium.DivIcon(html=f"""
                    <div style="background: white; border-radius: 6px; padding: 2px; border: 2px solid #00f2ff; 
                    box-shadow: 2px 2px 5px rgba(0,0,0,0.5); text-align: center; width: 38px;">
                        <span style="font-size: 18px;">{wp['cond'].split()[0]}</span>
                    </div>"""),
            ).add_to(m)

    # Popup Content
    t_rows = "".join([f"<tr><td>{i['time']}</td><td>: {i['cond']}</td></tr>" for i in s['timeline']])
    p_html = f"""
    <div style="font-family: Arial; width: 220px; font-size: 12px;">
        <b style="color: #2980b9; font-size: 14px;">{s['name']}</b><br><hr style="margin:4px 0;">
        <table style="width: 100%;">
            <tr><td>Speed</td><td>: {s['speed']}</td></tr>
            <tr><td>Course</td><td>: {s['course']}°</td></tr>
            <tr><td>Tujuan</td><td>: {s['dest']}</td></tr>
            <tr><td>ETA</td><td>: {s['eta']}</td></tr>
        </table>
        <hr style="margin:4px 0;"><b>Route Forecast:</b>
        <table style="width: 100%; margin-top:5px; font-size: 11px;">{t_rows}</table>
    </div>"""

    # Marker Kapal
    marker_color = "#00f2ff" if is_active else "#FF4B4B"
    folium.Marker(
        location=[s['lat'], s['lon']],
        popup=folium.Popup(p_html, max_width=250),
        tooltip=s['name'],
        icon=folium.DivIcon(html=f'<div style="transform: rotate({s["course"]}deg); color:{marker_color}; font-size:26px; text-shadow: 1px 1px 2px #000;">➤</div>')
    ).add_to(m)

# Tampilkan Peta
map_data = st_folium(m, width=1550, height=900, key="main_map")

# Update state berdasarkan klik
if map_data.get("last_object_clicked_tooltip"):
    clicked = map_data["last_object_clicked_tooltip"]
    if clicked != st.session_state.active_vessel:
        st.session_state.active_vessel = clicked
        st.rerun()
