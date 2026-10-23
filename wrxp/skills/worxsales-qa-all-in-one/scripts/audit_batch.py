"""Audit one finished worker batch before its results are published.

  python3 <skill>/scripts/audit_batch.py <run_dir> <batch-NNN> [--lanes refresh/lanes.json] [--reject]

Checks every row of <run_dir>/<batch-NNN>.json:
  - a result file with verdict and headline exists
  - every listed figure exists; the row has its own figure (<tc>.png / <tc>-*.png). Only 실행 불가 and 미구현 rows
    may instead point at another row's figure with details.shared_figure_with (the same blocker screen)
  - real started_at < ended_at, and no two rows share the same start or end time
  - not batch-written: rows must not overlap in time, and three or more result files must not be written
    within the same 2 seconds
  - details.role_before / role_after are recorded
  - with --lanes: a row whose previous verdict (latest older lane) was 문제 and now differs quotes a reason
    (details.verdict_reason)
--reject moves the result file and figures of every failing row into <run_dir>/_rejected/<batch-NNN>/ so the row
can be handed out again in a new batch (qa_queue.py treats rows in old batch files as claimed, so write the new
batch file by hand). Nothing is deleted.
Exit 0 = clean, 1 = findings. Stdlib only, no network.
"""
import datetime as dt, glob, json, os, shutil, sys

OWN_FIGURE_OPTIONAL = {"실행 불가", "미구현"}


def ts(s):
    try:
        return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S%z")
    except (TypeError, ValueError):
        try:
            return dt.datetime.fromisoformat(s)
        except (TypeError, ValueError):
            return None


def figures(run_dir, tc):
    return sorted(set(glob.glob(os.path.join(run_dir, f"{tc}.png")) + glob.glob(os.path.join(run_dir, f"{tc}-*.png"))))


def previous_verdicts(lanes_file, run_dir):
    lanes = [l["dir"] for l in json.load(open(lanes_file, encoding="utf-8"))]  # newest first
    norm = [os.path.normpath(d) for d in lanes]
    here = os.path.normpath(run_dir)
    older = lanes[norm.index(here) + 1:] if here in norm else lanes
    out = {}
    for d in reversed(older):  # newest lane last so it wins
        for f in glob.glob(os.path.join(d, "TC-*.json")):
            try:
                out[os.path.basename(f)[:-5]] = json.load(open(f, encoding="utf-8")).get("verdict")
            except ValueError:
                pass
    return out


def main(argv):
    pos = [a for i, a in enumerate(argv[1:], 1) if not a.startswith("--") and argv[i - 1] != "--lanes"]
    if len(pos) != 2 or "-h" in argv or "--help" in argv:
        sys.exit(__doc__)
    run_dir, batch = pos[0], os.path.basename(pos[1]).removesuffix(".json")
    rows = json.load(open(os.path.join(run_dir, batch + ".json"), encoding="utf-8"))
    prev = previous_verdicts(argv[argv.index("--lanes") + 1], run_dir) if "--lanes" in argv else {}
    bad, spans, mtimes = {}, [], []
    seen_start, seen_end = set(), set()
    for row in rows:
        tc = row["tc_id"]
        p = os.path.join(run_dir, f"{tc}.json")
        why = []
        if not os.path.exists(p):
            bad[tc] = ["no result file"]
            continue
        r = json.load(open(p, encoding="utf-8"))
        d = r.get("details") or {}
        if not r.get("verdict") or not r.get("headline"):
            why.append("verdict or headline missing")
        own = figures(run_dir, tc)
        for fig in r.get("figures") or []:
            f = fig.get("file") if isinstance(fig, dict) else fig
            if f and not os.path.exists(os.path.join(run_dir, os.path.basename(f))):
                why.append(f"listed figure missing: {os.path.basename(f)}")
        shared = d.get("shared_figure_with")
        if not own:
            if not shared:
                why.append("no own figure")
            elif r.get("verdict") not in OWN_FIGURE_OPTIONAL:
                why.append(f"{r.get('verdict')} row must have its own figure (shared_figure_with={shared})")
            elif not figures(run_dir, shared):
                why.append(f"shared figure of {shared} missing")
        a, b = ts(r.get("started_at")), ts(r.get("ended_at"))
        if not a or not b or a >= b:
            why.append(f"bad times {r.get('started_at')} .. {r.get('ended_at')}")
        else:
            if r["started_at"] in seen_start or r["ended_at"] in seen_end:
                why.append("start or end time equals another row's")
            seen_start.add(r["started_at"]); seen_end.add(r["ended_at"])
            spans.append((a, b, tc))
        if not d.get("role_before") or not d.get("role_after"):
            why.append("role_before/role_after missing")
        if prev.get(tc) == "문제" and r.get("verdict") != "문제" and not str(d.get("verdict_reason") or "").strip():
            why.append("changed from 문제 without details.verdict_reason")
        mtimes.append((os.path.getmtime(p), tc))
        if why:
            bad[tc] = why
    spans.sort()
    for (a1, b1, t1), (a2, b2, t2) in zip(spans, spans[1:]):
        if a2 < b1:
            bad.setdefault(t2, []).append(f"overlaps {t1} (rows must run one after another)")
    mtimes.sort()
    for i in range(len(mtimes) - 2):
        if mtimes[i + 2][0] - mtimes[i][0] < 2:
            for _, tc in mtimes[i:i + 3]:
                if "written together with other rows" not in bad.get(tc, []):
                    bad.setdefault(tc, []).append("written together with other rows")
    print(f"{batch}: rows={len(rows)} bad={len(bad)}")
    for tc, why in sorted(bad.items()):
        print(f"  {tc}: " + "; ".join(why))
    if bad and "--reject" in argv:
        dst = os.path.join(run_dir, "_rejected", batch)
        os.makedirs(dst, exist_ok=True)
        for tc in bad:
            for f in [os.path.join(run_dir, f"{tc}.json")] + figures(run_dir, tc):
                if os.path.exists(f):
                    shutil.move(f, os.path.join(dst, os.path.basename(f)))
        print("rejected ->", dst, "| re-run:", ",".join(sorted(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
