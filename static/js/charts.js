/**
 * CashPilot Charts Module
 * Initializes and manages Chart.js visualisations for:
 * 1. Monthly Income & Expense Bar Chart (Dashboard)
 * 2. 30/60/90-Day Cash Flow Forecast Area Chart
 * 3. What-If Scenario Comparison Chart (Baseline vs Delay)
 */

let incomeExpenseChart = null;
let cashForecastChart = null;
let whatifComparisonChart = null;

/**
 * Renders or updates the Monthly Income vs Expenses Chart on the Dashboard.
 * @param {Array<string>} labels - Month names (e.g. ['Jun 2026', 'Jul 2026', ...])
 * @param {Array<number>} income - Monthly tuition collected
 * @param {Array<number>} expenses - Monthly overhead expenses paid
 */
function renderIncomeExpenseChart(labels, income, expenses) {
  const canvas = document.getElementById("incomeExpenseChart");
  if (!canvas) return;

  if (incomeExpenseChart) {
    incomeExpenseChart.destroy();
  }

  const ctx = canvas.getContext("2d");

  // Chart gradient accents
  const incomeGradient = ctx.createLinearGradient(0, 0, 0, 300);
  incomeGradient.addColorStop(0, "#10b981");
  incomeGradient.addColorStop(1, "rgba(16, 185, 129, 0.4)");

  const expenseGradient = ctx.createLinearGradient(0, 0, 0, 300);
  expenseGradient.addColorStop(0, "#6366f1");
  expenseGradient.addColorStop(1, "rgba(99, 102, 241, 0.4)");

  incomeExpenseChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Tuition Inflow ($)",
          data: income,
          backgroundColor: incomeGradient,
          borderRadius: 6,
          barPercentage: 0.65,
          categoryPercentage: 0.7
        },
        {
          label: "Overhead Outflow ($)",
          data: expenses,
          backgroundColor: expenseGradient,
          borderRadius: 6,
          barPercentage: 0.65,
          categoryPercentage: 0.7
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "top",
          align: "end",
          labels: {
            boxWidth: 12,
            boxHeight: 12,
            usePointStyle: true,
            pointStyle: "circle",
            font: { family: "Inter", size: 12, weight: "600" }
          }
        },
        tooltip: {
          backgroundColor: "#0f172a",
          titleFont: { family: "Inter", size: 13, weight: "700" },
          bodyFont: { family: "Inter", size: 12 },
          padding: 12,
          cornerRadius: 8,
          callbacks: {
            label: function(context) {
              return ` ${context.dataset.label}: $${context.parsed.y.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
            }
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { font: { family: "Inter", size: 11.5, weight: "500" }, color: "#64748b" }
        },
        y: {
          grid: { color: "#f1f5f9", drawBorder: false },
          ticks: {
            font: { family: "Inter", size: 11.5 },
            color: "#64748b",
            callback: function(val) { return "$" + val; }
          }
        }
      }
    }
  });
}

/**
 * Renders the 30/60/90 Day Cash Flow Trajectory Chart.
 * Includes a gradient fill and the Emergency Safety Reserve Line.
 * @param {Array<Object>} timeline - Daily timeline items {label, balance, safety_buffer, etc.}
 * @param {number} horizonDays - 30, 60, or 90 days
 */
function renderCashForecastChart(timeline, horizonDays = 30) {
  const canvas = document.getElementById("cashForecastChart");
  if (!canvas) return;

  if (cashForecastChart) {
    cashForecastChart.destroy();
  }

  // Filter timeline slice to requested horizon
  const sliced = timeline.slice(0, horizonDays + 1);
  const labels = sliced.map(t => t.label);
  const balances = sliced.map(t => t.balance);
  const safetyBuffer = sliced.length > 0 ? sliced[0].safety_buffer : 1000;
  const safetyData = sliced.map(() => safetyBuffer);

  const ctx = canvas.getContext("2d");
  const fillGradient = ctx.createLinearGradient(0, 0, 0, 320);
  fillGradient.addColorStop(0, "rgba(99, 102, 241, 0.25)");
  fillGradient.addColorStop(1, "rgba(99, 102, 241, 0.0)");

  cashForecastChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Projected Cash Balance",
          data: balances,
          borderColor: "#4f46e5",
          borderWidth: 2.5,
          backgroundColor: fillGradient,
          fill: true,
          tension: 0.3,
          pointRadius: sliced.length > 40 ? 0 : 3,
          pointHoverRadius: 6,
          pointBackgroundColor: "#4f46e5"
        },
        {
          label: "Safety Reserve Reserve ($" + safetyBuffer + ")",
          data: safetyData,
          borderColor: "#ef4444",
          borderWidth: 1.8,
          borderDash: [5, 5],
          fill: false,
          pointRadius: 0
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          position: "top",
          align: "end",
          labels: {
            boxWidth: 14,
            usePointStyle: true,
            font: { family: "Inter", size: 12, weight: "600" }
          }
        },
        tooltip: {
          backgroundColor: "#0f172a",
          titleFont: { family: "Inter", size: 13, weight: "700" },
          padding: 12,
          cornerRadius: 8,
          callbacks: {
            label: function(context) {
              return ` ${context.dataset.label}: $${context.parsed.y.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
            }
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: {
            maxTicksLimit: 10,
            font: { family: "Inter", size: 11.5 },
            color: "#64748b"
          }
        },
        y: {
          grid: { color: "#f1f5f9" },
          ticks: {
            font: { family: "Inter", size: 11.5 },
            color: "#64748b",
            callback: function(val) { return "$" + val; }
          }
        }
      }
    }
  });
}

