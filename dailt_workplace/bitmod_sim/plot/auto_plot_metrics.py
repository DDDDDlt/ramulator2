import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端，适合无GUI环境

import os
import re
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patheffects
from matplotlib import gridspec
from matplotlib.patches import Patch

# ==============================
#  高级样式设置 - 与硬件框图统一风格
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
plt.rcParams['axes.facecolor'] = '#FAFAFA'  # 与硬件图统一的浅灰背景
plt.rcParams['axes.labelcolor'] = '#444444'  # 深灰坐标轴文字
plt.rcParams['xtick.color'] = '#444444'
plt.rcParams['ytick.color'] = '#444444'
plt.rcParams['text.color'] = '#444444'
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['grid.alpha'] = 0.5
plt.rcParams['grid.linestyle'] = ':'
plt.rcParams['grid.color'] = '#CCCCCC'

# ==============================
#  解析log文件
# ==============================
def parse_log_file(log_path):
    """
    解析单个log文件，提取latency和energy数据
    返回: (latency_list, on_chip_energy_list, off_chip_energy_list, accelerator_name)
    """
    with open(log_path, 'r') as f:
        content = f.read()
    
    # 提取accelerator名称（第一行）
    first_line = content.split('\n')[0]
    acc_name_match = re.search(r'Accelerator:\s+(.+)', first_line)
    accelerator_name = acc_name_match.group(1) if acc_name_match else "Unknown"
    
    # 提取Summary部分的Latency数据
    latency_match = re.search(r'Latency \(cycles\):\s*\[([^\]]+)\]', content)
    if not latency_match:
        print(f"警告: 无法在{log_path}中找到Latency数据")
        return None, None, None, accelerator_name
    
    latency_str = latency_match.group(1)
    latency_list = [float(x.strip()) for x in latency_str.split(',')]
    
    # 提取Summary部分的Energy数据
    # 格式: Energy [On-chip, Total] (mJ): [[on1, total1], [on2, total2], ...]
    energy_match = re.search(r'Energy \[On-chip, Total\] \(mJ\):\s*(\[\[.+?\]\])', content)
    if not energy_match:
        print(f"警告: 无法在{log_path}中找到Energy数据")
        return latency_list, None, None, accelerator_name
    
    energy_str = energy_match.group(1)
    # 解析嵌套列表 [[on1, total1], [on2, total2], ...]
    # 使用更精确的正则表达式匹配每个[数字, 数字]对
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
    
    # 打印解析结果
    print(f"\n{'='*70}")
    print(f"📄 文件: {os.path.basename(log_path)}")
    print(f"🏷️  加速器: {accelerator_name}")
    print(f"⏱️  Latency (cycles): {latency_list}")
    print(f"⚡ On-chip Energy (mJ): {on_chip_energy}")
    print(f"💾 Off-chip Energy (mJ): {off_chip_energy}")
    print(f"📊 Total Energy (mJ): {total_energy}")
    print(f"{'='*70}")
    
    return latency_list, on_chip_energy, off_chip_energy, accelerator_name


