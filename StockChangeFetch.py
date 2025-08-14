
# fetch_index_prices.py
def fetch_and_save_index_prices(cookie_string):
    import requests
    import urllib3
    import os
    from datetime import datetime
    import logging

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    url = f"https://oxide.sensibull.com/v1/compute/cache/quotes_v2"
    cookies = dict(x.strip().split("=", 1) for x in cookie_string.split("; "))


    # List of stock symbols to fetch
    symbols = [
        "RELIANCE", "HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK",
        "KOTAKBANK", "TCS", "INFY", "BHARTIARTL", "LT", "ITC", 
        "HINDUNILVR", "BAJFINANCE"
    ]

    # Example weights (replace with real weights)
    nifty_weights = {
        "RELIANCE": 9, "HDFCBANK": 13, "ICICIBANK": 9, "SBIN": 2, 
        "AXISBANK": 3, "KOTAKBANK": 3, "TCS": 3, "INFY": 4,
        "BHARTIARTL": 5, "LT": 3.5, "ITC": 3
    }
    banknifty_weights = {
     "HDFCBANK": 28, "ICICIBANK": 25, "SBIN": 9, 
        "AXISBANK": 8, "KOTAKBANK": 8
    }

    sensex_weights = {
        "RELIANCE": 12, "HDFCBANK": 10, "BHARTIARTL": 8, "TCS": 8, "ICICIBANK": 7, "SBIN": 4, 
        "BAJFINANCE": 3, "INFY": 4, "ITC": 3
    }

    output_dir = "data"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "stocks_price_change_table.txt")

    header = "| {:<19} | {:>9} | {:>9} | {:>9} |".format("Timestamp", "NIFTY", "BANKNIFTY", "SENSEX") + "".join(
        f" {symbol:>10} |" for symbol in symbols
    )

    if not os.path.exists(output_file):
        with open(output_file, "w") as f:
            f.write(header + "\n")

    try:
        payload = {"trading_symbols": symbols}
        response = requests.post(url, json=payload, cookies=cookies, timeout=10, verify=False)
        response.raise_for_status()
        payload_data = response.json().get("payload", {})

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        nifty_total = banknifty_total = sensex_total = 0
        stock_changes = []

        for symbol in symbols:
            price_change = payload_data.get(symbol, {}).get("price_change")
            if price_change is not None:
                try:
                    pct = float(price_change) * 100
                    price_str = f"{pct:+.2f}%"
                    nifty_total += pct * nifty_weights.get(symbol, 0)
                    banknifty_total += pct * banknifty_weights.get(symbol, 0)
                    sensex_total += pct * sensex_weights.get(symbol, 0)
                except:
                    price_str = "   N/A"
            else:
                price_str = "   N/A"
            stock_changes.append(f"{price_str:>10}")

        def calc_index(total, weights):
            w_sum = sum(weights.values())
            return f"{(total/w_sum):+6.2f}%" if w_sum else "  N/A "

        nifty_str = calc_index(nifty_total, nifty_weights)
        banknifty_str = calc_index(banknifty_total, banknifty_weights)
        sensex_str = calc_index(sensex_total, sensex_weights)

        row = f"| {timestamp:<19} | {nifty_str:>9} | {banknifty_str:>9} | {sensex_str:>9} |"
        for change in stock_changes:
            row += f" {change} |"

        with open(output_file, "a") as f:
            f.write(row + "\n")

        print("\n📊 Latest index/stock row added:")
        print(row)

    except Exception as e:
        logging.error(f"❌ Error fetching index prices: {e}")

