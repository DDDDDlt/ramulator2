#!/bin/bash

# 一键：基于 generation 的 per-model MAC 统计，并生成两套图：
# 1) RAW（MAC/cycle）  2) 范围归一化（shape 保持不变）

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

LOG_DIR="$SCRIPT_DIR/logs"
CSV_PATH="$SCRIPT_DIR/roofline_results.csv"
MACS_CSV="$SCRIPT_DIR/model_macs_gen.csv"
OUT_RAW="$SCRIPT_DIR/plots_mac_raw"
OUT_RANGE="$SCRIPT_DIR/plots_mac_range"

mkdir -p "$LOG_DIR" "$OUT_RAW" "$OUT_RANGE"

echo "=========================================="
echo "Generate per-model MACs (generation)"
echo "=========================================="
python3 "$SCRIPT_DIR/compute_model_macs.py" \
  --is_generation \
  --out "$MACS_CSV"

echo "=========================================="
echo "Parse logs -> CSV"
echo "=========================================="
python3 "$SCRIPT_DIR/parse_to_csv.py" \
  --log-dir "$LOG_DIR" \
  --out "$CSV_PATH"

echo "=========================================="
echo "Plot RAW (MAC/cycle)"
echo "=========================================="
python3 "$SCRIPT_DIR/plot_roofline.py" \
  --csv "$CSV_PATH" \
  --macs-csv "$MACS_CSV" \
  --out-dir "$OUT_RAW" \
  --throughput mac \
  --normalize no

echo "=========================================="
echo "Plot RAW with Y-normalized (MAC/cycle)"
echo "=========================================="
python3 "$SCRIPT_DIR/plot_roofline.py" \
  --csv "$CSV_PATH" \
  --macs-csv "$MACS_CSV" \
  --out-dir "$OUT_RAW" \
  --throughput mac \
  --normalize no \
  --normalize-y

echo "=========================================="
echo "Plot RANGE-normalized (MAC/cycle)"
echo "=========================================="
python3 "$SCRIPT_DIR/plot_roofline.py" \
  --csv "$CSV_PATH" \
  --macs-csv "$MACS_CSV" \
  --out-dir "$OUT_RANGE" \
  --throughput mac \
  --normalize range \
  --x-min 0.0 --x-max 1.0

echo "Done."
echo "RAW  -> $OUT_RAW"
echo "RANGE-> $OUT_RANGE"
echo "MACs -> $MACS_CSV"
echo "CSV  -> $CSV_PATH"


