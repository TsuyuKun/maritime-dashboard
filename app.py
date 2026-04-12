import streamlit as st
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import folium
from streamlit_folium import folium_static
import branca.colormap as cm
from io import BytesIO
import PIL.Image

st.set_page_config(page_title="Sunda Strait Flattened Dashboard", layout="wide")

st.title("🌊 Sunda Strait Flattened Shading Dashboard")

@st.cache_data
def get_static_overlay(file_path):
    ds = xr.open_dataset(file_path)
    # Clip area
    ds = ds.sel(lat=slice(-6.2, -5.7), lon=slice(105.7, 106.1))
    
    lon = ds.lon.values
    lat = ds.lat.values
    u = ds.u.isel(time=0).values
    v = ds.v.isel(time=0).values
    speed = np.sqrt(u**2 + v**2)
    
    # Flattening/Rendering ke Matplotlib
    fig, ax = plt.subplots(figsize=(10, 10))
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    ax.axis('off')
    
    im = ax.imshow(speed, extent=[lon.min(), lon.max(), lat.min(), lat.max()], 
                   origin='lower', cmap='jet', alpha=0.7, interpolation='bilinear')
    
    buf = BytesIO()
    plt.savefig(buf, format='png', transparent=True)
    plt.close(fig)
    
    # Konversi koordinat bounds ke float standar Python agar aman untuk JSON
    bounds = [float(lat.min()), float(lon.min()), float(lat.max()), float(lon.max())]
    
    return buf, bounds, speed

target_file = "CODAR_BADA_2025_04_12_1400-1744466400.nc"

try:
    img_buf, bounds, speed_data = get_static_overlay(target_file)
    
    # Peta Leaflet (Javascript Backend)
    m = folium.Map(location=[-5.95, 105.9], zoom_start=11, tiles="CartoDB dark_matter")
    
    # Overlay Gambar
    img = PIL.Image.open(img_buf)
    folium.raster_layers.ImageOverlay(
        image=np.array(img),
        bounds=[[bounds[0], bounds[1]], [bounds[2], bounds[3]]],
        opacity=0.7,
        interactive=True,
        zindex=1
    ).add_to(m)

    # PERBAIKAN: Konversi vmax ke float standar Python
    max_val = float(np.nanmax(speed_data)) if not np.all(np.isnan(speed_data)) else 2.5

    colormap = cm.LinearColormap(
        colors=['blue', 'cyan', 'green', 'yellow', 'red'], 
        vmin=0, 
        vmax=max_val,
        caption='Kecepatan Arus (m/s)'
    )
    colormap.add_to(m)

    folium_static(m, width=1100, height=700)

except Exception as e:
    st.error(f"Terjadi kesalahan: {e}")
