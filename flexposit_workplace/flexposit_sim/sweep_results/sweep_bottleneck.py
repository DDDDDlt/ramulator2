import sys, io, contextlib, os
sys.path.insert(0, '/home/liangtaodai/dailt_workplace/ramulator2/flexposit_workplace/flexposit_sim')
os.chdir('/home/liangtaodai/dailt_workplace/ramulator2/flexposit_workplace/flexposit_sim')
from accelerator import Accelerator

MODELS = [
    ("gpt2-large","GPT2-L"), ("gpt2-xl","GPT2-XL"), ("microsoft/phi-2","Phi-2"),
    ("facebook/opt-2.7b","OPT-2.7B"), ("meta-llama/Llama-2-7b-hf","Llama2-7B"),
    ("Qwen/Qwen2.5-7B","Qwen2.5-7B"), ("mistralai/Mistral-7B-v0.1","Mistral-7B"),
    ("deepseek-ai/deepseek-llm-7b-base","DeepSeek-7B"), ("Qwen/Qwen2.5-14B","Qwen2.5-14B"),
]
FLEX_W = {"gpt2-large":4.2,"gpt2-xl":4.1,"microsoft/phi-2":4.5,"facebook/opt-2.7b":4.1,
    "meta-llama/Llama-2-7b-hf":4.6,"Qwen/Qwen2.5-7B":4.4,"mistralai/Mistral-7B-v0.1":4.6,
    "deepseek-ai/deepseek-llm-7b-base":4.3,"Qwen/Qwen2.5-14B":5.0}

def make(kind, model, seqlen, batch):
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

def mem_frac(kind, model, seqlen, batch):
    with contextlib.redirect_stdout(io.StringIO()):
        a = make(kind,model,seqlen,batch)
        a.calc_cycle()
        s = a.analyze_bottleneck()
    tot = s['latency_from_compute'] + s['latency_from_memory']
    return 100.0 * s['latency_from_memory'] / tot  # % of latency that is memory-bound

ACCS=["Baseline","FlexPosit","BitMod","Olive"]
def tag(pct): return "MEM " if pct>=50 else "CMP "
SEQ=256
for batch in [1,8,32]:
    print("\n"+"="*92)
    print(f"BOTTLENECK  |  batch={batch}, seqlen={SEQ}   (% of latency that is MEMORY-bound; MEM=mem-bound, CMP=compute-bound)")
    print("="*92)
    print(f"{'model':<13}" + "".join(f"{a:>17}" for a in ACCS))
    print("-"*92)
    for model,short in MODELS:
        cells=[]
        for a in ACCS:
            p = mem_frac(a,model,SEQ,batch)
            cells.append(f"{tag(p)}{p:5.1f}% mem")
        print(f"{short:<13}" + "".join(f"{c:>17}" for c in cells))
    print("-"*92)
# also seqlen effect on bottleneck for one model
print("\n"+"="*60)
print("Seqlen effect on FlexPosit Llama2-7B (batch=1): % mem-bound")
for s in [256,1024,4096]:
    print(f"  seqlen={s:<5}: {mem_frac('FlexPosit','meta-llama/Llama-2-7b-hf',s,1):.1f}% mem-bound")
print("DONE")
