#!/usr/bin/env python3
"""
Automated Traceroute and Database Logging Script
Run this script via cronjob to collect time-series data.
"""

import sqlite3
from scapy.all import *
from ipwhois import IPWhois
from ipwhois.exceptions import IPDefinedError, HostLookupError
import time
import socket
import argparse

# Configuration
DB_PATH = 'bgp_measurements.db'
TARGETS_FILE = 'targets.txt'
SOURCE_REGION = 'local_mac'  # Change this if you run from different locations, e.g., 'aws_tokyo'

def get_asn(ip_address):
    """
    Attempts to find the ASN for a given IP address.
    Returns the ASN description or the AS number if description is unavailable.
    Returns 'Unknown' if lookup fails.
    """
    if ip_address.startswith('172.') or ip_address.startswith('192.168.') or ip_address.startswith('10.'):
        return 'Private'
    try:
        obj = IPWhois(ip_address)
        results = obj.lookup_rdap(depth=1)
        asn_desc = results.get('asn_description', 'Unknown')
        asn = results.get('asn', 'Unknown')
        # Prefer the description, fall back to just the AS number
        return asn_desc if asn_desc != 'Unknown' else f"AS{asn}"
    except (IPDefinedError, HostLookupError, ValueError, Exception):
        return 'Unknown'

def run_icmp_traceroute(destination, max_hops=30, timeout=2, probes=3):
    """
    Performs an ICMP-based traceroute.
    Returns a tuple: (success_bool, list_of_hops, list_of_latencies, as_path)
    """
    hop_ips = []
    latencies = []
    as_path = []

    try:
        dest_ip = socket.gethostbyname(destination)
    except socket.gaierror:
        print(f"ERROR: Could not resolve {destination}")
        return (False, [], [], [])

    print(f"[+] Tracing route to {destination} ({dest_ip})")

    for ttl in range(1, max_hops + 1):
        hop_replied = False
        probe_rtts = []

        for _ in range(probes):
            # Create and send packet
            pkt = IP(dst=dest_ip, ttl=ttl) / ICMP(type=8, code=0)
            start_time = time.time()
            reply = sr1(pkt, verbose=0, timeout=timeout)
            rtt = (time.time() - start_time) * 1000

            if reply is None:
                probe_rtts.append(None)  # Timeout
                continue

            reply_ip = reply.src
            probe_rtts.append(rtt)

            if not hop_replied:
                hop_replied = True
                hop_ips.append(reply_ip)
                # Get ASN for this hop and add to AS path if it's new
                hop_asn = get_asn(reply_ip)
                if not as_path or hop_asn != as_path[-1]:
                    as_path.append(hop_asn)
                latencies.append(rtt)

            # If we got an Echo Reply, we've reached the destination
            if reply.type == 0:
                # Check if the final destination IP is already listed
                if hop_ips[-1] != reply_ip:
                    hop_ips.append(reply_ip)
                    final_asn = get_asn(reply_ip)
                    if final_asn != as_path[-1]:
                        as_path.append(final_asn)
                break

        # If all probes for this hop timed out, record it as an asterisk
        if not hop_replied:
            hop_ips.append("*")
            latencies.append(None)

        # Break the loop if the destination was reached
        if hop_replied and hop_ips[-1] == dest_ip:
            break

    # Format the final results
    success = hop_ips and hop_ips[-1] == dest_ip
    traceroute_str = " → ".join(hop_ips)
    as_path_str = " → ".join(as_path) if as_path else "Unknown"
    avg_latency = sum([rtt for rtt in latencies if rtt is not None]) / len(latencies) if latencies else None

    return (success, hop_ips, avg_latency, traceroute_str, as_path_str)

def log_to_database(destination_ip, traceroute_result, as_path, latency):
    """Connects to the SQLite DB and inserts a new measurement."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        insert_sql = """
        INSERT INTO measurements 
        (source_region, destination_ip, bgp_as_path, latency_ms, traceroute_result)
        VALUES (?, ?, ?, ?, ?)
        """
        cursor.execute(insert_sql, (SOURCE_REGION, destination_ip, as_path, latency, traceroute_result))

        conn.commit()
        conn.close()
        print(f"[+] Successfully logged results for {destination_ip} to database.")
        return True

    except sqlite3.Error as e:
        print(f"[-] Database error: {e}")
        return False

def main():
    """Main function to read targets and run traceroutes."""
    print(f"[*] Starting automated traceroute run at {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Read the list of targets from the file
    try:
        with open(TARGETS_FILE, 'r') as f:
            targets = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except FileNotFoundError:
        print(f"[-] Error: File {TARGETS_FILE} not found.")
        return

    for target in targets:
        print(f"\n[*] Processing target: {target}")
        success, hops, avg_latency, trace_str, as_path_str = run_icmp_traceroute(target)

        if success:
            print(f"    Traceroute Successful. AS Path: {as_path_str}")
            print(f"    Average Latency: {avg_latency:.2f} ms")
            log_to_database(target, trace_str, as_path_str, avg_latency)
        else:
            print(f"    Traceroute to {target} failed or was incomplete.")
            # You might still want to log failed attempts
            # log_to_database(target, trace_str, "Failed", None)

    print(f"\n[*] Finished all measurements at {time.strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    # Run the script
    main()