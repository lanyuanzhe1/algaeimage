"""Frontend HTML/JS integration tests — V1.0 redesign."""

import os
import re


def _read_frontend_html():
    """Read index.html from the frontend directory."""
    path = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _read_js(filename):
    """Read a JS file from the frontend/js directory."""
    path = os.path.join(os.path.dirname(__file__), "..", "frontend", "js", filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _read_css():
    """Read style.css from the frontend/css directory."""
    path = os.path.join(os.path.dirname(__file__), "..", "frontend", "css", "style.css")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ══════════════════════════════════════════════════════════════════════════════
# Existing tests — folder upload support
# ══════════════════════════════════════════════════════════════════════════════

class TestFolderInput:
    """Verify the frontend supports folder-based image selection."""

    def test_has_folder_input_with_webkitdirectory(self):
        html = _read_frontend_html()
        match = re.search(r'<input[^>]*webkitdirectory[^>]*>', html)
        assert match is not None, (
            "Missing <input webkitdirectory> in frontend/index.html."
        )

    def test_drop_zone_handles_folder_drop(self):
        js = _read_js("detection.js")
        has_folder_drop = "webkitGetAsEntry" in js or "getAsEntry" in js
        assert has_folder_drop, (
            "detection.js drop handler does not recurse into folders."
        )


# ══════════════════════════════════════════════════════════════════════════════
# RED Phase — Navigation Structure
# ══════════════════════════════════════════════════════════════════════════════

class TestNavigation:
    """Navigation bar must have 6 buttons with correct states."""

    def test_nav_has_six_buttons(self):
        html = _read_frontend_html()
        buttons = re.findall(r'<button[^>]*data-page="([^"]*)"[^>]*>', html)
        assert len(buttons) == 6, (
            f"Expected 6 nav buttons, found {len(buttons)}: {buttons}"
        )

    def test_nav_pages_have_correct_names(self):
        html = _read_frontend_html()
        buttons = re.findall(r'<button[^>]*data-page="([^"]*)"[^>]*>', html)
        expected = ['home', 'detect', 'history', 'dashboard', 'devices', 'review']
        assert buttons == expected, (
            f"Nav page order wrong. Expected {expected}, got {buttons}"
        )

    def test_placeholder_pages_are_disabled(self):
        html = _read_frontend_html()
        devices_match = re.search(
            r'<button[^>]*data-page="devices"[^>]*disabled[^>]*>', html
        )
        review_match = re.search(
            r'<button[^>]*data-page="review"[^>]*disabled[^>]*>', html
        )
        assert devices_match is not None, "Devices nav button must be disabled"
        assert review_match is not None, "Review nav button must be disabled"

    def test_home_is_default_active(self):
        html = _read_frontend_html()
        # The home button must have both data-page="home" and class containing "active"
        match = re.search(
            r'<button[^>]*class="[^"]*\bactive\b[^"]*"[^>]*data-page="home"[^>]*>'
            r'|'
            r'<button[^>]*data-page="home"[^>]*class="[^"]*\bactive\b[^"]*"[^>]*>',
            html,
        )
        assert match is not None, "Home nav button must have 'active' class by default"


# ══════════════════════════════════════════════════════════════════════════════
# RED Phase — Pipeline Bar
# ══════════════════════════════════════════════════════════════════════════════

class TestPipelineBar:
    """Pipeline bar must show the 5-stage processing flow."""

    def test_pipeline_has_five_steps(self):
        html = _read_frontend_html()
        steps = re.findall(r'class="pipe-step"', html)
        assert len(steps) == 5, (
            f"Expected 5 pipeline steps, found {len(steps)}"
        )

    def test_pipeline_has_arrows_between_steps(self):
        html = _read_frontend_html()
        arrows = re.findall(r'class="pipe-arrow"', html)
        assert len(arrows) == 4, (
            f"Expected 4 arrows between 5 steps, found {len(arrows)}"
        )

    def test_pipeline_steps_have_expected_labels(self):
        html = _read_frontend_html()
        expected_phases = [
            '偏振暗场采集', 'Stokes重建', '图像增强',
            'YOLO识别计数', '融合预警',
        ]
        for phase in expected_phases:
            assert phase in html, (
                f"Pipeline step '{phase}' not found in index.html"
            )


# ══════════════════════════════════════════════════════════════════════════════
# RED Phase — Critical Element IDs (detection.js + dashboard.js depend on these)
# ══════════════════════════════════════════════════════════════════════════════

class TestCriticalElementIDs:
    """All element IDs referenced by existing JS must exist in new HTML."""

    DETECTION_IDS = [
        'uploadZone', 'fileInput', 'folderInput', 'previewImage',
        'btnSelectFolder', 'btnSingleDetect', 'btnBatchDetect',
        'fileCountLabel', 'progressWrap', 'progressFill', 'progressText',
        'resultPanel', 'resultTime', 'resultEmpty', 'resultContent',
        'resultImage', 'resultMeta', 'detectList',
    ]

    DASHBOARD_IDS = [
        'statTotal', 'statToday', 'statHighRisk',
        'chartClassDist', 'chartRiskDist', 'recentDetections',
        'historyTableBody', 'historyPagination',
    ]

    HOME_IDS = [
        'metricTotal', 'metricToday', 'metricHighRisk',
        'metricAvgQ', 'metricClassCount',
        'homeStatTotal', 'homeStatToday', 'homeStatHighRisk',
        'homeRecentList',
    ]

    MODAL_IDS = ['reportModal', 'reportText', 'reportSuggestion', 'closeModal']

    def test_all_detection_ids_exist(self):
        html = _read_frontend_html()
        missing = [eid for eid in self.DETECTION_IDS
                   if f'id="{eid}"' not in html]
        assert missing == [], f"Missing detection IDs: {missing}"

    def test_all_dashboard_ids_exist(self):
        html = _read_frontend_html()
        missing = [eid for eid in self.DASHBOARD_IDS
                   if f'id="{eid}"' not in html]
        assert missing == [], f"Missing dashboard IDs: {missing}"

    def test_all_home_ids_exist(self):
        html = _read_frontend_html()
        missing = [eid for eid in self.HOME_IDS
                   if f'id="{eid}"' not in html]
        assert missing == [], f"Missing homepage IDs: {missing}"

    def test_all_modal_ids_exist(self):
        html = _read_frontend_html()
        missing = [eid for eid in self.MODAL_IDS
                   if f'id="{eid}"' not in html]
        assert missing == [], f"Missing modal IDs: {missing}"


# ══════════════════════════════════════════════════════════════════════════════
# RED Phase — Design System (CSS variables)
# ══════════════════════════════════════════════════════════════════════════════

class TestDesignSystem:
    """CSS must define blue-cyan design tokens and 4-level risk colors."""

    def test_primary_is_blue_not_green(self):
        css = _read_css()
        assert '--primary: #1976d2' in css, (
            "Primary color must be blue (#1976d2), not green"
        )

    def test_four_level_risk_colors_defined(self):
        css = _read_css()
        risk_vars = ['--risk-red', '--risk-orange', '--risk-yellow', '--risk-green']
        for var in risk_vars:
            assert var in css, f"Missing risk color variable: {var}"

    def test_risk_background_colors_defined(self):
        css = _read_css()
        bg_vars = ['--risk-red-bg', '--risk-orange-bg',
                   '--risk-yellow-bg', '--risk-green-bg']
        for var in bg_vars:
            assert var in css, f"Missing risk background variable: {var}"

    def test_responsive_breakpoints_exist(self):
        css = _read_css()
        assert '@media (max-width:1200px)' in css, "Missing 1200px breakpoint"
        assert '@media (max-width:900px)' in css, "Missing 900px breakpoint"
        assert '@media (max-width:640px)' in css, "Missing 640px breakpoint"


# ══════════════════════════════════════════════════════════════════════════════
# RED Phase — Script Loading Order
# ══════════════════════════════════════════════════════════════════════════════

class TestScriptOrder:
    """Scripts must load in dependency order: detection → dashboard → app → home."""

    def test_scripts_load_in_correct_order(self):
        html = _read_frontend_html()
        scripts = re.findall(r'<script src="([^"]*)"', html)
        # Filter to our JS files (skip CDN)
        local = [s for s in scripts if s.startswith('js/')]
        expected = [
            'js/detection.js',
            'js/dashboard.js',
            'js/app.js',
            'js/dashboard-home.js',
        ]
        assert local == expected, (
            f"Script order wrong. Expected {expected}, got {local}"
        )

    def test_all_four_js_files_referenced(self):
        html = _read_frontend_html()
        scripts = re.findall(r'<script src="([^"]*)"', html)
        local = [s for s in scripts if s.startswith('js/')]
        assert len(local) == 4, (
            f"Expected 4 local JS files, found {len(local)}: {local}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# RED Phase — Backward Compatibility
# ══════════════════════════════════════════════════════════════════════════════

class TestBackwardCompat:
    """app.js must provide backward-compat shims for detection.js."""

    def test_currentTab_variable_exists(self):
        js = _read_js("app.js")
        assert 'var currentTab' in js, (
            "app.js must declare currentTab for backward compat with detection.js"
        )

    def test_switchTab_function_exists(self):
        js = _read_js("app.js")
        assert 'function switchTab(' in js, (
            "app.js must define switchTab() backward-compat wrapper"
        )

    def test_switchTab_maps_detect_to_home(self):
        js = _read_js("app.js")
        # JS object literal: { detect: 'home', ... } — keys are unquoted
        assert "detect: 'home'" in js or 'detect: "home"' in js, (
            "switchTab must map old 'detect' tab to new 'home' page"
        )

    def test_detection_js_calls_switchPage_not_switchTab(self):
        js = _read_js("detection.js")
        # viewHistoryDetail should now call switchPage, not switchTab
        assert "switchPage('home')" in js, (
            "detection.js viewHistoryDetail must call switchPage('home')"
        )


# ══════════════════════════════════════════════════════════════════════════════
# RED Phase — Pipeline Functions (app.js)
# ══════════════════════════════════════════════════════════════════════════════

class TestPipelineFunctions:
    """app.js must expose updatePipeline, completePipeline, resetPipeline."""

    def test_updatePipeline_defined(self):
        js = _read_js("app.js")
        assert 'function updatePipeline(' in js, (
            "app.js must define updatePipeline() for detection.js"
        )

    def test_completePipeline_defined(self):
        js = _read_js("app.js")
        assert 'function completePipeline(' in js, (
            "app.js must define completePipeline() for detection.js"
        )

    def test_resetPipeline_defined(self):
        js = _read_js("app.js")
        assert 'function resetPipeline(' in js, (
            "app.js must define resetPipeline() for detection.js"
        )


# ══════════════════════════════════════════════════════════════════════════════
# RED Phase — Placeholder Panels
# ══════════════════════════════════════════════════════════════════════════════

class TestPlaceholderPanels:
    """Devices and Review pages must exist as static placeholders."""

    def test_devices_page_exists(self):
        html = _read_frontend_html()
        assert 'id="page-devices"' in html, "Missing devices page panel"

    def test_review_page_exists(self):
        html = _read_frontend_html()
        assert 'id="page-review"' in html, "Missing review page panel"

    def test_devices_page_has_placeholder_content(self):
        html = _read_frontend_html()
        assert '设备管理模块将在后续版本开放' in html, (
            "Devices page must show placeholder message"
        )

    def test_review_page_has_placeholder_content(self):
        html = _read_frontend_html()
        assert '人工复核模块将在后续版本开放' in html, (
            "Review page must show placeholder message"
        )
