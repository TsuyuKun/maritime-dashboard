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
    page_title="Maritime FlightDoc", 
    layout="wide",
    initial_sidebar_state="expanded" 
)

# CSS diperbaiki agar sidebar tidak hilang
st.markdown("""
    <style>
        .block-container { padding: 0rem; background-color: #000000; }
        iframe { width: 100vw; height: 100vh; }
        .stMetric { background-color: #111; padding: 10px; border-radius: 5px; border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

if 'active_vessel' not in st.session_state:
    st.session_state.active_vessel = "KMP Portlink"

# --- 2. DATA ENGINE ---
@st.cache_data
def load_radar_engine(file_path):
    ds = xr.open_dataset(file_path)
    ds_clipped = ds.sel(lat=slice(-6.2, -5.7), lon=slice(105.7, 106.1))
    lon, lat = ds_clipped.lon.values, ds_clipped.lat.values
    speed = np.sqrt(ds_clipped.u.isel(time=0).values**2 + ds_clipped.v.isel(time=0).values**2)
    fig, ax = plt.subplots(figsize=(15, 15))
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    ax.axis('off')
    ax.imshow(speed, extent=[lon.min(), lon.max(), lat.min(), lat.max()], 
               origin='lower', cmap='turbo', alpha=0.75, interpolation='bilinear')
    buf = BytesIO()
    plt.savefig(buf, format='png', transparent=True, dpi=200)
    plt.close(fig)
    return buf, [float(lat.min()), float(lon.min()), float(lat.max()), float(lon.max())], ds_clipped

def get_route_profile(ds, start_pos, end_pos):
    steps = 40
    lats = np.linspace(start_pos[0], end_pos[0], steps)
    lons = np.linspace(start_pos[1], end_pos[1], steps)
    speeds = [float(np.sqrt(ds.sel(lat=la, lon=lo, method="nearest").u.isel(time=0)**2 + 
                            ds.sel(lat=la, lon=lo, method="nearest").v.isel(time=0)**2)) 
              for la, lo in zip(lats, lons)]
    return speeds

# --- 3. MOCK DATA DENGAN INFO CUACA ---
ships = [
    {
        "name": "KMP Portlink", "lat": -5.925, "lon": 105.910, "dest": "BAKAUHENI", "dest_pos": [-5.87, 105.76], 
        "speed": "12.4 kn", "course": "285", "eta": "10:45 UTC",
        "weather": "⚡ Badai Petir", "color": "red"
    },
    {
        "name": "KMP Sebuku", "lat": -5.935, "lon": 105.880, "dest": "MERAK", "dest_pos": [-5.93, 106.00], 
        "speed": "10.2 kn", "course": "105", "eta": "11:10 UTC",
        "weather": "☀️ Cerah", "color": "green"
    },
    {
        "name": "KMP Batumandi", "lat": -5.945, "lon": 105.850, "dest": "BAKAUHENI", "dest_pos": [-5.87, 105.76], 
        "speed": "11.0 kn", "course": "280", "eta": "11:30 UTC",
        "weather": "🌧️ Hujan Ringan", "color": "orange"
    },
]

# --- 4. RENDER ---
target_file = "CODAR_BADA_2025_04_12_1400-1744466400.nc"

try:
    img_buf, bounds, ds_radar = load_radar_engine(target_file)
    
    # --- SIDEBAR (Tetap Ada untuk Grafik) ---
    with st.sidebar:
        st.title("📊 Route Analysis")
        st.session_state.active_vessel = st.selectbox("Kapal Terpilih:", [s['name'] for s in ships])
        v_active = next(s for s in ships if s['name'] == st.session_state.active_vessel)
        r_data = get_route_profile(ds_radar, [v_active['lat'], v_active['lon']], v_active['dest_pos'])
        fig = go.Figure(go.Scatter(y=r_data, fill='tozeroy', line=dict(color='#00f2ff')))
        fig.update_layout(template="plotly_dark", height=200, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)
        st.info(f"Rute: {st.session_state.active_vessel} ➔ {v_active['dest']}")

    # --- MAP ---
    m = folium.Map(location=[-5.94, 105.88], zoom_start=11, tiles="CartoDB dark_matter")
    img_data = PIL.Image.open(img_buf)
    folium.raster_layers.ImageOverlay(np.array(img_data), bounds=[[bounds[0], bounds[1]], [bounds[2], bounds[3]]], opacity=0.7).add_to(m)

    for s in ships:
        # POPUP DENGAN INFO CUACA
        popup_html = f"""
        <div style="font-family: sans-serif; width: 200px;">
            <b style="font-size: 14px; color: #007bff;">{s['name']}</b><br>
            <hr style="margin: 5px 0;">
            <table style="width: 100%; font-size: 12px;">
                <tr><td><b>Dest:</b></td><td>{s['dest']}</td></tr>
                <tr><td><b>Speed:</b></td><td>{s['speed']}</td></tr>
                <tr><td><b>Course:</b></td><td>{s['course']}°</td></tr>
                <tr><td><b>ETA:</b></td><td>{s['eta']}</td></tr>
                <tr><td><b>Weather:</b></td><td style="color:{s['color']};"><b>{s['weather']}</b></td></tr>
            </table>
            <p style="font-size: 10px; color: gray; margin-top: 10px;">Lihat profil arus di sidebar (tombol &gt; di kiri atas)</p>
        </div>
        """
        
        folium.Marker(
            location=[s['lat'], s['lon']],
            popup=folium.Popup(popup_html, max_width=250),
            icon=folium.DivIcon(html=f'<div style="transform: rotate({s["course"]}deg); color:#FF4B4B; font-size:26px;">➤</div>')
        ).add_to(m)

    folium_static(m, width=1450, height=850)

except Exception as e:
    st.error(f"Error: {e}")
