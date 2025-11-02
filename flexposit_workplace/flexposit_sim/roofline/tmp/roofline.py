import numpy as np
import matplotlib.pyplot as plt

# --- parameters ---
A = np.linspace(0.0, 0.11, 600)
BW = {"FlexPosit": 1.6e-8, "OliVe": 0.9e-8, "BitMoD": 1.8e-8}
k = 1.35
P = {"FlexPosit": 3.0e-8, "OliVe": 2.2e-8, "BitMoD": 4.2e-8}
A_c = {"FlexPosit": 0.06, "OliVe": 0.03, "BitMoD": 0.11}

# --- helper functions ---
def compute_ramp(a, name):
    return P[name] * (a**k) / (a**k + A_c[name]**k)

def throughput(a, name):
    return np.minimum(compute_ramp(a, name), BW[name])

# --- build throughput curves ---
T = {n: throughput(A, n) for n in ["FlexPosit", "OliVe", "BitMoD"]}

# --- intersection finder ---
def find_intersections(a, y1, y2):
    diff = y1 - y2
    idxs = np.where(np.diff(np.sign(diff)) != 0)[0]
    xs = []
    for i in idxs:
        x0, x1 = a[i], a[i+1]
        y0, y1v = diff[i], diff[i+1]
        x = x0 - y0 * (x1 - x0) / (y1v - y0)
        xs.append(x)
    return xs

# --- find the two intersection x-values ---
A_left  = find_intersections(A, T["FlexPosit"], T["OliVe"])[1]
A_right = find_intersections(A, T["BitMoD"], T["FlexPosit"])[1]

print(f"A_left = {A_left:.4f}, A_right = {A_right:.4f}")

# --- plot and highlight region ---
plt.figure(figsize=(8.5, 6.0), dpi=150)
plt.axvspan(A_left, A_right, facecolor="#f2cc8f", alpha=0.35)
for x in (A_left, A_right):
    plt.axvline(x, linestyle="--", linewidth=1.4, color="#555555")

plt.plot(A, T["FlexPosit"], color="#f5a300", linewidth=2.6, label="FlexPosit")
plt.plot(A, T["OliVe"],     color="#3aa0e3", linewidth=2.6, label="OliVe")
plt.plot(A, T["BitMoD"],    color="#0a9d6d", linewidth=2.6, label="BitMoD")


# Compute mid x-position of the edge region
x_mid = (A_left + A_right) / 2
y_mid =  plt.ylim()[1] * 0.9  # adjust for visual placement (depends on your scale)

# Add descriptive texts
plt.text(x_mid, y_mid, "Edge mixed compute/memory region",
         ha="center", va="center", fontsize=10, color="black",
         bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.7, lw=0))

plt.text(A_left * 0.6, y_mid * 0.9, "Ultra-low-power", 
         ha="center", va="center", fontsize=9, color="#333333")

plt.text(A_right * 1.15, y_mid * 0.9, "Cloud-scale", 
         ha="center", va="center", fontsize=9, color="#333333")

plt.legend()
plt.xlabel("PE Array Area (mm$^2$)")
plt.ylabel("Throughput (1/cycle)")
plt.tight_layout()
plt.savefig("iso_area_edge_with_labels.png", bbox_inches="tight", dpi=300)
plt.savefig("roofline_temp.pdf", bbox_inches="tight")   # <-- PDF version
plt.show()