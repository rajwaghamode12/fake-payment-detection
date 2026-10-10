/**
 * charts.js — Chart.js global defaults for FraudShield AI
 * AI-Based Online Payment Fraud Detection System
 *
 * Imported by base.html — sets global Chart.js defaults so
 * every chart in every template inherits the dark theme.
 */

'use strict';

// ── Chart.js Global Defaults ────────────────────────
Chart.defaults.color            = '#7d8590';
Chart.defaults.font.family      = "'Inter', sans-serif";
Chart.defaults.font.size        = 11;
Chart.defaults.plugins.legend.labels.boxWidth = 12;
Chart.defaults.plugins.legend.labels.padding  = 14;
Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(22,27,34,0.95)';
Chart.defaults.plugins.tooltip.borderColor     = '#30363d';
Chart.defaults.plugins.tooltip.borderWidth     = 1;
Chart.defaults.plugins.tooltip.padding         = 10;
Chart.defaults.plugins.tooltip.titleColor      = '#e6edf3';
Chart.defaults.plugins.tooltip.bodyColor       = '#8d96a0';
Chart.defaults.plugins.tooltip.cornerRadius    = 6;

// ── Shared palette ──────────────────────────────────
const COLORS = {
  accent:   '#58a6ff',
  success:  '#3fb950',
  warning:  '#d29922',
  high:     '#f0883e',
  danger:   '#f85149',
  muted:    '#7d8590',
  purple:   '#a371f7',
  grid:     'rgba(255,255,255,0.05)',
  border:   '#30363d',
};

// ── Axis defaults helper ─────────────────────────────
function darkAxes(opts = {}) {
  return {
    x: { ticks: { color: COLORS.muted }, grid: { color: COLORS.grid }, ...opts.x },
    y: { ticks: { color: COLORS.muted }, grid: { color: COLORS.grid }, beginAtZero: true, ...opts.y },
  };
}

// ── Build a generic bar chart ────────────────────────
function buildBarChart(canvasId, labels, datasets, opts = {}) {
  const el = document.getElementById(canvasId);
  if (!el) return null;
  return new Chart(el, {
    type: 'bar',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: datasets.length > 1 } },
      scales: darkAxes(opts.axes || {}),
      ...opts.extra,
    },
  });
}

// ── Build a generic line chart ───────────────────────
function buildLineChart(canvasId, labels, datasets, opts = {}) {
  const el = document.getElementById(canvasId);
  if (!el) return null;
  return new Chart(el, {
    type: 'line',
    data: { labels, datasets: datasets.map(d => ({
        fill: true, tension: 0.4, pointRadius: 3,
        pointBackgroundColor: d.borderColor, ...d })) },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: COLORS.muted } } },
      scales: darkAxes(opts.axes || {}),
      ...opts.extra,
    },
  });
}

// ── Build a doughnut chart ───────────────────────────
function buildDoughnutChart(canvasId, labels, data, backgroundColors) {
  const el = document.getElementById(canvasId);
  if (!el) return null;
  return new Chart(el, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: backgroundColors,
        borderColor: '#161b22',
        borderWidth: 3,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '65%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: COLORS.muted, font: { size: 11 }, boxWidth: 12, padding: 12 },
        },
      },
    },
  });
}

// ── Risk score gradient fill ─────────────────────────
function riskGradient(ctx, score) {
  const g = ctx.createLinearGradient(0, 0, 300, 0);
  if (score <= 25)       { g.addColorStop(0, '#3fb950'); g.addColorStop(1, '#56d364'); }
  else if (score <= 50)  { g.addColorStop(0, '#d29922'); g.addColorStop(1, '#e3b341'); }
  else if (score <= 75)  { g.addColorStop(0, '#f0883e'); g.addColorStop(1, '#ffa657'); }
  else                   { g.addColorStop(0, '#f85149'); g.addColorStop(1, '#ff7b72'); }
  return g;
}
