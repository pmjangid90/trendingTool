import pandas as pd
import re
import os

# === PARAMETERS ===
ROLLING_WINDOW = 13
DEVIATION_THRESHOLD = 0.3
CONFIRMATION_STREAK = 2
FILES = {
    'BankNifty': f'backend/data/snapshots_BANKNIFTY_2025-08-13.txt',
    'Nifty': f'backend/data/snapshots_NIFTY_2025-08-13.txt',
    'Sensex': f'backend/data/snapshots_SENSEX_2025-08-13.txt',
}
#'BankNifty': f'backend/data/snapshots_BANKNIFTY_{pd.Timestamp.now().strftime("%Y-%m-%d")}.txt',

# === PARSING ===
def parse_input_file(filepath, symbol):
    rows = []
    pattern = re.compile(
        r"\|\s*(\d{2}-\d{2}-\d{4} \d{2}:\d{2})\s*\|\s*"
        r"([A-Z0-9]+)\s*\|\s*"
        r"EXP:([\d-]+)\s*\|\s*"
        r"LTP:\s*([\d.,-]+)\s*\|.*?"
        r"NetOI:\s*([-\d.,]+)",
        re.IGNORECASE
    )
    if not os.path.exists(filepath):
        print(f"⚠️ File not found: {filepath}")
        return pd.DataFrame()

    with open(filepath, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            match = pattern.search(line)
            if match:
                timestamp = match.group(1)
                expiry = match.group(3)
                ltp = float(match.group(4).replace(',', ''))
                net_oi_change = int(float(match.group(5).replace(',', '')))
                net_dex = net_oi_change * 0.5
                rows.append({
                    'timestamp': timestamp,
                    'symbol': symbol,
                    'expiry': expiry,
                    'ltp': ltp,
                    'net_oi_change': net_oi_change,
                    'net_dex': net_dex
                })
            else:
                if line.strip():
                    print(f"[Line {i}] ⚠️ Could not parse: {line.strip()}")
    return pd.DataFrame(rows)


# === CALCULATIONS ===
def add_moving_averages(df):
    df['ltp_ma'] = df['ltp'].rolling(ROLLING_WINDOW, min_periods=ROLLING_WINDOW).mean()
    df['net_oi_ma'] = df['net_oi_change'].rolling(ROLLING_WINDOW, min_periods=ROLLING_WINDOW).mean()
    df['ltp_std'] = df['ltp'].rolling(ROLLING_WINDOW, min_periods=ROLLING_WINDOW).std()
    df['net_oi_std'] = df['net_oi_change'].rolling(ROLLING_WINDOW, min_periods=ROLLING_WINDOW).std()
    return df


# === SENTIMENT LOGIC (updated as per OI principles) ===
def apply_sentiment_rules(df, dev_threshold):
    sentiments = []
    for idx, row in df.iterrows():
        ltp, ltp_ma, ltp_std = row['ltp'], row['ltp_ma'], row['ltp_std']
        net_oi, net_oi_ma, net_oi_std = row['net_oi_change'], row['net_oi_ma'], row['net_oi_std']

        if pd.isna(ltp_ma) or pd.isna(net_oi_ma) or pd.isna(ltp_std) or pd.isna(net_oi_std):
            sentiments.append('Not enough data')
            continue

        ltp_significant = abs(ltp - ltp_ma) >= dev_threshold * ltp_std
        netoi_significant = abs(net_oi - net_oi_ma) >= dev_threshold * net_oi_std

        if not (ltp_significant or netoi_significant):
            sentiments.append('Sideways/Chop')
            continue

        prev_net_oi_ma = df['net_oi_ma'].shift(1).iloc[idx]
        if pd.isna(prev_net_oi_ma):
            sentiments.append('Not enough data')
            continue

        direction_net_oi = net_oi_ma - prev_net_oi_ma

        if direction_net_oi > 0:  # More positive Net OI
            if ltp > ltp_ma:
                sentiments.append('Weak Bullish / Caution')
            else:
                sentiments.append('Strong Bearish')
        elif direction_net_oi < 0:  # More negative Net OI
            if ltp > ltp_ma:
                sentiments.append('Strong Bullish')
            else:
                sentiments.append('Weak Bearish / Caution')
        else:
            sentiments.append('Neutral')
    return sentiments


# === STREAK CONFIRMATION ===
def confirm_signals(sentiments, streak):
    confirmed = []
    count = 1
    for i in range(len(sentiments)):
        if i == 0:
            confirmed.append('Not enough data')
            continue
        if sentiments[i] == sentiments[i-1] and sentiments[i] not in ['Sideways/Chop', 'Not enough data']:
            count += 1
        else:
            count = 1
        if count >= streak and sentiments[i] not in ['Sideways/Chop', 'Not enough data']:
            confirmed.append(sentiments[i])
        else:
            confirmed.append('Sideways/Chop')
    return confirmed


# === PROCESSING PER SYMBOL ===
def process_symbol(symbol, filepath):
    print(f"\n📊 Processing {symbol}...")
    df = parse_input_file(filepath, symbol)
    if df.empty:
        return df

    df = add_moving_averages(df)
    base_sents = apply_sentiment_rules(df, DEVIATION_THRESHOLD)
    confirmed_sents = confirm_signals(base_sents, CONFIRMATION_STREAK)

    col_name = f"Sentiment_SD{DEVIATION_THRESHOLD}_Streak{CONFIRMATION_STREAK}"
    df[col_name] = confirmed_sents
    return df


# === CALLABLE RUN FUNCTION ===
def run_sentiment_analysis():
    all_dfs = []
    for symbol, filepath in FILES.items():
        df = process_symbol(symbol, filepath)
        if not df.empty:
            # Save per-symbol sentiment
            output_path = f'backend/data/sentiments_{symbol}_{pd.Timestamp.now().strftime("%d%b")}.csv'
            df.to_csv(output_path, index=False)
            print(f"✅ {symbol} sentiments saved to {output_path}")
            all_dfs.append(df)

    # Save combined file for all symbols
    if all_dfs:
        combined_df = pd.concat(all_dfs, ignore_index=True)
        combined_path = f'backend/data/sentiments_ALL_{pd.Timestamp.now().strftime("%d%b")}.csv'
        combined_df.to_csv(combined_path, index=False)
        print(f"📂 Combined sentiments saved to {combined_path}")
    else:
        print("⚠️ No data processed. Check input files.")



# === OLD STANDALONE MAIN (still works if run alone) ===
if __name__ == "__main__":
    run_sentiment_analysis()
