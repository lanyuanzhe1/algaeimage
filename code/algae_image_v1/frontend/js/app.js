/**
 * Algae Guardian V1.0 — Main Application
 * Navigation, pipeline animation, shared utilities, report modal.
 */

const API = '/api/v1';

// ── State ──────────────────────────────────────────────────────────────────
var currentPage = 'home';
var currentTab = 'home';  // backward compat for detection.js
var currentHistoryPage = 1;
var currentHistoryDetailId = null;

// ── DOM Ready ──────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
  try { initNavigation(); } catch (e) { console.error('initNavigation failed:', e); }
  try { initReportModal(); } catch (e) { console.error('initReportModal failed:', e); }
  try { loadHomeMetrics(); } catch (e) { console.error('loadHomeMetrics failed:', e); }
  // loadHomeMetrics is async — errors surface in its own catch block
});

// ── Navigation ─────────────────────────────────────────────────────────────
function initNavigation() {
  document.querySelectorAll('#navBar .nav-btn:not([disabled])').forEach(function (btn) {
    btn.addEventListener('click', function () {
      switchPage(btn.getAttribute('data-page'));
    });
  });
}

// Backward compat for detection.js (viewHistoryDetail calls switchTab)
function switchTab(pageName) {
  // Map old tab names to new page names
  var map = { detect: 'home', history: 'history', dashboard: 'dashboard' };
  switchPage(map[pageName] || pageName);
}

function switchPage(pageName) {
  if (currentPage === pageName) return;
  currentPage = pageName;
  currentTab = pageName;  // sync backward-compat var for detection.js

  // Manage auto-refresh: only active on home page
  if (pageName === 'home') {
    if (typeof startHomeAutoRefresh === 'function') startHomeAutoRefresh();
  } else {
    if (typeof stopHomeAutoRefresh === 'function') stopHomeAutoRefresh();
  }

  // Update nav button states
  document.querySelectorAll('#navBar .nav-btn').forEach(function (btn) {
    btn.classList.toggle('active', btn.getAttribute('data-page') === pageName);
  });

  // Show/hide page panels
  document.querySelectorAll('.page-panel').forEach(function (panel) {
    panel.classList.toggle('active', panel.id === 'page-' + pageName);
  });

  // Show/hide main-layout sections (only for home page)
  var mainLayout = document.querySelector('.main-layout');
  if (mainLayout) {
    mainLayout.style.display = (pageName === 'home') ? '' : 'none';
  }

  // Page-specific loading
  if (pageName === 'dashboard') {
    loadDashboard();
  }
  if (pageName === 'history') {
    loadHistory(currentHistoryPage);
  }
}

// ── Pipeline Animation ─────────────────────────────────────────────────────
var _pipelineTimer = null;

function updatePipeline(activeIndex) {
  document.querySelectorAll('.pipe-step').forEach(function (step, i) {
    step.classList.toggle('active', i === activeIndex);
    step.classList.toggle('done', i < activeIndex);
  });
}

function completePipeline() {
  document.querySelectorAll('.pipe-step').forEach(function (step) {
    step.classList.add('done');
    step.classList.remove('active');
  });
}

function resetPipeline() {
  document.querySelectorAll('.pipe-step').forEach(function (step) {
    step.classList.remove('active', 'done');
  });
  if (_pipelineTimer) {
    clearInterval(_pipelineTimer);
    _pipelineTimer = null;
  }
}

// ── Homepage Metrics ───────────────────────────────────────────────────────
async function loadHomeMetrics() {
  try {
    var data = await apiRequest('/dashboard/stats');

    // Top metrics row
    document.getElementById('metricTotal').textContent = (data.total_detections !== undefined ? data.total_detections : '--');
    document.getElementById('metricToday').textContent = (data.today_count !== undefined ? data.today_count : '--');
    var riskDist = data.risk_distribution || {};
    document.getElementById('metricHighRisk').textContent = (riskDist.high !== undefined ? riskDist.high : '--');

    // Average Q score
    var recent = data.recent_detections || [];
    if (recent.length > 0) {
      var sumQ = 0, countQ = 0;
      recent.forEach(function (r) {
        if (r.q_score !== undefined && r.q_score !== null) { sumQ += r.q_score; countQ++; }
      });
      document.getElementById('metricAvgQ').textContent = countQ > 0 ? (sumQ / countQ).toFixed(2) : '--';
    } else {
      document.getElementById('metricAvgQ').textContent = '--';
    }

    // Active class count
    var classDist = data.class_distribution || {};
    var classKeys = Object.keys(classDist);
    document.getElementById('metricClassCount').textContent = classKeys.length || '--';

    // Left panel stats
    document.getElementById('homeStatTotal').textContent = (data.total_detections !== undefined ? data.total_detections : '--');
    document.getElementById('homeStatToday').textContent = (data.today_count !== undefined ? data.today_count : '--');
    document.getElementById('homeStatHighRisk').textContent = (riskDist.high !== undefined ? riskDist.high : '--');

    // Right panel: recent detections
    renderHomeRecent(recent);

  } catch (err) {
    console.error('Load home metrics failed:', err);
    showToast('首页数据加载失败，请确认后端服务已启动', 'warning', 5000);
  }
}

