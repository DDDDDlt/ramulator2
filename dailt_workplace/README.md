# Reproducing Group-wise Scaling Overhead in Ramulator 2.0

用 **Ramulator 2.0（Standalone）** 对比两种场景：
- **Baseline**：只读取连续的 weights  
- **With-Scaling**：每个 group（128 元素）先读一次 **scaling factor**，再读该组 weights

通过把 **scale** 与 **data** 分开存放并强制顺序（scale→data），即可在统计中看到 **额外 DRAM 延迟**。

---

## 0) 先决条件

- 你已在仓库根目录（能看到 `./ramulator2` 可执行文件）  
- 示例命令均在仓库根目录执行

可选自检：
```bash
./ramulator2 -h
```

---

## 1) 生成访问序列（trace）

新建 `gen_traces.py`（在仓库根目录）：

```python
# gen_traces.py
# 生成 baseline.trace 与 with_scaling.trace（R 0xADDR）

LINE_FMT = "R 0x{:x}\n"   # 行格式；后面会转成 LD/ST

# -------- 可调参数 --------
NUM_GROUPS   = 4096        # 组数（越大越稳）
GROUP_SIZE   = 128         # 每组元素数
ELEM_SIZE_B  = 1           # 元素字节数（1/2/4）
SCALE_SIZE_B = 4           # scaling factor 大小（2/4）
LINE_SIZE_B  = 64          # 访问粒度（近似 cache line / BL8）
# scale 与 data 分开存放，制造额外开销
SCALE_BASE = 0x1000_0000
DATA_BASE  = 0x2000_0000
ROW_SPREAD_EXTRA = 0x0     # 想放大行冲突可改大，如 0x20000
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
            f.write(LINE_FMT.format(scale_addr))  # 先读 scale（串行）
            base = DATA_BASE + g * (GROUP_SIZE * ELEM_SIZE_B)
            n_lines = (GROUP_SIZE * ELEM_SIZE_B + LINE_SIZE_B - 1) // LINE_SIZE_B
            for i in range(n_lines):
                f.write(LINE_FMT.format(base + i * LINE_SIZE_B))

if __name__ == "__main__":
    gen_baseline("baseline.trace")
    gen_with_scaling("with_scaling.trace")
    print("Wrote baseline.trace & with_scaling.trace")
```

运行并检查：
```bash
python3 gen_traces.py
ls -lh *.trace
head -n 3 baseline.trace with_scaling.trace
```

---

## 2) 转换为 Ramulator 前端格式（LD/ST）

**LoadStoreTrace** 需要每行两列：`LD <addr>` / `ST <addr>`。  
新建 `rw2ldst.py`：

```python
#!/usr/bin/env python3
# rw2ldst.py : Convert R/W to LD/ST two-column trace for LoadStoreTrace
import argparse, sys, os

def convert_line(line, decimal=False, strict=False, lineno=0, src=""):
    s = line.strip()
    if not s or s.startswith(("#",";","//")):
        return None
    parts = s.split()
    if len(parts) < 2:
        if strict: raise ValueError(f"[{src}:{lineno}] invalid line: {line.strip()}")
        return None
    op, addr = parts[0].upper(), parts[1]
    if op in ("R","LD","L","LOAD"):  op2 = "LD"
    elif op in ("W","ST","S","STORE"): op2 = "ST"
    else:
        if strict: raise ValueError(f"[{src}:{lineno}] unknown op '{op}'")
        return None
    try:
        val = int(addr, 0)  # 支持 0x
    except Exception:
        if strict: raise ValueError(f"[{src}:{lineno}] bad addr '{addr}'")
        return None
    addr_out = str(val) if decimal else (addr if addr.startswith(("0x","0X")) else str(val))
    return f"{op2} {addr_out}\n"

def convert_file(inp, outp, decimal=False, strict=False):
    n_in=n_out=0
    with open(inp) as fin, open(outp,"w") as fout:
        for i, line in enumerate(fin, start=1):
            n_in += 1
            out = convert_line(line, decimal=decimal, strict=strict, lineno=i, src=os.path.basename(inp))
            if out is not None:
                fout.write(out); n_out += 1
    return n_in, n_out

def main():
    p = argparse.ArgumentParser(description="Convert R/W traces to LoadStoreTrace (LD/ST <addr>).")
    p.add_argument("inputs", nargs="+", help="input trace file(s)")
    p.add_argument("-o","--output", help="output file (when single input)")
    p.add_argument("--decimal", action="store_true", help="emit decimal addresses")
    p.add_argument("--strict", action="store_true", help="strict mode")
    args = p.parse_args()
    if args.output and len(args.inputs)!=1:
        p.error("--output only valid with a single input")
    if args.output:
        ni,no=convert_file(args.inputs[0], args.output, decimal=args.decimal, strict=args.strict)
        print(f"[OK] {args.inputs[0]} -> {args.output} ({no}/{ni} lines)")
    else:
        for inp in args.inputs:
            outp = inp + ".ldst.trace"
            ni,no=convert_file(inp, outp, decimal=args.decimal, strict=args.strict)
            print(f"[OK] {inp} -> {outp} ({no}/{ni} lines)")

if __name__ == "__main__":
    sys.exit(main())
```

