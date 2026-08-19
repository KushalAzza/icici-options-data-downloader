"""
Download NIFTY 1-minute OHLC using Dhan Intraday Historical Data API.

Date range is configured via START_DATE and END_DATE in .env.

Documentation: https://dhanhq.co/docs/v2/historical-data/#intraday-historical-data
"""

import os
import json
import time
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv

# Load environment variables (override any existing env vars)
load_dotenv(override=True)

# Get Dhan API credentials from .env file
dhan_access_token = os.getenv("DHAN_ACCESS_TOKEN")
dhan_client_id = os.getenv("DHAN_CLIENT_ID")

# Get security id from .env file (instrument to download)
use_security_id = os.getenv("USE_SECURITY_ID")

if not dhan_access_token:
    raise ValueError("DHAN_ACCESS_TOKEN must be set in .env file")

if not use_security_id:
    raise ValueError("USE_SECURITY_ID must be set in .env file (Dhan securityId for the index, e.g. 13 for NIFTY, 21 for India VIX)")

# Strip any whitespace from token / inputs (common issue)
dhan_access_token = dhan_access_token.strip()
use_security_id = use_security_id.strip()

# Dhan API configuration (intraday historical data)
# Reference: https://dhanhq.co/docs/v2/historical-data/#intraday-historical-data
DHAN_API_BASE = "https://api.dhan.co"
DHAN_INTRADAY_ENDPOINT = f"{DHAN_API_BASE}/v2/charts/intraday"

# Data/output configuration
DATA_DIR = "data"

# Security ID (instrument) from environment
# Common values: NIFTY=13, India VIX=21
SECURITY_ID = use_security_id
EXCHANGE_SEGMENT = "IDX_I"  # Index derivatives segment
INSTRUMENT_TYPE = "INDEX"

# Intraday configuration
INTERVAL = "1"  # 1-minute interval as per Dhan intraday docs
CHUNK_DAYS = 90  # Maximum 90 days per API call (as per docs)


