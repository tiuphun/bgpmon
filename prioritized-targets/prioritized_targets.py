#!/usr/bin/env python3
"""
Produce a prioritized /24 target list for given ASNs.

Outputs:
  - prioritized_targets.csv  (detailed rows with score & signals)
  - targets.txt              (plain list of target IPs, top-N selected)

Usage:
  python3 produce_prioritized_targets.py --count 150 --delay 0.5
  python3 produce_prioritized_targets.py --count 100 --ping  (to enable ICMP checks)

Notes:
  - Uses BGPView API to get prefixes originated by each ASN.
  - Splits larger prefixes into /24 subnets but samples them (configurable).
  - Reverse DNS is checked (cached in ptr_cache.json).
  - Ping test is optional (default off). If enabled, script will call system ping.
"""

import requests
import ipaddress
import socket
import json
import time
import csv
import argparse
import subprocess
from pathlib import Path

# ---------- Config ----------
ASNS = {
    3462: "HiNet",
    4780: "SEEDNet",
    1659: "TANet",
    7539: "TWAREN"
}
BGPVIEW_URL = "https://api.bgpview.io/asn/{asn}/prefixes"
PTR_CACHE_FILE = "ptr_cache.json"
DELAY = 0.5        # seconds between DNS/ping operations (politeness)
SAMPLE_PER_BIG_PREFIX = 6   # when splitting a big prefix (/16 -> many /24s), sample up to this many /24s
# scoring weights
WEIGHT_BASE = 100.0
WEIGHT_PTR = 30.0
WEIGHT_PTR_SERVICE = 20.0
WEIGHT_PING = 40.0

# service keywords to boost PTR
SERVICE_KEYWORDS = ["ns", "dns", "mail", "mx", "www", "web", "router", "core", "ix", "pop", "gw", "gw1", "time", "ntp"]

# ---------- Utilities ----------
def fetch_prefixes(asn):
    url = BGPVIEW_URL.format(asn=asn)
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    j = r.json()
    # BGPView /asn/<asn>/prefixes returns lists of ipv4_prefixes and ipv6_prefixes
    ipv4 = [p["prefix"] for p in j["data"].get("ipv4_prefixes", [])]
    return ipv4

def expand_to_24s(prefix):
    """
    Return a list of candidate /24 networks for this prefix.
    If prefix is /24 -> return [that /24].
    If prefix is longer (e.g., /25) -> include the containing /24.
    If prefix is shorter (e.g., /16) -> sample up to SAMPLE_PER_BIG_PREFIX /24 subnets spaced evenly.
    """
    net = ipaddress.ip_network(prefix, strict=False)
    if net.version != 4:
        return []
    if net.prefixlen == 24:
        return [net]
    if net.prefixlen > 24:
        # smaller than /24, include the /24 that contains the address
        # pick the first /24 that contains the network address
        containing = ipaddress.ip_network((int(net.network_address) & 0xFFFFFF00), strict=False)
        return [ipaddress.ip_network(str(containing))]
    # net.prefixlen < 24 -> split to /24s but sample
    total_24 = 2 ** (24 - net.prefixlen)
    # if total_24 small, return all
    if total_24 <= SAMPLE_PER_BIG_PREFIX:
        return list(net.subnets(new_prefix=24))
    # sample evenly across the space
    step = total_24 // SAMPLE_PER_BIG_PREFIX
    subnets = list(net.subnets(new_prefix=24))
    sampled = []
    idx = 0
    while len(sampled) < SAMPLE_PER_BIG_PREFIX and idx < len(subnets):
        sampled.append(subnets[idx])
        idx += step
    # ensure unique
    return sampled

def center_ip_of_24(net24):
    """Return representative IP for a /24 network. Use .1 (first usable) by default."""
    return str(net24.network_address + 1)

