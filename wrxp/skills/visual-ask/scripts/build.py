#!/usr/bin/env python3
"""spec.json과 그림 파일로 visual-ask 결정 페이지(index.html, img/)를 만든다.

사용법: python3 build.py spec.json out_dir [--max-width 1440] [--jpeg 74]

spec 안의 상대 경로는 spec.json이 있는 폴더를 기준으로 읽는다. 아티팩트로 게시할 때
쓸 `files` 묶음(files-1.json …, 묶음마다 200개 이하)을 out_dir에 함께 남긴다.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "template.html"
KINDS = ("approve", "choose")
CHUNK = 200


def safe(text):
    return re.sub(r"[^A-Za-z0-9_.~:@+-]", "-", str(text))[:200]


def fail(msg):
    sys.exit(f"spec 오류: {msg}")


def convert(src, dst, max_width, jpeg):
    """가능하면 줄이고 JPEG로 바꾼다. 도구가 없으면 원본을 복사한다."""
    if max_width or jpeg:
        if shutil.which("sips"):
            cmd = ["sips"]
            if jpeg:
                cmd += ["-s", "format", "jpeg", "-s", "formatOptions", str(jpeg)]
            if max_width:
                cmd += ["-Z", str(max_width)]
            if subprocess.run(cmd + [str(src), "--out", str(dst)], capture_output=True).returncode == 0:
                return
        try:
            from PIL import Image
            img = Image.open(src)
            if max_width and img.width > max_width:
                img = img.resize((max_width, round(img.height * max_width / img.width)))
            if jpeg:
                img.convert("RGB").save(dst, "JPEG", quality=jpeg)
            else:
                img.save(dst)
            return
        except Exception:
            pass
    shutil.copyfile(src, dst.with_suffix(src.suffix))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("out")
    ap.add_argument("--max-width", type=int, default=0)
    ap.add_argument("--jpeg", type=int, default=0, help="JPEG 품질(1~100). 0이면 원본 형식 유지")
    args = ap.parse_args()

    spec_path = Path(args.spec).resolve()
    base = spec_path.parent
    spec = json.loads(spec_path.read_text(encoding="utf8"))
    out = Path(args.out).resolve()
    img_dir = out / "img"
    img_dir.mkdir(parents=True, exist_ok=True)

    if not spec.get("title"):
        fail("title이 없습니다")
    default_kind = spec.get("kind", "approve")
    seen_items, seen_pages, published = set(), set(), {}
    sections = []
    for si, s in enumerate(spec.get("sections", [])):
        pages = []
        for p in s.get("pages", []):
            pid = safe(p.get("id") or fail(f"{s.get('title')}의 페이지에 id가 없습니다"))
            if pid in seen_pages:
                fail(f"페이지 id가 겹칩니다: {pid}")
            seen_pages.add(pid)
            items = []
            for it in p.get("items", []):
                key = safe(f"{pid}__{it.get('id') or fail(f'{pid}의 항목에 id가 없습니다')}")
                if key in seen_items:
                    fail(f"항목 id가 겹칩니다: {key}")
                seen_items.add(key)
                kind = it.get("kind", default_kind)
                if kind not in KINDS:
                    fail(f"{key}: kind는 {KINDS} 중 하나여야 합니다")
                opts = []
                for oi, o in enumerate(it.get("options", [])):
                    oid = safe(o.get("id") or f"o{oi}")
                    view = {"id": oid, "label": o.get("label", oid)}
                    if o.get("image"):
                        src = (base / o["image"]).resolve()
                        if not src.exists():
                            fail(f"{key}/{oid}: 그림이 없습니다: {src}")
                        dst = img_dir / f"{key}-{oid}{'.jpg' if args.jpeg else src.suffix}"
                        if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
                            convert(src, dst, args.max_width, args.jpeg)
                        if not dst.exists():
                            dst = dst.with_suffix(src.suffix)
                        view["src"] = f"img/{dst.name}"
                        published[view["src"]] = str(dst)
                    elif o.get("html_file"):
                        view["html"] = (base / o["html_file"]).read_text(encoding="utf8")
                    elif o.get("html"):
                        view["html"] = o["html"]
                    else:
                        view["text"] = o.get("text", "")
                    if o.get("height"):
                        view["height"] = int(o["height"])
                    opts.append(view)
                if not opts:
                    fail(f"{key}: options가 비었습니다")
                if kind == "choose" and len(opts) < 2:
                    fail(f"{key}: choose 항목은 선택지가 2개 이상이어야 합니다")
                rec = it.get("recommend")
                if rec is not None and safe(rec) not in {o["id"] for o in opts}:
                    fail(f"{key}: recommend가 선택지 id에 없습니다")
                items.append({"key": key, "title": it.get("title", it["id"]), "kind": kind,
                              "question": it.get("question", ""), "rev": int(it.get("rev", 1)),
                              "recommend": safe(rec) if rec is not None else None, "options": opts})
            pages.append({"key": pid, "title": p.get("title", pid), "badge": p.get("badge"),
                          "summary": p.get("summary", ""), "notes": p.get("notes", []), "items": items})
        sections.append({"title": s.get("title", f"묶음 {si + 1}"), "badge": s.get("badge"), "pages": pages})

    data = {"id": safe(spec.get("id") or spec["title"]), "title": spec["title"], "mark": spec.get("mark"),
            "note": spec.get("note", ""), "sections": sections}
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.read_text(encoding="utf8")
    title = spec["title"].replace("&", "&amp;").replace("<", "&lt;")
    html = html.replace("__TITLE__", title, 1).replace("/*__DATA__*/null", payload, 1)
    (out / "index.html").write_text(html, encoding="utf8")

    for old in out.glob("files-*.json"):
        old.unlink()
    entries = sorted(published.items())
    for n in range(0, len(entries), CHUNK):
        chunk = dict(entries[n:n + CHUNK])
        (out / f"files-{n // CHUNK + 1}.json").write_text(json.dumps(chunk, ensure_ascii=False, indent=1), encoding="utf8")

    size = sum(Path(p).stat().st_size for p in published.values())
    print(f"pages={len(seen_pages)} items={len(seen_items)} images={len(published)} "
          f"image_mb={size / 1e6:.1f} file_batches={-(-len(entries) // CHUNK)} out={out}")


if __name__ == "__main__":
    main()
