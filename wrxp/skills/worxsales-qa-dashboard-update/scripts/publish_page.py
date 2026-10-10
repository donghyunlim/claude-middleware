"""Publish the 진척판 HTML where people can open it.

Usage: python3 publish_page.py <watch.json> <page.html>

With watch.json dashboard.publish = {"ssh_host", "remote_dir", "url"} the page is copied to
<ssh_host>:<remote_dir>/index.html (upload to a temp name, then rename, so readers never see half a file)
and fetched back from <url> to confirm the served copy matches. Without it the page stays local and the
script prints how to open or serve it. remote_dir is relative to the remote home unless absolute.
"""
import hashlib, json, os, subprocess, sys, urllib.request


def main():
    watch, page = sys.argv[1], sys.argv[2]
    pub = json.load(open(watch, encoding="utf-8")).get("dashboard", {}).get("publish")
    body = open(page, "rb").read()
    if not pub:
        print(f"local only: file://{os.path.abspath(page)}")
        print(f"to share on this network: python3 -m http.server 8090 --directory {os.path.dirname(os.path.abspath(page))}")
        return
    host, rdir, url = pub["ssh_host"], pub["remote_dir"].rstrip("/"), pub["url"]
    run = lambda *a: subprocess.run(a, check=True, capture_output=True, text=True)
    run("ssh", "-o", "BatchMode=yes", host, f"mkdir -p {rdir}")
    subprocess.run(["ssh", "-o", "BatchMode=yes", host, f"cat > {rdir}/.index.html.tmp"], input=body, check=True, capture_output=True)
    run("ssh", "-o", "BatchMode=yes", host, f"mv -f {rdir}/.index.html.tmp {rdir}/index.html")
    served = urllib.request.urlopen(url, timeout=10).read()
    if hashlib.sha256(served).digest() != hashlib.sha256(body).digest():
        sys.exit(f"uploaded, but {url} serves different content ({len(served)} bytes vs {len(body)}); is the server pointed at {rdir}?")
    print(f"published: {url} ({len(body):,} bytes)")


if __name__ == "__main__":
    main()
