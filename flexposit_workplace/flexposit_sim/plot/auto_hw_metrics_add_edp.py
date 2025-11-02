import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for headless environments

import os
import argparse
import math
import re
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patheffects
from matplotlib import gridspec
from matplotlib.patches import Patch

# ==============================
#  Advanced style settings - consistent with hardware block diagrams
# ==============================
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'Roboto', 'Source Sans Pro', 'DejaVu Sans', 'Liberation Sans']
plt.rcParams['font.size'] = 11
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 13
plt.rcParams['legend.fontsize'] = 9
plt.rcParams['xtick.labelsize'] = 10
plt.rcParams['ytick.labelsize'] = 10
plt.rcParams['axes.linewidth'] = 1.2
plt.rcParams['axes.edgecolor'] = '#444444'
plt.rcParams['axes.facecolor'] = '#FAFAFA'  # light gray background
plt.rcParams['axes.labelcolor'] = '#444444'  # dark gray axis labels
plt.rcParams['xtick.color'] = '#444444'
plt.rcParams['ytick.color'] = '#444444'
plt.rcParams['text.color'] = '#444444'
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['grid.alpha'] = 0.5
plt.rcParams['grid.linestyle'] = ':'
plt.rcParams['grid.color'] = '#CCCCCC'

# ==============================
#  Parse log files
# ==============================
def parse_log_file(log_path):
    """
    Parse one log file and extract latency and energy arrays.
    Returns: (latency_list, on_chip_energy_list, off_chip_energy_list, accelerator_name)
    """
    with open(log_path, 'r') as f:
        content = f.read()
    
    # Extract accelerator name (first line)
    first_line = content.split('\n')[0]
    acc_name_match = re.search(r'Accelerator:\s+(.+)', first_line)
    accelerator_name = acc_name_match.group(1) if acc_name_match else "Unknown"
    
    # Extract latency array in Summary
    latency_match = re.search(r'Latency \(cycles\):\s*\[([^\]]+)\]', content)
    if not latency_match:
        print(f"Warning: Latency not found in {log_path}")
        return None, None, None, accelerator_name
    
    latency_str = latency_match.group(1)
    latency_list = [float(x.strip()) for x in latency_str.split(',')]
    
    # Extract Energy arrays in Summary
    # Format: Energy [On-chip, Total] (mJ): [[on1, total1], [on2, total2], ...]
    energy_match = re.search(r'Energy \[On-chip, Total\] \(mJ\):\s*(\[\[.+?\]\])', content)
    if not energy_match:
        print(f"Warning: Energy not found in {log_path}")
        return latency_list, None, None, accelerator_name
    
    energy_str = energy_match.group(1)
    # Parse nested list [[on1, total1], [on2, total2], ...]
    # Use precise regex to match each [num, num] pair
    energy_pairs = re.findall(r'\[(\d+(?:\.\d+)?),\s*(\d+(?:\.\d+)?)\]', energy_str)
    on_chip_energy = []
    off_chip_energy = []
    total_energy = []
    
    for on_chip_str, total_str in energy_pairs:
        on_chip = float(on_chip_str)
        total = float(total_str)
        off_chip = total - on_chip
        on_chip_energy.append(on_chip)
        off_chip_energy.append(off_chip)
        total_energy.append(total)
    
    # Print parsing result
    print(f"\n{'='*70}")
    print(f"📄 File: {os.path.basename(log_path)}")
    print(f"🏷️  Accelerator: {accelerator_name}")
    print(f"⏱️  Latency (cycles): {latency_list}")
    print(f"⚡ On-chip Energy (mJ): {on_chip_energy}")
    print(f"💾 Off-chip Energy (mJ): {off_chip_energy}")
    print(f"📊 Total Energy (mJ): {total_energy}")
    print(f"{'='*70}")
    
    return latency_list, on_chip_energy, off_chip_energy, accelerator_name


