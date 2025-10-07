# gen_traces.py
# 生成 baseline.trace 与 with_scaling.trace（R 0xADDR）
LINE_FMT = "R 0x{:x}\n"   # 行格式，后续会转换成 LD/ST

# -------- 可调参数 --------
NUM_GROUPS   = 100352        # 组数（越大结果越稳定）
GROUP_SIZE   = 64         # 每组元素数（本实验固定为 128）
ELEM_SIZE_B  = 1           # 元素字节数（1/2/4 都可）
SCALE_SIZE_B = 1           # scaling factor 大小（2 或 4 常见）
LINE_SIZE_B  = 8192          # 访问粒度（近似 cache line / BL8）
# scale 与 data 分开存放，制造额外开销（行冲突更明显）
SCALE_BASE = 0x1000_0000
DATA_BASE  = 0x2000_0000
ROW_SPREAD_EXTRA = 0x0     # 想放大行冲突可加大，如 0x20000
# --------------------------

def gen_baseline(fname):
    with open(fname, "w") as f:
        for g in range(NUM_GROUPS):
            base = DATA_BASE + g * (GROUP_SIZE * ELEM_SIZE_B)
            n_lines = (GROUP_SIZE * ELEM_SIZE_B + LINE_SIZE_B - 1) // LINE_SIZE_B
            for i in range(n_lines):
                f.write(LINE_FMT.format(base + i * LINE_SIZE_B))

def gen_with_scaling(fname):
    with open(fname, "w") as f:
        for g in range(NUM_GROUPS):
            scale_addr = SCALE_BASE + g * SCALE_SIZE_B + ROW_SPREAD_EXTRA
            f.write(LINE_FMT.format(scale_addr))  # 先读 scale（串行化）
            base = DATA_BASE + g * (GROUP_SIZE * ELEM_SIZE_B)
            n_lines = (GROUP_SIZE * ELEM_SIZE_B + LINE_SIZE_B - 1) // LINE_SIZE_B
            for i in range(n_lines):
                f.write(LINE_FMT.format(base + i * LINE_SIZE_B))

if __name__ == "__main__":
    gen_baseline("baseline.trace")
    gen_with_scaling("with_scaling.trace")
    print("Wrote baseline.trace & with_scaling.trace")



# python3 gen_traces.py
# python3 rw2ldst.py baseline.trace -o baseline.ldst.trace
# python3 rw2ldst.py with_scaling.trace -o with_scaling.ldst.trace
# ../ramulator2 -f cfg_baseline.yaml      | tee out_baseline.log
# ../ramulator2 -f cfg_with_scaling.yaml  | tee out_with_scaling.log