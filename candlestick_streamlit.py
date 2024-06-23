import streamlit as st
import pandas as pd
import numpy as np
from binance.client import Client
import time
from datetime import datetime, timezone
import dateparser
import json
import streamlit.components.v1 as components
import os

# Set up your Binance API credentials
try:
    api_key = st.secrets["binance"]["api_key"]
    api_secret = st.secrets["binance"]["api_secret"]
except KeyError as e:
    st.error(f"API credentials not found: {e}")
    st.stop()

try:
    client = Client(api_key, api_secret)
except Exception as e:
    st.error(f"Error initializing Binance client: {e}")
    st.stop()


# Function to fetch Binance futures pairs
def get_binance_futures_pairs():
    try:
        exchange_info = client.futures_exchange_info()
        symbols = [symbol['symbol'] for symbol in exchange_info['symbols']]
        return symbols
    except Exception as e:
        st.error(f"Error fetching Binance futures pairs: {e}")
        return []


# Function to parse time strings
def parse_time_string(time_str):
    try:
        if time_str == 'now UTC':
            return datetime.now(timezone.utc)
        parsed_time = dateparser.parse(time_str, settings={'TIMEZONE': 'UTC', 'RETURN_AS_TIMEZONE_AWARE': True})
        if parsed_time is None:
            raise ValueError(f"Unable to parse time string: {time_str}")
        return parsed_time
    except ValueError as e:
        st.error(e)
        st.stop()


def calculate_drawdown(df, candle_idx, bars_to_fill):
    try:
        candle = df.iloc[candle_idx]
        high_price = candle['high']
        low_price = candle['low']

        max_drawdown_high_pct = 0
        max_drawdown_low_pct = 0
        max_drawdown_high_dollar = 0
        max_drawdown_low_dollar = 0

        for i in range(1, bars_to_fill + 1):
            next_candle = df.iloc[candle_idx + i]
            drawdown_high_pct = (high_price - next_candle['low']) / high_price * 100
            drawdown_low_pct = (next_candle['high'] - low_price) / low_price * 100
            drawdown_high_dollar = high_price - next_candle['low']
            drawdown_low_dollar = next_candle['high'] - low_price

            if drawdown_high_pct > max_drawdown_high_pct:
                max_drawdown_high_pct = drawdown_high_pct
                max_drawdown_high_dollar = drawdown_high_dollar
            if drawdown_low_pct > max_drawdown_low_pct:
                max_drawdown_low_pct = drawdown_low_pct
                max_drawdown_low_dollar = drawdown_low_dollar

        if max_drawdown_high_pct > max_drawdown_low_pct:
            return max_drawdown_high_pct, max_drawdown_high_dollar
        else:
            return max_drawdown_low_pct, max_drawdown_low_dollar
    except IndexError as e:
        st.error(f"Index error in calculate_drawdown: {e}")
        return np.nan, np.nan


def calculate_potential_drawdown(row, df):
    try:
        current_price = df.iloc[-1]['close']
        upper_wick_length = row['high'] - max(row['open'], row['close'])
        lower_wick_length = min(row['open'], row['close']) - row['low']

        if upper_wick_length > lower_wick_length:
            drawdown_pct = (row['high'] - current_price) / row['high'] * 100
            drawdown_dollar = row['high'] - current_price
        else:
            drawdown_pct = (current_price - row['low']) / row['low'] * 100
            drawdown_dollar = current_price - row['low']

        return drawdown_pct, drawdown_dollar
    except Exception as e:
        st.error(f"Error in calculate_potential_drawdown: {e}")
        return np.nan, np.nan


