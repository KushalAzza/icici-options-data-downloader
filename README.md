# NIFTY Options Data Downloader

Python scripts that download NIFTY index and options data from [Dhan](https://dhan.co) and [ICICI Direct Breeze](https://www.icicidirect.com/).

Generated JSON is written under `data/` and is not in git.

```
icici-options-data-downloader/
├── LICENSE
├── README.md
├── env.example
├── requirements.txt
├── download_nifty_spot_dhan.py       # Daily NIFTY (or other index) via Dhan
├── download_nifty_intraday_dhan.py   # 1-minute OHLC via Dhan
├── download_nifty_options_monthly.py # Options via Breeze, nearest expiry
└── download_nifty_options_manual.py  # Options via Breeze, one expiry date
```

## Prerequisites

- Python 3.7 or later
- Dhan API credentials for spot and intraday
- ICICI Direct Breeze credentials for options

## Setup

```bash
git clone https://github.com/KushalAzza/icici-options-data-downloader.git
cd icici-options-data-downloader
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp env.example .env
```

Fill `.env`. Never commit that file.

| Variable | Used by | Notes |
| --- | --- | --- |
| `DHAN_ACCESS_TOKEN` | Dhan scripts | Dhan API token |
| `DHAN_CLIENT_ID` | Dhan scripts | Optional; some Dhan calls need it |
| `USE_SECURITY_ID` | Dhan scripts | Dhan instrument id (`13` = NIFTY, `21` = India VIX) |
| `ICICI_API_KEY` | options scripts | Breeze API key |
| `ICICI_SECRET_KEY` | options scripts | Breeze secret |
| `ICICI_SESSION_TOKEN` | options scripts | Breeze session token (expires; refresh as needed) |
| `START_DATE` | spot, monthly options, intraday | `YYYY-MM-DD` |
| `END_DATE` | spot, monthly options, intraday | `YYYY-MM-DD` |
| `EXPIRY_DAY` | monthly options | Weekday: `0` Monday … `6` Sunday. NIFTY is often Thursday (`3`) |
| `M_START_DATE` | manual options | `YYYY-MM-DD` |
| `M_END_DATE` | manual options | `YYYY-MM-DD` |
| `M_EXPIRY_DATE` | manual options | One expiry, `YYYY-MM-DD` |

## Usage

Spot prices first, then options (options scripts read `data/nifty_spot_prices.json`):

```bash
python download_nifty_spot_dhan.py
python download_nifty_options_monthly.py
python download_nifty_options_manual.py
python download_nifty_intraday_dhan.py
```

| Script | Output |
| --- | --- |
| `download_nifty_spot_dhan.py` | `data/nifty_spot_prices.json` |
| `download_nifty_intraday_dhan.py` | `data/nifty_intraday_price.json` |
| `download_nifty_options_monthly.py` | `data/options/nifty_options_YYYY-MM-DD.json` and, on expiry days, `…_next_expiry.json` |
| `download_nifty_options_manual.py` | `data/options/nifty_options_YYYY-MM-DD.json` |

Monthly options: for each trading day, 20 strikes above and 20 below the spot (multiples of 50), CALL and PUT, 1-minute bars from 09:15 to 15:30 IST. Days with no spot price are treated as holidays.

The scripts pause between requests (Dhan about 10/sec, Breeze about 100/min).

## Troubleshooting

- **Auth errors:** check tokens in `.env`. Breeze session tokens expire.
- **Missing spot file:** run `download_nifty_spot_dhan.py` before the options scripts.
- **Empty days:** holiday, or no contract for that expiry.

## License

MIT. See [LICENSE](LICENSE).
