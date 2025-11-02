# FlexPosit Simulation and Plotting Guide

This document explains how to run simulations for the accelerators and how to generate plots under `flexposit_sim`.

## Prerequisites

- Python 3.9+
- Ramulator 2.0 binary available (by default expected at `../../ramulator2` relative to this folder). You can override with `RAMULATOR_BIN=/path/to/ramulator2`.
- Dependencies installed (numpy, matplotlib, seaborn if needed). If you use a conda env:

```bash
conda install numpy matplotlib seaborn
```

## Directory layout (key files)

- `test_baseline.py`: Baseline FP16 accelerator
- `test_flexposit.py`: FlexPosit (bit-serial + mixed-precision) accelerator
- `test_olive.py`: OLIVE accelerator
- `test_bitmod.py`: BitMod accelerator
- `run_all_tests.sh`: Batch runner for all accelerators
- `plot/auto_plot_metrics.py`: Plot latency/energy (two subplots)
- `plot/auto_hw_metrics_add_edp.py`: Plot latency/energy/EDP (three subplots)
- `plot/ppl_vs_edp_plot_en.py`, `plot/ppl_vs_edp_multi_model.py`: PPL vs EDP plots
- `log/`: Simulation outputs (text logs)

## 1) Run a single simulation

Each test script accepts `--is_generation` to switch to generation mode.

Examples:

```bash
# Baseline (FP16)
python test_baseline.py --is_generation > ./log/test_baseline.log

# FlexPosit (mixed-precision)
python test_flexposit.py --is_generation > ./log/test_flexposit.log

# OLIVE
python test_olive.py --is_generation > ./log/test_olive.log

# BitMod
python test_bitmod.py --is_generation > ./log/test_bitmod.log
```

Outputs are written into `./log/`. The plotting scripts expect specific filenames:
- FlexPosit: `./log/test_flexposit.log`
- Baseline: `./log/test_baseline.log`
- OLIVE: `./log/test_olive.log`
- BitMod: `./log/test_bitmod.log`

## 2) Run all simulations

```bash
bash run_all_tests.sh --is_generation
```

This will launch all test scripts and save logs under `./log/`.

## 3) Generate plots

There are two primary plotting scripts:

A) Latency + Energy (2 subplots):
```bash
python plot/auto_plot_metrics.py \
  --bits 64 \
  --scale wo \
  --log-dir ./log
```
- Produces: `plot/auto_hw_metrics.png`, `plot/auto_hw_metrics.pdf`
- Reads `test_baseline.log`, `test_flexposit.log`, `test_olive.log`, `test_bitmod.log`

B) Latency + Energy + EDP (3 subplots):
```bash
python plot/auto_hw_metrics_add_edp.py \
  --bits 64 \
  --scale wo \
  --log-dir ./log
```
- Produces: `plot/auto_hw_metrics_edp.png`, `plot/auto_hw_metrics_edp.pdf`
- Reads same log files as above

Notes:
- `--bits` selects 32 or 64 bit mode for path selection; actual reading relies on `--log-dir`.
- `--scale w|wo` toggles whether to include per-group scale overhead; if you pass `--log-dir`, it overrides the default path pattern and reads logs from the given folder.

## 4) PPL vs EDP plots (optional)

If you have PPL vs EDP data prepared in `./log/ppl_vs_edp.log`:

```bash
python plot/ppl_vs_edp_plot_en.py
# or for multiple models
python plot/ppl_vs_edp_multi_model.py
```
- Outputs go into `plot/` by default.

## 5) Troubleshooting

- Ramulator binary not found:
  - Set `export RAMULATOR_BIN=/absolute/path/to/ramulator2`
- No data loaded:
  - Ensure `./log/test_*.log` exist and contain the expected "Latency (cycles): [...]" and "Energy [On-chip, Total] (mJ): [[...]]" lines.
- FlexPosit logs:
  - Make sure your FlexPosit run produced `./log/test_flexposit.log` (the plotting scripts expect this filename).

## 6) Repro tips

- Pin versions of Python packages for reproducibility.
- Save the exact command lines used into the log header for traceability.
- When changing directory names, update hard-coded paths in the plotting scripts (already adapted for `flexposit_workplace`).
