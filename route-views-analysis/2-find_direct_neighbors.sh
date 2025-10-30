# For HiNet (AS3462)
grep "^ASPATH:" all_taiwan_aspaths.txt | grep " 3462 " | \
  sed 's/ASPATH: //' | \
  awk '{
    for(i=1; i<=NF; i++) {
      if($i == "3462") {
        if(i > 1) print "neighbor:", $(i-1);
        if(i < NF) print "neighbor:", $(i+1);
      }
    }
  }' | sort | uniq -c | sort -rn > hinet_neighbors.txt

# Repeat for other ASNs
grep "^ASPATH:" all_taiwan_aspaths.txt | grep " 4780 " | \
  sed 's/ASPATH: //' | \
  awk '{
    for(i=1; i<=NF; i++) {
      if($i == "4780") {
        if(i > 1) print "neighbor:", $(i-1);
        if(i < NF) print "neighbor:", $(i+1);
      }
    }
  }' | sort | uniq -c | sort -rn > seednet_neighbors.txt

grep "^ASPATH:" all_taiwan_aspaths.txt | grep " 1659 " | \
  sed 's/ASPATH: //' | \
  awk '{
    for(i=1; i<=NF; i++) {
      if($i == "1659") {
        if(i > 1) print "neighbor:", $(i-1);
        if(i < NF) print "neighbor:", $(i+1);
      }
    }
  }' | sort | uniq -c | sort -rn > tanet_neighbors.txt

grep "^ASPATH:" all_taiwan_aspaths.txt | grep " 9924 " | \
  sed 's/ASPATH: //' | \
  awk '{
    for(i=1; i<=NF; i++) {
      if($i == "9924") {
        if(i > 1) print "neighbor:", $(i-1);
        if(i < NF) print "neighbor:", $(i+1);
      }
    }
  }' | sort | uniq -c | sort -rn > tfn_neighbors.txt

grep "^ASPATH:" all_taiwan_aspaths.txt | grep " 7539 " | \
  sed 's/ASPATH: //' | \
  awk '{
    for(i=1; i<=NF; i++) {
      if($i == "7539") {
        if(i > 1) print "neighbor:", $(i-1);
        if(i < NF) print "neighbor:", $(i+1);
      }
    }
  }' | sort | uniq -c | sort -rn > twaren_neighbors.txt