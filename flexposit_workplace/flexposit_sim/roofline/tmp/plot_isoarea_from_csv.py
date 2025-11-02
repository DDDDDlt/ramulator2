#!/usr/bin/env python3

import os
import sys
import csv
import argparse
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patheffects as patheffects


def read_rows(csv_path):
    rows = []
    with open(csv_path, 'r') as f:
        rdr = csv.DictReader(f)
        for r in rdr:
            try:
                r['model'] = r['model']
                r['log_file'] = r.get('log_file', '')
                r['pe_x'] = int(r['pe_x']) if r['pe_x'] else None
                r['pe_y'] = int(r['pe_y']) if r['pe_y'] else None
                r['total_cycle'] = float(r['total_cycle']) if r['total_cycle'] else None
                r['pe_array_area_mm2'] = float(r['pe_array_area_mm2']) if r['pe_array_area_mm2'] else 0.0
                r['total_macs'] = float(r['total_macs']) if 'total_macs' in r and r['total_macs'] else None
                rows.append(r)
            except Exception:
                continue
    return rows


def acc_key_from_log(log_file):
    base = os.path.basename(log_file)
    if base.startswith('test_') and '_x' in base:
        return base[len('test_'):base.index('_x')]
    return 'unknown'


ACC_PRETTY = {
    'flexposit': 'FlexPosit',
    'olive': 'OliVe',
    'bitmod': 'BitMoD',
}

ACC_COLOR = {
    'FlexPosit': '#f5a300',  # orange (match tmp/roofline.py)
    'OliVe':     '#3aa0e3',  # blue
    'BitMoD':    '#0a9d6d',  # green
}


def build_series(rows, model, use_macs):
    # returns dict {pretty_name: (areas, thpts)} sorted by area
    series = {}
    for r in rows:
        if r['model'] != model:
            continue
        key = acc_key_from_log(r['log_file'])
        if key not in ACC_PRETTY:
            continue
        pretty = ACC_PRETTY[key]
        area = r['pe_array_area_mm2']
        cycle = r['total_cycle']
        if cycle is None or cycle <= 0:
            continue
        if use_macs:
            macs = r.get('total_macs')
            if not macs:
                # skip if MACs missing for this record
                continue
            thpt = macs / cycle
        else:
            thpt = 1.0 / cycle
        series.setdefault(pretty, []).append((area, thpt))

    out = {}
    for pretty, pts in series.items():
        pts.sort(key=lambda t: t[0])
        if len(pts) >= 2:
            areas = np.array([p[0] for p in pts])
            thpts = np.array([p[1] for p in pts])
            out[pretty] = (areas, thpts)
    return out


def dense_intersect_xs(a, y1, y2):
    # a, y1, y2 are 1D arrays with same length in ascending a
    diff = y1 - y2
    idxs = np.where(np.diff(np.sign(diff)) != 0)[0]
    xs = []
    for i in idxs:
        x0, x1 = a[i], a[i+1]
        y0, y1v = diff[i], diff[i+1]
        if (y1v - y0) == 0:
            continue
        x = x0 - y0 * (x1 - x0) / (y1v - y0)
        xs.append(x)
    return xs


