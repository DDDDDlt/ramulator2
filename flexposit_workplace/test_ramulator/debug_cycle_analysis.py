# Debug script to analyze cycle breakdown for compute vs memory bound layers

import argparse
from accelerator import Accelerator

model_name = "gpt2-large"  # 先测试GPT2-large

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--use_scale", action="store_true", help="Use scale overhead")
    args = parser.parse_args()
    
    use_scale = args.use_scale
    
    pe_array_dim = [10, 16]
    w_prec = 4
    
    print("=" * 80)
    print(f"Detailed Cycle Analysis for {model_name}")
    print(f"PE Array: {pe_array_dim}, Weight Precision: {w_prec}-bit")
    print(f"Use Scale Overhead: {use_scale}")
    print("=" * 80)
    print()
    
    acc = Accelerator(
        model_name=model_name, 
        i_prec=16,
        w_prec=w_prec,
        is_bit_serial=True,
        pe_dp_size=4,
        pe_energy=0.563,
        pe_area=911,
        pe_array_dim=pe_array_dim,
        context_length=256,
        is_generation=True,
        use_scale_overhead_lat=use_scale,
        scale_bits=8,
        meta_bits=2,
        group_size=128,
    )
    
    total_cycle = acc.calc_cycle()
    bottleneck_stats = acc.analyze_bottleneck()
    
    print(f"Total Compute Cycles: {total_cycle[0]:,}")
    print(f"Total Actual Cycles:  {total_cycle[1]:,}")
    print(f"Compute Utilization:  {total_cycle[0]/total_cycle[1]*100:.2f}%")
    print()
    
    print(f"Bottleneck Summary:")
    print(f"  Total Layers:         {bottleneck_stats['total_layers']}")
    print(f"  Memory-bound Layers:  {bottleneck_stats['memory_bound_count']} ({bottleneck_stats['memory_bound_count']/bottleneck_stats['total_layers']*100:.1f}%)")
    print(f"  Compute-bound Layers: {bottleneck_stats['compute_bound_count']} ({bottleneck_stats['compute_bound_count']/bottleneck_stats['total_layers']*100:.1f}%)")
    print()
    
    # 分别统计两类层的总周期
    total_compute_cycles = 0
    total_dram_cycles = 0
    memory_bound_contribution = 0
    compute_bound_contribution = 0
    
    for detail in bottleneck_stats['layer_details']:
        total_compute_cycles += detail['compute_cycles']
        total_dram_cycles += detail['dram_cycles']
        
        layer_contribution = max(detail['compute_cycles'], detail['dram_cycles'])
        if detail['bottleneck'] == 'Memory':
            memory_bound_contribution += layer_contribution
        else:
            compute_bound_contribution += layer_contribution
    
    print(f"Cycle Contribution Analysis:")
    print(f"  Sum of all compute cycles: {total_compute_cycles:,}")
    print(f"  Sum of all dram cycles:    {total_dram_cycles:,}")
    print(f"  Memory-bound layers total contribution: {memory_bound_contribution:,} ({memory_bound_contribution/total_cycle[1]*100:.1f}%)")
    print(f"  Compute-bound layers total contribution: {compute_bound_contribution:,} ({compute_bound_contribution/total_cycle[1]*100:.1f}%)")
    print()
    
    # 打印详细的层级信息
    print("=" * 120)
    print(f"{'Layer Name':<40} {'Compute Cycles':>15} {'DRAM Cycles':>15} {'Actual Cycles':>15} {'Bottleneck':<12} {'Ratio (D/C)':>12}")
    print("=" * 120)
    
    for detail in bottleneck_stats['layer_details']:
        layer_name = detail['name']
        compute_cycles = detail['compute_cycles']
        dram_cycles = detail['dram_cycles']
        actual_cycles = max(compute_cycles, dram_cycles)
        bottleneck = detail['bottleneck']
        ratio = detail['dram_to_compute_ratio']
        
        print(f"{layer_name:<40} {compute_cycles:>15,} {dram_cycles:>15,} {actual_cycles:>15,} {bottleneck:<12} {ratio:>12.2f}")
    
    print("=" * 120)
    print()
    
    # 分析compute-bound层的特征
    print("Compute-bound Layers Analysis:")
    print("-" * 80)
    for layer_name in bottleneck_stats['compute_bound_layers']:
        detail = next(d for d in bottleneck_stats['layer_details'] if d['name'] == layer_name)
        print(f"  {layer_name}:")
        print(f"    Compute Cycles: {detail['compute_cycles']:,}")
        print(f"    DRAM Cycles:    {detail['dram_cycles']:,}")
        print(f"    Ratio (D/C):    {detail['dram_to_compute_ratio']:.3f}")
        
        # 获取该层的详细DRAM周期信息
        if hasattr(acc, '_layer_cycle_dram_detail'):
            dram_detail = acc._layer_cycle_dram_detail[layer_name]
            print(f"    DRAM Breakdown:")
            print(f"      Weight cycles: {dram_detail['weight_cycles']:,}")
            print(f"      Input cycles:  {dram_detail['input_cycles']:,}")
            print(f"      Output cycles: {dram_detail['output_cycles']:,}")
        print()
    
    # 分析一些memory-bound层的例子
    print("Memory-bound Layers Examples (first 5):")
    print("-" * 80)
    for i, layer_name in enumerate(bottleneck_stats['memory_bound_layers'][:5]):
        detail = next(d for d in bottleneck_stats['layer_details'] if d['name'] == layer_name)
        print(f"  {layer_name}:")
        print(f"    Compute Cycles: {detail['compute_cycles']:,}")
        print(f"    DRAM Cycles:    {detail['dram_cycles']:,}")
        print(f"    Ratio (D/C):    {detail['dram_to_compute_ratio']:.3f}")
        
        # 获取该层的详细DRAM周期信息
        if hasattr(acc, '_layer_cycle_dram_detail'):
            dram_detail = acc._layer_cycle_dram_detail[layer_name]
            print(f"    DRAM Breakdown:")
            print(f"      Weight cycles: {dram_detail['weight_cycles']:,}")
            print(f"      Input cycles:  {dram_detail['input_cycles']:,}")
            print(f"      Output cycles: {dram_detail['output_cycles']:,}")
        print()

