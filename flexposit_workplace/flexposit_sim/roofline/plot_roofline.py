#!/usr/bin/env python3

import os
import csv
import argparse
from collections import defaultdict, OrderedDict

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as patheffects


def read_csv(csv_path):
    rows = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                r['pe_x'] = int(r['pe_x']) if r['pe_x'] else None
                r['pe_y'] = int(r['pe_y']) if r['pe_y'] else None
                # cycles may be decimal in logs; keep as float
                r['total_cycle'] = float(r['total_cycle']) if r['total_cycle'] else None
                r['pe_array_area_mm2'] = float(r['pe_array_area_mm2']) if r['pe_array_area_mm2'] else 0.0
                r['weight_buffer_area_mm2'] = float(r['weight_buffer_area_mm2']) if r['weight_buffer_area_mm2'] else 0.0
                r['input_buffer_area_mm2'] = float(r['input_buffer_area_mm2']) if r['input_buffer_area_mm2'] else 0.0
                # optional: total_macs may be missing in older logs
                if 'total_macs' in r and r['total_macs'] not in (None, ''):
                    r['total_macs'] = float(r['total_macs'])
                else:
                    r['total_macs'] = None
            except Exception:
                # skip malformed rows
                continue
            rows.append(r)
    return rows


def extract_acc_key(log_file):
    # log_file like: test_baseline_x4_y16.log
    base = os.path.basename(log_file)
    if base.startswith('test_') and '_x' in base:
        return base[len('test_'):base.index('_x')]
    return 'unknown'


def compute_total_area(row):
    # 改为仅使用 PE 阵列面积作为横轴面积
    return (row['pe_array_area_mm2'] or 0.0)


def _area_from_dim(acc_key: str, dim: int) -> float:
    """Compute area (mm^2) from accelerator name and array first dimension."""
    k = acc_key.lower()
    if k == 'flexposit':
        val = dim * 16 * 341.41 + 32 * (14.72 + 23.12) + 15.97
    elif k == 'bitmod':
        val = dim * 16 * 859.28 + 302.38 * dim
    elif k == 'baseline':
        val = dim * 16 * 920.19
    elif k == 'olive':
        val = dim * 16 * 183.31 + 9.54 * dim
    else:
        val = 0.0
    # 单位换算：假设上式为 um^2，这里转为 mm^2
    return val / 1e6

def _format_model_name(model: str) -> str:
    """将模型名称格式化为大写格式，例如：gpt2-xl -> GPT2-XL"""
    # 处理特殊模型名称
    model_lower = model.lower()
    if 'phi-2' in model_lower:
        # microsoft/phi-2 -> Microsoft/Phi-2B
        parts = model.split('/')
        if len(parts) == 2:
            org, name = parts[0], parts[1]
            # Microsoft 首字母大写，其余小写
            org_formatted = org.capitalize()
            # phi-2 -> Phi-2B
            if 'phi-2' in name.lower():
                name_formatted = 'Phi-2B'
            else:
                name_formatted = name.upper()
            return f'{org_formatted}/{name_formatted}'
        elif 'phi-2' in model_lower:
            return 'Phi-2B'
    
    # Microsoft 处理
    if 'microsoft' in model_lower:
        parts = model.split('/')
        if len(parts) == 2:
            org, name = parts[0], parts[1]
            org_formatted = org.capitalize()  # Microsoft
            name_formatted = name.upper()
            return f'{org_formatted}/{name_formatted}'
    
    # 默认：直接转为大写，保持分隔符不变
    return model.upper()

def _dense_intersect_xs(a: np.ndarray, y1: np.ndarray, y2: np.ndarray) -> list:
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


