#!/usr/bin/env python3
"""
Extract traceroute target IPs from BGP data using bgpdump -m format
This works with the clean one-line-per-route format
"""

import subprocess
import ipaddress
import os
from collections import defaultdict, Counter
import json

TAIWAN_ASNS = {
    '3462': 'HiNet (Chunghwa)',
    '4780': 'SeedNet',
    '1659': 'TANet',
    '7539': 'TWARENet',
    '9924': 'Taiwan Fixed Network'
}

# Taiwan IP ranges for filtering - from RIPE Stat API
# Source: https://stat.ripe.net/data/country-resource-list/data.json?resource=TW
# Last updated: 2025-01-12
TAIWAN_PREFIXES_V4 = [
    "1.34.0.0/15","1.160.0.0/12","1.200.0.0/16","27.0.152.0/22","27.51.0.0/16","27.52.0.0/15",
    "27.96.224.0/19","27.100.64.0/18","27.105.0.0/16","27.147.0.0/18","27.240.0.0/13",
    "36.224.0.0/12","39.1.0.0/16","39.8.0.0/13","42.0.64.0/18","42.64.0.0/12","49.128.64.0/19",
    "49.128.112.0/20","49.158.0.0/15","49.213.128.0/17","49.214.0.0/15","49.216.0.0/14",
    "58.86.0.0/16","58.99.0.0/18","58.99.64.0/18","58.114.0.0/15","59.102.128.0/17",
    "59.104.0.0/15","59.112.0.0/13","59.120.0.0/14","59.124.0.0/14","60.198.0.0/16",
    "60.199.0.0/16","60.244.0.0/19","60.244.32.0/19","60.244.64.0/18","60.244.128.0/17",
    "60.245.0.0/18","60.245.64.0/19","60.245.96.0/19","60.248.0.0/16","60.249.0.0/16",
    "60.250.0.0/15","61.20.0.0/16","61.30.0.0/16","61.31.0.0/16","61.56.0.0/13",
    "61.64.0.0/14","61.70.0.0/17","61.70.128.0/17","61.71.0.0/17","61.71.128.0/17",
    "61.216.0.0/16","61.217.0.0/16","61.218.0.0/15","61.220.0.0/14","61.224.0.0/14",
    "61.228.0.0/14","61.247.160.0/20","101.0.128.0/17","101.3.0.0/16","101.8.0.0/13",
    "101.136.0.0/14","106.1.0.0/16","106.64.0.0/15","106.104.0.0/14","110.24.0.0/13",
    "110.50.128.0/18","111.67.48.0/20","111.70.0.0/15","111.80.0.0/14","111.125.128.0/21",
    "111.184.0.0/15","111.235.192.0/18","111.240.0.0/12","112.78.16.0/20","112.78.64.0/19",
    "112.78.104.0/21","112.104.0.0/15","112.121.32.0/20","112.121.64.0/18","112.213.48.0/20",
    "113.21.80.0/20","113.21.160.0/19","113.61.128.0/17","113.196.0.0/16","114.24.0.0/14",
    "114.30.32.0/20","114.32.0.0/12","114.136.0.0/15","114.140.0.0/16","114.198.160.0/20",
    "114.198.176.0/20","115.30.64.0/18","115.42.80.0/20","115.43.0.0/16","115.80.0.0/14",
    "115.85.144.0/20","115.165.192.0/18","116.50.32.0/20","116.59.0.0/16","116.89.128.0/20",
    "116.118.128.0/18","116.212.80.0/20","116.214.0.0/20","116.241.0.0/16","117.19.0.0/16",
    "117.56.0.0/16","117.103.96.0/20","118.99.128.0/17","118.150.0.0/16","118.160.0.0/13",
    "118.168.0.0/14","118.231.0.0/16","118.232.0.0/15","119.14.0.0/16","119.15.192.0/18",
    "119.30.16.0/20","119.31.176.0/20","119.75.240.0/20","119.77.128.0/17","119.160.240.0/20",
    "120.96.0.0/11","121.50.144.0/21","121.50.176.0/20","121.254.64.0/18","122.99.0.0/18",
    "122.100.64.0/18","122.116.0.0/15","122.118.0.0/16","122.120.0.0/13","122.128.80.0/21",
    "122.144.32.0/19","122.146.0.0/15","122.200.152.0/21","122.201.128.0/17","122.252.160.0/20",
    "122.254.0.0/18","122.255.80.0/20","123.0.32.0/19","123.0.192.0/18","123.50.32.0/19",
    "123.51.128.0/17","123.99.0.0/19","123.99.32.0/19","123.110.0.0/16","123.192.0.0/14",
    "123.204.0.0/15","123.240.0.0/15","123.252.0.0/17","124.6.0.0/19","124.8.0.0/14",
    "124.12.0.0/16","124.29.128.0/19","124.29.160.0/19","124.108.128.0/18","124.109.112.0/20",
    "124.150.128.0/21","124.155.128.0/19","124.155.160.0/19","124.199.64.0/19","124.199.96.0/20",
    "124.218.0.0/16","124.219.0.0/17","125.62.224.0/20","125.224.0.0/13","125.232.0.0/15",
    "134.208.0.0/16","139.175.0.0/16","139.223.0.0/16","140.92.0.0/16","140.96.0.0/16",
    "140.109.0.0/16","140.110.0.0/16","140.111.0.0/16","140.112.0.0/16","140.113.0.0/16",
    "140.114.0.0/16","140.115.0.0/16","140.116.0.0/14","140.120.0.0/13","140.128.0.0/16",
    "140.129.0.0/16","140.130.0.0/16","140.131.0.0/16","140.132.0.0/16","140.133.0.0/16",
    "140.134.0.0/16","140.135.0.0/16","140.136.0.0/15","140.138.0.0/16","150.116.0.0/15",
    "163.13.0.0/16","163.14.0.0/15","163.16.0.0/12","163.32.0.0/16","168.95.0.0/16",
    "175.41.48.0/20","175.96.0.0/14","175.111.32.0/19","175.111.192.0/18","175.180.0.0/14",
    "175.184.240.0/21","180.92.0.0/20","180.176.0.0/15","180.204.0.0/14","180.214.176.0/20",
    "180.217.0.0/16","180.218.0.0/16","182.54.136.0/22","182.155.0.0/16","182.173.0.0/18",
    "182.233.0.0/16","182.234.0.0/15","192.72.3.0/24","192.83.166.0/24","192.192.0.0/17",
    "192.192.128.0/19","192.192.160.0/22","192.192.164.0/24","192.192.165.0/24","192.192.166.0/23",
    "192.192.168.0/21","192.192.176.0/20","192.192.192.0/18","202.2.52.0/22","202.3.160.0/19",
    "202.5.8.0/22","202.5.12.0/22","202.5.224.0/19","202.8.14.0/23","202.12.76.0/22",
    "202.39.0.0/16","202.55.224.0/19","202.80.104.0/21","202.123.124.0/22","202.126.64.0/20",
    "202.132.0.0/16","202.133.224.0/19","202.140.160.0/19","202.145.32.0/19","202.145.64.0/18",
    "202.145.128.0/18","202.145.192.0/19","202.145.224.0/19","202.151.48.0/20","202.153.160.0/19",
    "202.153.192.0/20","202.154.192.0/19","202.160.64.0/19","202.165.128.0/20","202.165.144.0/20",
    "202.168.192.0/20","202.169.160.0/20","202.173.32.0/19","202.174.16.0/20","202.178.128.0/18",
    "202.178.192.0/19","202.178.224.0/19","203.64.0.0/14","203.68.0.0/14","203.72.0.0/14",
    "203.77.0.0/22","203.77.4.0/22","203.77.8.0/21","203.77.16.0/20","203.77.32.0/20",
    "203.77.48.0/20","203.77.64.0/19","203.77.96.0/19","203.78.176.0/20","203.79.128.0/18",
    "203.79.192.0/19","203.79.224.0/19","203.84.144.0/21","203.91.0.0/19","203.105.224.0/19",
    "203.111.208.0/20","203.118.224.0/20","203.121.224.0/20","203.121.240.0/20","203.133.0.0/19",
    "203.133.32.0/19","203.133.64.0/19","203.133.96.0/19","203.135.64.0/19","203.145.192.0/20",
    "203.145.208.0/20","203.160.144.0/20","203.160.224.0/19","203.163.192.0/19","203.187.0.0/19",
    "203.187.32.0/19","203.187.64.0/18","203.188.192.0/20","203.190.16.0/21","203.201.32.0/20",
    "203.203.0.0/17","203.203.128.0/17","203.204.0.0/17","203.204.128.0/17","203.207.0.0/20",
    "203.207.32.0/20","203.211.0.0/19","203.217.96.0/19","203.222.0.0/20","203.222.16.0/20",
    "210.17.0.0/17","210.58.0.0/17","210.58.128.0/17","210.59.0.0/16","210.60.0.0/14",
    "210.64.0.0/14","210.68.0.0/14","210.80.64.0/20","210.80.80.0/20","210.85.0.0/16",
    "210.192.0.0/18","210.192.128.0/17","210.200.0.0/19","210.200.32.0/19","210.200.64.0/19",
    "210.200.96.0/19","210.200.128.0/19","210.200.160.0/19","210.200.192.0/18","210.201.0.0/18",
    "210.201.64.0/18","210.201.128.0/18","210.201.192.0/20","210.201.208.0/20","210.201.224.0/19",
    "210.202.0.0/16","210.203.0.0/17","210.208.0.0/18","210.208.64.0/19","210.208.96.0/19",
    "210.208.128.0/18","210.208.192.0/18","210.209.0.0/18","210.209.128.0/20","210.209.144.0/20",
    "210.209.160.0/19","210.209.192.0/18","210.240.0.0/16","210.241.0.0/16","210.242.0.0/15",
    "210.244.0.0/17","210.244.128.0/17","211.20.0.0/14","211.72.0.0/14","211.76.0.0/14",
    "218.32.0.0/16","218.34.0.0/17","218.34.128.0/17","218.35.0.0/16","218.160.0.0/14",
    "218.164.0.0/15","218.166.0.0/15","218.168.0.0/13","218.184.0.0/16","218.187.0.0/17",
    "218.187.128.0/17","218.210.0.0/15","219.68.0.0/17","219.68.128.0/17","219.69.0.0/16",
    "219.70.0.0/15","219.80.0.0/15","219.84.0.0/15","219.86.0.0/15","219.90.0.0/18",
    "219.91.0.0/17","220.128.0.0/18","220.128.64.0/18","220.128.128.0/17","220.129.0.0/16",
    "220.130.0.0/15","220.132.0.0/14","220.136.0.0/13","220.157.112.0/20","220.228.0.0/15",
    "221.120.0.0/18","221.120.64.0/19","221.169.0.0/16","222.156.0.0/16","222.157.0.0/16",
    "222.250.0.0/16","222.251.0.0/17","223.22.0.0/15","223.26.0.0/20","223.26.64.0/18",
    "223.27.32.0/19","223.136.0.0/13","223.200.0.0/16"
]

