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
    if op in ("R", "LD", "L", "LOAD"):
        op2 = "LD"
    elif op in ("W", "ST", "S", "STORE"):
        op2 = "ST"
    else:
        if strict: raise ValueError(f"[{src}:{lineno}] unknown op '{op}'")
        return None
    try:
        val = int(addr, 0)
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

