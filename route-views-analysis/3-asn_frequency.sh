# Extract all ASNs from paths and count frequency
grep "^ASPATH:" all_taiwan_aspaths.txt | \
  sed 's/ASPATH: //' | \
  tr ' ' '\n' | \
  grep -E "^[0-9]+$" | \
  sort | uniq -c | sort -rn > asn_frequency.txt

# Top 20 most frequent ASNs (likely tier-1/tier-2 providers)
head -20 asn_frequency.txt