"""
Download NIFTY spot prices using Dhan REST API
Date range is configured via START_DATE and END_DATE in .env file

Documentation: https://dhanhq.co/docs/v2/historical-data/
"""

import os
import json
import time
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables (override any existing env vars)
load_dotenv(override=True)

# Get Dhan API credentials from .env file
dhan_access_token = os.getenv('DHAN_ACCESS_TOKEN')
dhan_client_id = os.getenv('DHAN_CLIENT_ID')

# Get date range from .env file
start_date_str = os.getenv('START_DATE')
end_date_str = os.getenv('END_DATE')

if not dhan_access_token:
    raise ValueError("DHAN_ACCESS_TOKEN must be set in .env file")

if not start_date_str or not end_date_str:
    raise ValueError("START_DATE and END_DATE must be set in .env file (format: YYYY-MM-DD)")

# Strip any whitespace from token (common issue)
dhan_access_token = dhan_access_token.strip()
start_date_str = start_date_str.strip()
end_date_str = end_date_str.strip()

# Parse dates
try:
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
except ValueError as e:
    raise ValueError(f"Invalid date format in .env file. Use YYYY-MM-DD format. Error: {e}")

# Validate dates
if start_date > end_date:
    raise ValueError("START_DATE must be before or equal to END_DATE")

# Dhan API configuration
DHAN_API_BASE = "https://api.dhan.co"
DHAN_HISTORICAL_ENDPOINT = f"{DHAN_API_BASE}/v2/charts/historical"

# NIFTY 50 security ID
NIFTY_SECURITY_ID = "13"

def fetch_nifty_spot_prices_dhan(start_date, end_date):
    """Fetch NIFTY spot prices from Dhan REST API for the given date range"""
    print(f"\n{'='*80}")
    print("Downloading NIFTY spot prices using Dhan REST API...")
    print(f"Date range: {start_date.date()} to {end_date.date()}")
    print(f"{'='*80}\n")
    
    spot_prices = {}
    
    # Headers for API request
    headers = {
        'Content-Type': 'application/json',
        'access-token': dhan_access_token
    }
    
    # Add client-id if available (some APIs require it)
    if dhan_client_id:
        headers['client-id'] = dhan_client_id
    
    # Split into monthly chunks to avoid API limits
    current_start = start_date
    chunk_count = 0
    
    while current_start <= end_date:
        chunk_count += 1
        # Calculate end date for this chunk (end of month or end_date, whichever is earlier)
        if current_start.month == 12:
            chunk_end = min(datetime(current_start.year + 1, 1, 1) - timedelta(days=1), end_date)
        else:
            chunk_end = min(datetime(current_start.year, current_start.month + 1, 1) - timedelta(days=1), end_date)
        
        start_date_str = current_start.strftime("%Y-%m-%d")
        end_date_str = chunk_end.strftime("%Y-%m-%d")
        
        print(f"  Chunk {chunk_count}: Fetching data from {start_date_str} to {end_date_str}...")
        
        try:
            # Request payload according to Dhan API documentation
            # Based on docs: https://dhanhq.co/docs/v2/historical-data/
            # For NIFTY index: exchangeSegment = "IDX_I", instrument = "INDEX"
            # Note: toDate is non-inclusive per documentation, so we add 1 day
            end_date_inclusive = (chunk_end + timedelta(days=1)).strftime("%Y-%m-%d")
            
            payload = {
                "securityId": NIFTY_SECURITY_ID,
                "exchangeSegment": "IDX_I",
                "instrument": "INDEX",
                "expiryCode": 0,
                "oi": False,
                "fromDate": start_date_str,
                "toDate": end_date_inclusive  # Non-inclusive, so add 1 day
            }
            
            response = requests.post(
                DHAN_HISTORICAL_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Dhan API returns arrays: open, high, low, close, volume, timestamp
                if isinstance(data, dict) and 'open' in data and 'timestamp' in data:
                    opens = data.get('open', [])
                    timestamps = data.get('timestamp', [])
                    
                    if len(opens) == len(timestamps) and len(opens) > 0:
                        print(f"    API returned {len(opens)} records for this chunk")
                        
                        for i, timestamp in enumerate(timestamps):
                            # Convert epoch timestamp to date
                            try:
                                dt = datetime.fromtimestamp(timestamp)
                                date_str = dt.strftime('%Y-%m-%d')
                                open_price = opens[i]
                                
                                if date_str and open_price:
                                    spot_prices[date_str] = float(open_price)
                            except (ValueError, TypeError, IndexError) as e:
                                continue
                        
                        chunk_dates = [d for d in spot_prices.keys() if start_date_str <= d <= end_date_str]
                        print(f"    ✓ Extracted {len(chunk_dates)} unique dates from this chunk")
                    else:
                        print(f"    ⚠ Mismatch in data arrays or no data")
                else:
                    # Check for error response
                    if isinstance(data, dict):
                        if 'error' in data or 'errorMessage' in data or 'message' in data:
                            error_msg = data.get('error') or data.get('errorMessage') or data.get('message')
                            print(f"    ✗ API error: {error_msg}")
                        else:
                            print(f"    ⚠ Unexpected response format")
                            if chunk_count == 1:  # Only print for first chunk
                                print(f"    Response keys: {list(data.keys())[:10] if isinstance(data, dict) else 'Not a dict'}")
                    else:
                        print(f"    ⚠ Unexpected response type: {type(data)}")
            elif response.status_code == 401:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get('errorMessage', 'Authentication failed')
                print(f"    ✗ Authentication error: {error_msg}")
                if chunk_count == 1:
                    print(f"    ⚠ Please check your DHAN_ACCESS_TOKEN in .env file")
                    print(f"    ⚠ Access tokens may expire and need to be regenerated")
                break  # Don't continue if authentication fails
            else:
                print(f"    ✗ HTTP error: Status {response.status_code}")
                print(f"    Response: {response.text[:200]}")
            
            # Rate limiting
            time.sleep(0.5)
            
        except Exception as e:
            print(f"    ✗ Error fetching chunk: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # Move to next month
        if current_start.month == 12:
            current_start = datetime(current_start.year + 1, 1, 1)
        else:
            current_start = datetime(current_start.year, current_start.month + 1, 1)
    
    return spot_prices

def main():
    # Dates are already parsed from .env file at module level
    print(f"Downloading NIFTY spot prices from {start_date.date()} to {end_date.date()}")
    
    # Fetch spot prices
    spot_prices = fetch_nifty_spot_prices_dhan(start_date, end_date)
    
    if not spot_prices:
        print("✗ Failed to download spot prices. Exiting.")
        return
    
    print(f"\n✓ Successfully downloaded {len(spot_prices)} spot price records")
    
    # Save to file in the same format as existing nifty_spot_prices.json
    output_file = 'nifty_spot_prices.json'
    output_data = {
        'date_range': {
            'start': start_date.strftime("%Y-%m-%d"),
            'end': end_date.strftime("%Y-%m-%d")
        },
        'spot_prices': spot_prices
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Spot prices saved to {output_file}")
    if spot_prices:
        print(f"\nDate range: {min(spot_prices.keys())} to {max(spot_prices.keys())}")
        print(f"Total trading days: {len(spot_prices)}")

if __name__ == "__main__":
    main()

