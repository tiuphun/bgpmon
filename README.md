# BGPMon - Taiwan BGP Routing Analysis & Traceroute Tool

A comprehensive toolkit for analyzing Taiwan's BGP routing infrastructure, extracting traceroute targets, and visualizing autonomous system (AS) relationships. This project processes RouteViews BGP data to identify strategic measurement targets for network topology research.

## Overview

BGPMon extracts actionable intelligence from BGP routing tables to support network measurement campaigns focused on Taiwan's Internet infrastructure. The toolkit identifies border routers, generates prioritized traceroute target lists, and analyzes inter-AS relationships for major Taiwan ISPs.

## Features

- **BGP Data Processing**: Parses RouteViews BGP dumps to extract routing information for Taiwan ASNs
- **Target Extraction**: Identifies next-hop IPs (border/edge routers) for traceroute measurements
- **Geolocation**: Maps IP prefixes to geographic locations using MaxMind and ip-api.com
- **Priority Scoring**: Ranks targets by frequency and strategic importance
- **AS Path Analysis**: Discovers peering relationships and transit providers
- **Visualization**: Generates publication-quality charts of AS frequency distributions
- **Automated Measurements**: Scripts for continuous traceroute data collection with database logging

## Project Structure

```
bgpmon/
├── ip-extractor/                    # Core BGP data extraction
│   ├── ip_extractor.py             # Main extraction script
│   ├── targets_AS*.txt             # Per-ASN target lists
│   ├── traceroute_targets.json     # Structured target data
│   └── vantage_points_guide.txt    # Measurement platform recommendations
│
├── extracted_prefixes/              # Advanced target generation
│   ├── next_target.py              # Strategic IP selection from prefixes
│   ├── targets_nexthop_AS*.txt     # Border router targets per ASN
│   ├── targets_prefix_AS*.txt      # Prefix-based targets per ASN
│   └── targets_priority_combined.txt # Top 100 priority targets
│
├── build-target-list/               # Geographic target selection
│   ├── build_target_list.py        # Score and rank targets by city
│   ├── taiwan_target_list.csv      # Prioritized target database
│   └── targets.txt                 # Formatted probe list
│
├── prefixes/                        # Raw prefix data per ASN
│   ├── HiNet_AS3462_ipv4.txt
│   ├── SEEDNet_AS4780_ipv4.txt
│   ├── TANet_AS1659_ipv4.txt
│   └── TFN_AS9924_ipv4.txt
│
├── prefixes-geo/                    # Prefix geolocation
│   ├── get_prefixes_geo.py         # Fetch and geolocate prefixes
│   └── cache_ip_geo.json           # Geolocation cache
│
├── route-views-analysis/            # AS relationship analysis
│   ├── 1-all_taiwan_aspaths.sh     # Extract all AS paths
│   ├── 2-find_direct_neighbors.sh  # Identify peering relationships
│   ├── 3-asn_frequency.sh          # Count AS appearances
│   ├── 4-as_lookup.py              # Resolve ASN to organization names
│   ├── visualize-frequent-as.py    # Generate distribution charts
│   ├── asn_frequency.txt           # AS frequency data
│   └── asn_frequency_*.pdf/png     # Publication-ready visualizations
│
├── archives/                        # Traceroute measurement scripts
│   ├── auto_traceroute.py          # Automated traceroute with DB logging
│   ├── icmp_traceroute.py          # ICMP-based traceroute
│   ├── udp_trace.py                # UDP-based traceroute
│   └── visualize.py                # Path visualization
│
├── visualization/                   # Network topology visualization
│   ├── visualize.py                # Generate topology graphs
│   ├── taiwan_topology_*.png       # Network diagrams
│   └── taiwan_as_relationships.csv # AS relationship data
│
├── route-views.*/                   # BGP RIB dumps from collectors
│   └── rib.*.bz2                   # Compressed routing tables
│
├── ip_geo_cache.json               # Global IP geolocation cache
└── ip_ptr_cache.json               # Reverse DNS PTR cache
```

