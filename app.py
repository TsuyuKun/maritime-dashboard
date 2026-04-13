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

# --- 1. CONFIG & UI STYLING ---
st.set_page_config(page_title="Maritime Crossing Monitor - FlightDoc", layout="wide")

# CSS untuk tampilan Command Center Profesional
st.markdown("""
    <style>
        .block-container { padding: 0rem; background-color: #000000; }
        iframe { width: 100vw; height: 100vh; }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stMetric { background-color: #111; padding: 10px; border-radius: 5px; border: 1px solid #333; }
        .stAlert { background-color: #1a1a1a; border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

# Session State untuk tracking kapal yang dipilih
if 'active_vessel' not in st.session_state:
    st.session_state.active_vessel = "KMP Portlink"

# --- 2. DATA ENGINE ---
@st.cache_data
def load_and_render_radar(file_path):
    ds = xr.open_dataset(file_path)
    # Fokus area penyeberangan Selat Sunda
    ds_clipped = ds.sel(lat=slice(-6.2, -5.7), lon=slice(105.7, 106.1))
    
    lon, lat = ds_clipped.lon.values, ds_clipped.lat.values
    speed = np.sqrt(ds_clipped.u.isel(time=0).values**2 + ds_clipped.v.isel(time=0).values**2)
    
    fig, ax = plt.subplots(figsize=(15, 15))
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    ax.axis('off')
    # Interpolasi bilinear agar shading halus (tidak kotak-kotak)
    ax.imshow(speed, extent=[lon.min(), lon.max(), lat.min(), lat.max()], 
               origin='lower', cmap='turbo', alpha=0.75, interpolation='bilinear')
    
    buf = BytesIO()
    plt.savefig(buf, format='png', transparent=True, dpi=200)
    plt.close(fig)
    
    bounds = [float(lat.min()), float(lon.min()), float(lat.max()), float(lon.max())]
    return buf, bounds, ds_clipped

def get_route_profile(ds, start_pos, end_pos):
    steps = 40
    lats = np.linspace(start_pos[0], end_pos[0], steps)
    lons = np.linspace(start_pos[1], end_pos[1], steps)
    
    speeds = []
    for i in range(steps):
        p = ds.sel(lat=lats[i], lon=lons[i], method="nearest")
        s = np.sqrt(p.u.isel(time=0).values**2 + p.v.isel(time=0).values**2)
        speeds.append(float(s))
    return speeds

# --- 3. MOCK VOYAGE DATA (AIS & WEATHER) ---
ships = [
    {
        "name": "KMP Portlink", "lat": -5.925, "lon": 105.910, "dest": "BAKAUHENI", "dest_pos": [-5.87, 105.76], 
        "speed": "12.4 kn", "course": "285", "eta": "10:45 UTC",
        "weather": "⚡ Badai Petir", "weather_desc": "Terdeteksi squall line di tengah selat. Jarak pandang turun ke 3km.",
        "status": "warning"
    },
    {
        "name": "KMP Sebuku", "lat": -5.935, "lon": 105.880, "dest": "MERAK", "dest_pos": [-5.93, 106.00], 
        "speed": "10.2 kn", "course": "105", "eta": "11:10 UTC",
        "weather": "☀️ Cerah", "weather_desc": "Kondisi stabil di sepanjang rute. Navigasi optimal.",
        "status": "success"
    },
    {
        "name": "KMP Batumandi", "lat": -5.945, "lon": 105.850, "dest": "BAKAUHENI", "dest_pos": [-5.87, 105.76], 
        "speed": "11.0 kn", "course": "280", "eta": "11:30 UTC",
        "weather": "🌧️ Hujan Ringan", "weather_desc": "Hujan di area dermaga tujuan. Waspada dek licin & visibility sedang.",
        "status": "info"
    },
]

# --- 4. MAIN RENDER ---
target_file = "CODAR_BADA_2025_04_12_1400-1744466400.nc"

try:
    img_buf, bounds, ds_radar = load_and_render_radar(target_file)
    
    # --- SIDEBAR: FLIGHTDOC INTERFACE ---
    with st.sidebar:
        st.title("📋 Maritime FlightDoc")
        st.session_state.active_vessel = st.selectbox("Select Vessel Analysis:", [s['name'] for s in ships], 
                                                     index=[s['name'] for s in ships].index(st.session_state.active_vessel))
        
        v = next(s for s in ships if s['name'] == st.session_state.active_vessel)
        
        # Grafik Profil Arus Unik
        route_data = get_route_profile(ds_radar, [v['lat'], v['lon']], v['dest_pos'])
        fig = go.Figure(go.Scatter(y=route_data, fill='tozeroy', line=dict(color='#00f2ff', width=3)))
        fig.update_layout(
            title="En-route Current Load (m/s)", template="plotly_dark", height=230, 
            margin=dict(l=0,r=0,t=40,b=0), xaxis_title="Departure ➔ Arrival"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Info Cuaca Taktis
        st.subheader(f"Weather: {v['weather']}")
        if v['status'] == "warning": st.error(v['weather_desc'])
        elif v['status'] == "info": st.info(v['weather_desc'])
        else: st.success(v['weather_desc'])
        
        st.markdown("---")
        c1, c2 = st.columns(2)
        c1.metric("Avg Current", f"{np.mean(route_data):.2f} m/s")
        c2.metric("ETA Status", "On Time")

    # --- MAP RENDER ---
    m = folium.Map(location=[-5.94, 105.88], zoom_start=11, tiles="CartoDB dark_matter")
    
    # Overlay Shading Arus
    img_data = PIL.Image.open(img_buf)
    folium.raster_layers.ImageOverlay(
        np.array(img_data), bounds=[[bounds[0], bounds[1]], [bounds[2], bounds[3]]], 
        opacity=0.75, zindex=1
    ).add_to(m)

    # Ikon Kapal & Popup
    for s in ships:
        # Garis rute virtual (Flight path)
        folium.PolyLine(
            locations=[[s['lat'], s['lon']], s['dest_pos']],
            color="#00f2ff", weight=1, opacity=0.3, dash_array='5, 10'
        ).add_to(m)
        
        # Konten Popup ala MarineTraffic
        popup_content = f"""
        <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; width: 180px;">
            <b style="font-size: 14px; color: #007bff;">{s['name']}</b><br>
            <span style="font-size: 11px; color: gray;">RO-RO PASSENGER</span>
            <hr style="margin: 5px 0;">
            <table style="width: 100%; font-size: 12px;">
                <tr><td><b>Dest:</b></td><td>{s['dest']}</td></tr>
                <tr><td><b>Speed:</b></td><td>{s['speed']}</td></tr>
                <tr><td><b>Course:</b></td><td>{s['course']}°</td></tr>
                <tr><td><b>ETA:</b></td><td>{s['eta']}</td></tr>
            </table>
            <div style="margin-top: 8px; font-size: 10px; background: #eee; padding: 3px; border-radius: 3px; text-align: center;">
                Check Sidebar for Route Forecast
            </div>
        </div>
        """
        
        icon_color = "#00f2ff" if s['name'] == st.session_state.active_vessel else "#FF4B4B"
        folium.Marker(
            location=[s['lat'], s['lon']],
            popup=folium.Popup(popup_content, max_width=250),
            tooltip=s['name'],
            icon=folium.DivIcon(html=f'<div style="transform: rotate({s["course"]}deg); color:{icon_color}; font-size:28px; text-shadow: 1px 1px 2px #000;">➤</div>')
        ).add_to(m)

    # Legend Colormap
    cm.LinearColormap(
        colors=['#30123b', '#4145ab', '#4672f1', '#2eb67d', '#f8e621', '#c72200'], 
        vmin=0, vmax=2.0, caption='Surface Current Velocity (m/s)'
    ).add_to(m)

    folium_static(m, width=1450, height=850)

except Exception as e:
    st.error(f"Operational Error: {e}")
