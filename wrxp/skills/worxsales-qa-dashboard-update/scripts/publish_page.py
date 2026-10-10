"""Publish the 진척판 HTML where people can open it.

Usage: python3 publish_page.py <watch.json> <page.html>

With watch.json dashboard.publish = {"ssh_host", "remote_dir", "url", "verify_url"?} the page is copied to
<ssh_host>:<remote_dir>/index.html (ssh_host "local" = this Mac; written to a temp name, then renamed, so
readers never see half a file) and fetched back from verify_url (default url) to confirm the served copy
matches. url is the address people open, e.g. http://<LocalHostName>.local:8090/ on the office Wi-Fi. Without it the page stays local and the
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
    if host == "local":
        d = os.path.join(os.path.expanduser("~"), rdir)
        os.makedirs(d, exist_ok=True)
        tmp = os.path.join(d, ".index.html.tmp")
        open(tmp, "wb").write(body)
        os.replace(tmp, os.path.join(d, "index.html"))
    else:
        ssh = ["ssh", "-o", "BatchMode=yes", host]
        subprocess.run(ssh + [f"mkdir -p {rdir} && cat > {rdir}/.index.html.tmp && mv -f {rdir}/.index.html.tmp {rdir}/index.html"],
                       input=body, check=True, capture_output=True)
    served = urllib.request.urlopen(pub.get("verify_url", url), timeout=10).read()
    if hashlib.sha256(served).digest() != hashlib.sha256(body).digest():
        sys.exit(f"uploaded, but {url} serves different content ({len(served)} bytes vs {len(body)}); is the server pointed at {rdir}?")
    print(f"published: {url} ({len(body):,} bytes)")


if __name__ == "__main__":
    main()
