# FlexPosit — Figure Reproduction Artifact

Self-contained artifact to reproduce the two hardware-evaluation figures from the FlexPosit
paper:

- **Figure 11** — Normalized latency / energy / EDP / energy-efficiency across accelerators
  (bar chart, 9 models + geo/arith-mean average).
- **Figure 12** — Perplexity vs Normalized-EDP Pareto plot on WikiText-2 (GPT2-XL, Phi-2).

Everything needed to regenerate both figures is bundled here: the parsed hardware-metric logs,
the consolidated PPL/EDP data, and the plotting scripts. **No simulator run is required** — the
figures replot deterministically from the committed data. The full simulator that produced the
data lives in `../flexposit_workplace/flexposit_sim/` (see *Data provenance* below).

## Requirements

```
python >= 3.8
matplotlib
numpy        # Figure 11 only
```
```bash
pip install matplotlib numpy
```

## Reproduce

```bash
# Figure 11 -> fig11_hardware_metrics/fig11_hardware_metrics.{png,pdf}
python fig11_hardware_metrics/plot_fig11.py

# Figure 12 -> fig12_ppl_vs_edp/fig12_ppl_vs_edp.{png,pdf}
python fig12_ppl_vs_edp/plot_fig12.py
```

## Directory layout

```
flexposit_artifact/
├── README.md                         # this file
├── fig11_hardware_metrics/
│   ├── plot_fig11.py                 # standalone plotter (reads ./data, writes ./fig11_*)
│   ├── data/                         # one parsed log per accelerator
│   │   ├── test_baseline.log         #   FP16 baseline
│   │   ├── test_flexposit.log        #   FlexPosit (PEB precision)
│   │   ├── test_bitmod.log           #   BitMoD (4b)
│   │   ├── test_olive.log            #   OliVe (a8w8)
│   │   └── test_fp16_mxfp8.log       #   FP16-MXFP8 (8b weight)
│   └── fig11_hardware_metrics.{png,pdf}
└── fig12_ppl_vs_edp/
    ├── plot_fig12.py                 # standalone plotter (reads ./ppl_edp_data.csv)
    ├── ppl_edp_data.csv              # PPL + EDP for every point in Figure 12
    └── fig12_ppl_vs_edp.{png,pdf}
```

## Evaluated designs (iso-area, decode / generation mode)

All accelerators are sized to an **iso-area** budget equivalent to a 32×16 FlexPosit PE array,
evaluated in autoregressive decode mode at context length 256, with DRAM modeled by Ramulator
(DDR4-3200AC preset).

| Design        | Act. | Weight            | Datapath    | PE array | Per-PE area (µm²) |
|---------------|:----:|:------------------|:------------|:--------:|:-----------------:|
| FP16 Baseline | 16b  | 16b               | parallel    | 7×16     | 1039.6            |
| **FlexPosit** | 16b  | **PEB, 4.1–5.0b** | bit-serial  | 32×16    | 243               |
| BitMoD        | 16b  | 4b                | bit-serial  | 8×16     | 777               |
| OliVe (a8w8)  | 8b   | 8b                | parallel    | 38×16    | 214.6             |
| FP16-MXFP8    | 16b  | 8b (MXFP8)        | parallel    | 9×16     | 768.0             |

**FlexPosit PEB precision per model** (minimum precision achieving iso-PPL with BitMoD's 4b):
GPT2-L 4.2, GPT2-XL 4.1, Phi-2 4.5, OPT-2.7B 4.1, LLaMA2-7B 4.6, Qwen2.5-7B 4.4,
Mistral-7B 4.6, DeepSeek-7B 4.3, Qwen2.5-14B 5.0.

## Figure 11 — normalized hardware metrics

Four panels (latency, energy, EDP, energy-efficiency), each normalized per model to the FP16
baseline (= 1.00). Average across the 9 models:

| Accelerator | Norm. Latency | Norm. Energy | Norm. EDP | Norm. Energy-Eff. |
|-------------|:-------------:|:------------:|:---------:|:-----------------:|
| **FlexPosit** | **0.245** | **0.248** | **0.061** | **4.05×** |
| BitMoD        | 0.439     | 0.305     | 0.134     | 3.29× |
| OliVe         | 0.357     | 0.507     | 0.181     | 1.97× |
| FP16-MXFP8    | 0.779     | 0.637     | 0.496     | 1.57× |
| FP16 Baseline | 1.00      | 1.00      | 1.00      | 1.00× |

FlexPosit delivers the lowest latency/energy/EDP and highest efficiency of all designs.

## Figure 12 — Perplexity vs Normalized-EDP Pareto

For GPT2-XL and Phi-2, FlexPosit is swept over fractional precisions 4.1–5.0b (step 0.1b),
forming a smooth Pareto frontier that occupies the **bottom-left** region (low perplexity and
low EDP) versus the BitMoD and OliVe baselines. EDP is normalized per model to OliVe a8w8 (=1.0).

Two rendering conventions:
- **Green light→dark gradient** encodes increasing FlexPosit precision (4.1b → 5.0b).
- **Flat tail:** the FlexPosit series is drawn as its running-minimum (Pareto) envelope, so higher
  precision never displays *worse* perplexity — it holds at the best value reached.

## Data provenance

- **Perplexity** — WikiText-2 evaluation (paper Table 2). OliVe a8w8 = Table-2 "Channel"
  variant, OliVe a4w4 = "Group"; BitMoD at 4b; FlexPosit swept 4.1–5.0b.
- **Hardware metrics (latency, energy, EDP)** — the Ramulator-backed analytical accelerator model
  in `../flexposit_workplace/flexposit_sim/` (`accelerator.py`, `pe_array.py`,
  `ramulator_dram_sim.py`). Each `data/test_*.log` is the stdout of the corresponding
  `test_<accel>.py --is_generation` run under the iso-area configs above.
  **EDP = latency(cycles) × total_energy(µJ)**; Figure 12's per-point EDP is bundled in
  `ppl_edp_data.csv`.

To regenerate the raw logs from scratch (requires the full simulator + Ramulator build):
```bash
cd ../flexposit_workplace/flexposit_sim
python test_baseline.py    --is_generation > <dir>/test_baseline.log
python test_flexposit.py   --is_generation > <dir>/test_flexposit.log
python test_bitmod.py      --is_generation > <dir>/test_bitmod.log
python test_olive.py       --is_generation > <dir>/test_olive.log
python test_fp16_mxfp8.py  --is_generation > <dir>/test_fp16_mxfp8.log
```
