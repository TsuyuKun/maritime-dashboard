import streamlit as st
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import folium
from streamlit_folium import folium_static
import branca.colormap as cm
from io import BytesIO
import PIL.Image
import plotly.graph_objects as go

# --- 1. CONFIG ---
st.set_page_config(page_title="Maritime FlightDoc Pro", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
        .block-container { padding: 0rem; background-color: #000000; }
        iframe { width: 100vw; height: 100vh; }
        .stMetric { background-color: #111; padding: 10px; border-radius: 5px; border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

# State untuk melacak kapal yang sedang dianalisis
if 'selected_ship' not in st.session_state:
    st.session_state.selected_ship = "KMP SEBUKU"

# --- 2. DATA ENGINE ---
@st.cache_data
def load_radar_engine(file_path):
    try:
        ds = xr.open_dataset(file_path)
        ds_clipped = ds.sel(lat=slice(-6.5, -5.5), lon=slice(105.0, 107.0))
        lon, lat = ds_clipped.lon.values, ds_clipped.lat.values
        speed = np.sqrt(ds_clipped.u.isel(time=0).values**2 + ds_clipped.v.isel(time=0).values**2)
        fig, ax = plt.subplots(figsize=(15, 15))
        fig.subplots_adjust(left=0, right=1, bottom=0, top=1); ax.axis('off')
        ax.imshow(speed, extent=[lon.min(), lon.max(), lat.min(), lat.max()], origin='lower', cmap='turbo', alpha=0.6, interpolation='bilinear')
        buf = BytesIO(); plt.savefig(buf, format='png', transparent=True, dpi=200); plt.close(fig)
        return buf, [float(lat.min()), float(lon.min()), float(lat.max()), float(lon.max())], ds_clipped
    except: return None, None, None

# --- 3. MOCK VOYAGE DATA ---
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
            {"time": "+15m", "pos": [-6.18, 105.75], "cond": "☀️ Cerah"},
            {"time": "+30m", "pos": [-6.25, 105.70], "cond": "⛅ Berawan"}
        ]
    }
]

# --- 4. RENDER ---
target_file = "CODAR_BADA_2025_04_12_1400-1744466400.nc"
img_buf, bounds, ds_radar = load_radar_engine(target_file)

if img_buf:
    with st.sidebar:
        st.title("🚢 Voyage Control")
        # Selector ini yang akan memicu perubahan Waypoint di Map
        st.session_state.selected_ship = st.selectbox("Select Vessel for Analysis:", [s['name'] for s in ships], 
                                                     index=[s['name'] for s in ships].index(st.session_state.selected_ship))
        
        v = next(s for s in ships if s['name'] == st.session_state.selected_ship)
        st.subheader("Route Timeline")
        for item in v['timeline']: st.write(f"**{item['time']}** | {item['cond']}")

    m = folium.Map(location=[-6.0, 105.9], zoom_start=11, tiles="CartoDB dark_matter")
    folium.raster_layers.ImageOverlay(np.array(PIL.Image.open(img_buf)), bounds=[[bounds[0], bounds[1]], [bounds[2], bounds[3]]], opacity=0.6).add_to(m)

    for s in ships:
        # Tentukan apakah kapal ini yang sedang dipilih
        is_active = (s['name'] == st.session_state.selected_ship)
        
        # 1. Gambar Lintasan
        folium.PolyLine(locations=s['past_track'], color="#e67e22", weight=2, opacity=0.6).add_to(m)
        line_color = "#00f2ff" if is_active else "#3498db"
        folium.PolyLine(locations=[[s['lat'], s['lon']], s['dest_pos']], color=line_color, weight=4 if is_active else 2, opacity=0.7).add_to(m)
        
        # 2. RENDER WAYPOINTS HANYA JIKA AKTIF
        if is_active:
            for wp in s['timeline']:
                folium.Marker(
                    location=wp['pos'],
                    icon=folium.DivIcon(html=f"""
                        <div style="background: white; border-radius: 6px; padding: 2px; border: 2px solid #00f2ff; 
                        box-shadow: 2px 2px 5px rgba(0,0,0,0.5); text-align: center; width: 35px;">
                            <span style="font-size: 16px;">{wp['cond'].split()[0]}</span>
                        </div>
                    """),
                    tooltip=f"{wp['time']}: {wp['cond']}"
                ).add_to(m)
        
        # 3. Popup Format Sesuai Request
        t_rows = "".join([f"<li><b>{i['time']}</b>: {i['cond']}</li>" for i in s['timeline']])
        p_html = f"""
        <div style="font-family: Arial; width: 220px; font-size: 11px;">
            <b style="color: #2980b9; font-size: 13px;">{s['name']}</b><br>
            <span style="color: gray;">{s['type']}</span><hr style="margin:4px 0;">
            <table style="width: 100%;">
                <tr><td>Speed</td><td>: {s['speed']}</td></tr>
                <tr><td>Course</td><td>: {s['course']}°</td></tr>
                <tr><td>Tujuan</td><td>: {s['dest']}</td></tr>
                <tr><td>ETA</td><td>: {s['eta']}</td></tr>
            </table>
            <hr style="margin:4px 0;">
            <b>Route Forecast:</b>
            <ul style="padding-left: 15px; margin: 5px 0; list-style: none;">
                {t_rows}
            </ul>
        </div>
        """
        
        marker_color = "#00f2ff" if is_active else "#FF4B4B"
        folium.Marker(
            location=[s['lat'], s['lon']], 
            popup=folium.Popup(p_html, max_width=250),
            icon=folium.DivIcon(html=f'<div style="transform: rotate({s["course"]}deg); color:{marker_color}; font-size:26px; text-shadow: 1px 1px 2px #000;">➤</div>')
        ).add_to(m)

    folium_static(m, width=1450, height=850)
