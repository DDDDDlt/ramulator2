# FlexPosit — Figure Reproduction Artifact

**Fully self-contained** artifact for the two hardware-evaluation figures of the FlexPosit paper.
Everything required to reproduce them — the analytical simulator, the Ramulator2 DRAM backend
(prebuilt binary **and** rebuildable source), the CACTI SRAM model, the model-shape configs, the
parsed data, and the plotting scripts — is bundled inside this folder. **If every other directory
in the repository is deleted, this folder still reproduces both figures** (verified by running the
pipeline in an isolated copy with the rest of the repo made unreachable).

- **Figure 11** — Normalized latency / energy / EDP / energy-efficiency across accelerators
  (FlexPosit, BitMoD, OliVe, FP16-MXFP8, FP16 baseline), 9 models + average.
- **Figure 12** — Perplexity vs Normalized-EDP Pareto plot on WikiText-2 (GPT2-XL, Phi-2).

Tested on Linux x86-64.

---

## Quick start

```bash
pip install -r requirements.txt          # numpy + matplotlib

# --- fast path: replot from committed data (seconds) ---
python fig11_hardware_metrics/plot_fig11.py     # -> fig11_hardware_metrics/fig11_hardware_metrics.{png,pdf}
python fig12_ppl_vs_edp/plot_fig12.py           # -> fig12_ppl_vs_edp/fig12_ppl_vs_edp.{png,pdf}

# --- full path: regenerate Figure 11's data from the simulator, then plot ---
bash sim/run_fig11_sim.sh                        # runs the 5 accelerators -> data logs
python fig11_hardware_metrics/plot_fig11.py
```

Two levels of reproduction are supported:

| Level | Command | What runs |
|-------|---------|-----------|
| **Replot** (fast) | `plot_fig11.py`, `plot_fig12.py` | Only matplotlib, from committed logs/CSV |
| **From scratch** (Fig 11) | `sim/run_fig11_sim.sh` → `plot_fig11.py` | Full simulator: CACTI + Ramulator2 subprocess per accelerator → logs → figure |

See *Data provenance* for why Figure 12 is replot-only.

---

## Requirements

- **Python** ≥ 3.8 with `numpy` and `matplotlib` (`pip install -r requirements.txt`). No PyTorch needed.
- **Bundled binaries** (`ramulator/ramulator2`, `ramulator/libramulator.so`, `sim/mem/cacti/cacti`)
  are **Linux x86-64 ELF**, dynamically linked against system `libstdc++`/`libc`. Host floor:
  **glibc ≥ 2.34 and libstdc++ with `GLIBCXX_3.4.30`** (Ubuntu 22.04+ / Debian 12+ / RHEL 9+).
- **Optional** (only to rebuild Ramulator from source): CMake ≥ 3.14, a C++20 compiler (GCC ≥ 10).

---

## Directory layout

```
flexposit_artifact/
├── README.md                       # this file
├── requirements.txt                # numpy, matplotlib
│
├── sim/                            # analytical simulator (RUN test scripts from here)
│   ├── accelerator.py              # accelerator energy/latency/area model
│   ├── pe_array.py                 # PE-array model + per-model shape profiler
│   ├── ramulator_dram_sim.py       # drives the Ramulator2 binary for DRAM cycles/energy
│   ├── test_baseline.py            # FP16 baseline
│   ├── test_flexposit.py           # FlexPosit (PEB precision)
│   ├── test_bitmod.py              # BitMoD (4b)
│   ├── test_olive.py               # OliVe (a8w8)
│   ├── test_fp16_mxfp8.py          # FP16-MXFP8 (8b weight)
│   ├── run_fig11_sim.sh            # regenerate all 5 logs into fig11.../data/
│   └── mem/                        # CACTI-backed SRAM model
│       ├── mem_instance.py, cacti_simulation.py, cacti_config.py, __init__.py
│       ├── cacti/cacti             # CACTI executable (x86-64)
│       ├── cacti/tech_params/*.dat # technology-node parameters (22nm used)
│       └── self_gen/               # writable scratch dir for CACTI config/output
│
├── model_shape_config/             # 9 per-model layer-shape pickles (loaded by pe_array.py)
│
├── ramulator/                      # DRAM simulator (Ramulator 2.0)
│   ├── ramulator2                  # prebuilt executable
│   ├── libramulator.so             # its shared library (co-located; found via LD_LIBRARY_PATH)
│   └── src_build/                  # full source to rebuild from scratch (CMakeLists.txt, src/, ext/)
│
├── fig11_hardware_metrics/
│   ├── plot_fig11.py               # reads ./data/*.log, writes the figure
│   ├── data/test_*.log             # 5 accelerator logs (regenerable by sim/run_fig11_sim.sh)
│   └── fig11_hardware_metrics.{png,pdf}
│
└── fig12_ppl_vs_edp/
    ├── plot_fig12.py               # reads ./ppl_edp_data.csv, writes the figure
    ├── ppl_edp_data.csv            # per-point PPL (external eval) + EDP (simulator)
    └── fig12_ppl_vs_edp.{png,pdf}
```

