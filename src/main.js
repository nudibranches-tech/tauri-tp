import { open } from "@tauri-apps/plugin-dialog";
import { invoke } from "@tauri-apps/api/core";

// Leaflet is loaded from the CDN <script> in index.html, exposed as global `L`.

// 1. A map centred on Montpellier. preferCanvas keeps it smooth with thousands
//    of rectangles.
const map = L.map("map", { preferCanvas: true }).setView([43.61, 3.88], 9);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "© OpenStreetMap contributors",
  maxZoom: 19,
}).addTo(map);

// One layer group holds the temperature cells so we can clear it on reload.
const cells = L.layerGroup().addTo(map);
const statusEl = document.querySelector("#status");

// 2. Map a temperature (°C) to a colour: blue (-5) → red (35).
function colorForTemp(celsius) {
  const ratio = Math.max(0, Math.min(1, (celsius - -5) / (35 - -5)));
  const hue = 240 - 240 * ratio;
  return `hsl(${hue}, 85%, 50%)`;
}

// 3. Open a GRIB file, decode it in Rust, draw one rectangle per grid cell.
async function loadFile() {
  const path = await open({
    multiple: false,
    directory: false,
    filters: [{ name: "GRIB2", extensions: ["grib2", "grb2", "grib"] }],
  });
  if (!path) return; // user cancelled

  statusEl.textContent = "Decoding…";
  try {
    const points = await invoke("load_temperature", { path });
    cells.clearLayers();

    for (const { lat, lon, value } of points) {
      L.rectangle(
        [
          [lat - 0.0125, lon - 0.0125],
          [lat + 0.0125, lon + 0.0125],
        ],
        { stroke: false, fillColor: colorForTemp(value), fillOpacity: 0.6 },
      )
        .bindTooltip(`${value.toFixed(1)} °C`)
        .addTo(cells);
    }

    statusEl.textContent = `Drew ${points.length} temperature cells.`;
  } catch (err) {
    statusEl.textContent = `Error: ${err}`;
    console.error(err);
  }
}

document.querySelector("#load-btn").addEventListener("click", loadFile);
