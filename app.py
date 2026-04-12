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

# --- 1. PAGE CONFIGURATION & FULL SCREEN CSS ---
st.set_page_config(page_title="Sunda Strait Command Center", layout="wide")

# This CSS hides the Streamlit UI and forces the map to be full screen
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

# --- 2. DATA PROCESSING (SHADED OVERLAY) ---
@st.cache_data
def get_vibrant_overlay(file_path):
    # Load dataset
    ds = xr.open_dataset(file_path)
    
    # Clip Boundary: Focusing specifically on the Sunda Strait crossing area
    ds = ds.sel(lat=slice(-6.2, -5.7), lon=slice(105.7, 106.1))
    
    lon, lat = ds.lon.values, ds.lat.values
    u = ds.u.isel(time=0).values
    v = ds.v.isel(time=0).values
    speed = np.sqrt(u**2 + v**2)
    
    # Render High-Quality Flattened Shading
    fig, ax = plt.subplots(figsize=(15, 15))
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    ax.axis('off')
    
    # Using 'turbo' colormap for high-visibility operasional shading
    ax.imshow(speed, extent=[lon.min(), lon.max(), lat.min(), lat.max()], 
               origin='lower', cmap='turbo', alpha=0.8, interpolation='bilinear')
    
    buf = BytesIO()
    plt.savefig(buf, format='png', transparent=True, dpi=200)
    plt.close(fig)
    
    # Standardize bounds for JSON serialization
    bounds = [float(lat.min()), float(lon.min()), float(lat.max()), float(lon.max())]
    return buf, bounds, speed

# --- 3. MOCK AIS DATA GENERATOR ---
def get_heavy_ais_data():
    ships = [
        # --- LINTASAN AKTIF (BACK AND FORTH) ---
        {"name": "KMP Portlink", "lat": -5.925, "lon": 105.910, "type": "Ferry", "speed": 12, "heading": 285},
        {"name": "KMP Sebuku", "lat": -5.935, "lon": 105.880, "type": "Ferry", "speed": 10, "heading": 105},
        {"name": "KMP Legundi", "lat": -5.915, "lon": 105.930, "type": "Ferry", "speed": 13, "heading": 110},
        {"name": "KMP Jatra III", "lat": -5.930, "lon": 105.820, "type": "Ferry", "speed": 14, "heading": 100},
        {"name": "KMP Labitra Adinda", "lat": -5.940, "lon": 105.800, "type": "Ferry", "speed": 11, "heading": 95},
        {"name": "KMP Rishel", "lat": -5.922, "lon": 105.890, "type": "Ferry", "speed": 12, "heading": 275},
        {"name": "KMP Amadea", "lat": -5.938, "lon": 105.865, "type": "Ferry", "speed": 10, "heading": 108},
        
        # --- ANTRIAN / SEKITAR PELABUHAN MERAK ---
        {"name": "KMP Rajabasa (Docking)", "lat": -5.932, "lon": 105.995, "type": "Ferry", "speed": 0, "heading": 45},
        {"name": "Tugboat Merak I", "lat": -5.935, "lon": 105.990, "type": "Patrol", "speed": 2, "heading": 0},
        {"name": "Tugboat Merak II", "lat": -5.930, "lon": 106.000, "type": "Patrol", "speed": 1, "heading": 90},
        
        # --- ANTRIAN / SEKITAR PELABUHAN BAKAUHENI ---
        {"name": "KMP Windu Karsa Pratama", "lat": -5.870, "lon": 105.760, "type": "Ferry", "speed": 0, "heading": 220},
        {"name": "KMP Neomi", "lat": -5.865, "lon": 105.755, "type": "Ferry", "speed": 1, "heading": 180},
        
        # --- KAPAL LOGISTIK & TANKER DI ALKI I ---
        {"name": "MT Martha Petrol", "lat": -5.850, "lon": 105.800, "type": "Tanker", "speed": 8, "heading": 210},
        {"name": "MV Ocean Voyager", "lat": -6.050, "lon": 105.750, "type": "Cargo", "speed": 15, "heading": 30},
        {"name": "CMA CGM Jakarta", "lat": -6.120, "lon": 105.850, "type": "Container", "speed": 18, "heading": 15},
        {"name": "Maersk Sunda", "lat": -5.780, "lon": 105.980, "type": "Container", "speed": 16, "heading": 195},
        
        # --- PENJAGA LAUT / PATROLI ---
        {"name": "KN Trisula (PPLP)", "lat": -5.980, "lon": 105.950, "type": "Patrol", "speed": 22, "heading": 340},
    ]
    return ships

# --- 4. MAIN APP LOGIC ---
target_file = "CODAR_BADA_2025_04_12_1400-1744466400.nc"

try:
    # Process Data
    img_buf, bounds, speed_data = get_vibrant_overlay(target_file)
    ships = get_heavy_ais_data()
    
    # Initialize Folium Map (Free Basemap)
    m = folium.Map(
        location=[-5.95, 105.9], 
        zoom_start=11, 
        tiles="CartoDB dark_matter",
        zoom_control=True
    )
    
    # Layer 1: Flattened Current Shading
    img = PIL.Image.open(img_buf)
    folium.raster_layers.ImageOverlay(
        image=np.array(img),
        bounds=[[bounds[0], bounds[1]], [bounds[2], bounds[3]]],
        opacity=0.85,
        zindex=1
    ).add_to(m)

    # Layer 2: Directional AIS Arrows
    for ship in ships:
        # Define color based on ship type
        ship_color = '#ff0000' if ship['type'] == 'Ferry' else '#00ccff'
        if ship['type'] == 'Patrol': ship_color = '#00ff00'
        
        # CSS DivIcon to rotate the arrow based on heading
        icon_html = f"""
            <div style="
                transform: rotate({ship['heading']}deg);
                color: {ship_color};
                font-size: 24px;
                font-weight: bold;
                text-shadow: 1px 1px 2px #000;
                width: 30px;
                height: 30px;
                display: flex;
                align-items: center;
                justify-content: center;
            ">➤</div>
        """
        
        folium.Marker(
            location=[ship['lat'], ship['lon']],
            popup=f"<b>{ship['name']}</b><br>Heading: {ship['heading']}°<br>Speed: {ship['speed']} kts",
            tooltip=ship['name'],
            icon=folium.DivIcon(
                icon_size=(30, 30),
                icon_anchor=(15, 15),
                html=icon_html
            )
        ).add_to(m)
        
                # Menambahkan garis putus-putus rute penyeberangan
        folium.PolyLine(
            locations=[[-5.93, 106.00], [-5.87, 105.76]],
            color="white",
            weight=2,
            opacity=0.5,
            dash_array='10, 10'
        ).add_to(m)

    # Layer 3: Dynamic Colormap (Turbo scale)
    max_val = float(np.nanmax(speed_data)) if not np.all(np.isnan(speed_data)) else 2.5
    colormap = cm.LinearColormap(
        colors=['#30123b', '#4145ab', '#4672f1', '#2eb67d', '#f8e621', '#c72200'], 
        vmin=0, vmax=max_val,
        caption='Surface Current Speed (m/s)'
    )
    colormap.add_to(m)

    # Render to Streamlit
    folium_static(m, width=1850, height=850)

except Exception as e:
    st.error(f"Operational Error: {e}")
