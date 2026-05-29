// AROME weather lab — Rust backend.
// Reads a GRIB2 file, finds the 2 m air-temperature field, and returns the
// grid points (lat, lon, °C) inside the Montpellier box to the frontend.
use grib::LatLons;
use std::io::BufReader;

/// One decoded grid cell sent to the frontend.
#[derive(serde::Serialize)]
struct TempPoint {
    lat: f64,
    lon: f64,
    value: f64, // degrees Celsius
}

/// Montpellier bounding box used to keep only the cells we draw.
const LAT_MIN: f64 = 43.0;
const LAT_MAX: f64 = 44.2;
const LON_MIN: f64 = 3.0;
const LON_MAX: f64 = 4.8;

/// `true` when a submessage is the "2 m air temperature" field:
/// discipline 0 (meteorology) / category 0 (temperature) / number 0 (temperature)
/// at a fixed surface of 2 (metres above ground).
fn is_2m_temperature(d: u8, cat: Option<u8>, num: Option<u8>, level: Option<f64>) -> bool {
    d == 0
        && cat == Some(0)
        && num == Some(0)
        && level.map_or(false, |v| (v - 2.0).abs() < 0.001)
}

/// Part 3.2 — list every field so we can spot the 2 m temperature one.
/// Returns one line per field: discipline / category / parameter / level / grid size.
#[tauri::command]
fn describe_grib(path: String) -> Result<Vec<String>, String> {
    let reader = BufReader::new(std::fs::File::open(&path).map_err(|e| e.to_string())?);
    let grib2 = grib::from_reader(reader).map_err(|e| e.to_string())?;

    let mut lines = Vec::new();
    for (index, submessage) in grib2.iter() {
        let d = submessage.indicator().discipline;
        let cat = submessage.prod_def().parameter_category();
        let num = submessage.prod_def().parameter_number();
        let lvl = submessage
            .prod_def()
            .fixed_surfaces()
            .map(|(s, _)| s.value());
        let shape = submessage
            .grid_shape()
            .map(|(ni, nj)| format!("{ni}x{nj}"))
            .unwrap_or_else(|_| "?x?".to_string());

        let marker = if is_2m_temperature(d, cat, num, lvl) {
            "  <- 2 m temperature"
        } else {
            ""
        };
        lines.push(format!(
            "#{index:?} discipline={d} category={cat:?} parameter={num:?} level={lvl:?} grid={shape}{marker}"
        ));
    }
    Ok(lines)
}

/// Part 3.3 — decode the first 2 m temperature field and return the points
/// inside the Montpellier box, converted from Kelvin to Celsius.
#[tauri::command]
fn load_temperature(path: String) -> Result<Vec<TempPoint>, String> {
    let reader = BufReader::new(std::fs::File::open(&path).map_err(|e| e.to_string())?);
    let grib2 = grib::from_reader(reader).map_err(|e| e.to_string())?;

    for (_index, submessage) in grib2.iter() {
        let d = submessage.indicator().discipline;
        let cat = submessage.prod_def().parameter_category();
        let num = submessage.prod_def().parameter_number();
        let lvl = submessage
            .prod_def()
            .fixed_surfaces()
            .map(|(s, _)| s.value());

        if !is_2m_temperature(d, cat, num, lvl) {
            continue;
        }

        // Coordinates FIRST, then move the submessage into the decoder.
        let latlons = submessage.latlons().map_err(|e| e.to_string())?;
        let decoder =
            grib::Grib2SubmessageDecoder::from(submessage).map_err(|e| e.to_string())?;
        let values = decoder.dispatch().map_err(|e| e.to_string())?;

        let mut points = Vec::new();
        for ((lat, lon), kelvin) in latlons.zip(values) {
            // Longitudes may be reported in 0..360; normalise to -180..180.
            let mut lon = lon as f64;
            if lon > 180.0 {
                lon -= 360.0;
            }
            let lat = lat as f64;
            if (LAT_MIN..=LAT_MAX).contains(&lat) && (LON_MIN..=LON_MAX).contains(&lon) {
                points.push(TempPoint {
                    lat,
                    lon,
                    value: kelvin as f64 - 273.15,
                });
            }
        }
        return Ok(points);
    }

    Err("no 2 m air-temperature field found in this GRIB file".to_string())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            greet,
            describe_grib,
            load_temperature
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn data_dir() -> std::path::PathBuf {
        std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../data")
    }

    fn sample() -> String {
        data_dir()
            .join("arome_sp1_montpellier_sample.grib2")
            .to_string_lossy()
            .into_owned()
    }

    #[test]
    fn describe_finds_the_2m_temperature_field() {
        let lines = describe_grib(sample()).expect("describe_grib should succeed");
        assert!(!lines.is_empty(), "expected at least one field");
        assert!(
            lines.iter().any(|l| l.contains("2 m temperature")),
            "no field matched the 2 m temperature rule:\n{}",
            lines.join("\n")
        );
    }

    #[test]
    fn load_returns_montpellier_points_in_celsius() {
        let points = load_temperature(sample()).expect("load_temperature should succeed");
        assert!(!points.is_empty(), "expected some points in the box");
        for p in &points {
            assert!(
                (LAT_MIN..=LAT_MAX).contains(&p.lat) && (LON_MIN..=LON_MAX).contains(&p.lon),
                "point ({}, {}) fell outside the Montpellier box",
                p.lat,
                p.lon
            );
            assert!(
                (-60.0..=60.0).contains(&p.value),
                "implausible temperature {} C (Kelvin conversion wrong?)",
                p.value
            );
        }
    }

    /// Runs only when a real AROME file has been downloaded (git-ignored).
    #[test]
    fn load_real_arome_file_if_present() {
        let Ok(entries) = std::fs::read_dir(data_dir()) else {
            return;
        };
        let real = entries.flatten().map(|e| e.path()).find(|p| {
            p.file_name()
                .and_then(|n| n.to_str())
                .map(|n| n.starts_with("arome_sp1_") && n.ends_with("H.grib2"))
                .unwrap_or(false)
        });
        let Some(path) = real else {
            eprintln!("(no real AROME file downloaded — skipping)");
            return;
        };
        let points = load_temperature(path.to_string_lossy().into_owned())
            .expect("decoding the real AROME file should succeed");
        assert!(!points.is_empty(), "real file produced no points in the box");
        eprintln!("real AROME file: {} points in the Montpellier box", points.len());
    }
}
