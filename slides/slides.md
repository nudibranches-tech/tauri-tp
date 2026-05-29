---
theme: frankfurt
title: Desktop Weather Map from Open Data
author: Lab — Tauri · Rust · Leaflet
date: 2026/05/29
infoLine: true
info: |
  A 4-hour lab: build a desktop app that opens a Météo-France AROME GRIB2 file,
  reads the 2 m air temperature in Rust, and draws it on an interactive map of
  Montpellier. Slides built with Slidev + the Frankfurt theme.
class: text-center
mdc: true
---

# Desktop Weather Map from Open Data

### Tauri · Rust · Leaflet — reading AROME weather data

<br>

A 4-hour hands-on lab — open a real **AROME GRIB2** file, decode the
**2 m air temperature** in Rust, and paint it on a map of **Montpellier**.

<br>

<div class="text-sm opacity-70">
Use <kbd>→</kbd> / <kbd>Space</kbd> to advance · press <kbd>o</kbd> for the slide overview
</div>

---
section: Overview
---

# What you will build

<div class="grid grid-cols-2 gap-8 mt-4">

<div>

A **native desktop window** that:

1. Opens a `.grib2` weather file from disk
2. Decodes the 2 m temperature field in **Rust**
3. Returns `[{ lat, lon, value }]` to the UI
4. Draws one coloured cell per grid point on a **Leaflet** map

</div>

<div>

```text
JavaScript frontend          Rust backend
  - file dialog    invoke()    - read the file
  - Leaflet map   ─────────►   - decode GRIB2
  - draw cells    ◄─────────   - return points
```

The whole app is one window: a **web UI** talking to a **Rust** program
through a single `invoke()` bridge.

</div>

</div>

---

# Why open weather data?

<Item title="Open data">
Data anyone can freely access, reuse and share — online, <b>machine-readable</b>,
openly licensed, usually free. Weather is a flagship example: public agencies
(Météo-France, NOAA, ECMWF, DWD…) publish forecasts openly.
</Item>

<div class="mt-4" />

**Local uses around Montpellier** — vineyard frost & irrigation · urban heat
islands · sailing/wind on the Golfe du Lion · solar production.

<div class="text-sm opacity-70 mt-6">
A 2.5 km forecast, free for anyone to build on. What would <i>you</i> improve with it?
</div>

---
section: Concepts
---

# AROME — a high-resolution weather model

<Item title="AROME (Météo-France)">
A numerical model that divides the atmosphere into a 3-D grid and solves physics
equations to forecast temperature, wind, humidity… for the coming hours.
</Item>

<div class="grid grid-cols-2 gap-6 mt-4 text-sm">

<div>

- Horizontal grid ≈ **0.025° (~2.5 km)**
- Covers France, incl. **Montpellier** (43.61° N, 3.88° E)
- New runs at **00 / 06 / 12 / 18 UTC**

</div>

<div>

- Output shipped as **GRIB2** files
- We only need the **2 m air temperature** field
- Values are in **Kelvin** (− 273.15 → °C)

</div>

</div>

---

# What is a GRIB file?

<Item title="GRIB — GRIdded Binary">
The WMO international standard for gridded weather data: compact, binary, and
<b>self-describing</b> — each field carries the metadata needed to read it. We use
<b>GRIB2</b>.
</Item>

Mental model: **a stack of labelled "spreadsheets."** Each sheet is one variable,
at one level, for one forecast time.

```text
GRIB2 file
 ├── message ─► one 2-D field
 │     ├── Grid Definition   : where  (corner lat/lon + step)
 │     ├── Product Definition: what   (parameter, level, time)
 │     ├── Data Representation: how   (packing method)
 │     └── Data              : the packed numbers
 └── …                                 end marker "7777"
```

---

# Three ideas that matter

<div class="space-y-3 mt-2">

<Item title="1 — The 'what' is numbers, not text">
2 m temperature = <code>discipline 0</code> / <code>category 0</code> /
<code>parameter 0</code>, at fixed surface <b>height 2 m</b>. Looked up in WMO code tables.
</Item>