def build_dataset(rows):
    # dataset[(model, pe_x, acc_key)] = {area, cycle}
    data = {}
    models = set()
    acc_keys = set()
    x_values = set()
    for r in rows:
        model = r['model']
        pe_x = r['pe_x']
        if model is None or pe_x is None:
            continue
        acc_key = extract_acc_key(r.get('log_file', ''))
        total_cycle = r['total_cycle']
        if total_cycle is None or total_cycle <= 0:
            continue
        total_area = compute_total_area(r)
        data[(model, pe_x, acc_key)] = {
            'area': total_area,
            'cycle': total_cycle,
            'macs': r.get('total_macs'),
        }
        models.add(model)
        acc_keys.add(acc_key)
        x_values.add(pe_x)
    return data, sorted(models), sorted(acc_keys), sorted(x_values)


def plot_per_model(norm, models, acc_keys, out_dir, x_min=None, x_max=None, x_label: str | None = None):
    os.makedirs(out_dir, exist_ok=True)
    # colors and markers per accelerator key
    color_map = OrderedDict([
        ('flexposit', '#4FB0A9'),
        ('bitmod', '#F4A261'),
        ('olive', '#457B9D'),
        ('baseline', '#BDBDBD'),
    ])
    pretty_label = {
        'flexposit': 'FlexPosit',
        'bitmod': 'BitMoD',
        'olive': 'OliVe',
        'baseline': 'Baseline',
    }
    marker_map = {
        'baseline': 'o',
        'olive': 's',
        'flexposit': 'D',
        'bitmod': '^',
    }

    for model in models:
        fig, ax = plt.subplots(figsize=(6.5, 5))
        series = {}
        for acc_key in acc_keys:
            xs = np.array(norm[model][acc_key]['x'])
            ys = np.array(norm[model][acc_key]['y'])
            if xs.size == 0:
                continue
            # 关键修正：按归一化后的 X 升序排序，避免曲线错乱
            order = np.argsort(xs)
            xs = xs[order]
            ys = ys[order]
            series[acc_key] = (xs, ys)

        # normalized: 使用归一化后的 X、Y，按 X 升序连线
        for acc_key, (xs, ys) in series.items():
            color = color_map.get(acc_key, '#777777')
            if xs.size == 0:
                continue
            # 直接绘制归一化后的点，不做额外变换保持原始形状
            line, = ax.plot(xs, ys, color=color, linewidth=3.0, label=pretty_label.get(acc_key, acc_key))
            line.set_solid_capstyle('round')
            line.set_solid_joinstyle('round')
            line.set_path_effects([patheffects.Stroke(linewidth=4.2, foreground='#FFFFFF'), patheffects.Normal()])
            

        ax.set_xlabel(x_label or 'Normalized Compute Area', fontsize=14, fontweight='bold')
        ax.set_ylabel('Normalized Throughput', fontsize=14, fontweight='bold')
        ax.grid(True, linestyle=':', alpha=0.5)
        ax.legend(frameon=True, framealpha=0.9, edgecolor='#CCCCCC', loc='lower right', fontsize=12)
        # draw dashed intersections: flexposit vs olive; bitmod vs flexposit
        # and shade outside the two vertical lines
        interxs = []
        def collect_inters(k1, k2):
            if (k1 in series) and (k2 in series):
                x1, y1 = series[k1]
                x2, y2 = series[k2]
                xmin = max(x1.min(), x2.min())
                xmax = min(x1.max(), x2.max())
                if xmax > xmin:
                    A = np.linspace(xmin, xmax, 800)
                    f = np.interp(A, x1, y1)
                    g = np.interp(A, x2, y2)
                    xs = _dense_intersect_xs(A, f, g)
                    interxs.extend(xs)
        collect_inters('flexposit', 'olive')
        collect_inters('bitmod', 'flexposit')
        if interxs:
            xs_sorted = sorted(set(interxs))
            # draw lines (lighter color)
            for xv in xs_sorted:
                ax.axvline(xv, linestyle='--', linewidth=1.2, color='#BBBBBB', alpha=0.9, zorder=0)
            if len(xs_sorted) >= 2:
                xl, xr = xs_sorted[0], xs_sorted[1]
                # shade outside the two lines
                cur_xmin, cur_xmax = ax.get_xlim()
                ax.axvspan(cur_xmin, xl, facecolor='#EEEEEE', alpha=0.35, zorder=0)
                ax.axvspan(xr, cur_xmax, facecolor='#EEEEEE', alpha=0.35, zorder=0)
                # 在两条虚线之间添加黄色高亮
                ax.axvspan(xl, xr, facecolor='white', alpha=0.3, zorder=0)
        # 仅在指定时设置 xlim；否则让数据自适应（baseline 归一化的 X 不一定在 [0,1]）
        if x_min is not None or x_max is not None:
            ax.set_xlim(left=x_min if x_min is not None else None, right=x_max if x_max is not None else None)
        ax.set_ylim(bottom=0)
        fig.tight_layout()
        out_png = os.path.join(out_dir, f"roofline_model_{model.replace('/', '_')}.png")
        out_pdf = os.path.join(out_dir, f"roofline_model_{model.replace('/', '_')}.pdf")
        fig.savefig(out_png, dpi=300)
        fig.savefig(out_pdf)
        plt.close(fig)


