import streamlit as st
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import folium
from streamlit_folium import folium_static
import branca.colormap as cm
from io import BytesIO
import PIL.Image
import pandas as pd

# --- KONFIGURASI FULL SCREEN ---
st.set_page_config(page_title="Sunda Strait Command Center", layout="wide")

# CSS Super Clean & Full Screen
st.markdown("""
    <style>
        .block-container { padding: 0rem; }
        iframe { width: 100vw; height: 100vh; }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stApp { bottom: 0; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def get_vibrant_overlay(file_path):
    ds = xr.open_dataset(file_path)
    # Clip Boundary Selat Sunda
    ds = ds.sel(lat=slice(-6.2, -5.7), lon=slice(105.7, 106.1))
    
    lon, lat = ds.lon.values, ds.lat.values
    speed = np.sqrt(ds.u.isel(time=0).values**2 + ds.v.isel(time=0).values**2)
    
    fig, ax = plt.subplots(figsize=(15, 15))
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    ax.axis('off')
    
    # Warna Turbo yang mencolok
    im = ax.imshow(speed, extent=[lon.min(), lon.max(), lat.min(), lat.max()], 
                   origin='lower', cmap='turbo', alpha=0.8, interpolation='bilinear')
    
    buf = BytesIO()
    plt.savefig(buf, format='png', transparent=True, dpi=200)
    plt.close(fig)
    
    bounds = [float(lat.min()), float(lon.min()), float(lat.max()), float(lon.max())]
    return buf, bounds, speed

# --- GENERATE MOCK AIS DATA (RAME & LENGKAP) ---
def get_heavy_ais_data():
    ships = [
        # Kapal Feri Lintas Merak - Bakauheni
        {"name": "KMP Portlink", "lat": -5.925, "lon": 105.910, "type": "Ferry", "speed": 12},
        {"name": "KMP Sebuku", "lat": -5.935, "lon": 105.880, "type": "Ferry", "speed": 10},
        {"name": "KMP Batumandi", "lat": -5.945, "lon": 105.850, "type": "Ferry", "speed": 11},
        {"name": "KMP Legundi", "lat": -5.915, "lon": 105.930, "type": "Ferry", "speed": 13},
        {"name": "KMP Jatra III", "lat": -5.920, "lon": 105.950, "type": "Ferry", "speed": 0}, # Anchored
        
        # Kapal Kargo & Tanker Melintas
        {"name": "MT Martha Petrol", "lat": -5.850, "lon": 105.800, "type": "Tanker", "speed": 8},
        {"name": "MV Ocean Voyager", "lat": -6.050, "lon": 105.750, "type": "Cargo", "speed": 15},
        {"name": "CMA CGM Jakarta", "lat": -6.120, "lon": 105.850, "type": "Container", "speed": 18},
        {"name": "Maersk Sunda", "lat": -5.780, "lon": 105.980, "type": "Container", "speed": 16},
        
        # Kapal Nelayan & Patroli
        {"name": "KN Trisula", "lat": -5.980, "lon": 105.950, "type": "Patrol", "speed": 22},
        {"name": "KM Nelayan Maju", "lat": -6.020, "lon": 106.020, "type": "Fishing", "speed": 4},
        {"name": "KM Sumber Rejeki", "lat": -5.820, "lon": 105.880, "type": "Fishing", "speed": 5},
    ]
    return ships

target_file = "CODAR_BADA_2025_04_12_1400-1744466400.nc"

try:
    img_buf, bounds, speed_data = get_vibrant_overlay(target_file)
    ships = get_heavy_ais_data()
    
    # Create Map
    m = folium.Map(
        location=[-5.95, 105.9], 
        zoom_start=11, 
        tiles="CartoDB dark_matter",
        zoom_control=True
    )
    
    # 1. Overlay Arus
    img = PIL.Image.open(img_buf)
    folium.raster_layers.ImageOverlay(
        image=np.array(img),
        bounds=[[bounds[0], bounds[1]], [bounds[2], bounds[3]]],
        opacity=0.85,
        zindex=1
    ).add_to(m)

    # 2. Tambahkan Kapal AIS (Rame)
    for ship in ships:
        # Tentukan warna icon berdasarkan tipe
        color = 'red' if ship['type'] == 'Ferry' else 'blue'
        color = 'green' if ship['type'] == 'Patrol' else color
        color = 'orange' if ship['type'] == 'Fishing' else color
        
        icon_type = 'ship' if ship['speed'] > 0 else 'anchor'
        
        folium.Marker(
            location=[ship['lat'], ship['lon']],
            popup=f"<b>{ship['name']}</b><br>Type: {ship['type']}<br>Speed: {ship['speed']} kts",
            tooltip=ship['name'],
            icon=folium.Icon(color=color, icon=icon_type, prefix='fa')
        ).add_to(m)

    # 3. Colormap
    max_val = float(np.nanmax(speed_data)) if not np.all(np.isnan(speed_data)) else 2.5
    colormap = cm.LinearColormap(
        colors=['#30123b', '#4145ab', '#4672f1', '#2eb67d', '#f8e621', '#c72200'], 
        vmin=0, vmax=max_val,
        caption='Surface Current Speed (m/s)'
    )
    colormap.add_to(m)

    # Render Full Screen
    folium_static(m, width=1450, height=850)

except Exception as e:
    st.error(f"Error: {e}")
