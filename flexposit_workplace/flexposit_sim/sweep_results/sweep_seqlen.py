import sys, io, contextlib, os
sys.path.insert(0, '/home/liangtaodai/dailt_workplace/ramulator2/flexposit_workplace/flexposit_sim')
os.chdir('/home/liangtaodai/dailt_workplace/ramulator2/flexposit_workplace/flexposit_sim')
from accelerator import Accelerator

# representative spread: small/MHA, 7B/MHA-big-KV, 7B/GQA, largest
MODELS = [
    ("gpt2-large","GPT2-L"),
    ("meta-llama/Llama-2-7b-hf","Llama2-7B"),
    ("Qwen/Qwen2.5-7B","Qwen2.5-7B(GQA)"),
    ("Qwen/Qwen2.5-14B","Qwen2.5-14B"),
]
FLEX_W = {"gpt2-large":4.2,"meta-llama/Llama-2-7b-hf":4.6,"Qwen/Qwen2.5-7B":4.4,"Qwen/Qwen2.5-14B":5.0}
SEQS = [256, 1024, 4096, 16384, 65536, 131072]

def make(kind, model, seqlen, batch=1):
    if kind=="Baseline":
        return Accelerator(model_name=model,i_prec=16,w_prec=16,is_bit_serial=False,pe_dp_size=1,
            pe_energy=0.475,pe_area=1039.559,pe_array_dim=[7,16],context_length=seqlen,is_generation=True,batch_size=batch)
    if kind=="FlexPosit":
        return Accelerator(model_name=model,i_prec=16,w_prec=FLEX_W[model],is_bit_serial=True,pe_dp_size=4,
            pe_energy=0.125,pe_area=243,pe_array_dim=[32,16],context_length=seqlen,is_generation=True,
            is_flexposit=True,batch_size=batch)
    if kind=="BitMod":
        return Accelerator(model_name=model,i_prec=16,w_prec=4,is_bit_serial=True,pe_dp_size=4,
            pe_energy=0.39593,pe_area=777,pe_array_dim=[8,16],context_length=seqlen,is_generation=True,
            scale_bits=8,meta_bits=2,group_size=128,batch_size=batch)
    if kind=="Olive":
        return Accelerator(model_name=model,i_prec=8,w_prec=8.0,is_bit_serial=False,pe_dp_size=1,
            pe_energy=0.33406,pe_area=214.6,pe_array_dim=[38,16],context_length=seqlen,is_generation=True,batch_size=batch)

def run(kind, model, seqlen):
    with contextlib.redirect_stdout(io.StringIO()):
        a = make(kind,model,seqlen)
        cyc = a.calc_cycle()[1]
        e = (a.calc_compute_energy()+a.calc_sram_rd_energy()+a.calc_sram_wr_energy()+a.calc_dram_energy())/1e6
        s = a.analyze_bottleneck()
    mempct = 100.0*s['latency_from_memory']/(s['latency_from_compute']+s['latency_from_memory'])
    return cyc, e, cyc*e, mempct

ACCS=["Baseline","FlexPosit","BitMod","Olive"]
data={}
for model,short in MODELS:
    data[short]={a:{s:run(a,model,s) for s in SEQS} for a in ACCS}

# Table A: FlexPosit metrics vs seqlen (growth relative to seq=256)
print("="*94)
print("A) FlexPosit  |  metric growth vs seqlen  (Latency cyc, Energy uJ, EDP) ; xN = vs seq=256")
print("="*94)
for short in data:
    base = data[short]["FlexPosit"][256]
    print(f"\n{short}")
    print(f"  {'seqlen':>8}{'Latency':>16}{'(x)':>7}{'Energy':>14}{'(x)':>7}{'EDP':>14}{'(x)':>7}{'mem%':>7}")
    for s in SEQS:
        c,e,edp,m = data[short]["FlexPosit"][s]
        print(f"  {s:>8}{c:>16,.0f}{c/base[0]:>6.2f}x{e:>14,.0f}{e/base[1]:>6.2f}x{edp:>14.2e}{edp/base[2]:>6.2f}x{m:>6.1f}%")

# Table B: FlexPosit win-factor (EDP) vs each accelerator across seqlen
print("\n"+"="*94)
print("B) FlexPosit EDP win-factor vs competitor across seqlen  (>1 = FlexPosit wins; * = lose)")
print("="*94)
for short in data:
    print(f"\n{short}")
    print(f"  {'seqlen':>8}" + "".join(f"{'vs '+a:>14}" for a in ['Baseline','BitMod','Olive']) + f"{'Olive-speed':>13}")
    for s in SEQS:
        fc,fe,fedp,_ = data[short]["FlexPosit"][s]
        row=f"  {s:>8}"
        for a in ['Baseline','BitMod','Olive']:
            cc,ce,cedp,_ = data[short][a][s]
            r=cedp/fedp
            row += f"{r:>13.2f}x"
        oc=data[short]["Olive"][s][0]
        osp=oc/fc
        row += f"{osp:>11.2f}x" + ("" if osp>=1 else "*")
        print(row)

# Table C: bottleneck (mem%) of every accelerator vs seqlen, one model (Llama2-7B = big KV)
print("\n"+"="*94)
print("C) Bottleneck mem% vs seqlen, per accelerator (>=50% = MEMORY-bound)")
print("="*94)
for short in data:
    print(f"\n{short}")
    print(f"  {'seqlen':>8}" + "".join(f"{a:>12}" for a in ACCS))
    for s in SEQS:
        row=f"  {s:>8}"
        for a in ACCS:
            m=data[short][a][s][3]
            row += f"{m:>10.1f}%"
        print(row)
print("\nDONE")
