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
        # Kapal Feri (Merak-Bakauheni)
        {"name": "KMP Portlink", "lat": -5.925, "lon": 105.910, "type": "Ferry", "speed": 12, "heading": 280},
        {"name": "KMP Sebuku", "lat": -5.935, "lon": 105.880, "type": "Ferry", "speed": 10, "heading": 100},
        {"name": "KMP Batumandi", "lat": -5.945, "lon": 105.850, "type": "Ferry", "speed": 11, "heading": 285},
        
        # Kapal Kargo/Tanker melintas ALKI
        {"name": "MT Martha Petrol", "lat": -5.850, "lon": 105.800, "type": "Tanker", "speed": 8, "heading": 210},
        {"name": "MV Ocean Voyager", "lat": -6.050, "lon": 105.750, "type": "Cargo", "speed": 15, "heading": 30},
        {"name": "CMA CGM Jakarta", "lat": -6.120, "lon": 105.850, "type": "Container", "speed": 18, "heading": 15},
    ]
    return ships

# --- INSIDE THE MAP RENDERING SECTION ---
ships = get_heavy_ais_data()

for ship in ships:
    # Set warna berdasarkan tipe
    color = '#ff0000' if ship['type'] == 'Ferry' else '#0074D9'
    if ship['type'] == 'Tanker': color = '#FF851B'
    
    # CSS untuk membuat tanda panah yang menunjuk ke arah 'heading'
    # Kita menggunakan simbol '➤' (Unicode) yang dirotasi
    icon_html = f"""
        <div style="
            transform: rotate({ship['heading']}deg);
            color: {color};
            font-size: 25px;
            text-shadow: 2px 2px 4px #000;
            width: 30px;
            height: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
        ">➤</div>
    """
    
    folium.Marker(
        location=[ship['lat'], ship['lon']],
        popup=f"<b>{ship['name']}</b><br>HDG: {ship['heading']}°<br>SPD: {ship['speed']} kts",
        tooltip=ship['name'],
        icon=folium.DivIcon(
            icon_size=(30, 30),
            icon_anchor=(15, 15),
            html=icon_html
        )
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
