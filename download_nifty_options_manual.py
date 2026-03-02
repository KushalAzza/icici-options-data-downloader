"""
NIFTY Options Data Downloader - Manual Expiry Date

This script allows you to manually specify:
- Start date
- End date  
- Expiry date

And downloads NIFTY options data for the specified expiry date across the date range.
Data is saved in the same format as download_nifty_options_monthly.py
"""

import os
import json
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
from breeze_connect import BreezeConnect
from collections import defaultdict

# Load environment variables
load_dotenv()

# Data/output configuration
DATA_DIR = "data"
OPTIONS_DIR = os.path.join(DATA_DIR, "options")
os.makedirs(OPTIONS_DIR, exist_ok=True)

# Get credentials from environment variables
api_key = os.getenv('ICICI_API_KEY')
api_secret = os.getenv('ICICI_SECRET_KEY')
session_token = os.getenv('ICICI_SESSION_TOKEN')

if not api_key or not api_secret or not session_token:
    raise ValueError("ICICI_API_KEY, ICICI_SECRET_KEY, and ICICI_SESSION_TOKEN must be set in .env file")

# Initialize SDK
print("Initializing BreezeConnect...")
breeze = BreezeConnect(api_key=api_key)

# Generate Session
print("Generating session...")
breeze.generate_session(api_secret=api_secret, session_token=session_token)

