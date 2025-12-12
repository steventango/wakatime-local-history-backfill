# WakaTime Local History Backfill

This script allows you to backfill WakaTime heartbeats using VS Code's Local History. This is useful if the WakaTime extension fails to log a period of time but you still have local history entries preserved by VS Code.

## Features

- Scans VS Code Local History directory for `entries.json` files.
- Filters edits based on a configurable time window.
- Deduplicates entries to prevent spamming the API (default: 1 heartbeat per 2 minutes per file).
- Uses `wakatime-cli` to send heartbeats, ensuring accurate project detection and metadata.
- Handles missing/deleted files by flagging them as unsaved entities.
- Bypasses offline buffering to force immediate sync.

## Prerequisites

- Python 3
- `wakatime-cli` (usually installed via the VS Code extension or `pip install wakatime`)
- `python-dateutil` library

## Usage

1.  **Dry Run** (Default):
    ```bash
    python backfill_wakatime.py
    ```

2.  **Custom Configuration**:
    You can specify the history directory and time window via arguments:
    ```bash
    python backfill_wakatime.py \
        --history-dir "/path/to/history" \
        --start "Dec 10 2025 6:00 pm MST" \
        --end "Dec 11 2025 8:00 pm MST"
    ```

3.  **Execute**: Add `--execute` to actually send the data.
    ```bash
    python backfill_wakatime.py --execute
    ```

## Arguments

- `--history-dir`: Path to VS Code Local History directory (default: `~/.antigravity-server/data/User/History`)
- `--start`: Start time for backfill (default: "Dec 10 2025 5:58 pm MST")
- `--end`: End time for backfill (default: "Dec 11 2025 7:58 pm MST")
- `--execute`: Flag to send data to WakaTime API. If omitted, runs in dry-run mode.
