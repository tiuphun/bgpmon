import argparse
import socket
from scapy.all import *
import time

def traceroute_to_taiwan(destination, max_hops=30, timeout=2, probes=3):
    """
    Perform a traceroute to a specified destination IP.
    
    Args:
        destination (str): Destination IP address.
        max_hops (int): Maximum number of hops to try.
        timeout (int): Timeout in seconds for each probe.
        probes (int): Number of probes per hop.
    """
    destination_ip = socket.gethostbyname(destination)
    port = 33434  # Default port for traceroute :cite[3]

    print(f"Traceroute to {destination} ({destination_ip}) with max {max_hops} hops:")
    
    for ttl in range(1, max_hops + 1):
        print(f"{ttl:2d}", end=" ")
        for probe in range(probes):
            # Create IP and UDP packets
            ip_layer = IP(dst=destination, ttl=ttl)
            udp_layer = UDP(dport=port + probe)
            packet = ip_layer / udp_layer

            # Send packet and get reply
            start_time = time.time()
            reply = sr1(packet, verbose=0, timeout=timeout)
            rtt = (time.time() - start_time) * 1000  # Convert to milliseconds

            if reply is None:
                # No reply within timeout
                print(" *", end="")
            elif reply.type == 3:
                # Destination unreachable or port unreachable
                print(f" {reply.src} (Destination unreachable)", end="")
                break
            elif reply.type == 11:
                # Time exceeded (intermediate hop)
                print(f" {reply.src} ({rtt:.2f} ms)", end="")
            else:
                # Other ICMP types
                print(f" {reply.src} (ICMP type {reply.type})", end="")
        print()  # New line after each hop

        # Check if destination reached
        if reply is not None and (reply.type == 3 or reply.src == destination_ip):
            print(f"Destination reached at hop {ttl}")
            break

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Traceroute to Taiwan RIPE Atlas anchors.")
    parser.add_argument("--anchor", default="203.75.10.5", help="IP address of the Taiwan anchor (default: 203.75.10.5)")
    parser.add_argument("--max-hops", type=int, default=30, help="Maximum number of hops (default: 30)")
    parser.add_argument("--timeout", type=int, default=2, help="Timeout per probe in seconds (default: 2)")
    parser.add_argument("--probes", type=int, default=3, help="Number of probes per hop (default: 3)")
    
    args = parser.parse_args()
    
    # Run traceroute
    traceroute_to_taiwan(args.anchor, args.max_hops, args.timeout, args.probes)