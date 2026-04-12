"""
Smart Maritime Dashboard — Sunda Strait, Indonesia
====================================================
Kapita Selekta | BMKG Operations | SOLAS Innovation
Author  : Final-Year Meteorology Student
Focus   : Safety of Life at Sea (SOLAS)

ETL Pipeline:
  [HF Radar Scraper] ─┐
  [Wave Model OPeNDAP]─┼─► [Spatial Regridder] ─► [Risk Engine] ─► [Streamlit UI]
  [AIS JSON API]      ─┘
"""

import time
import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Smart Maritime Dashboard — Sunda Strait",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM CSS  (dark nautical theme)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Exo+2:wght@300;600;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Exo 2', sans-serif;
    background-color: #050d1a;
    color: #c8dff0;
}

.stApp { background: #050d1a; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #071525 0%, #0a1e35 100%);
    border-right: 1px solid #1a3a5c;
}

/* Metric cards */
.metric-card {
    background: linear-gradient(135deg, #0d2137 0%, #0a2948 100%);
    border: 1px solid #1e4d7a;
    border-radius: 10px;
    padding: 16px 20px;
    text-align: center;
    box-shadow: 0 4px 20px rgba(0,150,255,0.08);
}
.metric-card h3 { font-size: 0.72rem; color: #5b93c7; letter-spacing: 0.12em; text-transform: uppercase; margin: 0 0 6px; }
.metric-card .value { font-family: 'Share Tech Mono', monospace; font-size: 1.9rem; color: #4fc3f7; margin: 0; }
.metric-card .unit  { font-size: 0.7rem; color: #5b93c7; }

/* Section headers */
.section-header {
    font-family: 'Exo 2', sans-serif;
    font-weight: 800;
    font-size: 0.8rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #4fc3f7;
    border-left: 3px solid #4fc3f7;
    padding-left: 10px;
    margin: 18px 0 10px;
}

/* Risk badge */
.badge-safe    { background:#0a3a1e; color:#4caf50; border:1px solid #4caf50; border-radius:6px; padding:2px 10px; font-size:0.78rem; font-weight:600; }
.badge-caution { background:#3a2a00; color:#ffc107; border:1px solid #ffc107; border-radius:6px; padding:2px 10px; font-size:0.78rem; font-weight:600; }
.badge-danger  { background:#3a0a0a; color:#f44336; border:1px solid #f44336; border-radius:6px; padding:2px 10px; font-size:0.78rem; font-weight:600; }

/* Divider */
hr { border-color: #1a3a5c; }

/* Plotly container shadow */
.stPlotlyChart { border-radius: 12px; overflow: hidden; box-shadow: 0 6px 30px rgba(0,100,200,0.15); }

/* Code block */
code { font-family: 'Share Tech Mono', monospace !important; background: #0d2137 !important; color: #4fc3f7 !important; border-radius: 4px; padding: 2px 6px; }

/* Info boxes */
.info-box { background: #071e33; border-left: 3px solid #1565c0; padding: 12px 16px; border-radius:0 8px 8px 0; font-size:0.82rem; color:#8ab4d4; margin-top:8px; }
</style>
""",
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────────────────────────────────────
# ① DATA INGESTION LAYER
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=600, show_spinner=False)
def ingest_hf_radar(
    lon_min: float = 105.5,
    lon_max: float = 106.2,
    lat_min: float = -6.5,
    lat_max: float = -5.8,
    resolution: float = 0.05,
) -> pd.DataFrame:
    """
    HF Radar Ingestion (Conceptual — Selenium / BeautifulSoup scraper).

    In production this function would:
      1. Launch a headless Chrome driver via Selenium.
      2. Navigate to the BMKG HF Radar portal (e.g. https://www.bmkg.go.id/maritim/).
      3. Wait for the JavaScript map canvas to render radar vectors.
      4. Parse the rendered HTML / embedded JSON payload with BeautifulSoup / json.loads().
      5. Extract U (eastward) and V (northward) current components on a regular grid.

    Selenium snippet (conceptual):
    ─────────────────────────────────
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from bs4 import BeautifulSoup

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=opts)
    driver.get("https://www.bmkg.go.id/maritim/arus-laut.bmkg")
    time.sleep(4)                          # wait for JS render
    soup = BeautifulSoup(driver.page_source, "lxml")
    payload = json.loads(soup.find("script", id="radar-data").string)
    driver.quit()
    ─────────────────────────────────
    Here we generate realistic synthetic data calibrated to Sunda Strait
    tidal-driven currents (peak ~2.5 m/s near narrows).
    """
    rng = np.random.default_rng(int(time.time()) // 600)  # refresh every 10 min

    lons = np.arange(lon_min, lon_max, resolution)
    lats = np.arange(lat_min, lat_max, resolution)
    lon2d, lat2d = np.meshgrid(lons, lats)

    # Tidal jet through the strait narrows (centred ~105.85°E, -5.95°N)
    x_norm = (lon2d - 105.85) / 0.3
    y_norm = (lat2d - (-5.95)) / 0.25
    jet = np.exp(-(y_norm**2)) * (1 + 0.4 * np.cos(np.pi * x_norm))
    tidal_phase = np.sin(2 * np.pi * datetime.now().hour / 12.42)  # M2 tide

    u = jet * 1.8 * tidal_phase + rng.normal(0, 0.15, lon2d.shape)
    v = -jet * 0.6 * tidal_phase + rng.normal(0, 0.1, lat2d.shape)

    records = []
    for i in range(lat2d.shape[0]):
        for j in range(lon2d.shape[1]):
            records.append(
                {
                    "lon": float(lon2d[i, j]),
                    "lat": float(lat2d[i, j]),
                    "u": float(u[i, j]),
                    "v": float(v[i, j]),
                    "speed": float(np.sqrt(u[i, j] ** 2 + v[i, j] ** 2)),
                }
            )

    df = pd.DataFrame(records)
    df["source"] = "HF_Radar_BMKG"
    df["timestamp"] = pd.Timestamp.utcnow()
    return df


@st.cache_data(ttl=1800, show_spinner=False)
def ingest_wave_model(
    lon_min: float = 105.5,
    lon_max: float = 106.2,
    lat_min: float = -6.5,
    lat_max: float = -5.8,
) -> pd.DataFrame:
    """
    Marine Model Wave Data via OPeNDAP / Xarray (Conceptual).

    In production this would use Xarray to stream from Copernicus Marine Service:
    ─────────────────────────────────────────────────────────────────────────────
    import xarray as xr
    import copernicusmarine                      # pip install copernicusmarine

    ds = copernicusmarine.open_dataset(
        dataset_id  = "cmems_mod_glo_wav_anfc_0.083deg_PT3H-i",
        variables   = ["VHM0", "VMDR", "VTPK"],  # Hs, mean dir, peak period
        minimum_longitude = lon_min,
        maximum_longitude = lon_max,
        minimum_latitude  = lat_min,
        maximum_latitude  = lat_max,
        start_datetime    = "2024-01-01T00:00:00",
        end_datetime      = "2024-01-02T00:00:00",
    )

    # Or InaWave (BRIN) via OPeNDAP:
    ds = xr.open_dataset(
        "https://opendap.brin.go.id/thredds/dodsC/inaware/wave/sunda_strait.nc",
        engine="netcdf4",
        chunks={"time": 1},
    )
    df = ds.sel(
        lon=slice(lon_min, lon_max),
        lat=slice(lat_min, lat_max),
    )["VHM0"].isel(time=0).to_dataframe().reset_index()
    ─────────────────────────────────────────────────────────────────────────────
    Synthetic data calibrated to Sunda Strait swell climatology.
    """
    rng = np.random.default_rng(42)

    # Coarser grid (0.083° like CMEMS global wave model)
    lons = np.arange(lon_min, lon_max, 0.083)
    lats = np.arange(lat_min, lat_max, 0.083)
    lon2d, lat2d = np.meshgrid(lons, lats)

    # Indian Ocean swell enters from SW, attenuates inside strait
    swell_decay = np.exp(-(lon2d - 105.5) / 0.5)
    wind_sea = 0.8 + 0.5 * rng.random(lon2d.shape)
    hs = np.clip(swell_decay * 2.8 + wind_sea, 0.2, 4.5)

    records = []
    for i in range(lat2d.shape[0]):
        for j in range(lon2d.shape[1]):
            records.append(
                {
                    "lon": float(lon2d[i, j]),
                    "lat": float(lat2d[i, j]),
                    "hs": float(hs[i, j]),
                    "tp": float(6 + 4 * swell_decay[i, j] + rng.uniform(-0.5, 0.5)),
                    "dir": float(rng.uniform(200, 280)),
                }
            )

    df = pd.DataFrame(records)
    df["source"] = "CMEMS_GloWave"
    df["timestamp"] = pd.Timestamp.utcnow()
    return df


# ── AIS vessel type code → human label (ITU/IMO type codes) ─────────────────
_AIS_TYPE_MAP = {
    20: "Wing-in-Ground", 21: "Wing-in-Ground", 22: "Wing-in-Ground",
    30: "Fishing", 31: "Tug", 32: "Tug", 33: "Dredger", 34: "Dive",
    35: "Military", 36: "Sailing", 37: "Pleasure",
    40: "High-Speed", 41: "High-Speed", 42: "High-Speed", 43: "High-Speed",
    44: "High-Speed", 45: "High-Speed", 46: "High-Speed", 47: "High-Speed",
    48: "High-Speed", 49: "High-Speed",
    50: "Pilot", 51: "SAR", 52: "Tug", 53: "Port Tender", 55: "Law Enforce",
    58: "Medical", 59: "Special",
    60: "Passenger", 61: "Passenger", 62: "Passenger", 63: "Passenger",
    64: "Passenger", 65: "Passenger", 66: "Passenger", 67: "Passenger",
    68: "Passenger", 69: "Passenger",
    70: "Cargo", 71: "Cargo", 72: "Cargo", 73: "Cargo", 74: "Cargo",
    75: "Cargo", 76: "Cargo", 77: "Cargo", 78: "Cargo", 79: "Cargo",
    80: "Tanker", 81: "Tanker", 82: "Tanker", 83: "Tanker", 84: "Tanker",
    85: "Tanker", 86: "Tanker", 87: "Tanker", 88: "Tanker", 89: "Tanker",
    90: "Other", 91: "Other", 92: "Other", 99: "Other",
}

# Sunda Strait bounding box
_BBOX = dict(lat_min=-6.5, lat_max=-5.8, lon_min=105.5, lon_max=106.2)

# ── Fallback mock data (shown when every live source fails) ──────────────────
_AIS_MOCK = [
    {"mmsi": "525001001", "name": "KM LABUAN BAJO",       "lat": -6.02, "lon": 105.87, "sog": 8.2,  "cog": 315, "type": "Cargo"},
    {"mmsi": "525001002", "name": "FERRY MERAK-BAKAUHENI","lat": -5.95, "lon": 105.98, "sog": 12.5, "cog": 180, "type": "Passenger"},
    {"mmsi": "525001003", "name": "MT PERTAMINA 7",       "lat": -6.28, "lon": 105.72, "sog": 6.1,  "cog": 45,  "type": "Tanker"},
    {"mmsi": "525001004", "name": "KM RORO NUSANTARA",    "lat": -6.10, "lon": 106.05, "sog": 9.8,  "cog": 270, "type": "Passenger"},
    {"mmsi": "525001005", "name": "TB TARAKAN",           "lat": -6.35, "lon": 105.82, "sog": 3.2,  "cog": 90,  "type": "Tug"},
    {"mmsi": "525001006", "name": "KM DOBONSOLO",         "lat": -5.88, "lon": 105.65, "sog": 14.0, "cog": 135, "type": "Cargo"},
    {"mmsi": "525001007", "name": "MV BUKIT RAYA",        "lat": -6.42, "lon": 106.12, "sog": 0.0,  "cog": 0,   "type": "Cargo"},
    {"mmsi": "525001008", "name": "PLTGU JTHRN FERRY",    "lat": -6.18, "lon": 105.95, "sog": 11.3, "cog": 200, "type": "Passenger"},
]


def _parse_aishub(raw: list) -> pd.DataFrame:
    """Parse AISHub /rec.php response (format=1 → list-of-dicts)."""
    vessels = raw[1] if isinstance(raw, list) and len(raw) > 1 else raw
    rows = []
    for v in vessels:
        try:
            lat = float(v.get("LATITUDE", v.get("LAT", 0)))
            lon = float(v.get("LONGITUDE", v.get("LON", 0)))
            # filter to bbox
            if not (_BBOX["lat_min"] <= lat <= _BBOX["lat_max"] and
                    _BBOX["lon_min"] <= lon <= _BBOX["lon_max"]):
                continue
            type_code = int(v.get("TYPE", 0) or 0)
            rows.append({
                "mmsi": str(v.get("MMSI", "")),
                "name": str(v.get("NAME", "UNKNOWN")).strip() or "UNKNOWN",
                "lat":  lat,
                "lon":  lon,
                "sog":  float(v.get("SOG", 0) or 0),
                "cog":  float(v.get("COG", 0) or 0),
                "type": _AIS_TYPE_MAP.get(type_code, "Other"),
            })
        except (ValueError, TypeError):
            continue
    return pd.DataFrame(rows)


def _parse_datalastic(raw: dict) -> pd.DataFrame:
    """Parse Datalastic vessel-in-area response."""
    rows = []
    for v in raw.get("data", []):
        try:
            rows.append({
                "mmsi": str(v.get("mmsi", "")),
                "name": str(v.get("name", "UNKNOWN")).strip() or "UNKNOWN",
                "lat":  float(v["latitude"]),
                "lon":  float(v["longitude"]),
                "sog":  float(v.get("speed", 0) or 0),
                "cog":  float(v.get("course", 0) or 0),
                "type": str(v.get("vessel_type", "Other")),
            })
        except (KeyError, ValueError, TypeError):
            continue
    return pd.DataFrame(rows)


@st.cache_data(ttl=120, show_spinner=False)
def ingest_ais_ships() -> tuple[pd.DataFrame, str, str]:
    """
    Real-time AIS ingestion with a 3-source waterfall:

      1. AISHub  (free, registration required — set AISHUB_USER in secrets)
         https://www.aishub.net/api
         Endpoint: http://data.aishub.net/rec.php?format=1&...

      2. Datalastic  (freemium — set DATALASTIC_KEY in secrets)
         https://datalastic.com/api-reference/
         Endpoint: https://api.datalastic.com/api/endpoint/vessel_inarea

      3. Mock data  (hardcoded fallback — always works, clearly labelled)

    Secrets (.streamlit/secrets.toml):
    ───────────────────────────────────
    [aishub]
    username = "AIS-XXXXX"

    [datalastic]
    api_key = "your_key_here"
    ───────────────────────────────────
    Returns: (df, source_label, status)
    """
    headers = {"User-Agent": "SmartMaritimeDashboard/1.0 (BMKG-Research)"}
    timeout = 8

    # ── Source 1: AISHub ────────────────────────────────────────────────────
    try:
        aishub_user = st.secrets.get("aishub", {}).get("username", "")
        if aishub_user:
            resp = requests.get(
                "http://data.aishub.net/rec.php",
                params={
                    "username": aishub_user,
                    "format":   1,           # JSON
                    "output":   "json",
                    "compress": 0,
                    "latmin":   _BBOX["lat_min"],
                    "latmax":   _BBOX["lat_max"],
                    "lonmin":   _BBOX["lon_min"],
                    "lonmax":   _BBOX["lon_max"],
                },
                headers=headers,
                timeout=timeout,
            )
            resp.raise_for_status()
            raw = resp.json()
            df = _parse_aishub(raw)
            if not df.empty:
                df["timestamp"] = pd.Timestamp.utcnow()
                return df, "AISHub (live)", "live"
    except Exception as e:
        pass  # fall through to next source

    # ── Source 2: Datalastic ────────────────────────────────────────────────
    try:
        dl_key = st.secrets.get("datalastic", {}).get("api_key", "")
        if dl_key:
            resp = requests.get(
                "https://api.datalastic.com/api/endpoint/vessel_inarea",
                params={
                    "api-key":  dl_key,
                    "latitude1": _BBOX["lat_min"],
                    "latitude2": _BBOX["lat_max"],
                    "longitude1": _BBOX["lon_min"],
                    "longitude2": _BBOX["lon_max"],
                },
                headers=headers,
                timeout=timeout,
            )
            resp.raise_for_status()
            df = _parse_datalastic(resp.json())
            if not df.empty:
                df["timestamp"] = pd.Timestamp.utcnow()
                return df, "Datalastic (live)", "live"
    except Exception:
        pass

    # ── Source 3: Mock fallback ─────────────────────────────────────────────
    df = pd.DataFrame(_AIS_MOCK)
    df["timestamp"] = pd.Timestamp.utcnow()
    return df, "Mock data (no API key configured)", "mock"


# ─────────────────────────────────────────────────────────────────────────────
# ② DATA PROCESSING LAYER
# ─────────────────────────────────────────────────────────────────────────────

def regrid_wave_to_radar(
    df_radar: pd.DataFrame, df_wave: pd.DataFrame
) -> pd.DataFrame:
    """
    Spatial Regridding: interpolate coarse CMEMS wave grid (0.083°)
    onto the fine HF Radar grid (0.05°) using bilinear interpolation.

    Production version uses xarray.Dataset.interp():
    ─────────────────────────────────────────────────────────────────────────────
    import xarray as xr

    ds_wave  = xr.Dataset.from_dataframe(df_wave.set_index(["lat","lon"]))
    ds_radar = xr.Dataset.from_dataframe(df_radar.set_index(["lat","lon"]))

    ds_wave_regridded = ds_wave.interp(
        lat=ds_radar.lat,
        lon=ds_radar.lon,
        method="linear",
        kwargs={"fill_value": "extrapolate"},
    )
    ─────────────────────────────────────────────────────────────────────────────
    """
    from scipy.interpolate import griddata  # lightweight stand-in

    points = df_wave[["lon", "lat"]].values
    hs_vals = df_wave["hs"].values
    tp_vals = df_wave["tp"].values
    xi = df_radar[["lon", "lat"]].values

    df_radar = df_radar.copy()
    df_radar["hs"] = griddata(points, hs_vals, xi, method="linear")
    df_radar["tp"] = griddata(points, tp_vals, xi, method="linear")
    return df_radar


def compute_risk(df: pd.DataFrame) -> pd.DataFrame:
    """
    SOLAS Risk Calculation.
    Hazard zone definition (BMKG operational threshold):
      DANGER  : current_speed > 1.5 m/s  AND  Hs > 2.0 m
      CAUTION : current_speed > 1.0 m/s  OR   Hs > 1.5 m
      SAFE    : otherwise
    """
    df = df.copy()
    danger  = (df["speed"] > 1.5) & (df["hs"] > 2.0)
    caution = (~danger) & ((df["speed"] > 1.0) | (df["hs"] > 1.5))

    df["risk"] = "SAFE"
    df.loc[caution, "risk"] = "CAUTION"
    df.loc[danger, "risk"] = "DANGER"

    risk_map = {"SAFE": 0, "CAUTION": 1, "DANGER": 2}
    df["risk_score"] = df["risk"].map(risk_map)
    return df


def enrich_ships_with_risk(
    df_ships: pd.DataFrame, df_grid: pd.DataFrame
) -> pd.DataFrame:
    """Nearest-neighbour join to assign grid risk level to each ship."""
    from scipy.spatial import cKDTree

    tree = cKDTree(df_grid[["lon", "lat"]].values)
    _, idx = tree.query(df_ships[["lon", "lat"]].values)
    df_ships = df_ships.copy()
    df_ships["local_speed"] = df_grid["speed"].iloc[idx].values
    df_ships["local_hs"]    = df_grid["hs"].iloc[idx].values
    df_ships["risk"]        = df_grid["risk"].iloc[idx].values
    return df_ships


# ─────────────────────────────────────────────────────────────────────────────
# ③ VISUALISATION LAYER
# ─────────────────────────────────────────────────────────────────────────────
RISK_COLORS = {"SAFE": "#4caf50", "CAUTION": "#ffc107", "DANGER": "#f44336"}
SHIP_SYMBOLS = {"Cargo": "square", "Passenger": "circle", "Tanker": "diamond", "Tug": "triangle-up"}

MAPBOX_STYLE = "carto-darkmatter"


def _contourf_traces(df_grid: pd.DataFrame, n_levels: int) -> list:
    """
    Convert a scattered Hs grid into filled-contour polygon traces for Mapbox.

    Strategy:
      1. Pivot scattered points onto a regular 2-D numpy grid.
      2. Run matplotlib.contourf() in memory (no display) to get contour paths.
      3. Convert each filled contour polygon into a Scattermapbox trace with
         fill="toself", giving true contourf appearance on the map.

    Compatible with matplotlib >= 3.8 (uses allsegs / get_paths() rather than
    the removed .collections attribute).
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # ── Pivot to regular grid ────────────────────────────────────────────────
    lons_u = np.sort(df_grid["lon"].unique())
    lats_u = np.sort(df_grid["lat"].unique())
    pivot  = df_grid.pivot_table(index="lat", columns="lon", values="hs", aggfunc="mean")
    pivot  = pivot.reindex(index=lats_u, columns=lons_u)

    Z   = pivot.values
    LON = pivot.columns.values
    LAT = pivot.index.values
    Lon2, Lat2 = np.meshgrid(LON, LAT)

    # Fill any NaNs from edge gaps after regridding
    if np.isnan(Z).any():
        Z = pd.DataFrame(Z).interpolate(axis=1).interpolate(axis=0).values

    # ── Run contourf ─────────────────────────────────────────────────────────
    levels = np.linspace(max(float(np.nanmin(Z)), 0.0),
                         min(float(np.nanmax(Z)), 4.5),
                         n_levels + 1)
    fig_mpl, ax = plt.subplots()
    cf = ax.contourf(Lon2, Lat2, Z, levels=levels)
    plt.close(fig_mpl)

    # Colour palette: deep blue → cyan → yellow-green → orange
    hs_cmap_stops = [
        (0.00, (0,   30,  100, 0.55)),
        (0.20, (0,   90,  200, 0.60)),
        (0.45, (0,   190, 210, 0.65)),
        (0.70, (80,  210, 140, 0.65)),
        (0.85, (240, 180,  30, 0.70)),
        (1.00, (230,  60,  20, 0.75)),
    ]

    def _interp_color(t: float) -> str:
        for i in range(len(hs_cmap_stops) - 1):
            t0, c0 = hs_cmap_stops[i]
            t1, c1 = hs_cmap_stops[i + 1]
            if t0 <= t <= t1 + 1e-9:
                f = (t - t0) / max(t1 - t0, 1e-9)
                r = int(c0[0] + f * (c1[0] - c0[0]))
                g = int(c0[1] + f * (c1[1] - c0[1]))
                b = int(c0[2] + f * (c1[2] - c0[2]))
                a = round(c0[3] + f * (c1[3] - c0[3]), 2)
                return f"rgba({r},{g},{b},{a})"
        r, g, b, a = hs_cmap_stops[-1][1]
        return f"rgba({r},{g},{b},{a})"

    traces = []

    # Invisible dummy trace carries the colorbar
    traces.append(
        go.Scattermapbox(
            lat=[None], lon=[None],
            mode="markers",
            marker=dict(
                size=0,
                color=[levels[0], levels[-1]],
                colorscale=[[t, f"rgba({c[0]},{c[1]},{c[2]},{c[3]})"]
                            for t, c in hs_cmap_stops],
                cmin=float(levels[0]),
                cmax=float(levels[-1]),
                showscale=True,
                colorbar=dict(
                    title=dict(text="Hs (m)", font=dict(color="#8ab4d4", size=11)),
                    tickfont=dict(color="#8ab4d4", size=10),
                    x=1.01,
                    thickness=10,
                    len=0.5,
                    tickvals=np.round(levels, 1).tolist(),
                ),
            ),
            showlegend=False,
            hoverinfo="skip",
            name="Hs colorbar",
        )
    )

    # ── Extract polygons — works on matplotlib 3.8+ ──────────────────────────
    # allsegs[i]  = list of (N,2) ndarray, one per filled polygon in band i
    # collections  = legacy API removed in mpl 3.10
    n_bands = len(levels) - 1
    if hasattr(cf, "allsegs"):
        band_segs = cf.allsegs                          # list[list[ndarray]]
    else:
        # mpl < 3.8 fallback: extract vertices from Path objects
        band_segs = [[p.vertices for p in coll.get_paths()]
                     for coll in cf.collections]

    for i, segs in enumerate(band_segs):
        t_norm = i / max(n_bands - 1, 1)
        fill_color = _interp_color(t_norm)
        lo, hi = float(levels[i]), float(levels[i + 1])

        for verts in segs:
            verts = np.asarray(verts)
            if len(verts) < 3:
                continue
            lons_p = verts[:, 0].tolist() + [verts[0, 0]]
            lats_p = verts[:, 1].tolist() + [verts[0, 1]]

            traces.append(
                go.Scattermapbox(
                    lon=lons_p,
                    lat=lats_p,
                    mode="lines",
                    fill="toself",
                    fillcolor=fill_color,
                    line=dict(width=0.5, color=fill_color),
                    showlegend=False,
                    name=f"Hs {lo:.1f}–{hi:.1f} m",
                    hovertemplate=f"Hs: {lo:.1f}–{hi:.1f} m<extra>Contourf</extra>",
                )
            )

    return traces


def build_main_map(
    df_grid: pd.DataFrame,
    df_ships: pd.DataFrame,
    hs_mode: str = "Density (smooth)",
    n_contours: int = 6,
    zoom: int = 9,
) -> go.Figure:
    # Region centres (used when sidebar focus changes — extensible)
    lon_center = 105.85
    lat_center = -6.15

    fig = go.Figure()

    # ── Wave height layer ────────────────────────────────────────────────────
    if hs_mode == "Contourf (filled contours)":
        for tr in _contourf_traces(df_grid, n_contours):
            fig.add_trace(tr)
    else:
        fig.add_trace(
            go.Densitymapbox(
                lat=df_grid["lat"],
                lon=df_grid["lon"],
                z=df_grid["hs"],
                radius=18,
                colorscale=[
                    [0.0, "rgba(0,60,120,0.0)"],
                    [0.3, "rgba(0,100,200,0.35)"],
                    [0.6, "rgba(0,180,255,0.55)"],
                    [1.0, "rgba(255,80,20,0.75)"],
                ],
                zmin=0,
                zmax=4,
                name="Wave Height Hs (m)",
                showscale=True,
                colorbar=dict(
                    title=dict(text="Hs (m)", font=dict(color="#8ab4d4", size=11)),
                    tickfont=dict(color="#8ab4d4", size=10),
                    x=1.01,
                    thickness=10,
                    len=0.5,
                ),
                hovertemplate="Lat: %{lat:.3f}<br>Lon: %{lon:.3f}<br>Hs: %{z:.2f} m<extra>Wave Model</extra>",
            )
        )

    # ── Current vectors (arrows via scattermapbox + quiver trick) ───────────
    df_sub = df_grid.iloc[::3].copy()
    scale = 0.04
    for _, row in df_sub.iterrows():
        speed_norm = min(row["speed"] / 2.5, 1.0)
        color = f"rgba({int(255*speed_norm)},{int(180*(1-speed_norm))},{int(255*(1-speed_norm))},0.8)"
        fig.add_trace(
            go.Scattermapbox(
                lat=[row["lat"], row["lat"] + row["v"] * scale],
                lon=[row["lon"], row["lon"] + row["u"] * scale],
                mode="lines+markers",
                line=dict(color=color, width=1.5),
                marker=dict(size=[0, 5], color=color),
                showlegend=False,
                hoverinfo="skip",
            )
        )

    # ── Risk overlay ─────────────────────────────────────────────────────────
    for risk_lvl in ["SAFE", "CAUTION", "DANGER"]:
        sub = df_grid[df_grid["risk"] == risk_lvl]
        if sub.empty:
            continue
        fig.add_trace(
            go.Scattermapbox(
                lat=sub["lat"],
                lon=sub["lon"],
                mode="markers",
                marker=dict(
                    size=7,
                    color=RISK_COLORS[risk_lvl],
                    opacity=0.35 if risk_lvl == "SAFE" else 0.65,
                ),
                name=f"Risk: {risk_lvl}",
                hovertemplate=(
                    f"<b>{risk_lvl}</b><br>"
                    "Lat: %{lat:.3f}<br>Lon: %{lon:.3f}<extra></extra>"
                ),
            )
        )

    # ── Ship icons ───────────────────────────────────────────────────────────
    for ship_type, symbol in SHIP_SYMBOLS.items():
        ships_sub = df_ships[df_ships["type"] == ship_type]
        if ships_sub.empty:
            continue
        risk_colors = ships_sub["risk"].map(RISK_COLORS).tolist()
        fig.add_trace(
            go.Scattermapbox(
                lat=ships_sub["lat"],
                lon=ships_sub["lon"],
                mode="markers+text",
                marker=dict(size=14, color=risk_colors, symbol="marker"),
                text=ships_sub["name"].str.split().str[-1],
                textposition="top right",
                textfont=dict(size=9, color="#c8dff0"),
                name=ship_type,
                customdata=ships_sub[["mmsi", "name", "sog", "cog", "local_speed", "local_hs", "risk"]].values,
                hovertemplate=(
                    "<b>%{customdata[1]}</b><br>"
                    "MMSI: %{customdata[0]}<br>"
                    "SOG: %{customdata[2]} kn | COG: %{customdata[3]}°<br>"
                    "Local Current: %{customdata[4]:.2f} m/s<br>"
                    "Local Hs: %{customdata[5]:.2f} m<br>"
                    "Risk: <b>%{customdata[6]}</b><extra></extra>"
                ),
            )
        )

    fig.update_layout(
        mapbox=dict(
            style=MAPBOX_STYLE,
            center=dict(lat=lat_center, lon=lon_center),
            zoom=zoom,
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=580,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            bgcolor="rgba(5,13,26,0.85)",
            bordercolor="#1a3a5c",
            borderwidth=1,
            font=dict(color="#8ab4d4", size=10),
            x=0.01,
            y=0.99,
        ),
        font=dict(family="Exo 2, sans-serif"),
    )
    return fig


def build_speed_histogram(df_grid: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    colors = {"SAFE": "#4caf50", "CAUTION": "#ffc107", "DANGER": "#f44336"}
    for lvl, col in colors.items():
        sub = df_grid[df_grid["risk"] == lvl]["speed"]
        fig.add_trace(go.Histogram(x=sub, name=lvl, marker_color=col, opacity=0.8, nbinsx=20))
    fig.update_layout(
        barmode="overlay",
        xaxis_title="Current Speed (m/s)",
        yaxis_title="Grid Points",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(13,33,55,0.5)",
        font=dict(color="#8ab4d4", size=11),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
        margin=dict(l=40, r=10, t=10, b=40),
        height=200,
    )
    fig.update_xaxes(gridcolor="#1a3a5c", zerolinecolor="#1a3a5c")
    fig.update_yaxes(gridcolor="#1a3a5c")
    return fig


def build_hs_timeseries() -> go.Figure:
    """Mock 24-hour Hs forecast for the narrows."""
    hours = pd.date_range(pd.Timestamp.utcnow(), periods=24, freq="1h")
    hs_fc = 1.5 + 0.8 * np.sin(np.linspace(0, 2 * np.pi, 24)) + np.random.default_rng(7).normal(0, 0.15, 24)
    fig = go.Figure(
        go.Scatter(
            x=hours,
            y=hs_fc,
            mode="lines+markers",
            line=dict(color="#4fc3f7", width=2),
            marker=dict(size=5, color="#4fc3f7"),
            fill="tozeroy",
            fillcolor="rgba(79,195,247,0.12)",
            name="Hs Forecast",
            hovertemplate="%{x|%H:%M UTC}<br>Hs = %{y:.2f} m<extra></extra>",
        )
    )
    fig.add_hline(y=2.0, line_dash="dash", line_color="#f44336", annotation_text="SOLAS Threshold 2.0 m", annotation_font_color="#f44336")
    fig.update_layout(
        xaxis_title="UTC Time",
        yaxis_title="Hs (m)",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(13,33,55,0.5)",
        font=dict(color="#8ab4d4", size=11),
        margin=dict(l=40, r=10, t=10, b=40),
        height=200,
        showlegend=False,
    )
    fig.update_xaxes(gridcolor="#1a3a5c", tickformat="%H:%M")
    fig.update_yaxes(gridcolor="#1a3a5c")
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# ④ SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown(
            """
            <div style="text-align:center;padding:10px 0 20px">
              <div style="font-size:2.2rem">🌊</div>
              <div style="font-family:'Exo 2',sans-serif;font-weight:800;font-size:1.1rem;color:#4fc3f7;letter-spacing:0.05em">SMART MARITIME</div>
              <div style="font-size:0.7rem;color:#5b93c7;letter-spacing:0.15em">DASHBOARD — SUNDA STRAIT</div>
              <div style="font-size:0.65rem;color:#2d5a80;margin-top:4px">BMKG | SOLAS Innovation</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('<div class="section-header">⚙️ Display Controls</div>', unsafe_allow_html=True)
        show_risk = st.toggle("Show Risk Overlay", value=True)
        show_ships = st.toggle("Show AIS Ships", value=True)
        show_vectors = st.toggle("Show Current Vectors", value=True)

        st.markdown('<div class="section-header">🌊 Wave Height (Hs) Display</div>', unsafe_allow_html=True)
        hs_mode = st.radio(
            "Hs Rendering",
            ["Density (smooth)", "Contourf (filled contours)"],
            index=0,
            label_visibility="collapsed",
        )
        if hs_mode == "Contourf (filled contours)":
            n_contours = st.slider("Contour levels", 4, 12, 6, 1)
        else:
            n_contours = 6

        st.markdown('<div class="section-header">📡 Data Sources</div>', unsafe_allow_html=True)
        st.markdown(
            """
            <div class="info-box">
              <b>HF Radar</b> — BMKG Selat Sunda<br>
              Res: 0.05° | Refresh: 10 min<br>
              <span style='color:#ffc107'>◌ Mock (awaiting BMKG access)</span><br><br>
              <b>Wave Model</b> — CMEMS GloWave<br>
              Res: 0.083° | Refresh: 30 min<br>
              <span style='color:#ffc107'>◌ Mock (awaiting Copernicus creds)</span><br><br>
              <b>AIS</b> — AISHub / Datalastic<br>
              Refresh: 2 min<br>
              <span style='color:#4caf50'>● Live (configure key in secrets.toml)</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="section-header">🎚️ Risk Thresholds</div>', unsafe_allow_html=True)
        spd_thresh = st.slider("Current Speed (m/s)", 0.5, 3.0, 1.5, 0.1)
        hs_thresh  = st.slider("Wave Height Hs (m)",  0.5, 4.0, 2.0, 0.1)

        st.markdown('<div class="section-header">🗺️ Region Focus</div>', unsafe_allow_html=True)
        region = st.selectbox(
            "Focus Area",
            ["Full Strait", "Northern Entrance", "Central Narrows", "Southern Exit"],
        )
        # Map zoom slider
        zoom_level = st.slider("Map Zoom", min_value=7, max_value=13, value=9, step=1)

        st.markdown("---")
        st.markdown(
            f"<div style='font-size:0.68rem;color:#2d5a80;text-align:center'>"
            f"Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC</div>",
            unsafe_allow_html=True,
        )
        auto_refresh = st.toggle("Auto-Refresh (2 min)", value=False)
        if auto_refresh:
            time.sleep(120)
            st.rerun()

    return show_risk, show_ships, show_vectors, spd_thresh, hs_thresh, hs_mode, n_contours, zoom_level


# ─────────────────────────────────────────────────────────────────────────────
# ⑤ MAIN APP
# ─────────────────────────────────────────────────────────────────────────────
def main():
    show_risk, show_ships, show_vectors, spd_thresh, hs_thresh, hs_mode, n_contours, zoom_level = render_sidebar()

    # Header ─────────────────────────────────────────────────────────────────
    col_h1, col_h2, col_h3 = st.columns([5, 2, 1])
    with col_h1:
        st.markdown(
            "<h1 style='font-family:Exo 2,sans-serif;font-weight:800;font-size:1.6rem;"
            "color:#4fc3f7;margin:0;letter-spacing:0.04em'>"
            "🌊 Smart Maritime Dashboard</h1>"
            "<div style='color:#5b93c7;font-size:0.78rem;letter-spacing:0.1em'>"
            "SUNDA STRAIT, INDONESIA — BMKG SOLAS INNOVATION PROJECT</div>",
            unsafe_allow_html=True,
        )
    with col_h2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with col_h3:
        st.markdown("<br>", unsafe_allow_html=True)
        now_str = datetime.now(timezone.utc).strftime("%H:%M UTC")
        st.markdown(
            f"<div style='font-family:Share Tech Mono,monospace;font-size:0.9rem;"
            f"color:#4fc3f7;text-align:center;padding-top:4px'>{now_str}</div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ── Load data ────────────────────────────────────────────────────────────
    with st.spinner("📡 Ingesting HF Radar, wave model, and AIS data…"):
        df_radar                      = ingest_hf_radar()
        df_wave                       = ingest_wave_model()
        df_ships, ais_source, ais_mode = ingest_ais_ships()
        df_grid                       = regrid_wave_to_radar(df_radar, df_wave)
        df_grid                       = compute_risk(df_grid)
        df_ships                      = enrich_ships_with_risk(df_ships, df_grid)

    # ── Data source status banner ─────────────────────────────────────────────
    src_cols = st.columns(3)
    _src_badges = [
        ("🔴 HF Radar",   "BMKG Selat Sunda",  "mock",  "Awaiting BMKG data access"),
        ("🔵 Wave Model",  "CMEMS GloWave",      "mock",  "Awaiting Copernicus credentials"),
        ("🟢 AIS",         ais_source,           ais_mode, ""),
    ]
    for col, (icon, label, mode, note) in zip(src_cols, _src_badges):
        with col:
            if mode == "live":
                pill_style = "background:#0a3a1e;color:#4caf50;border:1px solid #4caf50"
                pill_text  = "● LIVE"
            else:
                pill_style = "background:#3a2a00;color:#ffc107;border:1px solid #ffc107"
                pill_text  = "◌ MOCK"
            st.markdown(
                f"<div style='background:#0d2137;border:1px solid #1a3a5c;border-radius:8px;"
                f"padding:8px 14px;font-size:0.76rem;display:flex;align-items:center;gap:10px'>"
                f"<span style='font-size:1rem'>{icon.split()[0]}</span>"
                f"<div><b style='color:#c8dff0'>{icon.split(None,1)[1]}</b><br>"
                f"<span style='color:#5b93c7'>{label}</span>"
                f"{'<br><span style=color:#5b93c7;font-style:italic>' + note + '</span>' if note else ''}"
                f"</div>"
                f"<span style='margin-left:auto;{pill_style};border-radius:5px;padding:2px 8px;"
                f"font-size:0.7rem;font-weight:700;white-space:nowrap'>{pill_text}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    # ── KPI Row ──────────────────────────────────────────────────────────────
    n_danger  = (df_grid["risk"] == "DANGER").sum()
    n_caution = (df_grid["risk"] == "CAUTION").sum()
    n_total   = len(df_grid)
    max_speed = df_grid["speed"].max()
    max_hs    = df_grid["hs"].max()
    ships_at_risk = (df_ships["risk"] != "SAFE").sum()

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    metrics = [
        (k1, "Max Current Speed", f"{max_speed:.2f}", "m/s"),
        (k2, "Max Wave Height",   f"{max_hs:.2f}",   "m"),
        (k3, "Danger Zones",      str(n_danger),       "grid pts"),
        (k4, "Caution Zones",     str(n_caution),      "grid pts"),
        (k5, "Vessels Tracked",   str(len(df_ships)),  "AIS ships"),
        (k6, "Ships at Risk",     str(ships_at_risk),  "vessels"),
    ]
    for col, label, value, unit in metrics:
        with col:
            st.markdown(
                f'<div class="metric-card"><h3>{label}</h3>'
                f'<div class="value">{value}</div>'
                f'<div class="unit">{unit}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Map + Side panels ────────────────────────────────────────────────────
    col_map, col_side = st.columns([3, 1])
    with col_map:
        st.markdown('<div class="section-header">🗺️ Live Maritime Chart — Sunda Strait</div>', unsafe_allow_html=True)
        fig_map = build_main_map(df_grid, df_ships, hs_mode=hs_mode, n_contours=n_contours, zoom=zoom_level)
        st.plotly_chart(
            fig_map,
            use_container_width=True,
            config={
                "scrollZoom": True,
                "displayModeBar": True,
                "modeBarButtonsToRemove": [
                    "select2d", "lasso2d", "autoScale2d",
                    "hoverClosestCartesian", "hoverCompareCartesian",
                    "toggleSpikelines",
                ],
                "modeBarButtonsToAdd": ["zoomInGeo", "zoomOutGeo", "resetGeo"],
                "displaylogo": False,
                "toImageButtonOptions": {
                    "format": "png",
                    "filename": "sunda_strait_maritime_chart",
                    "height": 800,
                    "width": 1400,
                    "scale": 2,
                },
            },
        )

    with col_side:
        # AIS table
        st.markdown('<div class="section-header">🚢 AIS Vessel List</div>', unsafe_allow_html=True)
        for _, ship in df_ships.iterrows():
            badge_cls = f"badge-{ship['risk'].lower()}"
            st.markdown(
                f"<div style='background:#0d2137;border:1px solid #1a3a5c;border-radius:8px;"
                f"padding:8px 12px;margin-bottom:6px;font-size:0.75rem'>"
                f"<b style='color:#c8dff0'>{ship['name']}</b><br>"
                f"<span style='color:#5b93c7'>SOG {ship['sog']} kn | COG {ship['cog']}°</span><br>"
                f"Hs: <b>{ship['local_hs']:.2f} m</b> | Spd: <b>{ship['local_speed']:.2f} m/s</b><br>"
                f"<span class='{badge_cls}'>{ship['risk']}</span> — {ship['type']}"
                f"</div>",
                unsafe_allow_html=True,
            )

    # ── Bottom charts ────────────────────────────────────────────────────────
    st.markdown("---")
    col_hist, col_ts = st.columns(2)
    with col_hist:
        st.markdown('<div class="section-header">📊 Current Speed Distribution by Risk Level</div>', unsafe_allow_html=True)
        st.plotly_chart(build_speed_histogram(df_grid), use_container_width=True, config={"displayModeBar": False})
    with col_ts:
        st.markdown('<div class="section-header">📈 24-h Hs Forecast — Narrows (6°S, 105.85°E)</div>', unsafe_allow_html=True)
        st.plotly_chart(build_hs_timeseries(), use_container_width=True, config={"displayModeBar": False})

    # ── Risk summary table ───────────────────────────────────────────────────
    st.markdown("---")
    st.markdown('<div class="section-header">⚠️ Active Risk Alerts</div>', unsafe_allow_html=True)
    danger_ships = df_ships[df_ships["risk"] == "DANGER"]
    if danger_ships.empty:
        st.markdown('<div class="info-box">✅ No vessels currently in DANGER zones.</div>', unsafe_allow_html=True)
    else:
        st.dataframe(
            danger_ships[["name", "type", "lat", "lon", "sog", "local_speed", "local_hs", "risk"]]
            .rename(columns={"name": "Vessel", "type": "Type", "lat": "Lat", "lon": "Lon",
                              "sog": "SOG (kn)", "local_speed": "Current (m/s)", "local_hs": "Hs (m)", "risk": "Risk"}),
            use_container_width=True,
            hide_index=True,
        )

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown(
        "<div style='text-align:center;margin-top:30px;font-size:0.68rem;color:#2d5a80'>"
        "Smart Maritime Dashboard | Kapita Selekta — BMKG SOLAS Innovation | "
        "Data: HF Radar BMKG · CMEMS GloWave · AISHub · Synthetic Demo Mode"
        "</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
