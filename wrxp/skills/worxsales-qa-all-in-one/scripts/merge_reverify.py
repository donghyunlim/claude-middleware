"""Merge re-verification results into the full-scan results so the DB shows the final verdict.

  python3 <skill>/scripts/merge_reverify.py <reverify_dir> <full_dir>   # prints merged TC IDs (comma-separated)

재현 불가 keeps the first verdict. Rows already relabeled by the role audit (_role_revised_ids.txt) are skipped.
A row is merged once (details.reverify present); its reverify figures are copied next to the full result.
"""
import glob, json, os, shutil, sys

rev_dir, full_dir = sys.argv[1], sys.argv[2]
role_path = os.path.join(full_dir, "_role_revised_ids.txt")
role_ids = set(open(role_path).read().replace("\n", ",").split(",")) if os.path.exists(role_path) else set()
merged = []
for f in sorted(glob.glob(os.path.join(rev_dir, "TC-*.json"))):
    r = json.load(open(f, encoding="utf-8"))
    tc = r["tc_id"]
    p = os.path.join(full_dir, f"{tc}.json")
    if tc in role_ids or not os.path.exists(p):
        continue
    o = json.load(open(p, encoding="utf-8"))
    d = o.setdefault("details", {})
    if "reverify" in d:
        continue
    d["reverify"] = {k: r.get(k) for k in ("reverify", "final_verdict", "headline", "reason", "role_shown",
                                          "started_at", "ended_at", "reviewer_model")}
    if r.get("reverify") != "재현 불가" and r.get("final_verdict") and r["final_verdict"] != o["verdict"]:
        d["verdict_revision"] = {"from": o["verdict"], "to": r["final_verdict"],
                                 "reason": "재검증(" + str(r.get("reviewer_model")) + "): " + r.get("reason", ""),
                                 "at": r.get("ended_at")}
        o["verdict"] = r["final_verdict"]
        o["headline"] = r.get("headline") or o["headline"]
    elif r.get("reverify") == "문제 확정" and r.get("headline"):
        o["headline"] = r["headline"]
    for fig in r.get("figures") or []:
        fig = fig if isinstance(fig, dict) else {"file": fig, "caption": "재검증 장면"}
        for k in ("file", "zoom"):
            src = os.path.join(rev_dir, fig.get(k) or "")
            if fig.get(k) and os.path.exists(src):
                dst = os.path.join(full_dir, "rv-" + fig[k])
                shutil.copy2(src, dst)
                fig[k] = "rv-" + fig[k]
        if fig.get("file", "").startswith("rv-"):
            fig["caption"] = "재검증 · " + fig.get("caption", "")
            o.setdefault("figures", []).append(fig)
    json.dump(o, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    merged.append(tc)
print(",".join(merged))
