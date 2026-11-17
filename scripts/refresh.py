"""Observe registered sources; save measured baselines and actual catalog history."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from chemwatch import atomic_json, now, validate_catalog


def main():
    data_dir = ROOT / "dist/data"
    catalog = validate_catalog(json.loads((data_dir / "catalog.json").read_text()))
    # Keep the previous successfully observed revisions in the published JSON as well.
    # This restores the probe baseline on a clean CI checkout without a cache.
    state_dir = ROOT / ".chemwatch/publisher-state"
    command = [sys.executable, str(ROOT / "chemwatch.py"), "sync", "--source", str(data_dir / "catalog.json"), "--probe", "--json", "--state-dir", str(state_dir), "--report-dir", str(ROOT / ".chemwatch/publisher-reports")]
    import hashlib
    identity = {"source":str((data_dir / "catalog.json").resolve()), "topics":[], "kind":None}
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:16]
    prior_file = data_dir / "observations.json"
    state_file = state_dir / (key + ".json")
    if not state_file.exists() and prior_file.exists():
        prior = json.loads(prior_file.read_text())
        atomic_json(state_file, {"identity":identity, "entries":{e["id"]:e for e in catalog["entries"]}, "observations":{e["id"]:{k:v for k,v in e.items() if k!="id"} for e in prior.get("items",[])}, "pending_email":[]})
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if result.returncode not in (0, 2):
        print(result.stderr, file=sys.stderr)
        return 1
    report = json.loads(result.stdout)
    old_events = json.loads(prior_file.read_text()).get("events",[]) if prior_file.exists() else []
    events = ([{**event, "observed_at":report["checked_at"]} for event in report["upstream_changes"]] + old_events)[:50]
    atomic_json(prior_file, {"schema_version":"1.0", "checked_at":report["checked_at"], "items":[{"id":k,**v} for k,v in report["observations"].items()], "errors":report["errors"], "events":events, "note":"Upstream revision signals, not dataset record counts. Failures retain the last successful observation."})
    history_file = data_dir / "history.json"
    history = json.loads(history_file.read_text()) if history_file.exists() else {"schema_version":"1.0", "metric":"catalog_coverage", "points":[]}
    date = now()[:10]
    def counts(entries):
        return {"entries":len(entries), "dataset_families":len({e["family_id"] for e in entries if e["kind"]=="dataset"}), "benchmark_suites":sum(e["kind"]=="benchmark" for e in entries), "databases":sum(e["kind"]=="database" for e in entries)}
    from chemwatch import TOPICS
    point = {"date":date, **counts(catalog["entries"]), "topics":{topic:counts([e for e in catalog["entries"] if topic in e["topics"]]) for topic in sorted(TOPICS)}}
    history["points"] = [p for p in history["points"] if p["date"]!=date] + [point]
    atomic_json(history_file, history)
    print(json.dumps({"checked_at":report["checked_at"], "observations":len(report["observations"]), "changes":len(report["upstream_changes"]), "errors":report["errors"]}, ensure_ascii=False, indent=2))
    return 2 if report["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
