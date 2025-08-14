const SYMBOLS = ["BANKNIFTY", "NIFTY", "SENSEX"];
const COLORS = {
  ltp: '#1a5a99',        // Blue solid
  ltp_ma: '#1a5a99',     // Blue dashed
  net_oi: '#b40000',     // Red solid
  net_oi_ma: '#b40000',  // Red dashed
};

const DASHED = LightweightCharts.LineStyle.Dashed;

// ---------- Convert API "HH:MM" to UNIX timestamp seconds ----------
function convertTimeToTS(timeStr) {
  const today = new Date();
  const [hours, minutes] = timeStr.split(':').map(Number);
  const dt = new Date(today.getFullYear(), today.getMonth(), today.getDate(), hours, minutes);
  return Math.floor(dt.getTime() / 1000); // seconds since epoch
}

// ---------- Prepare chart series data (dedupe + sort) ----------
const seriesData = (arr, key) => {
  const map = new Map();

  arr.forEach(pt => {
    if (typeof pt[key] === 'number' && !isNaN(pt[key]) && pt.time) {
      const ts = convertTimeToTS(pt.time);
      map.set(ts, { time: ts, value: Number(pt[key]) }); // overwrite if duplicate
    }
  });

  return Array.from(map.values()).sort((a, b) => a.time - b.time);
};

