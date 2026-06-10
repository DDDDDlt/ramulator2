# #!/usr/bin/env python3
# """
# Plot PPL vs EDP scatter plots for multiple models
# Read data from ppl_vs_edp.log file and generate side-by-side plots for each model
# """

# import matplotlib.pyplot as plt
# from matplotlib.ticker import MultipleLocator, AutoMinorLocator
# from matplotlib.legend_handler import HandlerTuple, HandlerBase
# import numpy as np
# import re
# import os

# # Global counter to track handler calls
# _flexposit_handler_call_count = 0

# class HandlerHorizontalTuple(HandlerBase):
#     """
#     Custom handler to horizontally arrange multiple handles in legend
#     """
#     # Class-level set to track created handles across all instances
#     _created_handles = set()
    
#     def __init__(self, pad=0.1, **kwargs):
#         super().__init__(**kwargs)
#         self.pad = pad
    
#     def create_artists(self, legend, orig_handle,
#                        xdescent, ydescent, width, height, fontsize, trans):
#         global _flexposit_handler_call_count
        
#         # Check if already created to prevent duplicates using class-level tracking
#         handle_id = id(orig_handle)
        
#         # Use a more unique identifier: handle_id + legend object id
#         legend_id = id(legend) if legend else 0
#         unique_id = (handle_id, legend_id)
        
#         _flexposit_handler_call_count += 1
#         n_circles = len(orig_handle.facecolors) if hasattr(orig_handle, 'facecolors') else 'unknown'
#         print(f"DEBUG: Handler call #{_flexposit_handler_call_count} for handle {handle_id} in legend {legend_id}, creating {n_circles} circles")
        
#         if unique_id in HandlerHorizontalTuple._created_handles:
#             print(f"DEBUG: Already created, returning empty list")
#             return []  # Already created, return empty list
        
#         # Mark as created
#         HandlerHorizontalTuple._created_handles.add(unique_id)
        
#         # Get the handles from the tuple, wrapper, or composite class
#         # Handle FlexPositCircles class (preferred), wrapper class, or tuple
#         if hasattr(orig_handle, 'facecolors') and hasattr(orig_handle, 'sizes'):
#             # FlexPositCircles or FlexPositComposite class - use its properties directly
#             n = len(orig_handle.facecolors)
#             use_composite = True
#         elif hasattr(orig_handle, 'handles'):
#             # Wrapper class
#             handles = orig_handle.handles
#             n = len(handles)
#             use_composite = False
#         elif isinstance(orig_handle, tuple):
#             handles = orig_handle
#             n = len(handles)
#             use_composite = False
#         else:
#             handles = (orig_handle,) if orig_handle else ()
#             n = len(handles)
#             use_composite = False
        
#         if n == 0:
#             return []
        
#         # Calculate spacing between circles
#         # For 11 circles, we need larger spacing to prevent overlap
#         # Increase spacing by using a larger multiplier
#         spacing_multiplier = 6.0  # Increase spacing between circles (larger = more space)
#         base_spacing = width / max(n, 1)
        
#         # Calculate spacing between circle centers with increased distance
#         if n > 1:
#             # Use wider spacing to ensure circles don't overlap
#             spacing = base_spacing * spacing_multiplier
#             # Adjust starting position - move circles to the left
#             total_width = (n - 1) * spacing
#             # Use negative offset to move circles further left
#             start_offset = -width * 4.5  # Slightly less negative to move circles a bit right
#         else:
#             spacing = width
#             start_offset = -width * 4.5
        
#         artists = []
        
#         if use_composite:
#             # Use composite class properties directly
#             for i in range(n):
#                 # Position each circle horizontally, from left to right
#                 if n > 1:
#                     x_offset = xdescent + start_offset + i * spacing
#                     # Ensure circles don't go outside the legend box
#                     # Add some padding from the left edge
#                     min_x = xdescent + width * 0.05  # 5% padding from left
#                     x_offset = max(x_offset, min_x)
#                 else:
#                     x_offset = xdescent + width / 2
#                 # Center vertically
#                 y_offset = ydescent + height / 2
                
#                 # Get properties from composite class
#                 fc = orig_handle.facecolors[i] if i < len(orig_handle.facecolors) else 'blue'
#                 ec = orig_handle.edgecolors[i] if i < len(orig_handle.edgecolors) else 'black'
#                 lw = orig_handle.linewidths[i] if i < len(orig_handle.linewidths) else 1.0
#                 size = orig_handle.sizes[i] if i < len(orig_handle.sizes) else 300
#                 # Reduce circle size for legend
#                 size = size * 0.6  # Make circles smaller in legend
#                 alpha = orig_handle.alphas[i] if i < len(orig_handle.alphas) else 1.0
                
#                 # Create new scatter plot at the legend position
#                 scatter = plt.scatter([x_offset], [y_offset], 
#                                      s=size,
#                                      c=[fc],
#                                      edgecolors=ec,
#                                      linewidths=lw,
#                                      alpha=alpha,
#                                      marker='o',
#                                      transform=trans,
#                                      clip_on=False)
#                 artists.append(scatter)
#         else:
#             # Use handles from tuple or wrapper
#             for i, handle in enumerate(handles):
#                 # Position each circle horizontally, from left to right
#                 if n > 1:
#                     x_offset = xdescent + start_offset + i * spacing
#                     # Ensure circles don't go outside the legend box
#                     # Add some padding from the left edge
#                     min_x = xdescent + width * 0.05  # 5% padding from left
#                     x_offset = max(x_offset, min_x)
#                 else:
#                     x_offset = xdescent + width / 2
#                 # Center vertically
#                 y_offset = ydescent + height / 2
                
