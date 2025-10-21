# python test_olive.py --is_generation > ./log/test_olive.log
import argparse
from accelerator import Accelerator
from ramulator_dram_sim import get_cache_stats 

model_list = ["gpt2-large", "gpt2-xl", "microsoft/phi-2", "facebook/opt-2.7b",  "meta-llama/Llama-2-7b-hf"]
# model_list = ["microsoft/phi-2"]"01-ai/Yi-6B",
# model_list = ["facebook/opt-1.3b" ]  "meta-llama/Meta-Llama-3-8B"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--is_generation", action="store_true", help="If enabled, then evaluate")
    args = parser.parse_args()
    is_generation = args.is_generation

    w_prec_list = {
        'gpt2-large': 8,
        'gpt2-xl': 8,
        'facebook/opt-1.3b': 8,
        'facebook/opt-2.7b': 8,
        'microsoft/phi-2': 8, 
        '01-ai/Yi-6B': 8, 
        'meta-llama/Llama-2-7b-hf': 8, 
        'meta-llama/Llama-2-13b-hf': 8, 
        'meta-llama/Meta-Llama-3-8B': 8, 
    }

    if is_generation:
        pe_array_dim = [72, 16]
        # pe_array_dim = [32, 23]
        # pe_array_dim = [32, 30]
    else:
        pe_array_dim = [36, 32]
    
    total_energy_list = [[0, 0] for _ in model_list]
    total_latency_list = [0 for _ in model_list]

    # 打印加速器配置信息
    print("Accelerator: OLIVE (Non-uniform Quantization)")
    print(f"PE Array Dimension: {pe_array_dim}")
    print(f"Input Precision: 8-bit, Weight Precision: Variable (per-model)")
    print(f"Context Length: 256, Generation Mode: {is_generation}")
    print(f"Models to test: {len(model_list)}")
    print(f"pe_energy: {0.179497375}")
    print(f"pe_area: {767.41875}")
    print(f"pe_dp_size: 1")
    print()

    for idx, model_name in enumerate(model_list):
        if is_generation:
            w_prec = w_prec_list[model_name]
        else:
            w_prec = 4.5

        acc = Accelerator(
            model_name=model_name, 
            i_prec=8,
            w_prec=w_prec,
            is_bit_serial=False,
            pe_dp_size=1,
            # pe_energy=0.179497375,
            pe_energy=0.613,
            # pe_area=767.41875,
            pe_area=1318.6,
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

        w_prec_display = f"{w_prec:.4f}-bit" if isinstance(w_prec, float) else f"{w_prec}-bit"
        print(f'[{idx+1}/{len(model_list)}] Model: {model_name} (W_prec: {w_prec_display})')
        print(f'  Total Cycle:        {total_cycle[1]:,}')
        print(f'  PE Array Area:      {acc.pe_array_area / 1e6:.2f} mm²')
        print(f'  Weight Buffer:      {acc.w_sram.area:.2f} mm²')
        print(f'  Input Buffer:       {acc.i_sram.area:.2f} mm²')
        print(f'  DRAM Energy:        {dram_energy:.2f} mJ')
        print(f'  On-chip Energy:     {onchip_energy:.2f} mJ')
        print(f'  Total Energy:       {total_energy:.2f} mJ')


        print(f'  Energy Delay Product: {total_energy * total_cycle[1]:.2f}')

        print(f'  --- Energy Breakdown ---')
        print(f'  PE Compute Energy:  {compute_energy:.2f} mJ')
        print(f'  SRAM Read Energy:   {sram_rd_energy:.2f} mJ')
        print(f'  SRAM Write Energy:  {sram_wr_energy:.2f} mJ')
        
        # Bottleneck analysis
        # acc.print_bottleneck_analysis(show_details=False)
        
        total_latency_list[idx] = total_cycle[1]
        total_energy_list[idx][0] = round(onchip_energy)
        total_energy_list[idx][1] = round(total_energy)
        print()

    print("\nSummary:")
    print(f'Latency (cycles): {total_latency_list}')
    print(f'Energy [On-chip, Total] (mJ): {total_energy_list}')
    
    # Print cache statistics
    # cache_stats = get_cache_stats()
    # print("\nRamulator Cache Statistics:")
    # print(f"  Cache Hits:   {cache_stats['hits']}")
    # print(f"  Cache Misses: {cache_stats['misses']}")
    # print(f"  Hit Rate:     {cache_stats['hit_rate']:.1f}%")
    