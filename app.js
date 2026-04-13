const map = L.map('map').setView([-6.0, 105.9], 11);
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png').addTo(map);

// 1. DATA KAPAL
const ships = [
    {
        name: "KMP SEBUKU", lat: -5.89, lon: 105.82, course: 115, dest: [-5.93, 106.00],
        timeline: [
            {pos: [-5.90, 105.86], icon: "🌧️", desc: "10:30 | Hujan"},
            {pos: [-5.93, 106.00], icon: "☀️", desc: "11:15 | Cerah"}
        ]
    }
];

// 2. FUNGSI BACA .NC (70KB)
async function loadRadarData() {
    const response = await fetch('CODAR_BADA_2025_04_12_1400.nc'); // Pastikan file ada di GitHub
    const buffer = await response.arrayBuffer();
    const reader = new netcdfjs(buffer);
    
    // Contoh pengambilan data (sesuaikan dengan nama variabel di file .nc kamu)
    // const u = reader.getDataVariable('u'); 
    // const v = reader.getDataVariable('v');
    
    console.log("Radar Data Loaded via JS");
}

// 3. RENDER KAPAL & INTERAKSI
let activeWaypoints = L.layerGroup().addTo(map);

ships.forEach(s => {
    // Garis Rute Standar
    const route = L.polyline([[s.lat, s.lon], s.dest], {color: '#3498db', weight: 2}).addTo(map);

    // Marker Kapal
    const marker = L.divIcon({
        html: `<div style="transform:rotate(${s.course}deg); color:#FF4B4B; font-size:26px;">➤</div>`,
        className: 'ship-icon'
    });

    const shipMarker = L.marker([s.lat, s.lon], {icon: marker}).addTo(map);

    // Event Klik
    shipMarker.on('click', () => {
        // Reset rute lain
        map.eachLayer(l => { if(l instanceof L.PolyLine) l.setStyle({color:'#3498db', weight:2}); });
        activeWaypoints.clearLayers();

        // Aktifkan Kapal Ini
        route.setStyle({color: '#00f2ff', weight: 5});
        s.timeline.forEach(wp => {
            L.marker(wp.pos, {
                icon: L.divIcon({ html: `<div class="weather-wp">${wp.icon}</div>`, className: '' })
            }).addTo(activeWaypoints);
        });
    });
});

loadRadarData();