#                 # Create a copy of the handle's artist
#                 if hasattr(handle, 'get_offsets'):
#                     # For scatter plots (PathCollection)
#                     sizes = handle.get_sizes()
#                     facecolors = handle.get_facecolors()
#                     edgecolors = handle.get_edgecolors()
#                     linewidths = handle.get_linewidths()
#                     alphas = handle.get_alpha()
                    
#                     # Get marker style
#                     marker = handle.get_paths()[0] if hasattr(handle, 'get_paths') and len(handle.get_paths()) > 0 else 'o'
                    
#                     # Extract color values
#                     if len(facecolors) > 0:
#                         fc = facecolors[0] if facecolors.shape[0] > 0 else 'blue'
#                     else:
#                         fc = 'blue'
                    
#                     if len(edgecolors) > 0:
#                         ec = edgecolors[0] if edgecolors.shape[0] > 0 else 'black'
#                     else:
#                         ec = 'black'
                    
#                     lw = linewidths[0] if len(linewidths) > 0 else 1.0
#                     size = sizes[0] if len(sizes) > 0 else 300
#                     # Reduce circle size for legend
#                     size = size * 0.6  # Make circles smaller in legend
#                     alpha = alphas if isinstance(alphas, (int, float)) else (alphas[0] if hasattr(alphas, '__len__') and len(alphas) > 0 else 1.0)
                    
#                     # Create new scatter plot at the legend position
#                     scatter = plt.scatter([x_offset], [y_offset], 
#                                          s=size,
#                                          c=[fc],
#                                          edgecolors=ec,
#                                          linewidths=lw,
#                                          alpha=alpha,
#                                          marker=marker,
#                                          transform=trans,
#                                          clip_on=False)
#                     artists.append(scatter)
#                 else:
#                     # For other types, use the original handler
#                     handler = HandlerTuple()
#                     handler_artists = handler.create_artists(legend, orig_handle,
#                                                              xdescent, ydescent, width, height, fontsize, trans)
#                     artists.extend(handler_artists)
        
#         return artists

# def parse_log_file(log_file_path):
#     """
#     Parse log file to extract model names, PPL and EDP data for each model
#     """
#     models_data = {}
#     current_model = None
    
#     with open(log_file_path, 'r') as f:
#         for line in f:
#             line = line.strip()
#             if line.startswith('Model:'):
#                 current_model = line.split(':')[1].strip()
#                 models_data[current_model] = []
#             elif line and not line.startswith('Model:'):
#                 # Parse format: model_name = [ppl, edp] (support parentheses and 'b' suffix)
#                 match = re.match(r'([^=]+?)\s*=\s*\[([\d.]+),\s*(\d+)\]', line)
#                 if match and current_model:
#                     model_name = match.group(1)
#                     ppl = float(match.group(2))
#                     edp = int(match.group(3))
#                     # Skip fp16 data point
#                     if model_name != 'fp16':
#                         models_data[current_model].append((model_name, ppl, edp))
    
#     return models_data

# def normalize_edp(edp_values):
#     """
#     Normalize EDP values to 0-1 range, where 0 stays 0
#     """
#     max_edp = max(edp_values)
#     return [edp / max_edp for edp in edp_values]

# def create_ppl_vs_edp_plot(models_data, output_dir='.'):
#     """
#     Create PPL vs normalized EDP scatter plots for each model
#     """
#     if not models_data:
#         print("No valid data found")
#         return
    
#     # Get all unique accelerator names across all models to create consistent color mapping
#     all_accelerators = set()
#     for data in models_data.values():
#         for name, _, _ in data:
#             all_accelerators.add(name)
#     all_accelerators = sorted(list(all_accelerators))
    
#     # Create color mapping with unique colors for each accelerator
#     # Use a combination of colormaps to ensure all colors are unique
#     colors = []
#     # Use tab10 for first 10
#     colors.extend(plt.cm.tab10(np.linspace(0, 1, min(10, len(all_accelerators)))))
#     # Use Set3 for next 12
#     if len(all_accelerators) > 10:
#         colors.extend(plt.cm.Set3(np.linspace(0, 1, min(12, len(all_accelerators) - 10))))
#     # Use Dark2 for additional colors
#     if len(all_accelerators) > 22:
#         colors.extend(plt.cm.Dark2(np.linspace(0, 1, len(all_accelerators) - 22)))
    
#     color_map = {name: colors[i] for i, name in enumerate(all_accelerators)}
    
#     print(f"Color mapping for {len(all_accelerators)} accelerators:")
#     for name, color in color_map.items():
#         print(f"  {name}: {color}")
    
#     # Create subplots for each model with more spacing
#     num_models = len(models_data)
#     # Increase figure height to accommodate legends at the top
#     fig, axes = plt.subplots(1, num_models, figsize=(10.0 * num_models, 9.5))
    
#     if num_models == 1:
#         axes = [axes]  # Make it iterable for single subplot
    
#     # Add less spacing between subplots and reserve room at the top for legends
#     # Increase top margin to accommodate two legend rows
#     plt.subplots_adjust(wspace=0.35, left=0.1, right=0.95, top=0.70)
    
#     model_names = list(models_data.keys())
    
#     legend_handles = None
#     legend_labels = None
#     legend_ncol = None
#     # Collect all flexposit handles across all subplots (scatter points and lines)
#     # Use dictionary to avoid duplicates by name
#     all_flexposit_handles_dict = {}  # key: flexposit name, value: handle
#     all_flexposit_handles = []
#     all_flexposit_lines = []

#     for idx, (model_name, data) in enumerate(models_data.items()):
#         ax = axes[idx]
        
#         if not data:
#             continue
            
#         # Extract data
#         accelerator_names = [item[0] for item in data]
#         ppl_values = [item[1] for item in data]
#         edp_values = [item[2] for item in data]
        
