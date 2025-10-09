#!/usr/bin/env python3
import requests, json

# --- Targets: ASN number and short name ---
ASNS = {
    3462: "HiNet",
    4780: "SEEDNet",
    1659: "TANet",
    7539: "TWAREN",
    9924: "TFN"
}

API_URL = "https://api.bgpview.io/asn/{asn}/prefixes"

for asn, name in ASNS.items():
    print(f"[+] Fetching prefixes for AS{asn} ({name})...")
    r = requests.get(API_URL.format(asn=asn), timeout=30)
    r.raise_for_status()
    data = r.json()

    v4_list = [p["prefix"] for p in data["data"]["ipv4_prefixes"]]
    v6_list = [p["prefix"] for p in data["data"]["ipv6_prefixes"]]

    with open(f"{name}_AS{asn}_ipv4.txt", "w") as f4:
        f4.write("\n".join(v4_list))
    with open(f"{name}_AS{asn}_ipv6.txt", "w") as f6:
        f6.write("\n".join(v6_list))

    print(f"    -> {len(v4_list)} IPv4 and {len(v6_list)} IPv6 prefixes saved")

print("\n✅ Done. You now have one file per ASN in the current directory.")
