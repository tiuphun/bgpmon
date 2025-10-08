# BGP Monitoring Tool
(still in development)

Activate virtual environment: `source /Users/tieuphuong/Downloads/bgpmon/.venv/bin/activate`
Run the script: `sudo python log_trace.py` (log version) or `sudo python auto_traceroute.py` (no-log version)
Create the database: `sqlite3 bgp_measurements.db < create_table.sql`
Open the database: `sqlite3 bgp_measurements.db`
View schema: `.schema measurements`
Find entries: `select * from measurements ORDER BY timestamp DESC;`

## Cronjob
0 * * * * cronitor exec V7iGrw "cd /Users/tieuphuong/Downloads/bgpmon && sudo python auto_traceroute.py >> measurement_log.txt 2>&1"
* * * * * /Users/tieuphuong/Downloads/bgpmon/.venv/bin/python /Users/tieuphuong/Downloads/bgpmon/test.py oke 

Start the dashboard:
`cronitor dash`