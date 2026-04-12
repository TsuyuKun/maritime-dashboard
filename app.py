import streamlit as st
import xarray as xr
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Sunda Strait Maritime Dashboard", layout="wide")

st.title("🚢 Smart Maritime Dashboard: Selat Sunda")
st.markdown("""
Dashboard ini mengintegrasikan data **Radar Maritim (HF Radar)** untuk arus permukaan 
dan **Marine Tracker (AIS)** untuk posisi kapal secara real-time.
""")

# --- FUNGSI LOAD DATA ---
@st.cache_data
def load_radar_data(file_path):
    # Membaca data NetCDF
    ds = xr.open_dataset(file_path)
    
    # Ambil variabel u, v, lat, lon
    # Mengambil time step pertama [0]
    df = ds.isel(time=0).to_dataframe().reset_index()
    
    # Bersihkan data dari NaN (area daratan biasanya NaN)
    df = df.dropna(subset=['u', 'v'])
    
    # Hitung kecepatan (magnitude) dalam m/s
    df['speed'] = np.sqrt(df['u']**2 + df['v']**2)
    
    return df

# --- SIDEBAR & INPUT ---
st.sidebar.header("Pengaturan Dashboard")
selected_file = st.sidebar.selectbox(
    "Pilih File Data Radar (NetCDF):",
    ["CODAR_BADA_2025_04_12_1400-1744466400.nc"] # Sesuaikan dengan nama filemu
)

# Load data kapal (Dummy AIS untuk Demo)
ais_data = pd.DataFrame({
    'Ship_Name': ['KMP Portlink', 'KMP Sebuku', 'MV Dharma Rucitra', 'Tanker Pertamina'],
    'Lat': [-5.925, -5.940, -5.980, -5.890],
    'Lon': [105.910, 105.860, 105.790, 105.940],
    'Type': ['Ferry', 'Ferry', 'Ro-Ro', 'Tanker'],
    'Speed_Knot': [12.5, 10.2, 14.0, 8.5]
})

# --- PROSES DATA ---
try:
    df_radar = load_radar_data(selected_file)
    
    # --- VISUALISASI MAP ---
    # Kita gunakan Plotly Mapbox agar lebih interaktif
    fig = go.Figure()

    # 1. Plot Arus (Vektor)
    # Sampling data agar tidak terlalu berat (ambil setiap 3 titik)
    sample = df_radar.iloc[::3]
    
    fig.add_trace(go.Scattermapbox(
        lat=sample['lat'],
        lon=sample['lon'],
        mode='markers',
        marker=go.scattermapbox.Marker(
            size=sample['speed']*15, # Ukuran titik berdasarkan kecepatan
            color=sample['speed'],
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title="Arus (m/s)", x=0)
        ),
        text=sample['speed'].apply(lambda x: f"Speed: {x:.2f} m/s"),
        name="Arus Permukaan"
    ))

    # 2. Plot Kapal (AIS)
    fig.add_trace(go.Scattermapbox(
        lat=ais_data['Lat'],
        lon=ais_data['Lon'],
        mode='markers+text',
        marker=go.scattermapbox.Marker(size=15, color='red', symbol='ferry'),
        text=ais_data['Ship_Name'],
        textposition="top right",
        name="Posisi Kapal (AIS)"
    ))

    # Update Layout Mapbox
    fig.update_layout(
        mapbox_style="open-street-map",
        mapbox=dict(
            center=go.layout.mapbox.Center(lat=-5.95, lon=105.88),
            zoom=10
        ),
        margin={"r":0,"t":0,"l":0,"b":0},
        height=700,
        showlegend=True
    )

    st.plotly_chart(fig, use_container_width=True)

    # --- METRIK UTAMA ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Rata-rata Arus", f"{df_radar['speed'].mean():.2f} m/s")
    col2.metric("Arus Maksimum", f"{df_radar['speed'].max():.2f} m/s")
    col3.metric("Kapal Terdeteksi", len(ais_data))

except Exception as e:
    st.error(f"Error: {e}. Pastikan file .nc berada di folder yang sama.")

# --- FOOTER ---
st.info("Inovasi Kapita Selekta - Prototype operasional untuk monitoring Selat Sunda.")
