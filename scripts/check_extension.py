"""Verify the unpacked manifest and self-contained browser bundles after npm build."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "extension/dist"
manifest = json.loads((root / "manifest.json").read_text())
assert manifest["manifest_version"] == 3
assert manifest["permissions"] == ["storage"]
assert manifest["host_permissions"] == ["http://127.0.0.1:8000/*"]
for bundle in ["background.js", "content.js"]:
    text = (root / bundle).read_text()
    assert "process.env" not in text, f"Node environment reference left in {bundle}"
    assert "eval(" not in text, f"Dynamic code execution in {bundle}"
assert (root / manifest["options_page"]).exists()
print("Extension manifest and browser bundles validated")
