import os
import json
import subprocess
import sys
import time
from datetime import datetime
from urllib.parse import unquote, urlparse
from dateutil import parser
from dateutil import tz

import argparse

# Configuration defaults
DEFAULT_HISTORY_DIR = "/home/steven/.antigravity-server/data/User/History"
DEFAULT_START_TIME = "Dec 10 2025 5:58 pm MST"
DEFAULT_END_TIME = "Dec 11 2025 7:58 pm MST"

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


def main():
    parser_args = argparse.ArgumentParser(
        description="Backfill WakaTime history from VS Code Local History."
    )
    parser_args.add_argument(
        "--history-dir",
        default=DEFAULT_HISTORY_DIR,
        help="Path to VS Code Local History directory",
    )
    parser_args.add_argument(
        "--start",
        default=DEFAULT_START_TIME,
        help="Start time (e.g. 'Dec 10 2025 5:58 pm MST')",
    )
    parser_args.add_argument(
        "--end",
        default=DEFAULT_END_TIME,
        help="End time (e.g. 'Dec 11 2025 7:58 pm MST')",
    )
    parser_args.add_argument(
        "--execute",
        action="store_true",
        help="Execute the backfill (send data to WakaTime). Default is dry-run.",
    )
    args = parser_args.parse_args()

    dry_run = not args.execute

    print(f"Starting WakaTime backfill (Dry Run: {dry_run})")
    try:
        start_ts = get_timestamp(args.start)
        end_ts = get_timestamp(args.end)
    except Exception as e:
        print(f"Error parsing dates: {e}")
        sys.exit(1)

    print(f"Time window: {args.start} ({start_ts}) to {args.end} ({end_ts})")
    print(f"History Directory: {args.history_dir}")

    heartbeats = []

    if not os.path.exists(args.history_dir):
        print(f"Error: History directory not found: {args.history_dir}")
        sys.exit(1)

    for root, dirs, files in os.walk(args.history_dir):
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
        print("\nTo actually send data, run with --execute")
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
    main()
