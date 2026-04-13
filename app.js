const map = L.map('map').setView([-5.9, 105.85], 11);

// Basemap Gelap
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png').addTo(map);

// --- 1. RENDER DATA RADAR (GeoJSON) ---
fetch('radar_data.json')
    .then(response => response.json())
    .then(data => {
        L.geoJSON(data, {
            pointToLayer: function (feature, latlng) {
                const speed = feature.properties.speed;
                
                // Abaikan jika speed adalah NaN
                if (isNaN(speed) || speed === null) return null;

                // Tentukan warna berdasarkan kecepatan (degradasi Biru ke Merah)
                let color = "#3b4cc0"; // Low speed (Blue)
                if (speed > 0.4) color = "#add1fb";
                if (speed > 0.6) color = "#f7ad8f";
                if (speed > 0.8) color = "#b40426"; // High speed (Red)

                return L.circleMarker(latlng, {
                    radius: 5,
                    fillColor: color,
                    color: "#fff",
                    weight: 0.5,
                    fillOpacity: 0.8
                });
            },
            onEachFeature: function (feature, layer) {
                layer.bindTooltip(`Speed: ${feature.properties.speed} m/s`);
            }
        }).addTo(map);
    });

// --- 2. DATA KAPAL & INTERAKSI ---
const ships = [
    {
        name: "KMP SEBUKU", lat: -5.89, lon: 105.82, course: 115, dest: [-5.93, 106.00],
        speed: "10.8 kn", eta: "11:15 UTC",
        timeline: [
            {pos: [-5.90, 105.86], icon: "🌧️"},
            {pos: [-5.93, 106.00], icon: "☀️"}
        ]
    }
];

let activeWaypoints = L.layerGroup().addTo(map);

ships.forEach(s => {
    const route = L.polyline([[s.lat, s.lon], s.dest], {color: '#3498db', weight: 2, opacity: 0.7}).addTo(map);
    const shipIcon = L.divIcon({
        html: `<div style="transform:rotate(${s.course}deg); color:#FF4B4B; font-size:26px; cursor:pointer;">➤</div>`,
        className: 'ship-marker'
    });

    const marker = L.marker([s.lat, s.lon], {icon: shipIcon}).addTo(map);

    marker.on('click', function() {
        // Reset state
        activeWaypoints.clearLayers();
        route.setStyle({color: '#00f2ff', weight: 5});
        
        // Munculkan Waypoint Cuaca
        s.timeline.forEach(wp => {
            L.marker(wp.pos, {
                icon: L.divIcon({ html: `<div class="weather-wp">${wp.icon}</div>`, className: '' })
            }).addTo(activeWaypoints);
        });
    });
});
