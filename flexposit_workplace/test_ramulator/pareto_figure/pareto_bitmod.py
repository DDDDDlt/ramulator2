import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from accelerator import Accelerator
import numpy as np

# 移除pareto前沿计算函数，简化脚本

def main():
    # 模型配置 - 使用标准格式，系统会自动映射到正确的文件路径
    model_name = "facebook/opt-1.3b"
    # 减少维度范围，避免过大的PE阵列导致配置不合法
    dim_options = [
        [4, 4], [8, 4], [8, 8], [16, 8], [16, 16],
        [32, 8], [32, 16], [32, 32]  # 移除[64, 16], [64, 32]这些过大的配置
    ]

    results = []

    print("Testing different PE array dimensions...")
    print("Dim\t\tLatency\t\tEnergy(uJ)\tArea(mm2)")
    print("-" * 55)

    for dim in dim_options:
        try:
            acc = Accelerator(
                model_name=model_name,
                i_prec=16,
                w_prec=4.0625,
                is_bit_serial=True,
                pe_dp_size=4,
                pe_energy=0.56,
                pe_area=1507.7,
                pe_array_dim=dim,
                context_length=256,
                is_generation=False,
                use_scale_overhead_lat=True,
                scale_bits=8,
                meta_bits=2,
                group_size=128,
            )

            total_cycle = acc.calc_cycle()
            compute_energy = acc.calc_compute_energy() / 1e6
            sram_rd_energy = acc.calc_sram_rd_energy() / 1e6
            sram_wr_energy = acc.calc_sram_wr_energy() / 1e6
            dram_energy = acc.calc_dram_energy() / 1e6
            total_energy = compute_energy + sram_rd_energy + sram_wr_energy + dram_energy

            latency = total_cycle[1]  # 使用总的latency
            area = acc.pe_array_area / 1e6  # 转换为mm2
            results.append((latency, total_energy, area))

            print(f"{dim}\t\t{latency}\t\t{total_energy:.2f}\t\t{area:.2f}")

        except Exception as e:
            print(f"Error with dim {dim}: {str(e)[:100]}...")  # 截断错误信息
            continue

    # 显示所有测试结果
    if results:
        # 打印所有结果
        print(f"\nAll test results ({len(results)} configurations):")
        for i, (lat, eng, area) in enumerate(results):
            print(f"  {i+1}. Latency: {lat}, Energy: {eng:.2f}, Area: {area:.2f}")

        # 2D投影图
        latencies = [p[0] for p in results]
        energies = [p[1] for p in results]
        areas = [p[2] for p in results]

        plt.figure(figsize=(15, 6))

        # 子图1: 2D Latency vs Energy
        plt.subplot(1, 3, 1)
        plt.scatter(latencies, energies, alpha=0.7, s=60, color='blue')
        plt.xlabel('Latency (cycles)')
        plt.ylabel('Energy (uJ)')
        plt.title('Latency vs Energy')
        plt.grid(True, alpha=0.3)

        # 子图2: 2D Latency vs Area
        plt.subplot(1, 3, 2)
        plt.scatter(latencies, areas, alpha=0.7, s=60, color='green')
        plt.xlabel('Latency (cycles)')
        plt.ylabel('Area (mm²)')
        plt.title('Latency vs Area')
        plt.grid(True, alpha=0.3)

        # 子图3: 2D Energy vs Area
        plt.subplot(1, 3, 3)
        plt.scatter(energies, areas, alpha=0.7, s=60, color='red')
        plt.xlabel('Energy (uJ)')
        plt.ylabel('Area (mm²)')
        plt.title('Energy vs Area')
        plt.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.suptitle('PE Array Configurations: 2D Projections', fontsize=16, y=0.98)
        plt.savefig('pe_configurations_bitmod_2d.png', dpi=150, bbox_inches='tight')

        # 3D图
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')

        # 绘制所有点
        ax.scatter(latencies, energies, areas, alpha=0.7, s=80, color='blue')

        ax.set_xlabel('Latency (cycles)', fontsize=12, labelpad=10)
        ax.set_ylabel('Energy (uJ)', fontsize=12, labelpad=10)
        ax.set_zlabel('Area (mm²)', fontsize=12, labelpad=10)
        ax.set_title('PE Array Configurations: 3D View\nLatency × Energy × Area', fontsize=14, pad=20)
        ax.grid(True, alpha=0.3)

        # 设置视角
        ax.view_init(elev=20, azim=45)

        plt.tight_layout()
        plt.savefig('pe_configurations_bitmod_3d.png', dpi=150, bbox_inches='tight')

        print(f"\n📊 2D projections saved as 'pe_configurations_2d.png'")
        print(f"🎯 3D view saved as 'pe_configurations_bitmod_3d.png'")
        print(f"Total configurations tested: {len(results)}")
    else:
        print("No valid results obtained.")

if __name__ == "__main__":
    main()
