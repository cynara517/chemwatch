"""Reconstruct comparable yearly series from reviewed publications and official archives."""
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from chemwatch import TOPICS, atomic_json, now, tls_context

DATA = ROOT / "dist/data"
ARCHIVE = "https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/"
CSD = "https://www.ccdc.cam.ac.uk/media/CSD-Publication-Year-Statistics-{}.pdf"


def fetch(url):
    request = Request(url, headers={"User-Agent": "ChemWatch archive reader/0.3"})
    with urlopen(request, timeout=18, context=tls_context()) as response:
        return response.read(4_000_000)


def publication_series(entries, kind, topic, end):
    groups = {}
    for row in sorted(entries, key=lambda r: (r["publication_year"], r["id"])):
        if row["kind"] == kind and (not topic or topic in row["topics"]):
            key = row["family_id"] if kind == "dataset" else row["id"]
            groups.setdefault(key, row)
    by_year = defaultdict(list)
    for row in groups.values():
        by_year[row["publication_year"]].append({"label":row["name"], "url":row["date_source"]})
    points = []
    total = 0
    for year in range(min(by_year, default=end+1), end+1):
        evidence = by_year[year]
        total += len(evidence)
        points.append(dict(year=year, annual=len(evidence), total=total, sources=evidence))
    return points


def parse_csd(text, edition, url):
    baseline = re.search(r"1923\s*[–-]\s*1964\s+([\d,]+)", text)
    table = re.findall(r"^\s*((?:19|20)\d{2})\s+([\d,]+)\s+\d+\s*$", text, re.M)
    if not baseline or [int(year) for year, _ in table] != list(range(1965, edition+1)):
        raise ValueError("CSD annual table or historical baseline incomplete")
    initial = int(baseline[1].replace(",", ""))
    total, points = initial, []
    for year, count in table:
        annual = int(count.replace(",", ""))
        total += annual
        points.append(dict(year=int(year), annual=annual, total=total, partial=int(year)>=edition-1))
    return dict(edition=edition, url=url, baseline=initial, points=points)


def csd_series(edition, old):
    url = CSD.format(edition)
    try:
        raw = fetch(url)
    except HTTPError as exc:
        if exc.code == 404 and old and old["edition"] < edition:
            return old
        raise
    digest = hashlib.sha256(raw).hexdigest()
    if old.get("sha256") == digest:
        return old
    if shutil.which("pdftotext"):
        text = subprocess.run(["pdftotext","-layout","-","-"], input=raw, capture_output=True, check=True).stdout.decode()
    else:
        from pypdf import PdfReader
        text = "\n".join(page.extract_text(extraction_mode="layout") for page in PdfReader(io.BytesIO(raw)).pages)
    return {**parse_csd(text, edition, url), "sha256":digest}


def parse_release(text, version, url):
    date = re.search(r"prepared on\s+(.+?)\s+contains", text, re.I)
    count = re.search(r"^\s*([\d,]+) activities\b", text, re.M | re.I)
    if not count:
        count = re.search(r"assays and ([\d,]+) activities from", text, re.I)
    if not date or not count:
        raise ValueError(f"{version}: missing date or activity count")
    value = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", date[1], flags=re.I)
    for fmt in ("%d/%m/%Y", "%d %B %Y", "%d %b %Y"):
        try:
            stamp = datetime.strptime(value, fmt).date()
            return dict(version=version, date=stamp.isoformat(), total=int(count[1].replace(",","")), url=url)
        except ValueError:
            continue
    raise ValueError(f"{version}: unsupported date {value}")


def chembl_releases(old, errors):
    known = {p["version"]:p for p in old}
    versions = re.findall(r'href="(chembl_\d+(?:_\d+)?)/"', fetch(ARCHIVE).decode())
    if not versions:
        raise ValueError("Empty ChEMBL release index")
    # 01 and 02 lack activity-count notes. 22 and 24 explicitly point to patch releases.
    for version in sorted(set(versions)-known.keys()-{"chembl_01","chembl_02","chembl_22","chembl_24"}):
        url = f"{ARCHIVE}{version}/{version}_release_notes.txt"
        try:
            known[version] = parse_release(fetch(url).decode("utf-8-sig", errors="replace"),version,url)
        except (ValueError, OSError) as exc:
            errors.append(f"{version}: {exc}")
    return sorted(known.values(), key=lambda p:(p["date"],p["version"]))


def chembl_years(releases):
    latest = {}
    for release in sorted(releases, key=lambda p:(p["date"],p["version"])):
        latest[int(release["date"][:4])] = release
    points = []
    for year, release in sorted(latest.items()):
        previous = latest.get(year-1)
        annual = release["total"] - previous["total"] if previous else None
        points.append(dict(year=year, total=release["total"], annual=annual,
                           sources=[{"label":release["version"]+" · "+release["date"],"url":release["url"]}]))
    return points


def refresh():
    path = DATA / "timeseries.json"
    old = json.loads(path.read_text()) if path.exists() else {}
    catalog = json.loads((DATA / "catalog.json").read_text())
    year = datetime.now(timezone.utc).year
    data = {"checked_at":now(), "errors":[], "publications":{}}
    for kind in ("dataset","benchmark"):
        data["publications"][kind] = {topic:publication_series(catalog["entries"],kind,topic,year) for topic in ["",*sorted(TOPICS)]}
    try:
        data["csd"] = csd_series(year, old.get("csd",{}))
    except Exception as exc:
        data["errors"].append(f"CSD: {exc}")
        data["csd"] = old.get("csd",{})
    releases = old.get("chembl",{}).get("releases",[])
    try:
        releases = chembl_releases(releases, data["errors"])
    except (ValueError,OSError) as exc:
        data["errors"].append(f"ChEMBL: {exc}")
    data["chembl"] = {"url":ARCHIVE, "releases":releases, "points":chembl_years(releases)}
    atomic_json(path, data)
    return data["errors"]


if __name__ == "__main__":
    errors = refresh()
    print(errors)
    sys.exit(2 if errors else 0)