def load_spot_prices_from_file(file_path=os.path.join(DATA_DIR, 'nifty_spot_prices.json')):
    """Load NIFTY spot prices from JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        spot_prices = data.get('spot_prices', {})
        date_range = data.get('date_range', {})
        
        if not spot_prices:
            raise ValueError(f"No spot prices found in {file_path}")
        
        print(f"✓ Loaded {len(spot_prices)} spot price records from {file_path}")
        if date_range:
            print(f"  Date range in file: {date_range.get('start')} to {date_range.get('end')}")
        
        return spot_prices
    except FileNotFoundError:
        raise FileNotFoundError(f"Spot prices file not found: {file_path}. Please run download_nifty_spot_dhan.py first.")
    except json.JSONDecodeError as e:
        raise ValueError(f"Error parsing {file_path}: {e}")

def calculate_strikes(spot_price, num_strikes=20):
    """Calculate strike prices (20 above and 20 below spot)"""
    # NIFTY strikes are typically in multiples of 50
    strike_interval = 50
    
    # Round spot to nearest strike
    base_strike = round(spot_price / strike_interval) * strike_interval
    
    strikes = []
    # 20 strikes below
    for i in range(num_strikes, 0, -1):
        strikes.append(int(base_strike - (i * strike_interval)))
    # Spot strike (or nearest)
    strikes.append(int(base_strike))
    # 20 strikes above
    for i in range(1, num_strikes + 1):
        strikes.append(int(base_strike + (i * strike_interval)))
    
    return strikes

def download_options_data(breeze, date_str, expiry_date_str, strike_price, right_type):
    """Download 1-minute historical data for a specific option"""
    try:
        from_time = f"{date_str}T09:15:00.000Z"
        to_time = f"{date_str}T15:30:00.000Z"
        
        data = breeze.get_historical_data_v2(
            stock_code="NIFTY",
            exchange_code="NFO",
            from_date=from_time,
            to_date=to_time,
            interval="1minute",
            product_type="options",
            expiry_date=expiry_date_str,
            right=right_type,
            strike_price=str(strike_price)
        )
        
        # Rate limiting - be respectful
        time.sleep(0.1)  # Small delay between requests
        
        if isinstance(data, dict) and data.get('Status') == 200:
            success = data.get('Success', [])
            if success and len(success) > 0:
                return success
        return []
    except Exception as e:
        print(f"    Error downloading {right_type} {strike_price}: {e}")
        return []

def save_daily_data(date_str, day_data, spot_price, expiry_date_str):
    """Save data for a single day to a separate file"""
    output_file = os.path.join(OPTIONS_DIR, f"nifty_options_{date_str}.json")
    
    output_data = {
        'date': date_str,
        'spot_price': spot_price,
        'expiry_date': expiry_date_str,
        'data': day_data
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    return output_file

def main():
    print("=" * 80)
    print("NIFTY Options Data Downloader - Manual Expiry Date")
    print("=" * 80)
    print()
    
    # Get parameters from environment variables
    start_date_str = os.getenv('M_START_DATE')
    end_date_str = os.getenv('M_END_DATE')
    expiry_date_str = os.getenv('M_EXPIRY_DATE')
    
    if not start_date_str or not end_date_str or not expiry_date_str:
        raise ValueError("M_START_DATE, M_END_DATE, and M_EXPIRY_DATE must be set in .env file (format: YYYY-MM-DD)")
    
    # Strip whitespace
    start_date_str = start_date_str.strip()
    end_date_str = end_date_str.strip()
    expiry_date_str = expiry_date_str.strip()
    
    # Parse dates
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d')
    except ValueError as e:
        raise ValueError(f"Invalid date format in .env file. Use YYYY-MM-DD format. Error: {e}")
    
    # Validate dates
    if start_date > end_date:
        raise ValueError("Start date must be before or equal to end date")
    
    if expiry_date < start_date:
        print(f"⚠ Warning: Expiry date ({expiry_date.date()}) is before start date ({start_date.date()})")
    
    expiry_date_iso = expiry_date.strftime("%Y-%m-%dT00:00:00.000Z")
    expiry_date_formatted = expiry_date.strftime("%d-%b-%Y").upper()
    
    print()
    print("=" * 80)
    print(f"Configuration:")
    print(f"  Start date: {start_date.date()}")
    print(f"  End date: {end_date.date()}")
    print(f"  Expiry date: {expiry_date_formatted} ({expiry_date.date()})")
    print("=" * 80)
    print()
    
    # Load spot prices
    print(f"{'='*80}")
    print("Step 1: Loading NIFTY spot prices from file...")
    print(f"{'='*80}\n")
    
    # Load spot prices from data/nifty_spot_prices.json (default path)
    spot_prices = load_spot_prices_from_file()
    
    if not spot_prices:
        print("✗ Failed to load spot prices. Exiting.")
        return
    
    # Verify date range coverage
    sorted_dates = sorted(spot_prices.keys())
    file_start = sorted_dates[0]
    file_end = sorted_dates[-1]
    
    if file_start > start_date_str:
        print(f"⚠ Warning: Spot prices file starts from {file_start}, but requested start date is {start_date_str}")
    if file_end < end_date_str:
        print(f"⚠ Warning: Spot prices file ends at {file_end}, but requested end date is {end_date_str}")
    
    print(f"\n{'='*80}")
    print("Step 2: Downloading options data for each day...")
    print(f"{'='*80}\n")
    
    holidays = []
    total_requests = 0
    total_records = 0
    day_count = 0
    total_days = (end_date - start_date).days + 1
    
    current_date = start_date
    while current_date <= end_date:
        day_count += 1
        date_str = current_date.strftime("%Y-%m-%d")
        weekday = current_date.strftime("%A")
        
        print(f"\n[{day_count}/{total_days}] [{date_str}] {weekday} - Processing...")
        
        # Get spot price from pre-downloaded data
        spot_price = spot_prices.get(date_str)
        
        if spot_price is None or spot_price == 0:
            print(f"  ⚠ No spot price available for {date_str} - marking as holiday")
            holidays.append(date_str)
            current_date += timedelta(days=1)
            continue
        
        print(f"  NIFTY Spot Price: {spot_price}")
        print(f"  Using Expiry Date: {expiry_date_formatted} ({expiry_date.date()})")
        
        # Calculate strikes
        strikes = calculate_strikes(spot_price, num_strikes=20)
        
        print(f"  Downloading {len(strikes)} strikes: {strikes[0]} to {strikes[-1]}")
        
        # Download data for each strike and right type
        day_data = defaultdict(lambda: defaultdict(list))
        day_data_count = 0
        
        for strike in strikes:
            for right_type in ['call', 'put']:
                print(f"    Downloading {right_type.upper()} {strike}...", end=" ")
                data = download_options_data(breeze, date_str, expiry_date_iso, strike, right_type)
                total_requests += 1
                
                if data:
                    day_data[right_type][str(strike)].extend(data)
                    day_data_count += len(data)
                    print(f"✓ {len(data)} records")
                else:
                    print("✗ No data")
                
                # Rate limiting - API allows 100 calls per minute
                # Pause every 50 requests to stay under 100/minute limit
                if total_requests % 50 == 0:
                    print(f"  Rate limit check: {total_requests} requests made, pausing 2 seconds...")
                    time.sleep(2)
        
        if day_data_count == 0:
            print(f"  ⚠ No data for this day - marking as holiday")
            holidays.append(date_str)
        else:
            print(f"  ✓ Total records for {date_str}: {day_data_count}")
            total_records += day_data_count
            
            # Save data to file
            output_file = save_daily_data(date_str, dict(day_data), spot_price, expiry_date_formatted)
            print(f"  ✓ Data saved to {output_file}")
        
        current_date += timedelta(days=1)
    
    # Save summary
    print("\n" + "=" * 80)
    print("Download Summary")
    print("=" * 80)
    print(f"Total days processed: {day_count - len(holidays)}")
    print(f"Holidays detected: {len(holidays)}")
    if holidays:
        print(f"  Holiday dates: {', '.join(holidays)}")
    print(f"Total API requests: {total_requests}")
    print(f"Total records downloaded: {total_records}")
    print(f"\nFiles created:")
    print(f"  - nifty_options_YYYY-MM-DD.json (one file per trading day)")
    print(f"\nNote: All files use expiry date: {expiry_date_formatted}")

if __name__ == "__main__":
    main()

