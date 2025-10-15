import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端，适合无GUI环境

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import gridspec

# ==============================
#  高级样式设置
# ==============================
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Liberation Sans']
plt.rcParams['font.size'] = 11
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 13
plt.rcParams['legend.fontsize'] = 10
plt.rcParams['xtick.labelsize'] = 10
plt.rcParams['ytick.labelsize'] = 10
plt.rcParams['axes.linewidth'] = 1.2
plt.rcParams['axes.edgecolor'] = '#333333'
plt.rcParams['axes.facecolor'] = '#FAFAFA'
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['grid.alpha'] = 0.6
plt.rcParams['grid.linestyle'] = ':'

# ==============================
#  模型和加速器
# ==============================
models = [
    "GPT2-L", "GPT2-XL", "Phi-2",
    "OPT-2.7B", "Yi-6B",
    "Llama2-7B", "Llama3-8B"
]
accelerators = ["FlexPosit", "BitMod", "ANT", "Olive", "Baseline"]

# Nature期刊风格配色
acc_colors = ['#E64B35', '#4DBBD5', '#00A087', '#3C5488', '#F39B7F']

# ==============================
#  (1) Cycle 数据
# ==============================
# 形状: 7模型 × 5加速器
norm_cycle = np.array([
    [0.82, 0.71, 0.35, 0.28, 0.4],   # gpt2-large
    [0.87, 0.68, 0.32, 0.3, 0.42],   # gpt2-xl
    [0.9, 0.7, 0.36, 0.3, 0.45],     # phi-2
    [0.78, 0.6, 0.3, 0.28, 0.38],    # opt-2.7b
    [0.83, 0.63, 0.33, 0.3, 0.4],    # Yi-6B
    [0.8, 0.58, 0.3, 0.25, 0.38],    # Llama-2-7b
    [0.85, 0.6, 0.33, 0.28, 0.4],    # Llama-3-8B
])

# ==============================
#  (2) Energy 数据
# ==============================
# 形状: 7模型 × 5加速器 × 2部分 (On-chip, Off-chip)
norm_energy = np.array([
    # gpt2-large
    [[0.55, 0.45],
     [0.52, 0.48],
     [0.5, 0.5],
     [0.45, 0.55],
     [0.5, 0.5]],
    # gpt2-xl
    [[0.5, 0.5],
     [0.48, 0.52],
     [0.45, 0.55],
     [0.43, 0.57],
     [0.45, 0.55]],
    # phi-2
    [[0.53, 0.47],
     [0.5, 0.5],
     [0.47, 0.53],
     [0.45, 0.55],
     [0.5, 0.5]],
    # opt-2.7b
    [[0.55, 0.45],
     [0.52, 0.48],
     [0.5, 0.5],
     [0.48, 0.52],
     [0.5, 0.5]],
    # Yi-6B
    [[0.5, 0.5],
     [0.47, 0.53],
     [0.45, 0.55],
     [0.43, 0.57],
     [0.45, 0.55]],
    # Llama-2-7b
    [[0.52, 0.48],
     [0.5, 0.5],
     [0.48, 0.52],
     [0.46, 0.54],
     [0.5, 0.5]],
    # Llama-3-8B
    [[0.5, 0.5],
     [0.48, 0.52],
     [0.46, 0.54],
     [0.44, 0.56],
     [0.48, 0.52]],
])

# ==============================
#  绘图部分
# ==============================
energy_names = ["On-Chip Energy", "Off-Chip Energy"]
energy_colors = ["#8ECFC9", "#FFBE7A"]  # 高级莫兰迪色系
bar_width = 0.14
x_base = np.arange(len(models))

fig = plt.figure(figsize=(14, 9))
gs = gridspec.GridSpec(2, 1, height_ratios=[1, 1], hspace=0.4)
axes = [plt.subplot(gs[i]) for i in range(2)]

