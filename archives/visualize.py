import pandas as pd
import matplotlib.pyplot as plt

# Load the data from the database directly
df = pd.read_sql_query("SELECT timestamp, latency_ms, destination_ip FROM measurements WHERE source_region='local_mac'", 'sqlite:///bgp_measurements.db')

# Convert timestamp to datetime
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Create a plot
plt.figure(figsize=(12, 6))
for ip, group in df.groupby('destination_ip'):
    plt.plot(group['timestamp'], group['latency_ms'], label=ip, marker='o', linestyle='-')

plt.title('Latency to Taiwanese Targets Over Time')
plt.xlabel('Time')
plt.ylabel('Latency (ms)')
plt.legend()
plt.grid(True)
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('latency_trends.png')  # Save the plot
plt.show()