<Item title="2 — The 'where' is a grid description">
The file stores corner coordinates + step. Every point's lat/lon is <i>derived</i> —
the library hands it to us via <code>latlons()</code>.
</Item>

<Item title="3 — The data is packed (compressed)">
Scaled integers, then compressed. Real AROME files use <b>JPEG2000</b> (openjpeg) or
<b>CCSDS/AEC</b> (libaec) — a decoder reconstructs the real numbers for us.
</Item>

</div>

---
section: Architecture
---

# How the app is built

<div class="grid grid-cols-2 gap-8 mt-2">

<div>

<Item title="Tauri">
A native window showing a <b>web UI</b> (HTML/CSS/JS) backed by a <b>Rust</b> program.
Heavy work (decoding GRIB) runs in Rust; the UI runs in the webview.
</Item>

<div class="mt-4" />

<Item title="The bridge">
Frontend calls Rust with<br><code>invoke("name", { args })</code><br>and Rust returns JSON.
That's the only "magic."
</Item>

</div>

<div>

<Item title="Leaflet">
A slippy map of OpenStreetMap tiles. You place things by <b>(lat, lon)</b> — exactly
what our decoder produces. We draw one small coloured rectangle per grid cell.
</Item>

<div class="mt-4" />

```js
const points =
  await invoke("load_temperature", { path });
// → [{ lat, lon, value }, …]
```

</div>

</div>

---
section: The Lab
---

# Five parts, ~3.5 hours hands-on

| Time | Part | Goal | Tag |
|------|------|------|-----|
| 0:30–1:00 | **1** | Install & scaffold the app | `part1` |
| 1:00–1:15 | **2** | Get an AROME GRIB file | `part2` |
| 1:15–2:15 | **3** | Decode the temperature in Rust | `part3` |
| 2:15–3:25 | **4** | Show it on a Leaflet map | `part4` |
| 3:25–4:00 | **5** | Polish + bonus | `part5` |

<div class="mt-6 p-3 rounded bg-blue-500 bg-opacity-10 text-sm">
💡 <b>Each part is a git tag.</b> Behind, or a step won't work? Check out the tag for
the part you are on and keep going — details on the next slides and at the end.
</div>

---

# Part 1 — Install & scaffold

- Toolchains: **Rust** (rustup) + **Node.js** (LTS)
- System libs: `webkit2gtk-4.1`, `openjpeg2`, `libaec`, `librsvg`, `cmake`, `clang`, `pkgconf`

```bash
npm create tauri-app@latest      # name it grib-map (Vanilla / JS / npm)
cd grib-map && npm install
npm run tauri dev                # first build is slow; a window opens
```

**Know your files:** frontend `index.html`, `src/main.js`, `src/styles.css` ·
backend `src-tauri/src/lib.rs`, `src-tauri/Cargo.toml`, `capabilities/default.json`.

<div class="mt-4 text-sm opacity-90">
✅ <b>Checkpoint 1:</b> the default Tauri window opens.
</div>

> 💡 **Stuck or just joined?** `git checkout part1` → a working scaffold to start from.

---

# Part 2 — Get an AROME GRIB file

You need a `.grib2` file containing **2 m temperature**:

- **In class:** copy the file from the instructor; note its full path.
- **Download (no login):** the latest real AROME `+00H SP1` file (~16 MB) from the
  Météo-France open-data mirror — see `data/fetch_arome_sp1.sh`.
- **Offline:** a tiny synthetic sample is provided for testing.

<div class="mt-4 text-sm opacity-90">
✅ <b>Checkpoint 2:</b> you have a <code>.grib2</code> file and know its path.
</div>

> 💡 **No file yet?** `git checkout part2` → the `data/` helpers and a ready sample.

---

# Part 3 — Decode the temperature in Rust

Find the field where `discipline 0 / category 0 / parameter 0`, surface `2 m`.

```rust
let latlons = submessage.latlons()?;                     // coords FIRST
let decoder = grib::Grib2SubmessageDecoder::from(submessage)?;
let values  = decoder.dispatch()?;                       // Kelvin
for ((lat, lon), kelvin) in latlons.zip(values) { /* … */ }
```

