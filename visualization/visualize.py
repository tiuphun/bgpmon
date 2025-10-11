#!/usr/bin/env python3
"""
Taiwan Internet Topology Analyzer
Analyzes BGP data and generates network topology visualizations
"""

import re
import subprocess
import os
from collections import defaultdict, Counter
import json

# You'll need to install these packages:
# pip install networkx matplotlib pandas

try:
    import networkx as nx
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import pandas as pd
except ImportError:
    print("Missing required packages. Install with:")
    print("pip install networkx matplotlib pandas")
    exit(1)

# Taiwan ASNs we're focusing on
TAIWAN_ASNS = {
    '3462': 'HiNet (Chunghwa)',
    '4780': 'SeedNet',
    '1659': 'TANet',
    '7539': 'TWARENet',
    '9924': 'Taiwan Fixed Network'
}

# Known Tier-1 providers (add more as needed)
TIER1_ASNS = {
    '174', '209', '286', '701', '1239', '1299', '2828', '2914', 
    '3257', '3320', '3356', '3491', '5511', '6453', '6461', '6762', '6830', '7018'
}

class BGPTopologyAnalyzer:
    def __init__(self):
        self.as_paths = []
        self.as_graph = nx.DiGraph()
        self.as_counter = Counter()
        self.as_neighbors = defaultdict(lambda: defaultdict(int))
        
    def parse_bgpdump_file(self, filepath):
        """Parse a single BGP dump file"""
        print(f"Processing {filepath}...")
        
        try:
            # Run bgpdump on the file
            result = subprocess.run(
                ['bgpdump', '-H', filepath],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Parse the output
            for line in result.stdout.split('\n'):
                if line.startswith('ASPATH:'):
                    aspath = line.replace('ASPATH:', '').strip()
                    if aspath:
                        as_list = aspath.split()
                        # Filter for paths containing Taiwan ASNs
                        if any(asn in TAIWAN_ASNS for asn in as_list):
                            self.as_paths.append(as_list)
                            
        except subprocess.TimeoutExpired:
            print(f"Timeout processing {filepath}")
        except Exception as e:
            print(f"Error processing {filepath}: {e}")
    
    def parse_directory(self, base_dir):
        """Parse all BGP dump files in directory structure"""
        collectors = ['route-views.eqix', 'route-views.sg', 'route-views.syd', 'route-views.wide']
        
        for collector in collectors:
            collector_path = os.path.join(base_dir, collector)
            if os.path.exists(collector_path):
                for filename in os.listdir(collector_path):
                    if filename.endswith('.bz2'):
                        filepath = os.path.join(collector_path, filename)
                        self.parse_bgpdump_file(filepath)
    
    def analyze_paths(self):
        """Analyze AS paths to build topology"""
        print(f"\nAnalyzing {len(self.as_paths)} AS paths...")
        
        for path in self.as_paths:
            # Count ASN appearances
            for asn in path:
                self.as_counter[asn] += 1
            
            # Build adjacency relationships
            for i in range(len(path) - 1):
                current_asn = path[i]
                next_asn = path[i + 1]
                
                # Add edge to graph
                if self.as_graph.has_edge(current_asn, next_asn):
                    self.as_graph[current_asn][next_asn]['weight'] += 1
                else:
                    self.as_graph.add_edge(current_asn, next_asn, weight=1)
                
                # Track neighbors
                self.as_neighbors[current_asn][next_asn] += 1
    
    def get_taiwan_neighbors(self):
        """Get direct neighbors for each Taiwan ASN"""
        neighbors = {}
        
        for tw_asn in TAIWAN_ASNS.keys():
            neighbors[tw_asn] = {
                'upstream': defaultdict(int),
                'downstream': defaultdict(int)
            }
            
            for path in self.as_paths:
                if tw_asn in path:
                    idx = path.index(tw_asn)
                    
                    # Get upstream (before in path)
                    if idx > 0:
                        neighbors[tw_asn]['upstream'][path[idx - 1]] += 1
                    
                    # Get downstream (after in path)
                    if idx < len(path) - 1:
                        neighbors[tw_asn]['downstream'][path[idx + 1]] += 1
        
        return neighbors
    
    def visualize_topology(self, output_file='taiwan_topology.png', max_nodes=50):
        """Generate network topology visualization"""
        print("\nGenerating topology visualization...")
        
        # Create a subgraph focusing on Taiwan and top ASNs
        important_asns = set(TAIWAN_ASNS.keys())
        
        # Add most frequent ASNs
        for asn, count in self.as_counter.most_common(max_nodes):
            important_asns.add(asn)
        
        # Build subgraph
        subgraph = self.as_graph.subgraph(important_asns).copy()
        
        # Create figure
        plt.figure(figsize=(20, 16))
        
        # Layout
        pos = nx.spring_layout(subgraph, k=2, iterations=50, seed=42)
        
        # Node colors and sizes
        node_colors = []
        node_sizes = []
        
        for node in subgraph.nodes():
            if node in TAIWAN_ASNS:
                node_colors.append('#FF6B6B')  # Red for Taiwan ASNs
                node_sizes.append(3000)
            elif node in TIER1_ASNS:
                node_colors.append('#4ECDC4')  # Cyan for Tier-1
                node_sizes.append(2000)
            else:
                node_colors.append('#95E1D3')  # Light green for others
                node_sizes.append(1000)
        
        # Draw network
        nx.draw_networkx_nodes(subgraph, pos, 
                              node_color=node_colors,
                              node_size=node_sizes,
                              alpha=0.8)
        
        # Draw edges with varying thickness
        edges = subgraph.edges()
        weights = [subgraph[u][v]['weight'] for u, v in edges]
        max_weight = max(weights) if weights else 1
        
        nx.draw_networkx_edges(subgraph, pos,
                              width=[w/max_weight * 3 for w in weights],
                              alpha=0.3,
                              arrows=True,
                              arrowsize=10,
                              edge_color='gray')
        
        # Labels
        labels = {}
        for node in subgraph.nodes():
            if node in TAIWAN_ASNS:
                labels[node] = f"AS{node}\n{TAIWAN_ASNS[node]}"
            else:
                labels[node] = f"AS{node}"
        
        nx.draw_networkx_labels(subgraph, pos, labels, font_size=8, font_weight='bold')
        
        # Legend
        taiwan_patch = mpatches.Patch(color='#FF6B6B', label='Taiwan ASNs')
        tier1_patch = mpatches.Patch(color='#4ECDC4', label='Tier-1 Providers')
        other_patch = mpatches.Patch(color='#95E1D3', label='Other ASNs')
        plt.legend(handles=[taiwan_patch, tier1_patch, other_patch], loc='upper left', fontsize=12)
        
        plt.title('Taiwan Internet AS-Level Topology', fontsize=20, fontweight='bold', pad=20)
        plt.axis('off')
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Topology visualization saved to {output_file}")
        plt.close()
    
    def visualize_taiwan_focus(self, output_file='taiwan_focus.png'):
        """Generate Taiwan-focused topology showing only direct relationships"""
        print("\nGenerating Taiwan-focused visualization...")
        
        # Get neighbors for Taiwan ASNs
        neighbors = self.get_taiwan_neighbors()
        
        # Build focused graph
        G = nx.DiGraph()
        
        for tw_asn in TAIWAN_ASNS.keys():
            G.add_node(tw_asn, node_type='taiwan')
            
            # Add top upstream neighbors
            for asn, count in sorted(neighbors[tw_asn]['upstream'].items(), 
                                    key=lambda x: x[1], reverse=True)[:10]:
                G.add_node(asn, node_type='upstream')
                G.add_edge(asn, tw_asn, weight=count)
            
            # Add top downstream neighbors
            for asn, count in sorted(neighbors[tw_asn]['downstream'].items(), 
                                    key=lambda x: x[1], reverse=True)[:5]:
                G.add_node(asn, node_type='downstream')
                G.add_edge(tw_asn, asn, weight=count)
        
        # Create figure
        plt.figure(figsize=(20, 16))
        
        # Layout - shell layout to show Taiwan ASNs in center
        shells = [
            [n for n in G.nodes() if G.nodes[n]['node_type'] == 'upstream'],
            list(TAIWAN_ASNS.keys()),
            [n for n in G.nodes() if G.nodes[n]['node_type'] == 'downstream']
        ]
        pos = nx.shell_layout(G, shells)
        
        # Node colors and sizes
        node_colors = []
        node_sizes = []
        
        for node in G.nodes():
            node_type = G.nodes[node]['node_type']
            if node_type == 'taiwan':
                node_colors.append('#FF6B6B')
                node_sizes.append(4000)
            elif node_type == 'upstream':
                node_colors.append('#4ECDC4')
                node_sizes.append(2500)
            else:
                node_colors.append('#FFD93D')
                node_sizes.append(2000)
        
        # Draw
        nx.draw_networkx_nodes(G, pos,
                              node_color=node_colors,
                              node_size=node_sizes,
                              alpha=0.9)
        
        edges = G.edges()
        weights = [G[u][v]['weight'] for u, v in edges]
        max_weight = max(weights) if weights else 1
        
        nx.draw_networkx_edges(G, pos,
                              width=[w/max_weight * 5 for w in weights],
                              alpha=0.5,
                              arrows=True,
                              arrowsize=15,
                              edge_color='gray',
                              connectionstyle='arc3,rad=0.1')
        
        # Labels
        labels = {}
        for node in G.nodes():
            if node in TAIWAN_ASNS:
                labels[node] = f"AS{node}\n{TAIWAN_ASNS[node]}"
            else:
                labels[node] = f"AS{node}"
        
        nx.draw_networkx_labels(G, pos, labels, font_size=10, font_weight='bold')
        
        # Legend
        taiwan_patch = mpatches.Patch(color='#FF6B6B', label='Taiwan ASNs (Target)')
        upstream_patch = mpatches.Patch(color='#4ECDC4', label='Upstream/Transit Providers')
        downstream_patch = mpatches.Patch(color='#FFD93D', label='Downstream Customers')
        plt.legend(handles=[taiwan_patch, upstream_patch, downstream_patch], 
                  loc='upper left', fontsize=12)
        
        plt.title('Taiwan ASN Direct Connectivity', fontsize=20, fontweight='bold', pad=20)
        plt.axis('off')
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Taiwan-focused visualization saved to {output_file}")
        plt.close()
    
    def generate_report(self, output_file='taiwan_bgp_report.txt'):
        """Generate text report with statistics"""
        print("\nGenerating analysis report...")
        
        neighbors = self.get_taiwan_neighbors()
        
        with open(output_file, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("Taiwan Internet Topology Analysis Report\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"Total AS paths analyzed: {len(self.as_paths)}\n")
            f.write(f"Unique ASNs observed: {len(self.as_counter)}\n\n")
            
            # Top ASNs by frequency
            f.write("-" * 80 + "\n")
            f.write("Top 20 Most Frequent ASNs (Potential Tier-1/Tier-2 Providers)\n")
            f.write("-" * 80 + "\n")
            for asn, count in self.as_counter.most_common(20):
                name = TAIWAN_ASNS.get(asn, '')
                tier = " [TIER-1]" if asn in TIER1_ASNS else ""
                f.write(f"AS{asn:8s} {name:30s} Count: {count:6d}{tier}\n")
            
            # Taiwan ASN analysis
            f.write("\n" + "=" * 80 + "\n")
            f.write("Taiwan ASN Connectivity Analysis\n")
            f.write("=" * 80 + "\n\n")
            
            for tw_asn, name in TAIWAN_ASNS.items():
                f.write(f"\n{'=' * 80}\n")
                f.write(f"AS{tw_asn} - {name}\n")
                f.write(f"{'=' * 80}\n")
                
                if tw_asn in neighbors:
                    # Upstream providers
                    f.write(f"\nTop Upstream/Transit Providers:\n")
                    f.write("-" * 50 + "\n")
                    for asn, count in sorted(neighbors[tw_asn]['upstream'].items(),
                                            key=lambda x: x[1], reverse=True)[:15]:
                        tier = " [TIER-1]" if asn in TIER1_ASNS else ""
                        f.write(f"  AS{asn:8s} - {count:6d} occurrences{tier}\n")
                    
                    # Downstream
                    f.write(f"\nTop Downstream Customers/Peers:\n")
                    f.write("-" * 50 + "\n")
                    for asn, count in sorted(neighbors[tw_asn]['downstream'].items(),
                                            key=lambda x: x[1], reverse=True)[:15]:
                        f.write(f"  AS{asn:8s} - {count:6d} occurrences\n")
                else:
                    f.write("  No connectivity data found\n")
        
        print(f"Analysis report saved to {output_file}")
    
    def export_csv(self, output_file='taiwan_as_relationships.csv'):
        """Export AS relationships as CSV"""
        print("\nExporting AS relationships to CSV...")
        
        data = []
        for source, targets in self.as_neighbors.items():
            for target, count in targets.items():
                data.append({
                    'source_asn': source,
                    'source_name': TAIWAN_ASNS.get(source, ''),
                    'target_asn': target,
                    'target_name': TAIWAN_ASNS.get(target, ''),
                    'occurrences': count,
                    'source_is_taiwan': source in TAIWAN_ASNS,
                    'target_is_taiwan': target in TAIWAN_ASNS
                })
        
        df = pd.DataFrame(data)
        df = df.sort_values('occurrences', ascending=False)
        df.to_csv(output_file, index=False)
        print(f"AS relationships exported to {output_file}")


def main():
    print("Taiwan Internet Topology Analyzer")
    print("=" * 80)
    
    # Initialize analyzer
    analyzer = BGPTopologyAnalyzer()
    
    # Parse BGP dumps (assumes current directory structure)
    base_dir = "."
    analyzer.parse_directory(base_dir)
    
    if not analyzer.as_paths:
        print("\nNo BGP data found! Make sure you have the correct directory structure.")
        print("Expected structure:")
        print("  ./route-views.eqix/rib.*.bz2")
        print("  ./route-views.sg/rib.*.bz2")
        print("  ./route-views.syd/rib.*.bz2")
        print("  ./route-views.wide/rib.*.bz2")
        return
    
    # Analyze
    analyzer.analyze_paths()
    
    # Generate outputs
    analyzer.generate_report('taiwan_bgp_report.txt')
    analyzer.export_csv('taiwan_as_relationships.csv')
    analyzer.visualize_topology('taiwan_topology_full.png', max_nodes=60)
    analyzer.visualize_taiwan_focus('taiwan_topology_focused.png')
    
    print("\n" + "=" * 80)
    print("Analysis complete! Generated files:")
    print("  - taiwan_bgp_report.txt (detailed text report)")
    print("  - taiwan_as_relationships.csv (AS relationship data)")
    print("  - taiwan_topology_full.png (full topology visualization)")
    print("  - taiwan_topology_focused.png (Taiwan-focused visualization)")
    print("=" * 80)


if __name__ == "__main__":
    main()