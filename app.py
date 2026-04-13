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
st.set_page_config(page_title="Maritime FlightDoc Dashboard", layout="wide")

# CSS untuk Command Center Look (Full Screen)
st.markdown("""
    <style>
        .block-container { padding: 0rem; background-color: #000000; }
        iframe { width: 100vw; height: 100vh; }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stMetric { background-color: #111; padding: 10px; border-radius: 5px; border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE (Radar & Route) ---
@st.cache_data
def load_and_process_radar(file_path):
    ds = xr.open_dataset(file_path)
    # Clip Boundary: Fokus Selat Sunda
    ds_clipped = ds.sel(lat=slice(-6.2, -5.7), lon=slice(105.7, 106.1))
    
    lon, lat = ds_clipped.lon.values, ds_clipped.lat.values
    speed = np.sqrt(ds_clipped.u.isel(time=0).values**2 + ds_clipped.v.isel(time=0).values**2)
    
    # Render Shading ke PNG (Flattening)
    fig, ax = plt.subplots(figsize=(15, 15))
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    ax.axis('off')
    ax.imshow(speed, extent=[lon.min(), lon.max(), lat.min(), lat.max()], 
               origin='lower', cmap='turbo', alpha=0.75, interpolation='bilinear')
    
    buf = BytesIO()
    plt.savefig(buf, format='png', transparent=True, dpi=200)
    plt.close(fig)
    
    bounds = [float(lat.min()), float(lon.min()), float(lat.max()), float(lon.max())]
    return buf, bounds, ds_clipped

def get_unique_route_profile(ds, start_pos, end_pos, steps=40):
    """Menghitung profil arus di sepanjang rute spesifik kapal"""
    lats = np.linspace(start_pos[0], end_pos[0], steps)
    lons = np.linspace(start_pos[1], end_pos[1], steps)
    
    route_speeds = []
    for i in range(steps):
        # Sampling data terdekat di grid radar
        p = ds.sel(lat=lats[i], lon=lons[i], method="nearest")
        s = np.sqrt(p.u.isel(time=0).values**2 + p.v.isel(time=0).values**2)
        route_speeds.append(float(s))
    return route_speeds

# --- 3. MOCK VOYAGE DATA (AIS) ---
def get_voyage_data():
    return [
        {"name": "KMP Portlink", "lat": -5.925, "lon": 105.910, "dest": "Bakauheni", "dest_pos": [-5.87, 105.76], "heading": 285, "type": "Ferry", "wind": "12 kts"},
        {"name": "KMP Sebuku", "lat": -5.935, "lon": 105.880, "dest": "Merak", "dest_pos": [-5.93, 106.00], "heading": 105, "type": "Ferry", "wind": "10 kts"},
        {"name": "KMP Batumandi", "lat": -5.945, "lon": 105.850, "dest": "Bakauheni", "dest_pos": [-5.87, 105.76], "heading": 280, "type": "Ferry", "wind": "14 kts"},
    ]

# --- 4. MAIN APP ---
target_file = "CODAR_BADA_2025_04_12_1400-1744466400.nc"

try:
    img_buf, bounds, ds_radar = load_and_process_radar(target_file)
    ships = get_voyage_data()

    # --- SIDEBAR: MARITIME FLIGHTDOC ---
    with st.sidebar:
        st.title("📋 FlightDoc")
        selected_name = st.selectbox("Select Vessel for Briefing:", [s['name'] for s in ships])
        ship = next(s for s in ships if s['name'] == selected_name)
        
        st.markdown(f"**Target:** {ship['dest']} | **ETA:** 10:45 UTC")
        
        # Hitung Route Forecast unik
        route_profile = get_unique_route_profile(ds_radar, [ship['lat'], ship['lon']], ship['dest_pos'])
        
        # Plotly Profile Chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=route_profile, fill='tozeroy', line=dict(color='#00f2ff', width=3)))
        fig.update_layout(
            title="Current Load Profile (En-route)",
            xaxis_title="Route Progress (%)", yaxis_title="Current (m/s)",
            template="plotly_dark", height=250, margin=dict(l=10, r=10, t=40, b=10)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # FlightDoc Metrics
        c1, c2 = st.columns(2)
        c1.metric("Avg Current", f"{np.mean(route_profile):.2f} m/s")
        c2.metric("Wind Feed", ship['wind'])
        
        st.warning(f"🚩 **Briefing:** Peak current at middle passage. Anticipate drift toward North-East.")

    # --- MAIN MAP ---
    m = folium.Map(location=[-5.94, 105.88], zoom_start=11, tiles="CartoDB dark_matter")
    
    # 1. Layer Arus
    img = PIL.Image.open(img_buf)
    folium.raster_layers.ImageOverlay(
        image=np.array(img), bounds=[[bounds[0], bounds[1]], [bounds[2], bounds[3]]],
        opacity=0.8, zindex=1
    ).add_to(m)

    # 2. Layer Kapal & Jalur Spesifik
    for s in ships:
        # Garis lintasan unik kapal (Flight Path)
        folium.PolyLine(
            locations=[[s['lat'], s['lon']], s['dest_pos']],
            color="#00f2ff", weight=1.5, opacity=0.4, dash_array='5, 10'
        ).add_to(m)
        
        # Arrow Marker (Heading aware)
        icon_color = "#FF4B4B" if s['name'] == selected_name else "#555"
        icon_html = f'<div style="transform: rotate({s["heading"]}deg); color: {icon_color}; font-size: 26px; text-shadow: 1px 1px 2px #000;">➤</div>'
        
        folium.Marker(
            location=[s['lat'], s['lon']],
            tooltip=f"{s['name']} (To: {s['dest']})",
            icon=folium.DivIcon(icon_size=(30,30), icon_anchor=(15,15), html=icon_html)
        ).add_to(m)

    # 3. Colormap Legend
    colormap = cm.LinearColormap(
        colors=['#30123b', '#4145ab', '#4672f1', '#2eb67d', '#f8e621', '#c72200'], 
        vmin=0, vmax=2.0, caption='Surface Velocity (m/s)'
    )
    colormap.add_to(m)

    folium_static(m, width=1450, height=850)

except Exception as e:
    st.error(f"System Error: {e}")
