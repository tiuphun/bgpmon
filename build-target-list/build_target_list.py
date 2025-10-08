#!/usr/bin/env python3
import requests
import ipaddress
import time
import json
import csv
from collections import defaultdict
from pathlib import Path

# === Configuration ===
ASNS = {
    3462: "HiNet",
    4780: "SEEDNet",
    1659: "TANet",
    7539: "TWAREN",
    9924: "TFN"
}
OUT_CSV = "taiwan_target_list.csv"
OUT_TXT = "targets.txt"
CACHE_FILE = "prefix_geo_cache.json"
TARGET_COUNT = 150  # adjust as needed
DELAY = 1.2

# === Utilities ===
def load_cache(file):
    if Path(file).exists():
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return {}

def save_cache(cache, file):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

def get_prefixes(asn):
    url = f"https://api.bgpview.io/asn/{asn}/prefixes"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    j = resp.json()["data"]
    prefixes = [p["prefix"] for p in j.get("ipv4_prefixes", [])]
    return prefixes

def prefix_center_ip(prefix):
    net = ipaddress.ip_network(prefix, strict=False)
    mid = int(net.network_address) + net.num_addresses // 2
    return str(ipaddress.ip_address(mid))

def geolocate_ip(ip, cache):
    if ip in cache:
        return cache[ip]
    try:
        r = requests.get(f"http://ip-api.com/json/{ip}?fields=country,regionName,city,lat,lon,status,message", timeout=5)
        data = r.json()
    except Exception as e:
        data = {"status": "fail", "message": str(e)}
    cache[ip] = data
    time.sleep(DELAY)
    return data

def prefix_score(prefix, geo):
    """
    Simpler scoring: prefer /24, prefer populated cities
    """
    net = ipaddress.ip_network(prefix, strict=False)
    score = 0
    if net.prefixlen == 24:
        score += 5
    elif net.prefixlen < 24:
        # larger prefixes get less weight
        score += max(0, 5 - (24 - net.prefixlen))
    city = geo.get("city")
    if city in ("Taipei", "New Taipei", "Taichung", "Tainan", "Kaohsiung", "Hsinchu"):
        score += 3
    return score

# === Main ===
def main():
    geo_cache = load_cache(CACHE_FILE)
    candidates = []

    for asn, name in ASNS.items():
        prefixes = get_prefixes(asn)
        print(f"AS{asn} {name}: {len(prefixes)} prefixes")
        for prefix in prefixes:
            if ":" in prefix:
                continue
            ip = prefix_center_ip(prefix)
            geo = geolocate_ip(ip, geo_cache)
            score = prefix_score(prefix, geo)
            candidates.append({
                "asn": asn,
                "org": name,
                "prefix": prefix,
                "center_ip": ip,
                "city": geo.get("city") or "Unknown",
                "score": score
            })

    save_cache(geo_cache, CACHE_FILE)

    # Sort by score descending
    candidates.sort(key=lambda x: x["score"], reverse=True)

    # Optionally enforce diversity by city
    by_city = defaultdict(list)
    for c in candidates:
        by_city[c["city"]].append(c)

    final = []
    while len(final) < TARGET_COUNT and any(by_city.values()):
        # iterate cities in order of descending number of candidates
        sorted_cities = sorted(by_city.keys(), key=lambda c: -len(by_city[c]))
        for city in sorted_cities:
            if by_city[city]:
                final.append(by_city[city].pop(0))
            if len(final) >= TARGET_COUNT:
                break

    # Write CSV
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=final[0].keys())
        writer.writeheader()
        writer.writerows(final)
    print(f"Wrote {len(final)} targets to {OUT_CSV}")

    # Write probe list file
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        grouped = defaultdict(list)
        for entry in final:
            key = (entry["asn"], entry["org"], entry["city"])
            grouped[key].append(entry)
        for (asn, org, city), items in sorted(grouped.items()):
            f.write(f"# AS{asn} {org} — {city}\n")
            for it in items:
                f.write(f"{it['center_ip']}\n")
            f.write("\n")
    print(f"Wrote probe list to {OUT_TXT}")

if __name__ == "__main__":
    main()
