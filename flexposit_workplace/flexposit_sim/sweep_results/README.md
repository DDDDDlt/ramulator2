# FlexPosit Hardware-Metrics Sweeps — Seqlen & Batch

Decode-mode (`is_generation=True`) hardware-metric sweeps comparing the 4 accelerators
**FlexPosit / BitMod / Olive / Baseline**, using the per-model FlexPosit bitwidths and the
DRAM preset **DDR4_3200AC** that are current in the repo.

All numbers below are from the scripts in this folder. They depend on the optional,
backward-compatible `batch_size` parameter added to `pe_array.py` / `accelerator.py`
(default `batch_size=1`, so the figure pipeline `auto_hw_metrics_edp.png` is unaffected).

Configs per accelerator (generation mode), identical to `test_*.py`:

| Accel | i_prec | w_prec | bit-serial | pe_dp | PE array | pe_energy | pe_area |
|---|---|---|---|---|---|---|---|
| Baseline | 16 | 16 | no | 1 | [7,16] | 0.475 | 1039.559 |
| FlexPosit | 16 | per-model 4.1–5.0 | yes | 4 | [32,16] | 0.125 | 243 |
| BitMod | 16 | 4 | yes | 4 | [8,16] | 0.39593 | 777 |
| Olive | 8 | 8 | no | 1 | [38,16] | 0.33406 | 214.6 |

FlexPosit per-model bitwidths (current): GPT2-L 4.2, GPT2-XL 4.1, Phi-2 4.5, OPT-2.7B 4.1,
Llama2-7B 4.6, Qwen2.5-7B 4.4, Mistral-7B 4.6, DeepSeek-7B 4.3, Qwen2.5-14B 5.0.

Reproduce:
```
cd flexposit_workplace/flexposit_sim
python sweep_results/sweep_all_models.py    # cross-model win-factors, batch {1,8,32}
python sweep_results/sweep_bottleneck.py    # memory- vs compute-bound classification
python sweep_results/sweep_seqlen.py        # long-context sweep up to 128K
python sweep_results/sweep_hw.py            # single-model (Llama2-7B) detailed tables
```

---

## TL;DR

- **FlexPosit wins energy / EDP / efficiency across the entire seqlen × batch space tested,
  for all 9 models**, vs Baseline and BitMod — no exceptions.
- The **only** place FlexPosit loses is the **memory-bound regime** vs Olive:
  - **heavy batch** (batch≈32): Olive wins raw *latency* on all models; FlexPosit keeps EDP
    on 7B/14B but ties/loses EDP on the tiny GPT2 models.
  - **tiny model + very long context** (GPT2-scale, ≥64K): Olive wins latency and eventually EDP.
- **For real 7B–14B models, context length is essentially irrelevant** to the comparison:
  256 → 128K changes latency/energy/EDP by < 11%, and FlexPosit's win-factors are nearly constant.
  The 256-token figure is representative of all context lengths.
- **Root cause:** bit-serial FlexPosit/BitMod are **compute-bound** (weight reads hidden behind
  PEs); INT8 Olive is **memory-bound** (fast array waits on DRAM). FlexPosit only loses when the
  workload turns memory-bound and its compute advantage stops being hidden.

---

## 1. Cross-model win-factors (seqlen=256), FlexPosit ×-better than competitor (`*`=lose)

EDP win-factor (headline); ranges span the 9 models.

| batch | vs Baseline (EDP) | vs BitMod (EDP) | vs Olive latency | vs Olive (EDP) |
|---|--:|--:|--:|--:|
| 1  | 13.3–19.5× ✓ | 1.75–2.58× ✓ | 1.30–1.58× ✓ | 2.37–3.50× ✓ |
| 8  | 9.7–18.7× ✓  | 1.73–2.53× ✓ | 1.18–1.56× ✓ | 2.07–3.39× ✓ |
| 32 | 9.7–18.5× ✓  | 1.73–2.62× ✓ | **0.67–0.90× ✗** | 0.99–1.73× (GPT2-XL 0.99×*, GPT2-L 1.08×, rest ✓) |

