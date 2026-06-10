#!/usr/bin/env python3
# plot_sweeps.py — Highlight zone + MixPosit PPL labels (below points) + PDF export

import argparse
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

def load_and_prepare(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    cols = {c.lower(): c for c in df.columns}
    def get(name):
        lname = name.lower()
        if name in df.columns:
            return name
        if lname in cols:
            return cols[lname]
        raise KeyError(f"Missing required column '{name}' in {path}. Found columns: {list(df.columns)}")
    df = df.rename(columns={get("achieved_avg_bits"): "achieved_avg_bits",
                            get("ppl"): "ppl"})
    df = df.sort_values("achieved_avg_bits").reset_index(drop=True)
    return df

def main():
    plt.rcParams.update({
        "font.size": 15,         # Base font size
        "axes.labelsize": 16,    # X/Y labels
        "axes.titlesize": 18,    # Title
        "legend.fontsize": 14,
        "xtick.labelsize": 13,
        "ytick.labelsize": 13,
    })

    ap = argparse.ArgumentParser(
        description="Plot PPL vs achieved_avg_bits with highlight and MixPosit labels; exports PNG and PDF."
    )
    ap.add_argument("--location", default="location.csv")
    ap.add_argument("--random",   default="random.csv")
    ap.add_argument("--mixposit", default="mixposit.csv")

    ap.add_argument("--title",   default="Phi-2 PPL vs Average Bits")
    ap.add_argument("--outfile", default="sweep_plot.png")  # PNG path
    ap.add_argument("--outpdf",  default=None,              # PDF path; default inferred from outfile
                    help="PDF output filename (default: same as --outfile but .pdf)")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--annotate-mixposit", action="store_true")

    ap.add_argument("--highlight-start", type=float, default=4.0)
    ap.add_argument("--highlight-end",   type=float, default=4.1)

    # Output toggles
    ap.add_argument("--no-png", action="store_true", help="Do not save PNG (save only PDF).")

    args = ap.parse_args()

    # Infer PDF filename if not provided
    if args.outpdf is None:
        out_pdf = str(Path(args.outfile).with_suffix(".pdf"))
    else:
        out_pdf = args.outpdf

    # Load data
    loc_df = load_and_prepare(args.location)
    rnd_df = load_and_prepare(args.random)
    mix_df = load_and_prepare(args.mixposit)

    # --- Plot ---
    plt.figure(figsize=(7.2, 4.3))
    ax = plt.gca()

    # Draw curves with different linestyles for better distinction
    # Draw other lines first, then red line on top
    # Colors with higher saturation for vivid appearance
    ax.plot(loc_df["achieved_avg_bits"], loc_df["ppl"],
            linestyle='--', marker="o", linewidth=2.0, markersize=7, 
            label="Location-guided", color="#1f77b4")  # Higher saturation blue
    ax.plot(rnd_df["achieved_avg_bits"], rnd_df["ppl"],
            linestyle='-.', marker="s", linewidth=2.0, markersize=7, 
            label="Random-guided", color="#2ca02c")  # Higher saturation green
    # Red line drawn last so it's on top
    ax.plot(mix_df["achieved_avg_bits"], mix_df["ppl"],
            linestyle='-', marker="^", linewidth=2.0, markersize=7, 
            label="Sensitivity-guided", color="#d62728", zorder=10)  # Higher saturation red

    # Get initial y-range and set bottom to -10 to make room for labels
    ymin_auto, ymax_auto = ax.get_ylim()
    
    # Set Y-axis bottom to -10 to provide space for labels below points
    ymin_adjusted = -10  # Set bottom to -10 for label space
    ymax_adjusted = ymax_auto * 1.02  # Small padding at top
    ax.set_ylim(ymin_adjusted, ymax_adjusted)
    
    # Recalculate y-range for label positioning
    ymin, ymax = ax.get_ylim()
    yrange = ymax - ymin
    
    # Annotate MixPosit points with PPL values below points
    for x, y in zip(mix_df["achieved_avg_bits"], mix_df["ppl"]):
        # Position label below the point, use absolute offset since we have -10 as bottom
        label_y = y - 8  # Even larger offset below point to move labels further down
        # Ensure label stays within bounds but with space above -10
        if label_y < -4:
            label_y = -4
        ax.text(x, label_y, f"{y:.2f}",
                fontsize=9, color="black", ha="center", va="top", zorder=11)

    # Highlight region (top label)
    ax.axvspan(args.highlight_start, args.highlight_end, color="gray", alpha=0.2, zorder=0)
    ax.text((args.highlight_start + args.highlight_end) / 2.0+0.28,
            ymax - 0.05 * yrange,
            r"Tight Budget ($\leq$ 4.1 b)",
            fontsize=14, color="black", ha="center", va="top")


    # Axes & style
    ax.set_xlabel("Achieved average bits")
    ax.set_ylabel("Perplexity (↓)")
    # Grid: both horizontal and vertical
    ax.grid(True, axis='both', linewidth=0.6, alpha=0.5)
    
    # Legend: inside plot, right side, slightly above middle
    legend = ax.legend(loc='center right', bbox_to_anchor=(1, 0.65), frameon=True, framealpha=0.8)
    legend.get_frame().set_linewidth(0.5)
    legend.get_frame().set_edgecolor('0.8')

    # Tight layout with extra bottom padding for labels
    plt.tight_layout(rect=[0, 0.06, 1, 1])

    # Save vector PDF (publication-ready)
    plt.savefig(out_pdf, bbox_inches="tight")  # PDF is vector by default
    if not args.no_png:
        plt.savefig(args.outfile, dpi=args.dpi, bbox_inches="tight")

    if args.show:
        plt.show()

if __name__ == "__main__":
    main()