def plot_average(norm, models, acc_keys, out_dir, x_min=None, x_max=None, x_label: str | None = None):
    # average across models at each pe_x position. Build aligned x across pe_x by intersecting where all models have data for baseline
    # We'll average y over models for matching pe_x indices (by sorting pe_x); x averaged similarly.
    os.makedirs(out_dir, exist_ok=True)
    color_map = OrderedDict([
        ('flexposit', '#4FB0A9'),
        ('bitmod', '#F4A261'),
        ('olive', '#457B9D'),
        ('baseline', '#BDBDBD'),
    ])
    pretty_label = {
        'flexposit': 'FlexPosit',
        'bitmod': 'BitMoD',
        'olive': 'OliVe',
        'baseline': 'Baseline',
    }
    marker_map = {
        'baseline': 'o',
        'olive': 's',
        'flexposit': 'D',
        'bitmod': '^',
    }

    fig, ax = plt.subplots(figsize=(6.5, 5))
    for acc_key in acc_keys:
        # gather per model series sorted by pe_x
        series = []
        for model in models:
            xs = np.array(norm[model][acc_key]['x'])
            ys = np.array(norm[model][acc_key]['y'])
            pes = np.array(norm[model][acc_key]['pe_x'])
            if xs.size == 0:
                continue
            # 关键修正：按归一化后的 X 排序，但保留同序的 pe_x 以便对齐
            order = np.argsort(xs)
            series.append((pes[order], xs[order], ys[order]))
        if not series:
            continue
        # find common pe_x positions across models
        common_pes = None
        for pes, _, _ in series:
            common_pes = pes if common_pes is None else np.intersect1d(common_pes, pes)
        if common_pes is None or common_pes.size == 0:
            continue
        avg_x = []
        avg_y = []
        for px in common_pes:
            xs_at = []
            ys_at = []
            for pes, xs, ys in series:
                idx = np.where(pes == px)[0]
                if idx.size:
                    xs_at.append(xs[idx[0]])
                    ys_at.append(ys[idx[0]])
            if xs_at and ys_at:
                avg_x.append(np.mean(xs_at))
                avg_y.append(np.mean(ys_at))

        if not avg_x:
            continue
        color = color_map.get(acc_key, '#777777')
        # 关键修正：按归一化后的 X 排序再绘制，避免用 pe_x 排序导致折线错乱
        avg_x = np.array(avg_x)
        avg_y = np.array(avg_y)
        order = np.argsort(avg_x)
        avg_x = avg_x[order]
        avg_y = avg_y[order]
        # 直接绘制，不做变换
        line, = ax.plot(avg_x, avg_y, color=color, linewidth=3.2, label=pretty_label.get(acc_key, acc_key))
        line.set_solid_capstyle('round')
        line.set_solid_joinstyle('round')
        line.set_path_effects([patheffects.Stroke(linewidth=4.6, foreground='#FFFFFF'), patheffects.Normal()])
        

    ax.set_xlabel(x_label or 'Normalized Compute Area', fontsize=14, fontweight='bold')
    ax.set_ylabel('Normalized Throughput', fontsize=14, fontweight='bold')
    ax.grid(True, linestyle=':', alpha=0.5)
    ax.legend(frameon=True, framealpha=0.9, edgecolor='#CCCCCC', fontsize=12)
    # baseline 归一化：不强制 [0,1]，除非显式指定
    if x_min is not None or x_max is not None:
        ax.set_xlim(left=x_min if x_min is not None else None, right=x_max if x_max is not None else None)
    ax.set_ylim(bottom=0)
    fig.tight_layout()
    out_png = os.path.join(out_dir, f"roofline_average.png")
    out_pdf = os.path.join(out_dir, f"roofline_average.pdf")
    fig.savefig(out_png, dpi=300)
    fig.savefig(out_pdf)
    plt.close(fig)


