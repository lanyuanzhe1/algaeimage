"""Frontend HTML/JS integration tests."""

import os
import re


def _read_frontend_html():
    """Read index.html from the frontend directory."""
    path = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


class TestFolderInput:
    """Verify the frontend supports folder-based image selection."""

    def test_has_folder_input_with_webkitdirectory(self):
        """RED — currently no folder input exists."""
        html = _read_frontend_html()

        # A folder input must have webkitdirectory (or directory) attribute
        match = re.search(
            r'<input[^>]*webkitdirectory[^>]*>',
            html,
        )
        assert match is not None, (
            "Missing <input webkitdirectory> in frontend/index.html. "
            "Users cannot select a folder of images for batch detection."
        )

    def test_drop_zone_handles_folder_drop(self):
        """RED — verify detection.js has folder-aware drop handling."""
        js_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "js", "detection.js")
        with open(js_path, "r", encoding="utf-8") as f:
            js = f.read()

        # The drop handler should use webkitGetAsEntry for recursive folder traversal
        has_folder_drop = "webkitGetAsEntry" in js or "getAsEntry" in js
        assert has_folder_drop, (
            "detection.js drop handler does not recurse into folders. "
            "Dropping a folder onto the upload zone will not extract files recursively."
        )
