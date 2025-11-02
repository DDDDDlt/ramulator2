#!/usr/bin/env python3
"""
Plot PPL vs EDP scatter plots for multiple models
Read data from ppl_vs_edp.log file and generate side-by-side plots for each model
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

def create_ppl_vs_edp_plot(models_data, output_dir='.'):
    """
    Create PPL vs normalized EDP scatter plots for each model
    """
    if not models_data:
        print("No valid data found")
        return
    
    # Get all unique accelerator names across all models to create consistent color mapping
    all_accelerators = set()
    for data in models_data.values():
        for name, _, _ in data:
            all_accelerators.add(name)
    all_accelerators = sorted(list(all_accelerators))
    
    # Create color mapping with unique colors for each accelerator
    # Use a combination of colormaps to ensure all colors are unique
    colors = []
    # Use tab10 for first 10
    colors.extend(plt.cm.tab10(np.linspace(0, 1, min(10, len(all_accelerators)))))
    # Use Set3 for next 12
    if len(all_accelerators) > 10:
        colors.extend(plt.cm.Set3(np.linspace(0, 1, min(12, len(all_accelerators) - 10))))
    # Use Dark2 for additional colors
    if len(all_accelerators) > 22:
        colors.extend(plt.cm.Dark2(np.linspace(0, 1, len(all_accelerators) - 22)))
    
    color_map = {name: colors[i] for i, name in enumerate(all_accelerators)}
    
    print(f"Color mapping for {len(all_accelerators)} accelerators:")
    for name, color in color_map.items():
        print(f"  {name}: {color}")
    
    # Create subplots for each model with more spacing
    num_models = len(models_data)
    fig, axes = plt.subplots(1, num_models, figsize=(10.2 * num_models, 8))
    
    if num_models == 1:
        axes = [axes]  # Make it iterable for single subplot
    
    # Add more spacing between subplots and reserve room on the right for legend
    plt.subplots_adjust(wspace=0.50, left=0.1, right=0.85)
    
    model_names = list(models_data.keys())
    
    for idx, (model_name, data) in enumerate(models_data.items()):
        ax = axes[idx]
        
        if not data:
            continue
            
        # Extract data
        accelerator_names = [item[0] for item in data]
        ppl_values = [item[1] for item in data]
        edp_values = [item[2] for item in data]
        
        # Normalize EDP values
        normalized_edp = normalize_edp(edp_values)
        
        # Plot each point with consistent colors and specified markers
        for i, (name, ppl, edp) in enumerate(data):
            lname = name.lower()
            if 'bitmod' in lname:
                marker = '^'  # triangle
            elif 'olive' in lname:
                marker = 's'  # square
            elif 'flexposit' in lname:
                marker = 'o'  # circle
            else:
                marker = 'o'

            ax.scatter(normalized_edp[i], ppl, s=300, alpha=0.8, c=[color_map[name]],
                      marker=marker, edgecolors='black', linewidth=1.0, label=name)
        
        # Connect flexposit points with lines
        flexposit_data = [(name, ppl, edp) for name, ppl, edp in data if 'flexposit' in name.lower()]
        if len(flexposit_data) > 1:
            # Sort by version number for proper line connection
            flexposit_data.sort(key=lambda x: float(x[0].split('(')[1].split('b')[0]))
            # Get indices of flexposit data in the original data
            flexposit_indices = [i for i, (name, ppl, edp) in enumerate(data) if 'flexposit' in name.lower()]
            flexposit_normalized_edp = [normalized_edp[i] for i in flexposit_indices]
            flexposit_ppl = [item[1] for item in flexposit_data]
            ax.plot(flexposit_normalized_edp, flexposit_ppl, '--', color='red', alpha=0.7, linewidth=2, label='FlexPosit Series')
        
        # Set labels
        ax.set_xlabel('Normalized EDP', fontsize=14, fontweight='bold')
        ax.set_ylabel('Perplexity (PPL)', fontsize=14, fontweight='bold')
        
        # Add title below the plot with (a), (b) labels
        subplot_label = chr(97 + idx)  # 'a' for first subplot, 'b' for second, etc.
        ax.text(0.5, -0.15, f'({subplot_label}) {model_name}', 
                transform=ax.transAxes, ha='center', va='top', 
                fontsize=16, fontweight='bold')
        
        # Add grid with better visibility
        ax.grid(True, alpha=0.7, linestyle='-', linewidth=0.8, color='darkgray')
        ax.grid(True, alpha=0.5, linestyle='--', linewidth=0.5, color='gray', which='minor')
        
        # Set axis ranges - use normalized EDP values, focus on data range
        ax.set_xlim(min(normalized_edp) - 0.05, max(normalized_edp) + 0.05)
        ax.set_ylim(min(ppl_values) - 0.3, max(ppl_values) + 0.3)
        
        # Add legend on the right: larger font, adequate paddings to avoid overlap
        ax.legend(
            bbox_to_anchor=(1.02, 0.5), loc='center left', fontsize=12,
            ncol=1, frameon=True, fancybox=True, shadow=False,
            handletextpad=1.2, columnspacing=2.0, borderpad=1.2,
            labelspacing=1.0, markerscale=1.1
        )
        
        # Print data summary for this model
        print(f"\n{model_name} Data Summary:")
        print("-" * 60)
        print(f"{'Accelerator':<20} | {'PPL':<8} | {'EDP':<15}")
        print("-" * 60)
        for name, ppl, edp in zip(accelerator_names, ppl_values, edp_values):
            print(f"{name:<20} | {ppl:<8.2f} | {edp:<15,}")
    
    # Adjust layout - avoid tight_layout so that manual wspace remains effective
    
    # Save figure
    output_path = os.path.join(output_dir, 'ppl_vs_edp_multi_model.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"\nPlot saved to: {output_path}")
    
    # Also save as PDF
    pdf_path = os.path.join(output_dir, 'ppl_vs_edp_multi_model.pdf')
    plt.savefig(pdf_path, bbox_inches='tight', facecolor='white')
    print(f"PDF saved to: {pdf_path}")
    
    # Show plot
    plt.show()

def main():
    """
    Main function
    """
    # Log file path
    log_file = '/home/liangtaodai/dailt_workplace/ramulator2/flexposit_workplace/flexposit_sim/log/ppl_vs_edp.log'
    
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
    
    print(f"Found {len(models_data)} models: {list(models_data.keys())}")
    
    # Create plots
    output_dir = '/home/liangtaodai/dailt_workplace/ramulator2/flexposit_workplace/flexposit_sim/plot'
    create_ppl_vs_edp_plot(models_data, output_dir)

if __name__ == "__main__":
    main()