执行转换：
```bash
python3 rw2ldst.py baseline.trace -o baseline.ldst.trace
python3 rw2ldst.py with_scaling.trace -o with_scaling.ldst.trace

ls -lh baseline.ldst.trace with_scaling.ldst.trace
head -n 3 baseline.ldst.trace with_scaling.ldst.trace
# baseline:       LD 0x20000000 ...
# with_scaling:   LD 0x10000000 (scale), LD 0x20000000 (data group0) ...
```

---

## 3) 准备两个配置（YAML）

复制示例并分别指向两份 trace：

```bash
cp example_config.yaml cfg_baseline.yaml
cp example_config.yaml cfg_with_scaling.yaml
```

把两份 YAML 的 **Frontend** 改为 **LoadStoreTrace**，并**关闭地址翻译**：

```yaml
Frontend:
  impl: LoadStoreTrace
  path: ./baseline.ldst.trace     # 另一份改成 ./with_scaling.ldst.trace
  clock_ratio: 1

Translation:
  impl: NoTranslation
```

> **建议（放大差距）**：行策略改为 **OpenRowPolicy**（两份配置都改）：
> ```yaml
> MemorySystem:
>   Controller:
>     Scheduler:
>       impl: FRFCFS
>     RowPolicy:
>       impl: OpenRowPolicy
> ```

其余 `MemorySystem/DRAM/AddrMapper` 保持一致（例如示例的 `DDR4_2400R`、`RoBaRaCoCh`）。

---

## 4) 运行模拟

```bash
../ramulator2 -f cfg_baseline.yaml      | tee out_baseline.log
../ramulator2 -f cfg_with_scaling.yaml  | tee out_with_scaling.log
```

---

## 5) 获取关键指标（metrics）

常见字段（名字可能略有差别）：
- `avg_read_latency_0`：平均读延迟（**周期**）
- `row_hits_0 / row_misses_0 / row_conflicts_0`：行命中/未命中/冲突
- `num_read_reqs_0`：读请求数
- `memory_system_cycles`：内存系统总周期

**对比平均读延迟（cycles）：**
```bash
echo "baseline cycles:"     $(grep -m1 "avg_read_latency_0" out_baseline.log     | awk '{print $2}')
echo "with_scaling cycles:" $(grep -m1 "avg_read_latency_0" out_with_scaling.log | awk '{print $2}')
```

**换算为纳秒（DDR4-2400：tCK≈0.833ns）：**
```bash
B=$(grep -m1 "avg_read_latency_0" out_baseline.log     | awk '{print $2}')
S=$(grep -m1 "avg_read_latency_0" out_with_scaling.log | awk '{print $2}')
python3 - <<PY
b=float("$B"); s=float("$S"); tCK=0.833
print(f"avg latency: baseline={b:.2f} cyc ({b*tCK:.2f} ns), "
      f"with_scaling={s:.2f} cyc ({s*tCK:.2f} ns), "
      f"Δ={(s-b):.2f} cyc (+{(s/b-1)*100:.1f}%)")
PY
```

