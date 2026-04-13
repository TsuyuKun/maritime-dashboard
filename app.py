import streamlit as st
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import folium
from streamlit_folium import folium_static
import PIL.Image
from io import BytesIO

# --- 1. CONFIG ---
st.set_page_config(page_title="Sunda Strait Crossing Maritime Dashboard", layout="wide")

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

# --- 3. DATA PELABUHAN & ARMADA DENGAN CUACA ---
ports = [
    {"name": "Pelabuhan Merak", "pos": [-5.93, 106.00]},
    {"name": "Pelabuhan Bakauheni", "pos": [-5.87, 105.76]},
    {"name": "Pelabuhan Bojonegara", "pos": [-5.95, 106.09]}
]

ships_data = [
    {
        "name": "KMP SEBUKU", "type": "Ferry", "color": "#00f2ff", "lat": -5.89, "lon": 105.82, 
        "speed": "10.8 kn", "course": 320, "eta": "11:15 UTC", "dest": "MERAK", "dest_pos": [-5.93, 106.00],
        "past": [[-5.87, 105.77], [-5.89, 105.82]],
        "timeline": [
            {"time": "10:30", "pos": [-5.90, 105.86], "cond": "🌧️ Hujan"},
            {"time": "10:45", "pos": [-5.91, 105.91], "cond": "☁️ Tebal"},
            {"time": "11:00", "pos": [-5.92, 105.95], "cond": "⛅ Berawan"},
            {"time": "11:15", "pos": [-5.93, 106.00], "cond": "☀️ Cerah"}
        ]
    },
    {
        "name": "MV PORTLINK", "type": "Ro-Ro", "color": "#2ecc71", "lat": -5.91, "lon": 105.90, 
        "speed": "12.5 kn", "course": 290, "eta": "10:45 UTC", "dest": "BAKAUHENI", "dest_pos": [-5.87, 105.76],
        "past": [[-5.93, 106.00], [-5.91, 105.90]],
        "timeline": [{"time": "10:30", "pos": [-5.89, 105.83], "cond": "🌧️ Hujan"}, {"time": "10:45", "pos": [-5.87, 105.76], "cond": "☁️ Tebal"}]
    },
    {
        "name": "MT OCEAN PRIDE", "type": "Tanker", "color": "#e74c3c", "lat": -6.10, "lon": 105.80, 
        "speed": "14.2 kn", "course": 210, "eta": "N/A", "dest": "AUSTRALIA", "dest_pos": [-6.50, 105.50],
        "past": [[-6.00, 105.85], [-6.10, 105.80]],
        "timeline": [{"time": "12:00", "pos": [-6.25, 105.70], "cond": "⛅ Berawan"}]
    },
    {
        "name": "KM LOGISTIK 1", "type": "Cargo", "color": "#f1c40f", "lat": -5.98, "lon": 106.05, 
        "speed": "9.0 kn", "course": 180, "eta": "12:00 UTC", "dest": "BOJONEGARA", "dest_pos": [-5.95, 106.09],
        "past": [[-6.05, 106.05], [-5.98, 106.05]],
        "timeline": [{"time": "11:30", "pos": [-5.97, 106.07], "cond": "☁️ Tebal"}]
    },
    {
        "name": "TK BARGE 88", "type": "Barge", "color": "#9b59b6", "lat": -6.02, "lon": 105.95, "speed": "4.5 kn", "course": 45, "eta": "-", "dest": "CIGADING", "dest_pos": [-6.01, 105.98],
        "past": [], "timeline": []
    },
    {
        "name": "KN JALAKULA", "type": "Patrol", "color": "#3498db", "lat": -5.95, "lon": 105.88, "speed": "18.0 kn", "course": 330, "eta": "-", "dest": "-", "dest_pos": [-5.80, 105.80],
        "past": [], "timeline": []
    }
]

# --- 4. MAP GENERATION ---
target_file = "CODAR_BADA_2025_04_12_1400-1744466400.nc"
img_buf, bounds = get_shaded_radar(target_file)
m = folium.Map(location=[-5.95, 105.9], zoom_start=11, tiles="CartoDB dark_matter")

