#!/bin/bash

# Profile所有模型形状配置
# 输出目录: model_shape_config/

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Set your HuggingFace HOME directory to store downloaded model and datasets
export HF_HOME="${HF_HOME:-/home/liangtaodai/.cache/huggingface}"

echo "=========================================="
echo "Profile模型形状配置"
echo "HF_HOME: ${HF_HOME}"
echo "=========================================="
echo ""

# 切换到脚本目录
cd "${SCRIPT_DIR}"

# 模型列表（9个模型）
declare -a model_list=(
    "gpt2-large"
    "gpt2-xl"
    "microsoft/phi-2"
    "facebook/opt-2.7b"
    "meta-llama/Llama-2-7b-hf"
    "Qwen/Qwen2.5-7B"
    "mistralai/Mistral-7B-v0.1"
    "deepseek-ai/deepseek-llm-7b-base"
    "Qwen/Qwen2.5-14B"
)

# 创建输出目录
mkdir -p "${SCRIPT_DIR}/model_shape_config"

SUCCESS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

for model in "${model_list[@]}"
do
    # 获取模型文件名
    model_file=$(python3 -c "
model_name_dict = {
    'gpt2-large': 'gpt2_large',
    'gpt2-xl': 'gpt2_xl',
    'microsoft/phi-2': 'phi_2',
    'facebook/opt-2.7b': 'opt_2_point_7',
    'meta-llama/Llama-2-7b-hf': 'llama_2_7',
    'Qwen/Qwen2.5-7B': 'qwen2_5_7b',
    'Qwen/Qwen2.5-14B': 'qwen2_5_14b',
    'mistralai/Mistral-7B-v0.1': 'mistral_7b',
    'deepseek-ai/deepseek-llm-7b-base': 'deepseek_llm_7b',
}
print(model_name_dict.get('${model}', 'unknown') + '.pickle')
" 2>/dev/null)
    
    model_path="${SCRIPT_DIR}/model_shape_config/${model_file}"
    
    if [ -f "$model_path" ]; then
        echo "[跳过] ${model} (已存在: ${model_file})"
        SKIP_COUNT=$((SKIP_COUNT + 1))
    else
        echo "[Profile] ${model}..."
        python3 llm_shape_profile.py --model "${model}" 2>&1
        if [ $? -eq 0 ]; then
            echo "✅ ${model} Profile完成"
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        else
            echo "❌ ${model} Profile失败"
            FAIL_COUNT=$((FAIL_COUNT + 1))
        fi
        echo ""
    fi
done

echo "=========================================="
echo "Profile完成！"
echo "  成功: ${SUCCESS_COUNT}"
echo "  失败: ${FAIL_COUNT}"
echo "  跳过: ${SKIP_COUNT}"
echo "  总计: ${#model_list[@]}"
echo "=========================================="
