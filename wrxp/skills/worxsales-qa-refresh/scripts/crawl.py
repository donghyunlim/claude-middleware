"""Crawl every watched Notion root from the top and write a full manifest.

Usage: python3 crawl.py <watch.json> <out_dir>
Writes <out_dir>/manifest.json and <out_dir>/pages/<page_id>.md (same header format as fetch_spec.py).

Deliberately re-reads everything on every run. A parent page's last_edited_time does not change when a
child changes, and new children can appear inside column/toggle/synced blocks or as database rows, so
nothing is skipped by date. Pages the integration cannot open are recorded as errors, not dropped.
Root kinds:
  tree      every block, child page, child database row and file under the root, with page text
  discover  titles only, `depth` levels down; flags pages/databases whose title matches `keywords`
"""
import hashlib, json, os, sys, threading, urllib.parse
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _notion import call, children, norm, page_title, query

CONTAINER_SKIP = {"child_page", "child_database"}
LAYOUT = {"column_list", "column", "toggle", "synced_block", "callout", "heading_1", "heading_2", "heading_3", "quote"}
PREFIX = {"heading_1": "# ", "heading_2": "## ", "heading_3": "### ", "bulleted_list_item": "- ", "numbered_list_item": "1. ",
          "to_do": "- [ ] ", "quote": "> ", "callout": "> ", "toggle": "▸ "}


def rich(rt):
    return "".join(t.get("plain_text", "") for t in rt or [])


def mentions(rt):
    return [norm(t["mention"].get("page", {}).get("id") or t["mention"].get("database", {}).get("id"))
            for t in rt or [] if t.get("type") == "mention" and t["mention"].get("type") in ("page", "database")]


def prop_value(v):
    t = v.get("type"); x = v.get(t)
    if t in ("title", "rich_text"): return rich(x)
    if t in ("select", "status"): return (x or {}).get("name") or ""
    if t == "multi_select": return ", ".join(o["name"] for o in x or [])
    if t == "date": return " ~ ".join(filter(None, [(x or {}).get("start"), (x or {}).get("end")]))
    if t in ("number", "checkbox", "url", "email", "phone_number"): return "" if x is None else str(x)
    if t == "people": return ", ".join(u.get("name") or u.get("id", "") for u in x or [])
    if t == "relation": return ", ".join(norm(r["id"]) for r in x or [])
    if t == "files": return ", ".join(f["name"] for f in x or [])
    return ""  # created_time, last_edited_time, formula, rollup: derived, not authored


def prop_lines(p):
    out = [f"[속성] {k}: {prop_value(v)}" for k, v in sorted(p.get("properties", {}).items())
           if v.get("type") != "title" and prop_value(v)]
    return out + [""] if out else []


