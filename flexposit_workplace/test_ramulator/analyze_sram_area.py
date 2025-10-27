#!/usr/bin/env python3
"""
分析不同加速器的SRAM area计算方式
"""
import math

def calc_sram_bandwidth(accelerator_name, pe_array_h, pe_array_w, i_prec, w_prec, is_bit_serial, pe_dp_size):
    """
    根据accelerator.py中的_init_mem()函数计算SRAM带宽
    """
    # Weight SRAM带宽计算
    if is_bit_serial:
        w_bandwidth = pe_dp_size * math.ceil(w_prec / 4) * 4 * pe_array_h / 2
    else:
        w_bandwidth = pe_dp_size * math.ceil(w_prec / 4) * 4 * pe_array_h
    
    # Input SRAM带宽计算
    if is_bit_serial:
        i_bandwidth = pe_dp_size * i_prec * pe_array_w / 2
    else:
        i_bandwidth = pe_dp_size * i_prec * pe_array_w
    
    return w_bandwidth, i_bandwidth

# 定义各个加速器的配置参数
accelerators = {
    'OLIVE': {
        'pe_array': [72, 16],
        'i_prec': 8,
        'w_prec': 8,
        'is_bit_serial': False,
        'pe_dp_size': 1,
    },
    'BitMod': {
        'pe_array': [64, 16],
        'i_prec': 16,
        'w_prec': 4,
        'is_bit_serial': True,
        'pe_dp_size': 4,
    },
    'Baseline': {
        'pe_array': [64, 12],
        'i_prec': 16,
        'w_prec': 16,
        'is_bit_serial': False,
        'pe_dp_size': 1,
    },
    'MixPosit': {
        'pe_array': [64, 16],
        'i_prec': 16,
        'w_prec': 4.5,
        'is_bit_serial': True,
        'pe_dp_size': 4,
    },
}

# SRAM配置参数（所有加速器共同的）
SRAM_SIZE = 512 * 1024 * 8  # bits
SRAM_BANK_COUNT = 8
TECHNOLOGY = 0.028  # μm

print("=" * 80)
print("SRAM Area 计算分析")
print("=" * 80)
print()

print("关键点：SRAM area由CACTI工具根据以下参数计算：")
print("  - technology: 工艺节点 (28nm)")
print("  - size: SRAM大小 (512KB)")
print("  - bank_count: Bank数量 (8)")
print("  - rw_bw: 读写带宽 (bits/cycle) ← 这是导致不同加速器area不同的关键！")
print()
print("=" * 80)
print()

results = []
for name, config in accelerators.items():
    pe_array_h, pe_array_w = config['pe_array']
    i_prec = config['i_prec']
    w_prec = config['w_prec']
    is_bit_serial = config['is_bit_serial']
    pe_dp_size = config['pe_dp_size']
    
    w_bw, i_bw = calc_sram_bandwidth(
        name, pe_array_h, pe_array_w, i_prec, w_prec, is_bit_serial, pe_dp_size
    )
    
    results.append({
        'name': name,
        'pe_array': config['pe_array'],
        'i_prec': i_prec,
        'w_prec': w_prec,
        'is_bit_serial': is_bit_serial,
        'pe_dp_size': pe_dp_size,
        'w_bandwidth': w_bw,
        'i_bandwidth': i_bw,
    })

# 打印结果
for r in results:
    print(f"加速器: {r['name']}")
    print(f"  PE Array维度: {r['pe_array'][0]} × {r['pe_array'][1]}")
    print(f"  输入精度: {r['i_prec']}-bit")
    print(f"  权重精度: {r['w_prec']}-bit")
    print(f"  是否Bit-Serial: {r['is_bit_serial']}")
    print(f"  PE DP Size: {r['pe_dp_size']}")
    print(f"  → Weight SRAM带宽: {r['w_bandwidth']:.1f} bits/cycle")
    print(f"  → Input SRAM带宽:  {r['i_bandwidth']:.1f} bits/cycle")
    print()

print("=" * 80)
print("带宽计算公式:")
print("=" * 80)
print()
print("Weight SRAM带宽:")
print("  if is_bit_serial:")
print("    w_bw = pe_dp_size × ⌈w_prec/4⌉ × 4 × pe_array_h ÷ 2")
print("  else:")
print("    w_bw = pe_dp_size × ⌈w_prec/4⌉ × 4 × pe_array_h")
print()
print("Input SRAM带宽:")
print("  if is_bit_serial:")
print("    i_bw = pe_dp_size × i_prec × pe_array_w ÷ 2")
print("  else:")
print("    i_bw = pe_dp_size × i_prec × pe_array_w")
print()

print("=" * 80)
print("为什么不同加速器的SRAM area不同？")
print("=" * 80)
print()
print("1. **带宽需求不同**：")
print("   - 不同的PE array维度、精度、bit-serial模式会导致不同的带宽需求")
print("   - 例如：OLIVE使用72×16的PE array，而Baseline使用64×12")
print()
print("2. **CACTI的area计算**：")
print("   - CACTI根据带宽需求来设计SRAM的物理实现")
print("   - 更高的带宽需要：")
print("     * 更多的I/O端口")
print("     * 更宽的数据总线")
print("     * 可能需要更多的sense amplifier和其他外围电路")
print("   - 这些都会增加SRAM的面积")
print()
print("3. **面积权衡**：")
print("   - 虽然所有加速器使用相同的SRAM容量（512KB）")
print("   - 但为了支持不同的带宽，物理实现（端口数、线宽等）不同")
print("   - 导致最终面积有所差异")
print()

# 从log文件中提取实际的area数据进行对比
print("=" * 80)
print("实际Area对比（从log文件）：")
print("=" * 80)
print()
print("加速器       | Weight Buffer | Input Buffer  | 差异原因")
print("-" * 80)
print("OLIVE        | 1.43 mm²      | 1.43 mm²      | 8-bit精度，非bit-serial，较大PE array")
print("BitMod       | 1.60 mm²      | 1.60 mm²      | 16-bit输入，bit-serial，高带宽")
print("Baseline     | 1.57 mm²      | 1.53 mm²      | 16-bit全精度，较小PE array宽度")
print("MixPosit     | 1.57 mm²      | 1.60 mm²      | 16-bit输入，bit-serial")
print()
print("注意：Weight Buffer和Input Buffer的area略有不同，因为它们的带宽配置不同")
print()

