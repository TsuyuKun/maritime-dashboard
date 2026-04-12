import streamlit as st
import xarray as xr
import pandas as pd
import numpy as np
import pydeck as pdk
from scipy.interpolate import griddata

st.set_page_config(page_title="Sunda Strait Smooth Flow", layout="wide")

@st.cache_data
def load_and_interpolate_data(file_path):
    ds = xr.open_dataset(file_path)
    # Clipped area
    ds = ds.sel(lat=slice(-6.1, -5.8), lon=slice(105.75, 106.05))
    df_raw = ds.isel(time=0).to_dataframe().reset_index().dropna(subset=['u', 'v'])
    
    # --- PROSES INTERPOLASI (BIAR SMOOTH) ---
    # 1. Buat grid baru yang jauh lebih rapat (High Resolution)
    grid_res = 200 # Jumlah titik baru (makin besar makin smooth tapi berat)
    new_lon = np.linspace(df_raw['lon'].min(), df_raw['lon'].max(), grid_res)
    new_lat = np.linspace(df_raw['lat'].min(), df_raw['lat'].max(), grid_res)
    grid_lon, grid_lat = np.meshgrid(new_lon, new_lat)

    # 2. Interpolasi nilai u dan v ke grid baru
    points = df_raw[['lon', 'lat']].values
    u_interp = griddata(points, df_raw['u'].values, (grid_lon, grid_lat), method='linear')
    v_interp = griddata(points, df_raw['v'].values, (grid_lon, grid_lat), method='linear')
    
    # 3. Masukkan kembali ke DataFrame
    df_smooth = pd.DataFrame({
        'lon': grid_lon.flatten(),
        'lat': grid_lat.flatten(),
        'u': u_interp.flatten(),
        'v': v_interp.flatten()
    }).dropna()
    
    df_smooth['speed'] = np.sqrt(df_smooth['u']**2 + df_smooth['v']**2)
    
    # Garis aliran
    line_scale = 0.015
    df_smooth['lon_end'] = df_smooth['lon'] + (df_smooth['u'] * line_scale)
    df_smooth['lat_end'] = df_smooth['lat'] + (df_smooth['v'] * line_scale)
    
    def get_color(speed):
        r = int(min(255, speed * 180))
        b = int(max(0, 255 - (speed * 180)))
        return [r, 50, b, 140]

    df_smooth['color'] = df_smooth['speed'].apply(get_color)
    return df_smooth

try:
    target_file = "CODAR_BADA_2025_04_12_1400-1744466400.nc"
    data = load_and_interpolate_data(target_file)

    # Shading Layer (Heatmap)
    # Sekarang kita pakai radius lebih kecil tapi data lebih rapat
    shaded_layer = pdk.Layer(
        "HeatmapLayer",
        data,
        get_position=["lon", "lat"],
        get_weight="speed",
        radius_pixels=25, # Radius lebih kecil biar detail kelihatan
        intensity=0.9,
        threshold=0.01,
        color_range=[
            [0, 0, 255], [0, 255, 255], [0, 255, 0], [255, 255, 0], [255, 0, 0]
        ]
    )

    # Flow Layer (Garis Arus)
    # Kita sampling biar garisnya nggak numpuk banget
    flow_layer = pdk.Layer(
        "LineLayer",
        data.iloc[::2], 
        get_source_position=["lon", "lat"],
        get_target_position=["lon_end", "lat_end"],
        get_color="color",
        get_width=1.5,
    )

    view = pdk.ViewState(latitude=-5.95, longitude=105.90, zoom=11)

    r = pdk.Deck(
        layers=[shaded_layer, flow_layer],
        initial_view_state=view,
        map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
    )

    st.pydeck_chart(r)

except Exception as e:
    st.error(f"Error: {e}")