#         # Normalize EDP values
#         normalized_edp = normalize_edp(edp_values)
        
#         # Plot each point with consistent colors and specified markers
#         for i, (name, ppl, edp) in enumerate(data):
#             lname = name.lower()
#             if 'bitmod' in lname:
#                 marker = '^'  # triangle
#             elif 'olive' in lname:
#                 marker = 's'  # square
#             elif 'flexposit' in lname:
#                 marker = 'o'  # circle
#             else:
#                 marker = 'o'

#             # For flexposit points, don't add label (will be handled separately)
#             # For other points, add label as usual
#             if 'flexposit' in lname:
#                 scatter_handle = ax.scatter(normalized_edp[i], ppl, s=300, alpha=0.8, c=[color_map[name]],
#                           marker=marker, edgecolors='black', linewidth=1.0)
#                 # Collect flexposit handles for legend, avoid duplicates by name
#                 if name not in all_flexposit_handles_dict:
#                     all_flexposit_handles_dict[name] = scatter_handle
#             else:
#                 ax.scatter(normalized_edp[i], ppl, s=300, alpha=0.8, c=[color_map[name]],
#                           marker=marker, edgecolors='black', linewidth=1.0, label=name)
        
#         # Connect flexposit points with lines (but don't add to legend yet)
#         flexposit_data = [(name, ppl, edp) for name, ppl, edp in data if 'flexposit' in name.lower()]
#         series_line = None
#         if len(flexposit_data) > 1:
#             # Sort by version number for proper line connection
#             flexposit_data.sort(key=lambda x: float(x[0].split('(')[1].split('b')[0]))
#             # Get indices of flexposit data in the original data
#             flexposit_indices = [i for i, (name, ppl, edp) in enumerate(data) if 'flexposit' in name.lower()]
#             flexposit_normalized_edp = [normalized_edp[i] for i in flexposit_indices]
#             flexposit_ppl = [item[1] for item in flexposit_data]
#             # Don't add label for the line, will be merged into FlexPosit legend
#             series_line = ax.plot(flexposit_normalized_edp, flexposit_ppl, '--', color='red', alpha=0.7, linewidth=2)[0]
#             # Collect flexposit line handles for legend (only once, all lines have same style)
#             if not all_flexposit_lines:
#                 all_flexposit_lines.append(series_line)
        
#         # Set labels with larger font
#         ax.set_xlabel('Normalized EDP', fontsize=28, fontweight='bold')
#         ax.set_ylabel('Perplexity', fontsize=28, fontweight='bold')
        
#         # Set tick label font size
#         ax.tick_params(labelsize=26)
        
#         # Set axis ranges - use normalized EDP values, focus on data range
#         ax.set_xlim(min(normalized_edp) - 0.05, max(normalized_edp) + 0.05)
#         ax.set_ylim(min(ppl_values) - 0.3, max(ppl_values) + 0.3)
        
#         # Set minor tick locators to make grid denser and well-aligned
#         # Use AutoMinorLocator with n=2 to create 2 minor ticks between major ticks
#         ax.xaxis.set_minor_locator(AutoMinorLocator(n=2))
#         ax.yaxis.set_minor_locator(AutoMinorLocator(n=2))
        
#         # Add grid with better visibility
#         ax.grid(True, alpha=0.7, linestyle='-', linewidth=0.8, color='darkgray')
#         ax.grid(True, alpha=0.4, linestyle='--', linewidth=0.4, color='lightgray', which='minor')
        
#         # Add title below the plot with (a), (b) labels
#         subplot_label = chr(97 + idx)  # 'a' for first subplot, 'b' for second, etc.
#         ax.text(0.5, -0.15, f'({subplot_label}) {model_name}', 
#                 transform=ax.transAxes, ha='center', va='top', 
#                 fontsize=30, fontweight='bold')
        
#         # Get all legend handles and labels (flexposit items won't have labels now)
#         handles, labels = ax.get_legend_handles_labels()
        
#         # Remove any existing legend
#         if ax.get_legend() is not None:
#             ax.get_legend().remove()
        
#         # All handles should be non-flexposit items (flexposit items don't have labels)
#         ordered_handles = handles
#         ordered_labels = labels
        
#         # Reorder for row-major layout (instead of column-major)
#         # matplotlib legend fills by columns, but we want row-major order
#         legend_ncol = min(max(len(ordered_handles), 1), 6) if legend_ncol is None else legend_ncol
#         ncol = legend_ncol
#         n_items = len(ordered_handles)
#         n_rows = (n_items + ncol - 1) // ncol  # Ceiling division
        
#         # Create a 2D grid in row-major order (row by row, left to right)
#         # This is how we want the legend to appear visually
#         grid_handles = [[None] * ncol for _ in range(n_rows)]
#         grid_labels = [[None] * ncol for _ in range(n_rows)]
        
#         for idx in range(n_items):
#             row = idx // ncol
#             col = idx % ncol
#             grid_handles[row][col] = ordered_handles[idx]
#             grid_labels[row][col] = ordered_labels[idx]
        
#         # Convert from row-major grid to column-major list for matplotlib
#         # matplotlib fills by columns, so we need to read column by column
#         column_major_handles = []
#         column_major_labels = []
#         for col in range(ncol):
#             for row in range(n_rows):
#                 if grid_handles[row][col] is not None:
#                     column_major_handles.append(grid_handles[row][col])
#                     column_major_labels.append(grid_labels[row][col])
        
#         if legend_handles is None:
#             legend_handles = column_major_handles
#             legend_labels = column_major_labels
        
