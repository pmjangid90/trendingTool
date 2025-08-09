import time
import logging
import csv
from datetime import datetime, timedelta
import threading
import os

from sensibull_greeks_fetcher import SensibullFetcher
from straddle_oi_fetcher import StraddleOIFetcher
from StockChangeFetch import fetch_and_save_index_prices

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Setup
CSV_PATH = r"C:\Users\Paras.Mal\OneDrive - Reliance Corporate IT Park Limited\Documents\Personal\option_chain_dashboard\backend\data\tokens.csv"
SENSIBULL_ACCESS_TOKEN = "free_user"
COOKIE_STRING = "_cfuvid=IGBW.L5YL1RxUbiof17w_Im5oLtQpPZMW3MRb4aBlIA-1754240533702-0.0.1.1-604800000; rl_page_init_referrer=RudderEncrypt%3AU2FsdGVkX1%2BPAheNwaDrAHTlr8TsxWeNFZ5HXpA0EXA%3D; rl_page_init_referring_domain=RudderEncrypt%3AU2FsdGVkX19h0sHHtoeGC2fbWTp1a39uWblGZx9Zgh8%3D; _ga=GA1.1.105033444.1754240536; _clck=1rhf54c%7C2%7Cfy5%7C0%7C2041; _clsk=1wjmrn%7C1754240537943%7C1%7C1%7Cb.clarity.ms%2Fcollect; sb_rudder_utm={}; bkd_ref=78htFMp7dNetNHMP; access_token=6bEkiE1A6eYwXL2SCF-CFb4aGfDyzS6zQgQhpIhra6w; _ga_NC7XJTRTDX=GS2.1.s1754240535$o1$g1$t1754240568$j27$l0$h0; rl_anonymous_id=RudderEncrypt%3AU2FsdGVkX1%2FpGRBc9xw6p9PgBZ6xyGq0m0ZA5TUsCaRVJp9OXxoN7g9%2FrQAwBz6oV9W8yd%2FKD3RByDFpdQwmrA%3D%3D; rl_user_id=RudderEncrypt%3AU2FsdGVkX1%2FZmQXmz5w7WVwzTZL1sxvFG%2BtCJjoFhrHl4%2Fsb9hNTGCRNvwRaEfpEjXnvyB1saEywMHT2ZTH0iQ%3D%3D; rl_trait=RudderEncrypt%3AU2FsdGVkX1%2BOzZ8j7A1sCnyV0epkv5wIs6aSCHqphEOqsMDlWB8wisMS8qzJaoIMzrrumE5S4LJDcPsUmlcxJPmYc5T3wBCM1C5RXbuTgDg6SQ3v%2FhxcnfLrBTLFOqa2DKwvT4UA9eY18ZTLaZLlzwP%2B6L5%2B%2BgZeT2hrXOzYbdHoQQ1zBGyQnbBjOb1NDktGoTvsj22YOO0gxY%2FI63Gx8%2FWRHmUw4pi%2FbDFgu37dVcx6PqSm5EyM1OKrHUKFte1kPRVNICUuIlBLImb6f35z%2Bg%3D%3D; rl_session=RudderEncrypt%3AU2FsdGVkX1%2Bj2JHj%2FDO0rQCR1pqbk%2FNYUJ2cTjqzx8QiDgBbUm3L0BKlVHo%2BTjAqYnPJQORKFlbo2ftXKNKhwGwMgANgWpUwGYRqHOo2mHlj43DQkT2%2BNyDolaFHe5PGjCrNLUl%2Fz5I0mZacT65Qdg%3D%3D"
sensibull_fetcher = SensibullFetcher(SENSIBULL_ACCESS_TOKEN, CSV_PATH, COOKIE_STRING)
straddle_fetcher = StraddleOIFetcher(COOKIE_STRING)

os.makedirs("backend/data", exist_ok=True)

def save_snapshot(symbol, snapshot):
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"backend/data/snapshots_{symbol}_{date_str}.txt"
    with open(filename, "a", encoding="utf-8") as f:
        f.write(snapshot + "\n")

