#!/usr/bin/env python3
"""
Autonomous System (AS) Information Lookup Script
Reads a file with AS numbers and their appearance counts, then looks up AS information.

# Display results in terminal
python as_lookup.py your_file.txt

# Save results to a file
python as_lookup.py your_file.txt output.txt
"""

import urllib.request
import json
import time
import sys
from typing import Dict, Optional

def lookup_as_info(asn: int) -> Optional[Dict]:
    """
    Look up AS information using the RIPEStat API.
    
    Args:
        asn: Autonomous System Number
        
    Returns:
        Dictionary with AS information or None if lookup fails
    """
    try:
        # Using RIPEStat Data API (no authentication required)
        url = f"https://stat.ripe.net/data/as-overview/data.json?resource=AS{asn}"
        
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            
        if data.get('status') == 'ok' and 'data' in data:
            as_data = data['data']
            return {
                'asn': asn,
                'holder': as_data.get('holder', 'Unknown'),
                'announced': as_data.get('announced', False),
                'resource': as_data.get('resource', f'AS{asn}')
            }
    except Exception as e:
        print(f"Error looking up AS{asn}: {e}", file=sys.stderr)
    
    return None

def parse_input_file(filename: str) -> list:
    """
    Parse the input file containing count and ASN pairs.
    
    Args:
        filename: Path to input file
        
    Returns:
        List of tuples (count, asn)
    """
    entries = []
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                try:
                    count = int(parts[0])
                    asn = int(parts[1])
                    entries.append((count, asn))
                except ValueError:
                    print(f"Skipping invalid line: {line}", file=sys.stderr)
    return entries

def main():
    if len(sys.argv) < 2:
        print("Usage: python as_lookup.py <input_file> [output_file]")
        print("\nExample:")
        print("  python as_lookup.py as_data.txt")
        print("  python as_lookup.py as_data.txt output.txt")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"Reading AS data from {input_file}...")
    entries = parse_input_file(input_file)
    print(f"Found {len(entries)} entries")
    
    # Open output file if specified
    out = open(output_file, 'w') if output_file else sys.stdout
    
    # Print header
    header = f"{'Count':<12} {'ASN':<12} {'Holder'}"
    print(header)
    print("-" * 80)
    if output_file:
        out.write(header + "\n")
        out.write("-" * 80 + "\n")
    
    # Look up each AS
    for i, (count, asn) in enumerate(entries):
        as_info = lookup_as_info(asn)
        
        if as_info:
            holder = as_info['holder']
            line = f"{count:<12} {asn:<12} {holder}"
        else:
            line = f"{count:<12} {asn:<12} [Lookup Failed]"
        
        print(line)
        if output_file:
            out.write(line + "\n")
        
        # Rate limiting: sleep briefly to avoid overwhelming the API
        if (i + 1) % 10 == 0:
            time.sleep(1)
            print(f"Processed {i + 1}/{len(entries)} entries...", file=sys.stderr)
    
    if output_file:
        out.close()
        print(f"\nResults saved to {output_file}", file=sys.stderr)
    
    print(f"\nCompleted! Processed {len(entries)} AS numbers.", file=sys.stderr)

if __name__ == "__main__":
    main()