#         # Print data summary for this model
#         print(f"\n{model_name} Data Summary:")
#         print("-" * 60)
#         print(f"{'Accelerator':<20} | {'PPL':<8} | {'EDP':<15}")
#         print("-" * 60)
#         for name, ppl, edp in zip(accelerator_names, ppl_values, edp_values):
#             print(f"{name:<20} | {ppl:<8.2f} | {edp:<15,}")
    
#     # Filter flexposit handles to only include 4.0-5.0b range
#     def extract_version(name):
#         """Extract version number from flexposit name like 'flexposit(4.0b)'"""
#         try:
#             if '(' in name and 'b' in name:
#                 version_str = name.split('(')[1].split('b')[0]
#                 return float(version_str)
#         except:
#             pass
#         return None
    
#     # Filter handles for 4.0-5.0b range
#     filtered_flexposit_handles_dict = {}
#     for name, handle in all_flexposit_handles_dict.items():
#         version = extract_version(name)
#         if version is not None and 4.0 <= version <= 5.0:
#             filtered_flexposit_handles_dict[name] = handle
    
#     # Convert filtered flexposit handles dictionary to list, sorted by name for consistent order
#     all_flexposit_handles = [filtered_flexposit_handles_dict[name] for name in sorted(filtered_flexposit_handles_dict.keys())]
    
#     # Debug: print number of flexposit handles
#     print(f"\nDebug: Number of filtered flexposit handles (4.0-5.0b): {len(all_flexposit_handles)}")
#     print(f"Debug: Filtered Flexposit names: {sorted(filtered_flexposit_handles_dict.keys())}")
    
#     # Separate FlexPosit items from other legend items
#     flexposit_handles = []
#     flexposit_labels = []
#     other_handles = []
#     other_labels = []
    
#     # Add combined FlexPosit legend entry with filtered scatter handles (4.0-5.0b only)
#     # Create a single scatter plot with all circles positioned horizontally for legend
#     if all_flexposit_handles:
#         # Extract all properties from handles
#         all_facecolors = []
#         all_edgecolors = []
#         all_sizes = []
#         all_linewidths = []
#         all_alphas = []
        
#         for handle in all_flexposit_handles:
#             if hasattr(handle, 'get_facecolors'):
#                 sizes = handle.get_sizes()
#                 facecolors = handle.get_facecolors()
#                 edgecolors = handle.get_edgecolors()
#                 linewidths = handle.get_linewidths()
#                 alphas = handle.get_alpha()
                
#                 all_sizes.append(sizes[0] if len(sizes) > 0 else 300)
#                 if len(facecolors) > 0:
#                     fc = facecolors[0] if facecolors.shape[0] > 0 else 'blue'
#                     all_facecolors.append(fc)
#                 else:
#                     all_facecolors.append('blue')
#                 if len(edgecolors) > 0:
#                     ec = edgecolors[0] if edgecolors.shape[0] > 0 else 'black'
#                     all_edgecolors.append(ec)
#                 else:
#                     all_edgecolors.append('black')
#                 all_linewidths.append(linewidths[0] if len(linewidths) > 0 else 1.0)
#                 if isinstance(alphas, (int, float)):
#                     all_alphas.append(alphas)
#                 elif hasattr(alphas, '__len__') and len(alphas) > 0:
#                     all_alphas.append(alphas[0])
#                 else:
#                     all_alphas.append(1.0)
        
#         # Create a simple composite object for custom handler
#         class FlexPositCircles:
#             def __init__(self, facecolors, edgecolors, sizes, linewidths, alphas):
#                 self.facecolors = facecolors
#                 self.edgecolors = edgecolors
#                 self.sizes = sizes
#                 self.linewidths = linewidths
#                 self.alphas = alphas
        
#         flexposit_circles = FlexPositCircles(
#             all_facecolors,
#             all_edgecolors,
#             all_sizes,
#             all_linewidths,
#             all_alphas
#         )
#         flexposit_handles.append(flexposit_circles)
#         flexposit_labels.append('FlexPosit')
    
#     # Add FlexPosit Series line as a separate legend entry
#     if all_flexposit_lines:
#         # Use the first line handle as representative (all lines have same style)
#         flexposit_handles.append(all_flexposit_lines[0])
#         flexposit_labels.append('FlexPosit Series')
    
#     # Separate other handles from flexposit
#     if legend_handles:
#         for handle, label in zip(legend_handles, legend_labels):
#             # Skip any flexposit-related items that might have been added
#             if label not in ['FlexPosit', 'FlexPosit Series']:
#                 other_handles.append(handle)
#                 other_labels.append(label)
    
#     # Clear the created handles set before creating legends
#     HandlerHorizontalTuple._created_handles.clear()
    
#     # Create handler map for FlexPosit handles
#     handler_map = {}
#     for handle in flexposit_handles:
#         # Check if it's FlexPositCircles class
#         if hasattr(handle, 'facecolors') and hasattr(handle, 'sizes'):
#             # Use custom handler to horizontally arrange circles
#             # pad controls spacing between circles - increased for 11 circles
#             handler_map[handle] = HandlerHorizontalTuple(pad=2.0)
    
#     # Create two separate legends: one for other items, one for FlexPosit items
#     if other_handles and other_labels:
#         # First legend: other items in one row
#         ncol_other = len(other_handles)
#         fig.legend(
#             other_handles,
#             other_labels,
#             bbox_to_anchor=(0.5, 1.0),
#             loc='upper center',
#             fontsize=20,
#             ncol=ncol_other,
#             frameon=True,
#             fancybox=True,
#             shadow=False,
#             handletextpad=0.5,
#             columnspacing=1.2,
#             borderpad=0.8,
#             labelspacing=0.5,
#             markerscale=1.2
#         )
    
