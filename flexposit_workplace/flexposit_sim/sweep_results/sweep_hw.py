import sys, io, contextlib
sys.path.insert(0, '/home/liangtaodai/dailt_workplace/ramulator2/flexposit_workplace/flexposit_sim')
import os
os.chdir('/home/liangtaodai/dailt_workplace/ramulator2/flexposit_workplace/flexposit_sim')
from accelerator import Accelerator

MODEL = "meta-llama/Llama-2-7b-hf"
BASE_OPS = 6611533824 * 2  # per-token (batch=1) MACs*2

# Accelerator configs (generation mode), identical to test_*.py
def make_acc(kind, seqlen, batch):
    common = dict(model_name=MODEL, pe_array_dim_key=None, context_length=seqlen,
                  is_generation=True, batch_size=batch)
    if kind == "Baseline":
        return Accelerator(model_name=MODEL, i_prec=16, w_prec=16, is_bit_serial=False,
                           pe_dp_size=1, pe_energy=0.475, pe_area=1039.559,
                           pe_array_dim=[7,16], context_length=seqlen,
                           is_generation=True, use_scale_overhead_lat=False, batch_size=batch)
    if kind == "FlexPosit":
        return Accelerator(model_name=MODEL, i_prec=16, w_prec=4.6, is_bit_serial=True,
                           pe_dp_size=4, pe_energy=0.125, pe_area=243,
                           pe_array_dim=[32,16], context_length=seqlen, is_generation=True,
                           is_flexposit=True, use_scale_overhead_lat=False, batch_size=batch)
    if kind == "BitMod":
        return Accelerator(model_name=MODEL, i_prec=16, w_prec=4, is_bit_serial=True,
                           pe_dp_size=4, pe_energy=0.39593, pe_area=777,
                           pe_array_dim=[8,16], context_length=seqlen, is_generation=True,
                           use_scale_overhead_lat=False, scale_bits=8, meta_bits=2,
                           group_size=128, batch_size=batch)
    if kind == "Olive":
        return Accelerator(model_name=MODEL, i_prec=8, w_prec=8.0, is_bit_serial=False,
                           pe_dp_size=1, pe_energy=0.33406, pe_area=214.6,
                           pe_array_dim=[38,16], context_length=seqlen, is_generation=True,
                           use_scale_overhead_lat=False, batch_size=batch)

def metrics(kind, seqlen, batch):
    with contextlib.redirect_stdout(io.StringIO()):
        acc = make_acc(kind, seqlen, batch)
        cyc = acc.calc_cycle()[1]
        e = (acc.calc_compute_energy() + acc.calc_sram_rd_energy()
             + acc.calc_sram_wr_energy() + acc.calc_dram_energy()) / 1e6  # uJ
    ops = BASE_OPS * batch
    gops = ops / cyc
    power_mw = e / cyc * 1e6
    gops_w = gops / power_mw * 1000
    edp = e * cyc
    return cyc, e, edp, gops_w

ACCS = ["Baseline", "FlexPosit", "BitMod", "Olive"]

def run_sweep(title, combos):
    print("\n" + "="*96)
    print(title)
    print("="*96)
    hdr = f"{'config':<18}{'accel':<11}{'Latency(cyc)':>16}{'Energy(uJ)':>14}{'EDP':>16}{'GOPS/W':>10}"
    print(hdr)
    print("-"*96)
    allm = {}
    for label, seqlen, batch in combos:
        allm[label] = {}
        for a in ACCS:
            cyc, e, edp, gw = metrics(a, seqlen, batch)
            allm[label][a] = (cyc, e, edp, gw)
            tag = label if a == ACCS[0] else ""
            print(f"{tag:<18}{a:<11}{cyc:>16,.0f}{e:>14,.1f}{edp:>16,.3e}{gw:>10.3f}")
        print("-"*96)
    # Comparison: FlexPosit win-factor vs each competitor (>1 = FlexPosit better)
    print("\n  >> FlexPosit win-factor (x times better; <1.0 = FlexPosit LOSES, marked *)")
    print(f"  {'config':<14}{'vs':<11}{'Speedup':>10}{'Energy':>10}{'EDP':>10}{'Eff':>10}")
    for label in allm:
        fc, fe, fedp, fgw = allm[label]["FlexPosit"]
        for a in ["Baseline", "BitMod", "Olive"]:
            cc, ce, cedp, cgw = allm[label][a]
            sp, en, ed, ef = cc/fc, ce/fe, cedp/fedp, fgw/cgw
            mark = "" if min(sp, en, ed, ef) >= 1.0 else "  *LOSE"
            print(f"  {label:<14}{a:<11}{sp:>9.2f}x{en:>9.2f}x{ed:>9.2f}x{ef:>9.2f}x{mark}")
        print()

# Sweep 1: seqlen, batch=1
run_sweep("Llama-2-7B  |  SEQLEN sweep (batch=1, decode)",
          [(f"seq={s}", s, 1) for s in [256, 1024, 4096]])

# Sweep 2: batch, seqlen=256
run_sweep("Llama-2-7B  |  BATCH sweep (seqlen=256, decode)",
          [(f"batch={b}", 256, b) for b in [1, 8, 32]])
