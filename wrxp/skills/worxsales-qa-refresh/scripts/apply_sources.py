"""Apply a diff report to the local sources/ copy. Dry run unless --apply.

Usage: python3 apply_sources.py <watch.json> <new_manifest_dir> <report.json> [--apply] [--date YYYY-MM-DD]

- local_stale  : old file copied to sources/_snapshot_<date>/<same path>, then replaced with the crawled text
                 (renamed when the page title changed; the old name stays only in the snapshot)
- local_missing: written next to the nearest ancestor page that already has a local file; with no such
                 ancestor it goes to sources/_unmapped/ and must be placed by hand
- local_orphan : moved to sources/_stale/ (page gone, archived or unreadable)
- mockup       : every new or newer version of the watched family is downloaded to sources/_mockups/
                 with a .txt text extraction beside it
Writes <new_manifest_dir>/applied.json: the files each change touched, for the scenario update step.
"""
import argparse, datetime, glob, html, json, os, re, shutil, sys, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _notion import call


def fname(title):
    return re.sub(r"[\\/:*?\"<>|\s]+", "_", title)[:80] + ".md"


HANGUL_STR = re.compile(r"""(["'`])((?:(?!\1)[^\\\n]|\\.){0,400}?[\uac00-\ud7a3](?:(?!\1)[^\\\n]|\\.){0,400}?)\1""")


def html_text(raw):
    """Visible text plus, for single-page mockups whose screens live in script code, every Korean string
    literal in order of first appearance (one per line), so two versions can be compared with diff."""
    seen, lits = set(), []
    for m in HANGUL_STR.finditer(raw):
        v = m.group(2).strip()
        if v and v not in seen: seen.add(v); lits.append(v)
    raw = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<br\s*/?>|</(p|div|li|h[1-6]|tr|section)>", "\n", raw)
    visible = [l.strip() for l in html.unescape(re.sub(r"<[^>]+>", " ", raw)).splitlines() if l.strip()]
    return "\n".join(visible + ["", "## script strings"] + lits)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("watch"); ap.add_argument("new"); ap.add_argument("report")
    ap.add_argument("--apply", action="store_true"); ap.add_argument("--date", default=datetime.date.today().isoformat())
    a = ap.parse_args()
    w = json.load(open(a.watch, encoding="utf-8")); rep = json.load(open(a.report, encoding="utf-8"))
    nodes = json.load(open(os.path.join(a.new, "manifest.json"), encoding="utf-8"))["nodes"]
    src = w.get("sources_dir", "sources"); snap = os.path.join(src, f"_snapshot_{a.date}")
    done = {"replaced": [], "added": [], "unmapped": [], "stale": [], "mockups": []}

    def crawled(i): return open(os.path.join(a.new, "pages", i + ".md"), encoding="utf-8").read()

    def do(fn, *args):
        if a.apply: fn(*args)

    def keep_old(f):
        dst = os.path.join(snap, os.path.relpath(f, src)); os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy2(f, dst)

    for s in rep.get("local_stale", []):
        f, n = s["file"], nodes[s["id"]]
        target = os.path.join(os.path.dirname(f), fname(n["title"]))
        do(keep_old, f)
        if target != f: do(os.remove, f)
        do(lambda t, i: open(t, "w", encoding="utf-8").write(crawled(i)), target, s["id"])
        done["replaced"].append({"id": s["id"], "file": target, "was": f})

    owner = {}
    for s in rep.get("local_stale", []): owner[s["id"]] = os.path.dirname(s["file"])
    for f in glob.glob(os.path.join(src, "**", "*.md"), recursive=True):
        m = re.search(r"/p/([0-9a-f]{32})", open(f, encoding="utf-8").read(600))
        if m: owner.setdefault(m.group(1), os.path.dirname(f))
    for s in rep.get("local_missing", []):
        p, folder = nodes[s["id"]].get("parent"), None
        while p and not folder:
            folder = owner.get(p); p = nodes.get(p, {}).get("parent")
        key = "added" if folder and not os.path.basename(folder).startswith("_") else "unmapped"
        folder = folder if key == "added" else os.path.join(src, "_unmapped")
        target = os.path.join(folder, fname(s["title"]))
        do(os.makedirs, folder, 0o777, True)
        do(lambda t, i: open(t, "w", encoding="utf-8").write(crawled(i)), target, s["id"])
        owner[s["id"]] = folder
        done[key].append({"id": s["id"], "file": target, "path": s["path"]})

    for s in rep.get("local_orphan", []):
        for f in s["files"]:
            dst = os.path.join(src, "_stale", os.path.relpath(f, src))
            do(os.makedirs, os.path.dirname(dst), 0o777, True); do(shutil.move, f, dst)
            done["stale"].append({"id": s["id"], "file": f, "moved_to": dst, "state": s["state"]})

    fam = w["mockup"]["family"]; pat = re.compile(w["mockup"]["pattern"])
    for e in rep.get("mockup", []):
        if e["family"] != fam: continue
        want = set(e["new_versions"]) | ({e["latest"]} if e.get("newer_than_used") else set())
        used = e.get("used_version")  # the comparison baseline, fetched once if it is not local yet
        if used and used in e["versions"] and not glob.glob(os.path.join(src, "_mockups", f"*_v{used}.txt")): want.add(used)
        page = call("GET", f"/pages/{e['page']}") if a.apply else {"properties": {}}
        urls = {f["name"]: (f.get("file") or f.get("external") or {}).get("url")
                for prop in page["properties"].values() if prop.get("type") == "files" for f in prop["files"]}
        for name, url in urls.items():
            g = pat.fullmatch(name)
            if not g or g["ver"] not in want or not url: continue
            dst = os.path.join(src, "_mockups", name); os.makedirs(os.path.dirname(dst), exist_ok=True)
            raw = urllib.request.urlopen(url, timeout=120).read()
            open(dst, "wb").write(raw)
            open(dst[:-5] + ".txt", "w", encoding="utf-8").write(html_text(raw.decode("utf-8", "replace")))
            done["mockups"].append({"version": g["ver"], "file": dst})
        if not a.apply: done["mockups"] += [{"version": v, "file": "(dry run)"} for v in sorted(want)]

    if a.apply: json.dump(done, open(os.path.join(a.new, "applied.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(("applied" if a.apply else "dry run"), {k: len(v) for k, v in done.items()})
    for k in ("unmapped",):
        for x in done[k]: print("  UNMAPPED", x["file"], " / ".join(x["path"]))


if __name__ == "__main__":
    main()
