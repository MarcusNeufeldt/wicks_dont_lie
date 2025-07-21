# Unfilled Wick Analysis Tool

A sophisticated analysis tool that identifies unfilled candlestick wicks in cryptocurrency markets. Based on the principle that price tends to return to and "fill" significant unfilled wicks, especially those with long upside wicks and small bodies.

## Trading Strategy

### Core Concept
- The tool identifies candlesticks with long wicks (especially upside) and small bodies
- These patterns often indicate areas where price is likely to return in the future
- 99% of significant unfilled wicks eventually get filled by price

### Recommended Approach
- **Investment Strategy**: This is primarily an investment tool, not for day trading
- **DCA (Dollar Cost Average)**: Best used for systematic buying in the direction of upside wicks
- **Time Horizon**: Be prepared for longer holding periods as some wicks may take time to fill
- **Success Rate**: Historical data shows approximately 99% of significant wicks eventually get filled

### Best Practices
1. Focus on upside wicks (wicks pointing up)
2. Look for small bodies with long wicks
3. Use multiple timeframes for confirmation
4. Apply DCA strategy rather than all-in entries
5. Maintain patience - some wicks may take weeks or months to fill

## Features
- Real-time data from Binance Futures API
- Custom timeframe analysis (2m-10m)
- Standard timeframe analysis (1m-1M)
- Unfilled wick pattern detection
- Interactive charts and visualizations
- Configurable wick-to-body ratio analysis

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure Binance API credentials:
   - Create `.streamlit/secrets.toml`
   - Add your Binance API credentials:
```toml
[binance]
BINANCE_API_KEY = "your_api_key"
BINANCE_SECRET_KEY = "your_secret_key"
```

## Usage

1. Start the application:
```bash
streamlit run main.py
```

2. Analysis Parameters:
   - Select cryptocurrency pairs of interest
   - Choose appropriate timeframes (longer timeframes often show more significant wicks)
   - Adjust wick ratio to identify meaningful patterns
   - Set body threshold to find candles with small bodies

## Risk Warning

While unfilled wick analysis has shown high historical reliability (≈99% fill rate), please note:
- This tool should be part of a broader investment strategy
- Never invest more than you can afford to lose
- Some positions may require longer holding periods
- Always use proper position sizing and risk management
- Past performance doesn't guarantee future results
