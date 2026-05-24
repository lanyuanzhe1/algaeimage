/**
 * Algae Guardian V1.0 — Detection Module
 * Upload handling, single & batch detection, result rendering.
 */

// ── State ──────────────────────────────────────────────────────────────────
var selectedFiles = [];
var isDetecting = false;

// ── Risk label mapping ─────────────────────────────────────────────────────
var RISK_LABELS = { high: '高危', medium: '中危', low: '低危' };
var RISK_COLORS = { high: '#dc2626', medium: '#f59e0b', low: '#16a34a' };

// ── Init on DOM Ready ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
  initUploadZone();
});

// ── Upload Zone ────────────────────────────────────────────────────────────
function initUploadZone() {
  var zone = document.getElementById('uploadZone');
  var fileInput = document.getElementById('fileInput');
  var folderInput = document.getElementById('folderInput');

  // Click to open file dialog
  zone.addEventListener('click', function (e) {
    if (e.target === fileInput || e.target === folderInput) return;
    fileInput.click();
  });

  fileInput.addEventListener('change', function () {
    handleFiles(fileInput.files);
  });

  folderInput.addEventListener('change', function () {
    handleFiles(folderInput.files);
  });

  // "Select folder" button
  document.getElementById('btnSelectFolder').addEventListener('click', function (e) {
    e.stopPropagation();
    folderInput.click();
  });

  // Drag and drop (with folder recursion support)
  zone.addEventListener('dragover', function (e) {
    e.preventDefault();
    e.stopPropagation();
    zone.classList.add('drag-over');
  });

  zone.addEventListener('dragleave', function (e) {
    e.preventDefault();
    e.stopPropagation();
    zone.classList.remove('drag-over');
  });

  zone.addEventListener('drop', function (e) {
    e.preventDefault();
    e.stopPropagation();
    zone.classList.remove('drag-over');

    var items = e.dataTransfer.items;
    if (items && items.length > 0) {
      // Use webkitGetAsEntry for folder-aware traversal
      var entries = [];
      for (var i = 0; i < items.length; i++) {
        var entry = items[i].webkitGetAsEntry ? items[i].webkitGetAsEntry() : null;
        if (entry) {
          entries.push(entry);
        }
      }
      if (entries.length > 0) {
        collectFilesFromEntries(entries, function (files) {
          if (files.length > 0) {
            handleFiles(files);
          } else {
            showToast('未在文件夹中找到图片文件', 'warning');
          }
        });
        return;
      }
    }
    // Fallback to dataTransfer.files
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  });

  // Button handlers
  document.getElementById('btnSingleDetect').addEventListener('click', runSingleDetection);
  document.getElementById('btnBatchDetect').addEventListener('click', runBatchDetection);
}

/**
 * Recursively collect image files from dropped entries (files + folders).
 * @param {Array<FileSystemEntry>} entries
 * @param {Function} callback - receives a File[] array
 */
function collectFilesFromEntries(entries, callback) {
  var files = [];
  var pending = entries.length;

  if (pending === 0) {
    callback(files);
    return;
  }

  var validExtensions = ['jpg', 'jpeg', 'png', 'tif', 'tiff', 'bmp'];

  function checkDone() {
    pending--;
    if (pending === 0) {
      callback(files);
    }
  }

  entries.forEach(function (entry) {
    if (entry.isFile) {
      entry.file(function (file) {
        var ext = file.name.split('.').pop().toLowerCase();
        if (validExtensions.indexOf(ext) !== -1) {
          files.push(file);
        }
        checkDone();
      }, function () {
        checkDone();
      });
    } else if (entry.isDirectory) {
      var reader = entry.createReader();
      reader.readEntries(function (childEntries) {
        if (childEntries.length === 0) {
          checkDone();
          return;
        }
        pending += childEntries.length;
        childEntries.forEach(function (child) { entries.push(child); });
        checkDone();
      }, function () {
        checkDone();
      });
    } else {
      checkDone();
    }
  });
}

