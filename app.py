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
st.set_page_config(
    page_title="Maritime FlightDoc Pro", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
        .block-container { padding: 0rem; background-color: #000000; }
        iframe { width: 100vw; height: 100vh; }
        .stMetric { background-color: #111; padding: 10px; border-radius: 5px; border: 1px solid #333; }
        .stSelectbox label { color: white !important; }
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
        fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
        ax.axis('off')
        ax.imshow(speed, extent=[lon.min(), lon.max(), lat.min(), lat.max()], 
                   origin='lower', cmap='turbo', alpha=0.6, interpolation='bilinear')
        
        buf = BytesIO()
        plt.savefig(buf, format='png', transparent=True, dpi=200)
        plt.close(fig)
        return buf, [float(lat.min()), float(lon.min()), float(lat.max()), float(lon.max())], ds_clipped
    except Exception as e:
        st.error(f"Radar Data Error: {e}")
        return None, None, None

# --- 3. MOCK VOYAGE DATA WITH 15-MIN TIMELINE ---
ships = [
    {
        "name": "KMP SEBUKU", 
        "type": "Ferry", "lat": -5.89, "lon": 105.82, 
        "origin": "Bakauheni", "dest": "MERAK", "dest_pos": [-5.93, 106.00],
        "speed": "10.8 kn", "course": "115", "eta": "11:15 UTC",
        "past_track": [[-5.87, 105.77], [-5.88, 105.79], [-5.89, 105.82]],
        "timeline": [
            {"time": "10:30", "km": "KM 30", "cond": "🌧️ Hujan"},
            {"time": "10:45", "km": "KM 45", "cond": "☁️ Berawan Tebal"},
            {"time": "11:00", "km": "KM 60", "cond": "⛅ Berawan"},
            {"time": "11:15", "km": "Arrival", "cond": "☀️ Cerah"}
        ]
    },
    {
        "name": "MT OCEAN PRIDE", 
        "type": "Tanker", "lat": -6.10, "lon": 105.80, 
        "origin": "Singapore", "dest": "AUSTRALIA", "dest_pos": [-6.50, 105.50],
        "speed": "14.2 kn", "course": "210", "eta": "Apr 15, 04:00",
        "past_track": [[-5.80, 105.95], [-6.10, 105.80]],
        "timeline": [
            {"time": "Now", "km": "ALKI I", "cond": "☀️ Cerah"},
            {"time": "+15m", "km": "KM 10", "cond": "☀️ Cerah"},
            {"time": "+30m", "km": "KM 20", "cond": "⛅ Berawan"}
        ]
    }
]

# --- 4. MAIN RENDER ---
target_file = "CODAR_BADA_2025_04_12_1400-1744466400.nc"

img_buf, bounds, ds_radar = load_radar_engine(target_file)

if img_buf:
    # --- SIDEBAR: VOYAGE CONTROL ---
    with st.sidebar:
        st.title("🚢 Voyage Control")
        selected_name = st.selectbox("Select Vessel for Briefing:", [s['name'] for s in ships])
        
        # Ambil data kapal yang dipilih
        v = next(s for s in ships if s['name'] == selected_name)
        
        st.markdown(f"**Status:** En-route to {v['dest']}")
        st.markdown("---")
        
        st.subheader("⏱️ Route Timeline (15-min)")
        for item in v['timeline']:
            st.markdown(f"**{item['time']}** | {item['km']} : {item['cond']}")
        
        st.info("Weather updated dynamically based on vessel trajectory.")

    # --- MAP RENDER ---
    m = folium.Map(location=[-6.0, 105.9], zoom_start=10, tiles="CartoDB dark_matter")
    
    # Overlay Radar
    img_data = PIL.Image.open(img_buf)
    folium.raster_layers.ImageOverlay(
        np.array(img_data), 
        bounds=[[bounds[0], bounds[1]], [bounds[2], bounds[3]]], 
        opacity=0.6
    ).add_to(m)

    for s in ships:
        # Draw tracks
        folium.PolyLine(locations=s['past_track'], color="#e67e22", weight=3, opacity=0.8, tooltip="Past Track").add_to(m)
        folium.PolyLine(locations=[[s['lat'], s['lon']], s['dest_pos']], color="#3498db", weight=2, opacity=0.6, dash_array='10, 10', tooltip="Expected Route").add_to(m)
        
        # Popup HTML with Timeline
        timeline_rows = "".join([f"<li><b>{i['time']}</b> - {i['cond']}</li>" for i in s['timeline']])
        popup_html = f"""
        <div style="font-family: Arial; width: 220px; font-size: 12px;">
            <b style="color: #2980b9; font-size: 14px;">{s['name']}</b><br>
            <b>ETA:</b> {s['eta']}<hr style="margin:5px 0;">
            <b>Forecast Timeline:</b>
            <ul style="padding-left: 15px; margin-top: 5px; list-style-type: none;">
                {timeline_rows}
            </ul>
        </div>
        """
        
        folium.Marker(
            location=[s['lat'], s['lon']],
            popup=folium.Popup(popup_html, max_width=250),
            icon=folium.DivIcon(html=f'<div style="transform: rotate({s["course"]}deg); color:#00f2ff; font-size:24px; text-shadow: 1px 1px 2px #000;">➤</div>')
        ).add_to(m)

    folium_static(m, width=1450, height=850)
else:
    st.error("Gagal memuat data radar. Pastikan file .nc tersedia.")
