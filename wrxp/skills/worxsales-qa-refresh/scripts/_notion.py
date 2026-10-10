"""Minimal Notion REST client shared by the refresh scripts (stdlib only). Requires NOTION_API_KEY."""
import json, os, time, urllib.error, urllib.request

API, VERSION = "https://api.notion.com/v1", "2022-06-28"


def call(method, path, body=None):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    for attempt in range(8):
        req = urllib.request.Request(API + path, data=data, method=method, headers={
            "Authorization": "Bearer " + os.environ["NOTION_API_KEY"], "Notion-Version": VERSION,
            "Content-Type": "application/json; charset=utf-8"})
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < 7:
                time.sleep(float(e.headers.get("Retry-After", 2 ** attempt))); continue
            raise RuntimeError(f"{method} {path} -> {e.code}: {e.read().decode('utf-8')[:400]}")
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            if attempt < 7:
                time.sleep(min(60, 2 ** attempt)); continue
            raise


def children(block_id):
    out, cur = [], None
    while True:
        r = call("GET", f"/blocks/{block_id}/children?page_size=100" + (f"&start_cursor={cur}" if cur else ""))
        out += r["results"]
        if not r.get("has_more"): return out
        cur = r["next_cursor"]


def query(db_id, limit=5000):
    out, cur = [], None
    while len(out) < limit:
        r = call("POST", f"/databases/{db_id}/query", {"page_size": 100, **({"start_cursor": cur} if cur else {})})
        out += r["results"]
        if not r.get("has_more"): break
        cur = r["next_cursor"]
    return out


def page_title(p):
    if p.get("object") == "database":
        return "".join(t.get("plain_text", "") for t in p.get("title", []))
    return "".join(t.get("plain_text", "") for v in p.get("properties", {}).values() if v.get("type") == "title" for t in v["title"])


def norm(i):
    return (i or "").replace("-", "")