def build_raw_series(data, models, acc_keys, x_values, use_macs=False, area_limit: float | None = None):
    # raw[model][acc_key] = { 'x': [area...], 'y': [throughput...], 'pe_x': [pe_x...] }
    raw = {m: {a: {'x': [], 'y': [], 'pe_x': []} for a in acc_keys} for m in models}
    for model in models:
        for acc_key in acc_keys:
            # collect all pe_x available
            points = []
            for px in x_values:
                row = data.get((model, px, acc_key))
                if not row:
                    continue
                area = _area_from_dim(acc_key, px)
                # 不再按面积阈值过滤
                cycle = row['cycle']
                if area is None or cycle is None or cycle <= 0:
                    continue
                if use_macs:
                    macs = row.get('macs')
                    if macs in (None, 0):
                        continue
                    tp = float(macs) / float(cycle)
                else:
                    tp = 1.0 / float(cycle)
                points.append((px, area, tp))
            if points:
                points.sort(key=lambda t: t[0])
                raw[model][acc_key]['pe_x'] = [p[0] for p in points]
                raw[model][acc_key]['x'] = [p[1] for p in points]
                raw[model][acc_key]['y'] = [p[2] for p in points]
    return raw


def plot_per_model_raw(raw, models, acc_keys, out_dir, x_min=None, x_max=None, y_label='Throughput', normalize_y=False):
    os.makedirs(out_dir, exist_ok=True)
    color_map = OrderedDict([
        ('flexposit', '#4FB0A9'),
        ('bitmod', '#F4A261'),
        ('olive', '#457B9D'),
        ('baseline', '#BDBDBD'),
    ])
    pretty_label = {
        'flexposit': 'FlexPosit',
        'bitmod': 'BitMoD',
        'olive': 'OliVe',
        'baseline': 'Baseline',
    }
    marker_map = {
        'baseline': 'o',
        'olive': 's',
        'flexposit': 'D',
        'bitmod': '^',
    }

    for model in models:
        fig, ax = plt.subplots(figsize=(6.5, 5))
        series = {}
        for acc_key in acc_keys:
            xs = np.array(raw[model][acc_key]['x'])
            ys = np.array(raw[model][acc_key]['y'])
            if xs.size == 0:
                continue
            # 只保留横坐标 <= 0.45 的点
            mask = xs <= 0.45
            xs_filtered = xs[mask]
            ys_filtered = ys[mask]
            if xs_filtered.size == 0:
                continue
            series[acc_key] = (xs_filtered, ys_filtered)
        
        # 纵坐标归一化：使用所有加速器中（0-0.45范围内）的全局最大值
        if normalize_y and series:
            # 找到所有加速器中的最大y值（只考虑0-0.45范围内的点）
            global_max_y = max([np.max(ys) for xs, ys in series.values() if len(ys) > 0])
            if global_max_y > 0:
                for acc_key in series:
                    normalized_ys = series[acc_key][1] / global_max_y
                    series[acc_key] = (series[acc_key][0], normalized_ys)

        # compute global max x
        all_last = [v[0][-1] for v in series.values() if len(v[0]) > 0]
        global_max_x = max(all_last) if all_last else None

        for acc_key, (xs, ys) in series.items():
            color = color_map.get(acc_key, '#777777')
            if normalize_y and len(xs) > 0:
                # 归一化模式：将横坐标从0-0.45映射到0-1（除以0.45）
                xs_mapped = xs / 0.45
                
                # 左侧：在第一个点前添加原点(0, 0)
                xs_extended = np.concatenate([[0.0], xs_mapped])
                ys_extended = np.concatenate([[0.0], ys])
                
                # 右侧：在最后一个点后添加水平延长的点（延长到1.0）
                last_y = ys[-1]
                xs_extended = np.concatenate([xs_extended, [1.0]])
                ys_extended = np.concatenate([ys_extended, [last_y]])
                
                line, = ax.plot(xs_extended, ys_extended, color=color, linewidth=2.0, label=pretty_label.get(acc_key, acc_key))
            else:
                # 非归一化模式：直接绘制（0-0.45范围）
                line, = ax.plot(xs, ys, color=color, linewidth=2.0, label=pretty_label.get(acc_key, acc_key))
            line.set_solid_capstyle('round')
            line.set_solid_joinstyle('round')
            line.set_path_effects([patheffects.Stroke(linewidth=3.0, foreground='#FFFFFF'), patheffects.Normal()])
            

        ax.set_xlabel('Normalized Compute Area', fontsize=14, fontweight='bold')
        if normalize_y:
            ax.set_ylabel(f'Normalized {y_label}', fontsize=14, fontweight='bold')
        else:
            ax.set_ylabel(y_label, fontsize=14, fontweight='bold')
        ax.grid(True, linestyle=':', alpha=0.5)
        ax.legend(frameon=True, framealpha=0.9, edgecolor='#CCCCCC', loc='lower right', fontsize=12)
        # dashed intersections for RAW as well (lighter & shade outside two lines)
        interxs = []
        def collect_inters(k1, k2):
            if (k1 in series) and (k2 in series):
                x1, y1 = series[k1]
                x2, y2 = series[k2]
                xmin = max(x1.min(), x2.min())
                xmax = min(x1.max(), x2.max())
                if xmax > xmin:
                    A = np.linspace(xmin, xmax, 800)
                    f = np.interp(A, x1, y1)
                    g = np.interp(A, x2, y2)
                    xs = _dense_intersect_xs(A, f, g)
                    interxs.extend(xs)
        collect_inters('flexposit', 'olive')
        collect_inters('bitmod', 'flexposit')
        if interxs:
            xs_sorted = sorted(set(interxs))
            # 归一化模式下，将交点横坐标从0-0.45映射到0-1（除以0.45）
            if normalize_y:
                xs_sorted = [xv / 0.45 for xv in xs_sorted]
            for xv in xs_sorted:
                ax.axvline(xv, linestyle='--', linewidth=1.2, color='#BBBBBB', alpha=0.9, zorder=0)
            if len(xs_sorted) >= 2:
                xl, xr = xs_sorted[0], xs_sorted[1]
                # 先设置x和y轴范围，确保后续文本位置计算正确
                # 横坐标显示范围：归一化模式0到1，非归一化模式0-0.5（可通过参数覆盖）
                if normalize_y:
                    # 归一化模式：横坐标显示0到1
                    if x_min is not None or x_max is not None:
                        ax.set_xlim(left=x_min if x_min is not None else 0.0, right=x_max if x_max is not None else 1.0)
                    else:
                        ax.set_xlim(0, 1)
                else:
                    # 非归一化模式：横坐标显示0-0.45
                    if x_min is not None or x_max is not None:
                        ax.set_xlim(left=x_min if x_min is not None else 0.0, right=x_max if x_max is not None else 0.45)
                    else:
                        ax.set_xlim(0, 0.45)
                # 设置y轴范围
                if normalize_y:
                    ax.set_ylim(0, 1.1)
                # 获取设置后的轴范围
                cur_xmin, cur_xmax = ax.get_xlim()
                cur_ymin, cur_ymax = ax.get_ylim()
                ax.axvspan(cur_xmin, xl, facecolor='#EEEEEE', alpha=0.35, zorder=0)
                ax.axvspan(xr, cur_xmax, facecolor='#EEEEEE', alpha=0.35, zorder=0)
                # 在两条虚线之间添加黄色高亮
                ax.axvspan(xl, xr, facecolor='white', alpha=0.3, zorder=0)
                # 添加三个区域的文本标注
                # 左侧区域：ultra-low-power
                left_center_x = (cur_xmin + xl) / 2.0
                ax.text(left_center_x, cur_ymax * 0.98, 'Ultra-low-power', 
                       ha='center', va='top', fontsize=12, fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8, edgecolor='none'),
                       zorder=10)
                # 中间区域：edge mixed compute/memory
                mid_center_x = (xl + xr) / 2.0
                ax.text(mid_center_x, cur_ymax * 0.98, 'Edge-scale', 
                       ha='center', va='top', fontsize=12, fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8, edgecolor='none'),
                       zorder=10)
                # 右侧区域：cloud-scale
                right_center_x = (xr + cur_xmax) / 2.0
                # 确保文本不会超出右边界，如果太靠右则稍微向左移动
                if right_center_x > cur_xmax * 0.95:
                    right_center_x = cur_xmax * 0.90
                ax.text(right_center_x, cur_ymax * 0.98, 'Cloud-scale', 
                       ha='center', va='top', fontsize=12, fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8, edgecolor='none'),
                       zorder=10)
        # 横坐标显示范围：归一化模式0到1，非归一化模式0-0.5（可通过参数覆盖）
        # 如果已经在虚线区域设置过，这里就不重复设置
        if len(interxs) < 2 or not normalize_y:
            if normalize_y:
                # 归一化模式：横坐标显示0到1
                if x_min is not None or x_max is not None:
                    ax.set_xlim(left=x_min if x_min is not None else 0.0, right=x_max if x_max is not None else 1.0)
                else:
                    ax.set_xlim(0, 1)
            else:
                # 非归一化模式：横坐标显示0-0.45
                if x_min is not None or x_max is not None:
                    ax.set_xlim(left=x_min if x_min is not None else 0.0, right=x_max if x_max is not None else 0.45)
                else:
                    ax.set_xlim(0, 0.45)
        # y轴范围（如果还没设置过）
        if not (normalize_y and len(interxs) >= 2):
            if normalize_y:
                # 设置范围为0到1.1，为区域标注留出空间
                ax.set_ylim(0, 1.1)
            else:
                ax.set_ylim(bottom=0)
        fig.tight_layout()
        suffix = '_raw_normalized' if normalize_y else '_raw'
        out_png = os.path.join(out_dir, f"roofline_model_{model.replace('/', '_')}{suffix}.png")
        out_pdf = os.path.join(out_dir, f"roofline_model_{model.replace('/', '_')}{suffix}.pdf")
        fig.savefig(out_png, dpi=300)
        fig.savefig(out_pdf)
        plt.close(fig)


