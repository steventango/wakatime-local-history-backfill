import os
import json
import subprocess
import sys
import time
from datetime import datetime
from urllib.parse import unquote, urlparse
from dateutil import parser
from dateutil import tz

# Configuration
HISTORY_DIR = "/home/steven/.antigravity-server/data/User/History"
START_TIME_STR = "Dec 10 2025 5:58 pm MST"
END_TIME_STR = "Dec 11 2025 7:58 pm MST"

# MST is UTC-7.
TZINFOS = {"MST": tz.gettz("US/Mountain"), "MDT": tz.gettz("US/Mountain")}


def get_timestamp(time_str):
    dt = parser.parse(time_str, tzinfos=TZINFOS)
    return dt.timestamp()


def parse_vscode_uri(uri):
    decoded = unquote(uri)
    try:
        parsed = urlparse(decoded)
        if parsed.scheme == "file":
            return parsed.path
        elif parsed.scheme == "vscode-remote":
            if "/home/steven/" in decoded:
                idx = decoded.find("/home/steven/")
                return decoded[idx:]

        if "/home/steven/" in decoded:
            idx = decoded.find("/home/steven/")
            return decoded[idx:]

        return parsed.path
    except Exception as e:
        print(f"Error parsing URI {uri}: {e}")
        return None


def main(dry_run=True):
    print(f"Starting WakaTime backfill (Dry Run: {dry_run})")
    start_ts = get_timestamp(START_TIME_STR)
    end_ts = get_timestamp(END_TIME_STR)
    print(f"Time window: {START_TIME_STR} ({start_ts}) to {END_TIME_STR} ({end_ts})")

    heartbeats = []

    for root, dirs, files in os.walk(HISTORY_DIR):
        if "entries.json" in files:
            entry_path = os.path.join(root, "entries.json")
            try:
                with open(entry_path, "r") as f:
                    data = json.load(f)
                    resource_uri = data.get("resource")
                    file_path = parse_vscode_uri(resource_uri)

                    if not file_path:
                        continue

                    entries = data.get("entries", [])
                    for entry in entries:
                        timestamp = entry.get("timestamp")  # ms
                        if timestamp:
                            ts_sec = timestamp / 1000.0
                            if start_ts <= ts_sec <= end_ts:
                                heartbeats.append(
                                    {
                                        "file": file_path,
                                        "time": ts_sec,
                                        "is_write": True,
                                    }
                                )
            except Exception as e:
                print(f"Error reading {entry_path}: {e}")

    # Deduplicate
    heartbeats.sort(key=lambda x: x["time"])
    unique_heartbeats = []

    last_times = {}  # file -> timestamp

    print(f"Found {len(heartbeats)} raw heartbeats entries in range.")

    for hb in heartbeats:
        f = hb["file"]
        t = hb["time"]
        if f not in last_times or (t - last_times[f] >= 120):
            unique_heartbeats.append(hb)
            last_times[f] = t

    print(f"After deduplication: {len(unique_heartbeats)} heartbeats to send.")

    if dry_run:
        print("Dry run complete. No data sent.")
        for i, hb in enumerate(unique_heartbeats[:5]):
            print(f"Sample {i + 1}: {hb}")
        return

    # Send data
    count = 0
    missing_files = 0

    for hb in unique_heartbeats:
        cmd = [
            ".venv/bin/wakatime",
            "--entity",
            hb["file"],
            "--time",
            str(hb["time"]),
            "--write",
            "--plugin",
            "antigravity_backfill",
            # FORCE sending immediately, bypass buffer
            "--heartbeat-rate-limit-seconds",
            "0",
        ]

        if not os.path.exists(hb["file"]):
            missing_files += 1
            cmd.append("--is-unsaved-entity")

        try:
            # check=True will raise error if exit code != 0
            subprocess.run(
                cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
            )
            count += 1
            if count % 10 == 0:
                print(f"Sent {count}/{len(unique_heartbeats)} heartbeats...")
        except subprocess.CalledProcessError as e:
            print(
                f"Failed to send heartbeat for {hb['file']}: {e.stderr.decode().strip()}"
            )

    print(
        f"Backfill complete. Sent {count} heartbeats. (Files missing on disk: {missing_files})"
    )


if __name__ == "__main__":
    if "--execute" in sys.argv:
        main(dry_run=False)
    else:
        main(dry_run=True)
        print("\nTo actually send data, run with --execute")