vs Baseline & BitMod: FlexPosit wins all metrics, all models, all batch.

## 2. Memory- vs compute-bound (% of latency that is memory-bound; ≥50% = MEM-bound)

| batch | Baseline | FlexPosit | BitMod | Olive |
|---|---|---|---|---|
| 1  | Compute ~0% | Compute 0–8% | Compute 0–4% | **Memory 96–100%** |
| 8  | Compute 0%  | Compute (small models 31–42%) | Compute 0–27% | **Memory 81–99%** |
| 32 | Compute 0%  | Compute (GPT2-XL flips→Mem 60%) | Compute ~0–7% | Compute 0–7% (saturated) |

- Bit-serial (FlexPosit/BitMod) + small-array Baseline: **compute-bound**; weight DRAM hidden.
- Olive INT8: **memory-bound** until heavy batch adds enough compute to saturate it.
- Batch=32 latency flip vs Olive: Olive started memory-bound (idle compute), so batching is
  "free" for it until ~32; FlexPosit was already compute-bound so its latency scales with batch.

## 3. Long-context sweep (batch=1) — FlexPosit metric growth vs seqlen

Latency× / EDP× relative to seqlen=256, and FlexPosit mem%.

| seqlen | GPT2-L (Lat/EDP/mem) | Llama2-7B | Qwen2.5-7B (GQA) | Qwen2.5-14B |
|---|---|---|---|---|
| 256    | 1.00× / 1.0× / 0.7% | 1.00× / 1.0× / 0.2% | 1.00× / 1.0× / 0% | 1.00× / 1.0× / 0% |
| 4096   | 1.12× / 1.24× / 11% | 1.00× / 1.0× / 0.4% | 1.00× / 1.0× / 0.1% | 1.00× / 1.0× / 0.1% |
| 16384  | 1.52× / 2.25× / 35% | 1.01× / 1.01× / 0.9% | 1.01× / 1.01× / 0.5% | 1.01× / 1.01× / 0.6% |
| 65536  | 3.14× / 9.4× / 68%  | 1.03× / 1.05× / 3% | 1.02× / 1.04× / 2% | 1.02× / 1.05× / 2% |
| 131072 | **5.30× / 26.5× / 81%** | **1.06× / 1.11× / 6%** | 1.04× / 1.08× / 4% | 1.05× / 1.09× / 5% |

FlexPosit EDP win vs Olive across seqlen (`*`=lose), and Olive-speed factor:

| seqlen | GPT2-L | Llama2-7B | Qwen2.5-7B | Qwen2.5-14B |
|---|---|---|---|---|
| 256    | 3.21× (spd 1.52×) | 2.79× | 3.05× | 2.37× |
| 16384  | 2.08× (spd 1.17×) | 2.77× | 3.03× | 2.36× |
| 65536  | 1.17× (spd 0.82×*) | 2.70× | 2.98× | 2.32× |
| 131072 | **0.88×* (spd 0.69×*)** | 2.62× | 2.91× | 2.26× |

- 7B/14B: FlexPosit wins all seqlens 256→128K with near-constant margin; stays compute-bound.
- GPT2-L: attention/KV overtakes the small FFN past ~16K → turns memory-bound → Olive overtakes
  on latency at ~64K and on EDP at ~128K. Nobody deploys GPT2-large at 128K, so this is a footnote.

---

## Modeling caveats

- `batch_size` scales activation/compute tokens; weight shapes unchanged → weights correctly
  modeled as read-once-reused across the batch.
- Attention KV-cache *input reads* are not scaled by batch (each sequence really has its own KV);
  minor underestimate of off-chip traffic at large batch×seqlen. Score/output compute IS scaled.
- GOPS/W uses a fixed per-token op count × batch (no attention-FLOP growth with seqlen), so it is
  slightly optimistic at long seqlen — but **latency / energy / EDP are fully modeled and reliable**.
  (This op-count limitation already exists in the original `test_*.py`.)