#     # Add FlexPosit legend for 4.0-5.0b range and series
#     if flexposit_handles and flexposit_labels:
#         # Second legend: FlexPosit items in one row, placed below the first legend
#         ncol_flexposit = len(flexposit_handles)
#         # Calculate y position for second legend (below first legend)
#         # Adjust based on whether first legend exists
#         if other_handles:
#             y_pos = 0.90  # Below first legend
#         else:
#             y_pos = 1.0  # Top if no first legend
#         fig.legend(
#             flexposit_handles,
#             flexposit_labels,
#             bbox_to_anchor=(0.5, y_pos, 1.2, 0.1),  # (x, y, width, height) - wider box (width=1.2)
#             loc='upper center',
#             fontsize=16,  # Reduced from 20
#             ncol=ncol_flexposit,
#             frameon=True,
#             fancybox=True,
#             shadow=False,
#             handletextpad=1.5,  # Reduced from 2.5
#             columnspacing=1.5,  # Reduced from 2.0
#             borderpad=1.2,  # Reduced from 2.0
#             labelspacing=0.3,  # Reduced from 0.5
#             markerscale=0.8,  # Reduced from 1.2 to make circles smaller
#             handler_map=handler_map
#         )
    
#     # Save figure
#     output_path = os.path.join(output_dir, 'ppl_vs_edp_multi_model.png')
#     plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
#     print(f"\nPlot saved to: {output_path}")
    
#     # Also save as PDF
#     pdf_path = os.path.join(output_dir, 'ppl_vs_edp_multi_model.pdf')
#     plt.savefig(pdf_path, bbox_inches='tight', facecolor='white')
#     print(f"PDF saved to: {pdf_path}")
    
#     # Show plot
#     plt.show()

# def main():
#     """
#     Main function
#     """
#     # Log file path
#     log_file = '/home/liangtaodai/dailt_workplace/ramulator2/flexposit_workplace/flexposit_sim/log/ppl_vs_edp.log'
    
#     # Check if file exists
#     if not os.path.exists(log_file):
#         print(f"Error: Log file not found: {log_file}")
#         return
    
#     # Parse data
#     print("Parsing log file...")
#     models_data = parse_log_file(log_file)
    
#     if not models_data:
#         print("No valid data found")
#         return
    
#     print(f"Found {len(models_data)} models: {list(models_data.keys())}")
    
#     # Create plots
#     output_dir = '/home/liangtaodai/dailt_workplace/ramulator2/flexposit_workplace/flexposit_sim/plot'
#     create_ppl_vs_edp_plot(models_data, output_dir)

# if __name__ == "__main__":
#     main()


#!/usr/bin/env python3
"""
Plot PPL vs EDP scatter plots for multiple models
Read data from ppl_vs_edp.log file and generate side-by-side plots for each model
"""

import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, AutoMinorLocator
from matplotlib.legend_handler import HandlerTuple, HandlerBase
from matplotlib.lines import Line2D
import numpy as np
import re
import os

# Global counter to track handler calls
_flexposit_handler_call_count = 0

