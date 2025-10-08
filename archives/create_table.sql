CREATE TABLE measurements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    source_region TEXT NOT NULL,
    destination_ip TEXT NOT NULL,
    bgp_as_path TEXT,
    latency_ms REAL,
    traceroute_result TEXT
);