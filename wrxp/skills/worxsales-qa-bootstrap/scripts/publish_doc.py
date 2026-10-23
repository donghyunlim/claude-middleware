"""Publish a simple Markdown file as a Notion child page (creates once, then replaces body).

Supports: #/##/### headings, - bullets, 1. numbered, ``` code fences, | tables |, > callout, plain paragraphs, `code` and **bold** inline.
Usage: python3 <skill>/scripts/publish_doc.py <md_file> <config_key>
Run from the QA workspace. The page goes under config.json parent_page_id; its id is saved under <config_key>
(e.g. db_doc_page_id for docs/DB_만들기.md, howto_page_id for docs/실행_방법.md). Env: NOTION_API_KEY.
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from notion_api import call, children

INLINE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))")


def rich(s):
    out = []
    for part in INLINE.split(s):
        if not part:
            continue
        ann, link = {}, None
        if part.startswith("**"):
            part, ann = part[2:-2], {"bold": True}
        elif part.startswith("`"):
            part, ann = part[1:-1], {"code": True}
        elif part.startswith("["):
            m = re.match(r"\[([^\]]+)\]\(([^)]+)\)", part)
            part, link = m.group(1), m.group(2)
        t = {"type": "text", "text": {"content": part[:1900], **({"link": {"url": link}} if link else {})}}
        if ann:
            t["annotations"] = ann
        out.append(t)
    return out


def blocks(md):
    lines, out, i = md.splitlines(), [], 0
    while i < len(lines):
        l = lines[i]
        if l.startswith("```"):
            lang, buf = l[3:].strip() or "plain text", []
            i += 1
            while not lines[i].startswith("```"):
                buf.append(lines[i]); i += 1
            out.append({"type": "code", "code": {"language": lang, "rich_text": [{"type": "text", "text": {"content": "\n".join(buf)[:1900]}}]}})
        elif l.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            i -= 1
            w = max(len(r) for r in rows)
            out.append({"type": "table", "table": {"table_width": w, "has_column_header": True, "has_row_header": False,
                        "children": [{"type": "table_row", "table_row": {"cells": [rich(c) for c in r + [""] * (w - len(r))]}} for r in rows]}})
        elif m := re.match(r"(#{1,3}) (.*)", l):
            k = f"heading_{len(m.group(1))}"
            out.append({"type": k, k: {"rich_text": rich(m.group(2))}})
        elif m := re.match(r"\s*- (.*)", l):
            out.append({"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": rich(m.group(1))}})
        elif m := re.match(r"\s*\d+\. (.*)", l):
            out.append({"type": "numbered_list_item", "numbered_list_item": {"rich_text": rich(m.group(1))}})
        elif l.startswith("> "):
            out.append({"type": "callout", "callout": {"rich_text": rich(l[2:]), "icon": {"emoji": "📌"}}})
        elif l.strip():
            out.append({"type": "paragraph", "paragraph": {"rich_text": rich(l)}})
        i += 1
    return out


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] in ("-h", "--help"):
        sys.exit(__doc__)
    md_file, key = sys.argv[1], sys.argv[2]
    cfg = json.load(open("config.json", encoding="utf-8"))
    md = open(md_file, encoding="utf-8").read()
    title, body = md.split("\n", 1)
    title = title.lstrip("# ").strip()
    bl = blocks(body)
    if key in cfg:
        pid = cfg[key]
        for b in children(pid):
            if not b.get("archived") and not b.get("in_trash"):
                call("DELETE", f"/blocks/{b['id']}")
        call("PATCH", f"/pages/{pid}", {"properties": {"title": {"title": rich(title)}}})
    else:
        p = call("POST", "/pages", {"parent": {"page_id": cfg["parent_page_id"]}, "icon": {"emoji": "🛠️"},
                                    "properties": {"title": {"title": rich(title)}}})
        pid = cfg[key] = p["id"]
        json.dump(cfg, open("config.json", "w"), ensure_ascii=False, indent=2)
    for j in range(0, len(bl), 90):
        call("PATCH", f"/blocks/{pid}/children", {"children": bl[j:j + 90]})
    print(pid, len(bl))
