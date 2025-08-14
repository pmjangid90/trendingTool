import requests
import pandas as pd
import urllib3
from datetime import datetime, timedelta

# Disable SSL warnings (only for dev; remove in prod)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class IndiaVIXFetcher:
    """
    Fetches latest India VIX close price.
    """
    def __init__(self, cookie_string: str):
        self.url = "https://oxide.sensibull.com/v1/compute/candles/INDIAVIX"
        self.cookies = dict(x.strip().split("=", 1) for x in cookie_string.split("; "))

    def fetch_latest_close(self):
        # Automatically set from_date = yesterday, to_date = today in YYYY-MM-DD format
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        payload = {
            "from_date": yesterday.strftime("%Y-%m-%d"),
            "to_date": today.strftime("%Y-%m-%d"),
            "interval": "1M",
            "skip_last_ts": False
        }
        try:
            response = requests.post(self.url, json=payload, cookies=self.cookies, timeout=10, verify=False)
            response.raise_for_status()
            raw = response.json()
            #print(raw)
            candles = raw.get('payload', {}).get('candles', [])
            #print(f"candles:{candles}")
            if candles:
                latest_close = candles[-1].get('close')
                return latest_close
            else:
                print("⚠ No VIX candles data found")
                return None
        except Exception as e:
            print(f"❌ Error fetching India VIX: {e}")
            return None


class SensibullFetcher:
    """
    Fetches option chain data and computes total vega & theta.
    """
    SYMBOL_TO_TOKEN = {
        "NIFTY": "256265",
        "BANKNIFTY": "260105",
        "SENSEX": "265",
    }
    SYMBOL_TO_STRIKE_STEP = {
        "NIFTY": 50,
        "BANKNIFTY": 100,
        "SENSEX": 100,
    }

    def __init__(self, access_token: str, csv_path: str, cookie_string: str):
        self.access_token = access_token
        self.token_map = pd.read_csv(csv_path)
        self.token_map["INSTRUMENT_TOKEN"] = self.token_map["INSTRUMENT_TOKEN"].astype(str)
        self.vix_fetcher = IndiaVIXFetcher(cookie_string)  # add vix fetcher

    def fetch_vix_close(self):
        return self.vix_fetcher.fetch_latest_close()

    def fetch_data(self, symbol: str, expiry_date: str = None):
        underlying_token = self.SYMBOL_TO_TOKEN.get(symbol)
        strike_step = self.SYMBOL_TO_STRIKE_STEP.get(symbol, 50)

        url = f"https://oxide.sensibull.com/v1/compute/cache/live_derivative_prices/{underlying_token}"
        cookies = {"access_token": self.access_token}

        try:
            response = requests.get(url, cookies=cookies, timeout=10, verify=False)
            response.raise_for_status()
            raw = response.json()
            data = raw.get("data", {})
            #print(data)
            ltp = float(data.get("underlying_price", 0))
            per_expiry_data = data.get("per_expiry_data", {})

            available_expiries = sorted(per_expiry_data.keys())
            result = {
                "ltp": ltp,
                "atm": None,
                "expiries": {}
            }

            for expiry in available_expiries:
                if expiry_date and expiry != expiry_date:
                    continue

                expiry_data = per_expiry_data.get(expiry, {})
                atm_raw = expiry_data.get("atm_strike")
                atm = int(atm_raw) if atm_raw else round(ltp / strike_step) * strike_step

                call_strikes = [atm - 2 * strike_step + i * strike_step for i in range(11)]
                put_strikes  = [atm - 8 * strike_step + i * strike_step for i in range(11)]

                options = expiry_data.get("options", [])
                rows = []
                for opt in options:
                    token_str = str(opt.get("token"))
                    mapped = self.token_map[self.token_map["INSTRUMENT_TOKEN"] == token_str]
                    if not mapped.empty:
                        strike = mapped.iloc[0]["STRIKE"]
                        option_type = mapped.iloc[0]["INSTRUMENT_TYPE"]
                        greeks = opt.get("greeks_with_iv") or {}
                        rows.append({
                            "strike": int(strike),
                            "type": option_type,
                            "theta": greeks.get("theta", 0),
                            "vega": greeks.get("vega", 0),
                            "delta": greeks.get("delta", 0),
                            "gamma": greeks.get("gamma", 0),
                        })
                #print(rows)
                if not rows:
                    result["expiries"][expiry] = None
                    continue

                df = pd.DataFrame(rows)
                #print(df)

                call_df = df[(df["type"] == "CE") & (df["strike"].isin(call_strikes))]
                put_df  = df[(df["type"] == "PE") & (df["strike"].isin(put_strikes))]

                stats = {
                    "total_call_vega": float(call_df["vega"].sum()),
                    "total_put_vega": float(put_df["vega"].sum()),
                    "total_call_theta": float(call_df["theta"].sum()),
                    "total_put_theta": float(put_df["theta"].sum()),
                    "total_call_delta": float(call_df["delta"].sum()),
                    "total_put_delta": float(put_df["delta"].sum()),
                    "total_call_gamma": float(call_df["gamma"].sum()),
                    "total_put_gamma": float(put_df["gamma"].sum()),
                }
                # For Net Delta Exposure
                stats["per_strike_deltas"] = {
                (row["strike"], row["type"]): row["delta"] for row in rows
                }
                #print(stats)
                result["expiries"][expiry] = stats
                result["atm"] = atm

            return result

        except Exception as e:
            print(f"❌ Error fetching data for {symbol}: {e}")
            return None
