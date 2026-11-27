#!/usr/bin/env python3
"""ChemWatch: portable catalog synchronization and upstream signals. Python >=3.10."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import secrets
import subprocess
import smtplib
import ssl
import sys
import tempfile
import time
from datetime import datetime, timezone
from email.message import EmailMessage
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

VERSION = "0.3.0"
ROOT = Path(__file__).resolve().parent
PUBLIC_CATALOG = "https://cynara517.github.io/chemwatch/data/catalog.json"
STATE_ROOT = Path(os.getenv("XDG_STATE_HOME", str(Path.home() / ".local/state"))) / "chemwatch"
TOPICS = {"chemistry-ai", "retrosynthesis", "coupling", "materials", "yield", "free-energy", "selectivity", "bioactivity", "bioprocess", "penicillin", "erythromycin"}


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def tls_context():
    # Python.org macOS builds may have an uninitialized private CA directory.
    # Use the system PEM bundle without disabling certificate verification.
    system_ca = Path("/etc/ssl/cert.pem")
    if sys.platform == "darwin" and not os.getenv("SSL_CERT_FILE") and system_ca.is_file():
        return ssl.create_default_context(cafile=str(system_ca))
    return ssl.create_default_context()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix=".chemwatch-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def read_json(source):
    if str(source).startswith(("http://", "https://")):
        req = Request(str(source), headers={"User-Agent": "ChemWatch/" + VERSION, "Accept": "application/json"})
        with urlopen(req, timeout=30, context=tls_context()) as response:
            raw = response.read(10_000_001)
        if len(raw) > 10_000_000:
            raise ValueError("JSON exceeds 10 MB limit")
        return json.loads(raw)
    return json.loads(Path(source).read_text(encoding="utf-8"))


def validate_catalog(data):
    if not isinstance(data, dict) or data.get("schema_version") != "1.0" or not isinstance(data.get("entries"), list):
        raise ValueError("Expected a ChemWatch catalog v1.0 JSON document")
    ids = set()
    for entry in data["entries"]:
        if not isinstance(entry, dict) or not all(isinstance(entry.get(k), str) and entry[k] for k in ("id", "name", "kind", "family_id", "url")):
            raise ValueError("Catalog entry is missing required string fields")
        if entry["id"] in ids:
            raise ValueError("Duplicate catalog ID: " + entry["id"])
        if entry["kind"] not in {"dataset", "benchmark", "database", "resource"}:
            raise ValueError("Unknown catalog kind")
        if not isinstance(entry.get("topics"), list) or not all(isinstance(t, str) for t in entry["topics"]):
            raise ValueError("Invalid topic list")
        if urlparse(entry["url"]).scheme != "https":
            raise ValueError("Source links must use HTTPS")
        ids.add(entry["id"])
    return data


def select(data, topics=(), kind=None):
    # Multiple topics are OR; within a topic, the page and CLI share identical membership.
    return [e for e in data["entries"] if (not topics or set(topics) & set(e["topics"])) and (not kind or e["kind"] == kind)]


def semantic(entry):
    return {k: v for k, v in entry.items() if k not in {"verified_at", "checked_at"}}


def compare(old, new):
    return {
        "added": [new[k] for k in sorted(new.keys() - old.keys())],
        "changed": [{"before": old[k], "after": new[k]} for k in sorted(new.keys() & old.keys()) if semantic(old[k]) != semantic(new[k])],
        "removed": [old[k] for k in sorted(old.keys() - new.keys())],
    }


def api_json(url, github=False):
    headers = {"User-Agent": "ChemWatch/" + VERSION, "Accept": "application/json"}
    if github and os.getenv("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    with urlopen(Request(url, headers=headers), timeout=25, context=tls_context()) as response:
        return json.load(response)


def fetch_public_text(url):
    with urlopen(Request(url, headers={"User-Agent": "ChemWatch/" + VERSION}),
                 timeout=25, context=tls_context()) as response:
        raw = response.read(5_000_001)
    if len(raw) > 5_000_000:
        raise ValueError("Public page exceeds 5 MB limit")
    return raw.decode("utf-8")


def parse_deltascience(bundle):
    # Parse data literals only; never execute downloaded JavaScript.
    string = r'"(?:[^"\\]|\\.)*"'
    fields = ["code", "group", "discipline", "author", "organization", "focus", "title"]
    row_pattern = r'\{' + ','.join(f'{key}:({string})' for key in fields) + r',position:(\d+)\}'
    array = re.search(r'\[(\{code:.*?\})\]', bundle, re.S)
    if not array:
        raise ValueError("DeltaScience public task table missing")
    body = array[1]
    matches = list(re.finditer(row_pattern, body))
    if not matches or ','.join(m[0] for m in matches) != body:
        raise ValueError("DeltaScience task schema changed; refusing partial snapshot")
    rows = [dict(zip(fields, [json.loads(v) for v in m.groups()[:-1]])) for m in matches]
    if len({r['code'] for r in rows}) != len(rows):
        raise ValueError("DeltaScience duplicate task IDs")
    items = [{"id":r['code'], "title":r['title'] or r['focus'] or r['discipline'],
              "discipline":r['discipline'], "focus":r['focus'],
              "url":"https://deltascience.bohrium.com/questions/" + quote(r['code'], safe="")}
             for r in rows if r['group'] == '化学']
    if not items:
        raise ValueError("DeltaScience chemistry category missing")
    return sorted(items, key=lambda r:r['id']), len(rows)


def probe_deltascience():
    url = "https://deltascience.bohrium.com/"
    html = fetch_public_text(url)
    assets = re.findall(r'<script\b[^>]*\bsrc=[\"\'](/assets/[^\"\']+\.js)[\"\']', html)
    if len(assets) != 1:
        raise ValueError("DeltaScience entry asset changed")
    asset_url = url.rstrip('/') + assets[0]
    items, total = parse_deltascience(fetch_public_text(asset_url))
    revision = hashlib.sha256(json.dumps(items, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return {"revision":revision, "url":url+"questions?subject="+quote("化学"),
            "upstream_date":None, "signal":"public_task_catalog", "asset_url":asset_url,
            "chemistry_tasks":len(items), "total_tasks":total, "items":items, "observed_at":now(),
            "note":"DeltaScience官方主分类为化学的公开题单元数据变化；不是新增独立benchmark或实验记录数"}


def probe(entry):
    monitor = entry.get("monitor")
    if not monitor:
        return None
    if monitor["type"] == "deltascience":
        return probe_deltascience()
    if monitor["type"] == "github":
        repo = monitor["repo"]
        if len(repo.split("/")) != 2 or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._/" for c in repo):
            raise ValueError("Invalid repository name")
        query = {"per_page": 1}
        if monitor.get("path"):
            query["path"] = monitor["path"]
        rows = api_json("https://api.github.com/repos/" + repo + "/commits?" + urlencode(query), github=True)
        if not rows:
            raise ValueError("No commit found for monitored path")
        r = rows[0]
        return {"revision": r["sha"], "url": r["html_url"], "upstream_date": r["commit"]["committer"]["date"], "signal": "repository_change", "note": "仓库或指定路径提交变化；不代表数据记录数量增长"}
    if monitor["type"] == "huggingface":
        repo = monitor["repo"]
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo) or ".." in repo:
            raise ValueError("Invalid Hugging Face dataset ID")
        data = api_json("https://huggingface.co/api/datasets/" + repo)
        sha = data.get("sha")
        if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40,64}", sha):
            raise ValueError("Missing Hugging Face dataset revision")
        return {"revision":sha, "upstream_date":data.get("lastModified"),
                "url":f"https://huggingface.co/datasets/{repo}/commit/{sha}",
                "signal":"dataset_repository_revision", "note":"Hugging Face 数据仓库修订，含数据卡和文件更新"}
    if monitor["type"] == "zenodo":
        record = str(monitor["record"])
        if not record.isdigit():
            raise ValueError("Invalid Zenodo record")
        r = api_json("https://zenodo.org/api/records/" + record)
        latest = r.get("links", {}).get("latest", "")
        # A fixed record can point to a newer version. Follow only the same trusted API.
        if latest.startswith("https://zenodo.org/api/records/"):
            r = api_json(latest)
        fingerprint = {"id": r["id"], "version": r["metadata"].get("version"), "files": [(f["key"], f.get("checksum")) for f in r.get("files", [])]}
        digest = hashlib.sha256(json.dumps(fingerprint, sort_keys=True).encode()).hexdigest()
        record_url = r["links"].get("self_html") or r["links"].get("html") or ("https://zenodo.org/records/" + str(r["id"]))
        return {"revision": digest, "url": record_url, "upstream_date": r.get("modified"), "signal": "archive_version_or_files", "note": "存档版本或文件校验和变化；需核验具体内容"}
    raise ValueError("Unsupported monitor type")


def summary_text(report):
    lines = ["# ChemWatch 同步报告", "", "检查时间：" + report["checked_at"], "状态：" + report["status"], "目录：" + report["source"], ""]
    if report["baseline"]:
        lines += ["首次建立基线，已收录条目不记为新发现；未触发邮件。", ""]
    for key, title in [("added", "新增目录条目"), ("changed", "目录元数据变化"), ("removed", "移出当前订阅范围")]:
        lines += ["## " + title, ""]
        for item in report[key]:
            entry = item.get("after", item)
            lines.append("- [" + entry["name"] + "](" + entry["url"] + ")")
        if not report[key]:
            lines.append("无")
        lines.append("")
    lines += ["## 上游变化信号", ""]
    for item in report["upstream_changes"]:
        lines.append("- [" + item["name"] + "](" + item["observation"]["url"] + ")：" + item["observation"]["note"])
    if not report["upstream_changes"]:
        lines.append("无；首次成功探测只建立版本基线。")
    if report["errors"]:
        lines += ["", "## 检查失败（保留上次成功版本）", ""] + ["- " + e["id"] + ": " + e["error"] for e in report["errors"]]
    return "\n".join(lines) + "\n"


def send_email(recipient, content, report_id):
    required = ["CHEMWATCH_SMTP_HOST", "CHEMWATCH_SMTP_FROM"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise ValueError("Missing environment: " + ", ".join(missing))
    host = os.environ["CHEMWATCH_SMTP_HOST"]
    sender = os.environ["CHEMWATCH_SMTP_FROM"]
    mode = os.getenv("CHEMWATCH_SMTP_MODE", "starttls")
    if mode not in {"starttls", "ssl"}:
        raise ValueError("CHEMWATCH_SMTP_MODE must be starttls or ssl")
    msg = EmailMessage()
    msg["From"], msg["To"] = sender, recipient
    msg["Subject"] = "ChemWatch · 订阅主题有更新"
    msg["Message-ID"] = "<chemwatch-" + report_id + "@" + sender.split("@")[-1] + ">"
    msg.set_content(content)
    port = int(os.getenv("CHEMWATCH_SMTP_PORT", "465" if mode == "ssl" else "587"))
    client = smtplib.SMTP_SSL(host, port, timeout=30, context=tls_context()) if mode == "ssl" else smtplib.SMTP(host, port, timeout=30)
    with client:
        if mode == "starttls":
            client.starttls(context=tls_context())
        if os.getenv("CHEMWATCH_SMTP_USER"):
            client.login(os.environ["CHEMWATCH_SMTP_USER"], os.environ.get("CHEMWATCH_SMTP_PASSWORD", ""))
        client.send_message(msg)


def sync(args, data, entries):
    identity = {"source": args.source if args.source.startswith(("http://", "https://")) else str(Path(args.source).resolve()), "topics": sorted(args.topic), "kind": args.kind}
    identity_hash = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:16]
    state_path = Path(args.state_dir) / (identity_hash + ".json")
    prior = read_json(state_path) if state_path.exists() else {}
    current = {e["id"]: e for e in entries}
    baseline = not prior
    delta = compare(prior.get("entries", {}), current) if not baseline else {"added": [], "changed": [], "removed": []}
    observations = {k: v for k, v in prior.get("observations", {}).items() if k in current}
    upstream_changes, errors = [], []
    if args.probe:
        for entry in entries:
            try:
                obs = probe(entry)
                if obs:
                    old = observations.get(entry["id"])
                    if old and old["revision"] != obs["revision"]:
                        upstream_changes.append({"id": entry["id"], "name": entry["name"], "observation": obs})
                    observations[entry["id"]] = obs
            except Exception as exc:
                errors.append({"id": entry["id"], "error": str(exc)})
    changed = any(delta.values()) or bool(upstream_changes)
    report = {"schema_version": "1.0", "checked_at": now(), "source": identity["source"], "topics": args.topic, "baseline": baseline, "status": "partial_error" if errors else "baseline" if baseline else "changed" if changed else "unchanged", "selected_count": len(entries), **delta, "upstream_changes": upstream_changes, "errors": errors, "observations": observations}
    report_text = summary_text(report)
    pending = prior.get("pending_email", [])
    # Preserve unsent reports; never lose a notification if SMTP fails after state advances.
    if changed and args.email:
        report_id = hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()[:24]
        pending.append({"recipient": args.email, "content": report_text, "report_id": report_id})
    state = {"identity": identity, "checked_at": report["checked_at"], "entries": current, "observations": observations, "pending_email": pending}
    if baseline or changed or errors:
        name = report["checked_at"].replace(":", "").replace(".", "-") + "-" + identity_hash
        folder = Path(args.report_dir)
        atomic_json(folder / (name + ".json"), report)
        (folder / (name + ".md")).write_text(report_text, encoding="utf-8")
        report["report_file"] = str(folder / (name + ".md"))
    atomic_json(state_path, state)
    if args.email:
        # Pending mail is only sent for the same explicitly selected recipient.
        for message in list(pending):
            if message["recipient"] != args.email:
                continue
            try:
                send_email(message["recipient"], message["content"], message["report_id"])
                pending.remove(message)
                state["pending_email"] = pending
                atomic_json(state_path, state)
            except Exception as exc:
                report["email_error"] = str(exc)
                report["status"] = "notification_error"
                break
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif report["status"] != "unchanged":
        print(report_text)
        if report.get("email_error"):
            print("邮件未发送，已保留待重试报告：" + report["email_error"], file=sys.stderr)
    return 2 if errors or report.get("email_error") else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=VERSION)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("list", "sync"):
        p = sub.add_parser(name)
        p.add_argument("--source", default=os.getenv("CHEMWATCH_SOURCE", PUBLIC_CATALOG), help="Catalog JSON path or public HTTP(S) URL; no account required")
        p.add_argument("--topic", action="append", default=[], choices=sorted(TOPICS), help="Repeat for OR matching")
        p.add_argument("--kind", choices=["dataset", "benchmark", "database", "resource"])
        p.add_argument("--json", action="store_true")
        if name == "sync":
            p.add_argument("--probe", action="store_true", help="Check configured upstream revision signals; not record counts")
            p.add_argument("--state-dir", default=str(STATE_ROOT / "state"))
            p.add_argument("--report-dir", default=str(STATE_ROOT / "reports"))
            p.add_argument("--email", help="Opt in to sending changed reports via configured SMTP; baseline is silent")
    follow_parser = sub.add_parser("follow", help="Save a subscription and establish its baseline")
    follow_parser.add_argument("--topic", action="append", default=[], choices=sorted(TOPICS))
    follow_parser.add_argument("--source", default=PUBLIC_CATALOG)
    follow_parser.add_argument("--email")
    follow_parser.add_argument("--no-probe", action="store_true")
    follow_parser.add_argument("--json", action="store_true")
    follow_parser.add_argument("--config", default=str(STATE_ROOT / "subscription.json"))
    check_parser = sub.add_parser("check", help="Check the saved subscription once")
    check_parser.add_argument("--json", action="store_true")
    check_parser.add_argument("--config", default=str(STATE_ROOT / "subscription.json"))
    watch_parser = sub.add_parser("watch", help="Monitor a saved subscription in the foreground or as a local background process")
    watch_parser.add_argument("--config", default=str(STATE_ROOT / "subscription.json"))
    watch_parser.add_argument("--interval", type=int, default=86400, help="Seconds between checks (minimum 60)")
    watch_modes = watch_parser.add_mutually_exclusive_group()
    watch_modes.add_argument("--background", action="store_true")
    watch_modes.add_argument("--stop", action="store_true")
    watch_modes.add_argument("--status", action="store_true")
    watch_parser.add_argument("--_token", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        if args.command == "follow":
            config_path = Path(args.config).expanduser().resolve()
            config = {"source":args.source, "topics":sorted(set(args.topic)), "email":args.email, "probe":not args.no_probe, "updated_at":now()}
            # Validate the remote/local catalog before replacing a working subscription.
            validate_catalog(read_json(args.source))
            atomic_json(config_path, config)
            code = check_subscription(config_path, args.json)
            if not args.json:
                print("Subscription saved: " + str(config_path))
                print("Next: chemwatch check; daily background monitoring: chemwatch watch --background")
            return code
        if args.command == "check":
            return check_subscription(Path(args.config).expanduser().resolve(), args.json)
        if args.command == "watch":
            return watch_subscription(args)
        data = validate_catalog(read_json(args.source))
        entries = select(data, args.topic, args.kind)
        if args.command == "sync":
            return sync(args, data, entries)
        print(json.dumps(entries, ensure_ascii=False, indent=2) if args.json else "\n".join(f"{e['id']:25} {e['kind']:10} {e['name']}" for e in entries))
        return 0
    except Exception as exc:
        print("ChemWatch: " + str(exc), file=sys.stderr)
        return 1


def check_subscription(config_path, as_json=False):
    if not config_path.exists():
        raise ValueError("No subscription yet. Run: chemwatch follow --topic retrosynthesis")
    config = read_json(config_path)
    topics = config.get("topics", [])
    if not isinstance(topics, list) or not set(topics) <= TOPICS:
        raise ValueError("Invalid subscription topics")
    source = config["source"]
    data = validate_catalog(read_json(source))
    args = argparse.Namespace(source=source, topic=topics, kind=None, probe=config.get("probe", True), json=as_json, email=config.get("email"), state_dir=str(config_path.parent / "state"), report_dir=str(config_path.parent / "reports"))
    return sync(args, data, select(data, topics))


def watch_subscription(args):
    config_path = Path(args.config).expanduser().resolve()
    if not config_path.exists():
        raise ValueError("Run chemwatch follow before starting a watcher")
    folder = config_path.parent / (config_path.stem + "-watcher")
    control_path = folder / "control.json"
    heartbeat_path = folder / "heartbeat.json"
    control = read_json(control_path) if control_path.exists() else {}
    heartbeat = read_json(heartbeat_path) if heartbeat_path.exists() else {}
    fresh = time.time() - heartbeat.get("epoch", 0) < 120
    running = bool(control.get("active") and control.get("token") == heartbeat.get("token") and fresh)
    if args.status:
        print(json.dumps({"running":running, "config":str(config_path), "heartbeat":heartbeat, "log":str(folder / "watch.log")}, indent=2))
        return 0
    if args.stop:
        atomic_json(control_path, {**control, "active":False, "stopped_at":now()})
        print("Stop requested; the watcher exits within 5 seconds. No process is killed by PID.")
        return 0
    if args.interval < 60:
        raise ValueError("Watch interval must be at least 60 seconds")
    if not args._token and running:
        print("A watcher is already running for this subscription. Use watch --status or watch --stop.")
        return 0
    token = args._token or secrets.token_hex(16)
    if not args._token:
        atomic_json(control_path, {"active":True, "token":token, "interval":args.interval, "started_at":now()})
    if args.background:
        folder.mkdir(parents=True, exist_ok=True)
        with (folder / "watch.log").open("a", encoding="utf-8") as log:
            process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "watch", "--config", str(config_path), "--interval", str(args.interval), "--_token", token], stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
        print(json.dumps({"started":True,"pid":process.pid,"config":str(config_path),"interval_seconds":args.interval,"log":str(folder / "watch.log"),"note":"Local process; runs while this computer is on. Not registered as a boot service."}, indent=2))
        return 0
    next_check = 0
    try:
        while True:
            control = read_json(control_path)
            if not control.get("active") or control.get("token") != token:
                return 0
            atomic_json(heartbeat_path, {"token":token,"epoch":time.time(),"checked_at":now(),"pid":os.getpid()})
            if time.monotonic() >= next_check:
                try:
                    check_subscription(config_path)
                except Exception as exc:
                    print(now() + " Check failed: " + str(exc), file=sys.stderr, flush=True)
                next_check = time.monotonic() + args.interval
                sys.stdout.flush()
            time.sleep(5)
    finally:
        current = read_json(control_path)
        if current.get("token") == token:
            atomic_json(control_path, {**current,"active":False,"stopped_at":now()})


if __name__ == "__main__":
    sys.exit(main())
