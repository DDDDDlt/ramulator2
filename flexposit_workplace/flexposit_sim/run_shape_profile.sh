#!/bin/bash

# Set your HuggingFace HOME directory to store downloaded model and datasets, default is your own HOME directory.
export HF_HOME="/home/liangtaodai/.cache/huggingface"

declare -a model_list=("gpt2-large" "gpt2-xl" "microsoft/phi-2" "facebook/opt-2.7b" "meta-llama/Llama-2-7b-hf" "Qwen/Qwen2.5-7B" "mistralai/Mistral-7B-v0.1" "deepseek-ai/deepseek-llm-7b-base" "Qwen/Qwen2.5-14B")
# declare -a model_list=("facebook/opt-1.3b")


for model in "${model_list[@]}"
do
    echo "model = ${model}"
    python llm_shape_profile.py --model ${model} 
done

