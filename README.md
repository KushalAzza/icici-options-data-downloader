# NIFTY Options Data Downloader

A Python toolkit for downloading NIFTY options and spot price data from ICICI Direct (Breeze Connect) and Dhan APIs.

## Features

- **Spot Price Download**: Download NIFTY spot prices using Dhan API
- **Intraday Data**: Download 1-minute intraday OHLC data for NIFTY
- **Options Data**: Download NIFTY options data (CALL and PUT) for multiple strikes
- **Monthly Expiry**: Automatically find and download data for monthly expiry dates
- **Manual Expiry**: Download data for a specific expiry date

## Prerequisites

- Python 3.7+
- Virtual environment (recommended)
- API credentials from ICICI Direct (Breeze Connect) and/or Dhan

## Installation

1. Clone the repository:
```bash
git clone https://github.com/KushalAzza/options-downloader.git
cd options-downloader
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root (see `env.example` for template):
```bash
cp env.example .env
```

5. Configure your API credentials in `.env` file (see Configuration section below)

## Configuration

Create a `.env` file in the project root with your API credentials. See `env.example` for a template.

### Required Environment Variables

#### For Dhan API (Spot Prices & Intraday)
- `DHAN_ACCESS_TOKEN`: Your Dhan API access token
- `DHAN_CLIENT_ID`: (Optional) Your Dhan client ID

#### For ICICI Direct / Breeze Connect (Options Data)
- `ICICI_API_KEY`: Your ICICI Direct API key
- `ICICI_SECRET_KEY`: Your ICICI Direct secret key
- `ICICI_SESSION_TOKEN`: Your ICICI Direct session token

#### For Monthly Options Download
- `START_DATE`: Start date in YYYY-MM-DD format (e.g., `2025-01-01`)
- `END_DATE`: End date in YYYY-MM-DD format (e.g., `2025-12-31`)
- `EXPIRY_DAY`: Expiry weekday (0=Monday, 1=Tuesday, 2=Wednesday, 3=Thursday, 4=Friday, 5=Saturday, 6=Sunday)

#### For Manual Options Download
- `M_START_DATE`: Start date in YYYY-MM-DD format
- `M_END_DATE`: End date in YYYY-MM-DD format
- `M_EXPIRY_DATE`: Specific expiry date in YYYY-MM-DD format

## Usage

### 1. Download NIFTY Spot Prices

First, download the spot prices which are required for options data download:

```bash
python download_nifty_spot_dhan.py
```

**Output File**: `nifty_spot_prices.json`

**Output Structure**:
```json
{
  "date_range": {
    "start": "2023-01-01",
    "end": "2025-12-31"
  },
  "spot_prices": {
    "2023-01-02": 18123.45,
    "2023-01-03": 18234.56,
    ...
  }
}
```

### 2. Download NIFTY Intraday Data

Download 1-minute intraday OHLC data:

```bash
python download_nifty_intraday_dhan.py
```

**Output File**: `nifty_intraday_price.json`

**Output Structure**:
```json
{
  "2023-01-02": [
    {
      "time": "2023-01-02 09:15:00",
      "close": 18123.4,
      "open": 18120.0,
      "high": 18125.0,
      "low": 18118.0,
      "volume": 1234567,
      "timestamp": 1672644300
    },
    {
      "time": "2023-01-02 09:16:00",
      "close": 18124.2,
      "open": 18123.4,
      "high": 18126.0,
      "low": 18123.0,
      "volume": 1234890,
      "timestamp": 1672644360
    },
    ...
  ],
  "2023-01-03": [
    ...
  ]
}
```

### 3. Download NIFTY Options Data (Monthly Expiry)

Downloads options data for the nearest monthly expiry date for each trading day:

```bash
python download_nifty_options_monthly.py
```

**Prerequisites**: Requires `nifty_spot_prices.json` from step 1.

**Output Files**: 
- `nifty_options_YYYY-MM-DD.json` (one file per trading day)
- `nifty_options_YYYY-MM-DD_next_expiry.json` (on expiry days, contains next expiry data)

**Output Structure**:
```json
{
  "date": "2025-01-02",
  "spot_price": 18123.45,
  "expiry_date": "02-JAN-2025",
  "data": {
    "call": {
      "18000": [
        {
          "datetime": "2025-01-02T09:15:00.000Z",
          "open": 123.45,
          "high": 125.67,
          "low": 122.34,
          "close": 124.56,
          "volume": 1234567
        },
        ...
      ],
      "18050": [...],
      ...
    },
    "put": {
      "18000": [...],
      "18050": [...],
      ...
    }
  }
}
```

**Strike Range**: For each day, downloads 20 strikes above and 20 below the spot price (strikes are in multiples of 50).

### 4. Download NIFTY Options Data (Manual Expiry)

Download options data for a specific expiry date:

```bash
python download_nifty_options_manual.py
```

**Prerequisites**: Requires `nifty_spot_prices.json` from step 1.

**Output Files**: `nifty_options_YYYY-MM-DD.json` (one file per trading day)

**Output Structure**: Same as monthly expiry output above.

## Output File Structure Details

### Spot Prices File (`nifty_spot_prices.json`)
- **Purpose**: Contains daily NIFTY spot prices
- **Format**: JSON object with date range metadata and spot prices dictionary
- **Date Format**: YYYY-MM-DD
- **Price Format**: Float

### Intraday Data File (`nifty_intraday_price.json`)
- **Purpose**: Contains 1-minute OHLC candle data
- **Format**: JSON object where keys are dates and values are arrays of candle objects
- **Time Format**: YYYY-MM-DD HH:MM:SS
- **Interval**: 1 minute
- **Fields**: time, open, high, low, close, volume, timestamp

### Options Data Files (`nifty_options_YYYY-MM-DD.json`)
- **Purpose**: Contains options data for a specific trading day
- **Format**: JSON object with metadata and nested data structure
- **Strike Prices**: Automatically calculated based on spot price (±20 strikes in multiples of 50)
- **Option Types**: Both CALL and PUT options
- **Data Granularity**: 1-minute intervals (09:15 AM to 03:30 PM IST)
- **Expiry Date Format**: DD-MMM-YYYY (e.g., "02-JAN-2025")

### Options Data Structure Breakdown

Each options file contains:
- `date`: Trading date (YYYY-MM-DD)
- `spot_price`: NIFTY spot price for that day
- `expiry_date`: Expiry date of the options contract (DD-MMM-YYYY format)
- `data`: Nested structure containing:
  - `call`: Dictionary of CALL options by strike price
  - `put`: Dictionary of PUT options by strike price
  - Each strike contains an array of 1-minute OHLC records

## Workflow Example

1. **Download spot prices** (required first):
   ```bash
   python download_nifty_spot_dhan.py
   ```

2. **Download options data** (uses spot prices):
   ```bash
   python download_nifty_options_monthly.py
   ```

3. **Optional: Download intraday data**:
   ```bash
   python download_nifty_intraday_dhan.py
   ```

## Rate Limiting

The scripts include rate limiting to respect API limits:
- **ICICI Direct**: ~100 requests per minute
- **Dhan**: ~10 requests per second

The scripts automatically pause when approaching these limits.

## Notes

- All dates are in IST (Indian Standard Time)
- Trading hours: 09:15 AM to 03:30 PM IST
- Holidays are automatically detected (days with no spot price data)
- Strike prices are calculated in multiples of 50 (NIFTY standard)
- Expiry dates are automatically detected based on the configured expiry day

## Troubleshooting

### Authentication Errors
- Verify your API tokens in `.env` file
- Check if tokens have expired (especially ICICI session tokens)
- Ensure no extra whitespace in token values

### Missing Spot Prices
- Run `download_nifty_spot_dhan.py` first before downloading options data
- Ensure the date range in spot prices file covers your options download date range

### No Data for Certain Dates
- Check if the date is a trading holiday
- Verify the expiry date exists for that period
- Ensure your API credentials have access to historical data

## License

This project is provided as-is for educational and research purposes.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