function renderHomeRecent(recent) {
  var container = document.getElementById('homeRecentList');
  if (!container) return;

  if (!recent || recent.length === 0) {
    container.innerHTML = '<div class="empty-state"><p class="empty-text">暂无数据</p></div>';
    return;
  }

  container.innerHTML = recent.slice(0, 5).map(function (item) {
    var riskLevel = item.risk_level || 'low';
    var riskLabel = (typeof RISK_LABELS !== 'undefined' ? RISK_LABELS[riskLevel] : riskLevel) || riskLevel;
    var qScore = item.q_score !== undefined && item.q_score !== null
      ? (typeof item.q_score === 'number' ? item.q_score.toFixed(2) : item.q_score)
      : '--';
    var filename = item.filename || '未知文件';
    return '<div class="recent-item">' +
      '<span class="recent-name" title="' + escapeHtml(filename) + '">' + escapeHtml(filename) + '</span>' +
      '<span style="font-family:var(--font-mono);font-size:12px;">Q=' + qScore + '</span>' +
      '<span class="risk-badge risk-' + riskLevel + '">' + riskLabel + '</span>' +
      '<span style="font-size:11px;color:var(--muted);">' + formatTime(item.created_at || item.timestamp || item.detect_time) + '</span>' +
      '</div>';
  }).join('');
}

// ── Report Modal ───────────────────────────────────────────────────────────
function initReportModal() {
  var reportBtn = document.getElementById('reportBtn');
  var closeBtn = document.getElementById('closeModal');
  var modal = document.getElementById('reportModal');
  if (!reportBtn || !closeBtn || !modal) {
    console.warn('initReportModal: required DOM elements missing');
    return;
  }

  reportBtn.addEventListener('click', function () {
    var totalEl = document.getElementById('metricTotal');
    var highRiskEl = document.getElementById('metricHighRisk');
    var todayEl = document.getElementById('metricToday');
    var total = totalEl ? totalEl.textContent : '--';
    var highRisk = highRiskEl ? highRiskEl.textContent : '--';
    var today = todayEl ? todayEl.textContent : '--';

    document.getElementById('reportText').textContent =
      '藻影卫士 V1.0 当前监测状态：累计检测 ' + total + ' 次，今日 ' + today + ' 次，' +
      '高危预警 ' + highRisk + ' 条。系统基于结构张量偏振模拟 + RDN偏振重建 + YOLOv8s检测管线运行。';
    document.getElementById('reportSuggestion').textContent =
      '建议：持续监控藻密度变化趋势，对高危样本及时复核确认。定期检查模型性能，必要时触发增量再训练。';
    modal.classList.add('show');
  });

  closeBtn.addEventListener('click', function () {
    modal.classList.remove('show');
  });
  modal.addEventListener('click', function (event) {
    if (event.target === modal) {
      modal.classList.remove('show');
    }
  });
}

// ── Utilities ──────────────────────────────────────────────────────────────

function formatTime(ts) {
  if (!ts) return '--';
  var num = typeof ts === 'string' ? parseInt(ts, 10) : ts;
  if (num < 1e12) num = num * 1000;
  var d = new Date(num);
  if (isNaN(d.getTime())) return '--';
  return d.toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
}

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

function toggleVisibility(el, show) {
  if (typeof el === 'string') el = document.getElementById(el);
  if (!el) return;
  if (show) { el.classList.remove('hidden'); }
  else { el.classList.add('hidden'); }
}

function setHTML(id, html) {
  var el = document.getElementById(id);
  if (el) el.innerHTML = html;
}

async function apiRequest(url, options) {
  var opts = options || {};
  try {
    var response = await fetch(API + url, opts);
    if (!response.ok) {
      var errorBody = '';
      try { errorBody = await response.text(); } catch (e) {}
      throw new Error('HTTP ' + response.status + ': ' + (errorBody || response.statusText));
    }
    return await response.json();
  } catch (err) {
    // fetch() throws TypeError for network errors in all browsers
    if (err instanceof TypeError && /fetch|network|failed/i.test(err.message || '')) {
      throw new Error('无法连接到后端服务，请确认服务器已启动 (localhost:8000)');
    }
    throw err;
  }
}
