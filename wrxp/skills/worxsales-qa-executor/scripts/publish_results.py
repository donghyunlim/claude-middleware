"""Publish run results to the WorxSales scenario DB (Notion).

For every result JSON in <run_dir> (schema: references/result-schema.md):
- updates the row's 최근 판정 / 최근 실행일 / 최근 실행 빌드 / 최근 요약 properties
- rewrites the row page body in three layers: 결과 한눈에 -> 증거(그림·번호) -> 상세 기록(토글),
  plus a collapsed 이전 실행 기록 built from older result files of the same tc_id under <runs_root>.

Usage: python3 publish_results.py <run_dir> [--runs-root DIR] [--only TC-..,TC-..] [--dry-run]
Env: NOTION_API_KEY. Reads <QA_HOME or cwd>/config.json for scenario_db_id.
Stdlib only.
"""
import argparse, glob, json, mimetypes, os, time, urllib.error, urllib.request, uuid

API, VERSION = "https://api.notion.com/v1", "2022-06-28"
ICON = {"OK": "✅", "문제": "❌", "미구현": "🚧", "보류-기록": "⏸️", "알려진 차이": "↔️", "실행 불가": "⚠️"}
COLOR = {"OK": "green_background", "문제": "red_background", "미구현": "gray_background",
         "보류-기록": "yellow_background", "알려진 차이": "blue_background", "실행 불가": "orange_background"}
CIRCLED = lambda n: chr(0x2460 + n - 1) if 1 <= n <= 20 else str(n)


def call(method, path, body=None, raw=None, ctype="application/json; charset=utf-8"):
    data = raw if raw is not None else (json.dumps(body, ensure_ascii=False).encode() if body is not None else None)
    for attempt in range(6):
        req = urllib.request.Request(API + path, data=data, method=method, headers={
            "Authorization": "Bearer " + os.environ["NOTION_API_KEY"], "Notion-Version": VERSION, "Content-Type": ctype})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < 5:
                time.sleep(float(e.headers.get("Retry-After", 2 ** attempt))); continue
            raise RuntimeError(f"{method} {path} -> {e.code}: {e.read().decode()[:400]}")
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            if attempt < 5:
                time.sleep(2 ** attempt); continue
            raise


def rt(s, bold=False):
    s = s or ""
    out = [{"type": "text", "text": {"content": s[i:i + 1900]}} for i in range(0, len(s), 1900)][:100]
    if bold:
        for t in out: t["annotations"] = {"bold": True}
    return out