def load_ptr_cache():
    if Path(PTR_CACHE_FILE).exists():
        try:
            return json.loads(Path(PTR_CACHE_FILE).read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_ptr_cache(cache):
    Path(PTR_CACHE_FILE).write_text(json.dumps(cache, indent=2), encoding="utf-8")

def reverse_dns(ip, cache):
    if ip in cache:
        return cache[ip]
    try:
        name = socket.gethostbyaddr(ip)[0]
    except Exception:
        name = None
    cache[ip] = name
    time.sleep(args.delay)
    return name

def ping_ip(ip):
    """
    Perform a single ICMP ping. Returns True if reachable.
    Uses system ping for portability.
    """
    # Platform-specific ping flags: -c 1 (count 1) -W timeout (Linux). Use -w 1 on mac? We'll try common flags.
    try:
        proc = subprocess.run(["ping", "-c", "1", "-W", "1", ip],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=4)
        return proc.returncode == 0
    except Exception:
        try:
            # fallback for macOS (timeout uses -W in seconds float not supported), so use -c 1 -W 1000ms? if fails, return False
            proc = subprocess.run(["ping", "-c", "1", ip],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=4)
            return proc.returncode == 0
        except Exception:
            return False

def score_candidate(original_prefix_len, ptr, ping_alive):
    """
    Score by:
      - base: longer original prefixlen (more specific) -> higher
      - PTR presence -> boost
      - PTR service keyword -> additional boost
      - ping alive -> big boost
    Normalize base to WEIGHT_BASE range.
    """
    base_component = (min(original_prefix_len, 24) / 24.0) * WEIGHT_BASE
    score = base_component
    ptr_flag = False
    ptr_service_flag = False
    if ptr:
        score += WEIGHT_PTR
        ptr_flag = True
        # check service-like words
        low = ptr.lower()
        for kw in SERVICE_KEYWORDS:
            if kw in low:
                score += WEIGHT_PTR_SERVICE
                ptr_service_flag = True
                break
    if ping_alive:
        score += WEIGHT_PING
    return score, ptr_flag, ptr_service_flag

# ---------- Main flow ----------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Produce prioritized /24 traceroute targets from ASNs")
    parser.add_argument("--count", type=int, default=150, help="Number of target IPs to produce (50-200 recommended)")
    parser.add_argument("--delay", type=float, default=DELAY, help="Delay (s) between DNS/ping ops")
    parser.add_argument("--ping", action="store_true", help="Enable ICMP ping check (slower, optional)")
    parser.add_argument("--out-csv", default="prioritized_targets.csv", help="CSV output filename")
    parser.add_argument("--out-txt", default="targets.txt", help="Plain target list file (one IP per line)")
    parser.add_argument("--sample-per-prefix", type=int, default=SAMPLE_PER_BIG_PREFIX,
                        help="Max /24 samples to take from a big prefix (e.g., from /16)")
    args = parser.parse_args()
    SAMPLE_PER_BIG_PREFIX = args.sample_per_prefix

    ptr_cache = load_ptr_cache()

    candidates = []  # each entry: dict with asn,name,orig_prefix,net24,ip,ptr,...
    print("[*] Fetching prefixes from BGPView for configured ASNs...")
    for asn, name in ASNS.items():
        try:
            prefixes = fetch_prefixes(asn)
        except Exception as e:
            print(f"[!] Failed to fetch prefixes for AS{asn}: {e}")
            continue
        print(f"    AS{asn} ({name}): {len(prefixes)} prefixes")
        for p in prefixes:
            try:
                net = ipaddress.ip_network(p, strict=False)
            except Exception:
                continue
            # only IPv4
            if net.version != 4:
                continue
            # expand to /24 candidates (sample large nets)
            nets24 = expand_to_24s(p)
            for n24 in nets24:
                ip = center_ip_of_24(n24)
                candidates.append({
                    "asn": asn,
                    "name": name,
                    "orig_prefix": p,
                    "orig_prefix_len": net.prefixlen,
                    "net24": str(n24),
                    "target_ip": ip
                })

    print(f"[*] Generated {len(candidates)} /24 candidates (after sampling).")
    # enrichment & scoring
    enriched = []
    for i, c in enumerate(candidates):
        ip = c["target_ip"]
        # PTR lookup (cached)
        ptr = reverse_dns(ip, ptr_cache)
        ping_alive = False
        if args.ping:
            ping_alive = ping_ip(ip)
            time.sleep(args.delay)
        score, ptr_flag, ptr_service = score_candidate(c["orig_prefix_len"], ptr, ping_alive)
        reason = []
        reason.append(f"base_prflen={c['orig_prefix_len']}")
        if ptr_flag:
            reason.append("ptr")
        if ptr_service:
            reason.append("ptr_service")
        if ping_alive:
            reason.append("ping_ok")
        enriched.append({
            **c,
            "ptr": ptr or "",
            "ping": ping_alive,
            "score": round(score, 2),
            "reason": ";".join(reason)
        })

    # sort by score desc
    enriched_sorted = sorted(enriched, key=lambda x: x["score"], reverse=True)

    # take top N
    top_n = max(1, min(args.count, len(enriched_sorted)))
    top_list = enriched_sorted[:top_n]

    # save CSV
    fieldnames = ["asn","name","orig_prefix","orig_prefix_len","net24","target_ip","ptr","ping","score","reason"]
    with open(args.out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in enriched_sorted:
            writer.writerow({k: row.get(k, "") for k in fieldnames})
    # save plain targets
    with open(args.out_txt, "w", encoding="utf-8") as f:
        for r in top_list:
            f.write(r["target_ip"] + "\n")

    save_ptr_cache(ptr_cache)
    print(f"[*] Wrote full scored list to {args.out_csv}")
    print(f"[*] Wrote top {top_n} targets to {args.out_txt}")
    print("[*] Summary (top items):")
    for r in top_list[:20]:
        print(f"  {r['target_ip']} (AS{r['asn']} {r['name']}) score={r['score']} reason={r['reason']} ptr={r['ptr']} ping={r['ping']}")
