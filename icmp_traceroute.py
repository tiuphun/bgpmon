#!/usr/bin/env python3

import argparse
import socket
from scapy.all import *
import time

def traceroute_icmp(destination, max_hops=30, timeout=2, probes=3):
    """
    Perform an ICMP-based traceroute, mimicking the standard command.
    """
    # Resolve hostname to IP
    try:
        dest_ip = socket.gethostbyname(destination)
    except socket.gaierror:
        print(f"Unable to resolve '{destination}'")
        return

    print(f"traceroute to {destination} ({dest_ip}), {max_hops} hops max, {40} byte packets")

    for ttl in range(1, max_hops + 1):
        # List to store results for each probe in this hop
        hop_results = []

        for probe_seq in range(probes):
            # Create IP and ICMP Echo Request packets
            ip_layer = IP(dst=dest_ip, ttl=ttl)
            icmp_layer = ICMP(type=8, code=0) # Type 8 = Echo Request
            packet = ip_layer / icmp_layer

            # Send packet and get reply
            start_time = time.time()
            reply = sr1(packet, verbose=0, timeout=timeout)
            rtt = (time.time() - start_time) * 1000  # Convert to milliseconds

            if reply is None:
                # No reply within timeout
                hop_results.append(" *")
            elif reply.type == 0:
                # ICMP Echo Reply (Type 0) - we reached the destination!
                hop_results.append(f" {reply.src} ({rtt:.3f} ms)")
                # We break early on success for this probe? No, let's get all probes.
            elif reply.type == 11:
                # ICMP Time Exceeded (Type 11) - an intermediate router replied
                hop_results.append(f" {reply.src} ({rtt:.3f} ms)")
            else:
                # Other ICMP types (e.g., Destination Unreachable)
                hop_results.append(f" {reply.src} ({rtt:.3f} ms)")

        # Format the output for this hop
        output_line = f"{ttl:2d}"
        for result in hop_results:
            output_line += result
        print(output_line)

        # Check if we've reached the destination for all intents and purposes
        # If we get an Echo Reply, we are done.
        if reply is not None and reply.type == 0:
            break

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ICMP-based Traceroute similar to the standard command.")
    parser.add_argument("destination", help="Hostname or IP address to trace to")
    parser.add_argument("-m", "--max-hops", type=int, default=30, help="Maximum number of hops (default: 30)")
    parser.add_argument("-t", "--timeout", type=int, default=2, help="Timeout per probe in seconds (default: 2)")
    parser.add_argument("-q", "--probes", type=int, default=3, help="Number of probes per hop (default: 3)")
    
    args = parser.parse_args()
    
    # Run traceroute
    traceroute_icmp(args.destination, args.max_hops, args.timeout, args.probes)