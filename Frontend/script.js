const COLORS = {
  ltp: "#1a5a99",
  ltp_ma: "#4682b4",
  net_oi: "#b40000",
  net_oi_ma: "#ce0707ff",
  net_dex: "#cf1c70ff",
  net_dex_ma: "#e20b9aff"
};
const DASHED = LightweightCharts.LineStyle.Dashed;
const INDICES = ["BANKNIFTY", "NIFTY", "SENSEX"];

// ===== TIME UTILITIES =====
function convertTimeToTS(timeStr) {
  // Always local day (Indian market hours)
  const today = new Date();
  const [hours, minutes] = timeStr.split(':').map(Number);
  const dt = new Date(today.getFullYear(), today.getMonth(), today.getDate(), hours, minutes);
  return Math.floor(dt.getTime() / 1000);
}

const seriesData = (arr, key) => {
  const map = new Map();
  arr.forEach(pt => {
    if (typeof pt[key] === 'number' && !isNaN(pt[key]) && pt.time) {
      const ts = convertTimeToTS(pt.time);
      map.set(ts, { time: ts, value: Number(pt[key]) });
    }
  });
  return Array.from(map.values()).sort((a, b) => a.time - b.time);
};

// ========= TABLE LOADING =======
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

    INDICES.forEach(symbol => {
      const lines = snapshots[symbol];
      const levels = levelsData[symbol];
      let ltp = 0;
      if (lines && lines.length > 0) {
        const latestLine = lines[lines.length - 1];
        ltp = extractFirstLTP(latestLine);
      }
      const row = document.createElement("tr");
      row.innerHTML = `
        <td><b>${symbol}</b></td>
        <td>-</td>
        <td>${ltp}</td>
        <td>-</td>
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

    const lastUpdatedElem = document.getElementById('lastUpdated');
    const timeString = new Date().toLocaleTimeString("en-IN", { hour12: false, timeZone: "Asia/Kolkata" });
    lastUpdatedElem.textContent = "Last updated: " + timeString;

  } catch (err) {
    console.error("Error loading data:", err);
  }
}

// ========== GENERALIZED DUAL AXIS CHART ===============
function createDualAxisChart({
  containerId,
  data,
  rightSeriesKey,
  rightSeriesMAKey,
  rightColor,
  rightColorMA,
  rightLabel,
  rightLabelMA
}) {
  const chartDiv = document.getElementById(containerId);
  if (!chartDiv) {
    console.error(`Chart container for ${containerId} not found`);
    return;
  }
  chartDiv.innerHTML = "";

  const chart = LightweightCharts.createChart(chartDiv, {
    height: chartDiv.clientHeight || 360,
    width: chartDiv.clientWidth || 540,
    timeScale: {
      timeVisible: true,
      secondsVisible: false,
      fixLeftEdge: true,
      fixRightEdge: true,
      rightOffset: 5,
      tickMarkFormatter: (time) => {
        const date = new Date(time * 1000);
        return date.toLocaleTimeString("en-IN", {
          hour12: false,
          hour: "2-digit",
          minute: "2-digit",
          timeZone: "Asia/Kolkata"
        });
      }
    },
    localization: {
      timeFormatter: (time) => {
        const date = new Date(time * 1000);
        return date.toLocaleTimeString("en-IN", {
          hour12: false,
          hour: "2-digit",
          minute: "2-digit",
          timeZone: "Asia/Kolkata"
        });
      }
    },
    layout: { background: { type: "solid", color: "#fff" }, textColor: "#111" },
    rightPriceScale: { visible: true, alignLabels: true, borderColor: rightColor },
    leftPriceScale: { visible: true, alignLabels: true, borderColor: COLORS.ltp },
    grid: {
      horzLines: { color: "#eee" },
      vertLines: { color: "#f6f6f6" }
    }
  });

  chart.priceScale("left").applyOptions({ scaleMargins: { top: 0.08, bottom: 0.08 } });
  chart.priceScale("right").applyOptions({ scaleMargins: { top: 0.08, bottom: 0.08 } });

  function convertData(data, key) {
    return data
      .map(d => {
        if (!d.time) return null;
        const [hh, mm] = String(d.time).split(":").map(Number);
        const dateObj = new Date();
        dateObj.setHours(hh, mm, 0, 0);
        return { time: convertTimeToTS(d.time), value: d[key] };
      })
      .filter(pt => pt && pt.value != null && pt.value !== 0)
      .sort((a, b) => a.time - b.time)
      .filter((pt, idx, arr) => idx === 0 || pt.time > arr[idx - 1].time);
  }

  const ltpData = convertData(data, "ltp");
  const ltpMAData = convertData(data, "ltp_ma");
  const rightData = convertData(data, rightSeriesKey);
  const rightMAData = convertData(data, rightSeriesMAKey);

  chart.addLineSeries({ priceScaleId: "left", color: COLORS.ltp, lineWidth: 2 }).setData(ltpData);
  chart.addLineSeries({ priceScaleId: "left", color: COLORS.ltp_ma, lineWidth: 2, lineStyle: DASHED }).setData(ltpMAData);
  chart.addLineSeries({ priceScaleId: "right", color: rightColor, lineWidth: 2 }).setData(rightData);
  chart.addLineSeries({ priceScaleId: "right", color: rightColorMA, lineWidth: 2, lineStyle: DASHED }).setData(rightMAData);

  // --- ALWAYS 09:15 to 15:30 IST as visible range ---
  const today = new Date();
  const start = Math.floor(new Date(today.getFullYear(), today.getMonth(), today.getDate(), 9, 15).getTime() / 1000);
  const end = Math.floor(new Date(today.getFullYear(), today.getMonth(), today.getDate(), 15, 30).getTime() / 1000);
  chart.timeScale().setVisibleRange({
    from: start,
    to: end
  });

  // ========== CUSTOM LEGEND =========
  chartDiv.insertAdjacentHTML(
    "beforeend",
    `<div class="custom-legend" style="margin-top: 8px; font-size:14px">
      <span style="color:${COLORS.ltp};font-weight:bold;">━ LTP</span>
      <span style="color:${COLORS.ltp_ma};font-weight:bold;">╌ LTP MA</span>
      <span style="color:${rightColor};font-weight:bold;margin-left:16px;">━ ${rightLabel}</span>
      <span style="color:${rightColorMA};font-weight:bold;">╌ ${rightLabelMA}</span>
      <span style="color:#444;margin-left:16px;">
        (Left Y: LTP, Right Y: ${rightLabel})
      </span>
    </div>`
  );
}

// =========== LOAD ALL CHARTS =============
async function loadAllCharts() {
  try {
    const res = await fetch("http://127.0.0.1:5000/api/chartdata");
    const data = await res.json();

    INDICES.forEach(symbol => {
      // OI Chart
      createDualAxisChart({
        containerId: `chart_${symbol}_OI`,
        data: data[symbol] || [],
        rightSeriesKey: "net_oi_change",
        rightSeriesMAKey: "net_oi_ma",
        rightColor: COLORS.net_oi,
        rightColorMA: COLORS.net_oi_ma,
        rightLabel: "Net OI",
        rightLabelMA: "Net OI MA"
      });

      // DEX Chart
      createDualAxisChart({
        containerId: `chart_${symbol}_DEX`,
        data: data[symbol] || [],
        rightSeriesKey: "net_dex",
        rightSeriesMAKey: "net_dex_ma",
        rightColor: COLORS.net_dex,
        rightColorMA: COLORS.net_dex_ma,
        rightLabel: "Net Dex",
        rightLabelMA: "Net Dex MA"
      });
    });
  } catch (e) {
    console.error("Chart load error:", e);
  }
}

// ========== EXTRACT/HELPERS FOR TABLE ==========
function extractFirstLTP(text) {
  try {
    const parts = text.split("LTP:");
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

// ========== NAVBAR GAP FIX ======
document.addEventListener("DOMContentLoaded", function () {
  function adjustPadding() {
    const navbar = document.querySelector(".navbar");
    if (navbar) {
      const navHeight = navbar.offsetHeight;
      document.body.style.paddingTop = navHeight + "px";
      const firstSection = document.querySelector("section.container");
      if (firstSection) firstSection.style.marginTop = "20px";
    }
  }
  adjustPadding();
  window.addEventListener("resize", adjustPadding);
});

// ==== WINDOW RESIZE: (Optional) Add Chart Resize Logic If Needed =====


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
  refreshAll();
};
