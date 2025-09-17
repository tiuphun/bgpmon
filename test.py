import datetime
import os

# Get the user's home directory (cron runs with a limited environment)
home_dir = os.path.expanduser("~")
log_path = os.path.join(home_dir, "cron_test.log")

# Create/log execution timestamp
with open(log_path, "a") as log_file:
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_file.write(f"Cron job executed at {timestamp}\n")