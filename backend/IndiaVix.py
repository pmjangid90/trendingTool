import requests
import pandas as pd
import urllib3
import os

# Disable SSL warnings (only for dev; remove in prod)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        

url = f"https://oxide.sensibull.com/v1/compute/candles/INDIAVIX"
COOKIE_STRING = "_ga=GA1.1.552304479.1724843613; sb_rudder_utm={}; rl_page_init_referrer=RudderEncrypt%3AU2FsdGVkX18xqnYBb%2B%2BpcG%2BAMoPU6KkB8XiTkY%2FHPmBnf23V13kM2yD36Px7D29%2F; rl_page_init_referring_domain=RudderEncrypt%3AU2FsdGVkX19uZNPb2yjsbSXxP13M2EYO1VdzfRVcqdtcE%2FKmo4TZyC92Oc1HK6JR; _cfuvid=bcdQjiGd2rc1eeoc2ljAu.fRYG2i3O8RfjtFAhaC6bg-1753278747834-0.0.1.1-604800000; _clck=1pn399u%7C2%7Cfxv%7C0%7C1701; _clsk=gzofr2%7C1753332215772%7C1%7C1%7Ca.clarity.ms%2Fcollect; bkd_ref=iiWK2VQZZQVeJjUx; access_token=cKyLJna7Gz0aoBlLAk1lwFHQoHIcWdpKcTRsGrqcw-U; rl_anonymous_id=RudderEncrypt%3AU2FsdGVkX1%2FnqoPXjE%2FHwTNwCMcqJCjLbSbuV%2Bqt8iQA6O5HLKBohgRFhAIyO8nnc11DehpzaNGPqawkcX6Qvw%3D%3D; rl_user_id=RudderEncrypt%3AU2FsdGVkX1%2FtKcuxePUeIuyzSGjsSt0fbdIalpsp2%2FScepemgvD%2BWNPFQcDzZgCXkgMG8SQ%2F1Z7Ql0YPzLje7g%3D%3D; rl_trait=RudderEncrypt%3AU2FsdGVkX18BILMaOomm5IL8wV0u%2Fb1Uz1a7g4Ot825auoIXIX6Snkn3EAtNQdvZN4OwKwUfczCCYQn9yXPuAJGF5%2FbKaD%2F9PMS%2FvQaBU7lNECVHk0c8yKujR04eYDI4l3DALsd6Fcpg5E5hUUc11tz4GCKetszjHYXUsVFowDzOAfuYGqHx5%2FdzXioDs%2FGsR%2FTp%2BJ5YqI3TGOqN%2FwgJU2cxwlRh6YhrVbZVG2vZTYlYDHvX30VXuWjiBXh7X1clZb%2Fjw7kLUFEbMhWbUKBc9g%3D%3D; _ga_NC7XJTRTDX=GS2.1.s1753332217$o4$g1$t1753332271$j6$l0$h0; rl_session=RudderEncrypt%3AU2FsdGVkX19IlCwFLXrIYYOOf432qrNuvRcFw4wZU4JIMllmRi%2BDkIa3qwaNKQfPrcHIpc%2FAkseUHACrGao30%2FjP6b0%2BiZTHDYtDPfOQRxj0rGtnrg6fjn69R9puAthAdg%2F%2F6Fig8rOxLOMAkHeZyA%3D%3D"   # replace with actual cookie
  # replace with actual cookie

cookies = dict(x.strip().split("=", 1) for x in COOKIE_STRING.split("; "))

cookies = dict(x.strip().split("=", 1) for x in COOKIE_STRING.split("; "))

# Prepare payload for 1-minute candles from 30 July to 31 July 2025
payload = {
    "from_date": "2025-07-30",
    "to_date": "2025-07-31",
    "interval": "1M",
    "skip_last_ts": False
}

try:
    response = requests.post(url, json=payload, cookies=cookies, timeout=10, verify=False)
    response.raise_for_status()
    raw = response.json()

    # Extract candles
    payload_data = raw.get('payload', {})
    candles = payload_data.get('candles', [])

    print(f"\n✅ Total candles fetched: {len(candles)}")

    if candles:
        df = pd.DataFrame(candles)
        df.rename(columns={'ts': 'timestamp'}, inplace=True)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Show sample
        print("\n📊 Sample data:")
        print(df.head())

        # Create data folder if doesn't exist
        os.makedirs('data', exist_ok=True)

        # Save to CSV
        filename = f"data/india_vix_.csv"
        df.to_csv(filename, index=False)
        print(f"\n✅ Data saved to: {filename}")

    else:
        print("⚠ No candles data found")

except Exception as e:
    print(f"❌ Error fetching data for INDIAVIX: {e}")
