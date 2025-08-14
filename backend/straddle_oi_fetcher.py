import requests
import urllib3
import json

# Disable SSL warnings (only for dev; remove in prod)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class StraddleOIFetcher:
    def __init__(self, cookie_string):
        self.cookies = self._parse_cookie_string(cookie_string)
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": "https://sensibull.com/",
            "Origin": "https://sensibull.com",
            "Accept": "application/json, text/plain, */*"
        }

    def _parse_cookie_string(self, cookie_string):
        cookies = {}
        for item in cookie_string.split("; "):
            key, value = item.split("=", 1)
            cookies[key] = value
        return cookies

    def fetch_latest_straddle(self, symbol, expiry):
        url = f"https://straddle-chart.financedeft.com/{symbol}_{expiry}.json"
        try:
            resp = requests.get(url, timeout=10, verify=False)
            resp.raise_for_status()
            data = resp.json()
            price_list = data.get("price_list", [])
            if not price_list:
                return None
            latest = sorted(price_list, key=lambda x: x['time'], reverse=True)[0]
            return {
                "straddle_price": round(latest.get('price', 0), 2),
                "ce_price": round(latest.get('ce_price', 0), 2),
                "pe_price": round(latest.get('pe_price', 0), 2)
            }
        except Exception as e:
            print(f"[Error] Fetching straddle for {symbol} {expiry}: {e}")
            return None

    def fetch_oi_data(self, symbol, expiry, from_time, to_time):
        expiries_payload = {expiry: {"is_enabled": True, "is_weekly": True}}
        payload = {
            "underlying": symbol,
            "mode": "intraday",
            "expiries": expiries_payload,
            "atm_strike_selection": "ten",
            "input_min_strike": None,
            "input_max_strike": None,
            "from_time": from_time,
            "to_time": to_time,
            "auto_update": "full_day",
            "from_date": None,
            "to_date": None,
            "show_oi": True
        }
        try:
            response = requests.post(
                "https://oxide.sensibull.com/v1/compute/1/oi_graphs/oi_change_chart",
                json=payload, cookies=self.cookies, headers=self.headers,
                timeout=10, verify=False
            )
            response.raise_for_status()
            data = response.json()
            #print(f"\n\n==== DEBUG OI for {symbol} {expiry} ====")
            with open(f"debug_oi_{symbol}_{expiry}.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            per_strike = data.get('payload', {}).get('per_strike_data', {})
            if not per_strike:
                return None

            total_from_call = sum(oi.get('from_call_oi', 0) for oi in per_strike.values())
            total_to_call   = sum(oi.get('to_call_oi', 0) for oi in per_strike.values())
            total_from_put  = sum(oi.get('from_put_oi', 0) for oi in per_strike.values())
            total_to_put    = sum(oi.get('to_put_oi', 0) for oi in per_strike.values())

            return {
                "call_oi": total_to_call,
                "put_oi": total_to_put,
                "change_call_oi": total_to_call - total_from_call,
                "change_put_oi": total_to_put - total_from_put,
                "per_strike": per_strike  # <-- new field
            }
        except Exception as e:
            print(f"[Error] Fetching OI for {symbol} {expiry}: {e}")
            return None
