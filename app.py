import streamlit as st
import xarray as xr
import pandas as pd
import numpy as np
import plotly.figure_factory as ff
import plotly.graph_objects as go

# --- PAGE CONFIG ---
st.set_page_config(page_title="Sunda Strait Interactive Dashboard", layout="wide")

st.title("🌊 Interactive Maritime Dashboard: Sunda Strait")
st.markdown("Zoom and hover to explore current patterns and ship positions.")

# --- DATA LOADING ---
@st.cache_data
def load_radar_data(file_path):
    ds = xr.open_dataset(file_path)
    df = ds.isel(time=0).to_dataframe().reset_index()
    df = df.dropna(subset=['u', 'v'])
    df['speed'] = np.sqrt(df['u']**2 + df['v']**2)
    return df

# --- SIDEBAR ---
nc_files = [
    "CODAR_BADA_2025_04_12_1400-1744466400.nc",
    "CODAR_BADA_2025_04_12_1410-1744467000.nc",
    "CODAR_BADA_2025_04_12_1420-1744467600.nc",
    "CODAR_BADA_2025_04_12_1430-1744468200.nc",
    "CODAR_BADA_2025_04_12_1440-1744468800.nc"
]
selected_file = st.sidebar.selectbox("Select Radar Data:", nc_files)

# Mock AIS Data
ais_data = pd.DataFrame({
    'Ship_Name': ['KMP Portlink', 'KMP Sebuku', 'MV Dharma Rucitra'],
    'Lat': [-5.925, -5.940, -5.980],
    'Lon': [105.910, 105.860, 105.790],
    'Type': ['Ferry', 'Ferry', 'Ro-Ro']
})

try:
    df = load_radar_data(selected_file)

    # --- 1. CREATE INTERACTIVE QUIVER PLOT ---
    # Downsample slightly for smoother interactivity (skip every 2)
    skip = df.iloc[::2]
    
    # ff.create_quiver generates the arrows as a set of lines
    fig = ff.create_quiver(skip['lon'], skip['lat'], skip['u'], skip['v'],
                           scale=.05,
                           arrow_scale=.3,
                           name='Current Direction',
                           line_color='black')

    # --- 2. ADD COLOR CONTOURS (SHADING) ---
    # We add a heatmap layer behind the arrows
    fig.add_trace(go.Contour(
        x=df['lon'],
        y=df['lat'],
        z=df['speed'],
        colorscale='Jet',
        line_smoothing=0.8,
        contours_coloring='heatmap',
        name='Current Speed (m/s)',
        colorbar=dict(title="m/s"),
        opacity=0.8,
        hovertemplate="Lon: %{x}<br>Lat: %{y}<br>Speed: %{z:.2f} m/s<extra></extra>"
    ))

    # --- 3. ADD SHIPS (AIS) ---
    fig.add_trace(go.Scatter(
        x=ais_data['Lon'],
        y=ais_data['Lat'],
        mode='markers+text',
        name='Ships (AIS)',
        marker=dict(symbol='triangle-up', size=15, color='white', line=dict(width=2, color='black')),
        text=ais_data['Ship_Name'],
        textposition="top center",
        customdata=ais_data['Type'],
        hovertemplate="<b>%{text}</b><br>Type: %{customdata}<extra></extra>"
    ))

    # --- LAYOUT TUNING ---
    fig.update_layout(
        width=1000,
        height=700,
        xaxis_title="Longitude",
        yaxis_title="Latitude",
        xaxis=dict(scaleanchor="y", scaleratio=1), # Maintain aspect ratio
        template="plotly_white",
        margin=dict(l=0, r=0, t=40, b=0)
    )

    st.plotly_chart(fig, use_container_width=True)

    # --- METRICS ---
    m1, m2, m3 = st.columns(3)
    m1.metric("Avg Speed", f"{df['speed'].mean():.2f} m/s")
    m2.metric("Max Speed", f"{df['speed'].max():.2f} m/s")
    m3.metric("Ships Active", len(ais_data))

except Exception as e:
    st.error(f"Error loading data: {e}")
