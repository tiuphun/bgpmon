# BGP Monitoring Tool

Activate virtual environment: `source /Users/tieuphuong/Downloads/bgpmon/.venv/bin/activate`

## Cronjob
0 * * * * cronitor exec V7iGrw "cd /Users/tieuphuong/Downloads/bgpmon && sudo python auto_traceroute.py >> measurement_log.txt 2>&1"
* * * * * /Users/tieuphuong/Downloads/bgpmon/.venv/bin/python /Users/tieuphuong/Downloads/bgpmon/test.py oke 

Start the dashboard:
`cronitor dash`


## Database
Open database: `sqlite3 bgp_measurements.db`

Find entries:
`SELECT * FROM measurements ORDER BY timestamp DESC;`