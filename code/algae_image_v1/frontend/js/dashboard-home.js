/**
 * Algae Guardian V1.0 — Dashboard Homepage Module
 * Homepage-specific rendering and refresh logic.
 * Core metrics rendering is in app.js (loadHomeMetrics).
 */

// ── Auto-refresh (every 60s when home page is active) ──────────────────────
var _homeRefreshInterval = null;

function startHomeAutoRefresh() {
  if (_homeRefreshInterval) return;
  _homeRefreshInterval = setInterval(function () {
    if (currentPage === 'home') {
      loadHomeMetrics();
    }
  }, 60000);
}

function stopHomeAutoRefresh() {
  if (_homeRefreshInterval) {
    clearInterval(_homeRefreshInterval);
    _homeRefreshInterval = null;
  }
}

// Start auto-refresh on load
document.addEventListener('DOMContentLoaded', function () {
  startHomeAutoRefresh();
});
