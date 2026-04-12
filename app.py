import streamlit as st
import xarray as xr
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# --- PAGE CONFIG ---
st.set_page_config(page_title="Sunda Strait Smart Maritime", layout="wide")

st.title("🌊 Advanced Maritime Flow Dashboard: Selat Sunda")
st.markdown("Integrasi Real-time HF Radar Flow & AIS Monitoring")

# --- DATA LOADING ---
@st.cache_data
def load_radar_data(file_path):
    ds = xr.open_dataset(file_path)
    # Clip Boundary: Kita batasi koordinat agar fokus di Selat Sunda saja (Clipped)
    # Sesuaikan slice jika area radar lebih luas dari Selat Sunda
    ds = ds.sel(lat=slice(-6.2, -5.7), lon=slice(105.7, 106.1))
    
    df = ds.isel(time=0).to_dataframe().reset_index()
    df = df.dropna(subset=['u', 'v'])
    df['speed'] = np.sqrt(df['u']**2 + df['v']**2)
    
    # Menghitung arah arus untuk simbol panah
    df['angle'] = np.arctan2(df['u'], df['v']) * 180 / np.pi
    return df

# --- SIDEBAR ---
nc_files = [
    "CODAR_BADA_2025_04_12_1400-1744466400.nc",
    "CODAR_BADA_2025_04_12_1410-1744467000.nc",
    "CODAR_BADA_2025_04_12_1420-1744467600.nc",
    "CODAR_BADA_2025_04_12_1430-1744468200.nc",
    "CODAR_BADA_2025_04_12_1440-1744468800.nc"
]
selected_file = st.sidebar.selectbox("Pilih Data Radar:", nc_files)

# Mock AIS Data
ais_data = pd.DataFrame({
    'Ship_Name': ['KMP Portlink', 'KMP Sebuku', 'MV Dharma Rucitra'],
    'Lat': [-5.925, -5.940, -5.980],
    'Lon': [105.910, 105.860, 105.790],
    'Course': [120, 300, 45] # Arah kapal
})

try:
    df = load_radar_data(selected_file)

    # --- 1. BASEMAP & SHADING (SPEED) ---
    # Menggunakan Density Mapbox untuk shading warna yang halus (Flow feel)
    fig = px.density_mapbox(df, lat='lat', lon='lon', z='speed',
                            radius=15, 
                            center=dict(lat=-5.95, lon=105.90),
                            zoom=10,
                            mapbox_style="carto-darkmatter", # Dark mode agar arus lebih "menyala"
                            color_continuous_scale="Jet",
                            range_color=[0, 2.0],
                            opacity=0.6)

    # --- 2. FLOW DIRECTIONS (ARROW OVERLAY) ---
    # Kita ambil sampel data untuk panah agar tidak terlalu padat
    arrows = df.iloc[::4] 
    
    fig.add_trace(go.Scattermapbox(
        lat=arrows['lat'],
        lon=arrows['lon'],
        mode='markers',
        marker=go.scattermapbox.Marker(
            size=10,
            symbol='arrow', # Plotly Mapbox mendukung simbol arrow
            angle=arrows['angle'],
            color='white',
            opacity=0.8
        ),
        name='Flow Direction',
        hoverinfo='skip'
    ))

    # --- 3. SHIPS (AIS) ---
    fig.add_trace(go.Scattermapbox(
        lat=ais_data['Lat'],
        lon=ais_data['Lon'],
        mode='markers+text',
        marker=go.scattermapbox.Marker(
            size=18, 
            color='red', 
            symbol='ferry'
        ),
        text=ais_data['Ship_Name'],
        textposition="top right",
        name='Ship (AIS)',
        hovertemplate="<b>%{text}</b><extra></extra>"
    ))

    # --- LAYOUT SETUP ---
    fig.update_layout(
        margin={"r":0,"t":40,"l":0,"b":0},
        height=750,
        title=dict(text=f"HF Radar Operasional: {selected_file}", font=dict(size=20, color="white")),
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(0,0,0,0.5)", font=dict(color="white"))
    )

    st.plotly_chart(fig, use_container_width=True)

    # --- DASHBOARD METRICS ---
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    c1.metric("Avg Surface Flow", f"{df['speed'].mean():.2f} m/s")
    c2.metric("Max Flow Velocity", f"{df['speed'].max():.2f} m/s")
    c3.metric("Ships Tracked", len(ais_data))

except Exception as e:
    st.error(f"Gagal memproses visualisasi: {e}")
