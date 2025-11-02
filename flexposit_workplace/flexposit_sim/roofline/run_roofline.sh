#!/bin/bash

# 触发所有加速器+模型的维度扫描，并把日志与汇总结果放入 roofline 目录
# 缺省：y=16，x=4..80，步长=4，生成模式
# 用法示例：
#   bash roofline/run_roofline.sh
#   bash roofline/run_roofline.sh --y 16 --x-start 4 --x-end 80 --x-step 4

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

Y=16
X_START=2
X_END=120
X_STEP=2

while [[ $# -gt 0 ]]; do
    case "$1" in
        --y) Y="$2"; shift 2 ;;
        --x-start) X_START="$2"; shift 2 ;;
        --x-end) X_END="$2"; shift 2 ;;
        --x-step) X_STEP="$2"; shift 2 ;;
        -h|--help)
            echo "Usage: bash roofline/run_roofline.sh [--y INT] [--x-start INT] [--x-end INT] [--x-step INT]";
            exit 0 ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

echo "=========================================="
echo "Run roofline sweep"
echo "Logs: $LOG_DIR"
echo "Y   : $Y"
echo "X   : $X_START..$X_END (step $X_STEP)"
echo "Mode: Generation"
echo "=========================================="

# 1) 扫描（调用上一级的 run_dim_sweep.sh）
bash "$PROJECT_DIR/run_dim_sweep.sh" \
  --is_generation \
  --log-dir "$LOG_DIR" \
  --y "$Y" \
  --x-start "$X_START" \
  --x-end "$X_END" \
  --x-step "$X_STEP"

# 2) 解析日志 -> CSV
OUT_CSV="$SCRIPT_DIR/roofline_results.csv"
python3 "$SCRIPT_DIR/parse_to_csv.py" --log-dir "$LOG_DIR" --out "$OUT_CSV"

# 3) 绘图 -> PNG/PDF 到 plots/
PLOTS_DIR="$SCRIPT_DIR/plots"
# 按你的需求，默认不做归一化，直接画原始 Area / Throughput，并限制横轴范围到 [0.9, 2.5]
python3 "$SCRIPT_DIR/plot_roofline.py" --csv "$OUT_CSV" --out-dir "$PLOTS_DIR" --normalize no --x-min 0.9 --x-max 2.5

echo "Done. CSV -> $OUT_CSV"
echo "Plots saved in: $PLOTS_DIR"