# Function to fetch historical candlestick data
@st.cache_data(show_spinner=True)
def get_historical_klines(symbol, interval, start_str, end_str=None):
    try:
        limit = 1500
        df = pd.DataFrame()
        start_time = parse_time_string(start_str)
        end_time = parse_time_string(end_str) if end_str else None

        while True:
            start_ms = int(start_time.timestamp() * 1000)
            klines = client.futures_klines(symbol=symbol, interval=interval, startTime=start_ms, limit=limit)
            if len(klines) == 0:
                break

            temp_df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time',
                                                    'quote_asset_volume', 'number_of_trades',
                                                    'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume',
                                                    'ignore'])
            temp_df['timestamp'] = pd.to_datetime(temp_df['timestamp'], unit='ms', utc=True)
            temp_df[['open', 'high', 'low', 'close', 'volume']] = temp_df[
                ['open', 'high', 'low', 'close', 'volume']].astype(float)
            df = pd.concat([df, temp_df], ignore_index=True)

            last_timestamp = temp_df.iloc[-1]['timestamp']
            interval_timedelta = pd.Timedelta(
                interval.replace('m', 'min').replace('h', 'H').replace('d', 'D').replace('w', 'W').replace('M', 'M'))
            start_time = last_timestamp + interval_timedelta

            if len(klines) < limit or (end_time and start_time >= end_time):
                break

            time.sleep(1)

        return df
    except Exception as e:
        st.error(f"Error fetching historical data: {e}")
        return pd.DataFrame()


# Function to identify candlesticks with tiny body and long wicks and a minimum candle size
def has_tiny_body_long_wick_with_min_size(candle, body_threshold=0.1, wick_ratio=0.8, min_size=100):
    try:
        open_price = float(candle['open'])
        close_price = float(candle['close'])
        high_price = float(candle['high'])
        low_price = float(candle['low'])

        body_size = abs(open_price - close_price)
        total_height = high_price - low_price
        upper_wick = high_price - max(open_price, close_price)
        lower_wick = min(open_price, close_price) - low_price
        wick_size = upper_wick + lower_wick

        if total_height < min_size:
            return False
        return body_size <= total_height * body_threshold and wick_size >= total_height * wick_ratio
    except Exception as e:
        st.error(f"Error in has_tiny_body_long_wick_with_min_size: {e}")
        return False


# Function to find the number of bars taken to fill the wick
def bars_to_fill_wick(df, candle_idx):
    try:
        candle = df.iloc[candle_idx]
        upper_wick_price = candle['high']
        lower_wick_price = candle['low']

        upper_wick_filled = False
        lower_wick_filled = False

        for idx in range(candle_idx + 1, len(df)):
            next_candle = df.iloc[idx]
            if next_candle['high'] >= upper_wick_price:
                upper_wick_filled = True
            if next_candle['low'] <= lower_wick_price:
                lower_wick_filled = True

            if upper_wick_filled and lower_wick_filled:
                return idx - candle_idx
        return None
    except IndexError as e:
        st.error(f"Index error in bars_to_fill_wick: {e}")
        return None


# Function to determine if a wick is filled
def is_wick_filled(candle, df, wick_type):
    try:
        for idx in range(candle.name + 1, len(df)):
            next_candle = df.iloc[idx]
            if wick_type == 'upper' and next_candle['high'] >= candle['high']:
                return True
            if wick_type == 'lower' and next_candle['low'] <= candle['low']:
                return True
        return False
    except IndexError as e:
        st.error(f"Index error in is_wick_filled: {e}")
        return False


# Function to calculate ATR
def calculate_atr(df, period=14):
    try:
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        return true_range.rolling(period).mean()
    except Exception as e:
        st.error(f"Error in calculate_atr: {e}")
        return pd.Series()


# Function to assess wick risk
def assess_wick_risk(row, atr, price_volatility_threshold=2, volume_threshold=1.5):
    try:
        wick_size = max(row['high'] - max(row['open'], row['close']), min(row['open'], row['close']) - row['low'])
        body_size = abs(row['open'] - row['close'])

        # Compare wick size to ATR
        wick_atr_ratio = wick_size / atr[row.name]

        # Check if volume is significantly higher than average
        volume_ratio = row['volume'] / df['volume'].rolling(20).mean()[row.name]

        # Assess risk based on multiple factors
        risk_score = 0
        if wick_atr_ratio > price_volatility_threshold:
            risk_score += 1
        if volume_ratio > volume_threshold:
            risk_score += 1
        if body_size < 0.1 * wick_size:  # Extremely small body
            risk_score += 1

        return risk_score
    except Exception as e:
        st.error(f"Error in assess_wick_risk: {e}")
        return np.nan


