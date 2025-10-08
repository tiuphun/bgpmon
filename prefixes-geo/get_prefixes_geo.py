#!/usr/bin/env python3
"""
Fetch IPv4/IPv6 prefixes for target ASNs (via BGPView),
choose a center IP for each prefix, geolocate the center IP using ip-api.com,
and save per-AS CSV files with geography fields.

Produces files:
  <Name>_AS<asn>_prefixes_geolocated.csv
  cache_ip_geo.json    (local cache of IP -> geo result)

Dependencies: requests (pip install requests)
Run: python3 get_prefixes_with_geo.py
"""

import requests
import json
import time
import argparse
import csv
import sys
import os
from ipaddress import ip_network, IPv4Network, IPv6Network, IPv4Address, IPv6Address

# --- Configuration: targets ---
ASNS = {
    3462: "HiNet",
    4780: "SEEDNet",
    1659: "TANet",
    7539: "TWAREN"
}

BGPVIEW_PREFIXES_URL = "https://api.bgpview.io/asn/{asn}/prefixes"
IP_API_URL = "http://ip-api.com/json/{ip}?fields=status,message,country,regionName,city,lat,lon,query,timezone,isp,as"

# Cache filename for IP -> geo JSON
CACHE_FILE = "cache_ip_geo.json"

# Default delay (seconds) between API calls — adjustable to avoid rate limits
DEFAULT_DELAY = 1.5

# Simple exponential backoff retries for ip-api calls
MAX_RETRIES = 4
BACKOFF_FACTOR = 2.0

# --- Utility functions ---
def load_cache(path=CACHE_FILE):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            # If cache is corrupted, start fresh
            return {}
    return {}

def save_cache(cache, path=CACHE_FILE):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(cache, fh, indent=2, ensure_ascii=False)

def fetch_prefixes_for_asn(asn):
    url = BGPVIEW_PREFIXES_URL.format(asn=asn)
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    j = r.json()
    # return lists of prefix strings
    v4 = [p["prefix"] for p in j["data"].get("ipv4_prefixes", [])]
    v6 = [p["prefix"] for p in j["data"].get("ipv6_prefixes", [])]
    return v4, v6, j

def prefix_center_ip(prefix_str):
    """
    Choose a central IP for a prefix:
    - Convert to ip_network, then pick network_address + (num_addresses // 2)
    - Avoid returning network or broadcast if possible (for very small nets)
    """
    net = ip_network(prefix_str, strict=False)
    num = net.num_addresses
    mid_offset = num // 2
    center_int = int(net.network_address) + mid_offset
    center_ip = net.network_address + mid_offset
    # Convert to string
    return str(center_ip)

def geolocate_ip(ip, cache, session, delay):
    """
    Use ip-api.com to geolocate ip.
    Use local cache if present. Implements retries with backoff.
    Returns dict with fields or an error state.
    """
    if ip in cache:
        return cache[ip]

    # attempt with retries
    attempt = 0
    while attempt <= MAX_RETRIES:
        try:
            url = IP_API_URL.format(ip=ip)
            resp = session.get(url, timeout=15)
            if resp.status_code != 200:
                raise requests.RequestException(f"HTTP {resp.status_code}")
            data = resp.json()
            # ip-api returns {"status":"success", ...} or {"status":"fail","message":"..."}
            cache[ip] = data
            # be polite: sleep a bit after a successful request
            time.sleep(delay)
            return data
        except Exception as e:
            attempt += 1
            wait = (BACKOFF_FACTOR ** attempt)
            if attempt > MAX_RETRIES:
                # record failure in cache to avoid repeated failed attempts
                cache[ip] = {"status": "error", "message": str(e)}
                return cache[ip]
            time.sleep(wait)
    # unreachable
    cache[ip] = {"status": "error", "message": "unreachable"}
    return cache[ip]

def sanitize_cell(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)

