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
    page_title="Maritime Pro", 
    layout="wide",
    initial_sidebar_state="expanded" 
)

st.markdown("""
    <style>
        .block-container { padding: 0rem; background-color: #000000; }
        iframe { width: 100vw; height: 100vh; }
        .stMetric { background-color: #111; padding: 10px; border-radius: 5px; border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
@st.cache_data
def load_radar_pro(file_path):
    ds = xr.open_dataset(file_path)
    ds_clipped = ds.sel(lat=slice(-6.5, -5.5), lon=slice(105.0, 107.0)) # Zoom out sedikit
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

# --- 3. ENRICHED AIS MOCK DATA ---
ships = [
    {
        "name": "KMP SATRIA NUSANTARA", 
        "type": "Ferry", "lat": -5.93, "lon": 105.97, 
        "origin": "Merak", "dest": "BAKAUHENI", "dest_pos": [-5.87, 105.76],
        "past_track": [[-5.93, 105.99], [-5.94, 105.98], [-5.93, 105.97]],
        "speed": "12.4 kn", "course": "285", "eta": "10:45 UTC", "weather": "☀️ Cerah", "color": "cyan"
    },
    {
        "name": "MT OCEAN PRIDE", 
        "type": "Crude Oil Tanker", "lat": -6.10, "lon": 105.80, 
        "origin": "Singapore", "dest": "AUSTRALIA", "dest_pos": [-6.50, 105.50],
        "past_track": [[-5.80, 105.95], [-5.95, 105.90], [-6.10, 105.80]],
        "speed": "14.2 kn", "course": "210", "eta": "Apr 15, 04:00", "weather": "🌧️ Hujan Ringan", "color": "#f1c40f"
    },
    {
        "name": "KMP SEBUKU", 
        "type": "Ferry", "lat": -5.89, "lon": 105.82, 
        "origin": "Bakauheni", "dest": "MERAK", "dest_pos": [-5.93, 106.00],
        "past_track": [[-5.87, 105.77], [-5.88, 105.79], [-5.89, 105.82]],
        "speed": "10.8 kn", "course": "115", "eta": "11:15 UTC", "weather": "⚡ Badai Petir", "color": "cyan"
    }
]

# --- 4. MAIN RENDER ---
target_file = "CODAR_BADA_2025_04_12_1400-1744466400.nc"

try:
    img_buf, bounds, ds_radar = load_radar_pro(target_file)
    
    with st.sidebar:
        st.title("🚢 Voyage Control")
        selected_vessel = st.selectbox("Select Vessel:", [s['name'] for s in ships])
        v = next(s for s in ships if s['name'] == selected_vessel)
        st.markdown(f"**Status:** En-route from {v['origin']} to {v['dest']}")
        st.metric("Weather", v['weather'])
        st.info("Past track (Orange) & Expected Route (Blue) are visible on map.")

    m = folium.Map(location=[-6.0, 105.9], zoom_start=10, tiles="CartoDB dark_matter")
    
    # Radar Overlay
    img_data = PIL.Image.open(img_buf)
    folium.raster_layers.ImageOverlay(np.array(img_data), bounds=[[bounds[0], bounds[1]], [bounds[2], bounds[3]]], opacity=0.6).add_to(m)

    for s in ships:
        # 1. DRAW PAST TRACK (Jejak Masa Lalu - Warna Oranye)
        folium.PolyLine(locations=s['past_track'], color="#e67e22", weight=3, opacity=0.8, tooltip="Past Track").add_to(m)
        
        # 2. DRAW EXPECTED ROUTE (Jalur ke Tujuan - Putus-putus Biru)
        folium.PolyLine(locations=[[s['lat'], s['lon']], s['dest_pos']], color="#3498db", weight=2, opacity=0.6, dash_array='10, 10', tooltip="Expected Route").add_to(m)
        
        # POPUP HTML
        popup_html = f"""
        <div style="font-family: sans-serif; width: 220px;">
            <b style="color: #2980b9;">{s['name']}</b><br>
            <small>{s['type']}</small><hr style="margin:5px 0;">
            <table style="width:100%; font-size:11px;">
                <tr><td><b>From:</b></td><td>{s['origin']}</td></tr>
                <tr><td><b>To:</b></td><td>{s['dest']}</td></tr>
                <tr><td><b>Speed:</b></td><td>{s['speed']}</td></tr>
                <tr><td><b>Weather:</b></td><td>{s['weather']}</td></tr>
            </table>
        </div>
        """
        
        # Marker Kapal (Arrow)
        arrow_color = "#3498db" if s['type'] == "Ferry" else "#f1c40f"
        folium.Marker(
            location=[s['lat'], s['lon']],
            popup=folium.Popup(popup_html, max_width=250),
            icon=folium.DivIcon(html=f'<div style="transform: rotate({s["course"]}deg); color:{arrow_color}; font-size:24px; text-shadow: 1px 1px 2px #000;">➤</div>')
        ).add_to(m)

    folium_static(m, width=1450, height=850)

except Exception as e:
    st.error(f"Error: {e}")