**行命中率变化：**
```bash
echo "baseline hits/misses:"   $(grep -m1 "row_hits_0" out_baseline.log | awk '{print $2}')   $(grep -m1 "row_misses_0" out_baseline.log | awk '{print $2}')
echo "with_scaling hits/misses:"   $(grep -m1 "row_hits_0" out_with_scaling.log | awk '{print $2}')   $(grep -m1 "row_misses_0" out_with_scaling.log | awk '{print $2}')
```

**粗算带宽（若未直接打印，假设每行 64B）：**
```bash
N=$(grep -m1 "num_read_reqs_0" out_baseline.log | awk '{print $2}')
CYC=$(grep -m1 "memory_system_cycles" out_baseline.log | awk '{print $2}')
python3 - <<PY
N=int("$N"); cyc=int("$CYC"); LINE=64; tCK=0.833e-9
bytes=N*LINE; sec=cyc*tCK
print(f"baseline approx read BW = {bytes/sec/1e9:.2f} GB/s")
PY
```

---

## 6) 放大 “with-scaling” 开销的小技巧（可选）

- **增大 `ROW_SPREAD_EXTRA`**（在 `gen_traces.py`）：让 scale 地址更远，更可能落到不同 **row**，增加 row-miss/冲突；改完需重新生成/转换 `with_scaling`。
- **OpenRowPolicy + FRFCFS**：更容易看到 baseline 的 row-hit 优势与 with-scaling 的额外 miss 成本。
- **保持两份 YAML 除了 trace 路径外完全一致**：保证可比。

---

## 7) 常见报错与排查

- `Trying to create an implementation "TRACE" ... not registered`  
  → `impl` 名写错。用：
  ```yaml
  Frontend:
    impl: LoadStoreTrace
  ```
- `Param "path"/"clock_ratio" ... required but not given.`  
  → 补齐：
  ```yaml
  Frontend:
    impl: LoadStoreTrace
    path: ./baseline.ldst.trace
    clock_ratio: 1
  ```
- `Trace ... format invalid!`  
  → 行格式不对。确保**两列**：`LD <addr>` / `ST <addr>`，无多余空白/注释；地址可十进制或 `0x`。

---

## 8) 一键对比（可选）

```bash
B=$(grep -m1 "avg_read_latency_0" out_baseline.log     | awk '{print $2}')
S=$(grep -m1 "avg_read_latency_0" out_with_scaling.log | awk '{print $2}')
HB=$(grep -m1 "row_hits_0"   out_baseline.log | awk '{print $2}')
MB=$(grep -m1 "row_misses_0" out_baseline.log | awk '{print $2}')
HS=$(grep -m1 "row_hits_0"   out_with_scaling.log | awk '{print $2}')
MS=$(grep -m1 "row_misses_0" out_with_scaling.log | awk '{print $2}')
python3 - <<PY
b=float("$B"); s=float("$S"); tCK=0.833
hb=int("$HB"); mb=int("$MB"); hs=int("$HS"); ms=int("$MS")
print(f"Latency  : baseline={b:.2f} cyc ({b*tCK:.2f} ns) | with_scaling={s:.2f} cyc ({s*tCK:.2f} ns) | Δ={(s-b):.2f} cyc (+{(s/b-1)*100:.1f}%)")
def rate(h,m):
    tot=h+m
    return (h/tot*100 if tot>0 else 0.0, m/tot*100 if tot>0 else 0.0)
rb,mbp = rate(hb,mb); rs,msp = rate(hs,ms)
print(f"Row-hit% : baseline={rb:.1f}%, with_scaling={rs:.1f}%")
print(f"Row-miss%: baseline={mbp:.1f}%, with_scaling={msp:.1f}%")
PY
```

---

## 9) 结果预期

- **with-scaling** 的 `avg_read_latency_0` 明显 **高于** baseline  
- **with-scaling** 的 `row_misses_0` 比例更高（OpenRowPolicy 下更明显）  
- 调大 `ROW_SPREAD_EXTRA` → 差距进一步增大

---

如需把 DRAM 标准改为 **DDR5 / HBM3**，只需在 YAML 的 `MemorySystem -> DRAM` 更改 `impl/preset/timing`，其余流程相同。
