import streamlit as st
import xarray as xr
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as colors

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Sunda Strait Smart Maritime", layout="wide")

st.title("🚢 Smart Maritime Dashboard: Selat Sunda")
st.markdown("""
Dashboard operasional untuk monitoring **Arus Permukaan** (Radar Maritim) dan 
**Posisi Kapal (AIS)** di wilayah strategis Selat Sunda.
""")

# --- DATA LOADING FUNCTION ---
@st.cache_data
def load_radar_data(file_path):
    ds = xr.open_dataset(file_path)
    # Using the first time step
    df = ds.isel(time=0).to_dataframe().reset_index()
    # Clean NaN values (land areas)
    df = df.dropna(subset=['u', 'v'])
    # Calculate speed magnitude (m/s)
    df['speed'] = np.sqrt(df['u']**2 + df['v']**2)
    return df

# --- SIDEBAR & SELECTION ---
st.sidebar.header("Control Panel")
# List of files you uploaded
nc_files = [
    "CODAR_BADA_2025_04_12_1400-1744466400.nc",
    "CODAR_BADA_2025_04_12_1410-1744467000.nc",
    "CODAR_BADA_2025_04_12_1420-1744467600.nc",
    "CODAR_BADA_2025_04_12_1430-1744468200.nc",
    "CODAR_BADA_2025_04_12_1440-1744468800.nc"
]
selected_file = st.sidebar.selectbox("Pilih Data Radar (.nc):", nc_files)

# Mock AIS Data
ais_data = pd.DataFrame({
    'Ship_Name': ['KMP Portlink', 'KMP Sebuku', 'MV Dharma Rucitra'],
    'Lat': [-5.925, -5.940, -5.980],
    'Lon': [105.910, 105.860, 105.790]
})

# --- PROCESSING & PLOTTING ---
try:
    df_radar = load_radar_data(selected_file)

    # Creating Grid for Plotting
    lon_unique = np.sort(df_radar['lon'].unique())
    lat_unique = np.sort(df_radar['lat'].unique())
    Lon, Lat = np.meshgrid(lon_unique, lat_unique)

    U_grid = np.full(Lon.shape, np.nan)
    V_grid = np.full(Lat.shape, np.nan)
    Speed_grid = np.full(Lon.shape, np.nan)

    # Pivot the dataframe to grid
    pivot_u = df_radar.pivot(index='lat', columns='lon', values='u').reindex(index=lat_unique, columns=lon_unique)
    pivot_v = df_radar.pivot(index='lat', columns='lon', values='v').reindex(index=lat_unique, columns=lon_unique)
    pivot_speed = df_radar.pivot(index='lat', columns='lon', values='speed').reindex(index=lat_unique, columns=lon_unique)

    U_grid = pivot_u.values
    V_grid = pivot_v.values
    Speed_grid = pivot_speed.values

    # Start Matplotlib Figure
    fig, ax = plt.subplots(figsize=(12, 9), dpi=100)
    
    # Style: Background Color (Land/Sea)
    ax.set_facecolor('#e0e0e0') # Light grey for missing data/land

    # Layer 1: Filled Contours (Speed)
    levels = np.linspace(0, 2.0, 21) # Speed range 0 to 2.0 m/s
    cf = ax.contourf(Lon, Lat, Speed_grid, levels=levels, cmap='jet', extend='both', alpha=0.9)
    
    # Layer 2: Quiver Plot (Current Arrows)
    # We skip every 2 points to avoid overcrowding
    skip = (slice(None, None, 2), slice(None, None, 2))
    Q = ax.quiver(Lon[skip], Lat[skip], U_grid[skip], V_grid[skip], 
                  color='black', scale=20, width=0.0025, headwidth=3)

    # Layer 3: AIS Ships
    ax.scatter(ais_data['Lon'], ais_data['Lat'], color='white', marker='^', s=150, 
               label='Ship (AIS)', edgecolor='black', linewidth=1.5, zorder=5)
    
    for i, txt in enumerate(ais_data['Ship_Name']):
        ax.annotate(txt, (ais_data['Lon'].iloc[i], ais_data['Lat'].iloc[i]), 
                    xytext=(5, 5), textcoords='offset points', fontweight='bold',
                    fontsize=10, color='white', path_effects=None, zorder=6,
                    bbox=dict(boxstyle='round,pad=0.2', fc='black', alpha=0.5))

    # Formatting
    ax.set_title(f"Sunda Strait Surface Current & Ship Tracking\nSource: {selected_file}", fontsize=14, fontweight='bold')
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.grid(True, linestyle=':', alpha=0.6)

    # Colorbar
    cbar = fig.colorbar(cf, ax=ax, fraction=0.03, pad=0.04)
    cbar.set_label('Current Speed (m/s)', fontsize=12)

    st.pyplot(fig)

    # --- METRICS ---
    st.markdown("---")
    m1, m2, m3 = st.columns(3)
    m1.metric("Average Speed", f"{df_radar['speed'].mean():.2f} m/s")
    m2.metric("Max Speed", f"{df_radar['speed'].max():.2f} m/s")
    m3.metric("Ships in Area", len(ais_data))

except Exception as e:
    st.error(f"Error: {e}. Please ensure the .nc files are in the same directory.")