// ---------- Table/Levels Load ----------
async function loadData() {
  try {
    const [snapRes, niftyRes, bankniftyRes, sensexRes] = await Promise.all([
      fetch('http://127.0.0.1:5000/api/snapshots'),
      fetch('http://127.0.0.1:5000/api/levels/levels_NIFTY_50.json'),
      fetch('http://127.0.0.1:5000/api/levels/levels_NIFTY_BANK.json'),
      fetch('http://127.0.0.1:5000/api/levels/levels_SENSEX.json')
    ]);

    const snapshots = await snapRes.json();
    const levelsData = {
      NIFTY: await niftyRes.json(),
      BANKNIFTY: await bankniftyRes.json(),
      SENSEX: await sensexRes.json()
    };

    const tbody = document.querySelector("#dataTable tbody");
    tbody.innerHTML = "";

    const indices = ["NIFTY", "BANKNIFTY", "SENSEX"];
    indices.forEach(symbol => {
      const lines = snapshots[symbol];
      const levels = levelsData[symbol];
      let ltp = 0;
      if (lines && lines.length > 0) {
        const latestLine = lines[lines.length - 1];
        ltp = extractFirstLTP(latestLine);
      }
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${symbol}</td>
        <td>-</td>
        <td>${ltp}</td>
        <td>-</td>
        <td>-</td>
        <td>-</td>
        <td>-</td>
        <td class="${color(levels.PDH, ltp)}">${status(levels.PDH, ltp)}</td>
        <td class="${color(levels.PDL, ltp)}">${status(levels.PDL, ltp)}</td>
        <td class="${color(levels.CWH, ltp)}">${status(levels.CWH, ltp)}</td>
        <td class="${color(levels.CWL, ltp)}">${status(levels.CWL, ltp)}</td>
        <td class="${color(levels.PWH, ltp)}">${status(levels.PWH, ltp)}</td>
        <td class="${color(levels.PWL, ltp)}">${status(levels.PWL, ltp)}</td>
        <td class="${color(levels.PMH, ltp)}">${status(levels.PMH, ltp)}</td>
        <td class="${color(levels.PML, ltp)}">${status(levels.PML, ltp)}</td>
      `;
      tbody.appendChild(row);
    });

    document.getElementById('lastUpdated').textContent =
      "Last updated: " + new Date().toLocaleTimeString();

  } catch (err) {
    console.error("Error loading data:", err);
  }
}

// ---------- Chart Section: Dual Y-Axis for Each Symbol ----------
function timeStringToUnix(timeStr) {
    const [hours, minutes] = timeStr.split(":").map(Number);
    const now = new Date();
    now.setHours(hours, minutes, 0, 0);
    return Math.floor(now.getTime() / 1000);
}
function createDualAxisChart(symbol, data) {
    const chartDiv = document.getElementById(`chart_${symbol}`);
    if (!chartDiv) {
        console.error(`Chart container for ${symbol} not found`);
        return;
    }
    chartDiv.innerHTML = "";

    const chart = LightweightCharts.createChart(chartDiv, {
        height: chartDiv.clientHeight || 530,
        width: chartDiv.clientWidth || 1300,
        timeScale: {
            timeVisible: true,
            secondsVisible: false,
            fixLeftEdge: true,
            fixRightEdge: true,
            rightOffset: 5,
            tickMarkFormatter: (time) => {
                const date = new Date(time * 1000);
                return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
            }
        },
          localization: {
            timeFormatter: (time) => {
                const date = new Date(time * 1000);
                return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
        }
    },
        layout: { background: { type: 'solid', color: '#fff' }, textColor: '#111' },
        rightPriceScale: { visible: true, alignLabels: true, borderColor: COLORS.net_oi },
        leftPriceScale: { visible: true, alignLabels: true, borderColor: COLORS.ltp },
        grid: {
            horzLines: { color: '#eee' },
            vertLines: { color: '#f6f6f6' }
        }
    });

    chart.priceScale('left').applyOptions({ scaleMargins: { top: 0.1, bottom: 0.1 } });
    chart.priceScale('right').applyOptions({ scaleMargins: { top: 0.1, bottom: 0.1 } });

    function convertData(data, key) {
        const today = new Date();
        let converted = data.map(d => {
            if (!d.time) return null; // skip if no time
            const [hh, mm] = String(d.time).split(':').map(Number);
            const dateObj = new Date(today.getFullYear(), today.getMonth(), today.getDate(), hh, mm);
            return {
                time: Math.floor(dateObj.getTime() / 1000),
                value: d[key]
            };
        }).filter(pt => pt && pt.value != null && pt.value !== 0);

        converted.sort((a, b) => a.time - b.time);

        return converted.filter((pt, idx, arr) => idx === 0 || pt.time > arr[idx - 1].time);
    }

    const ltpData = convertData(data, "ltp");
    const ltpMAData = convertData(data, "ltp_ma");
    const netOIData = convertData(data, "net_oi_change");
    const netOIMAData = convertData(data, "net_oi_ma");

    chart.addLineSeries({ priceScaleId: 'left', color: COLORS.ltp, lineWidth: 2 }).setData(ltpData);
    chart.addLineSeries({ priceScaleId: 'left', color: COLORS.ltp_ma, lineWidth: 2, lineStyle: DASHED }).setData(ltpMAData);
    chart.addLineSeries({ priceScaleId: 'right', color: COLORS.net_oi, lineWidth: 2 }).setData(netOIData);
    chart.addLineSeries({ priceScaleId: 'right', color: COLORS.net_oi_ma, lineWidth: 2, lineStyle: DASHED }).setData(netOIMAData);

    // Only set visible range if there is valid data
    const allTimes = [...ltpData, ...netOIData].map(p => p.time);
    if (allTimes.length > 0) {
        const minTime = Math.min(...allTimes);
        const maxTime = Math.max(...allTimes);

        const today = new Date();
        const start = Math.floor(new Date(today.getFullYear(), today.getMonth(), today.getDate(), 9, 15).getTime() / 1000);
        const end = Math.floor(new Date(today.getFullYear(), today.getMonth(), today.getDate(), 15, 30).getTime() / 1000);

        chart.timeScale().setVisibleRange({
            from: Math.max(start, minTime),
            to: Math.min(end, maxTime)
        });
    }

    chartDiv.insertAdjacentHTML(
        'beforeend',
        `<div class="custom-legend" style="margin-top: 8px; font-size:14px">
            <span style="color:${COLORS.ltp};font-weight:bold;">━ LTP</span>
            <span style="color:${COLORS.ltp_ma};font-weight:bold;">╌ LTP MA</span>
            <span style="color:${COLORS.net_oi};font-weight:bold;margin-left:16px;">━ Net OI</span>
            <span style="color:${COLORS.net_oi_ma};font-weight:bold;">╌ Net OI MA</span>
            <span style="color:#444;margin-left:16px;">(Left Y: LTP, Right Y: Net OI)</span>
        </div>`
    );
}


// -------- LOAD ALL CHARTS BASED ON BACKEND DATA --------
async function loadAllCharts() {
  try {
    const res = await fetch('http://127.0.0.1:5000/api/chartdata');
    const data = await res.json();
    SYMBOLS.forEach(symbol => createDualAxisChart(symbol, data[symbol] || []));
  } catch (e) {
    console.error("Chart load error:", e);
  }
}

// --------- Utility Functions ----------
function extractFirstLTP(text) {
  try {
    const parts = text.split('LTP:');
    for (let i = 1; i < parts.length; i++) {
      const after = parts[i].trim();
      const numberStr = after.split(/[\s|]+/)[0];
      const num = parseFloat(numberStr);
      if (!isNaN(num) && num > 0) return num;
    }
  } catch (e) {
    console.error("Error extracting LTP:", e);
  }
  return 0;
}

function status(level, ltp) {
  if (typeof level !== "number" || ltp === 0) return "-";
  return ltp > level ? "ABOVE" : "BELOW";
}

function color(level, ltp) {
  if (typeof level !== "number" || ltp === 0) return "";
  return ltp > level ? "above" : "below";
}

// ---------- Refresh Everything with precise 30-second interval ----------
function scheduleRefresh() {
  const now = new Date();
  const seconds = now.getSeconds();
  const delay = (30 - (seconds % 30)) * 1000 - now.getMilliseconds();

  setTimeout(() => {
    refreshAll();
    setInterval(refreshAll, 30000);
  }, delay);
}

function refreshAll() {
  loadData();
  loadAllCharts();
}

window.onload = () => {
  scheduleRefresh();
  refreshAll(); // Initial immediate load
};
