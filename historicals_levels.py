# backend/historical_levels.py
import requests
import datetime
import logging
from urllib.parse import quote
import json
import pandas as pd
from time import sleep

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class HistoricalLevelsCalculator:
    def __init__(self, symbol, from_date, to_date):
        """
        symbol: e.g., 'NIFTY 50', 'BANKNIFTY', 'SENSEX'
        from_date, to_date: 'dd-mm-yyyy' strings
        """
        self.symbol = symbol
        self.from_date = from_date
        self.to_date = to_date
        self.fixed_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        self.session = self._create_session()
        self.url = "https://www.nseindia.com/api/historical/indicesHistory"

    def _create_session(self):
        session = requests.Session()
        session.headers.update({
            "User-Agent": self.fixed_user_agent,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nseindia.com/",
            "Origin": "https://www.nseindia.com",
            "DNT": "1"
        })
        return session

    def fetch_historical_data(self):
        if self.symbol == "SENSEX":
            return self._fetch_from_csv()
        else:
            try:
                logging.info(f"[{self.symbol}] Fetching data from API")
                # warm-up homepage request to get cookies
                self.session.get("https://www.nseindia.com", timeout=10)
                sleep(1)
                index_encoded = quote(self.symbol)  # encode spaces to %20
                url = f"{self.url}?indexType={index_encoded}&from={self.from_date}&to={self.to_date}"
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()
                records = data.get("data", {}).get("indexCloseOnlineRecords", [])
                logging.info(f"[{self.symbol}] Fetched {len(records)} records")
                return records
            except Exception as e:
                logging.error(f"[{self.symbol}] Error fetching historical data: {e}")
                return []

    def _fetch_from_csv(self):
        try:
            df = pd.read_csv('backend/data/sensex_ohlc_data.csv')
            df['Date'] = pd.to_datetime(df['Date'], format='%d-%B-%Y')
            df = df.sort_values('Date', ascending=False)
            logging.info(f"[{self.symbol}] Loaded {len(df)} rows from CSV")
            records = []
            for _, row in df.iterrows():
                records.append({
                    'EOD_TIMESTAMP': row['Date'].strftime("%d-%b-%Y"),
                    'EOD_OPEN_INDEX_VAL': row['Open'],
                    'EOD_HIGH_INDEX_VAL': row['High'],
                    'EOD_LOW_INDEX_VAL': row['Low'],
                    'EOD_CLOSE_INDEX_VAL': row['Close']
                })
            return records
        except Exception as e:
            logging.error(f"[{self.symbol}] Error reading CSV: {e}")
            return []

    def calculate_levels(self, data):
        if not data:
            logging.warning(f"[{self.symbol}] No data to calculate levels")
            return {}

        today = datetime.datetime.today()
        current_week = today.isocalendar()[1]
        current_month = today.month

        prev_week = current_week - 1
        prev_month = current_month - 1 if current_month > 1 else 12

        # Group data by calendar week & month
        current_week_data, previous_week_data = [], []
        current_month_data, previous_month_data = [], []

        for day in data:
            dt = datetime.datetime.strptime(day['EOD_TIMESTAMP'], "%d-%b-%Y")
            week = dt.isocalendar()[1]
            month = dt.month

            if week == current_week:
                current_week_data.append(day)
            elif week == prev_week:
                previous_week_data.append(day)

            if month == current_month:
                current_month_data.append(day)
            elif month == prev_month:
                previous_month_data.append(day)

        # Previous day data: last available date minus today
        sorted_data = sorted(data, key=lambda d: datetime.datetime.strptime(d['EOD_TIMESTAMP'], "%d-%b-%Y"), reverse=True)
        prev_day_data = sorted_data[1:2]  # second latest day

        def get_high_low(items):
            if not items:
                return None, None
            highs = [d['EOD_HIGH_INDEX_VAL'] for d in items]
            lows = [d['EOD_LOW_INDEX_VAL'] for d in items]
            return max(highs), min(lows)

        PDH, PDL = get_high_low(prev_day_data)
        CWH, CWL = get_high_low(current_week_data)
        PWH, PWL = get_high_low(previous_week_data)
        PMH, PML = get_high_low(previous_month_data)

        levels = {
            "symbol": self.symbol,
            "PDH": PDH, "PDL": PDL,
            "CWH": CWH, "CWL": CWL,
            "PWH": PWH, "PWL": PWL,
            "PMH": PMH, "PML": PML
        }

        logging.info(f"[{self.symbol}] Levels calculated: {levels}")
        return levels

    def save_levels(self, levels):
        filename = f"backend/data/levels_{self.symbol.replace(' ', '_')}.json"
        try:
            with open(filename, "w") as f:
                json.dump(levels, f, indent=2)
            logging.info(f"[{self.symbol}] Levels saved to {filename}")
        except Exception as e:
            logging.error(f"[{self.symbol}] Error saving levels: {e}")

    def run(self):
        data = self.fetch_historical_data()
        levels = self.calculate_levels(data)
        if levels:
            self.save_levels(levels)
        return levels
