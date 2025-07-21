# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Streamlit web application that analyzes cryptocurrency candlestick patterns to identify "unfilled wicks" - trading patterns with a 99% historical success rate. The application is designed for investment/DCA strategies rather than day trading.

## Commands

### Starting the Application
```bash
streamlit run landing.py
# or use the Windows batch file:
candlestick_mtf.bat
```

### Initial Setup (if needed)
```bash
python setup_auth.py    # Create authentication config
python setup_pages.py   # Setup page structure
```

## Architecture

### Entry Points
- **landing.py**: Main entry point with authentication
- **pages/1_Main.py**: Primary analysis interface after login

### Core Modules
- **binance_utils.py**: Binance API integration with caching (1h for pairs, 5m for data)
- **data_processing.py**: Pattern recognition algorithms and scoring
- **chart_utils.py**: Interactive TradingView-style charts with LightweightCharts
- **db_utils.py**: SQLite user management and analytics
- **config.py**: Application constants and settings

### Authentication System
Uses streamlit-authenticator with:
- YAML-based credential storage (`.streamlit/config.yaml`) 
- Bcrypt password hashing
- 30-day cookie persistence
- User registration/login with SQLite tracking

### Data Flow
1. User selects symbols/timeframes/parameters in Main.py
2. binance_utils fetches historical data (cached)
3. data_processing identifies unfilled wick patterns
4. Results scored and aggregated across timeframes
5. chart_utils generates interactive visualizations
6. Search logged to database for analytics

## Configuration

### Required Files
- `.streamlit/secrets.toml`: Binance API credentials
```toml
[binance]
BINANCE_API_KEY = "your_key"
BINANCE_SECRET_KEY = "your_secret"
```
- `.streamlit/config.yaml`: Authentication config (auto-managed)
- `user_data.db`: SQLite database (auto-created)

### Key Parameters
- **Wick Ratio** (0.7-0.95): Minimum wick-to-total-size ratio
- **Body Threshold** (0.01-0.2): Maximum body size relative to total
- **Candle Size Multiplier** (0.1-3.0): Size filter
- **Timeframes**: 1m-1M standard + custom 2m-10m intervals

## Custom Timeframe Implementation

The app generates 2m-10m intervals by:
1. Fetching 1-minute data from Binance
2. Using pandas resample with proper OHLCV aggregation
3. Timezone adjustment (+2 hours to timestamps)

## Database Schema

```sql
-- Users table
CREATE TABLE users (
    username TEXT PRIMARY KEY,
    name TEXT,
    email TEXT UNIQUE,
    signup_date TEXT,
    last_login TEXT
);

-- Searches table  
CREATE TABLE searches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    timestamp TEXT,
    symbols TEXT,
    timeframes TEXT,
    FOREIGN KEY (username) REFERENCES users (username)
);
```

## Pattern Detection Algorithm

The core `identify_unfilled_wicks()` function:
1. Calculates wick ratios for each candle
2. Identifies significant wicks based on body/wick thresholds
3. Checks if wicks remain unfilled in subsequent candles
4. Scores patterns based on quality factors (body, size, volume, asymmetry)
5. Returns top patterns by score

## Dependencies

Key packages:
- streamlit>=1.40.0 (web framework)
- python-binance>=1.0.17 (API client) 
- streamlit-authenticator==0.4.1 (auth)
- pandas>=2.0.3, numpy>=1.24.3 (data processing)

## Development Notes

### Caching Strategy
- Binance client: Resource-level caching
- API data: TTL-based caching (5m for klines, 1h for pairs)
- Analysis results: Function-level with parameter hashing

### Chart Technology
- LightweightCharts library via custom HTML template
- JavaScript injection for data and functionality
- Fullscreen mode and screenshot capabilities

### Security
- Read-only Binance API permissions recommended
- No plaintext password storage
- Session state management for user persistence