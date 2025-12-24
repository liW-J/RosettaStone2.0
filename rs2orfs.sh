#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: rs2orfs.sh BENCH_JSON LEFDEF_JSON [RESULTS_DIR] [DESIGN_NICKNAME]
  BENCH_JSON      Path to benchGen config file (used for bench_gen_one)
  LEFDEF_JSON     Path to lefdef2odb config file (used for lefdef2odb_one)
  RESULTS_DIR     Target directory for the output .odb
                  - If omitted: prefer RESULTS_DIR from flow/designs/$PLATFORM/$DESIGN_NICKNAME/config.mk
                  - If RESULTS_DIR is not defined in config.mk: default = $FLOW_HOME/results/$PLATFORM/$DESIGN_NICKNAME/base
  DESIGN_NICKNAME Optional, subdirectory name under flow/designs; default is 'design' from BENCH_JSON
You can also pass values via environment variables: BENCH_JSON / LEFDEF_JSON / RESULTS_DIR / DESIGN_NICKNAME.
EOF
  exit 1
}

BENCH_JSON="${1:-${BENCH_JSON:-}}"
LEFDEF_JSON="${2:-${LEFDEF_JSON:-}}"
RESULTS_DIR_INPUT="${3:-${RESULTS_DIR:-}}"
DESIGN_NICKNAME="${4:-${DESIGN_NICKNAME:-}}"

if [[ -z "${BENCH_JSON}" || -z "${LEFDEF_JSON}" ]]; then
  usage
fi

to_abs() {
  local p="$1"
  if [[ "$p" == /* ]]; then
    printf '%s\n' "$p"
    return 0
  fi
  local dir base
  dir="$(cd "$(dirname "$p")" && pwd)"
  base="$(basename "$p")"
  printf '%s/%s\n' "$dir" "$base"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

BENCH_JSON="$(to_abs "${BENCH_JSON}")"
LEFDEF_JSON="$(to_abs "${LEFDEF_JSON}")"

read -r DESIGN_NAME BENCHMARKS PLATFORM_FROM_BENCH <<<"$(python3 - "${BENCH_JSON}" <<'PY'
import json, sys
cfg_path = sys.argv[1]
with open(cfg_path) as f:
    cfg = json.load(f)
design = cfg.get("design")
benchmarks = cfg.get("benchmarks")
platform = cfg.get("platform") or cfg.get("pdk", {}).get("name")
missing = [k for k, v in {"design": design, "benchmarks": benchmarks, "platform": platform}.items() if not v]
if missing:
    sys.exit(f"Missing required config fields: {', '.join(missing)}")
print(f"{design} {benchmarks} {platform}")
PY
)"

read -r CONTEST OUTPUT_DIR PLATFORM_FROM_LEFDEF CFG_DESIGN <<<"$(python3 - "${LEFDEF_JSON}" <<'PY'
import json, sys
cfg_path = sys.argv[1]
with open(cfg_path) as f:
    cfg = json.load(f)
contest = cfg.get("contest") or "ispd2005"
output_dir = cfg.get("output_dir") or "odbFiles"
platform = cfg.get("platform") or ""
designs = cfg.get("designs") or []
cfg_design = designs[0] if designs else ""
print(f"{contest} {output_dir} {platform} {cfg_design}")
PY
)"

# Prefer platform/design from bench config
PLATFORM="${PLATFORM_FROM_LEFDEF:-${PLATFORM_FROM_BENCH}}"
DESIGN_USE="${DESIGN_NAME}"
DESIGN_NICKNAME="${DESIGN_NICKNAME:-${DESIGN_USE}}"

FLOW_HOME="${FLOW_HOME:-$(cd "${SCRIPT_DIR}/../../flow" && pwd)}"

# Determine RESULTS_DIR:
# 1) If the user explicitly provides the third argument / env var RESULTS_DIR, use it
# 2) Otherwise, try to read RESULTS_DIR from flow/designs/$PLATFORM/$DESIGN_NICKNAME/config.mk
# 3) If still empty, fall back to $FLOW_HOME/results/$PLATFORM/$DESIGN_NICKNAME/base
if [[ -n "${RESULTS_DIR_INPUT}" ]]; then
  RESULTS_DIR="${RESULTS_DIR_INPUT}"
else
  DESIGN_CFG="${FLOW_HOME}/designs/${PLATFORM}/${DESIGN_NICKNAME}/config.mk"
  RESULTS_DIR_FROM_CFG=""
  if [[ -f "${DESIGN_CFG}" ]]; then
    RESULTS_DIR_FROM_CFG="$(bash -lc "source \"${DESIGN_CFG}\" >/dev/null 2>&1; printf '%s' \"\$RESULTS_DIR\"")"
  fi
  if [[ -n "${RESULTS_DIR_FROM_CFG}" ]]; then
    RESULTS_DIR="${RESULTS_DIR_FROM_CFG}"
  else
    RESULTS_DIR="${FLOW_HOME}/results/${PLATFORM}/${DESIGN_NICKNAME}/base"
  fi
fi

RESULTS_DIR="$(to_abs "${RESULTS_DIR}")"
mkdir -p "${RESULTS_DIR}"

OUTPUT_DIR_ABS="${OUTPUT_DIR}"
if [[ "${OUTPUT_DIR_ABS}" != /* ]]; then
  OUTPUT_DIR_ABS="${SCRIPT_DIR}/${OUTPUT_DIR_ABS}"
fi

# echo "[INFO] Running bench_gen_one..."
# make bench_gen_one JSON="${BENCH_JSON}"

# echo "[INFO] Running lefdef2odb_one..."
# make lefdef2odb_one JSON="${LEFDEF_JSON}"

ODB_SRC="${OUTPUT_DIR_ABS}/${PLATFORM}_${CONTEST}_${DESIGN_USE}.odb"
if [[ ! -f "${ODB_SRC}" ]]; then
  echo "[ERROR] Generated ODB not found: ${ODB_SRC}"
  exit 1
fi
mkdir -p "${RESULTS_DIR}"
cp -f "${ODB_SRC}" "${RESULTS_DIR}/2_1_floorplan.odb"
echo "[INFO] Copied ODB to ${RESULTS_DIR}/2_1_floorplan.odb"

BENCH_DIR="${SCRIPT_DIR}/bench/${PLATFORM}/${BENCHMARKS}_${DESIGN_USE}"
MACRO_LEF="${BENCH_DIR}/${DESIGN_USE}_macro.lef"
MACRO_LED="${BENCH_DIR}/${DESIGN_USE}_macro.led"
MACRO_SRC=""
if [[ -f "${MACRO_LEF}" ]]; then
  MACRO_SRC="${MACRO_LEF}"
elif [[ -f "${MACRO_LED}" ]]; then
  MACRO_SRC="${MACRO_LED}"
else
  echo "[ERROR] Macro LEF/LED file not found: ${MACRO_LEF} or ${MACRO_LED}"
  exit 1
fi

DESIGN_DST="${FLOW_HOME}/designs/${PLATFORM}/${DESIGN_NICKNAME}"
mkdir -p "${DESIGN_DST}"
cp -f "${MACRO_SRC}" "${DESIGN_DST}/"
echo "[INFO] Copied macro file to ${DESIGN_DST}/"

