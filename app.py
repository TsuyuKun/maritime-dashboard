import streamlit as st
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import folium
from streamlit_folium import folium_static
import PIL.Image
from io import BytesIO
import json

# --- 1. CONFIG ---
st.set_page_config(page_title="Maritime FlightDoc Pro", layout="wide")

st.markdown("""
    <style>
        .block-container { padding: 0rem; background-color: #000000; }
        #MainMenu, footer, header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

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
# Data dikirim ke JS sebagai objek JSON
ships_data = [
    {
        "name": "KMP SEBUKU", "lat": -5.89, "lon": 105.82, "course": 115,
        "dest_pos": [-5.93, 106.00],
        "timeline": [
            {"pos": [-5.90, 105.86], "icon": "🌧️"},
            {"time": "11:15", "pos": [-5.93, 106.00], "icon": "☀️"}
        ]
    },
    {
        "name": "MT OCEAN PRIDE", "lat": -6.10, "lon": 105.80, "course": 210,
        "dest_pos": [-6.50, 105.50],
        "timeline": [
            {"pos": [-6.10, 105.80], "icon": "☀️"},
            {"pos": [-6.25, 105.70], "icon": "⛅"}
        ]
    }
]

# --- 4. MAP RENDER ---
img_buf, bounds = get_radar_overlay("CODAR_BADA_2025_04_12_1400-1744466400.nc")
m = folium.Map(location=[-6.0, 105.9], zoom_start=11, tiles="CartoDB dark_matter")

if img_buf:
    folium.raster_layers.ImageOverlay(np.array(PIL.Image.open(img_buf)), bounds=[[bounds[0], bounds[1]], [bounds[2], bounds[3]]], opacity=0.6).add_to(m)

# Tambahkan Kapal & Logic via JS
for s in ships_data:
    # Buat grup khusus untuk waypoints kapal ini (default: tidak muncul di peta)
    wp_group_name = f"wp_{s['name'].replace(' ', '_')}"
    wp_group = folium.FeatureGroup(name=wp_group_name, show=False).add_to(m)
    
    # Tambahkan Waypoints ke grup
    for wp in s['timeline']:
        folium.Marker(
            location=wp['pos'],
            icon=folium.DivIcon(html=f'<div style="background:white; border-radius:4px; padding:2px; border:1px solid cyan; font-size:14px; text-align:center; width:30px;">{wp["icon"]}</div>')
        ).add_to(wp_group)

    # Tambahkan Jalur (Expected Route)
    route = folium.PolyLine(locations=[[s['lat'], s['lon']], s['dest_pos']], color="#3498db", weight=2, opacity=0.7).add_to(m)

    # Tambahkan Marker Kapal dengan Event Click JS
    marker = folium.Marker(
        location=[s['lat'], s['lon']],
        icon=folium.DivIcon(html=f'<div style="transform:rotate({s["course"]}deg); color:#FF4B4B; font-size:26px; cursor:pointer;">➤</div>')
    ).add_to(m)

    # --- JAVASCRIPT INJECTION ---
    # Saat marker diklik:
    # 1. Sembunyikan semua grup waypoint lain.
    # 2. Tampilkan grup waypoint kapal ini.
    # 3. Ubah warna rute kapal ini menjadi Cyan.
    
    marker_id = marker.get_name()
    wp_id = wp_group.get_name()
    route_id = route.get_name()

    click_js = f"""
    function clickHandler() {{
        // Reset semua rute & sembunyikan semua waypoints
        var allLayers = {m.get_name()}._layers;
        for (var key in allLayers) {{
            if (allLayers[key] instanceof L.PolyLine) {{
                allLayers[key].setStyle({{color: '#3498db', weight: 2}});
            }}
            if (allLayers[key] instanceof L.FeatureGroup && allLayers[key].options.name && allLayers[key].options.name.startsWith('wp_')) {{
                {m.get_name()}.removeLayer(allLayers[key]);
            }}
        }}
        // Aktifkan yang dipilih
        {m.get_name()}.addLayer({wp_id});
        {route_id}.setStyle({{color: '#00f2ff', weight: 5}});
    }}
    
    document.getElementById('{marker_id}').addEventListener('click', clickHandler);
    """
    # Menyuntikkan script ke peta
    m.get_root().script.add_child(folium.Element(click_js))

# Render ke Streamlit
folium_static(m, width=1550, height=900