def p(s, bold=False): return {"type": "paragraph", "paragraph": {"rich_text": rt(s, bold)}}
def li(s): return {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": rt(s)}}
def num(s): return {"type": "numbered_list_item", "numbered_list_item": {"rich_text": rt(s)}}
def h3(s): return {"type": "heading_3", "heading_3": {"rich_text": rt(s)}}
def toggle(s, kids): return {"type": "toggle", "toggle": {"rich_text": rt(s, True), "children": kids[:90]}}
def labeled(label, value):
    return {"type": "paragraph", "paragraph": {"rich_text": rt(label + "  ", True) + rt(value)}}


def upload(path):
    name = os.path.basename(path)
    ctype = mimetypes.guess_type(name)[0] or "image/png"
    fu = call("POST", "/file_uploads", {"filename": name, "content_type": ctype})
    b = uuid.uuid4().hex
    raw = (f"--{b}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{name}\"\r\nContent-Type: {ctype}\r\n\r\n").encode() \
        + open(path, "rb").read() + f"\r\n--{b}--\r\n".encode()
    call("POST", f"/file_uploads/{fu['id']}/send", raw=raw, ctype=f"multipart/form-data; boundary={b}")
    return {"type": "image", "image": {"type": "file_upload", "file_upload": {"id": fu["id"]}}}


def rows_by_tc(db):
    out, cur = {}, None
    while True:
        r = call("POST", f"/databases/{db}/query", {"page_size": 100, **({"start_cursor": cur} if cur else {})})
        for pg in r["results"]:
            out["".join(t["plain_text"] for t in pg["properties"]["TC ID"]["rich_text"])] = pg["id"]
        if not r.get("has_more"): return out
        cur = r["next_cursor"]


def resolve(path, base):
    return path if os.path.isabs(path) else next((c for c in (os.path.join(base, path), os.path.join(os.getcwd(), path)) if os.path.exists(c)), path)


def body(r, base, older, dry):
    v = r["verdict"]
    head = [labeled("확인한 것", r.get("checked", "")), labeled("결과", r.get("outcome", ""))]
    if r.get("repro"):
        head.append(p("재현 순서", True))
        head += [num(s) for s in r["repro"]]
    blocks = [{"type": "callout", "callout": {"icon": {"emoji": ICON.get(v, "•")}, "color": COLOR.get(v, "default"),
               "rich_text": rt(f"{v} · {r.get('headline', '')}", True), "children": head}}]
    figs = r.get("figures", [])
    if figs:
        blocks.append(h3("증거"))
        for i, f in enumerate(figs, 1):
            blocks.append(p(f"그림 {i}. {f.get('caption', '')}", True))
            for key in ("zoom", "file"):
                if f.get(key):
                    img = resolve(f[key], base)
                    if os.path.exists(img):
                        blocks.append({"type": "image", "image": {"type": "external", "external": {"url": "https://example.invalid"}}} if dry else upload(img))
            blocks += [li(f"{CIRCLED(m['n'])} {m.get('label', '')}") for m in f.get("marks", [])]
    d = r.get("details", {})
    kids = [labeled("판정 근거", d.get("verdict_reason", "")),
            labeled("실행 환경", f"{r.get('run_id', '')} · {r.get('started_at', '')} ~ {r.get('ended_at', '')} · 빌드 {r.get('build', '')} · 역할 {r.get('role_context', '')} · 대상 {r.get('target_data', '')}"),
            p("수행한 액션과 관찰값", True)]
    kids += [li(f"{a.get('step', '')}. {a.get('action', '')} · {a.get('target', '')} → {a.get('observed', '')}") for a in d.get("actions", [])][:60]
    if d.get("name_mismatches"):
        kids.append(p("문서 이름 ↔ 앱 이름", True))
        kids += [li(f"{m.get('doc', '')} ↔ {m.get('app', '')}") for m in d["name_mismatches"]]
    if d.get("scenario_issue"):
        kids += [p("시나리오 확인 필요", True), p(d["scenario_issue"])]
    if d.get("side_findings"):
        kids.append(p("행 범위 밖 관찰", True))
        kids += [li(s) for s in d["side_findings"]]
    blocks.append(toggle("상세 기록 (개발자용)", kids))
    if older:
        blocks.append(toggle("이전 실행 기록", [li(f"{o.get('run_id', '')} · {o.get('ended_at', '')[:10]} · {o['verdict']} · {o.get('headline') or o.get('summary', '')}") for o in older]))
    return blocks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir"); ap.add_argument("--runs-root"); ap.add_argument("--only"); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    home = os.environ.get("QA_HOME", os.getcwd())
    db = json.load(open(os.path.join(home, "config.json"), encoding="utf-8"))["scenario_db_id"]
    runs_root = a.runs_root or os.path.dirname(os.path.abspath(a.run_dir))
    only = set(a.only.split(",")) if a.only else None
    pages = {} if a.dry_run else rows_by_tc(db)
    done = 0
    for f in sorted(glob.glob(os.path.join(a.run_dir, "TC-*.json"))):
        r = json.load(open(f, encoding="utf-8"))
        if only and r["tc_id"] not in only: continue
        if "headline" not in r:
            print("skip (old schema)", r["tc_id"]); continue
        older = []
        for g in glob.glob(os.path.join(runs_root, "*", r["tc_id"] + ".json")):
            if os.path.abspath(g) != os.path.abspath(f):
                o = json.load(open(g, encoding="utf-8")); o.setdefault("run_id", os.path.basename(os.path.dirname(g))); older.append(o)
        older.sort(key=lambda o: o.get("ended_at", ""), reverse=True)
        blocks = body(r, os.path.dirname(f), older, a.dry_run)
        if a.dry_run:
            print(r["tc_id"], len(blocks), "blocks"); done += 1; continue
        pid = pages.get(r["tc_id"])
        if not pid:
            print("skip (no row)", r["tc_id"]); continue
        day = (r.get("ended_at") or r.get("started_at") or "")[:10]
        call("PATCH", f"/pages/{pid}", {"properties": {
            "최근 판정": {"select": {"name": r["verdict"]}},
            "최근 실행일": {"date": {"start": day} if day else None},
            "최근 실행 빌드": {"rich_text": rt(r.get("build", ""))},
            "최근 요약": {"rich_text": rt(r.get("headline", ""))}}})
        while True:  # re-read the first page after each batch of deletes; cursors go stale once blocks are removed
            ch = call("GET", f"/blocks/{pid}/children?page_size=100")
            if not ch["results"]: break
            for b in ch["results"]: call("DELETE", f"/blocks/{b['id']}")
        for j in range(0, len(blocks), 80):
            call("PATCH", f"/blocks/{pid}/children", {"children": blocks[j:j + 80]})
        done += 1
        print("published", r["tc_id"], r["verdict"])
    print("done", done)


if __name__ == "__main__":
    main()