class HandlerHorizontalTuple(HandlerBase):
    """
    Custom handler to horizontally arrange multiple handles in legend
    """
    # Class-level set to track created handles across all instances
    _created_handles = set()
    
    def __init__(self, pad=0.1, **kwargs):
        super().__init__(**kwargs)
        self.pad = pad
    
    def create_artists(self, legend, orig_handle,
                       xdescent, ydescent, width, height, fontsize, trans):
        global _flexposit_handler_call_count
        
        # Check if already created to prevent duplicates using class-level tracking
        # Use ONLY handle_id to prevent duplicates across different legend objects
        # This is critical because fig.legend() creates multiple legend objects internally
        # (for layout calculation and actual rendering), causing legend_id to differ
        handle_id = id(orig_handle)
        legend_id = id(legend) if legend else 0
        
        _flexposit_handler_call_count += 1
        n_circles = len(orig_handle.facecolors) if hasattr(orig_handle, 'facecolors') else 'unknown'
        print(f"DEBUG: Handler call #{_flexposit_handler_call_count} for handle {handle_id}, legend_id={legend_id}, creating {n_circles} circles")
        
        # ✅ 只用 handle_id 去重
        if handle_id in HandlerHorizontalTuple._created_handles:
            print(f"DEBUG: Already created (handle_id={handle_id} in set), returning empty list. Set contents: {HandlerHorizontalTuple._created_handles}")
            return []  # Already created, return empty list
        
        # Mark as created
        HandlerHorizontalTuple._created_handles.add(handle_id)
        print(f"DEBUG: Marked as created, handle_id={handle_id} added to set (set size now: {len(HandlerHorizontalTuple._created_handles)})")
        
        # Get the handles from the tuple, wrapper, or composite class
        # Handle FlexPositCircles class (preferred), wrapper class, or tuple
        if hasattr(orig_handle, 'facecolors') and hasattr(orig_handle, 'sizes'):
            # FlexPositCircles or FlexPositComposite class - use its properties directly
            n = len(orig_handle.facecolors)
            use_composite = True
        elif hasattr(orig_handle, 'handles'):
            # Wrapper class
            handles = orig_handle.handles
            n = len(handles)
            use_composite = False
        elif isinstance(orig_handle, tuple):
            handles = orig_handle
            n = len(handles)
            use_composite = False
        else:
            handles = (orig_handle,) if orig_handle else ()
            n = len(handles)
            use_composite = False
        
        if n == 0:
            return []
        
        # Calculate spacing between circles
        # For 11 circles, we need larger spacing to prevent overlap
        # Increase spacing by using a larger multiplier
        spacing_multiplier = 6.0  # Increase spacing between circles (larger = more space)
        base_spacing = width / max(n, 1)
        
        # Calculate spacing between circle centers with increased distance
        if n > 1:
            # Use wider spacing to ensure circles don't overlap
            spacing = base_spacing * spacing_multiplier
            # Adjust starting position to center the group
            total_width = (n - 1) * spacing
            start_offset = (width - total_width) / 2
        else:
            spacing = width
            start_offset = 0
        
        artists = []
        
        if use_composite:
            # Use composite class properties directly
            for i in range(n):
                # Position each circle horizontally, from left to right
                if n > 1:
                    x_offset = xdescent + start_offset + i * spacing
                else:
                    x_offset = xdescent + width / 2
                # Center vertically
                y_offset = ydescent + height / 2
                
                # Get properties from composite class
                fc = orig_handle.facecolors[i] if i < len(orig_handle.facecolors) else 'blue'
                ec = orig_handle.edgecolors[i] if i < len(orig_handle.edgecolors) else 'black'
                lw = orig_handle.linewidths[i] if i < len(orig_handle.linewidths) else 1.0
                size = orig_handle.sizes[i] if i < len(orig_handle.sizes) else 300
                alpha = orig_handle.alphas[i] if i < len(orig_handle.alphas) else 1.0
                
                # Create new scatter plot at the legend position
                scatter = plt.scatter([x_offset], [y_offset], 
                                     s=size,
                                     c=[fc],
                                     edgecolors=ec,
                                     linewidths=lw,
                                     alpha=alpha,
                                     marker='o',
                                     transform=trans,
                                     clip_on=False)
                artists.append(scatter)
        else:
            # Use handles from tuple or wrapper
            for i, handle in enumerate(handles):
                # Position each circle horizontally, from left to right
                if n > 1:
                    x_offset = xdescent + start_offset + i * spacing
                else:
                    x_offset = xdescent + width / 2
                # Center vertically
                y_offset = ydescent + height / 2
                
                # Create a copy of the handle's artist
                if hasattr(handle, 'get_offsets'):
                    # For scatter plots (PathCollection)
                    sizes = handle.get_sizes()
                    facecolors = handle.get_facecolors()
                    edgecolors = handle.get_edgecolors()
                    linewidths = handle.get_linewidths()
                    alphas = handle.get_alpha()
                    
                    # Get marker style
                    marker = handle.get_paths()[0] if hasattr(handle, 'get_paths') and len(handle.get_paths()) > 0 else 'o'
                    
                    # Extract color values
                    if len(facecolors) > 0:
                        fc = facecolors[0] if facecolors.shape[0] > 0 else 'blue'
                    else:
                        fc = 'blue'
                    
                    if len(edgecolors) > 0:
                        ec = edgecolors[0] if edgecolors.shape[0] > 0 else 'black'
                    else:
                        ec = 'black'
                    
                    lw = linewidths[0] if len(linewidths) > 0 else 1.0
                    size = sizes[0] if len(sizes) > 0 else 300
                    alpha = alphas if isinstance(alphas, (int, float)) else (alphas[0] if hasattr(alphas, '__len__') and len(alphas) > 0 else 1.0)
                    
                    # Create new scatter plot at the legend position
                    scatter = plt.scatter([x_offset], [y_offset], 
                                         s=size,
                                         c=[fc],
                                         edgecolors=ec,
                                         linewidths=lw,
                                         alpha=alpha,
                                         marker=marker,
                                         transform=trans,
                                         clip_on=False)
                    artists.append(scatter)
                else:
                    # For other types, use the original handler
                    handler = HandlerTuple()
                    handler_artists = handler.create_artists(legend, orig_handle,
                                                             xdescent, ydescent, width, height, fontsize, trans)
                    artists.extend(handler_artists)
        
        print(f"DEBUG: create_artists returning {len(artists)} artists for handle {id(orig_handle)}")
        return artists

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
    # 先使用几套默认 colormap 保证不同加速器之间颜色可区分
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

    # 覆盖 BitMoD / OliVe 的颜色（参考 auto_hw_metrics_add_edp.py）
    for name in all_accelerators:
        lname = name.lower()
        if 'bitmod' in lname:
            # BitMoD：与 auto_hw_metrics_add_edp.py 保持一致的暖橙色 #F4A261
            color_map[name] = np.array([244/255.0, 162/255.0, 97/255.0])
        elif 'olive_a8w8' in lname:
            # OliVe_a8w8：与 auto_hw_metrics_add_edp.py 中 Olive 的深青蓝 #457B9D 保持一致
            color_map[name] = np.array([69/255.0, 123/255.0, 157/255.0])
        elif 'olive_a4w4' in lname:
            # OliVe_a4w4：稍微浅一点的紫色
            color_map[name] = np.array([0.65, 0.35, 0.85])

    # 覆盖 FlexPosit 系列的颜色：按版本号从 4.0b → 5.0b，使用原先的纯绿色渐变
    flexposit_names = [name for name in all_accelerators if 'flexposit' in name.lower()]
    if flexposit_names:
        # 按版本号排序，确保 4.0b 在最左、5.0b 在最右
        def _extract_flex_version(n):
            try:
                if '(' in n and 'b' in n:
                    return float(n.split('(')[1].split('b')[0])
            except Exception:
                return None
            return None

        flexposit_names = sorted(
            flexposit_names,
            key=lambda n: (_extract_flex_version(n) is None, _extract_flex_version(n) or 0.0)
        )

        n_fp = len(flexposit_names)
        # 定义从浅绿到深绿的线性渐变：浅绿(0.85, 1.0, 0.85) → 深绿(0.0, 0.55, 0.0)
        start_color = np.array([0.85, 1.0, 0.85])
        end_color = np.array([0.0, 0.55, 0.0])
        if n_fp == 1:
            color_map[flexposit_names[0]] = start_color
        else:
            for idx, name in enumerate(flexposit_names):
                t = idx / (n_fp - 1)
                color = (1 - t) * start_color + t * end_color
                color_map[name] = color
    
    print(f"Color mapping for {len(all_accelerators)} accelerators:")
    for name, color in color_map.items():
        print(f"  {name}: {color}")
    
    # Create subplots for each model
    num_models = len(models_data)
    # 再稍微增加子图高度，让长宽比更接近正方形（相比最初 9.5 仍略矮）
    fig, axes = plt.subplots(1, num_models, figsize=(9.0 * num_models, 9.0))
    
    if num_models == 1:
        axes = [axes]  # Make it iterable for single subplot
    
    # Add less spacing between subplots，并在顶部留出两行图例的空间
    # wspace 调小，让两张图靠得更紧；top 调整图例与子图整体距离
    plt.subplots_adjust(wspace=0.22, left=0.1, right=0.95, top=0.82)
    
    model_names = list(models_data.keys())
    
    legend_handles = None
    legend_labels = None
    legend_ncol = None
    # Collect all flexposit handles across all subplots (scatter points and lines)
    # Use dictionary to avoid duplicates by name
    all_flexposit_handles_dict = {}  # key: flexposit name, value: handle
    all_flexposit_handles = []
    all_flexposit_lines = []

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

            # BitMoD 的三角形稍微大一点，其它保持原大小
            if 'bitmod' in lname:
                scatter_size = 380
            else:
                scatter_size = 300

            # For flexposit points, don't add label (will be handled separately)
            # For other points, add label as usual
            if 'flexposit' in lname:
                scatter_handle = ax.scatter(normalized_edp[i], ppl, s=scatter_size, alpha=0.8, c=[color_map[name]],
                          marker=marker, edgecolors='black', linewidth=1.0)
                # Collect flexposit handles for legend, avoid duplicates by name
                if name not in all_flexposit_handles_dict:
                    all_flexposit_handles_dict[name] = scatter_handle
            else:
                ax.scatter(normalized_edp[i], ppl, s=scatter_size, alpha=0.8, c=[color_map[name]],
                          marker=marker, edgecolors='black', linewidth=1.0, label=name)
        
        # Connect flexposit points with lines (but don't add to legend yet)
        flexposit_data = [(name, ppl, edp) for name, ppl, edp in data if 'flexposit' in name.lower()]
        series_line = None
        if len(flexposit_data) > 1:
            # Sort by version number for proper line connection
            flexposit_data.sort(key=lambda x: float(x[0].split('(')[1].split('b')[0]))
            # Get indices of flexposit data in the original data
            flexposit_indices = [i for i, (name, ppl, edp) in enumerate(data) if 'flexposit' in name.lower()]
            flexposit_normalized_edp = [normalized_edp[i] for i in flexposit_indices]
            flexposit_ppl = [item[1] for item in flexposit_data]
            # Don't add label for the line, will be merged into FlexPosit legend
            # 改为黑色虚线
            series_line = ax.plot(flexposit_normalized_edp, flexposit_ppl, '--', color='black', alpha=0.7, linewidth=2)[0]
            # Collect flexposit line handles for legend (only once, all lines have same style)
            if not all_flexposit_lines:
                all_flexposit_lines.append(series_line)
        
        # Set labels with larger font
        ax.set_xlabel('Normalized EDP', fontsize=28, fontweight='bold')
        ax.set_ylabel('Perplexity', fontsize=28, fontweight='bold')
        
        # Set tick label font size
        ax.tick_params(labelsize=26)
        
        # Set axis ranges - use normalized EDP values, focus on data range
        ax.set_xlim(min(normalized_edp) - 0.05, max(normalized_edp) + 0.05)
        ax.set_ylim(min(ppl_values) - 0.3, max(ppl_values) + 0.3)
        
        # Set minor tick locators to make grid denser and well-aligned
        # Use AutoMinorLocator with n=2 to create 2 minor ticks between major ticks
        ax.xaxis.set_minor_locator(AutoMinorLocator(n=2))
        ax.yaxis.set_minor_locator(AutoMinorLocator(n=2))
        
        # Add grid with better visibility
        ax.grid(True, alpha=0.7, linestyle='-', linewidth=0.8, color='darkgray')
        ax.grid(True, alpha=0.4, linestyle='--', linewidth=0.4, color='lightgray', which='minor')
        
        # Add title below the plot with (a), (b) labels
        subplot_label = chr(97 + idx)  # 'a' for first subplot, 'b' for second, etc.
        ax.text(0.5, -0.15, f'({subplot_label}) {model_name}', 
                transform=ax.transAxes, ha='center', va='top', 
                fontsize=30, fontweight='bold')
        
        # Get all legend handles and labels (flexposit items won't have labels now)
        handles, labels = ax.get_legend_handles_labels()
        
        # Remove any existing legend
        if ax.get_legend() is not None:
            ax.get_legend().remove()
        
        # All handles should be non-flexposit items (flexposit items don't have labels)
        ordered_handles = handles
        ordered_labels = labels
        
        # Reorder for row-major layout (instead of column-major)
        # matplotlib legend fills by columns, but we want row-major order
        legend_ncol = min(max(len(ordered_handles), 1), 6) if legend_ncol is None else legend_ncol
        ncol = legend_ncol
        n_items = len(ordered_handles)
        n_rows = (n_items + ncol - 1) // ncol  # Ceiling division
        
        # Create a 2D grid in row-major order (row by row, left to right)
        # This is how we want the legend to appear visually
        grid_handles = [[None] * ncol for _ in range(n_rows)]
        grid_labels = [[None] * ncol for _ in range(n_rows)]
        
        for idx in range(n_items):
            row = idx // ncol
            col = idx % ncol
            grid_handles[row][col] = ordered_handles[idx]
            grid_labels[row][col] = ordered_labels[idx]
        
        # Convert from row-major grid to column-major list for matplotlib
        # matplotlib fills by columns, so we need to read column by column
        column_major_handles = []
        column_major_labels = []
        for col in range(ncol):
            for row in range(n_rows):
                if grid_handles[row][col] is not None:
                    column_major_handles.append(grid_handles[row][col])
                    column_major_labels.append(grid_labels[row][col])
        
        if legend_handles is None:
            legend_handles = column_major_handles
            legend_labels = column_major_labels
        
        # Print data summary for this model
        print(f"\n{model_name} Data Summary:")
        print("-" * 60)
        print(f"{'Accelerator':<20} | {'PPL':<8} | {'EDP':<15}")
        print("-" * 60)
        for name, ppl, edp in zip(accelerator_names, ppl_values, edp_values):
            print(f"{name:<20} | {ppl:<8.2f} | {edp:<15,}")
    
    # Filter flexposit handles to only include 4.0-5.0b range
    def extract_version(name):
        """Extract version number from flexposit name like 'flexposit(4.0b)'"""
        try:
            if '(' in name and 'b' in name:
                version_str = name.split('(')[1].split('b')[0]
                return float(version_str)
        except:
            pass
        return None
    
    # Filter handles for 4.0-5.0b range
    filtered_flexposit_handles_dict = {}
    for name, handle in all_flexposit_handles_dict.items():
        version = extract_version(name)
        if version is not None and 4.0 <= version <= 5.0:
            filtered_flexposit_handles_dict[name] = handle
    
    # Convert filtered flexposit handles dictionary to list, sorted by name for consistent order
    all_flexposit_handles = [filtered_flexposit_handles_dict[name] for name in sorted(filtered_flexposit_handles_dict.keys())]
    
    # Debug: print number of flexposit handles
    print(f"\nDebug: Number of filtered flexposit handles (4.0-5.0b): {len(all_flexposit_handles)}")
    print(f"Debug: Filtered Flexposit names: {sorted(filtered_flexposit_handles_dict.keys())}")
    
    # Separate FlexPosit items from other legend items
    flexposit_handles = []
    flexposit_labels = []
    other_handles = []
    other_labels = []

    # Separate other handles from flexposit（先收集其它模型）
    if legend_handles:
        for handle, label in zip(legend_handles, legend_labels):
            # Skip any flexposit-related items that might have been added
            if label not in ['FlexPosit', 'FlexPosit Series']:
                other_handles.append(handle)
                other_labels.append(label)

    # Add FlexPosit Series line as a separate legend entry
    # 放到第一行的最右侧：在其它模型之后 append
    if all_flexposit_lines:
        # Use the first line handle as representative (all lines have same style)
        series_handle = all_flexposit_lines[0]
        other_handles.append(series_handle)
        other_labels.append('FlexPosit Series')
    
    # ---------- Legend layout ----------
    # 新布局：
    # - 只用一个 legend
    # - 5 个图例项：BitMoD / OliVe_a8w8 / OliVe_a4w4 / FlexPosit(空心圆) / FlexPosit Series
    # - 全部放在一行，间距减小

    legend_handles_all = []
    legend_labels_all = []

    # 先放其它模型（不包含 FlexPosit Series），再放 FlexPosit，最后放 FlexPosit Series
    series_handle_for_legend = None
    if other_handles and other_labels:
        for h, lab in zip(other_handles, other_labels):
            if lab == 'FlexPosit Series':
                series_handle_for_legend = h
            else:
                # 美化 OliVe 的图例文字：去掉下划线、参数放到括号里
                pretty_label = lab
                if lab == 'OliVe_a8w8':
                    pretty_label = 'OliVe (a8w8)'
                elif lab == 'OliVe_a4w4':
                    pretty_label = 'OliVe (a4w4)'

                legend_handles_all.append(h)
                legend_labels_all.append(pretty_label)

    # 再追加一个 FlexPosit 的圆形图例项（再略深一点的绿色，与渐变风格统一）
    if all_flexposit_handles:
        base_color = np.array([0.45, 0.72, 0.45])  # 再稍微偏深一些的绿色
        flexposit_legend_handle = Line2D(
            [], [],
            linestyle='none',
            marker='o',
            markerfacecolor=base_color,                      # 适中偏深的绿色填充
            markeredgecolor=np.array([0.18, 0.45, 0.18]),    # 更深一点的边框
            markeredgewidth=1.5,
            markersize=18,                                   # 保持当前大小
        )
        legend_handles_all.append(flexposit_legend_handle)
        legend_labels_all.append('FlexPosit (4.0-5.0b, step=0.1b)')

    # 最后追加 FlexPosit Series，使其出现在最右边
    if series_handle_for_legend is not None:
        legend_handles_all.append(series_handle_for_legend)
        legend_labels_all.append('FlexPosit Series')

    if legend_handles_all and legend_labels_all:
        ncol_total = len(legend_handles_all)
        unified_legend = fig.legend(
            legend_handles_all,
            legend_labels_all,
            bbox_to_anchor=(0.5, 0.93),
            loc='upper center',
            fontsize=22,
            ncol=ncol_total,       # 一行显示 5 个图例
            frameon=True,          # 显示整体边框
            fancybox=True,
            shadow=False,
            handletextpad=0.4,     # 图形与文字距离稍小
            columnspacing=0.8,     # 各图例项之间间距减小
            borderpad=0.3,
            labelspacing=0.3,
            markerscale=1.0
        )
        print(f"DEBUG: Created unified legend object: {id(unified_legend)}")
    
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
