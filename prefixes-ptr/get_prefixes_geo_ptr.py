import requests
import ipaddress
import csv
import time
import json
import socket
from pathlib import Path

# === Configuration ===
ASNS = {
    3462: "HiNet",
    4780: "SEEDNet",
    1659: "TANet",
    7539: "TWAREN"
}
CACHE_FILE = "ip_geo_cache.json"
PTR_CACHE_FILE = "ip_ptr_cache.json"
DELAY = 1.5  # seconds between geolocation API requests

# === Utilities ===
def get_prefixes(asn):
    url = f"https://api.bgpview.io/asn/{asn}/prefixes"
    res = requests.get(url)
    res.raise_for_status()
    data = res.json()["data"]
    prefixes = [p["prefix"] for p in data["ipv4_prefixes"]] + [p["prefix"] for p in data["ipv6_prefixes"]]
    return prefixes

def prefix_center_ip(prefix):
    net = ipaddress.ip_network(prefix, strict=False)
    mid = int(net.network_address) + net.num_addresses // 2
    return str(ipaddress.ip_address(mid))

def load_cache(file):
    if Path(file).exists():
        with open(file, "r") as f:
            return json.load(f)
    return {}

def save_cache(cache, file):
    with open(file, "w") as f:
        json.dump(cache, f, indent=2)

def geolocate_ip(ip, cache):
    if ip in cache:
        return cache[ip]
    url = f"http://ip-api.com/json/{ip}?fields=status,country,regionName,city,lat,lon,message"
    r = requests.get(url)
    data = r.json()
    cache[ip] = data
    time.sleep(DELAY)
    return data

def reverse_dns(ip, cache):
    if ip in cache:
        return cache[ip]
    try:
        hostname = socket.gethostbyaddr(ip)[0]
    except Exception:
        hostname = None
    cache[ip] = hostname
    return hostname

# === Main ===
def main():
    geo_cache = load_cache(CACHE_FILE)
    ptr_cache = load_cache(PTR_CACHE_FILE)

    for asn, name in ASNS.items():
        print(f"Fetching prefixes for {name} (AS{asn})...")
        prefixes = get_prefixes(asn)
        results = []

        for prefix in prefixes:
            center_ip = prefix_center_ip(prefix)
            geo = geolocate_ip(center_ip, geo_cache)
            hostname = reverse_dns(center_ip, ptr_cache)

            results.append({
                "ASN": asn,
                "Org": name,
                "Prefix": prefix,
                "Center_IP": center_ip,
                "PTR_Hostname": hostname,
                "Status": geo.get("status"),
                "Country": geo.get("country"),
                "Region": geo.get("regionName"),
                "City": geo.get("city"),
                "Latitude": geo.get("lat"),
                "Longitude": geo.get("lon"),
                "Message": geo.get("message")
            })

        # Save per-AS CSV
        out_file = f"{name}_AS{asn}_prefixes.csv"
        with open(out_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)

        print(f"  → {len(results)} prefixes saved to {out_file}")

    save_cache(geo_cache, CACHE_FILE)
    save_cache(ptr_cache, PTR_CACHE_FILE)
    print("\n✅ All done! Cached data saved to:")
    print("   -", CACHE_FILE)
    print("   -", PTR_CACHE_FILE)

if __name__ == "__main__":
    main()