# --- Main workflow ---
def main(delay=DEFAULT_DELAY, save_json=False, target_asns=None):
    cache = load_cache()
    session = requests.Session()
    session.headers.update({"User-Agent": "prefix-geo-script/1.0 (+https://example.org/)"})

    asns = target_asns if target_asns else list(ASNS.keys())

    for asn in asns:
        name = ASNS.get(asn, f"AS{asn}")
        print(f"[+] Processing AS{asn} ({name}) ...")
        try:
            v4_list, v6_list, raw = fetch_prefixes_for_asn(asn)
        except Exception as e:
            print(f"    ERROR fetching prefixes for AS{asn}: {e}", file=sys.stderr)
            continue

        rows = []
        # Process IPv4 prefixes
        for p in v4_list:
            try:
                center = prefix_center_ip(p)
            except Exception as e:
                center = ""
            geo = None
            if center:
                geo = geolocate_ip(center, cache, session, delay)
            row = {
                "asn": asn,
                "name": name,
                "prefix": p,
                "family": "ipv4",
                "center_ip": center,
                "geo_status": geo.get("status") if isinstance(geo, dict) else "",
                "geo_message": geo.get("message", "") if isinstance(geo, dict) else "",
                "country": geo.get("country", "") if isinstance(geo, dict) else "",
                "region": geo.get("regionName", "") if isinstance(geo, dict) else "",
                "city": geo.get("city", "") if isinstance(geo, dict) else "",
                "lat": geo.get("lat", "") if isinstance(geo, dict) else "",
                "lon": geo.get("lon", "") if isinstance(geo, dict) else "",
                "isp": geo.get("isp", "") if isinstance(geo, dict) else "",
                "as": geo.get("as", "") if isinstance(geo, dict) else "",
                "query": geo.get("query", "") if isinstance(geo, dict) else ""
            }
            rows.append(row)

        # Process IPv6 prefixes
        for p in v6_list:
            try:
                center = prefix_center_ip(p)
            except Exception as e:
                center = ""
            geo = None
            if center:
                geo = geolocate_ip(center, cache, session, delay)
            row = {
                "asn": asn,
                "name": name,
                "prefix": p,
                "family": "ipv6",
                "center_ip": center,
                "geo_status": geo.get("status") if isinstance(geo, dict) else "",
                "geo_message": geo.get("message", "") if isinstance(geo, dict) else "",
                "country": geo.get("country", "") if isinstance(geo, dict) else "",
                "region": geo.get("regionName", "") if isinstance(geo, dict) else "",
                "city": geo.get("city", "") if isinstance(geo, dict) else "",
                "lat": geo.get("lat", "") if isinstance(geo, dict) else "",
                "lon": geo.get("lon", "") if isinstance(geo, dict) else "",
                "isp": geo.get("isp", "") if isinstance(geo, dict) else "",
                "as": geo.get("as", "") if isinstance(geo, dict) else "",
                "query": geo.get("query", "") if isinstance(geo, dict) else ""
            }
            rows.append(row)

        # Write per-AS CSV
        out_csv = f"{name}_AS{asn}_prefixes_geolocated.csv"
        fieldnames = ["asn","name","prefix","family","center_ip","geo_status","geo_message",
                      "country","region","city","lat","lon","isp","as","query"]
        with open(out_csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fieldnames)
            w.writeheader()
            for r in rows:
                # sanitize to avoid None
                r2 = {k: sanitize_cell(r.get(k)) for k in fieldnames}
                w.writerow(r2)
        print(f"    -> Wrote {len(rows)} rows to {out_csv}")

        # optionally save raw JSON prefix dump
        if save_json:
            json_file = f"{name}_AS{asn}_bgpview.json"
            with open(json_file, "w", encoding="utf-8") as jf:
                json.dump(raw, jf, indent=2)
            print(f"    -> Saved raw BGPView JSON to {json_file}")

        # Save cache after each ASN (progress persistence)
        save_cache(cache)

    print("\nAll done. Cache saved to", CACHE_FILE)
    save_cache(cache)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch prefixes and geolocate center IPs via ip-api.com")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY,
                        help=f"seconds to wait between ip-api requests (default {DEFAULT_DELAY})")
    parser.add_argument("--save-json", action="store_true", help="Save raw BGPView JSON per ASN")
    parser.add_argument("--asns", nargs="*", type=int, help="Optional list of ASNs to run (default: configured set)")
    args = parser.parse_args()
    main(delay=args.delay, save_json=args.save_json, target_asns=args.asns)
