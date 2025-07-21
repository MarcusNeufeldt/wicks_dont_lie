import pandas as pd

def pattern_quality_score(candle, avg_candle_size, avg_volume):
    body_size = abs(candle['open'] - candle['close'])
    total_size = candle['high'] - candle['low']

    body_factor = 1 - (body_size / total_size)
    size_factor = min(total_size / avg_candle_size, 2)
    volume_factor = min(candle['volume'] / avg_volume, 2)

    upper_wick = candle['high'] - max(candle['open'], candle['close'])
    lower_wick = min(candle['open'], candle['close']) - candle['low']
    wick_asymmetry = abs(upper_wick - lower_wick) / total_size

    weights = {'body': 0.4, 'size': 0.3, 'volume': 0.1, 'asymmetry': 0.2}

    score = (body_factor * weights['body'] +
             size_factor * weights['size'] +
             volume_factor * weights['volume'] +
             wick_asymmetry * weights['asymmetry']) * 100

    return score

def identify_unfilled_wicks(df, wick_ratio=0.8, body_threshold=0.1, candle_size_multiplier=1.0, min_unfilled_percentage=0.5):
    avg_candle_size = (df['high'] - df['low']).mean() * candle_size_multiplier
    avg_volume = df['volume'].mean()

    unfilled_wicks = []
    for i in range(len(df) - 1):  # Exclude the last candle as we can't determine if it's filled yet
        candle = df.iloc[i]
        body_size = abs(candle['open'] - candle['close'])
        total_size = candle['high'] - candle['low']

        if total_size == 0 or total_size < avg_candle_size:
            continue

        upper_wick = candle['high'] - max(candle['open'], candle['close'])
        lower_wick = min(candle['open'], candle['close']) - candle['low']
        wick_size = upper_wick + lower_wick

        is_tiny_body = body_size <= total_size * body_threshold
        is_long_wick = wick_size >= total_size * wick_ratio

        if is_tiny_body and is_long_wick:
            # Check if the wick remains unfilled in subsequent candles
            subsequent_candles = df.iloc[i + 1:]
            if upper_wick > lower_wick:
                highest_subsequent = subsequent_candles['high'].max()
                unfilled_percentage = (candle['high'] - highest_subsequent) / upper_wick
                is_unfilled = unfilled_percentage >= min_unfilled_percentage
            else:
                lowest_subsequent = subsequent_candles['low'].min()
                unfilled_percentage = (lowest_subsequent - candle['low']) / lower_wick
                is_unfilled = unfilled_percentage >= min_unfilled_percentage

            if is_unfilled:
                score = pattern_quality_score(candle, avg_candle_size, avg_volume)
                unfilled_wicks.append({
                    'timestamp': df.index[i],
                    'open': candle['open'],
                    'high': candle['high'],
                    'low': candle['low'],
                    'close': candle['close'],
                    'volume': candle['volume'],
                    'score': score,
                    'wick_type': 'upper' if upper_wick > lower_wick else 'lower',
                    'unfilled_percentage': unfilled_percentage
                })

    return pd.DataFrame(unfilled_wicks)

def prepare_chart_data(df, unfilled_wicks):
    chart_data = df.reset_index().apply(
        lambda row: {
            'time': int(row['timestamp'].timestamp()),
            'open': row['open'],
            'high': row['high'],
            'low': row['low'],
            'close': row['close']
        },
        axis=1
    ).tolist()

    wick_lines = unfilled_wicks.apply(
        lambda row: {
            'time': int(row['timestamp'].timestamp()),
            'endTime': int(df.index[-1].timestamp()),
            'high': row['high'] if row['wick_type'] == 'upper' else None,
            'low': row['low'] if row['wick_type'] == 'lower' else None,
            'high_unfilled': row['wick_type'] == 'upper',
            'low_unfilled': row['wick_type'] == 'lower'
        },
        axis=1
    ).tolist()

    return chart_data, wick_lines