def save_csv(symbol, header, row, write_header=False):
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"backend/data/{symbol}_{date_str}.csv"
    file_exists = os.path.isfile(filename)
    with open(filename, "a", newline='', encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        if write_header and not file_exists:
            writer.writerow(header)
        writer.writerow(row)

def format_float(value):
    try:
        return f"{float(value):.2f}"
    except:
        return value

def worker(symbol, expiry_dates, stop_event):
    target_second = 20  # run every minute at xx:xx:20

    while not stop_event.is_set():
        try:
            timestamp = datetime.now().strftime("%d-%m-%Y %H:%M")
            parts = []
            header = []
            row = []

            # Fetch sensibull
            start_sensi = datetime.now()
            logging.info(f"[{symbol}] Sending request to Sensibull at {start_sensi.strftime('%H:%M:%S.%f')[:-3]}")
            sensi_data = sensibull_fetcher.fetch_data(symbol)
            end_sensi = datetime.now()
            elapsed_sensi = (end_sensi - start_sensi).total_seconds()
            logging.info(f"[{symbol}] Received Sensibull response at {end_sensi.strftime('%H:%M:%S.%f')[:-3]} (took {elapsed_sensi:.2f}s)")

            now_utc = datetime.utcnow()
            from_time = (now_utc - timedelta(minutes=10)).isoformat() + "Z"
            to_time = now_utc.isoformat() + "Z"

            for expiry in expiry_dates:
                ltp = format_float(sensi_data.get("ltp", 0))
                atm = sensi_data.get("atm", "N/A")
                stats = sensi_data['expiries'].get(expiry)

                # Straddle data
                straddle_data = straddle_fetcher.fetch_latest_straddle(symbol, expiry)
                straddle_price = format_float(straddle_data.get('straddle_price', 0)) if straddle_data else 'N/A'
                ce_price = format_float(straddle_data.get('ce_price', 0)) if straddle_data else 'N/A'
                pe_price = format_float(straddle_data.get('pe_price', 0)) if straddle_data else 'N/A'

                # OI data
                oi_data = straddle_fetcher.fetch_oi_data(symbol, expiry, from_time, to_time)
                call_oi = oi_data.get('call_oi', 0)
                put_oi = oi_data.get('put_oi', 0)
                chg_call_oi = oi_data.get('change_call_oi', 0)
                chg_put_oi = oi_data.get('change_put_oi', 0)
                net_oi_chg = chg_call_oi - chg_put_oi

                vix_close = format_float(sensibull_fetcher.fetch_vix_close()) or 0

                if stats:
                    call_vega = int(stats.get('total_call_vega', 0) * 10000)
                    put_vega = int(stats.get('total_put_vega', 0) * 10000)
                    call_theta = int(stats.get('total_call_theta', 0) * 10000)
                    put_theta = int(stats.get('total_put_theta', 0) * 10000)
                    call_delta = int(stats.get('total_call_delta', 0) * 10000)
                    put_delta = int(stats.get('total_put_delta', 0) * 10000)
                    #print(call_delta,put_delta)
                    vega_diff = call_vega - put_vega
                    theta_diff = call_theta - put_theta
                    delta_diff = call_delta + put_delta
                else:
                    call_vega = put_vega = call_theta = put_theta = call_delta = put_delta = delta_diff = vega_diff = theta_diff = 'N/A'
                
                #Net DEX Calculations
                net_dex = 0
                if stats and oi_data and "per_strike" in oi_data:
                    per_strike_deltas = stats.get("per_strike_deltas", {})
                    per_strike_oi = oi_data["per_strike"]

                    for strike_str, oi_vals in per_strike_oi.items():
                        try:
                            strike = int(strike_str)
                            #print(strike)
                        except:
                                continue

                        # Call leg
                        call_delta = per_strike_deltas.get((strike, "CE"), 0)
                        call_oi_strike = oi_vals.get("to_call_oi", 0)
                        #print(strike,call_delta,call_oi_strike)
                        net_dex += call_delta * call_oi_strike
                        #print(net_dex)
                        # Put leg
                        put_delta = per_strike_deltas.get((strike, "PE"), 0)
                        put_oi_strike = oi_vals.get("to_put_oi", 0)
                        net_dex += put_delta * put_oi_strike
                        #print(strike,net_dex)
                else:
                    net_dex = "N/A"

                header += [
                    "timestamp", "symbol", "Expiry", "LTP", "ATM", "Straddle", "CE", "PE",
                    "Net_OI_Chg", "VIX", "NET_DEX", "DeltaDiff", "VegaDiff", "ThetaDiff", "C_Delta", "P_Delta", "C_Vega", "P_Vega", "C_Theta", "P_Theta",
                    "C_OI", "P_OI", "C_Chg_OI", "P_Chg_OI"
                ]
                row += [
                    timestamp, symbol, expiry, ltp, atm, straddle_price, ce_price, pe_price,
                    net_oi_chg, vix_close, net_dex, delta_diff, vega_diff, theta_diff, call_delta, put_delta, call_vega, put_vega, call_theta, put_theta,
                    call_oi, put_oi, chg_call_oi, chg_put_oi
                ]

                part = (
                        f"| EXP:{expiry:<10} | LTP:{ltp:>8} | ATM:{atm:>6} | Straddle:{straddle_price:>8} | CE:{ce_price:>6} | PE:{pe_price:>6} "
                        f"| NetOI:{net_oi_chg:>8} | VIX:{vix_close:>5} | NetDEX:{net_dex:>10.2f}| DeltaDiff:{delta_diff:>8} | VegaDiff:{vega_diff:>8} | ThetaDiff:{theta_diff:>8} "
                        f"| C_Delta:{call_delta:>8} | P_Delta:{put_delta:>8} | P_Vega:{put_vega:>8} | C_Theta:{call_theta:>8} | P_Theta:{put_theta:>8} "
                        f"| C_OI:{call_oi:>8} | P_OI:{put_oi:>8} | C_Chg_OI:{chg_call_oi:>8} | P_Chg_OI:{chg_put_oi:>8} |"
                        )               
                parts.append(part)

            snapshot_line = f"| {timestamp} | {symbol:<9} " + " ".join(parts)
            logging.info(f"[{symbol}] Snapshot: {snapshot_line}")

            save_snapshot(symbol, snapshot_line)
            save_csv(symbol, header, row, write_header=True)

        except Exception as e:
            logging.error(f"[{symbol}] Error: {e}")

        # schedule next run
        now = datetime.now()
        if now.second < target_second:
            sleep_seconds = target_second - now.second
        else:
            sleep_seconds = 60 - now.second + target_second
        next_run = now + timedelta(seconds=sleep_seconds)
        logging.info(f"[{symbol}] Next run at {next_run.strftime('%H:%M:%S')} (sleeping {sleep_seconds}s)")
        stop_event.wait(sleep_seconds)

def index_worker(stop_event):
    target_second = 20
    while not stop_event.is_set():
        try:
            logging.info("[IndexWorker] Running index & stock fetcher...")
            fetch_and_save_index_prices(COOKIE_STRING)
        except Exception as e:
            logging.error(f"[IndexWorker] Error: {e}")

        now = datetime.now()
        if now.second < target_second:
            sleep_seconds = target_second - now.second
        else:
            sleep_seconds = 60 - now.second + target_second
        next_run = now + timedelta(seconds=sleep_seconds)
        logging.info(f"[IndexWorker] Next run at {next_run.strftime('%H:%M:%S')} (sleeping {sleep_seconds}s)")
        stop_event.wait(sleep_seconds)

if __name__ == "__main__":
    stop_event = threading.Event()

    index_thread = threading.Thread(target=index_worker, args=(stop_event,))
    index_thread.start()

    symbols_and_expiries = [
        ("NIFTY", ["2025-08-14", "2025-08-21"]),
        ("BANKNIFTY", ["2025-08-28"]),
        ("SENSEX", ["2025-08-12"]),
    ]
    threads = []
    for symbol, expiry_dates in symbols_and_expiries:
        t = threading.Thread(target=worker, args=(symbol, expiry_dates, stop_event))
        t.start()
        threads.append(t)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping gracefully...")
        stop_event.set()
        for t in threads:
            t.join()
        index_thread.join()
        print("All workers stopped.")