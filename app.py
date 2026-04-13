import streamlit as st
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import folium
from streamlit_folium import folium_static
import PIL.Image
from io import BytesIO

# --- 1. CONFIG ---
st.set_page_config(page_title="Maritime FlightDoc Pro", layout="wide")

st.markdown("""
    <style>
        .block-container { padding: 0rem; background-color: #000000; }
        #MainMenu, footer, header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
@st.cache_data
def get_shaded_radar(file_path):
    try:
        ds = xr.open_dataset(file_path)
        ds_clipped = ds.sel(lat=slice(-6.5, -5.5), lon=slice(105.0, 107.0))
        lon, lat = ds_clipped.lon.values, ds_clipped.lat.values
        speed = np.sqrt(ds_clipped.u.isel(time=0).values**2 + ds_clipped.v.isel(time=0).values**2)
        
        fig, ax = plt.subplots(figsize=(10, 10))
        fig.subplots_adjust(0,0,1,1); ax.axis('off')
        ax.imshow(speed, extent=[lon.min(), lon.max(), lat.min(), lat.max()], 
                   origin='lower', cmap='turbo', alpha=0.6, interpolation='bilinear')
        
        buf = BytesIO(); plt.savefig(buf, format='png', transparent=True, dpi=150); plt.close(fig)
        return buf, [float(lat.min()), float(lon.min()), float(lat.max()), float(lon.max())]
    except: return None, None

# --- 3. MOCK DATA ---
ships_data = [
    {
        "name": "KMP_SEBUKU", "type": "Ferry", "lat": -5.89, "lon": 105.82, "speed": "10.8 kn", "course": 115, "eta": "11:15 UTC",
        "dest": "MERAK", "dest_pos": [-5.93, 106.00],
        # Tambahan Past Track
        "past_track": [[-5.87, 105.77], [-5.88, 105.79], [-5.89, 105.82]],
        "timeline": [
            {"time": "10:30", "pos": [-5.90, 105.86], "cond": "🌧️ Hujan"},
            {"time": "10:45", "pos": [-5.91, 105.91], "cond": "☁️ Tebal"},
            {"time": "11:00", "pos": [-5.92, 105.96], "cond": "⛅ Berawan"},
            {"time": "11:15", "pos": [-5.93, 106.00], "cond": "☀️ Cerah"}
        ]
    },
    {
        "name": "MT_OCEAN_PRIDE", "type": "Tanker", "lat": -6.10, "lon": 105.80, "speed": "14.2 kn", "course": 210, "eta": "14:00 UTC",
        "dest": "AUSTRALIA", "dest_pos": [-6.50, 105.50],
        "past_track": [[-5.80, 105.95], [-6.10, 105.80]],
        "timeline": [
            {"time": "Now", "pos": [-6.10, 105.80], "cond": "☀️ Cerah"},
            {"time": "+30m", "pos": [-6.25, 105.70], "cond": "⛅ Berawan"}
        ]
    }
]

# --- 4. MAP GENERATION ---
target_file = "CODAR_BADA_2025_04_12_1400-1744466400.nc"
img_buf, bounds = get_shaded_radar(target_file)
m = folium.Map(location=[-6.0, 105.9], zoom_start=11, tiles="CartoDB dark_matter")

if img_buf:
    folium.raster_layers.ImageOverlay(np.array(PIL.Image.open(img_buf)), 
                                     bounds=[[bounds[0], bounds[1]], [bounds[2], bounds[3]]], opacity=0.7).add_to(m)

js_objects = []

for s in ships_data:
    # 1. Past Track (Garis Oranye)
    folium.PolyLine(locations=s['past_track'], color="#e67e22", weight=3, opacity=0.8).add_to(m)

    # 2. Waypoint Group (Sembunyi di awal)
    wp_group = folium.FeatureGroup(name=f"wp_{s['name']}", show=False).add_to(m)
    for wp in s['timeline']:
        folium.Marker(
            location=wp['pos'],
            icon=folium.DivIcon(html=f'<div style="background:white; border-radius:4px; padding:2px; border:1px solid cyan; text-align:center; width:32px; font-size:14px;">{wp["cond"].split()[0]}</div>')
        ).add_to(wp_group)

    # 3. Expected Route (Garis Putus-putus Biru)
    route = folium.PolyLine(locations=[[s['lat'], s['lon']], s['dest_pos']], 
                            color="#3498db", weight=3, opacity=0.7, dash_array='10, 10').add_to(m)

    # Popup Content
    t_rows = "".join([f"<tr><td><b>{i['time']}</b></td><td>: {i['cond']}</td></tr>" for i in s['timeline']])
    p_html = f"""<div style="font-family: Arial; width: 220px; font-size: 11px;">
        <b style="color: #2980b9; font-size: 14px;">{s['name'].replace('_',' ')}</b><br>{s['type']}<hr style="margin:4px 0;">
        <table style="width: 100%;">
            <tr><td>Speed</td><td>: {s['speed']}</td></tr>
            <tr><td>Course</td><td>: {s['course']}°</td></tr>
            <tr><td>Tujuan</td><td>: {s['dest']}</td></tr>
            <tr><td>ETA</td><td>: {s['eta']}</td></tr>
        </table>
        <hr style="margin:4px 0;"><b>Route Forecast:</b>
        <table style="width: 100%; margin-top:5px;">{t_rows}</table></div>"""

    # Marker Kapal
    marker = folium.Marker(
        location=[s['lat'], s['lon']],
        popup=folium.Popup(p_html, max_width=250),
        icon=folium.DivIcon(html=f'<div style="transform:rotate({s["course"]}deg); color:#FF4B4B; font-size:26px; cursor:pointer;">➤</div>')
    ).add_to(m)

    js_objects.append({"marker": marker.get_name(), "wp": wp_group.get_name(), "route": route.get_name()})

# --- JAVASCRIPT INJECTION (STABLE) ---
all_wp_ids = [obj['wp'] for obj in js_objects]
all_route_ids = [obj['route'] for obj in js_objects]

script_content = ""
for obj in js_objects:
    script_content += f"""
    {obj['marker']}.on('click', function() {{
        {[f"map.removeLayer({wid});" for wid in all_wp_ids]}
        {[f"{rid}.setStyle({{color: '#3498db', weight: 3, dashArray: '10, 10'}});" for rid in all_route_ids]}
        map.addLayer({obj['wp']});
        {obj['route']}.setStyle({{color: '#00f2ff', weight: 5, dashArray: null}});
    }});
    """

m.get_root().script.add_child(folium.Element(f"""
    var map = {m.get_name()};
    {script_content.replace('[', '').replace(']', '').replace("'", "")}
"""))

folium_static(m, width=1550, height=900)
