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
FLEX_W = {  # new per-model FlexPosit bitwidths
    "gpt2-large":4.2, "gpt2-xl":4.1, "microsoft/phi-2":4.5, "facebook/opt-2.7b":4.1,
    "meta-llama/Llama-2-7b-hf":4.6, "Qwen/Qwen2.5-7B":4.4, "mistralai/Mistral-7B-v0.1":4.6,
    "deepseek-ai/deepseek-llm-7b-base":4.3, "Qwen/Qwen2.5-14B":5.0,
}
OPS = {  # MACs*2 per token (batch=1)
    "gpt2-large":65434880*2, "gpt2-xl":82638400*2, "microsoft/phi-2":2650537984*2,
    "facebook/opt-2.7b":2648162304*2, "meta-llama/Llama-2-7b-hf":6611533824*2,
    "Qwen/Qwen2.5-7B":6611533824*2, "mistralai/Mistral-7B-v0.1":6611533824*2,
    "deepseek-ai/deepseek-llm-7b-base":6611533824*2, "Qwen/Qwen2.5-14B":13223067648*2,
}

def make(kind, model, seqlen, batch):
    if kind=="Baseline":
        return Accelerator(model_name=model,i_prec=16,w_prec=16,is_bit_serial=False,pe_dp_size=1,
            pe_energy=0.475,pe_area=1039.559,pe_array_dim=[7,16],context_length=seqlen,
            is_generation=True,use_scale_overhead_lat=False,batch_size=batch)
    if kind=="FlexPosit":
        return Accelerator(model_name=model,i_prec=16,w_prec=FLEX_W[model],is_bit_serial=True,pe_dp_size=4,
            pe_energy=0.125,pe_area=243,pe_array_dim=[32,16],context_length=seqlen,is_generation=True,
            is_flexposit=True,use_scale_overhead_lat=False,batch_size=batch)
    if kind=="BitMod":
        return Accelerator(model_name=model,i_prec=16,w_prec=4,is_bit_serial=True,pe_dp_size=4,
            pe_energy=0.39593,pe_area=777,pe_array_dim=[8,16],context_length=seqlen,is_generation=True,
            use_scale_overhead_lat=False,scale_bits=8,meta_bits=2,group_size=128,batch_size=batch)
    if kind=="Olive":
        return Accelerator(model_name=model,i_prec=8,w_prec=8.0,is_bit_serial=False,pe_dp_size=1,
            pe_energy=0.33406,pe_area=214.6,pe_array_dim=[38,16],context_length=seqlen,is_generation=True,
            use_scale_overhead_lat=False,batch_size=batch)

def metr(kind, model, seqlen, batch):
    with contextlib.redirect_stdout(io.StringIO()):
        a = make(kind,model,seqlen,batch)
        cyc = a.calc_cycle()[1]
        e = (a.calc_compute_energy()+a.calc_sram_rd_energy()+a.calc_sram_wr_energy()+a.calc_dram_energy())/1e6
    edp = e*cyc
    gw = (OPS[model]*batch/cyc) / (e/cyc*1e6) * 1000
    return cyc,e,edp,gw

ACCS=["Baseline","FlexPosit","BitMod","Olive"]
SEQ=256
for batch in [1,8,32]:
    print("\n"+"="*100)
    print(f"ALL MODELS  |  batch={batch}, seqlen={SEQ}  |  FlexPosit win-factor vs each (>1=Flex wins; * = LOSE)")
    print("="*100)
    print(f"{'model':<13}| {'vs Baseline (sp/edp)':<22}| {'vs BitMod (sp/edp)':<22}| {'vs Olive (sp/en/edp/eff)':<30}")
    print("-"*100)
    for model,short in MODELS:
        m = {a:metr(a,model,SEQ,batch) for a in ACCS}
        fc,fe,fedp,fgw = m["FlexPosit"]
        def wf(a):
            cc,ce,cedp,cgw=m[a]; return cc/fc, ce/fe, cedp/fedp, fgw/cgw
        bsp,_,bedp,_ = wf("Baseline")
        msp,_,medp,_ = wf("BitMod")
        osp,oen,oedp,oeff = wf("Olive")
        lose = "  *LOSE" if min(bsp,bedp,msp,medp,osp,oen,oedp,oeff) < 1.0 else ""
        print(f"{short:<13}| {bsp:5.2f}x /{bedp:6.2f}x      | {msp:5.2f}x /{medp:6.2f}x      | "
              f"{osp:4.2f}x/{oen:4.2f}x/{oedp:4.2f}x/{oeff:4.2f}x{lose}")
    print("-"*100)
print("\nDONE")
