import streamlit as st
import xarray as xr
import pandas as pd
import numpy as np
import pydeck as pdk

# --- CONFIG ---
st.set_page_config(page_title="Sunda Strait Shaded Flow", layout="wide")

st.title("🌊 Operational Shaded Flow Dashboard: Selat Sunda")
st.markdown("Visualisasi Arus Permukaan (HF Radar) & Monitoring Kapal (AIS)")

# --- LOAD & PROCESS DATA ---
@st.cache_data
def load_radar_data(file_path):
    ds = xr.open_dataset(file_path)
    # Clipped Boundary Selat Sunda
    ds = ds.sel(lat=slice(-6.1, -5.8), lon=slice(105.75, 106.05))
    df = ds.isel(time=0).to_dataframe().reset_index()
    df = df.dropna(subset=['u', 'v'])
    
    # Hitung Speed & Vektor Target untuk Flow
    df['speed'] = np.sqrt(df['u']**2 + df['v']**2)
    
    # Skala panjang garis aliran (adjust jika garis terlalu pendek/panjang)
    line_scale = 0.015 
    df['lon_end'] = df['lon'] + (df['u'] * line_scale)
    df['lat_end'] = df['lat'] + (df['v'] * line_scale)
    
    # Color mapping (RGBA) - Biru ke Merah
    def get_color(speed):
        # Normalisasi speed 0-2 m/s ke 0-255
        r = int(min(255, speed * 150))
        b = int(max(0, 255 - (speed * 150)))
        return [r, 100, b, 160] # r, g, b, alpha

    df['color'] = df['speed'].apply(get_color)
    return df

# Pilih file yang ada di foldermu
target_file = "CODAR_BADA_2025_04_12_1400-1744466400.nc"

try:
    data = load_radar_data(target_file)

    # 1. LAYER SHADING (Heatmap agar tidak terlihat 'titik-titik')
    shaded_layer = pdk.Layer(
        "HeatmapLayer",
        data,
        get_position=["lon", "lat"],
        get_weight="speed",
        radius_pixels=35,
        intensity=0.8,
        threshold=0.05,
        color_range=[
            [0, 0, 255],     # Low: Biru
            [0, 255, 255],   # Cyan
            [0, 255, 0],     # Hijau
            [255, 255, 0],   # Kuning
            [255, 0, 0]      # High: Merah
        ]
    )

    # 2. LAYER FLOW (Garis Arus)
    flow_layer = pdk.Layer(
        "LineLayer",
        data,
        get_source_position=["lon", "lat"],
        get_target_position=["lon_end", "lat_end"],
        get_color="color",
        get_width=2.5,
        pickable=True,
    )

    # 3. LAYER KAPAL (AIS)
    ais_ships = pd.DataFrame([
        {"name": "KMP Portlink", "lon": 105.910, "lat": -5.925},
        {"name": "KMP Sebuku", "lon": 105.860, "lat": -5.940}
    ])

    ship_layer = pdk.Layer(
        "ScatterplotLayer",
        ais_ships,
        get_position=["lon", "lat"],
        get_radius=250,
        get_fill_color=[255, 255, 255], # Putih agar kontras di dark mode
        get_line_color=[255, 0, 0],
        line_width_min_pixels=2,
        pickable=True,
    )

    # --- VIEW STATE ---
    view = pdk.ViewState(
        latitude=-5.95,
        longitude=105.90,
        zoom=10.5,
        pitch=0
    )

    # --- RENDER DASHBOARD ---
    # Menggunakan gaya peta CartoDB (Gratis & No Token)
    r = pdk.Deck(
        layers=[shaded_layer, flow_layer, ship_layer],
        initial_view_state=view,
        map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
        tooltip={"text": "Kecepatan: {speed} m/s\nLokasi: {lon}, {lat}"}
    )

    st.pydeck_chart(r)

    # Metrik
    c1, c2 = st.columns(2)
    c1.metric("Max Speed", f"{data['speed'].max():.2f} m/s")
    c2.metric("Min Speed", f"{data['speed'].min():.2f} m/s")

except Exception as e:
    st.error(f"Error: {e}")
    st.info("Pastikan file .nc berada di folder yang sama dengan app.py")
