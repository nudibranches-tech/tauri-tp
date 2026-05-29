# Lab — Desktop Weather Map from Open Data (Tauri + Rust + Leaflet)

**Duration:** 4 h (30 min intro + 3 h 30 hands-on) · **You will build:** a desktop app that opens a
Météo-France **AROME** weather file (GRIB2), reads the **2 m air temperature** in Rust, and draws it
as a colored grid on an interactive map of **Montpellier**.

> This handout gives you the **goal, the key tools, and hints** for each step — not the full solution.
> A **Cheat-sheet** (last page) lists the exact function names you'll need so you never get fully stuck.

```
 JavaScript frontend            Rust backend
   - file dialog     invoke()     - read the file
   - Leaflet map   ───────────►   - decode GRIB2
   - draw cells    ◄───────────   - return [{lat,lon,value}]
```

| Time | Part | Goal |
|------|------|------|
| 0:00–0:30 | Intro | Concepts: open data, GRIB, how the app works |
| 0:30–1:00 | 1 | Install & scaffold the app |
| 1:00–1:15 | 2 | Get an AROME GRIB file |
| 1:15–2:15 | 3 | Decode the temperature in Rust |
| 2:15–3:25 | 4 | Show it on a Leaflet map |
| 3:25–4:00 | 5 | Polish + bonus |

---

## Part 0 — Concepts (30 min)

### Open data

**Open data** = data anyone can freely access, reuse and share. To be "open" it should be online,
**machine-readable**, openly **licensed**, and usually **free**. Weather is a flagship example: forecasts
are computed on supercomputers and published openly by public agencies (Météo-France, NOAA, ECMWF, DWD…).

**Think about — local uses around Montpellier:** vineyard frost & irrigation · urban heat islands ·
sailing/wind on the Golfe du Lion · solar energy production. *What else could a 2.5 km forecast improve?*

### What is a weather model? (AROME)

A numerical weather model divides the atmosphere into a 3-D grid of cells and computes physics equations
to forecast each cell's temperature, wind, humidity, etc., for the coming hours. **AROME** (Météo-France)
is a **high-resolution** model: horizontal grid ≈ **0.025° (~2.5 km)**, covering France including
**Montpellier (43.61° N, 3.88° E)**. New forecasts ("runs") are produced at **00/06/12/18 UTC**, and the
output is shipped as **GRIB2** files.

### What is a GRIB file, and how does it work?

**GRIB** = *GRIdded Binary*. It is the **WMO international standard** for storing gridded weather/ocean
data — compact, binary, and *self-describing* (each field carries the metadata needed to interpret it).
We use **GRIB2** (the current version; GRIB1 is the old one).

Mental model: **a GRIB file is a stack of labeled "spreadsheets."** Each sheet is a 2-D grid of numbers
for **one variable, at one level, for one forecast time** (e.g. "2 m temperature, +3 h"). Next to each
sheet there is a **label** ("what am I?") and a **recipe** ("how to unpack my numbers").

```
GRIB2 file
 ├── message  ──►  one 2-D field (a "submessage")
 │     ├── Indicator        : "GRIB", discipline (0 = meteorology), length
 │     ├── Identification   : center, run/reference time
 │     ├── Grid Definition  : grid type + size + corner lat/lon + step   ("where")
 │     ├── Product Definition: parameter, level, forecast time           ("what")
 │     ├── Data Representation: packing method + parameters               ("how to unpack")
 │     ├── Bit-map           : which points actually have a value
 │     └── Data              : the packed (compressed) numbers
 ├── message  ──►  another field …
 └── …                                                end marker "7777"
```

Three ideas matter for this lab:

1. **The "what" is stored as numbers, not text** (for compactness and language independence). You look
   them up in **WMO code tables**. For us: **2 m air temperature** = `discipline 0` (meteorology),
   `parameter category 0` (temperature), `parameter number 0` (temperature), at fixed surface
   **height 2 m**. Values are in **SI units → Kelvin** (so subtract 273.15 for °C).

2. **The "where" is a grid description, not a coordinate per point.** The Grid Definition stores the
   corner coordinates and the step (e.g. 0.025°); the latitude/longitude of every point is *derived* from
   it. The library does this for us via `latlons()`.

3. **The data is packed (compressed).** Raw floats would be huge, so values are encoded as scaled
   integers and then compressed. GRIB2 allows several methods (*simple*, *complex*, *JPEG2000*,
   **CCSDS/AEC**, PNG…). The **AROME open-data** files we download use **CCSDS/AEC**, which is why our Rust
   dependency needs the **libaec** library — and why we never read the bytes by hand: a GRIB **decoder**
   reconstructs the real numbers for us.

So our backend will: **iterate the fields → read each label (Product Definition) → keep the 2 m
temperature one → ask for its coordinates (`latlons`) and its decoded values, then pair them up.**

### How our app is built (Tauri)

