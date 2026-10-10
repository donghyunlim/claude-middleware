"""Full-scan queue for the QA executor.

  python3 <skill>/scripts/qa_queue.py build <run_dir> [--exclude-run DIR ...] [--only-ids FILE]  # writes <run_dir>/queue.json
  python3 <skill>/scripts/qa_queue.py next <run_dir> <n> [--group=역할/권한 수준]  # writes next batch file, prints its path
  python3 <skill>/scripts/qa_queue.py status <run_dir>                          # done / pending / by verdict

A row is done when <run_dir>/<tc_id>.json exists with a verdict. Order groups rows by role and access so
the executor switches roles as few times as possible, then by menu and TC ID.
"""
import collections, glob, json, os, sys

ORDER = [("영업자", "수정 가능"), ("영업팀장·관리자", "수정 가능"), ("영업팀장·관리자", "조회만"),
         ("영업운영", "수정 가능"), ("영업운영", "조회만"), ("권한 관리자", "수정 가능")]


def done(run_dir):
    out = {}
    for f in glob.glob(os.path.join(run_dir, "TC-*.json")):
        try:
            r = json.load(open(f, encoding="utf-8"))
        except ValueError:
            continue
        if r.get("verdict"):
            out[r["tc_id"]] = r["verdict"]
    return out


def main():
    cmd, run_dir = sys.argv[1], sys.argv[2]
    qpath = os.path.join(run_dir, "queue.json")
    if cmd == "build":
        skip, only = set(), None
        args = sys.argv[3:]
        for i, a in enumerate(args):
            if a == "--exclude-run":
                skip |= set(done(args[i + 1]))
            if a == "--only-ids":  # comma- or newline-separated TC IDs, e.g. the rows chosen for a re-run lane
                only = set(open(args[i + 1], encoding="utf-8").read().replace("\n", ",").split(",")) - {""}
        rows = [r for f in sorted(glob.glob("scenarios/*/*.json")) for r in json.load(open(f, encoding="utf-8"))
                if r["policy"] != "범위 제외" and r["tc_id"] not in skip and (only is None or r["tc_id"] in only)]
        key = lambda r: (ORDER.index((r["role"], r["access"])) if (r["role"], r["access"]) in ORDER else 99,
                         r["external"], int(r["menu"].split(".")[0]), r["tc_id"])
        rows.sort(key=key)
        json.dump(rows, open(qpath, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"queue={len(rows)} skipped_done={len(skip)}", dict(collections.Counter((r["role"], r["access"]) for r in rows)))
    elif cmd == "next":
        n = int(sys.argv[3]); q = json.load(open(qpath, encoding="utf-8")); d = done(run_dir)
        # rows already handed to a batch are claimed, even if their worker is still running
        claimed = {r["tc_id"] for f in glob.glob(os.path.join(run_dir, "batch-*.json")) for r in json.load(open(f, encoding="utf-8"))}
        pend = [r for r in q if r["tc_id"] not in d and r["tc_id"] not in claimed]
        if not pend:
            print("EMPTY"); return
        # keep a batch inside one role/access group; --group "역할/권한 수준" picks a specific group
        want = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--group=")), None)
        if want:
            pend = [r for r in pend if f'{r["role"]}/{r["access"]}' == want]
            if not pend:
                print("EMPTY"); return
        g = (pend[0]["role"], pend[0]["access"])
        batch = [r for r in pend if (r["role"], r["access"]) == g][:n]
        nums = [int(os.path.basename(f)[6:9]) for f in glob.glob(os.path.join(run_dir, "**", "batch-[0-9][0-9][0-9].json"), recursive=True)]
        k = max(nums, default=0) + 1  # never reuse a number, even if a batch file was moved aside
        p = os.path.join(run_dir, f"batch-{k:03d}.json")
        json.dump(batch, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(p, len(batch), f"{g[0]}/{g[1]}", f"pending_after={len(pend) - len(batch)}")
    elif cmd == "status":
        q = json.load(open(qpath, encoding="utf-8")); d = done(run_dir)
        print(f"done={sum(1 for r in q if r['tc_id'] in d)} pending={sum(1 for r in q if r['tc_id'] not in d)}",
              dict(collections.Counter(d.values())))


if __name__ == "__main__":
    main()