## Target Taiwan ASNs

The project focuses on five major Taiwan autonomous systems:

| ASN | Organization | Type |
|-----|--------------|------|
| **AS3462** | HiNet (Chunghwa Telecom) | Major ISP |
| **AS4780** | SeedNet (FarEasTone) | Commercial ISP |
| **AS1659** | TANet (Taiwan Academic Network) | Academic/Research |
| **AS7539** | TWAREN | Research Network |
| **AS9924** | Taiwan Fixed Network (Taiwan Mobile) | Telecommunications |

## Prerequisites

### System Requirements

- Python 3.7+
- Linux/macOS (for shell scripts)
- 10GB+ disk space for BGP dumps
- Internet connectivity for API calls

### Required Tools

```bash
# Install bgpdump for processing BGP data
# macOS:
brew install bgpdump

# Ubuntu/Debian:
sudo apt-get install bgpdump

# Or compile from source:
# https://github.com/RIPE-NCC/bgpdump
```

### Python Dependencies

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate  # On Windows

# Install required packages
pip install requests scapy ipwhois pandas matplotlib numpy
```

## Installation & Setup

1. **Clone or download the repository:**
   ```bash
   cd /path/to/bgpmon
   ```

2. **Activate virtual environment:**
   ```bash
   source .venv/bin/activate
   ```

3. **Download BGP RIB dumps** (one-time setup):
   ```bash
   # Download from RouteViews collectors
   # Example for route-views.sg:
   mkdir -p route-views.sg
   cd route-views.sg
   wget http://archive.routeviews.org/route-views.sg/bgpdata/2024.10/RIBS/rib.20241001.0000.bz2
   cd ..
   
   # Repeat for other collectors: route-views.eqix, route-views.syd, route-views.wide
   ```

## Usage

### 1. Extract Traceroute Targets from BGP Data

**Basic target extraction:**

```bash
cd ip-extractor
python3 ip_extractor.py
```

This generates:
- `traceroute_targets.json` - Structured target data
- `targets_AS*.txt` - Per-ASN IP lists with frequency annotations
- `traceroute_targets_priority.txt` - Top 100 priority targets
- `vantage_points_guide.txt` - Measurement platform recommendations

**Advanced target extraction with prefix analysis:**

```bash
cd extracted_prefixes
python3 next_target.py
```

This generates more strategic targets:
- `targets_nexthop_AS*.txt` - BGP next-hop IPs (border routers)
- `targets_prefix_AS*.txt` - Strategic IPs from prefix blocks
- `targets_priority_combined.txt` - Combined priority list
- `targets_complete_data.json` - Complete data export

### 2. Generate Geographic Target List

Build a geographically diverse target list with city-based scoring:

```bash
cd build-target-list
python3 build_target_list.py
```

Outputs:
- `taiwan_target_list.csv` - Scored and ranked targets
- `targets.txt` - Formatted list grouped by city
- `prefix_geo_cache.json` - Geolocation cache

### 3. Analyze AS Relationships

**Extract all Taiwan AS paths from BGP dumps:**

```bash
cd route-views-analysis
./1-all_taiwan_aspaths.sh
```

**Find direct peering neighbors:**

```bash
./2-find_direct_neighbors.sh
```

**Count AS frequency in paths:**

```bash
./3-asn_frequency.sh
```

**Lookup AS organization names:**

```bash
python3 4-as_lookup.py 3-asn_frequency.txt asn_info.txt
```

**Generate visualizations:**

```bash
python3 visualize-frequent-as.py
```

This creates publication-ready charts:
- `asn_frequency_full.png/pdf` - Complete AS distribution
- `asn_frequency_top20.png/pdf` - Top 20 ASNs
- `asn_frequency_cumulative.png/pdf` - Cumulative distribution

### 4. Run Automated Traceroute Measurements

**Set up the SQLite database:**

```bash
cd archives
sqlite3 bgp_measurements.db < create_table.sql
```

**Run single traceroute campaign:**

```bash
sudo python3 auto_traceroute.py
```

**Set up continuous measurements via cron:**

```bash
# Edit crontab
crontab -e

