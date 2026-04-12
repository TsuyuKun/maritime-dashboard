import streamlit as st
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import folium
from streamlit_folium import folium_static
import branca.colormap as cm
from io import BytesIO
import PIL.Image

# --- KONFIGURASI FULL SCREEN ---
st.set_page_config(page_title="Sunda Strait Dashboard", layout="wide")

# CSS untuk menghilangkan padding dan membuat elemen memenuhi layar
st.markdown("""
    <style>
        .reportview-container .main .block-container {
            padding-top: 0rem;
            padding-bottom: 0rem;
            padding-left: 0rem;
            padding-right: 0rem;
        }
        iframe {
            width: 100vw;
            height: 100vh;
        }
    </style>
    """, unsafe_allow_html=True)
@st.cache_data
def get_vibrant_overlay(file_path):
    ds = xr.open_dataset(file_path)
    ds = ds.sel(lat=slice(-6.2, -5.7), lon=slice(105.7, 106.1))
    
    lon, lat = ds.lon.values, ds.lat.values
    speed = np.sqrt(ds.u.isel(time=0).values**2 + ds.v.isel(time=0).values**2)
    
    fig, ax = plt.subplots(figsize=(15, 15)) # Resolusi lebih tinggi
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    ax.axis('off')
    
    # Menggunakan 'turbo' atau 'nipy_spectral' untuk warna yang lebih cerah
    # 'turbo' sangat bagus untuk visibilitas tinggi di operasional
    im = ax.imshow(speed, extent=[lon.min(), lon.max(), lat.min(), lat.max()], 
                   origin='lower', cmap='turbo', alpha=0.8, interpolation='bilinear')
    
    buf = BytesIO()
    plt.savefig(buf, format='png', transparent=True, dpi=200)
    plt.close(fig)
    
    bounds = [float(lat.min()), float(lon.min()), float(lat.max()), float(lon.max())]
    return buf, bounds, speed

target_file = "CODAR_BADA_2025_04_12_1400-1744466400.nc"

try:
    img_buf, bounds, speed_data = get_vibrant_overlay(target_file)
    
    # Buat Peta Dasar tanpa title/dashboard UI
    m = folium.Map(
        location=[-5.95, 105.9], 
        zoom_start=11, 
        tiles="CartoDB dark_matter",
        zoom_control=True, # Biar tetap bisa zoom manual
        scrollWheelZoom=True
    )
    
    # Overlay Gambar Vibrant
    img = PIL.Image.open(img_buf)
    folium.raster_layers.ImageOverlay(
        image=np.array(img),
        bounds=[[bounds[0], bounds[1]], [bounds[2], bounds[3]]],
        opacity=0.85,
        zindex=1
    ).add_to(m)

    # Colormap Cerah (Turbo Style)
    max_val = float(np.nanmax(speed_data)) if not np.all(np.isnan(speed_data)) else 2.5
    colormap = cm.LinearColormap(
        colors=['#30123b', '#4145ab', '#4672f1', '#2eb67d', '#f8e621', '#c72200'], # Turbo-like palette
        vmin=0, 
        vmax=max_val,
        caption='Kecepatan Arus (m/s)'
    )
    colormap.add_to(m)

    # Tampilkan Full Screen
    folium_static(m, width=1400, height=850) # Menyesuaikan aspek layar

except Exception as e:
    st.error(f"Error: {e}")
