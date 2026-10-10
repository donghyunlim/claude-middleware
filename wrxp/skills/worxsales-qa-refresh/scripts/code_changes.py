"""Code changes between the last tested build and the branch head, grouped by scenario menu.

Usage: python3 code_changes.py <watch.json> <from_commit> [--to REF] [--out report.json]
Fetches first. Splits runtime files from test-only files (tests, fixtures, stories, README), because
test-only changes do not change what the app does. Runtime paths that match no prefix in the code map
are listed as unmapped and count as attention: a new feature folder must be mapped, not skipped.
Exit 0 when the head equals from_commit, 1 when there are changes.
"""
import argparse, collections, json, re, subprocess

TEST = re.compile(r"(\.test\.|\.spec\.|__tests__/|/fixtures?/|\.stories\.|/README\.md$|\.md$)")


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], check=True, capture_output=True, text=True).stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("watch"); ap.add_argument("from_commit"); ap.add_argument("--to"); ap.add_argument("--out")
    a = ap.parse_args()
    c = json.load(open(a.watch, encoding="utf-8"))["code"]
    cmap = {k: v for k, v in json.load(open(c["map"], encoding="utf-8")).items() if not k.startswith("_")}
    repo, to = c["repo"], a.to or c["branch"]
    git(repo, "fetch", "-q", "origin")
    head = git(repo, "rev-parse", "--short", to).strip()
    commits = git(repo, "log", "--oneline", f"{a.from_commit}..{to}").splitlines()
    files = [l.split("\t") for l in git(repo, "diff", "--name-status", a.from_commit, to).splitlines()]
    menus, unmapped, test_only = collections.defaultdict(list), [], []
    for st, *paths in files:
        path = paths[-1]
        if TEST.search(path):
            test_only.append(path); continue
        hit = max((k for k in cmap if path.startswith(k)), key=len, default=None)
        if hit is None: unmapped.append(path); continue
        for m in cmap[hit]: menus[m].append(f"{st[0]} {path}")
    rep = {"from": a.from_commit, "to": head, "commits": commits, "menus": dict(menus), "unmapped": unmapped,
           "test_only": len(test_only)}
    if a.out: json.dump(rep, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{a.from_commit} → {head}: commits={len(commits)} runtime_files={sum(len(v) for v in menus.values())} test_only={len(test_only)}")
    for m in sorted(menus, key=lambda x: int(x)): print(f"  menu {m}: {len(menus[m])} files")
    for p in unmapped: print("  UNMAPPED", p)
    raise SystemExit(1 if commits else 0)


if __name__ == "__main__":
    main()