A **Tauri** app = a native window showing a **web UI** (HTML/CSS/JS) backed by a **Rust** program.
Heavy/low-level work (decoding GRIB) runs in **Rust**; the **UI** runs in the webview. The two talk through
one bridge: the frontend calls a Rust function with **`invoke("name", { args })`**, and Rust returns JSON.
That's the only "magic" to learn.

### How a web map works (Leaflet)

**Leaflet** shows a slippy map made of small image **tiles** fetched from a server (we use free
**OpenStreetMap** tiles). You place things on it using **(latitude, longitude)** — exactly the coordinates
our decoder produces. We'll draw one small colored rectangle per grid cell to make a temperature "image".

---

## Part 1 — Install & scaffold (30 min)

**Toolchains:** Rust (via [rustup.rs](https://rustup.rs)) and Node.js (LTS).

**System libraries** (needed by the webview *and* the GRIB decoder's libaec dependency):
- *Arch/Manjaro:* `webkit2gtk-4.1 base-devel openssl librsvg libaec cmake clang pkgconf`
- *Debian/Ubuntu:* `libwebkit2gtk-4.1-dev build-essential libssl-dev librsvg2-dev libaec-dev cmake clang pkg-config`
- *macOS:* `xcode-select --install` then `brew install libaec cmake`
- *Windows:* prefer **WSL (Ubuntu)** and follow the Debian steps.

**Scaffold** (choose: Vanilla / JavaScript / npm):
```bash
npm create tauri-app@latest        # name it grib-map
cd grib-map && npm install
npm run tauri dev                  # first build is slow (3–8 min); a window opens
```

**Know your files:** frontend = `src/main.js`, `index.html`, `src/styles.css` ·
backend = `src-tauri/src/lib.rs` (**not** `main.rs`), `src-tauri/Cargo.toml`,
`src-tauri/capabilities/default.json`.

> ✅ **Checkpoint 1:** the default Tauri window opens.

---

## Part 2 — Get an AROME GRIB file (15 min)

**Way A (use this in class):** copy the `.grib2` file provided by your instructor; note its full path.

**Way B (bonus):** download an AROME **SP1** package yourself — either from the official portal
<https://portail-api.meteofrance.fr/> (free account + token) or the **no-login AWS mirror**
documented at <https://mf-models-on-aws.org/> (model *arome-france*). *SP1* = surface package, it
contains 2 m temperature.

> ✅ **Checkpoint 2:** you have a `.grib2` file and know its path.

---

## Part 3 — Decode the temperature in Rust (60 min)

A GRIB2 file is a list of **fields**, each tagged with metadata. **2 m air temperature** is the field
where `discipline = 0`, `category = 0`, `parameter = 0`, at surface height `2`. Values are in **Kelvin**.

**3.1 — Add the library.** In `src-tauri/Cargo.toml` under `[dependencies]`:
```toml
grib = { version = "0.15.6", default-features = false, features = ["ccsds-unpack-with-libaec"] }
```
(`serde`, `serde_json` are already there.)

**3.2 — Explore the file.** *Your task:* write a Tauri command `describe_grib(path) -> Vec<String>`
that opens the file, iterates its fields, and returns one line per field showing its
`discipline / category / parameter / level / grid size`. Run it (see *Calling Rust from the console*
in the Cheat-sheet) and **find the line that matches the 2 m temperature rule above** — note its grid size.

**3.3 — Extract the points.** *Your task:* write a command
```rust
#[tauri::command]
fn load_temperature(path: String) -> Result<Vec<TempPoint>, String> { /* ... */ }
```
where `TempPoint { lat: f64, lon: f64, value: f64 }` derives `serde::Serialize`. It must:
1. find the **first** 2 m temperature field,
2. get its coordinates **and** decode its values (see Cheat-sheet for the exact calls + ordering gotcha),
3. keep only points inside the **Montpellier box** `lat ∈ [43.0, 44.2]`, `lon ∈ [3.0, 4.8]`,
4. convert **Kelvin → °C** (`k - 273.15`) and return the list.

Register both commands in `generate_handler![...]`.

> ✅ **Checkpoint 3:** the project compiles and `load_temperature` exists.
> *Build fails on `libaec-sys`?* re-check the system libs above. *Decode error at runtime?* your file may use
> a different packing — try the bundled *simple-packing* sample (`grib = { …, default-features = false }`), or
> if it's a JPEG2000 file (e.g. from the AWS mirror) add `"jpeg2000-unpack-with-openjpeg"` and install `openjpeg2`.

---

## Part 4 — Show it on a Leaflet map (70 min)

**4.1 — Enable the file dialog.**
```bash
npm run tauri add dialog
```
Then register it in `lib.rs` (`.plugin(tauri_plugin_dialog::init())`) and add `"dialog:default"` to the
`permissions` array in `src-tauri/capabilities/default.json`.

**4.2 — Page skeleton.** In `index.html`, inside `<head>` load Leaflet's CSS from the CDN and after the
body load its JS, then your module:
```html
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<!-- body: a #toolbar with a <button id="load-btn"> and a <span id="status">, plus a <div id="map"> -->
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script type="module" src="/src/main.js"></script>
```
In `styles.css` make `#map` fill the screen (`flex:1`, `html,body{height:100%}`).

**4.3 — Logic (`src/main.js`).** *Your task*, using the imports/calls in the Cheat-sheet:
1. Create the map centered on `[43.61, 3.88]`, zoom ~9, and add an OpenStreetMap tile layer.
   *(Use `L.map("map", { preferCanvas: true })` — it stays smooth with thousands of shapes.)*
2. On button click: open the file dialog → get the path → `invoke("load_temperature", { path })`.
3. For each returned point, draw a small **`L.rectangle`** (~0.025° wide, so `±0.0125°` around the point),
   filled with a color from a temperature → color function (e.g. blue at -5 °C → red at 35 °C using
   `hsl(hue,85%,50%)` with `hue = 240 - 240*ratio`). Add a tooltip with the value.
4. Update `#status` with how many points were drawn.

> ✅ **Checkpoint 4:** clicking the button fills the map with colored temperature cells over Montpellier.
> *Nothing shows?* check the dev-tools Console, confirm your file has 2 m temperature, and that your box
> overlaps the data.

---

## Part 5 — Polish & bonus (35 min)

Pick what interests you:
- **Polish:** auto-fit the map to the data (`map.fitBounds`), show min/max/avg temperature, opacity slider, a color legend.
- **Forecast hour:** a package holds the field for many hours — let the user choose one (`prod_def().forecast_time()`).
- **Wind (harder):** decode the **U** and **V** wind fields (`category 2`, `parameter 2` and `3`, level 10 m) and draw arrows; speed = `√(u²+v²)`.
- **Live data:** a button that downloads a fresh AROME SP1 from the AWS mirror in Rust, then reuses `load_temperature`.
- **Ship it:** `npm run tauri build` → a real installer in `src-tauri/target/release/`.

---

## Cheat-sheet (use only when stuck)

**GRIB (Rust) — needs `use grib::LatLons;` and `use std::io::BufReader;`**
```rust
let reader = BufReader::new(std::fs::File::open(&path).map_err(|e| e.to_string())?);
let grib2  = grib::from_reader(reader).map_err(|e| e.to_string())?;
for (index, submessage) in grib2.iter() {
    let d   = submessage.indicator().discipline;            // u8
    let cat = submessage.prod_def().parameter_category();   // Option<u8>
    let num = submessage.prod_def().parameter_number();     // Option<u8>
    let lvl = submessage.prod_def().fixed_surfaces().map(|(s, _)| s.value()); // Option<f32>
    let (ni, nj) = submessage.grid_shape().unwrap();        // grid dimensions

    // Coordinates FIRST, then move the submessage into the decoder:
    let latlons = submessage.latlons().map_err(|e| e.to_string())?;        // iterator of (lat, lon) f32, degrees
    let decoder = grib::Grib2SubmessageDecoder::from(submessage).map_err(|e| e.to_string())?;
    let values  = decoder.dispatch().map_err(|e| e.to_string())?;          // iterator of f32 (Kelvin)
    for ((lat, lon), kelvin) in latlons.zip(values) { /* ... */ }
}
```
*Ordering gotcha:* call `.latlons()` **before** `Grib2SubmessageDecoder::from(submessage)` (the decoder consumes the submessage).

**Tauri command + register**
```rust
#[tauri::command]
fn my_cmd(path: String) -> Result<Vec<TempPoint>, String> { /* ... */ }
// in run(): .plugin(tauri_plugin_dialog::init())
//           .invoke_handler(tauri::generate_handler![describe_grib, load_temperature])
```

**Frontend (`src/main.js`)**
```js
import { open }   from "@tauri-apps/plugin-dialog";
import { invoke } from "@tauri-apps/api/core";

const path = await open({ multiple:false, directory:false,
  filters:[{ name:"GRIB2", extensions:["grib2","grb2","grib"] }] });
const points = await invoke("load_temperature", { path }); // key "path" = Rust param name

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
  { attribution:"© OpenStreetMap contributors" }).addTo(map);
L.rectangle([[lat-0.0125, lon-0.0125],[lat+0.0125, lon+0.0125]],
  { stroke:false, fillColor: color, fillOpacity:0.6 }).addTo(layer);
```

**Calling Rust from the console** (to test `describe_grib`): in the Tauri window, open dev-tools
(`Ctrl+Shift+I`) and run:
```js
const { invoke } = window.__TAURI__.core;
console.log((await invoke("describe_grib", { path:"/full/path/file.grib2" })).join("\n"));
```

**Reminders:** edit `lib.rs` (not `main.rs`) · `invoke` arg key matches the Rust parameter name ·
temperature is in Kelvin (− 273.15 for °C) · 2 m temp = `discipline 0 / category 0 / parameter 0 / level 2`.
