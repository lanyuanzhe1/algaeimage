/**
 * Algae Guardian V1.0 — Dashboard Module
 * Stats, charts, and history management.
 */

// Chart.js CDN fallback: if Chart is undefined after script load, degrade to text
var HAS_CHART = (typeof Chart !== 'undefined');

// ── Chart instances (for cleanup on re-render) ─────────────────────────────
var chartClassDist = null;
var chartRiskDist = null;

// ── Load Dashboard ─────────────────────────────────────────────────────────
async function loadDashboard() {
  try {
    var data = await apiRequest('/dashboard/stats');

    // Update stat cards
    document.getElementById('statTotal').textContent = (data.total_detections !== undefined ? data.total_detections : '--');
    document.getElementById('statToday').textContent = (data.today_count !== undefined ? data.today_count : '--');
    document.getElementById('statHighRisk').textContent = ((data.risk_distribution || {}).high !== undefined ? data.risk_distribution.high : '--');

    // Render charts
    renderClassDistribution(data.class_distribution || {});
    renderRiskDistribution(data.risk_distribution || {});

  } catch (err) {
    showToast('加载仪表板失败: ' + err.message, 'error');
    console.error(err);
  }
}

// ── Class Distribution Pie Chart ───────────────────────────────────────────
function renderClassDistribution(distribution) {
  var container = document.getElementById('chartClassDist').parentNode.parentNode;
  var labels = Object.keys(distribution);
  var values = Object.values(distribution);

  if (!HAS_CHART) {
    // Text-only fallback
    var html = '<ul style="list-style:none;padding:8px;">';
    if (labels.length === 0) {
      html += '<li style="color:var(--text-secondary);">暂无数据</li>';
    } else {
      var total = values.reduce(function(a,b){return a+b;}, 0);
      for (var i = 0; i < labels.length; i++) {
        var pct = total > 0 ? ((values[i]/total)*100).toFixed(1) + '%' : '0%';
        html += '<li style="padding:4px 0;display:flex;justify-content:space-between;"><span>' + escapeHtml(labels[i]) + '</span><span>' + values[i] + ' (' + pct + ')</span></li>';
      }
    }
    html += '</ul>';
    container.innerHTML = '<div class="chart-card"><h3>藻类分布</h3>' + html + '</div>';
    return;
  }

  var ctx = document.getElementById('chartClassDist').getContext('2d');

  // Destroy previous chart
  if (chartClassDist) {
    chartClassDist.destroy();
    chartClassDist = null;
  }

  var labels = Object.keys(distribution);
  var values = Object.values(distribution);

  if (labels.length === 0) {
    // Draw empty chart placeholder
    chartClassDist = new Chart(ctx, {
      type: 'pie',
      data: {
        labels: ['暂无数据'],
        datasets: [{ data: [1], backgroundColor: ['#e2e8f0'] }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: { display: false },
        },
      },
    });
    return;
  }

  var colors = generateColors(labels.length);

  chartClassDist = new Chart(ctx, {
    type: 'pie',
    data: {
      labels: labels,
      datasets: [{
        data: values,
        backgroundColor: colors,
        borderColor: '#ffffff',
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          position: 'right',
          labels: {
            padding: 12,
            font: { size: 12 },
            usePointStyle: true,
            pointStyleWidth: 10,
          },
        },
        tooltip: {
          callbacks: {
            label: function (context) {
              var total = context.dataset.data.reduce(function (a, b) { return a + b; }, 0);
              var value = context.parsed;
              var pct = total > 0 ? ((value / total) * 100).toFixed(1) + '%' : '0%';
              return context.label + ': ' + value + ' (' + pct + ')';
            },
          },
        },
      },
    },
  });
}