# -------------------------------------------------------
# (1) Cycle 图
for j, acc in enumerate(accelerators):
    x = x_base + (j - 2) * bar_width
    bars = axes[0].bar(x, norm_cycle[:, j], bar_width, label=acc, 
                       color=acc_colors[j], edgecolor='white', linewidth=1.5,
                       alpha=0.85, zorder=3)
    
    # 添加数值标签（装逼必备）
    for i, (bar, val) in enumerate(zip(bars, norm_cycle[:, j])):
        if val > 0.05:  # 只显示足够大的值
            axes[0].text(bar.get_x() + bar.get_width()/2, val + 0.02, 
                        f'{val:.2f}', ha='center', va='bottom', 
                        fontsize=7.5, fontweight='bold', color=acc_colors[j])

axes[0].set_ylabel("Normalized Latency", fontweight='bold')
axes[0].set_ylim(0, 1.1)
axes[0].set_title("(a) Inference Latency Comparison", fontweight='bold', loc='left', pad=10)
axes[0].legend(accelerators, ncol=5, bbox_to_anchor=(0.5, 1.08),
               loc='upper center', frameon=True, fancybox=True, shadow=True)

# -------------------------------------------------------
# (2) Energy 图（堆叠柱状图）
for j, acc in enumerate(accelerators):
    x = x_base + (j - 2) * bar_width
    bottom = np.zeros(len(models))
    for k in range(2):  # On-Chip / Off-Chip
        bars = axes[1].bar(x, norm_energy[:, j, k], bar_width, bottom=bottom,
                          color=energy_colors[k], edgecolor='white', 
                          linewidth=1.2, alpha=0.9, zorder=3)
        
        # 在堆叠柱中添加百分比标签
        for i, (bar, val) in enumerate(zip(bars, norm_energy[:, j, k])):
            if val > 0.08:  # 只显示足够大的部分
                y_pos = bottom[i] + val/2
                axes[1].text(bar.get_x() + bar.get_width()/2, y_pos, 
                           f'{val*100:.0f}%', ha='center', va='center',
                           fontsize=6.5, fontweight='bold', color='white')
        bottom += norm_energy[:, j, k]

axes[1].set_ylabel("Normalized Energy", fontweight='bold')
axes[1].set_ylim(0, 1.15)
axes[1].set_xticks(x_base)
axes[1].set_xticklabels(models, rotation=25, ha='right', fontweight='bold')
axes[1].set_title("(b) Energy Consumption Breakdown", fontweight='bold', loc='left', pad=10)
axes[1].legend(energy_names, ncol=2, bbox_to_anchor=(0.5, 1.08),
               loc='upper center', frameon=True, fancybox=True, shadow=True)

# -------------------------------------------------------
# 高级美化
for ax in axes:
    # 网格线设置
    ax.grid(axis='y', linestyle=':', linewidth=0.8, alpha=0.6, zorder=0, color='#CCCCCC')
    ax.set_axisbelow(True)
    
    # 添加垂直分隔线（区分不同模型）
    for i in range(1, len(models)):
        ax.axvline(i - 0.5, color='#DDDDDD', linestyle='-', linewidth=1.2, alpha=0.5, zorder=1)
    
    # 美化边框
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_linewidth(1.5)
    ax.spines['bottom'].set_linewidth(1.5)
    ax.spines['left'].set_color('#333333')
    ax.spines['bottom'].set_color('#333333')

# 添加总标题（超级装逼）
fig.suptitle('Hardware Performance Evaluation of LLM Accelerators', 
             fontsize=16, fontweight='bold', y=0.995)

plt.tight_layout(rect=[0, 0, 1, 0.98])
plt.savefig('hw_metrics.png', dpi=400, bbox_inches='tight', facecolor='white', edgecolor='none')
plt.savefig('hw_metrics.pdf', bbox_inches='tight', facecolor='white', edgecolor='none')  # PDF矢量图
print("✅ 高清图像已保存:")
print("   📊 PNG格式 (400 DPI): hw_metrics.png")
print("   📄 PDF矢量图: hw_metrics.pdf")
