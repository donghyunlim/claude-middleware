"""List result files in a run dir that are new or changed since they were last bulk-published.

  python3 <skill>/scripts/publish_pending.py <run_dir> list [--exclude=ID,ID]   # prints comma-separated TC IDs
  python3 <skill>/scripts/publish_pending.py <run_dir> mark <ids>               # records their current mtime as published

The orchestrator publishes in bulk so app slots never wait on Notion writes.
"""
import glob, json, os, sys

run_dir, cmd = sys.argv[1], sys.argv[2]
state_path = os.path.join(run_dir, "_published.json")
state = json.load(open(state_path)) if os.path.exists(state_path) else {}
if cmd == "list":
    ex = set(next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--exclude=")), "").split(","))
    out = []
    for f in sorted(glob.glob(os.path.join(run_dir, "TC-*.json"))):
        tc = os.path.basename(f)[:-5]
        try:
            r = json.load(open(f, encoding="utf-8"))
        except ValueError:
            continue  # being written
        if tc in ex or not r.get("verdict") or not r.get("headline"):
            continue
        if state.get(tc) != os.path.getmtime(f):
            out.append(tc)
    print(",".join(out))
elif cmd == "mark":
    for tc in filter(None, sys.argv[3].split(",")):
        state[tc] = os.path.getmtime(os.path.join(run_dir, f"{tc}.json"))
    json.dump(state, open(state_path, "w"), indent=0)
