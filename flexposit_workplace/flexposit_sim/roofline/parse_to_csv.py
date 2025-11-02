#!/usr/bin/env python3

import os
import re
import csv
import argparse


def parse_one_log(file_path):
    with open(file_path, 'r') as f:
        content = f.read()

    # accelerator name
    m_acc = re.search(r'^Accelerator:\s*(.+)$', content, re.MULTILINE)
    accelerator = m_acc.group(1).strip() if m_acc else 'Unknown'

    # infer x,y from filename: test_<acc>_x{X}_y{Y}.log
    base = os.path.basename(file_path)
    m_xy = re.match(r'test_([a-zA-Z0-9_]+)_x(\d+)_y(\d+)\.log$', base)
    pe_x = int(m_xy.group(2)) if m_xy else None
    pe_y = int(m_xy.group(3)) if m_xy else None

    # iterate per-model blocks
    # e.g. "[1/5] Model: facebook/opt-2.7b" then several metric lines
    rows = []
    # split into lines for sequential parsing
    lines = content.splitlines()

    current = None
    for line in lines:
        m_model = re.search(r'^\[\d+/\d+\]\s*Model:\s*(.+?)(?:\s*\(.*\))?\s*$', line)
        if m_model:
            # flush previous
            if current:
                rows.append(current)
            current = {
                'accelerator': accelerator,
                'model': m_model.group(1).strip(),
                'pe_x': pe_x,
                'pe_y': pe_y,
                'total_cycle': None,
                'pe_array_area_mm2': None,
                'weight_buffer_area_mm2': None,
                'input_buffer_area_mm2': None,
                'dram_energy_mJ': None,
                'onchip_energy_mJ': None,
                'total_energy_mJ': None,
                'edp': None,
                'log_file': base,
            }
            continue

        if current is None:
            continue

        m = re.search(r'Total Cycle:\s*([0-9,]+(?:\.[0-9]+)?)', line)
        if m:
            # allow decimal cycles (e.g., 8,366,099.200000006)
            current['total_cycle'] = float(m.group(1).replace(',', ''))
            continue

        m = re.search(r'PE Array Area:\s*([0-9.]+)\s*mm', line)
        if m:
            current['pe_array_area_mm2'] = float(m.group(1))
            continue

        m = re.search(r'Weight Buffer:\s*([0-9.]+)\s*mm', line)
        if m:
            current['weight_buffer_area_mm2'] = float(m.group(1))
            continue

        m = re.search(r'Input Buffer:\s*([0-9.]+)\s*mm', line)
        if m:
            current['input_buffer_area_mm2'] = float(m.group(1))
            continue

        m = re.search(r'DRAM Energy:\s*([0-9.]+)\s*mJ', line)
        if m:
            current['dram_energy_mJ'] = float(m.group(1))
            continue

        m = re.search(r'On-chip Energy:\s*([0-9.]+)\s*mJ', line)
        if m:
            current['onchip_energy_mJ'] = float(m.group(1))
            continue

        m = re.search(r'Total Energy:\s*([0-9.]+)\s*mJ', line)
        if m:
            current['total_energy_mJ'] = float(m.group(1))
            continue

        # Total MACs
        m = re.search(r'Total MACs:\s*([0-9,]+)', line)
        if m:
            current['total_macs'] = int(m.group(1).replace(',', ''))
            continue

        m = re.search(r'Energy Delay Product:\s*([0-9.]+)', line)
        if m:
            current['edp'] = float(m.group(1))
            continue

    # flush last
    if current:
        rows.append(current)

    return rows


def parse_all_logs(log_dir):
    all_rows = []
    for name in os.listdir(log_dir):
        if not name.startswith('test_') or not name.endswith('.log'):
            continue
        rows = parse_one_log(os.path.join(log_dir, name))
        all_rows.extend(rows)
    return all_rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--log-dir', required=True, help='Directory containing logs')
    parser.add_argument('--out', required=True, help='Output CSV path')
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)

    rows = parse_all_logs(args.log_dir)
    header = [
        'accelerator', 'model', 'pe_x', 'pe_y',
        'total_cycle', 'pe_array_area_mm2', 'weight_buffer_area_mm2', 'input_buffer_area_mm2', 'total_area_mm2', 'total_macs',
        'dram_energy_mJ', 'onchip_energy_mJ', 'total_energy_mJ', 'edp', 'log_file'
    ]

    with open(args.out, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        for r in rows:
            try:
                # 按你的需求：总面积改为仅使用 PE 阵列面积
                v = r.get('pe_array_area_mm2')
                r['total_area_mm2'] = float(v) if v is not None else None
            except Exception:
                r['total_area_mm2'] = None
            writer.writerow(r)

    print(f"Wrote {len(rows)} rows to {args.out}")


if __name__ == '__main__':
    main()


