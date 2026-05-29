#!/usr/bin/env bash
# Download the +00H SP1 GRIB2 file from the latest AROME run on
# Météo-France open data. This is the "initial analysis" snapshot —
# the model's best view of the atmosphere at the moment the run was
# started. One file, ~16 MB.
#
# Discovery is fully dynamic. Météo-France retains 14 days of data.
# See: https://github.com/nudibranches-tech/tauri-tp/issues/1

set -euo pipefail

RESOLUTION="001"   # 0.01° (~1.3 km). Use "0025" for 0.025° (~2.5 km).
PACKAGE="SP1"
TERM="00H"
OUT_DIR="$(dirname "$0")"
INDEX_URL="https://files.data.gouv.fr/meteofrance-pnt/pnt/"
BASE="https://files.data.gouv.fr/meteofrance-pnt/pnt"

echo "Discovering latest run from ${INDEX_URL}…"

LATEST_RUN="$(
  curl --fail --silent --location "${INDEX_URL}" \
    | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}%3A00%3A00Z' \
    | sed 's/%3A/:/g' \
    | sort -ru \
    | head -1
)"

if [[ -z "${LATEST_RUN}" ]]; then
  echo "Failed to discover any runs at ${INDEX_URL}" >&2
  exit 1
fi

DATE="${LATEST_RUN:0:10}"
HOUR="${LATEST_RUN:11:2}"
DIR_URL="${BASE}/${LATEST_RUN}/arome/${RESOLUTION}/${PACKAGE}/"
FILENAME="arome__${RESOLUTION}__${PACKAGE}__${TERM}__${LATEST_RUN}.grib2"
URL="${DIR_URL}${FILENAME}"
OUT_FILE="${OUT_DIR}/arome_sp1_${DATE}_${HOUR}Z_${TERM}.grib2"

echo "Run ${LATEST_RUN} — term +${TERM} (valid at ${LATEST_RUN})"

if [[ -f "${OUT_FILE}" ]]; then
  echo "✓ ${OUT_FILE} already exists, skipping."
  exit 0
fi

echo "Downloading ${URL}…"
curl --fail --location --progress-bar -o "${OUT_FILE}" "${URL}"
echo "✓ Saved to ${OUT_FILE} ($(du -h "${OUT_FILE}" | cut -f1))"