if img_buf:
    folium.raster_layers.ImageOverlay(np.array(PIL.Image.open(img_buf)), 
                                     bounds=[[bounds[0], bounds[1]], [bounds[2], bounds[3]]], opacity=0.7).add_to(m)

for p in ports:
    folium.Marker(location=p['pos'], tooltip=p['name'], icon=folium.Icon(color='blue', icon='anchor', prefix='fa')).add_to(m)

js_objects = []

for s in ships_data:
    has_route = s['type'] not in ["Barge", "Patrol"]
    is_patrol = (s['type'] == "Patrol")
    main_ports = ["MERAK", "BAKAUHENI", "BOJONEGARA"]
    eta_val = s['eta'] if s['dest'].upper() in main_ports and not is_patrol else "-"
    dest_val = s['dest'] if not is_patrol else "-"

    route_id = "null"
    if has_route:
        folium.PolyLine(locations=s['past'], color=s['color'], weight=2, opacity=0.5).add_to(m)
        route = folium.PolyLine(locations=[[s['lat'], s['lon']], s['dest_pos']], color=s['color'], weight=3, opacity=0.7, dash_array='8, 8').add_to(m)
        route_id = route.get_name()

    wp_group = folium.FeatureGroup(name=f"wp_{s['name']}", show=False).add_to(m)
    for wp in s['timeline']:
        folium.Marker(location=wp['pos'], icon=folium.DivIcon(html=f'<div style="background:white; border-radius:4px; padding:2px; border:2px solid {s["color"]}; text-align:center; width:30px;">{wp["cond"].split()[0]}</div>')).add_to(wp_group)

    p_html = f"""<div style="font-family: Arial; width: 220px; font-size: 11px;">
        <b style="color: {s['color']}; font-size: 13px;">{s['name']}</b><br>{s['type']}<hr style="margin:4px 0;">
        <table style="width: 100%;">
            <tr><td>Speed</td><td>: {s['speed']}</td></tr>
            <tr><td>Course</td><td>: {s['course']}°</td></tr>
            <tr><td>Tujuan</td><td>: {dest_val}</td></tr>
            <tr><td>ETA</td><td>: {eta_val}</td></tr>
        </table>
        <hr style="margin:4px 0;"><b>Route Forecast:</b>
        <table style="width: 100%; margin-top:5px;">
            {"".join([f"<tr><td><b>{i['time']}</b></td><td>: {i['cond']}</td></tr>" for i in s['timeline']])}
        </table></div>"""

    marker = folium.Marker(
        location=[s['lat'], s['lon']],
        popup=folium.Popup(p_html, max_width=250),
        icon=folium.DivIcon(html=f'<div style="transform:rotate({s["course"]}deg); color:{s["color"]}; font-size:24px; cursor:pointer;">➤</div>')
    ).add_to(m)

    js_objects.append({"marker": marker.get_name(), "wp": wp_group.get_name(), "route": route_id})

# --- JS INJECTION ---
all_wp_ids = [obj['wp'] for obj in js_objects]
valid_route_objects = [obj for obj in js_objects if obj['route'] != "null"]

script_content = ""
for obj in js_objects:
    route_logic = f"{obj['route']}.setStyle({{weight: 5, dashArray: null}});" if obj['route'] != "null" else ""
    script_content += f"""
    {obj['marker']}.on('click', function() {{
        {[f"map.removeLayer({wid});" for wid in all_wp_ids]}
        {[f"{r['route']}.setStyle({{weight: 2, dashArray: '8, 8'}});" for r in valid_route_objects]}
        map.addLayer({obj['wp']});
        {route_logic}
    }});
    """

m.get_root().script.add_child(folium.Element(f"""
    var map = {m.get_name()};
    {script_content.replace('[', '').replace(']', '').replace("'", "")}
"""))

folium_static(m, width=1550, height=900)