/**
 * Renders the What-If Comparison Chart showing the original baseline
 * vs the simulated late payment trajectory.
 * @param {Array<Object>} comparisonTimeline - List with {label, base_balance, simulated_balance, safety_buffer}
 */
function renderWhatIfComparisonChart(comparisonTimeline) {
  const canvas = document.getElementById("whatifComparisonChart");
  if (!canvas) return;

  if (whatifComparisonChart) {
    whatifComparisonChart.destroy();
  }

  // Sample to first 45 days for optimal visibility of the delay window
  const sliced = comparisonTimeline.slice(0, 46);
  const labels = sliced.map(t => t.label);
  const baseData = sliced.map(t => t.base_balance);
  const simData = sliced.map(t => t.simulated_balance);
  const safetyBuffer = sliced.length > 0 ? sliced[0].safety_buffer : 1000;

  const ctx = canvas.getContext("2d");

  whatifComparisonChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Baseline Plan (On-Time)",
          data: baseData,
          borderColor: "#10b981",
          borderWidth: 2,
          fill: false,
          tension: 0.25,
          pointRadius: 2,
          pointHoverRadius: 5
        },
        {
          label: "Simulated Delay (Late Payment)",
          data: simData,
          borderColor: "#ef4444",
          borderWidth: 2.5,
          backgroundColor: "rgba(239, 68, 68, 0.08)",
          fill: true,
          tension: 0.25,
          pointRadius: 3,
          pointHoverRadius: 6
        },
        {
          label: "Safety Reserve ($" + safetyBuffer + ")",
          data: sliced.map(() => safetyBuffer),
          borderColor: "#94a3b8",
          borderWidth: 1.5,
          borderDash: [4, 4],
          fill: false,
          pointRadius: 0
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          position: "top",
          align: "end",
          labels: {
            boxWidth: 12,
            usePointStyle: true,
            font: { family: "Inter", size: 12, weight: "600" }
          }
        },
        tooltip: {
          backgroundColor: "#0f172a",
          padding: 12,
          cornerRadius: 8,
          callbacks: {
            label: function(context) {
              return ` ${context.dataset.label}: $${context.parsed.y.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
            }
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { maxTicksLimit: 12, font: { family: "Inter", size: 11.5 }, color: "#64748b" }
        },
        y: {
          grid: { color: "#f1f5f9" },
          ticks: {
            font: { family: "Inter", size: 11.5 },
            color: "#64748b",
            callback: function(val) { return "$" + val; }
          }
        }
      }
    }
  });
}
