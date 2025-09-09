# to_loadstore.py
import sys

def convert(in_path, out_path):
    with open(in_path, "r") as fin, open(out_path, "w") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 2:
                raise RuntimeError(f"Bad line: {line}")
            op, addr = parts[0], parts[1]
            # 规范操作符
            if op.upper().startswith('R'):
                op2 = 'L'
            elif op.upper().startswith('W'):
                op2 = 'S'
            else:
                raise RuntimeError(f"Unknown op: {op} in line: {line}")
            # 解析地址（支持 0x 前缀或十进制）
            addr_int = int(addr, 0)
            fout.write(f"{op2} {addr_int}\n")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 to_loadstore.py <in.trace> <out.trace>")
        sys.exit(1)
    convert(sys.argv[1], sys.argv[2])

