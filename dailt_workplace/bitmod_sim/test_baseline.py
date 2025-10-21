# python test_baseline.py --is_generation > ./log/test_baseline.log
import argparse
from accelerator import Accelerator
from ramulator_dram_sim import get_cache_stats 

model_list = ["gpt2-large", "gpt2-xl", "microsoft/phi-2", "facebook/opt-2.7b", "meta-llama/Llama-2-7b-hf"]
# model_list = ["facebook/opt-1.3b"]
# model_list = ["microsoft/phi-2"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--is_generation", action="store_true", help="If enabled, then evaluate")
    args = parser.parse_args()
    is_generation = args.is_generation
    
    if is_generation:
        pe_array_dim = [64, 12]
        # pe_array_dim = [32, 8]
        # pe_array_dim = [32, 12]
    else:
        pe_array_dim = [32, 24]
    
    total_energy_list = [[0, 0] for _ in model_list]
    total_latency_list = [0 for _ in model_list]

    # 打印加速器配置信息
    print("Accelerator: Baseline (FP16)")
    print(f"PE Array Dimension: {pe_array_dim}")
    print(f"Input Precision: 16-bit, Weight Precision: 16-bit")
    print(f"Context Length: 256, Generation Mode: {is_generation}")
    print(f"Models to test: {len(model_list)}")
    print()

    for idx, model_name in enumerate(model_list):
        acc = Accelerator(
            model_name=model_name, 
            i_prec=16,
            w_prec=16,
            is_bit_serial=False,
            pe_dp_size=1,
            pe_energy=0.77,
            pe_area=1968.7,
            pe_array_dim=pe_array_dim,
            context_length=256,
            is_generation=is_generation,
            use_scale_overhead_lat=False,
            # scale_bits=8,
            # meta_bits=2,
            # group_size=128,
        )

        total_cycle    = acc.calc_cycle()
        compute_energy = acc.calc_compute_energy() / 1e6
        sram_rd_energy = acc.calc_sram_rd_energy() / 1e6
        sram_wr_energy = acc.calc_sram_wr_energy() / 1e6
        dram_energy    = acc.calc_dram_energy() / 1e6
        onchip_energy  = compute_energy + sram_rd_energy + sram_wr_energy
        total_energy   = compute_energy + sram_rd_energy + sram_wr_energy + dram_energy

        print(f'[{idx+1}/{len(model_list)}] Model: {model_name}')
        print(f'  Total Cycle:        {total_cycle[1]:,}')
        print(f'  PE Array Area:      {acc.pe_array_area / 1e6:.2f} mm²')
        print(f'  Weight Buffer:      {acc.w_sram.area:.2f} mm²')
        print(f'  Input Buffer:       {acc.i_sram.area:.2f} mm²')
        print(f'  DRAM Energy:        {dram_energy:.2f} mJ')
        print(f'  On-chip Energy:     {onchip_energy:.2f} mJ')
        print(f'  Total Energy:       {total_energy:.2f} mJ')
        
        print(f'  Energy Delay Product: {total_energy * total_cycle[1]:.2f}')
        
        # Bottleneck analysis
        acc.print_bottleneck_analysis(show_details=False)
        
        total_latency_list[idx] = total_cycle[1]
        total_energy_list[idx][0] = round(onchip_energy)
        total_energy_list[idx][1] = round(total_energy)
        print()

    print("\nSummary:")
    print(f'Latency (cycles): {total_latency_list}')
    print(f'Energy [On-chip, Total] (mJ): {total_energy_list}')
    
    # # Print cache statistics
    # cache_stats = get_cache_stats()
    # print("\nRamulator Cache Statistics:")
    # print(f"  Cache Hits:   {cache_stats['hits']}")
    # print(f"  Cache Misses: {cache_stats['misses']}")
    # print(f"  Hit Rate:     {cache_stats['hit_rate']:.1f}%")