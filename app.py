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
st.markdown("Visualisasi arus statis (Fixed Shading) terintegrasi dengan Basemap.")

@st.cache_data
def get_static_overlay(file_path):
    ds = xr.open_dataset(file_path)
    # 1. Clip area agar pas di Selat Sunda
    ds = ds.sel(lat=slice(-6.2, -5.7), lon=slice(105.7, 106.1))
    
    # 2. Ambil data
    lon = ds.lon.values
    lat = ds.lat.values
    u = ds.u.isel(time=0).values
    v = ds.v.isel(time=0).values
    speed = np.sqrt(u**2 + v**2)
    
    # 3. Render Shading ke Gambar (Flattening process)
    # Kita buat plot tanpa axis/margin agar bisa di-overlay
    fig, ax = plt.subplots(figsize=(10, 10))
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    ax.axis('off')
    
    # Gunakan 'jet' atau 'Spectral_r' agar mirip contoh
    im = ax.imshow(speed, extent=[lon.min(), lon.max(), lat.min(), lat.max()], 
                   origin='lower', cmap='jet', alpha=0.7, interpolation='bilinear')
    
    # Simpan ke buffer sebagai PNG transparan
    buf = BytesIO()
    plt.savefig(buf, format='png', transparent=True)
    plt.close(fig)
    return buf, [lat.min(), lon.min(), lat.max(), lon.max()], speed

target_file = "CODAR_BADA_2025_04_12_1400-1744466400.nc"

try:
    img_buf, bounds, speed_data = get_static_overlay(target_file)
    
    # --- RENDER MAP DENGAN LEAFLET (JAVASCRIPT BACKEND) ---
    # Membuat peta dasar (Basemap Gratis)
    m = folium.Map(location=[-5.95, 105.9], zoom_start=11, tiles="CartoDB dark_matter")
    
    # Menambahkan Gambar Shading Arus yang sudah di-flatten
    img = PIL.Image.open(img_buf)
    folium.raster_layers.ImageOverlay(
        image=np.array(img),
        bounds=[[bounds[0], bounds[1]], [bounds[2], bounds[3]]],
        opacity=0.7,
        interactive=True,
        cross_origin=True,
        zindex=1
    ).add_to(m)

    # Menambahkan Legend (Colorbar)
    colormap = cm.LinearColormap(colors=['blue', 'cyan', 'green', 'yellow', 'red'], 
                                 vmin=0, vmax=np.nanmax(speed_data),
                                 caption='Kecepatan Arus (m/s)')
    colormap.add_to(m)

    # Tambah Kapal AIS
    folium.Marker([-5.925, 105.91], popup="KMP Portlink", icon=folium.Icon(color='red', icon='ship', prefix='fa')).add_to(m)

    # Tampilkan Peta
    folium_static(m, width=1100, height=700)

except Exception as e:
    st.error(f"Error: {e}")
