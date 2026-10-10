"""Baseline state of the refresh loop: refresh/state.json under QA_HOME.

  python3 state.py show
  python3 state.py commit --manifest refresh/<stamp> [--code <commit>] [--mockup <version>] [--note TEXT]

`commit` is the last step of a refresh and runs only after every check passed. Until then the next
refresh compares against the previous good baseline, so a half-applied refresh is redone, not lost.
"""
import argparse, datetime, json, os

P = os.path.join("refresh", "state.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["show", "commit"])
    ap.add_argument("--manifest"); ap.add_argument("--code"); ap.add_argument("--mockup"); ap.add_argument("--note")
    a = ap.parse_args()
    s = json.load(open(P, encoding="utf-8")) if os.path.exists(P) else {"history": []}
    if a.cmd == "commit":
        if not a.manifest or not os.path.exists(os.path.join(a.manifest, "manifest.json")):
            raise SystemExit("--manifest must point to a finished crawl")
        entry = {"at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "manifest": a.manifest,
                 "code_commit": a.code or s.get("code_commit"), "mockup_version": a.mockup or s.get("mockup_version"), "note": a.note}
        s.update({k: v for k, v in entry.items() if k != "at" and k != "note"}, last_success=entry["at"])
        s["history"] = (s.get("history") or []) + [entry]
        json.dump(s, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in s.items() if k != "history"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