# HTML content for the TradingView chart
html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TradingView Chart</title>
    <script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
    <style>
        #chart-container {
            width: 100%;
            height: 500px;
            position: relative;
        }
        #chart {
            width: 100%;
            height: 100%;
        }
        #fullscreenButton, #screenshotButton {
            position: absolute;
            top: 10px;
            z-index: 10;
            padding: 5px 10px;
            background-color: white;
            border: 1px solid #cccccc;
            cursor: pointer;
        }
        #fullscreenButton {
            right: 10px;
        }
        #screenshotButton {
            right: 140px;
        }
        #notification {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 10px 20px;
            background-color: #4CAF50;
            color: white;
            border-radius: 5px;
            display: none;
            z-index: 1000;
        }
        #loadingIndicator {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            display: none;
            background-color: rgba(255, 255, 255, 0.8);
            padding: 10px;
            border-radius: 5px;
            z-index: 1000;
        }
    </style>
</head>
<body>
    <div id="chart-container">
        <div id="chart"></div>
        <button id="fullscreenButton">Open Fullscreen</button>
        <button id="screenshotButton">Take Screenshot</button>
        <div id="loadingIndicator">Processing screenshot...</div>
    </div>
    <div id="notification"></div>
    <script>
        function createChart(data, wickLines) {
            const chartElement = document.getElementById('chart');
            const chartContainer = document.getElementById('chart-container');
            const chart = LightweightCharts.createChart(chartElement, {
                width: chartElement.offsetWidth,
                height: chartElement.offsetHeight,
                layout: {
                    backgroundColor: '#ffffff',
                    textColor: '#000000',
                },
                grid: {
                    vertLines: {
                        color: '#e0e0e0',
                    },
                    horzLines: {
                        color: '#e0e0e0',
                    },
                },
                priceScale: {
                    borderColor: '#cccccc',
                },
                timeScale: {
                    borderColor: '#cccccc',
                },
                localization: {
                    priceFormatter: price => price.toFixed(5),
                    timeFormatter: timestamp => {
                        const date = new Date(timestamp * 1000);
                        return date.toISOString().slice(0, 19).replace('T', ' ');
                    }
                },
            });

            const candleSeries = chart.addCandlestickSeries();
            candleSeries.setData(data);

            wickLines.forEach(line => {
                if (line.high_unfilled) {
                    const series = chart.addLineSeries({
                        color: 'rgba(255, 0, 0, 0.5)',
                        lineWidth: 3,
                        lineStyle: 2, // Dashed line
                    });
                    series.setData([
                        { time: line.time, value: line.high },
                        { time: line.endTime, value: line.high }
                    ]);
                }
                if (line.low_unfilled) {
                    const series = chart.addLineSeries({
                        color: 'rgba(0, 0, 255, 0.5)',
                        lineWidth: 3,
                        lineStyle: 2, // Dashed line
                    });
                    series.setData([
                        { time: line.time, value: line.low },
                        { time: line.endTime, value: line.low }
                    ]);
                }
            });

            const fullscreenButton = document.getElementById('fullscreenButton');
            const screenshotButton = document.getElementById('screenshotButton');

            fullscreenButton.addEventListener('click', () => {
                if (!document.fullscreenElement) {
                    if (chartContainer.requestFullscreen) {
                        chartContainer.requestFullscreen();
                    } else if (chartContainer.mozRequestFullScreen) { // Firefox
                        chartContainer.mozRequestFullScreen();
                    } else if (chartContainer.webkitRequestFullscreen) { // Chrome, Safari, and Opera
                        chartContainer.webkitRequestFullscreen();
                    } else if (chartContainer.msRequestFullscreen) { // IE/Edge
                        chartContainer.msRequestFullscreen();
                    }
                    fullscreenButton.innerText = 'Exit Fullscreen';
                } else {
                    if (document.exitFullscreen) {
                        document.exitFullscreen();
                    } else if (document.mozCancelFullScreen) { // Firefox
                        document.mozCancelFullScreen();
                    } else if (document.webkitExitFullscreen) { // Chrome, Safari, and Opera
                        document.webkitExitFullscreen();
                    } else if (document.msExitFullscreen) { // IE/Edge
                        document.msExitFullscreen();
                    }
                    fullscreenButton.innerText = 'Open Fullscreen';
                }
            });

            document.addEventListener('fullscreenchange', () => {
                if (!document.fullscreenElement) {
                    chart.resize(chartElement.offsetWidth, chartElement.offsetHeight);
                    fullscreenButton.innerText = 'Open Fullscreen';
                } else {
                    chart.resize(window.innerWidth, window.innerHeight);
                }
            });

            window.addEventListener('resize', () => {
                chart.resize(chartElement.offsetWidth, chartElement.offsetHeight);
            });

            screenshotButton.addEventListener('click', () => {
                const loadingIndicator = document.getElementById('loadingIndicator');
                loadingIndicator.style.display = 'block';

                html2canvas(chartContainer, { scale: 2 }).then(canvas => {
                    loadingIndicator.style.display = 'none';

                    // Always offer download as the primary method
                    downloadScreenshot(canvas);

                    // Try to copy to clipboard as a secondary method
                    if (navigator.clipboard && navigator.clipboard.write) {
                        canvas.toBlob(blob => {
                            navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })])
                                .then(() => {
                                    showNotification('Screenshot copied to clipboard and downloaded!');
                                })
                                .catch(err => {
                                    console.error('Failed to copy to clipboard:', err);
                                    showNotification('Screenshot downloaded. Clipboard copy failed.');
                                });
                        });
                    } else {
                        showNotification('Screenshot downloaded. Clipboard copy not supported in this browser.');
                    }
                }).catch(err => {
                    loadingIndicator.style.display = 'none';
                    console.error('Failed to capture screenshot:', err);
                    showNotification('Failed to capture screenshot. Please try again.', 'error');
                });
            });
        }

        function showNotification(message, type = 'success') {
            const notification = document.getElementById('notification');
            notification.textContent = message;
            notification.style.backgroundColor = type === 'success' ? '#4CAF50' : '#f44336';
            notification.style.display = 'block';
            setTimeout(() => {
                notification.style.display = 'none';
            }, 5000);
        }

        function downloadScreenshot(canvas) {
            canvas.toBlob(blob => {
                const url = URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.download = 'chart_screenshot.png';
                link.click();
                URL.revokeObjectURL(url);
            });
        }

        function getData() {
            const dataElement = document.getElementById('data-json');
            const wickLinesElement = document.getElementById('wick-lines-json');
            const data = JSON.parse(dataElement.textContent);
            const wickLines = JSON.parse(wickLinesElement.textContent);
            createChart(data, wickLines);
        }

        document.addEventListener('DOMContentLoaded', getData);
    </script>
    <div id="data-json" style="display: none;">{{ data }}</div>
    <div id="wick-lines-json" style="display: none;">{{ wick_lines }}</div>