/**
 * Process user-selected files.
 * @param {FileList} fileList
 */
function handleFiles(fileList) {
  var MAX_FILES = 50;
  var files = Array.from(fileList);

  // Filter to image types
  var validExtensions = ['jpg', 'jpeg', 'png', 'tif', 'tiff', 'bmp'];
  var imageFiles = files.filter(function (f) {
    var ext = f.name.split('.').pop().toLowerCase();
    return validExtensions.indexOf(ext) !== -1;
  });

  if (imageFiles.length === 0) {
    showToast('请选择有效的图片文件 (JPG/PNG/TIFF)', 'warning');
    return;
  }

  if (imageFiles.length > MAX_FILES) {
    showToast('最多支持 ' + MAX_FILES + ' 张图片，已截取前 ' + MAX_FILES + ' 张', 'warning');
    imageFiles = imageFiles.slice(0, MAX_FILES);
  }

  // Clear previous file input so re-selecting same file works
  document.getElementById('fileInput').value = '';

  selectedFiles = imageFiles;
  updateFileUI();
}

/**
 * Update UI after file selection.
 */
function updateFileUI() {
  var count = selectedFiles.length;
  var label = document.getElementById('fileCountLabel');
  var btnSingle = document.getElementById('btnSingleDetect');
  var btnBatch = document.getElementById('btnBatchDetect');
  var preview = document.getElementById('previewImage');

  if (count === 0) {
    label.textContent = '';
    btnSingle.disabled = true;
    btnBatch.disabled = true;
    preview.classList.add('hidden');
    return;
  }

  label.textContent = '已选择 ' + count + ' 个文件';
  btnSingle.disabled = false;

  // Batch enabled only if more than 1 file
  btnBatch.disabled = count < 2;

  // Preview the first file
  var reader = new FileReader();
  reader.onload = function (e) {
    preview.src = e.target.result;
    preview.classList.remove('hidden');
  };
  reader.readAsDataURL(selectedFiles[0]);
}

// ── Single Detection ───────────────────────────────────────────────────────
async function runSingleDetection() {
  if (selectedFiles.length === 0 || isDetecting) return;
  isDetecting = true;

  var btn = document.getElementById('btnSingleDetect');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> 检测中...';

  try {
    var formData = new FormData();
    formData.append('file', selectedFiles[0]);

    var data = await apiRequest('/detect', {
      method: 'POST',
      body: formData,
    });

    renderResult(data);
    showToast('检测完成', 'success');

    // Refresh dashboard and history if those tabs have been visited
    if (currentTab === 'dashboard') loadDashboard();
    if (currentTab === 'history') loadHistory(currentHistoryPage);

  } catch (err) {
    showToast('检测失败: ' + err.message, 'error');
    console.error(err);
  } finally {
    isDetecting = false;
    btn.disabled = false;
    btn.textContent = '单图检测';
  }
}

