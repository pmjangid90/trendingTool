# backend/server.py
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import os
import datetime
import csv

app = Flask(__name__)
CORS(app)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
date_str = datetime.now().strftime("%Y-%m-%d")
SNAPSHOT_FILES = {
    "NIFTY": f"snapshots_NIFTY_{date_str}.txt",
    "BANKNIFTY": f"snapshots_BANKNIFTY_{date_str}.txt",
    "SENSEX": f"snapshots_SENSEX_{date_str}.txt"
}

# Map index name to today's CSV filename


CSV_FILES = {
      "BANKNIFTY": f"Sentiments_BANKNIFTY_{datetime.datetime.now().strftime('%d%b')}.csv",
      "NIFTY": f"Sentiments_NIFTY_{datetime.datetime.now().strftime('%d%b')}.csv",
      "SENSEX": f"Sentiments_SENSEX_{datetime.datetime.now().strftime('%d%b')}.csv"
}
@app.route("/api/snapshots")
def get_snapshots():
    """
    Return all snapshots from individual text files.
    """
    all_snapshots = {}
    for index_name, filename in SNAPSHOT_FILES.items():
        file_path = os.path.join(DATA_DIR, filename)
        snapshots = []

        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        snapshots.append(line)
        else:
            print(f"Data file not found: {file_path}")

        all_snapshots[index_name] = snapshots

    return jsonify(all_snapshots)

@app.route("/api/levels/<filename>")
def get_levels(filename):
    """
    Serve levels JSON files directly, e.g. levels_NIFTY_50.json, levels_BANKNIFTY.json, levels_SENSEX.json
    """
    return send_from_directory(DATA_DIR, filename)

@app.route("/api/ohlc/<filename>")
def get_ohlc(filename):
    ohlc_folder = os.path.join(DATA_DIR, "ohlc")
    full_path = os.path.join(ohlc_folder, filename)
    print("Looking for file:", full_path)
    return send_from_directory(ohlc_folder, filename)

def safe_float(value, default=0.0):
    try:
        if value is None or value.strip() == "":
            return default
        return float(value)
    except ValueError:
        return default

@app.route("/api/chartdata")
def get_chartdata():
    chart_data = {}

    for index_name, filename in CSV_FILES.items():
        file_path = os.path.join(DATA_DIR, filename)
        data_points = []

        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ts_str = row.get("timestamp") or row.get("time")
                    try:
                        # If your CSV time has a date
                        dt = datetime.datetime.strptime(ts_str, "%d-%m-%Y %H:%M")
                        time_fmt = dt.strftime("%H:%M")
                    except Exception:
                        time_fmt = ts_str

                    data_points.append({
                        "time": time_fmt,
                        "ltp": safe_float(row.get("ltp")),
                        "ltp_ma": safe_float(row.get("ltp_ma")),
                        "net_oi_change": safe_float(row.get("net_oi_change")),
                        "net_oi_ma": safe_float(row.get("net_oi_ma")),
                        "net_dex": safe_float(row.get("net_dex")),
                        "net_dex_ma": safe_float(row.get("net_dex_ma"))                        
                    })

            data_points.sort(key=lambda x: x["time"])
        else:
            print(f"CSV file not found: {file_path}")

        chart_data[index_name] = data_points

    return jsonify(chart_data)


if __name__ == "__main__":
    app.run(port=5000, debug=True)