def load_all_logs(log_dir):
    """
    Load all log files
    Return: dict with keys as accelerator names
    """
    log_files = {
        'Baseline': 'test_baseline.log',
        'FlexPosit': 'test_flexposit.log',
        'BitMod': 'test_bitmod.log',
        'Olive': 'test_olive.log'
    }
    
    data = {}
    
    for acc_key, log_file in log_files.items():
        log_path = os.path.join(log_dir, log_file)
        if os.path.exists(log_path):
            latency, on_chip, off_chip, acc_name = parse_log_file(log_path)
            if latency is not None:
                data[acc_key] = {
                    'latency': np.array(latency),
                    'on_chip_energy': np.array(on_chip) if on_chip else None,
                    'off_chip_energy': np.array(off_chip) if off_chip else None,
                    'full_name': acc_name
                }
                print(f"✅ Loaded: {log_file} ({acc_name})")
        else:
            print(f"⚠️  File not found: {log_path}")
    
    return data


def normalize_data(data, baseline_key='Baseline'):
    """
    Normalize all data to baseline (per-model normalization)
    Each model independently normalized such that baseline total energy = 1.0
    """
    if baseline_key not in data:
        print(f"Warning: baseline missing, use the first accelerator as baseline")
        baseline_key = list(data.keys())[0]
    
    baseline_latency = np.array(data[baseline_key]['latency'])
    baseline_on_chip = np.array(data[baseline_key]['on_chip_energy'])
    baseline_off_chip = np.array(data[baseline_key]['off_chip_energy'])
    baseline_total_energy = baseline_on_chip + baseline_off_chip  # 每个模型的baseline总能量
    
    # Compute baseline EDP
    baseline_edp = baseline_latency * baseline_total_energy
    
    normalized_data = {}
    
    print("\n" + "="*70)
    print("🔄 Start normalizing data (relative to Baseline, per-model)")
    print("="*70)
    
    model_names = ["GPT2-L", "GPT2-XL", "Phi-2B", "OPT-2.7B", "Llama2-7B"]
    
    for acc_key, acc_data in data.items():
        acc_on_chip = np.array(acc_data['on_chip_energy'])
        acc_off_chip = np.array(acc_data['off_chip_energy'])
        acc_latency = np.array(acc_data['latency'])
        acc_total_energy = acc_on_chip + acc_off_chip
        
        # Latency normalization: per-model
        norm_latency = acc_latency / baseline_latency
        
        # Energy normalization: per-model (element-wise division)
        norm_on_chip = acc_on_chip / baseline_total_energy
        norm_off_chip = acc_off_chip / baseline_total_energy
        
        # EDP normalization: EDP = Latency × Total_Energy
        acc_edp = acc_latency * acc_total_energy
        norm_edp = acc_edp / baseline_edp
        
        normalized_data[acc_key] = {
            'norm_latency': norm_latency,
            'norm_on_chip': norm_on_chip,
            'norm_off_chip': norm_off_chip,
            'norm_edp': norm_edp,
            'full_name': acc_data['full_name']
        }
        
        # Print normalized results (per-model)
        print(f"\n📊 {acc_key} ({acc_data['full_name']})")
        for i, model_name in enumerate(model_names):
            total_norm = norm_on_chip[i] + norm_off_chip[i]
            print(f"   {model_name:12s}: Latency={norm_latency[i]:.3f}, "
                  f"Energy={total_norm:.3f}, EDP={norm_edp[i]:.3f}")
    
    print("\n" + "="*70)
    
    return normalized_data


