## Roofline 使用说明

### 目录结构
- `run_roofline.sh`：一键执行"维度扫描 → 解析日志 → 绘图（1/cycle）"。
- `run_roofline_mac.sh`：一键"统计 generation MAC → 解析 → 绘图（MAC/cycle，含 RAW 与 Range 两套）"。
- `parse_to_csv.py`：解析 `logs/` 下的日志为 CSV（面积/能量/周期等）。
- `plot_roofline.py`：从 CSV 读取数据并绘图（支持多种归一化、1/cycle 或 MAC/cycle）。
- `compute_model_macs.py`：基于模型形状计算每模型的总 MAC（与加速器无关，支持 generation）。
- `tmp/plot_isoarea_from_csv.py`：参考 `tmp/roofline.py` 风格，从 CSV 画三条曲线并自动找交点/竖线/阴影。
- `logs/`：维度扫描产生的日志目录（输入）。
- `plots/`、`plots_mac_raw/`、`plots_mac_range/`：绘图输出目录（输出）。
- `roofline_results.csv`：解析后的汇总 CSV（输出）。
- `model_macs_gen.csv`：由 `compute_model_macs.py` 生成的 generation 模式 MAC 映射（可选）。

### 快速开始（推荐）
```bash
# 一键：扫描 + 解析 + 绘图（默认：y=16，x=4..80，步长=4，绘制 RAW 图并限制 x∈[0.9, 2.5]）
bash roofline/run_roofline.sh
```

### 仅解析与绘图（不重跑扫描）
```bash
# 1) 解析已有日志 → CSV
python3 roofline/parse_to_csv.py \
  --log-dir roofline/logs \
  --out roofline/roofline_results.csv

# 2) 绘图（选择一种归一化模式，见下文）
python3 roofline/plot_roofline.py \
  --csv roofline/roofline_results.csv \
  --out-dir roofline/plots \
  --normalize no
```

### 日志命名要求
- 文件名形如：`test_<accelerator>_x{X}_y{Y}.log`，例如：`test_flexposit_x32_y16.log`
- 当前支持的 `<accelerator>`：`baseline`、`olive`、`flexposit`、`bitmod`
- 日志需放在 `roofline/logs/` 目录下（或通过 `--log-dir` 指定）

### 横纵坐标定义
- **横轴**：
  - 原始模式：PE 阵列面积（单位：mm²）
  - 归一化模式（`--normalize-y`）：Normalized Compute Intensity
- **纵轴（Throughput）**：
  - 模式一：`1 / total_cycle`
  - 模式二：`total_macs / total_cycle`（MAC/cycle，需要提供每模型的总 MAC）

### 三种绘图模式（--normalize）
- **no（原始 RAW）**
  - 横轴：PE 阵列面积（mm²）
  - 纵轴：Throughput（1/cycle 或 MAC/cycle）
  - 示例（1/cycle）：
    ```bash
    python3 roofline/plot_roofline.py --csv roofline/roofline_results.csv --out-dir roofline/plots --normalize no
    ```
  - 示例（MAC/cycle）：
    ```bash
    # 先计算 generation MAC（可重用）
    python3 roofline/compute_model_macs.py --is_generation --out roofline/model_macs_gen.csv
    # 使用 MAC/cycle 作图（RAW）
    python3 roofline/plot_roofline.py \
      --csv roofline/roofline_results.csv \
      --macs-csv roofline/model_macs_gen.csv \
      --out-dir roofline/plots_mac_raw \
      --throughput mac --normalize no
    ```

- **baseline（相对 Baseline 归一化，等价于旧的 `--normalize yes`）**
  - 基于同一模型、同一 `pe_x` 的 Baseline 点做比值：
    - X：PE 面积 / Baseline 面积
    - Y：Throughput / Baseline Throughput（先取倒数，再归一化）
  - 推荐横轴范围（可选）：`--x-min 0.9 --x-max 2.5`
  - 示例：
    ```bash
    python3 roofline/plot_roofline.py --csv roofline/roofline_results.csv --out-dir roofline/plots --normalize baseline --x-min 0.9 --x-max 2.5
    ```

- **range（基于范围的 Min-Max 归一化，保持曲线形状）**
  - 对每个模型独立，在"所有加速器×所有 `pe_x` 点"的集合上做 min-max 到 [0,1]：
    - X： (PE 面积 - Xmin) / (Xmax - Xmin)
    - Y： (Throughput - Ymin) / (Ymax - Ymin)
  - 建议横轴范围：`--x-min 0.0 --x-max 1.0`
  - 示例：
    ```bash
    # 1/cycle
    python3 roofline/plot_roofline.py --csv roofline/roofline_results.csv --out-dir roofline/plots \
      --normalize range --x-min 0.0 --x-max 1.0
    # MAC/cycle
    python3 roofline/plot_roofline.py --csv roofline/roofline_results.csv --macs-csv roofline/model_macs_gen.csv \
      --out-dir roofline/plots_mac_range --throughput mac --normalize range --x-min 0.0 --x-max 1.0
    ```

