import streamlit as st
import xarray as xr
import pandas as pd
import numpy as np
import pydeck as pdk

# --- PAGE CONFIG ---
st.set_page_config(page_title="Sunda Strait Flow Dashboard", layout="wide")

st.title("🌊 Sunda Strait Operational Flow Dashboard")

# --- DATA LOADING ---
@st.cache_data
def load_radar_data(file_path):
    ds = xr.open_dataset(file_path)
    # Clipped Boundary
    ds = ds.sel(lat=slice(-6.2, -5.7), lon=slice(105.7, 106.1))
    df = ds.isel(time=0).to_dataframe().reset_index()
    df = df.dropna(subset=['u', 'v'])
    
    # Hitung Speed & Arah
    df['speed'] = np.sqrt(df['u']**2 + df['v']**2)
    
    # Untuk "Flow" line, kita butuh koordinat tujuan (target)
    # Kita buat garis pendek yang menunjukkan arah arus
    scale = 0.02 # Panjang garis aliran
    df['lon_target'] = df['lon'] + (df['u'] * scale)
    df['lat_target'] = df['lat'] + (df['v'] * scale)
    
    # Warna berdasarkan speed (RGB untuk Pydeck)
    # 0 m/s = Biru, 2 m/s = Merah
    def get_rgb(speed):
        r = min(255, int(speed * 127))
        g = min(255, int(255 - (speed * 127)))
        b = 255 if speed < 0.5 else 0
        return [r, g, b, 200]

    df['color'] = df['speed'].apply(get_rgb)
    return df

# --- SELECTION ---
nc_file = "CODAR_BADA_2025_04_12_1400-1744466400.nc" # Sesuaikan filemu

try:
    df = load_radar_data(nc_file)

    # --- 1. LAYER SHADING (HEATMAP) ---
    # Memberikan efek warna gradasi di bawah arus
    heatmap_layer = pdk.Layer(
        "HeatmapLayer",
        df,
        get_position=["lon", "lat"],
        get_weight="speed",
        radius_pixels=40,
        intensity=0.7,
        threshold=0.1,
        color_range=[
            [0, 0, 255],     # Biru
            [0, 255, 255],   # Cyan
            [0, 255, 0],     # Hijau
            [255, 255, 0],   # Kuning
            [255, 0, 0]      # Merah
        ]
    )

    # --- 2. LAYER FLOW (LINE LAYER) ---
    # Membuat garis aliran yang menunjukkan arah u dan v
    flow_layer = pdk.Layer(
        "LineLayer",
        df,
        get_source_position=["lon", "lat"],
        get_target_position=["lon_target", "lat_target"],
        get_color="color",
        get_width=2,
        pickable=True,
    )

    # --- 3. LAYER SHIPS (AIS) ---
    ais_data = pd.DataFrame([
        {"name": "KMP Portlink", "lon": 105.910, "lat": -5.925},
        {"name": "KMP Sebuku", "lon": 105.860, "lat": -5.940}
    ])
    
    ship_layer = pdk.Layer(
        "ScatterplotLayer",
        ais_data,
        get_position=["lon", "lat"],
        get_radius=300,
        get_fill_color=[255, 0, 0], # Merah
        pickable=True,
    )

    # --- VIEW STATE ---
    view_state = pdk.ViewState(
        latitude=-5.95,
        longitude=105.88,
        zoom=10,
        pitch=0
    )

    # --- RENDER MAP ---
    r = pdk.Deck(
        layers=[heatmap_layer, flow_layer, ship_layer],
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/dark-v10", # Harus pake Dark biar Shading kelihatan
        tooltip={"text": "Speed: {speed} m/s\nShip: {name}"}
    )

    st.pydeck_chart(r)

    st.success("Tampilan Shaded Flow berhasil dimuat!")

except Exception as e:
    st.error(f"Gagal memproses data: {e}")