def plot_isoarea(model, series, use_macs, out_path):
    # Build a common dense grid over overlapping area range of all present accelerators
    names = [n for n in ['FlexPosit', 'OliVe', 'BitMoD'] if n in series]
    if len(names) < 2:
        print(f"Skip {model}: need at least two accelerators with data")
        return

    # Determine global overlap [xmin, xmax]
    xmin = -np.inf
    xmax = np.inf
    for n in names:
        areas = series[n][0]
        xmin = max(xmin, areas.min())
        xmax = min(xmax, areas.max())
    if not np.isfinite(xmin) or not np.isfinite(xmax) or xmax <= xmin:
        print(f"Skip {model}: no overlapping area range")
        return

    A = np.linspace(xmin, xmax, 800)
    T = {}
    for n in names:
        areas, thpts = series[n]
        T[n] = np.interp(A, areas, thpts)

    # Compute intersections: FlexPosit vs OliVe, BitMoD vs FlexPosit if available
    region_xs = []
    if 'FlexPosit' in T and 'OliVe' in T:
        xs = dense_intersect_xs(A, T['FlexPosit'], T['OliVe'])
        if len(xs) >= 2:
            region_xs.append((min(xs[0], xs[1]), max(xs[0], xs[1])))
    if 'BitMoD' in T and 'FlexPosit' in T:
        xs = dense_intersect_xs(A, T['BitMoD'], T['FlexPosit'])
        if len(xs) >= 2:
            region_xs.append((min(xs[0], xs[1]), max(xs[0], xs[1])))

    # Plot
    plt.figure(figsize=(8.5, 6.0), dpi=150)

    # Draw vertical dashed lines at intersections between FlexPosit-OliVe and BitMoD-FlexPosit
    x_fo = None
    if 'FlexPosit' in T and 'OliVe' in T:
        xs = dense_intersect_xs(A, T['FlexPosit'], T['OliVe'])
        if xs:
            x_fo = xs[0]
            plt.axvline(x_fo, linestyle="--", linewidth=1.6, color="#555555")
            # mark intersection point on FlexPosit curve
            y_fo = np.interp(x_fo, A, T['FlexPosit'])
            plt.scatter([x_fo], [y_fo], s=36, c='#000000', zorder=4)
    x_bf = None
    if 'BitMoD' in T and 'FlexPosit' in T:
        xs = dense_intersect_xs(A, T['BitMoD'], T['FlexPosit'])
        if xs:
            x_bf = xs[0]
            plt.axvline(x_bf, linestyle="--", linewidth=1.6, color="#555555")
            y_bf = np.interp(x_bf, A, T['FlexPosit'])
            plt.scatter([x_bf], [y_bf], s=36, c='#000000', zorder=4)

    for n in names:
        line, = plt.plot(A, T[n], color=ACC_COLOR.get(n, '#555555'), linewidth=3.2, label=n)
        line.set_solid_capstyle('round')
        line.set_solid_joinstyle('round')
        line.set_path_effects([patheffects.Stroke(linewidth=4.6, foreground='#FFFFFF'), patheffects.Normal()])

    plt.legend()
    plt.xlabel("PE Array Area (mm$^2$)", fontsize=14, fontweight='bold')
    plt.ylabel("Throughput (MAC/cycle)" if use_macs else "Throughput", fontsize=14, fontweight='bold')
    plt.title(f"{model}", fontsize=16, fontweight='bold')
    plt.tight_layout()
    png = out_path + ".png"
    pdf = out_path + ".pdf"
    plt.savefig(png, bbox_inches='tight', dpi=300)
    plt.savefig(pdf, bbox_inches='tight')
    plt.close()
    print(f"Saved: {png}\nSaved: {pdf}")


def main():
    parser = argparse.ArgumentParser(description="Plot iso-area style curves from CSV (reference tmp/roofline.py)")
    parser.add_argument('--csv', required=True, help='roofline_results.csv')
    parser.add_argument('--macs-csv', default=None, help='Optional model,total_macs CSV to fill missing MACs')
    parser.add_argument('--model', default=None, help='Only plot this model (default: all)')
    parser.add_argument('--out-dir', required=True, help='Output directory')
    parser.add_argument('--throughput', choices=['cycle', 'mac'], default='mac', help='Use 1/cycle or MAC/cycle')
    args = parser.parse_args()

    rows = read_rows(args.csv)
    # inject MACs if provided
    if args.macs_csv:
        try:
            with open(args.macs_csv, 'r') as f:
                rdr = csv.DictReader(f)
                m2m = {r['model']: float(r['total_macs']) for r in rdr if r.get('model') and r.get('total_macs')}
            for r in rows:
                if not r.get('total_macs') and r.get('model') in m2m:
                    r['total_macs'] = m2m[r['model']]
        except Exception as e:
            print(f"Warning: failed to load macs-csv: {e}")

    use_macs = (args.throughput == 'mac')
    models = sorted({r['model'] for r in rows})
    if args.model:
        models = [m for m in models if m == args.model]
    os.makedirs(args.out_dir, exist_ok=True)

    for m in models:
        series = build_series(rows, m, use_macs)
        if not series:
            print(f"No series for model {m}")
            continue
        out_path = os.path.join(args.out_dir, f"isoarea_{m.replace('/', '_')}")
        plot_isoarea(m, series, use_macs, out_path)


if __name__ == '__main__':
    main()


