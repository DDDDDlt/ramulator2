#!/bin/bash

# 运行所有加速器测试脚本
# 使用方法: bash run_all_tests.sh [--is_generation]

echo "=========================================="
echo "开始运行所有加速器测试"
echo "=========================================="
echo ""

# 检查是否有 --is_generation 参数
if [ "$1" == "--is_generation" ]; then
    GEN_FLAG="--is_generation"
    echo "模式: Generation"
else
    GEN_FLAG=""
    echo "模式: Prefill"
fi
echo ""

# 创建 log 目录（如果不存在）
mkdir -p ./log

# 测试列表
tests=("baseline" "olive" "ant" "mixposit" "bitmod")

# 运行每个测试
for test in "${tests[@]}"; do
    echo "=========================================="
    echo "正在运行: test_${test}.py"
    echo "=========================================="
    python test_${test}.py $GEN_FLAG > ./log/test_${test}.log 2>&1
    
    if [ $? -eq 0 ]; then
        echo "✓ test_${test}.py 运行成功"
    else
        echo "✗ test_${test}.py 运行失败"
    fi
    echo ""
done

echo "=========================================="
echo "所有测试完成！"
echo "日志文件保存在 ./log/ 目录下"
echo "=========================================="
echo ""

# 显示日志文件列表
echo "生成的日志文件："
ls -lh ./log/test_*.log

