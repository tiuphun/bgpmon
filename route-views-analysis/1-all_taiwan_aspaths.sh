# Get all AS paths containing any Taiwan ASN
for collector in route-views.eqix route-views.sg route-views.syd route-views.wide; do
  for file in $collector/rib.*.bz2; do
    bgpdump -H "$file" | grep "^ASPATH:" | \
      grep -e " 3462 | 4780 | 1659 | 7539 | 9924 "
  done
done > all_taiwan_aspaths.txt