# ==============================
#  Plotting (with EDP)
# ==============================
def plot_metrics_with_edp(normalized_data, output_prefix='auto_hw_metrics_edp'):
    """
    Plot latency, energy and EDP (three subplots)
    """
    # 模型名称（5个模型）+ 平均值
    models = [
        "GPT2-L", "GPT2-XL", "Phi-2B",
        "OPT-2.7B", "Llama2-7B", "Average"
    ]
    
    # Accelerator order (can be adjusted)
    accelerator_order = ['FlexPosit', 'BitMod', 'Olive', 'Baseline']
    accelerators = [acc for acc in accelerator_order if acc in normalized_data]
    
    # Color scheme consistent with hardware figures (teal, orange, gray)
    acc_colors = {
        'FlexPosit': '#4FB0A9',   # 青绿主色（与硬件图核心模块一致）
        'BitMod': '#F4A261',     # 暖橙色（与Bit-serial路径呼应）
        'Olive': '#457B9D',      # 深青蓝（稳重对比）
        'Baseline': '#BDBDBD'    # 浅灰（代表参考基线）
    }
    
    # Prepare matrices (including averages)
    n_models = len(models)  # 包含Average
    n_accs = len(accelerators)
    n_actual_models = n_models - 1  # actual models (exclude Average)
    
    norm_cycle = np.zeros((n_models, n_accs))
    norm_energy_on = np.zeros((n_models, n_accs))
    norm_energy_off = np.zeros((n_models, n_accs))
    norm_edp = np.zeros((n_models, n_accs))
    
    for j, acc in enumerate(accelerators):
        # 前n_actual_models行是实际数据
        norm_cycle[:n_actual_models, j] = normalized_data[acc]['norm_latency']
        norm_energy_on[:n_actual_models, j] = normalized_data[acc]['norm_on_chip']
        norm_energy_off[:n_actual_models, j] = normalized_data[acc]['norm_off_chip']
        norm_edp[:n_actual_models, j] = normalized_data[acc]['norm_edp']
        
        # 最后一行是平均值
        norm_cycle[n_actual_models, j] = np.mean(normalized_data[acc]['norm_latency'])
        norm_energy_on[n_actual_models, j] = np.mean(normalized_data[acc]['norm_on_chip'])
        norm_energy_off[n_actual_models, j] = np.mean(normalized_data[acc]['norm_off_chip'])
        norm_edp[n_actual_models, j] = np.mean(normalized_data[acc]['norm_edp'])
    
    # ==============================
    #  Plotting
    # ==============================
    energy_names = ["On-Chip Energy", "Off-Chip Energy"]
    # Use hatch to distinguish On-chip/Off-chip (instead of color)
    energy_hatches = ['///', '\\\\\\']  # On-chip用斜线，Off-chip用反斜线
    bar_width = 0.18  # 柱子宽度（再增加一点）
    bar_spacing = 1.3  # 组内柱子间距系数（增加组内间距）
    x_base = np.arange(len(models)) * 1.3  # 增加模型之间的间距
    
    # Create 3 subplots
    fig = plt.figure(figsize=(16, 12))  # 增加figure高度以容纳3个子图
    gs = gridspec.GridSpec(3, 1, height_ratios=[1, 1, 1], hspace=0.6)  # 3行1列，增大间距确保不重叠
    axes = [plt.subplot(gs[i]) for i in range(3)]
    
    # -------------------------------------------------------
    # (1) Latency plot
    for j, acc in enumerate(accelerators):
        x = x_base + (j - len(accelerators)//2) * bar_width * bar_spacing
        bars = axes[0].bar(x, norm_cycle[:, j], bar_width, label=acc, 
                           color=acc_colors.get(acc, '#999999'), 
                           edgecolor='black', linewidth=0.8,
                           alpha=0.90, zorder=3)
        
        # Add labels
        for i, (bar, val) in enumerate(zip(bars, norm_cycle[:, j])):
            if val > 0.05:  # 只显示足够大的值
                lbl = f"{val:.2f}" if math.isclose(val, 1.0, rel_tol=1e-9, abs_tol=1e-9) else f"{val:.3f}"
                axes[0].text(bar.get_x() + bar.get_width()/2, val + 0.02, 
                            lbl, ha='center', va='bottom', 
                            fontsize=8, fontweight='bold', 
                            color=acc_colors.get(acc, '#999999'),
                            rotation=90)
    
    axes[0].set_ylabel("Normalized Latency", fontweight='bold')
    max_latency = norm_cycle.max()
    axes[0].set_ylim(0, max(1.1, max_latency * 1.15))
    axes[0].set_xticks(x_base)
    axes[0].set_xticklabels(models, rotation=25, ha='right', fontweight='bold')
    
    # Highlight Average tick (teal)
    labels = axes[0].get_xticklabels()
    labels[-1].set_color('#4FB0A9')  # 青绿主色强调
    labels[-1].set_weight('extra bold')
    
    # X label
    axes[0].set_xlabel("(a) Inference Latency Comparison", fontweight='bold', fontsize=12)
    
    # Legend: transparent background
    axes[0].legend(accelerators, ncol=len(accelerators), bbox_to_anchor=(0.5, 1.15),
                   loc='upper center', frameon=True, fancybox=False, shadow=False,
                   framealpha=0.9, edgecolor='#CCCCCC')
    
    # -------------------------------------------------------
    # (2) Energy (stacked)
    for j, acc in enumerate(accelerators):
        x = x_base + (j - len(accelerators)//2) * bar_width * bar_spacing
        
        # On-chip部分（底部）- 使用加速器颜色 + 黑色斜线图案（黑色边框）
        bars_on = axes[1].bar(x, norm_energy_on[:, j], bar_width,
                              color=acc_colors.get(acc, '#999999'), 
                              edgecolor='black', 
                              linewidth=0.8, alpha=0.75, 
                              hatch=energy_hatches[0], zorder=3)
        
        # Off-chip部分（堆叠在上面）- 使用加速器颜色 + 黑色反斜线图案（黑色边框）
        bars_off = axes[1].bar(x, norm_energy_off[:, j], bar_width,
                               bottom=norm_energy_on[:, j],
                               color=acc_colors.get(acc, '#999999'), 
                               edgecolor='black', 
                               linewidth=0.8, alpha=0.45,
                               hatch=energy_hatches[1], zorder=3)
        
        # Add labels - show total energy only
        for i, (bar_on, bar_off, val_on, val_off) in enumerate(zip(
            bars_on, bars_off, norm_energy_on[:, j], norm_energy_off[:, j])):
            total = val_on + val_off
            
            # Total energy label
            total_energy = val_on + val_off
            lbl_total = f"{total_energy:.2f}" if math.isclose(total_energy, 1.0, rel_tol=1e-9, abs_tol=1e-9) else f"{total_energy:.3f}"
            txt_total = axes[1].text(bar_off.get_x() + bar_off.get_width()/2, 
                       total_energy + 0.02, 
                       lbl_total, ha='center', va='bottom',
                       fontsize=7.5, fontweight='bold', 
                       color='#000000',
                       rotation=90)
    
    axes[1].set_ylabel("Normalized Energy", fontweight='bold')
    max_energy = (norm_energy_on + norm_energy_off).max()
    axes[1].set_ylim(0, max(1.15, max_energy * 1.15))
    axes[1].set_xticks(x_base)
    axes[1].set_xticklabels(models, rotation=25, ha='right', fontweight='bold')
    
    # Highlight Average tick (teal)
    labels = axes[1].get_xticklabels()
    labels[-1].set_color('#4FB0A9')  # 青绿主色强调
    labels[-1].set_weight('extra bold')
    
    # X label
    axes[1].set_xlabel("(b) Energy Consumption Breakdown", fontweight='bold', fontsize=12, labelpad=10)
    
    # Custom legend - show hatch patterns
    legend_elements = [
        Patch(facecolor='gray', edgecolor='black', hatch=energy_hatches[0], 
              alpha=0.75, label='On-Chip Energy'),
        Patch(facecolor='gray', edgecolor='black', hatch=energy_hatches[1], 
              alpha=0.45, label='Off-Chip Energy')
    ]
    axes[1].legend(handles=legend_elements, ncol=2, bbox_to_anchor=(0.5, 1.15),
                   loc='upper center', frameon=True, fancybox=False, shadow=False,
                   framealpha=0.9, edgecolor='#CCCCCC')
    
    # -------------------------------------------------------
    # (3) EDP plot
    for j, acc in enumerate(accelerators):
        x = x_base + (j - len(accelerators)//2) * bar_width * bar_spacing
        bars = axes[2].bar(x, norm_edp[:, j], bar_width, label=acc,
                           color=acc_colors.get(acc, '#999999'), 
                           edgecolor='black', linewidth=0.8,
                           alpha=0.90, zorder=3)
        
        # Add labels
        for i, (bar, val) in enumerate(zip(bars, norm_edp[:, j])):
            if val > 0.05:  # 只显示足够大的值
                lbl = f"{val:.2f}" if math.isclose(val, 1.0, rel_tol=1e-9, abs_tol=1e-9) else f"{val:.3f}"
                axes[2].text(bar.get_x() + bar.get_width()/2, val + 0.02, 
                            lbl, ha='center', va='bottom', 
                            fontsize=8, fontweight='bold', 
                            color=acc_colors.get(acc, '#999999'),
                            rotation=90)
    
    axes[2].set_ylabel("Normalized EDP", fontweight='bold')
    max_edp = norm_edp.max()
    axes[2].set_ylim(0, max(1.1, max_edp * 1.15))
    axes[2].set_xticks(x_base)
    axes[2].set_xticklabels(models, rotation=25, ha='right', fontweight='bold')
    
    # Highlight Average tick (teal)
    labels = axes[2].get_xticklabels()
    labels[-1].set_color('#4FB0A9')  # 青绿主色强调
    labels[-1].set_weight('extra bold')
    
    # X label
    axes[2].set_xlabel("(c) Energy-Delay Product (EDP) Comparison", fontweight='bold', fontsize=12)
    
    # Legend
    axes[2].legend(accelerators, ncol=len(accelerators), bbox_to_anchor=(0.5, 1.15),
                   loc='upper center', frameon=True, fancybox=False, shadow=False,
                   framealpha=0.9, edgecolor='#CCCCCC')
    
    # -------------------------------------------------------
    # Styling
    for ax in axes:
        # Add background span for Average section
        avg_pos = x_base[-1]  # Average的位置
        half_group_width = (len(accelerators) * bar_width * bar_spacing) / 2
        ax.axvspan(avg_pos - half_group_width - 0.1, avg_pos + half_group_width + 0.1, 
                   color='#E8E8E8', alpha=0.4, zorder=0)
        
        # Grid
        ax.grid(axis='y', linestyle=':', linewidth=0.8, alpha=0.6, zorder=0, color='#CCCCCC')
        ax.set_axisbelow(True)
        
        # Vertical separators between models (exclude before Average)
        for i in range(1, len(models) - 1):  # 只到倒数第二个位置
            ax.axvline(x_base[i] - x_base[1]/2, color='#DDDDDD', linestyle='-', linewidth=1.2, alpha=0.5, zorder=1)
        
        # Axes spines
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_linewidth(1.5)
        ax.spines['bottom'].set_linewidth(1.5)
        ax.spines['left'].set_color('#444444')
        ax.spines['bottom'].set_color('#444444')
    
    # No suptitle, keep compact
    plt.tight_layout()
    
    # Save figures
    png_file = f'{output_prefix}.png'
    pdf_file = f'{output_prefix}.pdf'
    plt.savefig(png_file, dpi=400, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.savefig(pdf_file, bbox_inches='tight', facecolor='white', edgecolor='none')
    
    print("\n" + "="*60)
    print("✅ Figures saved:")
    print(f"   📊 PNG格式 (400 DPI): {png_file}")
    print(f"   📄 PDF矢量图: {pdf_file}")
    print("="*60)


# ==============================
#  Main
# ==============================
if __name__ == '__main__':
    # Resolve log directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_log_dir = os.path.join(os.path.dirname(script_dir), 'log')

    # Args: select bit width and whether to include scale overhead
    parser = argparse.ArgumentParser(description='Auto plot metrics (with EDP) from logs with selectable config')
    parser.add_argument('--bits', choices=['32', '64'], default='64', help='Select bit width: 32 or 64')
    parser.add_argument('--scale', choices=['w', 'wo'], default='wo', help='Include scale overhead: w(with) or wo(without)')
    parser.add_argument('--log-dir', default=None, help='Specify log dir to override bits/scale combo')
    args = parser.parse_args()

    # Resolve target log directory
    if args.log_dir is not None:
        log_dir = args.log_dir
    else:
        subdir = f"log_{args.bits}_{'w_scale' if args.scale == 'w' else 'wo_scale'}"
        candidate = os.path.join(base_log_dir, subdir)
        log_dir = candidate if os.path.isdir(candidate) else base_log_dir
    
    print("="*60)
    print("🚀 Start reading logs and generating plots (with EDP)")
    print("="*60)
    print(f"📁 Log dir: {log_dir}\n")
    
    # 加载所有log数据
    data = load_all_logs(log_dir)
    
    if not data:
        print("❌ Error: no data loaded")
        exit(1)
    
    print(f"\n📊 Loaded {len(data)} accelerators\n")
    
    # 归一化数据
    print("🔄 Normalizing data...")
    normalized_data = normalize_data(data)
    
    # 绘制图表（包含EDP）
    print("🎨 Generating plots (with EDP)...\n")
    output_prefix = os.path.join(script_dir, 'auto_hw_metrics_edp')
    plot_metrics_with_edp(normalized_data, output_prefix)
    
    print("\n✨ Done!")