# Add hourly measurements:
0 * * * * cd /path/to/bgpmon/archives && sudo python3 auto_traceroute.py >> measurement_log.txt 2>&1
```

**Query measurement results:**

```bash
sqlite3 bgp_measurements.db "SELECT * FROM measurements ORDER BY timestamp DESC LIMIT 10;"
```

### 5. Geolocate IP Prefixes

```bash
cd prefixes-geo
python3 get_prefixes_geo.py
```

Generates CSV files with geographic data for each ASN's prefixes.

## Measurement Platforms

### Recommended: RIPE Atlas

RIPE Atlas is the preferred platform for traceroute measurements:

1. **Register**: https://atlas.ripe.net
2. **Request credits** for research (free for academic use)
3. **Select probes** in Taiwan and neighboring countries
4. **Run measurements** using the target lists

**Example command:**
```bash
ripe-atlas measure traceroute --target <TARGET_IP> \
  --probes country:TW --probes 50 \
  --description "Taiwan ISP topology mapping"
```

### Alternative: Cloud VPS

Deploy measurement nodes on cloud platforms:
- **Taiwan**: Google Cloud (asia-east1), AWS (closest: Tokyo)
- **Regional**: Hong Kong, Singapore, Tokyo, Seoul
- **Global**: US West, Europe

### Alternative: PlanetLab

For academic users with institutional access:
- Check http://www.planet-lab.org
- Taiwan nodes typically at NTU, NCTU, Academia Sinica

## Data Sources

- **BGP Routing Tables**: RouteViews Project (http://www.routeviews.org)
- **AS Information**: RIPE Stat API
- **Geolocation**: ip-api.com, MaxMind GeoLite2
- **Prefix Data**: BGPView API (https://bgpview.io)

## Output Files Explained

### Target Lists

- **`traceroute_targets_priority.txt`**: Top 100 IPs ranked by frequency across all ASNs
- **`targets_nexthop_AS*.txt`**: BGP next-hop IPs (likely border routers) per ASN
- **`targets_prefix_AS*.txt`**: Strategic IPs from announced prefixes per ASN
- **`taiwan_target_list.csv`**: Geographically diverse targets with scoring

### Analysis Results

- **`asn_frequency.txt`**: Count of AS appearances in BGP paths
- **`*_neighbors.txt`**: Direct peering relationships for each Taiwan ASN
- **`all_taiwan_aspaths.txt`**: All AS paths involving Taiwan ASNs
- **`taiwan_as_relationships.csv`**: Structured relationship data

### Measurement Data

- **`bgp_measurements.db`**: SQLite database with traceroute results
- **`measurement_log.txt`**: Execution logs from automated runs

## Configuration

### Adjusting Target Count

In `build-target-list/build_target_list.py`:
```python
TARGET_COUNT = 150  # Modify as needed
```

### Changing API Rate Limits

In `prefixes-geo/get_prefixes_geo.py`:
```python
DEFAULT_DELAY = 1.5  # Seconds between API calls
```

### Selecting BGP Collectors

In `ip-extractor/ip_extractor.py`:
```python
collectors = ['route-views.eqix', 'route-views.sg', 'route-views.syd', 'route-views.wide']
```

## Best Practices

### Measurement Ethics

- Rate limit to ≤1 traceroute/second per target
- Respect network policies and acceptable use guidelines
- Use multiple vantage points to reduce load per network
- Run measurements during off-peak hours when possible

### Data Collection

- Collect data over multiple days/weeks for temporal patterns
- Use both ICMP and UDP traceroutes for comparison
- Repeat measurements 5-10 times per target for reliability
- Document vantage point locations and timestamps

### Performance Tips

- Cache geolocation results to minimize API calls
- Process BGP dumps in parallel when possible
- Use latest RIB dumps (not full UPDATE streams)
- Store intermediate results to avoid reprocessing

## Troubleshooting

### BGP Dump Processing Fails

```bash
# Verify bgpdump is installed
which bgpdump