class BGPTargetExtractor:
    def __init__(self):
        self.asn_data = defaultdict(lambda: {
            'prefixes': set(),
            'nexthops': [],
            'peer_ips': set()
        })
        self.nexthop_frequency = Counter()
        self.taiwan_networks = [ipaddress.ip_network(p) for p in TAIWAN_PREFIXES_V4]
        self.debug_mode = False
        self.sample_lines = []
        self.taiwan_routes_found = 0
    
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
    
    def process_bgpdump_line(self, line):
        """Process one line of bgpdump -m output
        
        Actual format from your bgpdump:
        TABLE_DUMP2|timestamp|type|peer_ip|peer_asn|prefix|aspath|origin|nexthop|localpref|med|community|atomic_agg|aggregator
        Example: TABLE_DUMP2|1759262400|B|202.249.2.169|2497|1.34.0.0/15|2497 3462|IGP|202.249.2.169|0|0||AG|3462 220.128.0.55|
        """
        parts = line.split('|')
        
        if len(parts) < 9:
            return
        
        # Extract fields based on actual format
        record_type = parts[0]
        peer_ip = parts[3]
        peer_asn = parts[4]
        prefix = parts[5]      # Already in CIDR format (e.g., 1.34.0.0/15)
        aspath_str = parts[6]  # AS path (e.g., "2497 3462")
        nexthop = parts[8]     # Next-hop IP
        
        # Only process TABLE_DUMP2 records
        if record_type != 'TABLE_DUMP2':
            return
        
        # Skip IPv6
        if ':' in prefix:
            return
        
        # Parse AS path - clean up brackets and special characters
        # Handle formats like: "7660 3462" or "{7660,3462}" or "7660 {3462}"
        aspath_str = aspath_str.replace('{', '').replace('}', '').replace(',', ' ')
        as_list = aspath_str.split()
        
        if not as_list:
            return
        
        # Get origin ASN (last in path)
        origin_asn = as_list[-1]
        
        # Only interested in Taiwan ASNs
        if origin_asn not in TAIWAN_ASNS:
            return
        
        # Found Taiwan route!
        self.taiwan_routes_found += 1
        
        # Store first 5 for debugging
        if len(self.sample_lines) < 5:
            self.sample_lines.append(line)
        
        # Store data
        self.asn_data[origin_asn]['prefixes'].add(prefix)
        self.asn_data[origin_asn]['peer_ips'].add(peer_ip)
        
        # Store next-hop if valid IPv4
        if nexthop and '.' in nexthop and ':' not in nexthop:
            self.asn_data[origin_asn]['nexthops'].append(nexthop)
            self.nexthop_frequency[nexthop] += 1
    
    def process_bgpdump_file(self, filepath):
        """Process a BGP dump file with bgpdump -m"""
        print(f"Processing {filepath}...")
        
        try:
            # Run bgpdump -m
            result = subprocess.run(
                ['bgpdump', '-m', filepath],
                capture_output=True,
                text=True,
                timeout=600
            )
            
            # Show sample output format for debugging
            first_lines = result.stdout.split('\n')[:3]
            if first_lines and not self.sample_lines:
                print(f"  Sample output format:")
                for line in first_lines:
                    if line.strip():
                        print(f"    {line[:150]}...")
                        break
            
            lines_processed = 0
            for line in result.stdout.split('\n'):
                if line.strip():
                    self.process_bgpdump_line(line)
                    lines_processed += 1
                    
                    if lines_processed % 100000 == 0:
                        print(f"  Processed {lines_processed} routes...")
            
            print(f"  ✓ Processed {lines_processed} routes")
            
            if self.taiwan_routes_found > 0:
                print(f"  ✓ Found {self.taiwan_routes_found} Taiwan ASN routes!")
            else:
                print(f"  ⚠ No Taiwan routes found in this file")
                if self.sample_lines:
                    print(f"\n  Sample lines for debugging:")
                    for sample in self.sample_lines[:3]:
                        print(f"    {sample[:200]}...")
            
        except subprocess.TimeoutExpired:
            print(f"  ✗ Timeout processing {filepath}")
        except FileNotFoundError:
            print(f"  ✗ bgpdump not found! Install with: apt-get install bgpdump")
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    def process_all_collectors(self, base_dir='.'):
        """Process latest file from each collector"""
        print("="*80)
        print("PROCESSING BGP DUMPS")
        print("="*80 + "\n")
        
        collectors = ['route-views.eqix', 'route-views.sg', 'route-views.syd', 'route-views.wide']
        
        for collector in collectors:
            collector_path = os.path.join(base_dir, collector)
            if os.path.exists(collector_path):
                files = sorted([f for f in os.listdir(collector_path) if f.endswith('.bz2')])
                if files:
                    # Use latest file
                    latest = os.path.join(collector_path, files[-1])
                    self.process_bgpdump_file(latest)
    
    def generate_strategic_targets(self, asn):
        """Generate strategic target IPs for an ASN"""
        prefixes = list(self.asn_data[asn]['prefixes'])
        
        # Sort by prefix size (smaller = more specific)
        prefixes.sort(key=lambda x: ipaddress.ip_network(x).num_addresses)
        
        strategic_ips = []
        
        for prefix in prefixes[:100]:  # Top 100 most specific prefixes
            try:
                network = ipaddress.ip_network(prefix)
                hosts = list(network.hosts())
                
                if not hosts:
                    continue
                
                # Gateway IP (first usable)
                strategic_ips.append({
                    'ip': str(hosts[0]),
                    'prefix': prefix,
                    'type': 'gateway',
                    'is_taiwan': self.is_taiwan_ip(str(hosts[0]))
                })
                
                # For larger networks, add more samples
                if len(hosts) > 10:
                    # Middle IP
                    strategic_ips.append({
                        'ip': str(hosts[len(hosts)//2]),
                        'prefix': prefix,
                        'type': 'internal',
                        'is_taiwan': self.is_taiwan_ip(str(hosts[len(hosts)//2]))
                    })
                
            except Exception as e:
                continue
        
        return strategic_ips
    
    def generate_reports(self):
        """Generate all output files"""
        print("\n" + "="*80)
        print("GENERATING TARGET LISTS")
        print("="*80 + "\n")
        
        # Summary statistics
        print("Statistics by ASN:")
        print("-"*80)
        for asn, name in TAIWAN_ASNS.items():
            if asn in self.asn_data:
                data = self.asn_data[asn]
                prefixes = len(data['prefixes'])
                nexthops = len(set(data['nexthops']))
                peers = len(data['peer_ips'])
                print(f"AS{asn} ({name}):")
                print(f"  Prefixes announced: {prefixes}")
                print(f"  Unique next-hops: {nexthops}")
                print(f"  BGP peers observed: {peers}")
        
        print("\n" + "="*80)
        print("GENERATING OUTPUT FILES")
        print("="*80 + "\n")
        
        # 1. Next-hop based targets (border routers)
        self.generate_nexthop_targets()
        
        # 2. Prefix-based targets (internal IPs)
        self.generate_prefix_targets()
        
        # 3. Combined priority list
        self.generate_combined_priority()
        
        # 4. JSON with all data
        self.generate_json_export()
        
        print("\n" + "="*80)
        print("COMPLETE!")
        print("="*80)
    
    def generate_nexthop_targets(self):
        """Generate next-hop based target list"""
        print("1. Generating next-hop targets (BGP border routers)...")
        
        for asn, name in TAIWAN_ASNS.items():
            if asn not in self.asn_data:
                continue
            
            nexthops = list(set(self.asn_data[asn]['nexthops']))
            
            # Categorize by location
            taiwan_nexthops = []
            foreign_nexthops = []
            
            for nh in nexthops:
                freq = self.nexthop_frequency[nh]
                if self.is_taiwan_ip(nh):
                    taiwan_nexthops.append((nh, freq))
                else:
                    foreign_nexthops.append((nh, freq))
            
            taiwan_nexthops.sort(key=lambda x: x[1], reverse=True)
            foreign_nexthops.sort(key=lambda x: x[1], reverse=True)
            
            # Save to file
            filename = f'targets_nexthop_AS{asn}.txt'
            with open(filename, 'w') as f:
                f.write(f"# BGP Next-Hop Targets for AS{asn} ({name})\n")
                f.write(f"# These are likely border/edge routers\n\n")
                
                if taiwan_nexthops:
                    f.write("# Taiwan-based next-hops (internal routers)\n")
                    for ip, freq in taiwan_nexthops:
                        f.write(f"{ip:15s}  # seen {freq} times\n")
                    f.write("\n")
                
                if foreign_nexthops:
                    f.write("# Foreign next-hops (international peering points)\n")
                    for ip, freq in foreign_nexthops[:20]:
                        f.write(f"{ip:15s}  # seen {freq} times\n")
            
            print(f"   ✓ {filename} ({len(taiwan_nexthops)} TW, {len(foreign_nexthops)} foreign)")
    
    def generate_prefix_targets(self):
        """Generate prefix-based strategic targets"""
        print("\n2. Generating prefix-based targets (strategic IPs)...")
        
        for asn, name in TAIWAN_ASNS.items():
            if asn not in self.asn_data:
                continue
            
            targets = self.generate_strategic_targets(asn)
            
            filename = f'targets_prefix_AS{asn}.txt'
            with open(filename, 'w') as f:
                f.write(f"# Strategic Target IPs from prefixes - AS{asn} ({name})\n")
                f.write(f"# Generated from announced prefix blocks\n\n")
                
                for target in targets:
                    location = "TW" if target['is_taiwan'] else "??"
                    f.write(f"{target['ip']:15s}  # {target['prefix']:18s} [{location}] {target['type']}\n")
            
            print(f"   ✓ {filename} ({len(targets)} targets)")
    
    def generate_combined_priority(self):
        """Generate combined priority target list"""
        print("\n3. Generating combined priority list...")
        
        # Collect all next-hops from Taiwan ASNs
        all_nexthops = {}  # ip -> {asns: set, frequency: int, is_taiwan: bool}
        
        for asn in TAIWAN_ASNS.keys():
            if asn not in self.asn_data:
                continue
            
            nexthops = set(self.asn_data[asn]['nexthops'])
            
            for nh in nexthops:
                if nh not in all_nexthops:
                    all_nexthops[nh] = {
                        'asns': set(),
                        'frequency': self.nexthop_frequency[nh],
                        'is_taiwan': self.is_taiwan_ip(nh)
                    }
                all_nexthops[nh]['asns'].add(asn)
        
        # Convert to list for sorting
        priority_targets = []
        for ip, data in all_nexthops.items():
            priority_targets.append({
                'ip': ip,
                'asns': data['asns'],
                'frequency': data['frequency'],
                'is_taiwan': data['is_taiwan'],
                'asn_count': len(data['asns'])
            })
        
        # Sort by: 1) Taiwan IPs first, 2) frequency, 3) number of ASNs using it
        priority_targets.sort(key=lambda x: (not x['is_taiwan'], -x['frequency'], -x['asn_count']))
        
        filename = 'targets_priority_combined.txt'
        with open(filename, 'w') as f:
            f.write("# Priority Traceroute Targets - All Taiwan ASNs\n")
            f.write("# BGP next-hop IPs (border/edge routers) sorted by priority\n")
            f.write("# Format: IP | ASNs | Frequency | Location\n")
            f.write("# High frequency = used by many prefixes = likely core router\n\n")
            
            if not priority_targets:
                f.write("# No next-hop targets found!\n")
                print(f"   ⚠ {filename} (NO TARGETS FOUND)")
                return
            
            f.write("# === TAIWAN-BASED NEXT-HOPS (Internal/Edge Routers) ===\n")
            taiwan_count = 0
            for target in priority_targets:
                if not target['is_taiwan']:
                    break
                asn_list = ','.join([f"AS{asn}" for asn in sorted(target['asns'])])
                f.write(f"{target['ip']:15s}  [{asn_list:20s}]  freq:{target['frequency']:4d}  [TW]\n")
                taiwan_count += 1
                if taiwan_count >= 50:
                    break
            
            f.write("\n# === FOREIGN NEXT-HOPS (International Peering Points) ===\n")
            foreign_count = 0
            for target in priority_targets:
                if target['is_taiwan']:
                    continue
                asn_list = ','.join([f"AS{asn}" for asn in sorted(target['asns'])])
                f.write(f"{target['ip']:15s}  [{asn_list:20s}]  freq:{target['frequency']:4d}  [INTL]\n")
                foreign_count += 1
                if foreign_count >= 50:
                    break
        
        print(f"   ✓ {filename} ({taiwan_count} TW + {foreign_count} intl targets)")
    
    def generate_json_export(self):
        """Export everything to JSON"""
        print("\n4. Generating JSON export...")
        
        export_data = {}
        
        for asn, name in TAIWAN_ASNS.items():
            if asn not in self.asn_data:
                continue
            
            data = self.asn_data[asn]
            
            # Categorize next-hops
            taiwan_nexthops = []
            foreign_nexthops = []
            
            for nh in set(data['nexthops']):
                nh_data = {
                    'ip': nh,
                    'frequency': self.nexthop_frequency[nh]
                }
                if self.is_taiwan_ip(nh):
                    taiwan_nexthops.append(nh_data)
                else:
                    foreign_nexthops.append(nh_data)
            
            taiwan_nexthops.sort(key=lambda x: x['frequency'], reverse=True)
            foreign_nexthops.sort(key=lambda x: x['frequency'], reverse=True)
            
            export_data[asn] = {
                'name': name,
                'prefixes': sorted(list(data['prefixes'])),
                'nexthops_taiwan': taiwan_nexthops,
                'nexthops_foreign': foreign_nexthops[:20],
                'bgp_peers': sorted(list(data['peer_ips']))
            }
        
        filename = 'targets_complete_data.json'
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"   ✓ {filename}")


def main():
    print("BGP Traceroute Target Extractor")
    print("Using bgpdump -m one-line format")
    print("="*80 + "\n")
    
    extractor = BGPTargetExtractor()
    
    # Process BGP dumps
    extractor.process_all_collectors()
    
    # Check if we got data
    if not extractor.asn_data:
        print("\n" + "="*80)
        print("ERROR: No data extracted!")
        print("="*80)
        print("\nPossible issues:")
        print("1. BGP dump files not found in current directory")
        print("2. bgpdump command not installed")
        print("3. Files are empty or corrupted")
        print("\nExpected directory structure:")
        print("  ./route-views.eqix/rib.*.bz2")
        print("  ./route-views.sg/rib.*.bz2")
        print("  ./route-views.syd/rib.*.bz2")
        print("  ./route-views.wide/rib.*.bz2")
        return
    
    # Generate all reports
    extractor.generate_reports()
    
    print("\nGenerated files:")
    print("  • targets_nexthop_AS*.txt - Next-hop IPs per ASN (border routers)")
    print("  • targets_prefix_AS*.txt - Strategic IPs from prefixes per ASN")
    print("  • targets_priority_combined.txt - Top 100 priority targets (all ASNs)")
    print("  • targets_complete_data.json - Complete data export")
    print("\n" + "="*80)
    print("NEXT STEPS:")
    print("="*80)
    print("1. Review targets_priority_combined.txt for your top targets")
    print("2. Set up RIPE Atlas account or deploy measurement VPS")
    print("3. Start with top 20-30 targets for initial measurements")
    print("4. Run traceroutes from multiple vantage points")
    print("="*80)


if __name__ == "__main__":
    main()