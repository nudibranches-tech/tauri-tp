#!/usr/bin/env python3
"""Generate a tiny, valid GRIB2 file mimicking an AROME SP1 *2 m temperature* field.

This is NOT a real Météo-France forecast — it is a small synthetic field over the
Montpellier box so the lab pipeline (Part 3 decode + Part 4 map) can be run and
tested offline without downloading a multi-hundred-MB AROME package.

Encoding choices kept deliberately simple so the `grib` Rust crate decodes it with
its default features (no JPEG2000 needed):
  * Grid Definition Template 3.0  — regular latitude/longitude grid
  * Product Definition Template 4.0 — analysis/forecast at a horizontal level
      discipline 0 (meteorology) / category 0 (temperature) / number 0 (temperature)
      first fixed surface 103 (height above ground) = 2 m   -> the "2 m temperature" rule
  * Data Representation Template 5.0 — grid-point data, simple packing

Run:  python3 make_sample_grib.py
Out:  arome_sp1_montpellier_sample.grib2
"""
import math
import struct
from pathlib import Path

# --- Grid: 0.025deg regular lat/lon grid covering the Montpellier box -----------
LA1, LA2 = 44.200, 43.000           # north -> south (scanning -j)
LO1, LO2 = 3.000, 4.800             # west  -> east  (scanning +i)
STEP = 0.025
NI = round((LO2 - LO1) / STEP) + 1  # points along a parallel (W->E)
NJ = round((LA1 - LA2) / STEP) + 1  # points along a meridian (N->S)
NPOINTS = NI * NJ
MICRO = 1_000_000                   # values are stored in units of 1e-6 degree


def temperature_kelvin(lat, lon):
    """A smooth, gentle gradient so the rendered map shows structure (~13-17 C)."""
    return 288.15 + (lat - 43.6) * 2.0 + (lon - 3.88) * 1.0


def u32(v):
    return struct.pack(">I", v & 0xFFFFFFFF)


def s32(v):
    # All our lat/lon are positive, so plain big-endian unsigned is fine.
    return struct.pack(">I", v)


def u16(v):
    return struct.pack(">H", v & 0xFFFF)


def u8(v):
    return struct.pack(">B", v & 0xFF)


def section(num, body):
    """Prefix a section body with its 4-byte length and 1-byte section number."""
    length = 4 + 1 + len(body)
    return u32(length) + u8(num) + body


# --- Section 1: Identification ---------------------------------------------------
sec1 = section(1,
    u16(85)    # originating centre (85 = Toulouse / Meteo-France)
    + u16(0)   # sub-centre
    + u8(2)    # GRIB master tables version
    + u8(0)    # local tables version
    + u8(1)    # significance of reference time (1 = start of forecast)
    + u16(2026) + u8(5) + u8(29)  # year, month, day
    + u8(0) + u8(0) + u8(0)       # hour, minute, second
    + u8(0)    # production status (0 = operational)
    + u8(1)    # type of processed data (1 = forecast)
)

# --- Section 3: Grid Definition (Template 3.0, regular lat/lon) ------------------
grid_tmpl = (
    u8(6)                       # shape of the earth (6 = sphere, r=6371229 m)
    + u8(0xFF) + u32(0xFFFFFFFF)  # radius of spherical earth (missing -> predefined)
    + u8(0xFF) + u32(0xFFFFFFFF)  # major axis (missing)
    + u8(0xFF) + u32(0xFFFFFFFF)  # minor axis (missing)
    + u32(NI) + u32(NJ)
    + u32(0)                    # basic angle of the initial production domain
    + u32(0xFFFFFFFF)           # subdivisions of basic angle (missing -> unit 1e-6)
    + s32(round(LA1 * MICRO)) + s32(round(LO1 * MICRO))
    + u8(0x30)                  # res/component flags: i & j increments given
    + s32(round(LA2 * MICRO)) + s32(round(LO2 * MICRO))
    + u32(round(STEP * MICRO)) + u32(round(STEP * MICRO))  # Di, Dj
    + u8(0x00)                  # scanning mode: +i, -j, row-major (first row = north)
)
sec3 = section(3,
    u8(0)            # source of grid definition (0 = template below)
    + u32(NPOINTS)   # number of data points
    + u8(0)          # number of octets for optional list
    + u8(0)          # interpretation of optional list
    + u16(0)         # grid definition template number (0 = lat/lon)
    + grid_tmpl
)