// ── Render Result ──────────────────────────────────────────────────────────
function renderResult(data) {
  var emptyEl = document.getElementById('resultEmpty');
  var contentEl = document.getElementById('resultContent');
  var timeEl = document.getElementById('resultTime');

  emptyEl.classList.add('hidden');
  contentEl.classList.remove('hidden');

  // Result image
  var resultImage = document.getElementById('resultImage');
  if (data.result_image_url) {
    resultImage.src = data.result_image_url;
  } else {
    resultImage.src = '';
  }

  // Meta info
  var metaHtml = '';
  if (data.q_score !== undefined && data.q_score !== null) {
    metaHtml += '<span class="meta-item">质量评分 <strong class="q-score">';
    metaHtml += '<span class="q-label">Q=</span>' + (typeof data.q_score === 'number' ? data.q_score.toFixed(2) : data.q_score);
    metaHtml += '</strong></span>';
  }
  if (data.processing_time_ms !== undefined && data.processing_time_ms !== null) {
    metaHtml += '<span class="meta-item">处理耗时 <strong>' + (typeof data.processing_time_ms === 'number' ? data.processing_time_ms.toFixed(0) + 'ms' : data.processing_time_ms) + '</strong></span>';
  }
  if (data.filename) {
    metaHtml += '<span class="meta-item">文件 <strong>' + escapeHtml(data.filename) + '</strong></span>';
  }
  document.getElementById('resultMeta').innerHTML = metaHtml;

  // Show processing time in panel header
  if (data.processing_time_ms !== undefined && data.processing_time_ms !== null) {
    timeEl.style.display = '';
    timeEl.textContent = (typeof data.processing_time_ms === 'number' ? data.processing_time_ms.toFixed(0) + 'ms' : data.processing_time_ms);
  } else {
    timeEl.style.display = 'none';
  }

  // Detection list
  var detections = data.detections || [];
  var listEl = document.getElementById('detectList');

  if (detections.length === 0) {
    listEl.innerHTML = '<li class="detect-item risk-low"><span class="detect-name">未检测到藻类目标</span></li>';
  } else {
    listEl.innerHTML = detections.map(function (d) {
      var riskLevel = d.risk_level || 'low';
      var className = d.class_name || d.class || 'Unknown';
      var confidence = d.confidence !== undefined ? (d.confidence * 100).toFixed(1) + '%' : '--';
      var riskLabel = RISK_LABELS[riskLevel] || riskLevel;
      return '<li class="detect-item risk-' + riskLevel + '">' +
        '<span class="detect-name">' + escapeHtml(className) + '</span>' +
        '<span class="detect-conf">' + confidence + '</span>' +
        '<span class="risk-badge risk-' + riskLevel + '">' + riskLabel + '</span>' +
        '</li>';
    }).join('');
  }
}

// ── Batch Detection ────────────────────────────────────────────────────────
async function runBatchDetection() {
  if (selectedFiles.length < 2 || isDetecting) return;
  isDetecting = true;

  var btn = document.getElementById('btnBatchDetect');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> 处理中...';

  // Show progress bar
  var progressWrap = document.getElementById('progressWrap');
  var progressFill = document.getElementById('progressFill');
  var progressText = document.getElementById('progressText');
  progressWrap.classList.add('visible');
  progressFill.style.width = '0%';
  progressText.textContent = '正在处理 0 / ' + selectedFiles.length;

  // Animate progress heuristically since we can't get real-time progress from a single batch POST
  var progressInterval = setInterval(function () {
    var currentWidth = parseFloat(progressFill.style.width) || 0;
    if (currentWidth < 90) {
      var newWidth = Math.min(currentWidth + 3, 90);
      progressFill.style.width = newWidth + '%';
      var done = Math.floor(selectedFiles.length * newWidth / 100);
      progressText.textContent = '正在处理 ' + done + ' / ' + selectedFiles.length;
    }
  }, 800);

  try {
    var formData = new FormData();
    for (var i = 0; i < selectedFiles.length; i++) {
      formData.append('files', selectedFiles[i]);
    }

    var data = await apiRequest('/detect/batch', {
      method: 'POST',
      body: formData,
    });

    clearInterval(progressInterval);
    progressFill.style.width = '100%';
    progressText.textContent = '处理完成: ' + selectedFiles.length + ' 张图片';

    renderBatchResult(data);
    showToast('批量检测完成', 'success');

    // Refresh other tabs
    if (currentTab === 'dashboard') loadDashboard();
    if (currentTab === 'history') loadHistory(currentHistoryPage);

  } catch (err) {
    clearInterval(progressInterval);
    progressFill.style.width = '0%';
    progressWrap.classList.remove('visible');
    showToast('批量检测失败: ' + err.message, 'error');
    console.error(err);
  } finally {
    isDetecting = false;
    btn.disabled = false;
    btn.textContent = '批量处理';

    // Hide progress bar after a delay
    setTimeout(function () {
      progressWrap.classList.remove('visible');
      progressFill.style.width = '0%';
    }, 3000);
  }
}

