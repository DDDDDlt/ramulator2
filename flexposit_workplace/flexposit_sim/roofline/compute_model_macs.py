#!/usr/bin/env python3

import argparse
import csv
import os
import sys
from typing import Dict, List

# ensure we can import from flexposit_sim root
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SIM_ROOT = os.path.dirname(CURRENT_DIR)
if SIM_ROOT not in sys.path:
    sys.path.insert(0, SIM_ROOT)

from pe_array import PE_Array


DEFAULT_MODELS: List[str] = [
    "gpt2-large",
    "gpt2-xl",
    "microsoft/phi-2",
    "facebook/opt-2.7b",
    "meta-llama/Llama-2-7b-hf",
]


def compute_total_macs_for_model(model_name: str, context_length: int, is_generation: bool) -> int:
    # PE_Array 读取形状时使用相对路径 './model_shape_config/...'
    # 这里临时切换到 flexposit_sim 根目录，确保能找到形状文件
    old_cwd = os.getcwd()
    try:
        os.chdir(SIM_ROOT)
        pe = PE_Array(
            model_name=model_name,
            i_prec=16,
            w_prec=16,
            is_bit_serial=False,
            pe_dp_size=1,
            pe_energy=1.0,
            pe_area=1.0,
            pe_array_dim=[1, 1],
            context_length=context_length,
            is_generation=is_generation,
            is_flexposit=False,
        )
    finally:
        os.chdir(old_cwd)

    total_macs = 0
    for lname in pe.layer_name_list:
        w_dim = pe.weight_dim[lname]
        o_dim = pe.output_dim[lname]
        if w_dim is None or o_dim is None:
            continue
        cout, cin = w_dim
        num_token, _ = o_dim
        total_macs += int(cout) * int(cin) * int(num_token)
    return total_macs


def main():
    parser = argparse.ArgumentParser(description="Compute per-model total MACs from shape configs")
    parser.add_argument("--models", nargs="*", default=DEFAULT_MODELS, help="Model names to compute; default common set")
    parser.add_argument("--context-length", type=int, default=256, help="Context length (prefill) or step length (gen)")
    parser.add_argument("--is_generation", action="store_true", help="Use generation shapes (default: prefill)")
    parser.add_argument("--out", default=None, help="Output CSV path (optional)")
    args = parser.parse_args()

    results: Dict[str, int] = {}
    for model in args.models:
        macs = compute_total_macs_for_model(model, args.context_length, args.is_generation)
        results[model] = macs
        print(f"{model}: {macs}")

    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["model", "total_macs", "context_length", "is_generation"])
            for model, macs in results.items():
                writer.writerow([model, macs, args.context_length, int(args.is_generation)])
        print(f"Wrote CSV: {args.out}")


if __name__ == "__main__":
    main()