# --- Section 4: Product Definition (Template 4.0) -------------------------------
prod_tmpl = (
    u8(0)            # parameter category (0 = temperature)
    + u8(0)          # parameter number   (0 = temperature)
    + u8(2)          # type of generating process (2 = forecast)
    + u8(0xFF)       # background generating process id
    + u8(0xFF)       # generating process identifier
    + u16(0)         # hours after reference time data cutoff
    + u8(0)          # minutes after reference time data cutoff
    + u8(1)          # indicator of unit of time range (1 = hour)
    + u32(3)         # forecast time (+3 h)
    + u8(103)        # type of first fixed surface (103 = height above ground)
    + u8(0)          # scale factor of first fixed surface
    + u32(2)         # scaled value of first fixed surface (= 2 m)
    + u8(0xFF)       # type of second fixed surface (missing)
    + u8(0xFF)       # scale factor of second fixed surface (missing)
    + u32(0xFFFFFFFF)  # scaled value of second fixed surface (missing)
)
sec4 = section(4,
    u16(0)           # number of coordinate values after template
    + u16(0)         # product definition template number (0)
    + prod_tmpl
)

# --- Build the data field, then Section 5 + Section 7 (simple packing) ----------
values = []
for j in range(NJ):                 # north -> south
    lat = LA1 - j * STEP
    for i in range(NI):             # west -> east
        lon = LO1 + i * STEP
        values.append(temperature_kelvin(lat, lon))

D = 2                               # decimal scale factor (centi-kelvin precision)
E = 0                               # binary scale factor
scaled = [round(v * (10 ** D)) for v in values]
ref = min(scaled)                   # reference value R (stored as IEEE float)
X = [s - ref for s in scaled]       # packed integers: Y = (R + X*2^E) / 10^D
maxX = max(X)
nbits = max(1, maxX.bit_length())

# pack the X values as an nbits-per-value big-endian bit stream
acc = 0
acc_bits = 0
packed = bytearray()
for x in X:
    acc = (acc << nbits) | x
    acc_bits += nbits
    while acc_bits >= 8:
        acc_bits -= 8
        packed.append((acc >> acc_bits) & 0xFF)
if acc_bits > 0:
    packed.append((acc << (8 - acc_bits)) & 0xFF)

sec5 = section(5,
    u32(NPOINTS)                 # number of data points where packed
    + u16(0)                     # data representation template number (0 = simple)
    + struct.pack(">f", float(ref))  # reference value R
    + u16(E)                     # binary scale factor
    + u16(D)                     # decimal scale factor
    + u8(nbits)                  # number of bits per packed value
    + u8(0)                      # type of original field values (0 = float)
)

# --- Section 6: Bit-map (none) --------------------------------------------------
sec6 = section(6, u8(255))       # 255 = no bit-map applies

# --- Section 7: Data ------------------------------------------------------------
sec7 = section(7, bytes(packed))

# --- Section 8: End -------------------------------------------------------------
sec8 = b"7777"

# --- Section 0: Indicator (needs the total length) ------------------------------
body = sec1 + sec3 + sec4 + sec5 + sec6 + sec7 + sec8
total_len = 16 + len(body)
sec0 = b"GRIB" + b"\x00\x00" + u8(0) + u8(2) + struct.pack(">Q", total_len)

out = Path(__file__).with_name("arome_sp1_montpellier_sample.grib2")
out.write_bytes(sec0 + body)
print(f"wrote {out.name}: {total_len} bytes, grid {NI}x{NJ} = {NPOINTS} points, "
      f"{nbits} bits/value, T range {min(values)-273.15:.1f}..{max(values)-273.15:.1f} C")