# Test on small dump
bgpdump -m route-views.sg/rib.*.bz2 | head -20

# Check file permissions
ls -la route-views.*/
```

### No Taiwan Routes Found

- Ensure you're using RIB dumps (not UPDATE messages)
- Verify Taiwan ASNs are in the routing table
- Check BGP dump date (use recent data)
- Try different RouteViews collectors

### API Rate Limiting

- Increase `DEFAULT_DELAY` in geolocation scripts
- Use cached results when available
- Consider self-hosting MaxMind GeoLite2 database

### Permission Errors (Traceroute)

Traceroute requires root/admin privileges:
```bash
sudo python3 auto_traceroute.py
```

Or use setcap on Linux:
```bash
sudo setcap cap_net_raw+ep $(which python3)
```

## Database Schema

The SQLite database stores measurement results:

```sql
CREATE TABLE measurements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    source_region TEXT,
    destination_ip TEXT,
    bgp_as_path TEXT,
    latency_ms REAL,
    traceroute_result TEXT
);
```

Query examples:
```sql
-- Latest measurements
SELECT * FROM measurements ORDER BY timestamp DESC LIMIT 10;

-- Average latency by destination
SELECT destination_ip, AVG(latency_ms) as avg_latency 
FROM measurements 
GROUP BY destination_ip 
ORDER BY avg_latency;

-- Measurements by AS path
SELECT bgp_as_path, COUNT(*) as count 
FROM measurements 
GROUP BY bgp_as_path 
ORDER BY count DESC;
```

## Research Applications

This toolkit supports research in:

- **Internet topology mapping**: Discover router-level connectivity
- **AS relationship inference**: Identify customer-provider vs. peering links
- **Latency analysis**: Measure performance between networks
- **Routing policy analysis**: Study BGP route selection
- **Network resilience**: Analyze path diversity and redundancy
- **Geolocation validation**: Compare BGP vs. geographic proximity

## Contributing

Contributions welcome! Areas for improvement:

- Additional BGP collectors (RIPE RIS, PCH, etc.)
- IPv6 support throughout the pipeline
- Real-time BGP stream processing
- Machine learning for target prioritization
- Web dashboard for visualization
- Integration with other measurement platforms

## Limitations

- Geolocation accuracy depends on IP-to-location database precision (50-200km typical)
- BGP next-hops may not always be traceroute-responsive
- Some targets may have firewall rules blocking probes
- API rate limits constrain large-scale data collection
- Results depend on vantage point selection and network policies

## License

This project uses:
- BGP data from RouteViews (public domain)
- RIPE Stat API (RIPE NCC terms)
- ip-api.com (free tier with rate limits)
- MaxMind GeoLite2 (CC BY-SA 4.0)

Please review individual data source licenses before commercial use.

## References

- RouteViews Project: http://www.routeviews.org
- RIPE Atlas: https://atlas.ripe.net
- RIPE Stat: https://stat.ripe.net
- BGPView: https://bgpview.io
- BGP Overview: https://www.ietf.org/rfc/rfc4271.txt

## Author
Tieu-Phuong Nguyen, National Chung Cheng University 

(TEEP Intern Fall 2025 @CISLab, Department of Computer Science and Information Engineering)

## Acknowledgments

- University of Oregon RouteViews Project
- RIPE NCC for measurement infrastructure
- Taiwan ISPs for operating critical Internet infrastructure
- Open source BGP analysis community
