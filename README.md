# grib-map — desktop AROME weather map

A reference implementation of the lab in
[`arome-tauri-weather-lab-student.md`](./arome-tauri-weather-lab-student.md):
a **Tauri + Rust + Leaflet** desktop app that opens a Météo-France **AROME**
GRIB2 file, decodes the **2 m air temperature** in Rust, and draws it as a
coloured grid over **Montpellier**.

```
JavaScript frontend            Rust backend
  - file dialog     invoke()     - read the file
  - Leaflet map   ───────────►   - decode GRIB2 (2 m temperature)
  - draw cells    ◄───────────   - return [{lat, lon, value}]
```

## Course checkpoints (git tags)

Each part of the lab is a working, tagged checkpoint:

| Tag     | Part | What works |
|---------|------|------------|
| `part1` | 1 | Tauri + Vite vanilla app scaffolds, frontend builds, backend compiles |
| `part2` | 2 | A `.grib2` file is available (`data/`, fetch script + synthetic sample) |
| `part3` | 3 | `describe_grib` + `load_temperature` decode 2 m temperature (unit-tested) |
| `part4` | 4 | Leaflet map fills with coloured temperature cells from a chosen file |
| `part5` | 5 | Polish: fit-to-data, min/max/avg, opacity slider, colour legend |

`git checkout part3` (etc.) to see the project at that stage.

## Prerequisites

Rust (rustup) + Node.js (LTS), plus the system libraries for the webview and the
GRIB decoders:

- **webview / build:** `webkit2gtk-4.1`, `base-devel`, `openssl`, `librsvg`, `cmake`, `clang`, `pkgconf`
- **GRIB decoding:** `libaec`

> Météo-France open-data AROME files (what `data/fetch_arome_sp1.sh` downloads)
> use **CCSDS/AEC** packing (data-representation template 5.42), decoded via
> `libaec` — so the `grib` crate is built with the `ccsds-unpack-with-libaec`
> feature. (The handout mentions JPEG2000/`openjpeg`; that path isn't needed for
> the open-data files this lab uses.)

On Arch/Manjaro: `pacman -S webkit2gtk-4.1 base-devel openssl librsvg libaec cmake clang pkgconf`

## Run

```bash
npm install
npm run tauri dev      # first build is slow; a window opens
```

Get a GRIB file first (see [`data/README.md`](./data/README.md)):

```bash
./data/fetch_arome_sp1.sh        # latest real AROME +00H SP1 (~16 MB), or
python3 data/make_sample_grib.py # tiny offline synthetic sample
```

Then click **Open a GRIB2 file…** and pick it.

## Test

```bash
cd src-tauri && cargo test       # decodes the synthetic sample + any real file in data/
```

## Build a release binary

```bash
npm run tauri build              # installer/binary in src-tauri/target/release/
```