</body>
</html>
"""

# Streamlit App
st.title("Because Wicks Don't Lie")
st.sidebar.title("Settings")
st.sidebar.markdown("Configure the parameters for the analysis.")

# Fetch Binance futures pairs
binance_futures_pairs = get_binance_futures_pairs()
if not binance_futures_pairs:
    st.stop()

symbol = st.sidebar.selectbox("Symbol", binance_futures_pairs, index=binance_futures_pairs.index("BTCUSDT"),
                              help="The symbol of the cryptocurrency pair (e.g., BTCUSDT).")
interval = st.sidebar.selectbox("Interval",
                                ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w",
                                 "1M"],
                                help="The interval for the candlestick data.")
start_date = st.sidebar.date_input("Start Date", value=datetime.now() - pd.DateOffset(days=9),
                                   help="Start date for fetching the historical data.")
start_time = st.sidebar.time_input("Start Time", value=datetime.now().time(),
                                   help="Start time for fetching the historical data.")
start_str = datetime.combine(start_date, start_time).strftime('%Y-%m-%d %H:%M:%S')
end_str = st.sidebar.text_input("End Time", value="now UTC",
                                help="End time for fetching the historical data (default is now UTC).")
wick_ratio = st.sidebar.number_input("Wick Ratio", value=0.83, min_value=0.0, max_value=1.0, step=0.01,
                                     help="Ratio to determine a long wick. The higher, the better the quality of a wick.")
body_threshold = st.sidebar.number_input("Body Threshold", value=0.06, min_value=0.0, max_value=1.0, step=0.01,
                                         help="Maximum ratio of body to total candle size for a tiny body. The lower, the less wicks will be shown, but higher quality and probability.")
candle_size_multiplier = st.sidebar.slider("Candle Size Multiplier", value=1.0, min_value=0.1, max_value=3.0, step=0.1,
                                           help="Multiplier to adjust the average candle size before searching for wicks. The lower, the more wicks will be shown, but possibly less quality wicks.")

if st.sidebar.button("Fetch Data"):
    with st.spinner("Fetching data..."):
        df = get_historical_klines(symbol, interval, start_str, end_str)

    if df.empty:
        st.error("No data fetched. Please check the symbol and time range.")
        st.stop()

    st.success("Data fetched successfully. Number of rows: {}".format(len(df)))

    df['timestamp'] = df['timestamp'] + pd.DateOffset(hours=2)

    # Calculate ATR
    df['atr'] = calculate_atr(df)

    # Calculate the average candle size for the first 1000 candles or fewer if not enough data
    sample_df = df.head(1000).copy()
    sample_df['candle_size'] = sample_df['high'] - sample_df['low']
    average_candle_size = sample_df['candle_size'].mean() * candle_size_multiplier

    st.write(f"Average Candle Size: {average_candle_size}")
    st.write(f"Using Wick Ratio: {wick_ratio}")

    df['tiny_body_long_wick'] = df.apply(has_tiny_body_long_wick_with_min_size, axis=1,
                                         body_threshold=body_threshold, wick_ratio=wick_ratio,
                                         min_size=average_candle_size)

    # Assess risk for each candle
    df['risk_score'] = df.apply(lambda row: assess_wick_risk(row, df['atr']), axis=1)

    df['bars_to_fill_wick'] = None
    df['drawdown_till_fill_pct'] = None
    df['drawdown_till_fill_dollar'] = None
    pattern_candles_idx = df[df['tiny_body_long_wick']].index

    for idx in pattern_candles_idx:
        bars_to_fill = bars_to_fill_wick(df, idx)
        df.loc[idx, 'bars_to_fill_wick'] = bars_to_fill
        if bars_to_fill is not None:
            drawdown_pct, drawdown_dollar = calculate_drawdown(df, idx, bars_to_fill)
            df.loc[idx, 'drawdown_till_fill_pct'] = drawdown_pct
            df.loc[idx, 'drawdown_till_fill_dollar'] = drawdown_dollar

    filled_wick_candles = df.dropna(subset=['bars_to_fill_wick'])
    unfilled_wick_candles = df[df['tiny_body_long_wick'] & df['bars_to_fill_wick'].isna()]

    # Calculate potential drawdown for unfilled wicks
    unfilled_wick_candles['potential_drawdown_pct'], unfilled_wick_candles['potential_drawdown_dollar'] = zip(
        *unfilled_wick_candles.apply(lambda row: calculate_potential_drawdown(row, df), axis=1))

    # Determine which wick (upper or lower) is longer and unfilled
    wick_lines = []
    valid_unfilled_wick_candles = []
    for _, row in unfilled_wick_candles.iterrows():
        upper_wick_length = row['high'] - max(row['open'], row['close'])
        lower_wick_length = min(row['open'], row['close']) - row['low']

        if upper_wick_length > lower_wick_length and not is_wick_filled(row, df, 'upper'):
            wick_lines.append({
                'time': int(row['timestamp'].timestamp()),
                'endTime': int(df['timestamp'].max().timestamp()),
                'high': row['high'],
                'low': row['low'],
                'high_unfilled': True,
                'low_unfilled': False
            })
            valid_unfilled_wick_candles.append(row)
        elif lower_wick_length > upper_wick_length and not is_wick_filled(row, df, 'lower'):
            wick_lines.append({
                'time': int(row['timestamp'].timestamp()),
                'endTime': int(df['timestamp'].max().timestamp()),
                'high': row['high'],
                'low': row['low'],
                'high_unfilled': False,
                'low_unfilled': True
            })
            valid_unfilled_wick_candles.append(row)

    valid_unfilled_wick_candles_df = pd.DataFrame(valid_unfilled_wick_candles)

    # Filter out high-risk wicks
    low_risk_filled_wicks = filled_wick_candles[filled_wick_candles['risk_score'] <= 1]
    high_risk_filled_wicks = filled_wick_candles[filled_wick_candles['risk_score'] > 1]
    low_risk_unfilled_wicks = unfilled_wick_candles[unfilled_wick_candles['risk_score'] <= 1]
    high_risk_unfilled_wicks = unfilled_wick_candles[unfilled_wick_candles['risk_score'] > 1]

    # Calculate average metrics for low-risk filled wicks
    avg_bars_to_fill = low_risk_filled_wicks['bars_to_fill_wick'].mean()
    avg_drawdown_till_fill_pct = low_risk_filled_wicks['drawdown_till_fill_pct'].mean()
    avg_drawdown_till_fill_dollar = low_risk_filled_wicks['drawdown_till_fill_dollar'].mean()

    # Calculate average metrics for low-risk unfilled wicks
    avg_potential_drawdown_pct = low_risk_unfilled_wicks['potential_drawdown_pct'].mean()
    avg_potential_drawdown_dollar = low_risk_unfilled_wicks['potential_drawdown_dollar'].mean()

    with st.expander("Metrics and Analysis"):
        st.write(f"Low-Risk Filled Wicks Metrics:")
        st.write(f"Number of low-risk filled wicks: {len(low_risk_filled_wicks)}")
        st.write(f"Average bars to fill wick: {avg_bars_to_fill:.2f}")
        st.write(
            f"Average drawdown till fill: {avg_drawdown_till_fill_pct:.2f}% (${avg_drawdown_till_fill_dollar:.2f})")

        st.write(f"\nLow-Risk Unfilled Wicks Metrics:")
        st.write(f"Number of low-risk unfilled wicks: {len(low_risk_unfilled_wicks)}")
        st.write(
            f"Average potential drawdown: {avg_potential_drawdown_pct:.2f}% (${avg_potential_drawdown_dollar:.2f})")

        st.subheader("Low-Risk Filled Wick Candles")
        st.dataframe(low_risk_filled_wicks[['timestamp', 'open', 'high', 'low', 'close', 'bars_to_fill_wick',
                                            'drawdown_till_fill_pct', 'drawdown_till_fill_dollar', 'risk_score']])

        st.subheader("High-Risk Filled Wick Candles")
        st.dataframe(high_risk_filled_wicks[['timestamp', 'open', 'high', 'low', 'close', 'bars_to_fill_wick',
                                             'drawdown_till_fill_pct', 'drawdown_till_fill_dollar', 'risk_score']])

        st.subheader("Low-Risk Unfilled Wick Candles")
        st.dataframe(low_risk_unfilled_wicks[['timestamp', 'open', 'high', 'low', 'close', 'potential_drawdown_pct',
                                              'potential_drawdown_dollar', 'risk_score']])

        st.subheader("High-Risk Unfilled Wick Candles")
        st.dataframe(high_risk_unfilled_wicks[
                         ['timestamp', 'open', 'high', 'low', 'close', 'potential_drawdown_pct',
                          'potential_drawdown_dollar', 'risk_score']])

    st.write("Creating candlestick chart...")

    # Prepare data for TradingView chart
    chart_data = df[['timestamp', 'open', 'high', 'low', 'close']].rename(columns={
        'timestamp': 'time',
        'open': 'open',
        'high': 'high',
        'low': 'low',
        'close': 'close'
    })

    # Convert timestamp to Unix timestamp in seconds
    chart_data['time'] = (chart_data['time'].astype('int64') // 10 ** 9).astype(int)

    # Convert the data to the correct format
    chart_data_list = chart_data.to_dict('records')

    chart_data_json = json.dumps(chart_data_list)
    wick_lines_json = json.dumps(wick_lines)

    # Create a temporary HTML file with the chart data and wick lines
    temp_html = html_content.replace('{{ data }}', chart_data_json).replace('{{ wick_lines }}', wick_lines_json)
    with open("temp_chart.html", "w") as f:
        f.write(temp_html)

    # Display the chart using components.html
    with open("temp_chart.html", "r") as f:
        components.html(f.read(), height=600)

    # Remove the temporary file
    os.remove("temp_chart.html")
