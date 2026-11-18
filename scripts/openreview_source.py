"""Public OpenReview submission forums, separate from reviewed chemical resources."""
import json
import re
import sys
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlencode

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from chemwatch import api_json, atomic_json, now

PATH = ROOT / "dist/data/openreview.json"
TERMS = {
    "retrosynthesis": ["retrosynthesis", "retrosynthetic"],
    "coupling": ["cross coupling", "Suzuki coupling", "Suzuki Miyaura", "Buchwald Hartwig", "direct arylation"],
    "materials": ["materials property", "material property", "materials benchmark", "crystal structure prediction"],
    "yield": ["reaction yield"],
    "free-energy": ["free energy"],
    "selectivity": ["enantioselectivity", "enantioselective", "enantiomeric excess"],
    "bioactivity": ["bioactivity", "binding affinity"],
    "penicillin": ["penicillin"],
    "erythromycin": ["erythromycin"],
}
# A title match alone can refer to a different discipline or to a drug's clinical use.
CONTEXT = {
    "free-energy": r"molecul|ligand|chemical system|chemical reaction|hydrat|solvat|alchemical|protein|potential of mean force|atomistic|boltzmann distribution of",
    "bioactivity": r"drug|ligand|small.molecul|compound|chemistr|inhibitor|bindingdb|chembl|bioactivity",

    "penicillin": r"ferment|bioreactor|indpensim|bioprocess|manufactur|batch process|production process",
    "erythromycin": r"ferment|bioreactor|bioprocess|manufactur|batch process|production process",
}
ENDPOINTS = ("https://api2.openreview.net", "https://api.openreview.net")
PAGE_SIZE = 100


def url_for(term, endpoint, offset=0):
    return endpoint+"/notes/search?" + urlencode({
        "term":term, "type":"exact", "content":"title", "source":"forum",
        "limit":PAGE_SIZE, "offset":offset,
    })


def value(note, key):
    field = note.get("content",{}).get(key)
    if isinstance(field,dict):
        field = field.get("value")
    return field if isinstance(field,str) else ""


def day(stamp):
    if isinstance(stamp,(int,float)) and stamp > 0:
        return datetime.fromtimestamp(stamp/1000,timezone.utc).date().isoformat()
    return None


def normalize(note, topic, term):
    forum = note.get("forum")
    if not forum or forum != note.get("id") or note.get("replyto") or note.get("ddate"):
        return None
    invitations = note.get("invitations") or [note.get("invitation","")]
    creation = next((i for i in invitations if i.rsplit("/",1)[-1].lower() in
                     {"submission","blind_submission","paper_submission"}), None)
    if not creation:
        return None
    title = value(note,"title")
    words = re.sub(r"[\W_]+"," ",title.casefold())
    if not re.search(r"\b"+re.escape(term.casefold())+r"(?:s|es)?\b", words):
        return None
    pattern = CONTEXT.get(topic)
    if pattern and not re.search(pattern, title+" "+value(note,"abstract"), re.I):
        return None
    return {"forum":forum, "title":title, "url":"https://openreview.net/forum?id="+quote(forum,safe=""),
            "date":day(note.get("cdate")), "public_date":day(note.get("odate")),
            "venue":value(note,"venue") or note.get("domain") or creation.split("/-/")[0],
            "venue_id":value(note,"venueid"), "topics":[topic]}


def page_at(url):
    time.sleep(3)
    for attempt in range(3):
        try:
            return api_json(url)
        except HTTPError as exc:
            if exc.code != 429:
                raise
            hint = exc.headers.get("Retry-After", "").strip()
            delay = 60 * (attempt + 1)
            if hint:
                try:
                    delay = float(hint)
                except ValueError:
                    retry_at = parsedate_to_datetime(hint)
                    delay = retry_at.timestamp() - time.time()
            exc.close()
            if attempt == 2 or delay > 240:
                raise ValueError(f"Rate limited on {url}; Retry-After={hint or 'unspecified'}") from exc
            time.sleep(max(3, delay))


def query_notes(term, endpoint):
    offset = 0
    seen = set()
    while True:
        data = page_at(url_for(term,endpoint,offset))
        rows, count = data["notes"], data["count"]
        ids = {r["id"] for r in rows}
        if (not rows and offset<count) or (rows and not ids-seen):
            raise ValueError(f"incomplete pagination for {term}")
        seen.update(ids)
        yield from rows
        offset += len(rows)
        if offset >= count:
            if len(seen) != count:
                raise ValueError(f"result count changed for {term}")
            return


def collect():
    records = {}
    for topic, terms in TERMS.items():
        for term in terms:
            for endpoint in ENDPOINTS:
                for note in query_notes(term,endpoint):
                    item = normalize(note,topic,term)
                    if item:
                        row = records.setdefault(item["forum"],item)
                        if topic not in row["topics"]:
                            row["topics"].append(topic)
    return sorted(records.values(),key=lambda r:(r["date"] or "",r["forum"]),reverse=True)


def refresh(path=PATH):
    old = json.loads(path.read_text()) if path.exists() else {"items":[], "last_success":None}
    stamp = now()
    try:
        records = collect()
    except (OSError,ValueError,TypeError,KeyError,OverflowError) as exc:
        old.update(checked_at=stamp,error=str(exc))
        atomic_json(path,old)
        return ["OpenReview: "+str(exc)]
    atomic_json(path,{"checked_at":stamp,"last_success":stamp,"error":None,"terms":TERMS,
                      "queries":{k:[url_for(t,api) for t in ts for api in ENDPOINTS] for k,ts in TERMS.items()},
                      "items":records})
    return []


def inbox(snapshot, topic, limit):
    items = [r for r in snapshot["items"] if topic in r["topics"]]
    return {"last_success":snapshot.get("last_success"),"error":snapshot.get("error"),
            "query_url":"data/openreview.json","items":items[:limit]}


if __name__ == "__main__":
    errors = refresh()
    print(errors or f'{len(json.loads(PATH.read_text())["items"])} submission forums')
    sys.exit(2 if errors else 0)
