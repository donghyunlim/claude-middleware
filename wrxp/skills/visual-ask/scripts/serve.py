#!/usr/bin/env python3
"""아티팩트를 쓸 수 없을 때 결정 페이지를 이 컴퓨터에서만 띄우고 답을 answers.json에 모은다.

사용법: python3 serve.py out_dir [--port 8790]

127.0.0.1에만 열린다. GET /api/answers는 지금까지의 답을, POST /api/answers는
{항목 키: 답} 묶음을 받아 out_dir/answers.json에 합쳐 쓴다.
"""
import argparse
import json
import os
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MAX_BODY = 256 * 1024
LOCK = threading.Lock()
SKELETON = ('<!doctype html><html><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            '</head><body>%s</body></html>')


class Handler(SimpleHTTPRequestHandler):
    answers_path: Path
    # 페이지에는 charset 선언이 없으므로(아티팩트가 감싸 줌) 로컬에서는 응답 헤더로 알린다.
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map,
                      ".html": "text/html; charset=utf-8", ".json": "application/json; charset=utf-8"}

    def log_message(self, *args):
        pass

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf8")
        self.send_response(code)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("cache-control", "no-store")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _load(self):
        try:
            return json.loads(self.answers_path.read_text(encoding="utf8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/answers":
            with LOCK:
                return self._json(200, self._load())
        if path in ("/", "/index.html"):
            # 아티팩트가 게시 때 씌우는 문서 뼈대(doctype, charset, viewport)를 로컬에서도 씌운다.
            page = (Path(self.directory) / "index.html").read_text(encoding="utf8")
            body = (SKELETON % page).encode("utf8")
            self.send_response(200)
            self.send_header("content-type", "text/html; charset=utf-8")
            self.send_header("cache-control", "no-store")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        return super().do_GET()

    def do_POST(self):
        if self.path.split("?", 1)[0] != "/api/answers":
            return self._json(404, {"error": "not found"})
        length = int(self.headers.get("content-length") or 0)
        if length <= 0 or length > MAX_BODY:
            return self._json(413, {"error": "body size"})
        try:
            patch = json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            return self._json(400, {"error": "json"})
        if not isinstance(patch, dict) or not all(isinstance(k, str) and isinstance(v, dict) for k, v in patch.items()):
            return self._json(400, {"error": "shape"})
        with LOCK:
            data = self._load()
            data.update(patch)
            tmp = self.answers_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf8")
            os.replace(tmp, self.answers_path)
        return self._json(200, {"ok": True})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--port", type=int, default=8790)
    args = ap.parse_args()
    root = Path(args.out).resolve()
    if not (root / "index.html").exists():
        raise SystemExit(f"{root}/index.html이 없습니다. build.py를 먼저 실행하십시오.")
    Handler.answers_path = root / "answers.json"
    server = ThreadingHTTPServer(("127.0.0.1", args.port), partial(Handler, directory=str(root)))
    print(f"http://127.0.0.1:{args.port}/  답: {Handler.answers_path}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