def fetch_nifty_intraday_close_dhan(start_date: datetime, end_date: datetime):
    """
    Fetch NIFTY 1-minute OHLC intraday data from Dhan in 90-day chunks
    and return a dict of per-day close prices.

    Structure:
        {
          "2023-01-02": [
            {"time": "2023-01-03 09:15:00", "close": 18123.4, "open": ..., "high": ..., "low": ..., "volume": ..., "timestamp": 1672644300},
            ...
          ],
          ...
        }
    """
    print(f"\n{'='*80}")
    print("Downloading NIFTY 1-minute intraday close prices using Dhan REST API...")
    print(f"Date range: {start_date.date()} to {end_date.date()}")
    print(f"{'='*80}\n")

    # Headers for API request
    headers = {
        "Content-Type": "application/json",
        "access-token": dhan_access_token,
    }

    # Add client-id if available
    if dhan_client_id:
        headers["client-id"] = dhan_client_id

    # Store per-day candle data
    per_day_data: dict[str, list[dict]] = {}

    current_start = start_date
    chunk_count = 0
    total_points = 0

    # Use non-inclusive toDate semantics as per Dhan docs:
    # For each chunk, fromDate is inclusive, toDate is non-inclusive.
    # We iterate until current_start reaches end_date + 1 day.
    final_end_exclusive = end_date + timedelta(days=1)

    while current_start < final_end_exclusive:
        chunk_count += 1

        # End of this chunk is min(start + CHUNK_DAYS, final_end_exclusive)
        chunk_end_exclusive = min(
            current_start + timedelta(days=CHUNK_DAYS),
            final_end_exclusive,
        )

        from_str = current_start.strftime("%Y-%m-%d %H:%M:%S")
        to_str = chunk_end_exclusive.strftime("%Y-%m-%d %H:%M:%S")

        print(
            f"  Chunk {chunk_count}: Fetching intraday data from "
            f"{current_start.date()} to {(chunk_end_exclusive - timedelta(days=1)).date()} "
            f"(fromDate={from_str}, toDate={to_str} non-inclusive)"
        )

        payload = {
            "securityId": SECURITY_ID,
            "exchangeSegment": EXCHANGE_SEGMENT,
            "instrument": INSTRUMENT_TYPE,
            "interval": INTERVAL,  # 1-minute candles
            "oi": False,
            "fromDate": from_str,
            "toDate": to_str,
        }

        try:
            response = requests.post(
                DHAN_INTRADAY_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=60,
            )

            if response.status_code == 200:
                data = response.json()

                # Dhan intraday response has arrays like daily:
                # open, high, low, close, volume, timestamp, open_interest
                if isinstance(data, dict) and "close" in data and "timestamp" in data:
                    closes = data.get("close", [])
                    opens = data.get("open", [])
                    highs = data.get("high", [])
                    lows = data.get("low", [])
                    volumes = data.get("volume", [])
                    timestamps = data.get("timestamp", [])

                    n = min(
                        len(closes),
                        len(opens),
                        len(highs),
                        len(lows),
                        len(volumes),
                        len(timestamps),
                    )

                    if n == 0:
                        print("    ⚠ No intraday data returned for this chunk")
                    else:
                        print(f"    ✓ API returned {n} candles for this chunk")

                        for i in range(n):
                            try:
                                ts = int(timestamps[i])
                                dt = datetime.fromtimestamp(ts)
                                date_str = dt.strftime("%Y-%m-%d")
                                time_str = dt.strftime("%Y-%m-%d %H:%M:%S")

                                candle = {
                                    "time": time_str,
                                    "close": float(closes[i]),
                                    "open": float(opens[i]),
                                    "high": float(highs[i]),
                                    "low": float(lows[i]),
                                    "volume": int(volumes[i]),
                                    "timestamp": ts,
                                }

                                per_day_data.setdefault(date_str, []).append(candle)
                                total_points += 1
                            except Exception:
                                # Skip malformed entries
                                continue
                else:
                    # Check for error response
                    if isinstance(data, dict) and "errorType" in data:
                        error_msg = data.get("errorMessage", "Unknown error")
                        print(f"    ✗ API error: {error_msg}")
                        if data.get("errorType") == "Invalid_Authentication":
                            print("    ⚠ Check DHAN_ACCESS_TOKEN in .env (may be expired)")
                    else:
                        print("    ⚠ Unexpected intraday response format")
                        print(f"    Response snippet: {str(data)[:200]}")
            else:
                print(f"    ✗ HTTP error: Status {response.status_code}")
                print(f"    Response: {response.text[:200]}")

        except Exception as e:
            print(f"    ✗ Error fetching intraday chunk: {e}")

        # Rate limiting: docs mention up to 10 requests/second for data APIs.
        # We're far below that; small sleep to be safe.
        time.sleep(0.2)

        # Move to next chunk
        current_start = chunk_end_exclusive

    print(f"\n✓ Finished downloading intraday data")
    print(f"  Total candles: {total_points}")
    print(f"  Trading days with data: {len(per_day_data)}")

    return per_day_data


def main():
    start_date_str = os.getenv("START_DATE")
    end_date_str = os.getenv("END_DATE")

    if not start_date_str or not end_date_str:
        raise ValueError("START_DATE and END_DATE must be set in .env file (format: YYYY-MM-DD)")

    start_date_str = start_date_str.strip()
    end_date_str = end_date_str.strip()

    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    except ValueError as e:
        raise ValueError(f"Invalid date format in .env file. Use YYYY-MM-DD format. Error: {e}")

    if start_date > end_date:
        raise ValueError("START_DATE must be before or equal to END_DATE")

    print(f"Downloading NIFTY 1-minute intraday data from {start_date.date()} to {end_date.date()}")

    # Ensure data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)
    output_file = os.path.join(DATA_DIR, "nifty_intraday_price.json")

    per_day_data = fetch_nifty_intraday_close_dhan(start_date, end_date)

    if not per_day_data:
        print("✗ No intraday data downloaded. Exiting without writing file.")
        return

    # Save price data directly without metadata
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(per_day_data, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Intraday close prices saved to {output_file}")
    print("  Structure:")
    print('    {')
    print('      "YYYY-MM-DD": [')
    print('          {"time": "YYYY-MM-DD HH:MM:SS", "close": ..., "open": ..., "high": ..., "low": ..., "volume": ..., "timestamp": ...},')
    print('          ...')
    print('      ],')
    print('      ...')
    print('    }')


if __name__ == "__main__":
    main()