def load_all_logs(log_dir):
    """
    加载所有log文件的数据
    返回: dict with keys as accelerator names
    """
    log_files = {
        'Baseline': 'test_baseline.log',
        'FlexPosit': 'test_mixposit.log',
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
                print(f"✅ 成功加载: {log_file} ({acc_name})")
        else:
            print(f"⚠️  未找到文件: {log_path}")
    
    return data


def normalize_data(data, baseline_key='Baseline'):
    """
    将所有数据归一化到baseline（逐模型归一化）
    每个模型独立归一化，使得每个模型的baseline total energy = 1.0
    """
    if baseline_key not in data:
        print(f"警告: 未找到baseline数据，使用第一个加速器作为baseline")
        baseline_key = list(data.keys())[0]
    
    baseline_latency = np.array(data[baseline_key]['latency'])
    baseline_on_chip = np.array(data[baseline_key]['on_chip_energy'])
    baseline_off_chip = np.array(data[baseline_key]['off_chip_energy'])
    baseline_total_energy = baseline_on_chip + baseline_off_chip  # 每个模型的baseline总能量
    
    normalized_data = {}
    
    print("\n" + "="*70)
    print("🔄 开始归一化数据（相对于Baseline，逐模型独立归一化）")
    print("="*70)
    
    model_names = ["GPT2-L", "GPT2-XL", "Phi-2", "OPT-2.7B", "Llama2-7B"]
    
    for acc_key, acc_data in data.items():
        acc_on_chip = np.array(acc_data['on_chip_energy'])
        acc_off_chip = np.array(acc_data['off_chip_energy'])
        acc_latency = np.array(acc_data['latency'])
        
        # Latency归一化：每个模型独立归一化
        norm_latency = acc_latency / baseline_latency
        
        # Energy归一化：每个模型独立归一化（逐元素除法）
        norm_on_chip = acc_on_chip / baseline_total_energy
        norm_off_chip = acc_off_chip / baseline_total_energy
        
        normalized_data[acc_key] = {
            'norm_latency': norm_latency,
            'norm_on_chip': norm_on_chip,
            'norm_off_chip': norm_off_chip,
            'full_name': acc_data['full_name']
        }
        
        # 打印归一化后的结果（逐模型显示）
        print(f"\n📊 {acc_key} ({acc_data['full_name']})")
        for i, model_name in enumerate(model_names):
            total_norm = norm_on_chip[i] + norm_off_chip[i]
            print(f"   {model_name:12s}: Latency={norm_latency[i]:.3f}, "
                  f"On-chip={norm_on_chip[i]:.3f}, Off-chip={norm_off_chip[i]:.3f}, "
                  f"Total={total_norm:.3f}")
    
    print("\n" + "="*70)
    
    return normalized_data


# ==============================
#  绘图函数
# ==============================
def plot_metrics(normalized_data, output_prefix='auto_hw_metrics'):
    """
    绘制latency和energy对比图
    """
    # 模型名称（5个模型）+ 平均值
    models = [
        "GPT2-L", "GPT2-XL", "Phi-2",
        "OPT-2.7B", "Llama2-7B", "Average"
    ]
    
    # 加速器顺序（可以根据需要调整）
    accelerator_order = ['FlexPosit', 'BitMod', 'Olive', 'Baseline']
    accelerators = [acc for acc in accelerator_order if acc in normalized_data]
    
    # 与硬件框图统一的配色方案（青绿主调 + 橙色强调 + 灰色基线）
    acc_colors = {
        'FlexPosit': '#4FB0A9',   # 青绿主色（与硬件图核心模块一致）
        'BitMod': '#F4A261',     # 暖橙色（与Bit-serial路径呼应）
        'Olive': '#457B9D',      # 深青蓝（稳重对比）
        'Baseline': '#BDBDBD'    # 浅灰（代表参考基线）
    }
    
    # 准备数据矩阵（包含平均值）
    n_models = len(models)  # 包含Average
    n_accs = len(accelerators)
    n_actual_models = n_models - 1  # 实际模型数量（不含Average）
    
    norm_cycle = np.zeros((n_models, n_accs))
    norm_energy_on = np.zeros((n_models, n_accs))
    norm_energy_off = np.zeros((n_models, n_accs))
    
    for j, acc in enumerate(accelerators):
        # 前n_actual_models行是实际数据
        norm_cycle[:n_actual_models, j] = normalized_data[acc]['norm_latency']
        norm_energy_on[:n_actual_models, j] = normalized_data[acc]['norm_on_chip']
        norm_energy_off[:n_actual_models, j] = normalized_data[acc]['norm_off_chip']
        
        # 最后一行是平均值
        norm_cycle[n_actual_models, j] = np.mean(normalized_data[acc]['norm_latency'])
        norm_energy_on[n_actual_models, j] = np.mean(normalized_data[acc]['norm_on_chip'])
        norm_energy_off[n_actual_models, j] = np.mean(normalized_data[acc]['norm_off_chip'])
    
    # ==============================
    #  绘图部分
    # ==============================
    energy_names = ["On-Chip Energy", "Off-Chip Energy"]
    # 使用斜线图案区分On-chip和Off-chip（而不是颜色）
    energy_hatches = ['///', '\\\\\\']  # On-chip用斜线，Off-chip用反斜线
    bar_width = 0.18  # 柱子宽度（再增加一点）
    bar_spacing = 1.3  # 组内柱子间距系数（增加组内间距）
    x_base = np.arange(len(models)) * 1.3  # 增加模型之间的间距
    
    fig = plt.figure(figsize=(16, 8))  # 增加figure宽度
    gs = gridspec.GridSpec(2, 1, height_ratios=[1, 1], hspace=0.55)  # 增加子图间距
    axes = [plt.subplot(gs[i]) for i in range(2)]
    
    # -------------------------------------------------------
    # (1) Latency 图 - 与硬件图统一配色（黑色边框）
    for j, acc in enumerate(accelerators):
        x = x_base + (j - len(accelerators)//2) * bar_width * bar_spacing  # 使用bar_spacing增加组内间距
        bars = axes[0].bar(x, norm_cycle[:, j], bar_width, label=acc, 
                           color=acc_colors.get(acc, '#999999'), 
                           edgecolor='black', linewidth=0.8,
                           alpha=0.90, zorder=3)
        
        # 添加数值标签（竖向显示避免重叠）
        for i, (bar, val) in enumerate(zip(bars, norm_cycle[:, j])):
            if val > 0.05:  # 只显示足够大的值
                axes[0].text(bar.get_x() + bar.get_width()/2, val + 0.02, 
                            f'{val:.2f}', ha='center', va='bottom', 
                            fontsize=8, fontweight='bold', 
                            color=acc_colors.get(acc, '#999999'),
                            rotation=90)
    
    axes[0].set_ylabel("Normalized Latency", fontweight='bold')
    max_latency = norm_cycle.max()
    axes[0].set_ylim(0, max(1.1, max_latency * 1.15))  # 增加y轴范围给图例留空间
    axes[0].set_xticks(x_base)
    axes[0].set_xticklabels(models, rotation=25, ha='right', fontweight='bold')
    
    # 高亮Average标签（与硬件图统一：青绿色强调）
    labels = axes[0].get_xticklabels()
    labels[-1].set_color('#4FB0A9')  # 青绿主色强调
    labels[-1].set_weight('extra bold')
    
    # 添加标题在图下方
    axes[0].set_xlabel("(a) Inference Latency Comparison", fontweight='bold', fontsize=12)
    
    # 图例：透明背景、无阴影、小字体
    axes[0].legend(accelerators, ncol=len(accelerators), bbox_to_anchor=(0.5, 1.15),
                   loc='upper center', frameon=True, fancybox=False, shadow=False,
                   framealpha=0.9, edgecolor='#CCCCCC')
    
    # -------------------------------------------------------
    # (2) Energy 图（堆叠柱状图）- 颜色统一为加速器颜色，用图案区分On-chip/Off-chip
    for j, acc in enumerate(accelerators):
        x = x_base + (j - len(accelerators)//2) * bar_width * bar_spacing  # 使用bar_spacing增加组内间距
        
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
        
        # 添加标签 - 只在柱子顶部显示total energy
        for i, (bar_on, bar_off, val_on, val_off) in enumerate(zip(
            bars_on, bars_off, norm_energy_on[:, j], norm_energy_off[:, j])):
            total = val_on + val_off
            
            # Total energy标签（在柱子顶部，竖向显示，黑色）
            total_energy = val_on + val_off
            txt_total = axes[1].text(bar_off.get_x() + bar_off.get_width()/2, 
                       total_energy + 0.02, 
                       f'{total_energy:.2f}', ha='center', va='bottom',
                       fontsize=7.5, fontweight='bold', 
                       color='#000000',
                       rotation=90)
    
    axes[1].set_ylabel("Normalized Energy", fontweight='bold')
    max_energy = (norm_energy_on + norm_energy_off).max()
    axes[1].set_ylim(0, max(1.15, max_energy * 1.15))  # 增加y轴范围给图例留空间
    axes[1].set_xticks(x_base)
    axes[1].set_xticklabels(models, rotation=25, ha='right', fontweight='bold')
    
    # 高亮Average标签（与硬件图统一：青绿色强调）
    labels = axes[1].get_xticklabels()
    labels[-1].set_color('#4FB0A9')  # 青绿主色强调
    labels[-1].set_weight('extra bold')
    
    # 添加标题在图下方
    axes[1].set_xlabel("(b) Energy Consumption Breakdown", fontweight='bold', fontsize=12, labelpad=10)
    
    # 创建自定义图例 - 显示黑色斜线图案
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
    # 高级美化
    for ax in axes:
        # 为Average区域添加背景色（学术风格：淡灰色背景）
        avg_pos = x_base[-1]  # Average的位置
        half_group_width = (len(accelerators) * bar_width * bar_spacing) / 2
        ax.axvspan(avg_pos - half_group_width - 0.1, avg_pos + half_group_width + 0.1, 
                   color='#E8E8E8', alpha=0.4, zorder=0)
        
        # 网格线设置
        ax.grid(axis='y', linestyle=':', linewidth=0.8, alpha=0.6, zorder=0, color='#CCCCCC')
        ax.set_axisbelow(True)
        
        # 添加垂直分隔线（区分不同模型）- 不包括Average前的虚线
        for i in range(1, len(models) - 1):  # 只到倒数第二个位置
            ax.axvline(x_base[i] - x_base[1]/2, color='#DDDDDD', linestyle='-', linewidth=1.2, alpha=0.5, zorder=1)
        
        # 美化边框（与硬件图统一）
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_linewidth(1.5)
        ax.spines['bottom'].set_linewidth(1.5)
        ax.spines['left'].set_color('#444444')
        ax.spines['bottom'].set_color('#444444')
    
    # 添加总标题（与硬件图统一风格）
    fig.suptitle('Performance Evaluation of LLM Inference Accelerators', 
                 fontsize=15, fontweight='bold', y=0.98, color='#444444')
    
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    # 保存图像
    png_file = f'{output_prefix}.png'
    pdf_file = f'{output_prefix}.pdf'
    plt.savefig(png_file, dpi=400, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.savefig(pdf_file, bbox_inches='tight', facecolor='white', edgecolor='none')
    
    print("\n" + "="*60)
    print("✅ 高清图像已保存:")
    print(f"   📊 PNG格式 (400 DPI): {png_file}")
    print(f"   📄 PDF矢量图: {pdf_file}")
    print("="*60)


# ==============================
#  主函数
# ==============================
if __name__ == '__main__':
    # 获取脚本所在目录的上级目录中的log文件夹
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(os.path.dirname(script_dir), 'log')
    
    print("="*60)
    print("🚀 开始自动读取log文件并生成图表")
    print("="*60)
    print(f"📁 Log目录: {log_dir}\n")
    
    # 加载所有log数据
    data = load_all_logs(log_dir)
    
    if not data:
        print("❌ 错误: 未能加载任何数据")
        exit(1)
    
    print(f"\n📊 成功加载 {len(data)} 个加速器的数据\n")
    
    # 归一化数据
    print("🔄 正在归一化数据...")
    normalized_data = normalize_data(data)
    
    # 绘制图表
    print("🎨 正在生成图表...\n")
    output_prefix = os.path.join(script_dir, 'auto_hw_metrics')
    plot_metrics(normalized_data, output_prefix)
    
    print("\n✨ 完成!")

