import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import sys

# Try to find and read the ASN data file
filename = 'asn_info.txt'  # Change this to your filename if different
import os

# Try current directory first, then check if script is in a subdirectory
if not os.path.exists(filename):
    print(f"File not found in current directory: {os.getcwd()}")
    print(f"Looking for: {filename}")
    sys.exit(1)

try:
    # Read the data manually to handle variable-length Holder names
    with open(filename, 'r') as f:
        lines = f.readlines()
    
    # Skip header and dashes (first 2 lines)
    data = []
    for line in lines[2:]:
        line = line.strip()
        if not line:
            continue
        
        parts = line.split(None, 2)  # Split on whitespace, max 3 parts
        if len(parts) >= 2:
            try:
                count = int(parts[0])
                asn = parts[1]
                holder = parts[2] if len(parts) > 2 else ""
                data.append({'Count': count, 'ASN': asn, 'Holder': holder})
            except ValueError:
                continue
    
    df = pd.DataFrame(data)
    print(f"Successfully loaded {filename} with {len(df)} records")
except Exception as e:
    print(f"Error reading file: {e}")
    sys.exit(1)

# Convert Count to numeric
df['Count'] = pd.to_numeric(df['Count'], errors='coerce')

# Remove rows with NaN counts and invalid entries
df = df.dropna(subset=['Count', 'ASN'])
df = df[df['Count'] > 0]

# Sort by count in descending order
df = df.sort_values('Count', ascending=True)

# Create figure with high DPI for print quality
fig, ax = plt.subplots(figsize=(12, 16), dpi=300)

# Create horizontal bar chart
bars = ax.barh(range(len(df)), df['Count'], color='#555555', edgecolor='black', linewidth=0.5)

# Create gradient effect for black & white using different shades of gray
colors = plt.cm.gray(np.linspace(0.3, 0.8, len(df)))
for bar, color in zip(bars, colors):
    bar.set_color(color)

# Set y-axis labels with ASN and abbreviated holder name
labels = [f"AS{row['ASN']}" for _, row in df.iterrows()]
ax.set_yticks(range(len(df)))
ax.set_yticklabels(labels, fontsize=8)

# Labels and title
ax.set_xlabel('Frequency (Count)', fontsize=12, fontweight='bold')
ax.set_title('ASN Frequency Distribution', fontsize=14, fontweight='bold', pad=20)

# Grid for easier reading
ax.grid(axis='x', linestyle='--', linewidth=0.5, color='gray', alpha=0.3)
ax.set_axisbelow(True)

# Format x-axis
ax.xaxis.set_major_locator(plt.MaxNLocator(nbins=8))
ax.tick_params(axis='both', labelsize=9)

plt.tight_layout()

# Save in multiple formats suitable for papers
plt.savefig('asn_frequency_full.png', dpi=300, bbox_inches='tight', facecolor='white')
plt.savefig('asn_frequency_full.pdf', bbox_inches='tight', facecolor='white')
print("Full visualization saved as 'asn_frequency_full.png' and 'asn_frequency_full.pdf'")

# Create a top-20 version for more detail
fig2, ax2 = plt.subplots(figsize=(10, 8), dpi=300)

df_top20 = df.tail(20)
bars2 = ax2.barh(range(len(df_top20)), df_top20['Count'], 
                  color='#555555', edgecolor='black', linewidth=0.8)

# Gradient for top 20
colors2 = plt.cm.gray(np.linspace(0.4, 0.75, len(df_top20)))
for bar, color in zip(bars2, colors2):
    bar.set_color(color)

labels2 = [f"AS{row['ASN']}" for _, row in df_top20.iterrows()]
ax2.set_yticks(range(len(df_top20)))
ax2.set_yticklabels(labels2, fontsize=10)

ax2.set_xlabel('Frequency (Count)', fontsize=12, fontweight='bold')
ax2.set_title('Top 20 ASNs by Frequency', fontsize=14, fontweight='bold', pad=20)

ax2.grid(axis='x', linestyle='--', linewidth=0.5, color='gray', alpha=0.3)
ax2.set_axisbelow(True)

ax2.xaxis.set_major_locator(plt.MaxNLocator(nbins=6))
ax2.tick_params(axis='both', labelsize=10)

plt.tight_layout()

plt.savefig('asn_frequency_top20.png', dpi=300, bbox_inches='tight', facecolor='white')
plt.savefig('asn_frequency_top20.pdf', bbox_inches='tight', facecolor='white')
print("Top 20 visualization saved as 'asn_frequency_top20.png' and 'asn_frequency_top20.pdf'")

# Optional: Create a cumulative distribution plot
fig3, ax3 = plt.subplots(figsize=(10, 6), dpi=300)

df_sorted = df.sort_values('Count', ascending=False).reset_index(drop=True)
cumsum = df_sorted['Count'].cumsum()
cumsum_pct = (cumsum / cumsum.iloc[-1]) * 100

ax3.plot(range(len(cumsum)), cumsum_pct, linewidth=2, color='black', marker='o', markersize=3)
ax3.fill_between(range(len(cumsum)), cumsum_pct, alpha=0.3, color='gray')

ax3.set_xlabel('ASN Rank (by frequency)', fontsize=12, fontweight='bold')
ax3.set_ylabel('Cumulative Percentage (%)', fontsize=12, fontweight='bold')
ax3.set_title('Cumulative ASN Frequency Distribution', fontsize=14, fontweight='bold', pad=20)

ax3.grid(True, linestyle='--', linewidth=0.5, color='gray', alpha=0.3)
ax3.set_axisbelow(True)

ax3.set_ylim([0, 105])
ax3.tick_params(axis='both', labelsize=10)

plt.tight_layout()

plt.savefig('asn_frequency_cumulative.png', dpi=300, bbox_inches='tight', facecolor='white')
plt.savefig('asn_frequency_cumulative.pdf', bbox_inches='tight', facecolor='white')
print("Cumulative distribution saved as 'asn_frequency_cumulative.png' and 'asn_frequency_cumulative.pdf'")

plt.show()