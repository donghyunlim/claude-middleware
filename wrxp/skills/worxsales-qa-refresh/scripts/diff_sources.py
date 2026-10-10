"""Compare a new crawl with the last good crawl and with the local sources/ copy.

Usage: python3 diff_sources.py <watch.json> <new_manifest_dir> [--prev <old_manifest_dir>] [--out report.json]
Exit 0 when nothing needs attention, 1 otherwise. Prints a Korean summary.

Nothing is assumed unchanged: a page the local copy does not have, a local file whose page vanished, an
unreadable page, a new attachment version, a link that leaves the crawled tree and a newly discovered
keyword page all count as attention until they are applied or listed in watch.json "ignore" with a reason.
"""
import argparse, glob, json, os, re

HEADER_ID = re.compile(r"source: https://app\.notion\.com/p/([0-9a-f]{32})")


def load(d):
    return json.load(open(os.path.join(d, "manifest.json"), encoding="utf-8"))["nodes"] if d else {}


MARKERS = ("[파일] ", "[링크] ")  # crawl.py adds these; fetch_spec.py copies do not have them


def body(text):
    parts = text.split("\n\n", 2)  # "# title", "source/last_edited", body
    lines = (parts[2] if len(parts) == 3 else "").splitlines()
    return "\n".join(l for l in lines if not l.lstrip().startswith(MARKERS)).strip()


def vtuple(v):
    return tuple(int(x) for x in v.split("."))


def local_sources(src):
    out = {}
    for f in glob.glob(os.path.join(src, "**", "*.md"), recursive=True):
        if any(part.startswith("_") for part in os.path.relpath(f, src).split(os.sep)[:-1]):
            continue  # _snapshot_*, _stale, _mockups: history, not the current copy
        m = HEADER_ID.search(open(f, encoding="utf-8").read(600))
        if m: out.setdefault(m.group(1), []).append(f)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("watch"); ap.add_argument("new"); ap.add_argument("--prev"); ap.add_argument("--out")
    a = ap.parse_args()
    w = json.load(open(a.watch, encoding="utf-8"))
    ignore = w.get("ignore", {})
    cur, prev = load(a.new), load(a.prev)
    tree_roots = {r["name"] for r in w["roots"] if r["kind"] == "tree"}
    pages = {k: n for k, n in cur.items() if n["kind"] in ("page", "db_row")}
    rep = {k: [] for k in ("added", "removed", "renamed", "moved", "edited", "archived", "errors", "local_missing",
                           "local_orphan", "local_stale", "local_duplicate", "mockup", "discovered_new", "external_links_new")}

    for k, n in cur.items():
        if n["kind"] == "error" and k not in ignore:
            rep["errors"].append({"id": k, "path": n.get("path"), "error": n.get("error")})
    if prev:
        for k, n in pages.items():
            o = prev.get(k)
            if not o or o["kind"] not in ("page", "db_row"):
                rep["added"].append({"id": k, "title": n["title"], "path": n["path"]}); continue
            if o.get("title") != n["title"]: rep["renamed"].append({"id": k, "was": o.get("title"), "now": n["title"]})
            if o.get("parent") != n.get("parent"): rep["moved"].append({"id": k, "title": n["title"], "was": o.get("path"), "now": n["path"]})
            if o.get("sha1") != n.get("sha1"): rep["edited"].append({"id": k, "title": n["title"], "last_edited": n.get("last_edited")})
        for k, o in prev.items():
            if o["kind"] in ("page", "db_row") and k not in pages:
                rep["removed"].append({"id": k, "title": o.get("title"), "path": o.get("path")})
    for k, n in pages.items():
        if n.get("archived"): rep["archived"].append({"id": k, "title": n["title"]})

    # local copy coverage: every crawled spec page needs exactly one current local file with the same text
    src = local_sources(w.get("sources_dir", "sources"))
    spec_root = w["roots"][0]["name"]
    for k, n in pages.items():
        if n["root"] != spec_root or k in ignore: continue
        files = src.get(k)
        if not files:
            rep["local_missing"].append({"id": k, "title": n["title"], "path": n["path"]}); continue
        if len(files) > 1: rep["local_duplicate"].append({"id": k, "files": files})
        new_text = open(os.path.join(a.new, "pages", k + ".md"), encoding="utf-8").read()
        for f in files:
            if body(open(f, encoding="utf-8").read()) != body(new_text):
                rep["local_stale"].append({"id": k, "title": n["title"], "file": f, "now_edited": n.get("last_edited")})
    for k, files in src.items():
        if k not in pages and k not in ignore:
            rep["local_orphan"].append({"id": k, "files": files, "state": cur.get(k, {}).get("kind", "not found")})

    # attachments with versions: latest by version number, never by list position
    pat, m = re.compile(w["mockup"]["pattern"]), w["mockup"]
    fams, prev_names = {}, {f for n in prev.values() for f in n.get("files", [])}
    for k, n in pages.items():
        for f in n.get("files", []):
            g = pat.fullmatch(f)
            if g: fams.setdefault(g["family"], {})[g["ver"]] = {"page": k, "title": n["title"], "name": f, "new": bool(prev) and f not in prev_names}
    for fam, vers in sorted(fams.items()):
        latest = max(vers, key=vtuple)
        entry = {"family": fam, "latest": latest, "page": vers[latest]["page"], "versions": sorted(vers, key=vtuple),
                 "new_versions": sorted((v for v, x in vers.items() if x["new"]), key=vtuple)}
        if fam == m["family"]:
            entry["used_version"] = m.get("used_version")
            entry["newer_than_used"] = bool(m.get("used_version")) and vtuple(latest) > vtuple(m["used_version"])
        if entry["new_versions"] or entry.get("newer_than_used"): rep["mockup"].append(entry)

    for k, n in cur.items():
        if n["kind"] == "discovered" and n.get("keyword_hit") and k not in pages and k not in ignore and k not in prev:
            rep["discovered_new"].append({"id": k, "title": n["title"], "path": n["path"]})
    known = set(cur) | set(ignore)
    prev_links = {l for n in prev.values() for l in n.get("links", [])}
    for k, n in pages.items():
        for l in n.get("links", []):
            if l and l not in known and (not prev or l not in prev_links):
                rep["external_links_new"].append({"from": k, "from_title": n["title"], "to": l})

    if not prev:
        # First run: everything would look "new". Keep the lists as the baseline record; later runs flag only additions.
        rep["baseline_discovered"] = rep.pop("discovered_new"); rep["baseline_external_links"] = rep.pop("external_links_new")
        rep["note"] = "첫 실행: added/removed/edited 비교는 건너뛰고(로컬 사본 대조는 수행), 발견 페이지·외부 링크는 기준 목록으로만 남겼습니다."
    attention = {k: len(v) for k, v in rep.items() if isinstance(v, list) and v and not k.startswith("baseline_")}
    rep["attention"] = attention
    if a.out: json.dump(rep, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"crawled pages={len(pages)} errors={len(rep['errors'])} local files={sum(len(v) for v in src.values())}")
    for k, v in attention.items(): print(f"  {k}: {v}")
    for e in rep["mockup"]:
        print(f"  mockup {e['family']}: latest v{e['latest']} (used {e.get('used_version')}) new={e['new_versions']}")
    raise SystemExit(1 if attention else 0)


if __name__ == "__main__":
    main()