/**
 * Render batch detection result summary.
 * @param {object} data - response from /detect/batch
 */
function renderBatchResult(data) {
  var results = data.results || [];
  var emptyEl = document.getElementById('resultEmpty');
  var contentEl = document.getElementById('resultContent');

  emptyEl.classList.add('hidden');
  contentEl.classList.remove('hidden');

  // Hide single image display for batch
  document.getElementById('resultImage').style.display = 'none';

  // Meta info — batch summary
  var totalDetections = 0;
  var highRiskCount = 0;
  results.forEach(function (r) {
    if (r.detections) {
      totalDetections += r.detections.length;
      r.detections.forEach(function (d) {
        if (d.risk_level === 'high') highRiskCount++;
      });
    }
  });

  var metaHtml = '';
  metaHtml += '<span class="meta-item">文件总数 <strong>' + results.length + '</strong></span>';
  metaHtml += '<span class="meta-item">检出目标 <strong>' + totalDetections + '</strong></span>';
  metaHtml += '<span class="meta-item">高危预警 <strong style="color:' + RISK_COLORS.high + '">' + highRiskCount + '</strong></span>';
  if (data.total_time !== undefined && data.total_time !== null) {
    metaHtml += '<span class="meta-item">总耗时 <strong>' + (typeof data.total_time === 'number' ? data.total_time.toFixed(2) + 's' : data.total_time) + '</strong></span>';
  }
  document.getElementById('resultMeta').innerHTML = metaHtml;

  // Build a summary list
  var listHtml = '';
  results.forEach(function (r, idx) {
    var riskLevel = r.risk_level || 'low';
    var maxRisk = riskLevel;
    if (r.detections) {
      for (var i = 0; i < r.detections.length; i++) {
        var rl = r.detections[i].risk_level || 'low';
        if (rl === 'high') { maxRisk = 'high'; break; }
        if (rl === 'medium' && maxRisk !== 'high') maxRisk = 'medium';
      }
    }
    var detCount = r.detections ? r.detections.length : 0;
    var status = r.status || 'success';
    var statusText = status === 'error' ? ' (失败)' : '';
    listHtml += '<li class="detect-item risk-' + maxRisk + '">' +
      '<span class="detect-name">' + escapeHtml(r.filename || ('文件 ' + (idx + 1))) + statusText + '</span>' +
      '<span class="detect-conf">检出: ' + detCount + '</span>' +
      '<span class="risk-badge risk-' + maxRisk + '">' + (RISK_LABELS[maxRisk] || maxRisk) + '</span>' +
      '</li>';
  });
  document.getElementById('detectList').innerHTML = listHtml;
}

// ── Helpers ────────────────────────────────────────────────────────────────

/**
 * Escape HTML entities to prevent XSS.
 * @param {string} str
 * @returns {string}
 */
function escapeHtml(str) {
  if (!str) return '';
  var div = document.createElement('div');
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}

// ── View History Detail (called from dashboard.js, renders in detect tab) ──
async function viewHistoryDetail(id) {
  currentHistoryDetailId = id;
  switchTab('detect');

  var emptyEl = document.getElementById('resultEmpty');
  var contentEl = document.getElementById('resultContent');

  try {
    var data = await apiRequest('/history/' + id);
    renderResult(data);

    // Show result image if available
    var resultImage = document.getElementById('resultImage');
    resultImage.style.display = '';
    if (data.image_url) {
      resultImage.src = data.image_url;
    } else if (data.image_path) {
      resultImage.src = data.image_path;
    }

  } catch (err) {
    showToast('加载历史详情失败: ' + err.message, 'error');
    emptyEl.classList.remove('hidden');
    contentEl.classList.add('hidden');
    console.error(err);
  }
}
