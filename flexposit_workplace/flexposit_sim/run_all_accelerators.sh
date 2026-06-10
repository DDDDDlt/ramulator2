#!/bin/bash

# 运行所有加速器测试脚本，使用 3200AA DRAM config
# 输出目录: log/v2_0302_ddr4_3200AA

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${SCRIPT_DIR}/log/v2_0302_ddr4_3200AA"

# 创建输出目录
mkdir -p "${LOG_DIR}"

echo "=========================================="
echo "运行所有加速器测试"
echo "输出目录: ${LOG_DIR}"
echo "DRAM Config: DDR4_3200AA (固定)"
echo "=========================================="
echo ""

# 切换到脚本目录
cd "${SCRIPT_DIR}"

# 1. 运行 Baseline
echo "[1/4] 运行 Baseline (FP16)..."
python test_baseline.py --is_generation 2>&1 | tee "${LOG_DIR}/test_baseline.log"
BASELINE_EXIT=$?
if [ $BASELINE_EXIT -eq 0 ]; then
    echo "✅ Baseline 完成"
else
    echo "❌ Baseline 失败 (退出码: $BASELINE_EXIT)"
    echo "最后10行错误信息:"
    tail -n 10 "${LOG_DIR}/test_baseline.log"
fi
echo ""

# 2. 运行 FlexPosit
echo "[2/4] 运行 FlexPosit (MixPosit)..."
python test_flexposit.py --is_generation 2>&1 | tee "${LOG_DIR}/test_flexposit.log"
FLEXPOSIT_EXIT=$?
if [ $FLEXPOSIT_EXIT -eq 0 ]; then
    echo "✅ FlexPosit 完成"
else
    echo "❌ FlexPosit 失败 (退出码: $FLEXPOSIT_EXIT)"
    echo "最后20行错误信息:"
    tail -n 20 "${LOG_DIR}/test_flexposit.log"
fi
echo ""

# 3. 运行 BitMod
echo "[3/4] 运行 BitMod (Bit-Serial)..."
python test_bitmod.py --is_generation 2>&1 | tee "${LOG_DIR}/test_bitmod.log"
BITMOD_EXIT=$?
if [ $BITMOD_EXIT -eq 0 ]; then
    echo "✅ BitMod 完成"
else
    echo "❌ BitMod 失败 (退出码: $BITMOD_EXIT)"
    echo "最后20行错误信息:"
    tail -n 20 "${LOG_DIR}/test_bitmod.log"
fi
echo ""

# 4. 运行 OLIVE
echo "[4/4] 运行 OLIVE (Non-uniform Quantization)..."
python test_olive.py --is_generation 2>&1 | tee "${LOG_DIR}/test_olive.log"
OLIVE_EXIT=$?
if [ $OLIVE_EXIT -eq 0 ]; then
    echo "✅ OLIVE 完成"
else
    echo "❌ OLIVE 失败 (退出码: $OLIVE_EXIT)"
    echo "最后20行错误信息:"
    tail -n 20 "${LOG_DIR}/test_olive.log"
fi
echo ""

echo "=========================================="
echo "所有测试完成！"
echo "结果保存在: ${LOG_DIR}"
echo ""
echo "测试结果汇总:"
echo "  Baseline:  $([ $BASELINE_EXIT -eq 0 ] && echo '✅ 成功' || echo '❌ 失败')"
echo "  FlexPosit: $([ $FLEXPOSIT_EXIT -eq 0 ] && echo '✅ 成功' || echo '❌ 失败')"
echo "  BitMod:    $([ $BITMOD_EXIT -eq 0 ] && echo '✅ 成功' || echo '❌ 失败')"
echo "  OLIVE:     $([ $OLIVE_EXIT -eq 0 ] && echo '✅ 成功' || echo '❌ 失败')"
echo "=========================================="