**Run-directory note:** the `test_*.py` scripts use bare imports (`from accelerator import ...`),
so they must be launched with the working directory set to `sim/`. `sim/run_fig11_sim.sh` handles
this automatically.

---

## Evaluated designs (iso-area, decode / generation mode)

All accelerators are sized to an **iso-area** budget equivalent to a 32×16 FlexPosit PE array,
evaluated in autoregressive decode mode at context length 256, with DRAM modeled by Ramulator2
(DDR4-3200AC preset) and SRAM by CACTI (22 nm).

| Design        | Act. | Weight            | Datapath   | PE array | Per-PE area (µm²) |
|---------------|:----:|:------------------|:-----------|:--------:|:-----------------:|
| FP16 Baseline | 16b  | 16b               | parallel   | 7×16     | 1039.6            |
| **FlexPosit** | 16b  | **PEB, 4.1–5.0b** | bit-serial | 32×16    | 243               |
| BitMoD        | 16b  | 4b                | bit-serial | 8×16     | 777               |
| OliVe (a8w8)  | 8b   | 8b                | parallel   | 38×16    | 214.6             |
| FP16-MXFP8    | 16b  | 8b (MXFP8)        | parallel   | 9×16     | 768.0             |

**FlexPosit PEB precision per model** (minimum precision achieving iso-PPL with BitMoD's 4b):
GPT2-L 4.2, GPT2-XL 4.1, Phi-2 4.5, OPT-2.7B 4.1, LLaMA2-7B 4.6, Qwen2.5-7B 4.4,
Mistral-7B 4.6, DeepSeek-7B 4.3, Qwen2.5-14B 5.0.

---

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

## Figure 12 — Perplexity vs Normalized-EDP Pareto

For GPT2-XL and Phi-2, FlexPosit is swept over fractional precisions 4.1–5.0b (step 0.1b), forming
a smooth Pareto frontier in the **bottom-left** region (low perplexity and low EDP) versus BitMoD
and OliVe. EDP is normalized per model to OliVe a8w8 (= 1.0). The green light→dark gradient encodes
increasing precision; the frontier is drawn as its running-minimum (Pareto) envelope so higher
precision never displays worse perplexity.

---

## Data provenance

- **Hardware metrics (latency, energy, EDP)** — produced end-to-end by the bundled simulator
  (`sim/`): each `test_<accel>.py` builds the accelerator model, calls CACTI for SRAM
  area/energy and the Ramulator2 binary for DRAM cycles/energy, and prints a log.
  **EDP = latency(cycles) × total_energy(µJ)**. Figure 11's `data/*.log` are exactly these logs
  and are regenerable via `sim/run_fig11_sim.sh`.
- **Perplexity** — from a separate WikiText-2 accuracy evaluation (paper Table 2). OliVe a8w8 =
  Table-2 "Channel", a4w4 = "Group"; BitMoD at 4b; FlexPosit swept 4.1–5.0b. This evaluation is
  **not part of this codebase**, so **Figure 12 is a replot from committed data** (`ppl_edp_data.csv`,
  whose `ppl` column is the external accuracy result and whose `edp` column is simulator-derived).
  Figure 11 is fully regenerable from the simulator; Figure 12's EDP axis is, but its PPL axis is not.

---

## Rebuilding the Ramulator2 binary from source (optional)

The prebuilt `ramulator/ramulator2` + `libramulator.so` are used by default. To rebuild from the
bundled source (vendored dependencies, no network required):

```bash
cd ramulator/src_build
mkdir -p build && cd build
cmake .. -DFETCHCONTENT_FULLY_DISCONNECTED=ON
make -j
# copy the freshly built ramulator2 and libramulator.so back into ramulator/,
# or point the simulator at them:  export RAMULATOR_BIN=$PWD/ramulator2
```

The simulator locates the binary at `ramulator/ramulator2` relative to `sim/`, overridable via the
`RAMULATOR_BIN` environment variable; the co-located `libramulator.so` is loaded via
`LD_LIBRARY_PATH` set by `ramulator_dram_sim.py` (so the ELF's original RUNPATH does not matter).

## Notes / limitations

- **Linux x86-64 only** — the bundled binaries and the `shell=True` subprocess calls assume a POSIX
  shell. Rebuild `cacti`/`ramulator2` for other platforms if needed (CACTI source is not bundled).
- `sim/mem/self_gen/` must be **writable** at runtime (CACTI writes its config/output there).
- Regenerated logs should match the committed reference logs bit-for-bit (verified for the FP16
  baseline); minor float/timing drift in the DRAM/SRAM subprocesses is possible on other hosts.