def plot_average_raw(raw, models, acc_keys, out_dir, x_min=None, x_max=None, y_label='Throughput', normalize_y=False):
    os.makedirs(out_dir, exist_ok=True)
    color_map = OrderedDict([
        ('flexposit', '#4FB0A9'),
        ('bitmod', '#F4A261'),
        ('olive', '#457B9D'),
        ('baseline', '#BDBDBD'),
    ])
    pretty_label = {
        'flexposit': 'FlexPosit',
        'bitmod': 'BitMoD',
        'olive': 'OliVe',
        'baseline': 'Baseline',
    }
    marker_map = {
        'baseline': 'o',
        'olive': 's',
        'flexposit': 'D',
        'bitmod': '^',
    }

    fig, ax = plt.subplots(figsize=(6.5, 5))
    series_dict = {}
    for acc_key in acc_keys:
        # collect series per model
        series = []
        for model in models:
            pes = np.array(raw[model][acc_key]['pe_x'])
            xs = np.array(raw[model][acc_key]['x'])
            ys = np.array(raw[model][acc_key]['y'])
            if xs.size == 0:
                continue
            # 只保留横坐标 <= 0.45 的点
            mask = xs <= 0.45
            pes_filtered = pes[mask]
            xs_filtered = xs[mask]
            ys_filtered = ys[mask]
            if xs_filtered.size == 0:
                continue
            order = np.argsort(pes_filtered)
            series.append((pes_filtered[order], xs_filtered[order], ys_filtered[order]))
        if not series:
            continue
        # find common pe_x across models
        common_pes = None
        for pes, _, _ in series:
            common_pes = pes if common_pes is None else np.intersect1d(common_pes, pes)
        if common_pes is None or common_pes.size == 0:
            continue
        avg_x = []
        avg_y = []
        for px in common_pes:
            xs_at = []
            ys_at = []
            for pes, xs, ys in series:
                idx = np.where(pes == px)[0]
                if idx.size:
                    xs_at.append(xs[idx[0]])
                    ys_at.append(ys[idx[0]])
            if xs_at and ys_at:
                avg_x.append(np.mean(xs_at))
                avg_y.append(np.mean(ys_at))

        if not avg_x:
            continue
        color = color_map.get(acc_key, '#777777')
        order = np.argsort(common_pes)
        avg_x = np.array(avg_x)[order]
        avg_y = np.array(avg_y)[order]
        series_dict[acc_key] = (avg_x, avg_y)
    
    # 纵坐标归一化：使用所有加速器中（0-0.45范围内）的全局最大值
    if normalize_y and series_dict:
        # 找到所有加速器中的最大y值（只考虑0-0.45范围内的点）
        global_max_y = max([np.max(avg_y) for avg_x, avg_y in series_dict.values() if len(avg_y) > 0])
        if global_max_y > 0:
            for acc_key in series_dict:
                normalized_ys = series_dict[acc_key][1] / global_max_y
                series_dict[acc_key] = (series_dict[acc_key][0], normalized_ys)
    
    # 绘制所有系列
    # 获取x轴范围（用于右侧水平延长）
    if series_dict:
        all_x_max = max([np.max(avg_x) for avg_x, avg_y in series_dict.values() if len(avg_x) > 0])
    else:
        all_x_max = 1.0
    
    for acc_key in acc_keys:
        if acc_key not in series_dict:
            continue
        avg_x, avg_y = series_dict[acc_key]
        color = color_map.get(acc_key, '#777777')
        
        if normalize_y and len(avg_x) > 0:
            # 归一化模式：将横坐标从0-0.45映射到0-1（除以0.45）
            avg_x_mapped = avg_x / 0.45
            
            # 左侧：在第一个点前添加原点(0, 0)
            xs_extended = np.concatenate([[0.0], avg_x_mapped])
            ys_extended = np.concatenate([[0.0], avg_y])
            
            # 右侧：在最后一个点后添加水平延长的点（延长到1.0）
            last_y = avg_y[-1]
            xs_extended = np.concatenate([xs_extended, [1.0]])
            ys_extended = np.concatenate([ys_extended, [last_y]])
            
            line, = ax.plot(xs_extended, ys_extended, color=color, linewidth=2.2, label=pretty_label.get(acc_key, acc_key))
        else:
            # 非归一化模式：直接绘制（0-0.4范围）
            line, = ax.plot(avg_x, avg_y, color=color, linewidth=2.2, label=pretty_label.get(acc_key, acc_key))
        line.set_solid_capstyle('round')
        line.set_solid_joinstyle('round')
        line.set_path_effects([patheffects.Stroke(linewidth=3.5, foreground='#FFFFFF'), patheffects.Normal()])
        

    ax.set_xlabel('PE Array Area (mm²)', fontsize=14, fontweight='bold')
    if normalize_y:
        ax.set_ylabel(f'Normalized {y_label}', fontsize=14, fontweight='bold')
    else:
        ax.set_ylabel(y_label, fontsize=14, fontweight='bold')
    ax.grid(True, linestyle=':', alpha=0.5)
    ax.legend(frameon=True, framealpha=0.9, edgecolor='#CCCCCC', loc='lower right', fontsize=12)
    if normalize_y:
        # 归一化模式：横坐标显示0到1
        if x_min is not None or x_max is not None:
            ax.set_xlim(left=x_min if x_min is not None else 0.0, right=x_max if x_max is not None else 1.0)
        else:
            ax.set_xlim(left=0, right=1)
    else:
        # 非归一化模式：横坐标显示0-0.45
        if x_min is not None or x_max is not None:
            ax.set_xlim(left=x_min if x_min is not None else 0.0, right=x_max if x_max is not None else 0.45)
        else:
            ax.set_xlim(left=0, right=0.45)
    if normalize_y:
        # 设置范围为0到1.1，为区域标注留出空间
        ax.set_ylim(0, 1.1)
    else:
        ax.set_ylim(bottom=0)
    fig.tight_layout()
    suffix = '_raw_normalized' if normalize_y else '_raw'
    out_png = os.path.join(out_dir, f"roofline_average{suffix}.png")
    out_pdf = os.path.join(out_dir, f"roofline_average{suffix}.pdf")
    fig.savefig(out_png, dpi=300)
    fig.savefig(out_pdf)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', required=True, help='Input CSV from parse_to_csv.py')
    parser.add_argument('--out-dir', required=True, help='Output directory for plots')
    parser.add_argument('--normalize', choices=['no', 'baseline', 'range', 'yes'], default='no', help='Normalization: no | baseline | range (yes==baseline)')
    parser.add_argument('--normalize-y', action='store_true', help='Normalize Y-axis (throughput) by global maximum across all accelerators')
    parser.add_argument('--throughput', choices=['cycle', 'mac'], default='cycle', help='Throughput definition: 1/cycle or MACs/cycle')
    parser.add_argument('--x-min', type=float, default=None, help='X-axis min (area or normalized area)')
    parser.add_argument('--x-max', type=float, default=None, help='X-axis max (area or normalized area)')
    parser.add_argument('--macs-csv', default=None, help='Optional CSV mapping model,total_macs to fill missing MACs')
    parser.add_argument('--dump-debug-dir', default=None, help='Dump normalized points into CSV under this directory')
    args = parser.parse_args()

    rows = read_csv(args.csv)
    # Optionally load external MACs mapping
    if args.macs_csv:
        try:
            with open(args.macs_csv, 'r') as f:
                rdr = csv.DictReader(f)
                model_to_macs = {r['model']: float(r['total_macs']) for r in rdr if r.get('model') and r.get('total_macs')}
            # fill missing
            for r in rows:
                if not r.get('total_macs') and r.get('model') in model_to_macs:
                    r['total_macs'] = model_to_macs[r['model']]
        except Exception as e:
            print(f"Warning: failed to read macs-csv {args.macs_csv}: {e}")

    data, models, acc_keys, x_values = build_dataset(rows)

    # enforce accelerator ordering
    desired_order = ['flexposit', 'bitmod', 'olive', 'baseline']
    acc_keys_sorted = [a for a in desired_order if a in acc_keys] + [a for a in acc_keys if a not in desired_order]

    os.makedirs(args.out_dir, exist_ok=True)
    # map legacy 'yes' to 'baseline'
    norm_mode = 'baseline' if args.normalize == 'yes' else args.normalize

    use_macs = (args.throughput == 'mac')
    raw = build_raw_series(data, models, acc_keys_sorted, x_values, use_macs=use_macs)
    y_label = 'Throughput' if use_macs else 'Throughput'
    
    # 使用 normalize_y 参数控制纵坐标归一化
    plot_per_model_raw(raw, models, acc_keys_sorted, args.out_dir, x_min=args.x_min, x_max=args.x_max, 
                      y_label=y_label, normalize_y=args.normalize_y)
    plot_average_raw(raw, models, acc_keys_sorted, args.out_dir, x_min=args.x_min, x_max=args.x_max, 
                    y_label=y_label, normalize_y=args.normalize_y)

    print(f"Saved plots to {args.out_dir}")


if __name__ == '__main__':
    main()