// ── Risk Distribution Bar Chart ────────────────────────────────────────────
function renderRiskDistribution(distribution) {
  var container = document.getElementById('chartRiskDist').parentNode.parentNode;
  var riskLabels = { high: '高危', medium: '中危', low: '低危' };
  var riskColors = { high: '#dc2626', medium: '#f59e0b', low: '#16a34a' };

  if (!HAS_CHART) {
    var html = '<ul style="list-style:none;padding:8px;">';
    var keys = ['high','medium','low'];
    var hasData = false;
    for (var i = 0; i < keys.length; i++) {
      var v = distribution[keys[i]] || 0;
      if (v > 0) hasData = true;
      html += '<li style="padding:4px 0;display:flex;align-items:center;"><span style="display:inline-block;width:12px;height:12px;border-radius:2px;background:' + riskColors[keys[i]] + ';margin-right:8px;"></span><span style="flex:1;">' + riskLabels[keys[i]] + '</span><span>' + v + '</span></li>';
    }
    if (!hasData) html += '<li style="color:var(--text-secondary);">暂无数据</li>';
    html += '</ul>';
    container.innerHTML = '<div class="chart-card"><h3>风险分布</h3>' + html + '</div>';
    return;
  }

  var ctx = document.getElementById('chartRiskDist').getContext('2d');

  // Destroy previous chart
  if (chartRiskDist) {
    chartRiskDist.destroy();
    chartRiskDist = null;
  }

  var riskOrder = ['high', 'medium', 'low'];
  var riskLabelsZh = { high: '高危', medium: '中危', low: '低危' };
  var riskColorsArr = { high: '#dc2626', medium: '#f59e0b', low: '#16a34a' };

  var labels = [];
  var values = [];
  var bgColors = [];

  riskOrder.forEach(function (key) {
    var val = distribution[key] || 0;
    labels.push(riskLabelsZh[key] || key);
    values.push(val);
    bgColors.push(riskColorsArr[key] || '#6b7280');
  });

  // Check if all zero
  var allZero = values.every(function (v) { return v === 0; });

  chartRiskDist = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: '检测数量',
        data: values,
        backgroundColor: bgColors,
        borderColor: bgColors,
        borderWidth: 1,
        borderRadius: 4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function (context) {
              return '数量: ' + context.parsed.y;
            },
          },
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            stepSize: 1,
            precision: 0,
          },
          grid: {
            color: '#f1f5f9',
          },
        },
        x: {
          grid: { display: false },
        },
      },
    },
  });
}

// ── History ────────────────────────────────────────────────────────────────
async function loadHistory(page) {
  page = page || 1;
  currentHistoryPage = page;
  var limit = 20;

  try {
    var data = await apiRequest('/history?page=' + page + '&limit=' + limit);

    var items = data.items || [];
    var total = data.total || 0;
    var totalPages = Math.ceil(total / limit) || 1;

    renderHistoryTable(items);
    renderPagination(page, totalPages);

  } catch (err) {
    showToast('加载历史记录失败: ' + err.message, 'error');
    console.error(err);
  }
}

/**
 * Render the history table body.
 * @param {Array} items
 */
function renderHistoryTable(items) {
  var tbody = document.getElementById('historyTableBody');

  if (!items || items.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6">' +
      '<div class="empty-state">' +
      '<span class="empty-icon">&#128196;</span>' +
      '<p class="empty-text">暂无检测记录</p>' +
      '<p class="empty-hint">完成检测后记录将显示在此处</p>' +
      '</div></td></tr>';
    return;
  }

  tbody.innerHTML = items.map(function (item) {
    var riskLevel = item.risk_level || 'low';
    var riskLabel = RISK_LABELS[riskLevel] || riskLevel;
    var qScore = item.q_score !== undefined && item.q_score !== null
      ? (typeof item.q_score === 'number' ? item.q_score.toFixed(2) : item.q_score)
      : '--';
    var detCount = item.detections_count !== undefined ? item.detections_count : (item.num_detections !== undefined ? item.num_detections : '--');
    var filename = item.filename || item.original_filename || '未知文件';

    return '<tr>' +
      '<td>' + formatTime(item.timestamp || item.created_at || item.detect_time) + '</td>' +
      '<td title="' + escapeHtml(filename) + '">' + truncate(escapeHtml(filename), 30) + '</td>' +
      '<td><span class="risk-badge risk-' + riskLevel + '">' + riskLabel + '</span></td>' +
      '<td>' + detCount + '</td>' +
      '<td>' + qScore + '</td>' +
      '<td>' +
      '<button class="btn btn-sm" onclick="viewHistoryDetail(' + item.id + ')" title="查看详情">查看</button> ' +
      '<button class="btn btn-sm btn-danger" onclick="deleteHistory(' + item.id + ')" title="删除">删除</button>' +
      '</td>' +
      '</tr>';
  }).join('');
}

/**
 * Render pagination buttons.
 * @param {number} currentPage
 * @param {number} totalPages
 */
