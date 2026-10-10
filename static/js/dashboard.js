/**
 * dashboard.js — Shared UI utilities for FraudShield AI
 * AI-Based Online Payment Fraud Detection System
 */

'use strict';

// ── Dismiss alerts after 6 seconds ─────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.alert-dismissible').forEach(alert => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) bsAlert.close();
    }, 6000);
  });

  // Animate stat card values
  animateCounters();

  // Initialise risk score bars width (CSS transition trigger)
  requestAnimationFrame(() => {
    document.querySelectorAll('.risk-score-fill').forEach(el => {
      const w = el.style.width;
      el.style.width = '0';
      requestAnimationFrame(() => { el.style.width = w; });
    });
  });
});

// ── Animate counter values ──────────────────────────
function animateCounters() {
  document.querySelectorAll('.stat-value').forEach(el => {
    const target = parseInt(el.textContent.replace(/[^\d]/g, ''), 10);
    if (isNaN(target) || target === 0) return;
    const duration = 800;
    const step = Math.ceil(target / (duration / 16));
    let current = 0;
    const prefix = el.textContent.match(/^[^\d]*/)?.[0] || '';
    const suffix = el.textContent.match(/[^\d]*$/)?.[0] || '';
    const timer = setInterval(() => {
      current = Math.min(current + step, target);
      el.textContent = prefix + current.toLocaleString('en-IN') + suffix;
      if (current >= target) clearInterval(timer);
    }, 16);
  });
}

// ── Copy TX ID to clipboard ─────────────────────────
function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    showToast('Copied: ' + text, 'success');
  }).catch(() => {
    showToast('Could not copy', 'danger');
  });
}

// ── Simple toast notification ───────────────────────
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer') || createToastContainer();
  const id = 'toast_' + Date.now();
  const icons = { success:'check-circle', danger:'exclamation-triangle', info:'info-circle', warning:'exclamation-circle' };
  const toast = document.createElement('div');
  toast.id = id;
  toast.className = `toast align-items-center text-bg-${type} border-0`;
  toast.setAttribute('role', 'alert');
  toast.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">
        <i class="bi bi-${icons[type] || 'info-circle'} me-2"></i>${message}
      </div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
    </div>`;
  container.appendChild(toast);
  new bootstrap.Toast(toast, { delay: 4000 }).show();
  toast.addEventListener('hidden.bs.toast', () => toast.remove());
}

function createToastContainer() {
  const c = document.createElement('div');
  c.id = 'toastContainer';
  c.className = 'toast-container position-fixed bottom-0 end-0 p-3';
  c.style.zIndex = '1100';
  document.body.appendChild(c);
  return c;
}

// ── Risk level colour helper ────────────────────────
function getRiskColor(level) {
  const map = { LOW:'#3fb950', MEDIUM:'#d29922', HIGH:'#f0883e', CRITICAL:'#f85149' };
  return map[level] || '#7d8590';
}

// ── Format currency (Indian Rupee) ──────────────────
function formatINR(amount) {
  return '₹' + parseFloat(amount).toLocaleString('en-IN', { maximumFractionDigits: 0 });
}

// ── Debounce helper ─────────────────────────────────
function debounce(fn, delay = 300) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

// ── Search input debounce for history page ──────────
const searchInput = document.querySelector('input[name="search"]');
if (searchInput) {
  const form = searchInput.closest('form');
  searchInput.addEventListener('input', debounce(() => {
    if (form) form.submit();
  }, 500));
}