### 纵坐标归一化（--normalize-y）

**功能说明**：
- 将纵坐标（吞吐量）归一化到 [0, 1] 范围
- 归一化方式：使用所有加速器中的**全局最大 y 值**进行归一化
- 全局最大值将被归一化为 1.0，其他值按比例缩放

**绘图特性**：
- 左侧：所有曲线从原点 (0, 0) 开始连接
- 右侧：所有曲线水平延长到图的右边界（保持最后一个点的 y 值）
- 纵坐标范围：固定显示为 [0, 1.05]（留出空间避免 y=1 的线与上边框重叠）
- 横轴标签：自动切换为 "Normalized Compute Intensity"
- 纵轴标签：自动添加 "Normalized" 前缀

**使用示例**：
```bash
# 基本用法（1/cycle + 纵坐标归一化）
python3 roofline/plot_roofline.py \
  --csv roofline/roofline_results.csv \
  --out-dir roofline/plots \
  --normalize no \
  --normalize-y

# MAC/cycle 模式 + 纵坐标归一化
python3 roofline/plot_roofline.py \
  --csv roofline/roofline_results.csv \
  --macs-csv roofline/model_macs_gen.csv \
  --out-dir roofline/plots_mac_raw \
  --throughput mac \
  --normalize no \
  --normalize-y

# 指定横坐标范围
python3 roofline/plot_roofline.py \
  --csv roofline/roofline_results.csv \
  --macs-csv roofline/model_macs_gen.csv \
  --out-dir roofline/plots_mac_raw \
  --throughput mac \
  --normalize no \
  --normalize-y \
  --x-min 0.9 \
  --x-max 2.5
```

**输出文件**：
- 启用 `--normalize-y` 后，输出文件名包含 `_raw_normalized` 后缀
- 例如：`roofline_model_<model>_raw_normalized.png`、`roofline_average_raw_normalized.png`

### 常用参数
- 维度扫描（仅 `run_roofline.sh`）：
  - `--y <INT>`、`--x-start <INT>`、`--x-end <INT>`、`--x-step <INT>`
- 绘图：
  - `--normalize {no|baseline|range}`：横坐标归一化模式
  - `--normalize-y`：纵坐标归一化（独立开关，可与 `--normalize` 组合使用）
  - `--throughput {cycle|mac}`：吞吐定义（1/cycle 或 MAC/cycle）
  - `--macs-csv <PATH>`：外部提供每模型 `total_macs` 的 CSV（建议使用 generation 的 `model_macs_gen.csv`）
  - `--x-min <FLOAT>`、`--x-max <FLOAT>`：横轴显示范围（原始模式可不设，范围归一化建议 [0,1]）

### 注意事项
- Baseline 归一化需要同一模型、同一 `pe_x` 下存在 Baseline 日志，否则该点会被跳过。
- 日志中 `Total Cycle` 可能以浮点形式出现（例如 `8,366,099.200000006`），解析器已支持。
- 为增强敏感度，脚本会打印并解析 6 位小数的面积；绘图横轴采用"PE 阵列面积"或"Normalized Compute Intensity"（取决于是否启用 `--normalize-y`）。
- 绘图美化：加粗圆角折线、浅色描边、放大标题/坐标轴字体；在每模型图中自动计算并绘制 FlexPosit–Olive 与 BitMoD–FlexPosit 的交点竖虚线（两线外侧区域灰色填充）。
- 纵坐标归一化模式下，所有曲线左侧连接原点，右侧水平延长，形成典型的 Roofline 曲线样式。

### 一键（MAC/cycle）
```bash
bash roofline/run_roofline_mac.sh
# 生成：
# - roofline/model_macs_gen.csv
# - roofline/roofline_results.csv
# - roofline/plots_mac_raw/* （RAW, MAC/cycle）
# - roofline/plots_mac_raw/*_raw_normalized.png （RAW + 纵坐标归一化, MAC/cycle）
# - roofline/plots_mac_range/* （Range, MAC/cycle）
```

### Iso-Area 风格（参考 tmp/roofline.py）
```bash
python3 roofline/tmp/plot_isoarea_from_csv.py \
  --csv roofline/roofline_results.csv \
  --macs-csv roofline/model_macs_gen.csv \
  --out-dir roofline/tmp \
  --throughput mac
# 输出：tmp/isoarea_<model>.png/pdf，自动插值三条曲线与交点竖线、并可视化交点
```

### 依赖环境
- Python 3
- `numpy`、`matplotlib`