function renderPagination(currentPage, totalPages) {
  var container = document.getElementById('historyPagination');

  if (totalPages <= 1) {
    container.innerHTML = '';
    return;
  }

  var html = '';

  // Previous
  html += '<button class="page-btn" ' + (currentPage <= 1 ? 'disabled' : '') + ' onclick="goToPage(' + (currentPage - 1) + ')">上一页</button>';

  // Page number buttons — show up to 7
  var maxButtons = 7;
  var startPage, endPage;

  if (totalPages <= maxButtons) {
    startPage = 1;
    endPage = totalPages;
  } else {
    var half = Math.floor(maxButtons / 2);
    if (currentPage <= half + 1) {
      startPage = 1;
      endPage = maxButtons;
    } else if (currentPage >= totalPages - half) {
      startPage = totalPages - maxButtons + 1;
      endPage = totalPages;
    } else {
      startPage = currentPage - half;
      endPage = currentPage + half;
    }
  }

  if (startPage > 1) {
    html += '<button class="page-btn" onclick="goToPage(1)">1</button>';
    if (startPage > 2) {
      html += '<span class="page-info">...</span>';
    }
  }

  for (var i = startPage; i <= endPage; i++) {
    html += '<button class="page-btn' + (i === currentPage ? ' active' : '') + '" onclick="goToPage(' + i + ')">' + i + '</button>';
  }

  if (endPage < totalPages) {
    if (endPage < totalPages - 1) {
      html += '<span class="page-info">...</span>';
    }
    html += '<button class="page-btn" onclick="goToPage(' + totalPages + ')">' + totalPages + '</button>';
  }

  // Next
  html += '<button class="page-btn" ' + (currentPage >= totalPages ? 'disabled' : '') + ' onclick="goToPage(' + (currentPage + 1) + ')">下一页</button>';

  container.innerHTML = html;
}

/**
 * Navigate to a specific history page.
 * @param {number} page
 */
function goToPage(page) {
  if (page < 1) return;
  loadHistory(page);
}

// ── Delete History ─────────────────────────────────────────────────────────
async function deleteHistory(id) {
  if (!confirm('确认删除该检测记录？此操作不可撤销。')) return;

  try {
    await apiRequest('/history/' + id, { method: 'DELETE' });
    showToast('记录已删除', 'success');
    loadHistory(currentHistoryPage);

    // Also refresh dashboard stats
    if (currentTab === 'dashboard') loadDashboard();

  } catch (err) {
    showToast('删除失败: ' + err.message, 'error');
    console.error(err);
  }
}

// ── Color Generator ────────────────────────────────────────────────────────
/**
 * Generate an array of n visually distinct colors.
 * Uses HSL with evenly-spaced hue and varying saturation/lightness.
 * @param {number} n
 * @returns {string[]} array of hex color strings
 */
function generateColors(n) {
  var colors = [];
  var goldenRatio = 0.618033988749895;
  var hue = 0.15; // start at green-ish

  for (var i = 0; i < n; i++) {
    hue = (hue + goldenRatio) % 1.0;
    var saturation = 0.55 + (i % 3) * 0.12;
    var lightness = 0.48 + (i % 2) * 0.12;
    colors.push(hslToHex(hue, saturation, lightness));
  }
  return colors;
}

/**
 * Convert HSL to hex color string.
 * @param {number} h - hue 0-1
 * @param {number} s - saturation 0-1
 * @param {number} l - lightness 0-1
 * @returns {string} hex color
 */
function hslToHex(h, s, l) {
  var r, g, b;

  if (s === 0) {
    r = g = b = l;
  } else {
    var hue2rgb = function (p, q, t) {
      if (t < 0) t += 1;
      if (t > 1) t -= 1;
      if (t < 1 / 6) return p + (q - p) * 6 * t;
      if (t < 1 / 2) return q;
      if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
      return p;
    };

    var q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    var p = 2 * l - q;
    r = hue2rgb(p, q, h + 1 / 3);
    g = hue2rgb(p, q, h);
    b = hue2rgb(p, q, h - 1 / 3);
  }

  var toHex = function (x) {
    var hex = Math.round(x * 255).toString(16);
    return hex.length === 1 ? '0' + hex : hex;
  };

  return '#' + toHex(r) + toHex(g) + toHex(b);
}

// ── Utility ────────────────────────────────────────────────────────────────

/**
 * Truncate string to maxLen with ellipsis.
 * @param {string} str
 * @param {number} maxLen
 * @returns {string}
 */
function truncate(str, maxLen) {
  if (!str) return '';
  if (str.length <= maxLen) return str;
  return str.substring(0, maxLen - 1) + '...';
}
