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

1.  **Configure limits**: Open `backfill_wakatime.py` and set `START_TIME_STR` and `END_TIME_STR` to your desired window.
2.  **Dry Run**: Run the script without arguments to see how many heartbeats would be sent.
    ```bash
    python backfill_wakatime.py
    ```
3.  **Execute**: Run with `--execute` to actually send the data.
    ```bash
    python backfill_wakatime.py --execute
    ```

## Configuration

modify the `HISTORY_DIR`, `START_TIME_STR`, and `END_TIME_STR` variables at the top of the script.

```python
HISTORY_DIR = "/home/steven/.antigravity-server/data/User/History"
START_TIME_STR = "Dec 10 2025 5:58 pm MST"
END_TIME_STR = "Dec 11 2025 7:58 pm MST"
```
