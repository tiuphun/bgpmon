#!/usr/bin/env python3
"""
Extract target IPs from BGP data for traceroute measurements
Focuses on BGP next-hop IPs which are typically border/edge routers
"""

import subprocess
import ipaddress
from collections import defaultdict, Counter
import json

# Taiwan ASNs
TAIWAN_ASNS = {
    '3462': 'HiNet (Chunghwa)',
    '4780': 'SeedNet',
    '1659': 'TANet',
    '7539': 'TWARENet',
    '9924': 'Taiwan Fixed Network'
}

# Taiwan IP prefixes (for filtering)
TAIWAN_PREFIXES_V4 = [
    '1.34.0.0/16', '1.160.0.0/12', '27.96.0.0/13', '27.240.0.0/13',
    '36.224.0.0/12', '42.72.0.0/15', '49.158.0.0/15', '58.84.0.0/14',
    '59.100.0.0/14', '59.104.0.0/13', '59.112.0.0/14', '59.116.0.0/15',
    '59.120.0.0/13', '60.198.0.0/15', '60.244.0.0/14', '60.248.0.0/13',
    '61.56.0.0/14', '61.60.0.0/15', '61.62.0.0/16', '61.64.0.0/13',
    '61.216.0.0/14', '61.220.0.0/15', '61.222.0.0/16', '61.224.0.0/12',
    '101.8.0.0/14', '101.12.0.0/15', '103.1.168.0/22', '106.64.0.0/11',
    '111.240.0.0/13', '111.248.0.0/14', '114.24.0.0/13', '114.32.0.0/11',
    '117.56.0.0/13', '118.160.0.0/11', '120.96.0.0/11', '122.116.0.0/14',
    '122.120.0.0/13', '123.192.0.0/11', '125.224.0.0/12', '140.96.0.0/11',
    '163.13.0.0/16', '163.14.0.0/15', '163.16.0.0/12', '168.95.0.0/16',
    '175.96.0.0/11', '180.176.0.0/12', '182.232.0.0/13', '192.83.166.0/24',
    '192.192.0.0/11', '203.66.0.0/15', '210.58.0.0/15', '210.60.0.0/14',
    '210.64.0.0/12', '210.200.0.0/13', '210.208.0.0/12', '211.20.0.0/14',
    '211.72.0.0/13', '218.32.0.0/11', '218.160.0.0/11'
]

