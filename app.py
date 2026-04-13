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

# --- 3. MOCK VOYAGE DATA WITH COORDINATED WAYPOINTS ---
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

# --- 4. RENDER ---
target_file = "CODAR_BADA_2025_04_12_1400-1744466400.nc"
img_buf, bounds, ds_radar = load_radar_engine(target_file)

if img_buf:
    with st.sidebar:
        st.title("🚢 Voyage Control")
        selected_name = st.selectbox("Select Vessel:", [s['name'] for s in ships])
        v = next(s for s in ships if s['name'] == selected_name)
        st.subheader("Route Timeline")
        for item in v['timeline']: st.write(f"**{item['time']}** | {item['cond']}")

    m = folium.Map(location=[-6.0, 105.9], zoom_start=11, tiles="CartoDB dark_matter")
    folium.raster_layers.ImageOverlay(np.array(PIL.Image.open(img_buf)), bounds=[[bounds[0], bounds[1]], [bounds[2], bounds[3]]], opacity=0.6).add_to(m)

    for s in ships:
        # 1. Past Track & Expected Route
        folium.PolyLine(locations=s['past_track'], color="#e67e22", weight=3, opacity=0.8).add_to(m)
        folium.PolyLine(locations=[[s['lat'], s['lon']], s['dest_pos']], color="#3498db", weight=4, opacity=0.6).add_to(m)
        
        # 2. Weather Waypoints (Ikon di Peta)
        for wp in s['timeline']:
            folium.Marker(
                location=wp['pos'],
                icon=folium.DivIcon(html=f"""
                    <div style="background: white; border-radius: 8px; padding: 4px; border: 2px solid #3498db; 
                    box-shadow: 2px 2px 5px rgba(0,0,0,0.5); text-align: center; width: 40px;">
                        <span style="font-size: 18px;">{wp['cond'].split()[0]}</span>
                    </div>
                """),
                tooltip=f"Forecast {wp['time']}: {wp['cond']}"
            ).add_to(m)
        
        # 3. Popup dengan Format Baru
        t_rows = "".join([f"<li><b>{i['time']}</b>: {i['cond']}</li>" for i in s['timeline']])
        p_html = f"""
        <div style="font-family: 'Segoe UI', Arial; width: 220px; font-size: 12px;">
            <b style="color: #2980b9; font-size: 14px;">{s['name']}</b><br>
            <span style="color: gray;">{s['type']}</span><hr style="margin:5px 0;">
            <table style="width: 100%;">
                <tr><td><b>Speed</b></td><td>: {s['speed']}</td></tr>
                <tr><td><b>Course</b></td><td>: {s['course']}°</td></tr>
                <tr><td><b>Tujuan</b></td><td>: {s['dest']}</td></tr>
                <tr><td><b>ETA</b></td><td>: {s['eta']}</td></tr>
            </table>
            <hr style="margin:5px 0;">
            <b>Route Forecast:</b>
            <ul style="padding-left: 15px; margin: 5px 0; list-style: none;">
                {t_rows}
            </ul>
        </div>
        """
        
        folium.Marker(
            location=[s['lat'], s['lon']], 
            popup=folium.Popup(p_html, max_width=250),
            icon=folium.DivIcon(html=f'<div style="transform: rotate({s["course"]}deg); color:#00f2ff; font-size:28px; text-shadow: 1px 1px 2px #000;">➤</div>')
        ).add_to(m)

    folium_static(m, width=1450, height=850)
