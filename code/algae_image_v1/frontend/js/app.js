/**
 * Algae Guardian V1.0 — Main Application
 * Tab switching, constants, and shared utilities.
 */

const API = '/api/v1';

// ── State ──────────────────────────────────────────────────────────────────
let currentTab = 'detect';
let currentHistoryPage = 1;
let currentHistoryDetailId = null;

// ── DOM Ready ──────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
  initTabs();
});

// ── Tab Switching ──────────────────────────────────────────────────────────
function initTabs() {
  const tabButtons = document.querySelectorAll('.tab-btn:not([disabled])');

  tabButtons.forEach(function (btn) {
    btn.addEventListener('click', function () {
      const tabName = btn.getAttribute('data-tab');
      switchTab(tabName);
    });
  });
}

function switchTab(tabName) {
  if (currentTab === tabName) return;
  currentTab = tabName;

  // Update button active states
  document.querySelectorAll('.tab-btn').forEach(function (btn) {
    btn.classList.toggle('active', btn.getAttribute('data-tab') === tabName);
  });

  // Update content visibility
  document.querySelectorAll('.tab-content').forEach(function (content) {
    content.classList.toggle('active', content.id === 'tab-' + tabName);
  });

  // Trigger tab-specific loading
  if (tabName === 'dashboard') {
    loadDashboard();
  } else if (tabName === 'history') {
    loadHistory(currentHistoryPage);
  }
}

// ── Utilities ──────────────────────────────────────────────────────────────

/**
 * Format a Unix timestamp (seconds or milliseconds) to locale string.
 * @param {number|string} ts
 * @returns {string}
 */
function formatTime(ts) {
  if (!ts) return '--';
  var num = typeof ts === 'string' ? parseInt(ts, 10) : ts;
  // Heuristic: if less than 1e12, treat as seconds
  if (num < 1e12) num = num * 1000;
  var d = new Date(num);
  if (isNaN(d.getTime())) return '--';
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

/**
 * Show a toast notification.
 * @param {string} message
 * @param {'success'|'error'|'warning'|'info'} type
 * @param {number} duration - ms, default 3000
 */
function showToast(message, type, duration) {
  type = type || 'info';
  duration = duration || 3000;

  var toast = document.createElement('div');
  toast.className = 'toast ' + type;
  toast.textContent = message;
  document.body.appendChild(toast);

  setTimeout(function () {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s';
    setTimeout(function () {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 300);
  }, duration);
}

/**
 * Toggle element visibility by class.
 * @param {HTMLElement|string} el - element or id
 * @param {boolean} show
 */
function toggleVisibility(el, show) {
  if (typeof el === 'string') el = document.getElementById(el);
  if (!el) return;
  if (show) {
    el.classList.remove('hidden');
  } else {
    el.classList.add('hidden');
  }
}

/**
 * Set inner HTML of an element by id.
 * @param {string} id
 * @param {string} html
 */
function setHTML(id, html) {
  var el = document.getElementById(id);
  if (el) el.innerHTML = html;
}

/**
 * Make an API request with error handling.
 * @param {string} url
 * @param {object} options - fetch options
 * @returns {Promise<object>}
 */
async function apiRequest(url, options) {
  var opts = options || {};
  try {
    var response = await fetch(API + url, opts);
    if (!response.ok) {
      var errorBody = '';
      try { errorBody = await response.text(); } catch (e) { /* ignore */ }
      throw new Error('HTTP ' + response.status + ': ' + (errorBody || response.statusText));
    }
    return await response.json();
  } catch (err) {
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      throw new Error('无法连接到后端服务，请确认服务器已启动 (localhost:8000)');
    }
    throw err;
  }
}
