#!/usr/bin/env python3
"""
Plot PPL vs EDP scatter plot
Read data from ppl_vs_edp.log file and generate scatter plot
"""

import matplotlib.pyplot as plt
import numpy as np
import re
import os

def parse_log_file(log_file_path):
    """
    Parse log file to extract model names, PPL and EDP data for each model
    """
    models_data = {}
    current_model = None
    
    with open(log_file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('Model:'):
                current_model = line.split(':')[1].strip()
                models_data[current_model] = []
            elif line and not line.startswith('Model:'):
                # Parse format: model_name = [ppl, edp] (support parentheses and 'b' suffix)
                match = re.match(r'([^=]+?)\s*=\s*\[([\d.]+),\s*(\d+)\]', line)
                if match and current_model:
                    model_name = match.group(1)
                    ppl = float(match.group(2))
                    edp = int(match.group(3))
                    # Skip fp16 data point
                    if model_name != 'fp16':
                        models_data[current_model].append((model_name, ppl, edp))
    
    return models_data

def normalize_edp(edp_values):
    """
    Normalize EDP values to 0-1 range, where 0 stays 0
    """
    max_edp = max(edp_values)
    return [edp / max_edp for edp in edp_values]

def create_ppl_vs_edp_plot(data, output_dir='.', title=None):
    """
    Create PPL vs normalized EDP scatter plot
    """
    if not data:
        print("No valid data found")
        return
    
    # Extract data
    model_names = [item[0] for item in data]
    ppl_values = [item[1] for item in data]
    edp_values = [item[2] for item in data]
    
    # Normalize EDP values
    normalized_edp = normalize_edp(edp_values)
    
    # Create figure with balanced aspect ratio
    plt.figure(figsize=(9, 8))
    
    # Create scatter plot with individual colors for each point
    colors = plt.cm.tab10(np.linspace(0, 1, len(model_names)))
    
    # Plot each point individually for legend
    for i, (name, ppl, edp) in enumerate(data):
        plt.scatter(normalized_edp[i], ppl, s=300, alpha=0.8, c=[colors[i]], edgecolors='black', linewidth=1.0, label=name)
    
    # Connect flexposit points with lines
    flexposit_data = [(name, ppl, edp) for name, ppl, edp in data if 'flexposit' in name.lower()]
    if len(flexposit_data) > 1:
        # Sort by version number for proper line connection
        flexposit_data.sort(key=lambda x: float(x[0].split('(')[1].split('b')[0]))
        # Get indices of flexposit data in the original data
        flexposit_indices = [i for i, (name, ppl, edp) in enumerate(data) if 'flexposit' in name.lower()]
        flexposit_normalized_edp = [normalized_edp[i] for i in flexposit_indices]
        flexposit_ppl = [item[1] for item in flexposit_data]
        plt.plot(flexposit_normalized_edp, flexposit_ppl, '--', color='red', alpha=0.7, linewidth=2, label='FlexPosit Series')
    
    # Set labels and title
    plt.xlabel('Normalized EDP', fontsize=16, fontweight='bold')
    plt.ylabel('Perplexity', fontsize=16, fontweight='bold')
    plot_title = title if title is not None else 'PPL vs Normalized EDP Scatter Plot'
    plt.title(plot_title, fontsize=18, fontweight='bold', pad=20)
    
    # Set tick label font size
    plt.tick_params(labelsize=14)
    
    # Add grid with better visibility
    plt.grid(True, alpha=0.7, linestyle='-', linewidth=0.8, color='darkgray')
    plt.grid(True, alpha=0.5, linestyle='--', linewidth=0.5, color='gray', which='minor')
    
    # Set axis ranges - use normalized EDP values, focus on data range
    plt.xlim(min(normalized_edp) - 0.05, max(normalized_edp) + 0.05)
    plt.ylim(min(ppl_values) - 0.3, max(ppl_values) + 0.3)
    
    # Remove statistics text - no longer needed
    
    # Create legend with more space
    fig = plt.gcf()
    fig.set_size_inches(11, 9)  # Balanced aspect ratio
    
    # Add legend outside the plot with maximum spacing
    legend = plt.legend(
        bbox_to_anchor=(1.02, 0.5), loc='center left', fontsize=14,
        ncol=1, frameon=True, fancybox=True, shadow=False,
        handletextpad=1.2, columnspacing=2.0, borderpad=1.2,
        labelspacing=1.0, markerscale=1.1
    )
    
    # Add spacing between legend entries
    legend.get_frame().set_facecolor('white')
    legend.get_frame().set_alpha(0.9)
    
    # Reserve right margin so enlarged legend will not overlap content
    plt.subplots_adjust(right=0.85)
    
    # Arrow removed as requested
    
    # Adjust layout
    plt.tight_layout()
    
    # Save figure
    output_path = os.path.join(output_dir, 'ppl_vs_edp_scatter.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"Plot saved to: {output_path}")
    
    # Also save as PDF
    pdf_path = os.path.join(output_dir, 'ppl_vs_edp_scatter.pdf')
    plt.savefig(pdf_path, bbox_inches='tight', facecolor='white')
    print(f"PDF saved to: {pdf_path}")
    
    # Show plot
    plt.show()
    
    # Print data summary
    print("\nData Summary:")
    print("-" * 60)
    print(f"{'Model':<15} | {'PPL':<8} | {'EDP':<15}")
    print("-" * 60)
    for name, ppl, edp in zip(model_names, ppl_values, edp_values):
        print(f"{name:<15} | {ppl:<8.2f} | {edp:<15,}")

def main():
    """
    Main function
    """
    import argparse
    parser = argparse.ArgumentParser(description='PPL vs EDP scatter (single model)')
    parser.add_argument('--log', default='/home/liangtaodai/dailt_workplace/ramulator2/flexposit_workplace/flexposit_sim/log/ppl_vs_edp.log', help='log file path')
    parser.add_argument('--model', default=None, help='model name to plot (if multiple present)')
    parser.add_argument('--out-dir', default='/home/liangtaodai/dailt_workplace/ramulator2/flexposit_workplace/flexposit_sim/plot', help='output directory')
    args = parser.parse_args()

    # Log file path
    log_file = args.log
    
    # Check if file exists
    if not os.path.exists(log_file):
        print(f"Error: Log file not found: {log_file}")
        return
    
    # Parse data
    print("Parsing log file...")
    models_data = parse_log_file(log_file)

    if not models_data:
        print("No valid data found")
        return
    
    # Choose model data
    if isinstance(models_data, dict):
        if args.model is not None and args.model in models_data:
            model_name = args.model
            data = models_data[model_name]
        else:
            model_name = next(iter(models_data.keys()))
            data = models_data[model_name]
    else:
        model_name = 'Model'
        data = models_data

    if not data:
        print("Selected model has no data points")
        return
    
    print(f"Using model: {model_name} ({len(data)} data points)")
    
    # Create plot
    output_dir = args.out_dir
    os.makedirs(output_dir, exist_ok=True)
    create_ppl_vs_edp_plot(data, output_dir, title=f'PPL vs Normalized EDP ({model_name})')

if __name__ == "__main__":
    main()
