# gen_traces.py
# 生成 baseline.trace 与 with_scaling.trace
# 假设：每个“读”一行，格式 "R 0x<hexaddr>"
# 如果你的示例是小写 'r' 或者不带 0x，改一下 LINE_FMT 即可。

LINE_FMT = "R 0x{:x}\n"   # 或者 "r {:x}\n"

# -------- 参数区（按需改） --------
NUM_GROUPS   = 4096        # 组数，越大越稳
GROUP_SIZE   = 128         # 题设：每组 128 个元素
ELEM_SIZE_B  = 1           # 每个元素字节数：1/2/4（int8/fp16/fp32等）
SCALE_SIZE_B = 4           # 每个 scale 的字节数：2/4 常见
LINE_SIZE_B  = 64          # 模拟 cache line / 常见突发粒度 BL8~64B

# 为了“制造额外开销”，将 scale 和 data 完全分开存放
SCALE_BASE = 0x1000_0000
DATA_BASE  = 0x2000_0000

# 如果想进一步增大“行冲突”，可以把这个偏移调更大
#（具体行大小与地址映射由 YAML 决定；这里简化为让地址相距较大，通常会落到不同 row）
ROW_SPREAD_EXTRA = 0x0      # 先置 0，能跑通后按需放大，例如 0x10000
# ---------------------------------

def align_up(x, a):
    return (x + a - 1) // a * a

def gen_baseline(fname):
    with open(fname, "w") as f:
        for g in range(NUM_GROUPS):
            # 连续 weights：每组一段连续数据
            group_data_base = DATA_BASE + g * (GROUP_SIZE * ELEM_SIZE_B)
            # 为了不让 trace 太庞大，这里按 cache line 粒度发“读”
            group_bytes = GROUP_SIZE * ELEM_SIZE_B
            n_lines = (group_bytes + LINE_SIZE_B - 1) // LINE_SIZE_B
            for i in range(n_lines):
                addr = group_data_base + i * LINE_SIZE_B
                f.write(LINE_FMT.format(addr))

def gen_with_scaling(fname):
    with open(fname, "w") as f:
        for g in range(NUM_GROUPS):
            # 每组的 scale 单独数组存放（与 data 分离）
            scale_addr = SCALE_BASE + g * SCALE_SIZE_B + ROW_SPREAD_EXTRA

            # 先读 scale（刻意串行化：把 scale 放在 data 前面）
            f.write(LINE_FMT.format(scale_addr))

            # 再读该组的 data（连续）
            group_data_base = DATA_BASE + g * (GROUP_SIZE * ELEM_SIZE_B)
            group_bytes = GROUP_SIZE * ELEM_SIZE_B
            n_lines = (group_bytes + LINE_SIZE_B - 1) // LINE_SIZE_B
            for i in range(n_lines):
                addr = group_data_base + i * LINE_SIZE_B
                f.write(LINE_FMT.format(addr))

if __name__ == "__main__":
    gen_baseline("baseline.trace")
    gen_with_scaling("with_scaling.trace")
    print("Wrote baseline.trace & with_scaling.trace")

