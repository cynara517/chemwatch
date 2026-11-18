"""Bounded topical searches. Results are a review inbox, never part of the counts."""
import json
import html
import re
import sys
import time
from urllib.error import HTTPError
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote, urlencode

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from chemwatch import api_json, atomic_json, now

# Search words are public so users can inspect what each source can miss.
TERMS = {
    "retrosynthesis":("retrosynthesis","retrosynthesis"),
    "coupling":("cross-coupling","cross-coupling"),
    "materials":("materials property","materials"),
    "yield":("reaction yield","reaction-yield"),
    "free-energy":("free energy","free-energy"),
    "selectivity":("enantioselectivity","enantioselectivity"),
    "penicillin":("penicillin fermentation","penicillin"),
    "erythromycin":("erythromycin fermentation","erythromycin"),
    "bioactivity":("bioactivity","bioactivity"),
}
LIMIT = 5
# Ambiguous platform names ("coupling", "penicillin") need chemical context.
CONTEXT = {
    "coupling": r"suzuki|buchwald|hartwig|cross.coupling reaction|cataly[sz]|palladium|aryl|chemical reaction",
    "materials": r"crystal|inorganic|material[s]? science|density functional|atomistic|materials propert|alloy|polymer",
    "free-energy": r"hydrat|solvat|binding|molecular dynamics|thermodynamic|chemical reaction|ligand",
    "penicillin": r"ferment|bioreactor|indpensim|bioprocess|soft.sensor|batch process",
    "erythromycin": r"ferment|bioreactor|bioprocess|soft.sensor|batch process",
}

def relevant(topic, metadata):
    pattern = CONTEXT.get(topic)
    return not pattern or bool(re.search(pattern, metadata, re.I))

def plain_title(title):
    return re.sub(r"</?(?:i|b|em|sup|sub)>", "", html.unescape(title), flags=re.I)



def crossref_json(url):
    # The public pool publishes a rate limit and may send Retry-After.
    for attempt in range(3):
        time.sleep(2)
        try:
            return api_json(url)
        except HTTPError as exc:
            if exc.code != 429 or attempt == 2:
                raise
            hint = (exc.headers or {}).get("Retry-After", "")
            delay = int(hint) if hint.isdigit() else 5 * (attempt+1)
            if delay > 45:
                raise
            exc.close()
            time.sleep(max(1, delay))


def search(source, topic):
    term, slug = TERMS[topic]
    if source == "papers":
        start = (date.today()-timedelta(days=365)).isoformat()
        query = f'TITLE_ABS:"{term}" AND (TITLE_ABS:dataset OR TITLE_ABS:benchmark) AND FIRST_PDATE:[{start} TO {date.today().isoformat()}]'
        url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urlencode(dict(query=query,format="json",pageSize=LIMIT,sort="FIRST_PDATE_D desc"))
        rows = api_json(url)["resultList"]["result"]
        items = [{"title":plain_title(r["title"]), "url":"https://europepmc.org/article/"+quote(r["source"],safe="")+"/"+quote(r["id"],safe=""), "date":r.get("firstPublicationDate")} for r in rows if r.get("id") and r.get("source") and r.get("title")]
    elif source == "crossref":
        start = (date.today()-timedelta(days=365)).isoformat()
        query = term + " dataset benchmark"
        url = "https://api.crossref.org/works?" + urlencode({
            "query.bibliographic":query, "filter":f"from-pub-date:{start},until-pub-date:{date.today()}",
            "rows":30, "select":"DOI,title,published",
        })
        items = []
        for row in crossref_json(url)["message"]["items"]:
            title = plain_title(next(iter(row.get("title",[])),""))
            words = title.lower().replace("-", " ").replace("–"," ")
            tokens = term.lower().replace("-", " ").split()
            if not all(t in words for t in tokens) or not re.search(r"data.set|dataset|database|benchmark|data collection", words):
                continue
            parts = row["published"]["date-parts"][0]
            stamp = "-".join([str(parts[0]),*(f"{n:02d}" for n in parts[1:])])
            items.append({"title":title,"url":"https://doi.org/"+quote(row["DOI"],safe="/"),"date":stamp})
        items = sorted(items,key=lambda r:r["date"],reverse=True)[:LIMIT]
    elif source == "github":
        query = f'"{term}" in:name,description fork:false'
        url = "https://api.github.com/search/repositories?" + urlencode(dict(q=query,sort="updated",order="desc",per_page=30))
        rows = api_json(url, github=True)["items"]
        items = [{"title":r["full_name"], "url":"https://github.com/"+quote(r["full_name"],safe="/"), "date":r["pushed_at"]} for r in rows
                 if relevant(topic, " ".join([r["full_name"],r.get("description") or "",*r.get("topics",[])]))
                 and re.search(r"data|benchmark|corpus|collection",r["full_name"]+" "+(r.get("description") or ""),re.I)][:LIMIT]
    else:
        query = slug
        url = "https://huggingface.co/api/datasets?" + urlencode(dict(search=query,sort="lastModified",direction=-1,limit=30,full="true"))
        rows = api_json(url)
        items = [{"title":r["id"], "url":"https://huggingface.co/datasets/"+quote(r["id"],safe="/"), "date":r.get("lastModified")} for r in rows if relevant(topic,r["id"]+" "+(r.get("description") or "")+" "+" ".join(r.get("tags",[])))][:LIMIT]
    return {"query":query, "query_url":url, "last_success":now(), "items":items}


def refresh():
    path = ROOT / "dist/data/discovery.json"
    old = json.loads(path.read_text()) if path.exists() else {}
    feeds = old.get("feeds",{})
    errors = []
    # Each platform handles its queries serially; platforms run independently.
    def platform(source):
        result = {}
        for topic in TERMS:
            key = source+"/"+topic
            try:
                result[key] = search(source,topic)
            except (ValueError,OSError,KeyError,TypeError) as exc:
                result[key] = {**feeds.get(key,{"items":[]}), "error":str(exc)}
        return result
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(platform, ("papers","crossref","github","huggingface")))
    feeds = {key:value for group in results for key,value in group.items()}
    from scripts import openreview_source
    openreview_source.refresh()
    snapshot = json.loads(openreview_source.PATH.read_text())
    for topic in openreview_source.TERMS:
        feeds["openreview/"+topic] = openreview_source.inbox(snapshot,topic,LIMIT)
    errors = [key+" "+value["error"] for key,value in feeds.items() if value.get("error")]
    atomic_json(path, {"checked_at":now(), "limit_per_query":LIMIT, "feeds":feeds, "errors":errors})
    return errors


if __name__ == "__main__":
    print(refresh())
