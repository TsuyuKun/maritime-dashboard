import streamlit as st
import xarray as xr
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as colors
from pyproj import Proj

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Sunda Strait Smart Maritime", layout="wide")

st.title("🚢 Smart Maritime Dashboard: Selat Sunda")
st.markdown("""
Dashboard operasional untuk monitoring **Arus Permukaan** (Radar Maritim) dan 
**Posisi Kapal (AIS)** di wilayah strategis Selat Sunda.
""")

# --- FUNGSI LOAD DATA ---
@st.cache_data
def load_radar_data(file_path):
    # Membaca data NetCDF
    ds = xr.open_dataset(file_path)
    # Ambil time step pertama [0] dan konversi ke DataFrame
    df = ds.isel(time=0).to_dataframe().reset_index()
    # Bersihkan data dari NaN
    df = df.dropna(subset=['u', 'v'])
    # Hitung kecepatan (magnitude) dalam m/s
    df['speed'] = np.sqrt(df['u']**2 + df['v']**2)
    return df

# --- SIDEBAR & INPUT ---
st.sidebar.header("Data Source")
selected_file = st.sidebar.selectbox(
    "Pilih Data Radar (.nc):",
    ["CODAR_BADA_2025_04_12_1400-1744466400.nc"] # Sesuaikan nama file
)

# Load data kapal (Dummy AIS untuk Demo)
ais_data = pd.DataFrame({
    'Ship_Name': ['KMP Portlink', 'KMP Sebuku', 'MV Dharma Rucitra'],
    'Lat': [-5.925, -5.940, -5.980],
    'Lon': [105.910, 105.860, 105.790],
    'Speed_Knot': [12.5, 10.2, 14.0]
})

# --- PROSES DATA & VISUALISASI MATPLOTLIB ---
try:
    df_radar = load_radar_data(selected_file)

    # 1. Menyiapkan Grid untuk Plotting
    lon_unique = np.unique(df_radar['lon'])
    lat_unique = np.unique(df_radar['lat'])
    Lon, Lat = np.meshgrid(lon_unique, lat_unique)

    # Mengisi nilai u, v, speed ke grid (NaN jika data tidak ada)
    U_grid = np.full(Lon.shape, np.nan)
    V_grid = np.full(Lat.shape, np.nan)
    Speed_grid = np.full(Lon.shape, np.nan)

    for i, lat_val in enumerate(lat_unique):
        for j, lon_val in enumerate(lon_unique):
            data = df_radar[(df_radar['lat'] == lat_val) & (df_radar['lon'] == lon_val)]
            if not data.empty:
                U_grid[i, j] = data['u'].values[0]
                V_grid[i, j] = data['v'].values[0]
                Speed_grid[i, j] = data['speed'].values[0]

    # 2. Membuat Plot (Matplotlib)
    fig, ax = plt.subplots(figsize=(12, 10))

    # Layer A: Kontur Warna Kecepatan (Shading)
    norm = colors.Normalize(vmin=0, vmax=2.5) # Threshold kecepatan max
    cf = ax.contourf(Lon, Lat, Speed_grid, cmap='Spectral_r', levels=25, norm=norm, alpha=0.8)
    
    # Layer B: Vektor Panah Arus (Quiver)
    # Sampling data agar tidak terlalu padat (skip 2 titik)
    skip = (slice(None, None, 2), slice(None, None, 2))
    Q = ax.quiver(Lon[skip], Lat[skip], U_grid[skip], V_grid[skip], 
                  Scale_grid[skip], cmap='Greys', # Warna panah kontras
                  units='width', width=0.002, headwidth=3, headlength=4)

    # Layer C: Data Kapal (AIS)
    ax.scatter(ais_data['Lon'], ais_data['Lat'], color='red', marker='^', s=100, label='AIS Ship', edgecolor='black')
    for i, txt in enumerate(ais_data['Ship_Name']):
        ax.annotate(txt, (ais_data['Lon'].iloc[i], ais_data['Lat'].iloc[i]), xytext=(3, 3), textcoords='offset points', color='black', fontsize=9)

    # Pengaturan Tampilan Peta
    ax.set_title(f"Visualisasi Arus Permukaan & AIS - {selected_file}")
    ax.set_xlabel("Bujur (Longitude)")
    ax.set_ylabel("Lintang (Latitude)")
    ax.set_facecolor('#d3d3d3') # Warna daratan kelabu
    ax.grid(True, linestyle='--', alpha=0.5)

    # Menambahkan Colorbar
    cbar = fig.colorbar(cf, ax=ax)
    cbar.set_label('Kecepatan Arus (m/s)')

    # Menampilkan Legenda
    ax.legend(loc='lower right')

    # Integrasi ke Streamlit
    st.pyplot(fig)

    # --- METRIK UTAMA ---
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    col1.metric("Rata-rata Arus", f"{df_radar['speed'].mean():.2f} m/s")
    col2.metric("Arus Maksimum", f"{df_radar['speed'].max():.2f} m/s")
    col3.metric("Kapal Terdeteksi", len(ais_data))

except Exception as e:
    st.error(f"Error: {e}. Pastikan file .nc ada di folder yang sama.")

# --- FOOTER ---
st.info("Prototype operasional untuk monitoring Selat Sunda - Inovasi Kapita Selekta.")
