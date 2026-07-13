export interface MapPin {
  id: string | number;
  lat: number;
  lng: number;
  label: string;
  subtitle?: string;
  kind: "device" | "member";
  tappable?: boolean;
}

interface BuildMapOptions {
  zoom?: number;
}

// Dark CartoDB basemap (free, no API key) to match the app's dark UI instead
// of Leaflet's default light OSM raster tiles.
const DARK_TILE_URL = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";
const DARK_TILE_ATTRIBUTION = "&copy; OpenStreetMap contributors &copy; CARTO";

const PIN_COLOR: Record<MapPin["kind"], string> = {
  device: "#dc2626", // matches the app's alert/camera red
  member: "#60a5fa", // matches the app's accent blue
};

// Custom Leaflet divIcon (styled HTML/CSS) with a pulsing ring, instead of
// the default blue teardrop marker -- no image assets needed.
function markerIconJs(pin: MapPin) {
  const color = PIN_COLOR[pin.kind];
  return `L.divIcon({
    className: '',
    html: '<div class="pin-wrap"><div class="pin-pulse" style="background:${color}"></div><div class="pin-dot" style="background:${color}"></div></div>',
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    popupAnchor: [0, -16],
  })`;
}

export function buildMapHtml(pins: MapPin[], options: BuildMapOptions = {}): string {
  const zoom = options.zoom ?? 15;
  const center = pins[0] ?? { lat: 0, lng: 0 };

  const markersJs = pins
    .map(
      (p) => `
      (function() {
        var marker = L.marker([${p.lat}, ${p.lng}], { icon: ${markerIconJs(p)} }).addTo(map);
        marker.bindPopup(${JSON.stringify(popupHtml(p))});
        ${
          p.tappable
            ? `marker.on('click', function() {
                 if (window.ReactNativeWebView) {
                   window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'pinTap', id: ${JSON.stringify(p.id)} }));
                 }
               });`
            : ""
        }
      })();`
    )
    .join("\n");

  return `<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <style>
    html, body, #map { margin:0; padding:0; height:100%; background:#0f172a; }
    .leaflet-popup-content-wrapper {
      background:#1e293b; color:#e2e8f0; border-radius:10px;
      box-shadow:0 8px 24px rgba(0,0,0,0.4);
    }
    .leaflet-popup-tip { background:#1e293b; }
    .leaflet-popup-content { margin:12px 14px; font-family:-apple-system,Roboto,sans-serif; }
    .popup-title { font-weight:700; font-size:14px; margin-bottom:2px; color:#fff; }
    .popup-subtitle { font-size:12px; color:#94a3b8; }
    .pin-wrap { position:relative; width:28px; height:28px; }
    .pin-dot {
      position:absolute; top:8px; left:8px; width:12px; height:12px;
      border-radius:50%; border:2px solid #0f172a; box-shadow:0 0 6px rgba(0,0,0,0.5);
    }
    .pin-pulse {
      position:absolute; top:0; left:0; width:28px; height:28px; border-radius:50%;
      opacity:0.45; animation: pulse 2s ease-out infinite;
    }
    @keyframes pulse {
      0% { transform: scale(0.4); opacity: 0.55; }
      100% { transform: scale(1.4); opacity: 0; }
    }
    .leaflet-control-attribution { background: rgba(15,23,42,0.7) !important; color:#64748b !important; }
    .leaflet-control-attribution a { color:#94a3b8 !important; }
  </style>
  </head>
  <body>
    <div id="map"></div>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
      const map = L.map('map', { zoomControl: true }).setView([${center.lat}, ${center.lng}], ${zoom});
      L.tileLayer('${DARK_TILE_URL}', { attribution: '${DARK_TILE_ATTRIBUTION}', maxZoom: 19 }).addTo(map);
      ${markersJs}
      setTimeout(function() {
        map.flyTo([${center.lat}, ${center.lng}], ${zoom}, { duration: 1.1 });
      }, 200);
    </script>
  </body></html>`;
}

function popupHtml(pin: MapPin): string {
  return `<div class="popup-title">${escapeHtml(pin.label)}</div>${
    pin.subtitle ? `<div class="popup-subtitle">${escapeHtml(pin.subtitle)}</div>` : ""
  }`;
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
