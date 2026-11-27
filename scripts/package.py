"""Create the portable user-facing source and CLI bundle (never include runtime state)."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import zipfile

root = Path(__file__).resolve().parents[1]


def stamp_frontend_assets(index):
    html = index.read_text(encoding="utf-8")
    # Only local style and script URLs are versioned. Data feeds keep stable URLs.
    asset_url = r'(?P<attr>href|src)="(?P<path>[\w./-]+\.(?:css|js))(?:\?v=[0-9a-f]+)?"'

    def versioned(match):
        path = match["path"]
        digest = hashlib.sha256((index.parent / path).read_bytes()).hexdigest()[:16]
        return f'{match["attr"]}="{path}?v={digest}"'

    stamped = re.sub(asset_url, versioned, html)
    if html != stamped:
        index.write_text(stamped, encoding="utf-8")


for html in (root / "dist").rglob("*.html"):
    stamp_frontend_assets(html)
target = root / "dist/downloads/chemwatch-toolkit.zip"
target.parent.mkdir(parents=True, exist_ok=True)
skill = root / "skills/chemwatch-monitor"
(skill / "scripts").mkdir(parents=True, exist_ok=True)
shutil.copyfile(root / "chemwatch.py", skill / "scripts/chemwatch.py")


def add_file(archive, path, name):
    info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    archive.writestr(info, path.read_bytes())


skill_zip = target.parent / "chemwatch-skill.zip"
with zipfile.ZipFile(skill_zip, "w") as z:
    for path in sorted(skill.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            add_file(z, path, str(Path("chemwatch-monitor") / path.relative_to(skill)))
manifest = {"version":"0.3.0", "sha256":hashlib.sha256(skill_zip.read_bytes()).hexdigest(), "format":"agent-skill", "python":">=3.10"}
(target.parent / "skill-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
shutil.copyfile(root / "install.sh", root / "dist/install.sh")
with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if not path.is_file() or any(part in {".git", ".openai", ".chemwatch", "__pycache__", "downloads", "node_modules"} for part in rel.parts) or path.suffix in {".pyc", ".zip", ".gz"} or path.name in {".DS_Store", ".env"}:
            continue
        add_file(z, path, str(Path("chemwatch") / rel))
shutil.copyfile(root / "chemwatch.py", root / "dist/downloads/chemwatch.py")
print(target)
