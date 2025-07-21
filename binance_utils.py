import streamlit as st
from binance.client import Client
import pandas as pd
import time
import os


@st.cache_resource
def get_binance_client():
    try:
        binance_secrets = st.secrets["binance"]
        api_key = binance_secrets["BINANCE_API_KEY"]
        api_secret = binance_secrets["BINANCE_SECRET_KEY"]
        return Client(api_key, api_secret)
    except KeyError as e:
        print(f"KeyError: {e}")  # Add this line for debugging
        raise ValueError(f"Binance API credentials not found in Streamlit secrets: {e}")


@st.cache_data(ttl=3600)
def get_binance_futures_pairs():
    client = get_binance_client()
    if not client:
        return []
    try:
        exchange_info = client.futures_exchange_info()
        symbols = [symbol['symbol'] for symbol in exchange_info['symbols']]
        return symbols
    except Exception as e:
        st.error(f"Error fetching Binance futures pairs: {e}")
        return []


@st.cache_data(ttl=300)
def get_historical_klines(symbol, interval, limit=20000):
    client = get_binance_client()
    if not client:
        return pd.DataFrame()
    try:
        if interval in ['2m', '3m', '4m', '6m', '7m', '8m', '9m', '10m']:
            base_interval = '1m'
            base_limit = limit * int(interval[:-1])
        else:
            # For standard intervals, use them directly
            base_interval = interval
            base_limit = limit

        end_time = int(time.time() * 1000)
        klines = []

        while len(klines) < limit:
            try:
                temp_klines = client.futures_klines(
                    symbol=symbol,
                    interval=base_interval,
                    limit=min(base_limit, 1000),
                    endTime=end_time
                )
            except Exception as api_error:
                st.error(f"Error fetching data for {symbol} with interval {interval} (base interval: {base_interval}): {str(api_error)}")
                return pd.DataFrame()

            if not temp_klines:
                break

            klines = temp_klines + klines
            end_time = temp_klines[0][0] - 1

            if len(temp_klines) < 1000:
                break

            time.sleep(0.1)

        df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time',
                                           'quote_asset_volume', 'number_of_trades',
                                           'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume',
                                           'ignore'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)

        # Add the timezone adjustment of +2 hours
        df['timestamp'] = df['timestamp'] + pd.Timedelta(hours=2)

        df.set_index('timestamp', inplace=True)
        df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)

        if interval in ['2m', '3m', '4m', '6m', '7m', '8m', '9m', '10m']:
            df = create_custom_interval(df, interval)

        return df.iloc[-limit:]
    except Exception as e:
        st.error(f"Error fetching historical data: {e}")
        return pd.DataFrame()


def create_custom_interval(df, interval):
    df = df.sort_index()
    minutes = int(interval[:-1])
    offset = pd.Timedelta(minutes=minutes)
    return df.resample(f'{minutes}T', offset=offset).agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()