1. find the **first** 2 m temperature field
2. get coordinates **and** decode values *(order matters!)*
3. keep the **Montpellier box** `lat ∈ [43, 44.2]`, `lon ∈ [3, 4.8]`
4. convert **K → °C** and return `Vec<TempPoint>`

<div class="mt-3 text-sm opacity-90">
✅ <b>Checkpoint 3:</b> the project compiles and <code>load_temperature</code> exists.
</div>

> 💡 **Decode errors / falling behind?** `git checkout part3` → working Rust commands + tests.

---

# Part 4 — Show it on a Leaflet map

```js
const map = L.map("map", { preferCanvas: true }).setView([43.61, 3.88], 9);
const path = await open({ filters: [{ name: "GRIB2", extensions: ["grib2"] }] });
const points = await invoke("load_temperature", { path });

for (const { lat, lon, value } of points)
  L.rectangle([[lat-0.0125, lon-0.0125], [lat+0.0125, lon+0.0125]],
    { stroke: false, fillColor: colorForTemp(value), fillOpacity: 0.6 }).addTo(map);
```

Enable the dialog plugin (`npm run tauri add dialog`), colour blue (−5 °C) → red (35 °C).

<div class="mt-3 text-sm opacity-90">
✅ <b>Checkpoint 4:</b> clicking the button fills the map with coloured cells.
</div>

> 💡 **Map blank or behind?** `git checkout part4` → the full working frontend.

---

# Part 5 — Polish & bonus

Pick what interests you:

- **Polish:** auto-fit the map (`map.fitBounds`), min/max/avg, opacity slider, colour legend
- **Forecast hour:** let the user choose a term (`prod_def().forecast_time()`)
- **Wind (harder):** decode U/V (category 2, params 2 & 3, level 10 m), draw arrows
- **Live data:** download a fresh AROME file from Rust
- **Ship it:** `npm run tauri build` → a real installer

<div class="mt-3 text-sm opacity-90">
✅ <b>Checkpoint 5:</b> a polished map with stats, legend and an opacity control.
</div>

> 💡 **Want the finished reference?** `git checkout part5` → everything, done.

---
section: Checkpoints
---

# The checkpoint tags — never get stuck

Every part is committed as a **git tag**. If a step won't work or you joined late,
jump straight to a known-good snapshot and keep up with the class:

```bash
git checkout part3      # working snapshot at the end of Part 3
# … follow along, then when ready:
git checkout main       # back to the course materials
```

| Tag | You get a working… |
|-----|--------------------|
| `part1` | scaffolded Tauri app |
| `part2` | GRIB file + `data/` helpers |
| `part3` | Rust decoder (`describe_grib`, `load_temperature`) |
| `part4` | Leaflet map frontend |
| `part5` | finished app + polish |

<div class="mt-3 text-sm opacity-80">
The tags are <b>incremental</b>: each contains every earlier part. <code>main</code> holds this subject + slides.
</div>

---

# Cheat-sheet — the calls you'll need

<div class="grid grid-cols-2 gap-6 text-sm">

<div>

**Rust** — `use grib::LatLons;`

```rust
let r = BufReader::new(File::open(&path)?);
let g = grib::from_reader(r)?;
for (i, m) in g.iter() {
  let d   = m.indicator().discipline;
  let cat = m.prod_def().parameter_category();
  let num = m.prod_def().parameter_number();
}
```

</div>

<div>

**Frontend** (`src/main.js`)

```js
import { open }   from
  "@tauri-apps/plugin-dialog";
import { invoke } from
  "@tauri-apps/api/core";
```

Reminders: edit `lib.rs` (not `main.rs`) · the
`invoke` arg key matches the Rust parameter name ·
K − 273.15 → °C.

</div>

</div>

---
layout: center
class: text-center
---

# Let's build it 🌡️🗺️

Open data → Rust → a map of Montpellier.

<br>

<div class="text-sm opacity-80">
Stuck at any point? <code>git checkout part&lt;N&gt;</code> and keep going.
</div>
