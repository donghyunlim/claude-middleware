"""Validate scenario JSON files against the scenario guide (references/scenario-guide.md).

Usage: python3 <skill>/scripts/validate.py <scenario_dir> [--menus FILE]
  Checks enums, TC ID format and menu prefix, duplicate TC IDs, required text fields and broken characters.
  Menu names come from --menus, else <scenario_dir>/menus.json, else the bundled assets/menus.json.
  Files whose name starts with "_" (change logs, id lists) and menus.json itself are skipped.
Exit 0 = no errors, 1 = errors (first 50 printed). Stdlib only, no network.
"""
import glob, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
E = {
    "role": {"영업자", "영업팀장·관리자", "영업운영", "권한 관리자"},
    "access": {"수정 가능", "조회만"},
    "target": {"본인 담당", "다른 담당", "범위 밖", "해당 없음"},
    "type": {"정상", "필수값 누락", "형식·경계값", "권한 거부", "조회만 차단", "상태·예외", "이동·복귀"},
    "policy": {"확정", "확정 필요(보류)", "범위 제외"},
    "impl": {"미확인", "구현됨", "미구현", "정책과 다름"},
    "priority": {"P0", "P1", "P2"},
    "run_mode": {"합성 데이터", "실서버 필요", "수동"},
}
TEXT = ["title", "menu", "screen", "screen_url", "precondition", "steps", "inputs", "omit", "required", "expected", "checkpoints", "evidence"]


def menus_file(src, argv):
    if "--menus" in argv:
        return argv[argv.index("--menus") + 1]
    local = os.path.join(src, "menus.json")
    return local if os.path.exists(local) else os.path.join(HERE, "..", "assets", "menus.json")


def scenario_files(src):
    return [f for f in sorted(glob.glob(os.path.join(src, "**", "*.json"), recursive=True))
            if not os.path.basename(f).startswith("_") and os.path.basename(f) != "menus.json"]


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        sys.exit(__doc__)
    src = argv[1]
    E["menu"] = set(json.load(open(menus_file(src, argv), encoding="utf-8")))
    errs, ids, n = [], set(), 0
    files = scenario_files(src)
    for f in files:
        rows = json.load(open(f, encoding="utf-8"))
        for i, r in enumerate(rows):
            n += 1
            w = f"{os.path.relpath(f, src)}[{i}]"
            m = re.fullmatch(r"TC-(\d{2})-\d{2}-\d{3}", r.get("tc_id", ""))
            if not m: errs.append(f"{w} bad tc_id {r.get('tc_id')}")
            if m and str(r.get("menu", "")).split(".")[0] != str(int(m.group(1))): errs.append(f"{w} tc_id menu != {r.get('menu')}")
            if r.get("tc_id") in ids: errs.append(f"{w} duplicate {r['tc_id']}")
            ids.add(r.get("tc_id"))
            for k, allowed in E.items():
                if r.get(k) not in allowed: errs.append(f"{w} {k}={r.get(k)!r}")
            for k in TEXT:
                if not isinstance(r.get(k), str): errs.append(f"{w} {k} not str")
            for k in ("title", "steps", "expected"):
                if not str(r.get(k) or "").strip(): errs.append(f"{w} empty {k}")
            if not r.get("services") or not set(r["services"]) <= {"JK", "AM"}: errs.append(f"{w} services={r.get('services')}")
            if not isinstance(r.get("external"), bool): errs.append(f"{w} external not bool")
            if "�" in json.dumps(r, ensure_ascii=False): errs.append(f"{w} replacement char")
    print(f"rows={n} files={len(files)} errors={len(errs)}")
    print("\n".join(errs[:50]))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
