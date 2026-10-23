"""Dump a 기능정의서 menu page and its child pages to sources/<menu>/*.md (plain text).

Usage: python3 <skill>/scripts/fetch_spec.py <page_id> <out_dir>
Env: NOTION_API_KEY. Run through the workspace wrapper (scripts/run.sh) under bws-run.
The refresh crawler (worxsales-qa-refresh/scripts/crawl.py) re-reads the same tree later and also covers DB rows.
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from notion_api import call, children


def rich(rt):
    return "".join(t.get("plain_text", "") for t in rt)


def render(block_id, depth=0, pages=None):
    lines = []
    for b in children(block_id):
        t = b["type"]
        v = b.get(t, {})
        ind = "  " * depth
        if t == "child_page":
            pages.append((b["id"], v["title"]))
            lines.append(f"{ind}[하위 페이지] {v['title']}")
            continue
        if t == "child_database":
            lines.append(f"{ind}[DB] {v.get('title','')}")
            continue
        if t == "table":
            for row in children(b["id"]):
                cells = [rich(c) for c in row["table_row"]["cells"]]
                lines.append(ind + "| " + " | ".join(c.replace("\n", " ") for c in cells) + " |")
            continue
        text = rich(v.get("rich_text", [])) if isinstance(v, dict) else ""
        prefix = {"heading_1": "# ", "heading_2": "## ", "heading_3": "### ", "bulleted_list_item": "- ",
                  "numbered_list_item": "1. ", "to_do": "- [ ] ", "quote": "> ", "callout": "> ", "toggle": "▸ "}.get(t, "")
        if text or prefix:
            lines.append(ind + prefix + text)
        if b.get("has_children"):
            lines += render(b["id"], depth + 1, pages)
    return lines


def dump(page_id, out_dir, seen):
    if page_id in seen:
        return
    seen.add(page_id)
    p = call("GET", f"/pages/{page_id}")
    title = "".join(t["plain_text"] for prop in p["properties"].values() if prop["type"] == "title" for t in prop["title"])
    subs = []
    body = render(page_id, 0, subs)
    name = re.sub(r"[\\/:*?\"<>|\s]+", "_", title)[:80]
    with open(os.path.join(out_dir, name + ".md"), "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\nsource: https://app.notion.com/p/{page_id.replace('-', '')}\nlast_edited: {p['last_edited_time']}\n\n")
        f.write("\n".join(body) + "\n")
    print(name, len(body))
    for sid, _ in subs:
        dump(sid, out_dir, seen)


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] in ("-h", "--help"):
        sys.exit(__doc__)
    os.makedirs(sys.argv[2], exist_ok=True)
    dump(sys.argv[1], sys.argv[2], set())