class Crawler:
    def __init__(self, out):
        self.out, self.nodes, self.seen, self.lock, self.stop = out, {}, set(), threading.Lock(), set()
        os.makedirs(os.path.join(out, "pages"), exist_ok=True)

    def render(self, block_id, depth, found):
        """Text in fetch_spec.py format; collects child pages/databases, links and files into `found`."""
        lines = []
        for b in children(block_id):
            t, v, ind = b["type"], b.get(b["type"], {}), "  " * depth
            if t == "child_page":
                found["pages"].append(norm(b["id"])); lines.append(f"{ind}[하위 페이지] {v['title']}"); continue
            if t == "child_database":
                found["dbs"].append(norm(b["id"])); lines.append(f"{ind}[DB] {v.get('title', '')}"); continue
            if t == "link_to_page":
                found["links"].append(norm(v.get("page_id") or v.get("database_id"))); lines.append(f"{ind}[링크] {found['links'][-1]}"); continue
            if t in ("file", "pdf", "image", "video"):
                name = v.get("name") or rich(v.get("caption")) or urllib.parse.unquote(
                    (v.get("file") or v.get("external") or {}).get("url", "").split("?")[0].rsplit("/", 1)[-1])
                found["files"].append(name); lines.append(f"{ind}[파일] {name}"); continue
            if t == "table":
                for row in children(b["id"]):
                    cells = [rich(c) for c in row["table_row"]["cells"]]
                    for c in row["table_row"]["cells"]: found["links"] += mentions(c)
                    lines.append(ind + "| " + " | ".join(c.replace("\n", " ") for c in cells) + " |")
                continue
            rt = v.get("rich_text", []) if isinstance(v, dict) else []
            found["links"] += mentions(rt)
            text = rich(rt)
            if text or PREFIX.get(t):
                lines.append(ind + PREFIX.get(t, "") + text)
            if b.get("has_children") and t not in CONTAINER_SKIP:
                lines += self.render(b["id"], depth + 1, found)
        return lines

    def add(self, nid, **kw):
        """Fully crawled nodes always win; a title-only discover record never replaces one."""
        with self.lock:
            if kw["kind"] == "discovered" and nid in self.nodes: return
            self.nodes[nid] = {"id": nid, **kw}

    def claim(self, nid):
        with self.lock:
            if nid in self.seen: return False
            self.seen.add(nid); return True

    def page(self, pid, parent, path, root, row_of=None):
        """Returns follow-up tasks (child pages and databases) instead of recursing, so pages crawl in parallel."""
        pid = norm(pid)
        if not self.claim(pid): return []
        try:
            p = call("GET", f"/pages/{pid}")
        except RuntimeError as e:
            self.add(pid, kind="error", parent=parent, path=path, root=root, error=str(e)[:200]); return []
        title = page_title(p)
        found = {"pages": [], "dbs": [], "links": [], "files": []}
        for prop in p.get("properties", {}).values():  # database rows keep files and links in properties
            if prop.get("type") == "files": found["files"] += [f["name"] for f in prop["files"]]
            if prop.get("type") == "rich_text": found["links"] += mentions(prop["rich_text"])
        # Database rows (e.g. policy decisions) keep 상태·결정 내용 in properties, not in the body, so a decision
        # can change without any body edit. Properties go into the text and the hash.
        props = prop_lines(p) if row_of else []
        body = props + self.render(pid, 0, found)
        text = f"# {title}\n\nsource: https://app.notion.com/p/{pid}\nlast_edited: {p['last_edited_time']}\n\n" + "\n".join(body) + "\n"
        open(os.path.join(self.out, "pages", pid + ".md"), "w", encoding="utf-8").write(text)
        self.add(pid, kind="db_row" if row_of else "page", title=title, parent=parent, path=path, root=root,
                 last_edited=p["last_edited_time"], archived=bool(p.get("archived") or p.get("in_trash")),
                 sha1=hashlib.sha1("\n".join(body).encode()).hexdigest(), files=found["files"],
                 links=sorted(set(found["links"]) - {pid}), children=found["pages"] + found["dbs"])
        print(f"page {len(self.nodes):4d} {title[:60]}", flush=True)
        return [(self.page, (c, pid, path + [title], root)) for c in found["pages"]] + \
               [(self.database, (d, pid, path + [title], root)) for d in found["dbs"]]

    def database(self, did, parent, path, root, limit=5000):
        did = norm(did)
        if not self.claim(did): return []
        try:
            d = call("GET", f"/databases/{did}")
            rows = query(did, limit)
        except RuntimeError as e:
            self.add(did, kind="error", parent=parent, path=path, root=root, error=str(e)[:200]); return []
        title = page_title(d)
        self.add(did, kind="database", title=title, parent=parent, path=path, root=root, last_edited=d["last_edited_time"],
                 archived=bool(d.get("archived") or d.get("in_trash")), rows=len(rows), children=[norm(r["id"]) for r in rows])
        return [(self.page, (r["id"], did, path + [title], root, did)) for r in rows]

    def discover(self, bid, path, root, depth, keywords, nest=0):
        """Titles only. Walks layout blocks (columns, toggles, synced blocks, callouts) up to 3 levels deep so
        pages placed inside them are found too; text-only blocks such as lists are not opened."""
        if depth < 0: return
        for b in children(bid):
            t = b["type"]
            if t in ("child_page", "child_database"):
                nid, title = norm(b["id"]), b[t].get("title", "")
                if nid in self.stop: continue  # a tree root: crawled in full elsewhere
                hit = any(k.lower() in title.lower() for k in keywords)
                self.add(nid, kind="discovered", title=title, parent=norm(bid), path=path, root=root,
                         last_edited=b.get("last_edited_time"), keyword_hit=hit)
                print(f"discover {'*' if hit else ' '} {' / '.join(path + [title])[:90]}", flush=True)
                if t == "child_page": self.discover(nid, path + [title], root, depth - 1, keywords)
            elif b.get("has_children") and nest < 3 and t in LAYOUT:
                self.discover(b["id"], path, root, depth, keywords, nest + 1)


def main():
    watch, out = json.load(open(sys.argv[1], encoding="utf-8")), sys.argv[2]
    c = Crawler(out)
    c.stop = {norm(r["id"]) for r in watch["roots"] if r["kind"] == "tree"}
    tasks = []
    for r in watch["roots"]:
        rid = norm(r["id"])
        if r["kind"] == "tree":
            tasks.append((c.database, (rid, None, [], r["name"], r.get("row_limit", 5000))) if r.get("is_database")
                         else (c.page, (rid, None, [], r["name"])))
        elif r["kind"] == "discover":
            tasks.append((lambda *a: c.discover(*a) or [], (rid, [r["name"]], r["name"], r.get("depth", 2), r.get("keywords", []))))
    # 3 workers stays under Notion's ~3 requests/s average; 429s are retried in _notion.call
    with ThreadPoolExecutor(int(os.environ.get("CRAWL_WORKERS", "3"))) as ex:
        running = {ex.submit(fn, *args) for fn, args in tasks}
        while running:
            finished, running = wait(running, return_when=FIRST_COMPLETED)
            for f in finished:
                running |= {ex.submit(fn, *args) for fn, args in f.result()}
    json.dump({"roots": watch["roots"], "nodes": c.nodes}, open(os.path.join(out, "manifest.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    kinds = {}
    for n in c.nodes.values(): kinds[n["kind"]] = kinds.get(n["kind"], 0) + 1
    print("manifest", os.path.join(out, "manifest.json"), kinds)


if __name__ == "__main__":
    main()
