#!/bin/bash

# Sweep PE array dimensions for each accelerator and model.
# 默认：y=16，x: 4..80 步长 4；日志目录可指定。
# 用法示例：
#   bash run_dim_sweep.sh --log-dir ./log_sweep --y 16 --x-start 4 --x-end 80 --x-step 4 --is_generation

set -e

LOG_DIR="./log_sweep"
Y=16
X_START=4
X_END=80
X_STEP=4
IS_GENERATION=false

# 解析参数
while [[ $# -gt 0 ]]; do
    case "$1" in
        --log-dir)
            LOG_DIR="$2"; shift 2 ;;
        --y)
            Y="$2"; shift 2 ;;
        --x-start)
            X_START="$2"; shift 2 ;;
        --x-end)
            X_END="$2"; shift 2 ;;
        --x-step)
            X_STEP="$2"; shift 2 ;;
        --is_generation)
            IS_GENERATION=true; shift 1 ;;
        --prefill)
            IS_GENERATION=false; shift 1 ;;
        -h|--help)
            echo "Usage: bash run_dim_sweep.sh [--log-dir DIR] [--y INT] [--x-start INT] [--x-end INT] [--x-step INT] [--is_generation|--prefill]"
            exit 0 ;;
        *)
            echo "Unknown argument: $1"; exit 1 ;;
    esac
done

mkdir -p "$LOG_DIR"

echo "=========================================="
echo "Start PE-dimension sweep"
echo "Log dir     : $LOG_DIR"
echo "Y           : $Y"
echo "X range     : $X_START..$X_END (step $X_STEP)"
echo "Mode        : $( $IS_GENERATION && echo Generation || echo Prefill )"
echo "=========================================="
echo ""

# 测试加速器列表（与 run_all_tests.sh 一致）
tests=("baseline" "olive" "flexposit" "bitmod")

# 生成模式标志
GEN_FLAG=""
if $IS_GENERATION; then
    GEN_FLAG="--is_generation"
fi

# 循环扫描 X
for (( x=$X_START; x<=$X_END; x+=$X_STEP )); do
    for test in "${tests[@]}"; do
        log_file="$LOG_DIR/test_${test}_x${x}_y${Y}.log"
        echo "------------------------------------------"
        echo "Running: test_${test}.py  pe_dim=[$x,$Y]  -> $log_file"
        echo "------------------------------------------"
        # 将 pe_x/pe_y 传给各脚本（已在脚本内支持）
        python "test_${test}.py" $GEN_FLAG --pe_x "$x" --pe_y "$Y" > "$log_file" 2>&1 || true
    done
done

echo "=========================================="
echo "All sweeps finished! Logs under: $LOG_DIR"
echo "=========================================="
echo "Generated log files:"
ls -lh "$LOG_DIR"/test_*.log 2>/dev/null || true