class IPExtractor:
    def __init__(self):
        self.nexthop_ips = defaultdict(list)  # ASN -> [IPs]
        self.prefix_map = defaultdict(set)    # ASN -> {prefixes}
        self.ip_frequency = Counter()
        self.taiwan_networks = []
        
        # Parse Taiwan prefixes
        for prefix in TAIWAN_PREFIXES_V4:
            self.taiwan_networks.append(ipaddress.ip_network(prefix))
    
    def is_taiwan_ip(self, ip_str):
        """Check if IP is in Taiwan address space"""
        try:
            ip = ipaddress.ip_address(ip_str)
            for network in self.taiwan_networks:
                if ip in network:
                    return True
        except:
            pass
        return False
    
    def parse_bgpdump_file(self, filepath):
        """Extract next-hop IPs from BGP dump"""
        print(f"Processing {filepath}...")
        
        try:
            result = subprocess.run(
                ['bgpdump', '-m', filepath],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            for line in result.stdout.split('\n'):
                if not line.strip():
                    continue
                
                # BGP MRT format: TABLE_DUMP2|timestamp|type|peer_ip|peer_asn|prefix|prefix_len|aspath|origin|nexthop|...
                parts = line.split('|')
                if len(parts) < 10:
                    continue
                
                prefix = parts[5]
                aspath = parts[6]
                nexthop = parts[8]
                
                # Extract origin ASN (last in path)
                as_list = aspath.split()
                if not as_list:
                    continue
                
                origin_asn = as_list[-1]
                
                # Only interested in Taiwan ASNs
                if origin_asn in TAIWAN_ASNS:
                    self.prefix_map[origin_asn].add(prefix)
                    
                    # Store next-hop if it's an IPv4 address
                    if nexthop and ':' not in nexthop:  # IPv4 only
                        self.nexthop_ips[origin_asn].append(nexthop)
                        self.ip_frequency[nexthop] += 1
        
        except subprocess.TimeoutExpired:
            print(f"Timeout processing {filepath}")
        except Exception as e:
            print(f"Error: {e}")
    
    def process_all_collectors(self, base_dir='.'):
        """Process BGP dumps from all collectors"""
        import os
        
        collectors = ['route-views.eqix', 'route-views.sg', 'route-views.syd', 'route-views.wide']
        
        for collector in collectors:
            collector_path = os.path.join(base_dir, collector)
            if os.path.exists(collector_path):
                # Use only the latest file from each collector
                files = sorted([f for f in os.listdir(collector_path) if f.endswith('.bz2')])
                if files:
                    latest_file = os.path.join(collector_path, files[-1])
                    self.parse_bgpdump_file(latest_file)
    
    def generate_target_list(self, output_file='traceroute_targets.json'):
        """Generate prioritized list of target IPs"""
        print("\n" + "="*80)
        print("Generating traceroute target list...")
        print("="*80)
        
        targets = {}
        
        for asn, name in TAIWAN_ASNS.items():
            print(f"\n{name} (AS{asn}):")
            
            # Get unique IPs for this ASN
            unique_ips = list(set(self.nexthop_ips[asn]))
            
            # Filter for Taiwan IPs and sort by frequency
            taiwan_ips = []
            foreign_ips = []
            
            for ip in unique_ips:
                freq = self.ip_frequency[ip]
                if self.is_taiwan_ip(ip):
                    taiwan_ips.append((ip, freq))
                else:
                    foreign_ips.append((ip, freq))
            
            taiwan_ips.sort(key=lambda x: x[1], reverse=True)
            foreign_ips.sort(key=lambda x: x[1], reverse=True)
            
            print(f"  Taiwan IPs: {len(taiwan_ips)}")
            print(f"  Foreign IPs (border routers): {len(foreign_ips)}")
            
            # Store in targets
            targets[asn] = {
                'name': name,
                'prefixes': list(self.prefix_map[asn]),
                'taiwan_nexthops': [{'ip': ip, 'frequency': freq} for ip, freq in taiwan_ips[:20]],
                'border_nexthops': [{'ip': ip, 'frequency': freq} for ip, freq in foreign_ips[:10]]
            }
            
            # Print top targets
            if taiwan_ips:
                print(f"  Top Taiwan next-hops:")
                for ip, freq in taiwan_ips[:5]:
                    print(f"    {ip:15s} (seen {freq} times)")
            
            if foreign_ips:
                print(f"  Top border router next-hops:")
                for ip, freq in foreign_ips[:5]:
                    print(f"    {ip:15s} (seen {freq} times)")
        
        # Save to JSON
        with open(output_file, 'w') as f:
            json.dump(targets, f, indent=2)
        
        print(f"\n✓ Target list saved to {output_file}")
        
        # Also create simple text lists
        self.generate_simple_lists()
    
    def generate_simple_lists(self):
        """Generate simple IP lists for each ASN"""
        print("\nGenerating simple IP lists...")
        
        for asn, name in TAIWAN_ASNS.items():
            # All unique IPs
            unique_ips = sorted(set(self.nexthop_ips[asn]))
            
            if unique_ips:
                filename = f'targets_AS{asn}_{name.replace(" ", "_")}.txt'
                with open(filename, 'w') as f:
                    f.write(f"# Target IPs for {name} (AS{asn})\n")
                    f.write(f"# Total: {len(unique_ips)} unique next-hop IPs\n\n")
                    for ip in unique_ips:
                        freq = self.ip_frequency[ip]
                        f.write(f"{ip:15s}  # frequency: {freq}\n")
                
                print(f"  ✓ {filename}")
        
        # Generate combined priority list
        print("\nGenerating combined priority target list...")
        
        # Get top IPs across all Taiwan ASNs
        taiwan_ip_scores = {}
        
        for asn in TAIWAN_ASNS.keys():
            for ip in set(self.nexthop_ips[asn]):
                if self.is_taiwan_ip(ip):
                    score = self.ip_frequency[ip]
                    if ip not in taiwan_ip_scores:
                        taiwan_ip_scores[ip] = {'score': 0, 'asns': []}
                    taiwan_ip_scores[ip]['score'] += score
                    taiwan_ip_scores[ip]['asns'].append(asn)
        
        # Sort by score
        sorted_targets = sorted(taiwan_ip_scores.items(), 
                               key=lambda x: (len(x[1]['asns']), x[1]['score']), 
                               reverse=True)
        
        with open('traceroute_targets_priority.txt', 'w') as f:
            f.write("# Priority Traceroute Targets - Taiwan Core/Border Routers\n")
            f.write("# Sorted by: 1) Number of ASNs using this next-hop, 2) Frequency\n\n")
            
            for ip, data in sorted_targets[:100]:
                asn_list = ','.join([f"AS{asn}" for asn in data['asns']])
                f.write(f"{ip:15s}  # ASNs: [{asn_list}], score: {data['score']}\n")
        
        print(f"  ✓ traceroute_targets_priority.txt (top 100 IPs)")


def generate_vantage_point_recommendations():
    """Generate recommendations for vantage points"""
    
    recommendations = """
================================================================================
RECOMMENDED VANTAGE POINTS FOR TRACEROUTE MEASUREMENTS
================================================================================

Option 1: RIPE Atlas Platform (Recommended)
---------------------------------------------
- Global network of ~12,000 probes
- Taiwan has ~50+ active probes
- Free for research (credit system)
- API access for automated measurements

To use RIPE Atlas:
1. Register at https://atlas.ripe.net
2. Request measurement credits for research
3. Select probes in/near Taiwan
4. Run traceroute measurements to your target list

Suggested probe selection:
- Probes in Taiwan (country: TW)
- Probes in nearby countries (JP, KR, HK, SG, CN)
- Probes from major international locations (US, EU)

Command example:
  ripe-atlas measure traceroute --target <IP> --probes country:TW


Option 2: PlanetLab (If you have academic access)
--------------------------------------------------
- Academic measurement platform
- Nodes at universities worldwide
- Need institutional sponsorship

Taiwan nodes:
- Check http://www.planet-lab.org for active nodes
- Usually at NTU, NCTU, Academia Sinica


Option 3: Cloud VPS Instances
-------------------------------
Deploy your own measurement nodes:

Taiwan locations:
- Hinet Data Center (Chunghwa Telecom)
- Chief Telecom data centers
- Google Cloud Taiwan (asia-east1)
- AWS Asia Pacific (Tokyo/Singapore - closest to Taiwan)
- Linode Tokyo
- DigitalOcean Singapore

International comparison points:
- Tokyo, Japan
- Hong Kong
- Singapore
- Los Angeles, USA
- London, UK


Option 4: Academic Network Access
-----------------------------------
If you're at a university:
- Use TANet (AS1659) as internal vantage point
- Request access to TWARENet (AS7539) nodes
- Coordinate with network operations team


Option 5: Looking Glass Servers
---------------------------------
Public looking glass servers from Taiwan ISPs:
- Check for public looking glass services from HiNet, SeedNet
- Limited but useful for quick checks
- Usually web-based interface


RECOMMENDED MEASUREMENT STRATEGY
================================================================================

Phase 1: Internal Taiwan Topology
----------------------------------
Vantage points: Within Taiwan (RIPE Atlas probes in TW, or cloud VPS)
Targets: Your extracted next-hop IPs from all 5 Taiwan ASNs
Purpose: Map internal Taiwan routing and peering

Phase 2: International Connectivity
------------------------------------
Vantage points: Major international locations (JP, HK, SG, US, EU)
Targets: Same Taiwan next-hop IPs
Purpose: Understand how traffic enters/exits Taiwan

Phase 3: Inter-ISP Paths
-------------------------
Vantage points: One ISP's network (e.g., HiNet customer)
Targets: Other Taiwan ISPs' IPs
Purpose: Map peering relationships and transit paths


MEASUREMENT BEST PRACTICES
================================================================================
1. Rate limiting: Don't exceed 1 traceroute/second per target
2. Time of day: Run measurements at different times (peak/off-peak)
3. Protocol: Use both ICMP and UDP traceroutes
4. Repetition: Run multiple measurements per target (5-10 times)
5. Duration: Collect data over multiple days/weeks
6. Ethics: Follow measurement ethics guidelines, respect rate limits
"""
    
    with open('vantage_points_guide.txt', 'w') as f:
        f.write(recommendations)
    
    print("\n✓ vantage_points_guide.txt created with recommendations")


def main():
    print("BGP Next-Hop IP Extractor for Traceroute Planning")
    print("="*80)
    
    extractor = IPExtractor()
    
    # Process BGP data
    extractor.process_all_collectors()
    
    if not extractor.nexthop_ips:
        print("\nNo next-hop IPs found!")
        print("Make sure you have BGP dump files in:")
        print("  ./route-views.*/rib.*.bz2")
        return
    
    # Generate target lists
    extractor.generate_target_list()
    
    # Generate vantage point guide
    generate_vantage_point_recommendations()
    
    print("\n" + "="*80)
    print("TARGET EXTRACTION COMPLETE")
    print("="*80)
    print("\nGenerated files:")
    print("  1. traceroute_targets.json - Structured target data")
    print("  2. traceroute_targets_priority.txt - Top 100 priority targets")
    print("  3. targets_AS*.txt - Per-ASN target lists")
    print("  4. vantage_points_guide.txt - Vantage point recommendations")
    print("\nNext steps:")
    print("  1. Review priority target list")
    print("  2. Choose vantage point platform (RIPE Atlas recommended)")
    print("  3. Design measurement schedule")
    print("  4. Run traceroute measurements")
    print("="*80)


if __name__ == "__main__":
    main()