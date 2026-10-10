"""Render refresh/history.json as the QA round dashboard page: one self-contained HTML file, no scripts.

Usage: python3 render_html.py <history.json> <out.html> [--notion-url URL]
Dot plots are drawn as inline SVG from one scale each; every metric also appears in a table.
"""
import argparse, html, json

E = html.escape
VCOL = {"OK": "ok", "부분 OK": "partial", "미구현": "unimpl", "문제": "problem", "실행 불가": "blocked", "보류-기록": "hold", "알려진 차이": "known"}

CSS = """
/* Layout: one column ledger — summary strip, two dot plots, then the full tables. */
:root{
  --bg:#f4f6f9; --panel:#ffffff; --ink:#1b2230; --muted:#5f6b7d; --rule:#dde2ea; --grid:#e9edf3;
  --accent:#2c5fd4;
  --ok:#1f8a5b; --partial:#73b892; --unimpl:#8d97a8; --problem:#cc3d3d; --blocked:#c98322; --hold:#7d68c4; --known:#3d8fb0;
  --f-body:"IBM Plex Sans KR","Apple SD Gothic Neo","Malgun Gothic",system-ui,sans-serif;
  --f-num:"IBM Plex Mono",ui-monospace,"SFMono-Regular",Menlo,monospace;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --bg:#0e131d; --panel:#151c29; --ink:#e4e8ef; --muted:#97a2b4; --rule:#273042; --grid:#1d2535; --accent:#7ea3ff;
  --ok:#46c488; --partial:#3f8f67; --unimpl:#7d879a; --problem:#f06a6a; --blocked:#e3a24a; --hold:#a593ec; --known:#5fb6d6; color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#0e131d; --panel:#151c29; --ink:#e4e8ef; --muted:#97a2b4; --rule:#273042; --grid:#1d2535; --accent:#7ea3ff;
  --ok:#46c488; --partial:#3f8f67; --unimpl:#7d879a; --problem:#f06a6a; --blocked:#e3a24a; --hold:#a593ec; --known:#5fb6d6; color-scheme:dark}
body{background:var(--bg);color:var(--ink);font-family:var(--f-body);font-size:14px;line-height:1.55}
.wrap{max-width:1120px;margin:0 auto;padding-inline:16px;padding-block:28px 56px;display:grid;gap:28px}
h1{font-size:26px;line-height:1.2;margin:0;text-wrap:balance;letter-spacing:-.01em}
h2{font-size:17px;margin:0 0 4px;text-wrap:balance}
.sub{color:var(--muted);margin:6px 0 0}
.sub a{color:var(--accent)}
.num{font-family:var(--f-num);font-variant-numeric:tabular-nums}
section{display:grid;gap:10px;min-width:0}
.note{color:var(--muted);font-size:13px;margin:0;max-width:72ch}
.strip{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:1px;background:var(--rule);border:1px solid var(--rule);border-radius:6px;overflow:hidden}
.cell{background:var(--panel);padding:12px 14px;display:grid;gap:2px;min-width:0}
.cell .k{color:var(--muted);font-size:12px;letter-spacing:.02em}
.cell .v{font-family:var(--f-num);font-size:22px;font-variant-numeric:tabular-nums}
.cell .d{font-family:var(--f-num);font-size:12px;color:var(--muted)}
.cell.warn .v{color:var(--problem)}
.panel{background:var(--panel);border:1px solid var(--rule);border-radius:6px;padding:12px;overflow-x:auto}
svg{display:block;max-width:none}
svg text{font-family:var(--f-num);font-size:11px;fill:var(--muted)}
svg .lbl{font-family:var(--f-body);font-size:12px;fill:var(--ink)}
svg .grid{stroke:var(--grid);stroke-width:1}
svg .axis{stroke:var(--rule);stroke-width:1}
svg .s-impl{fill:var(--ok);stroke:var(--ok)}
svg .s-ok{fill:var(--panel);stroke:var(--ok);stroke-width:2}
svg .s-unimpl{fill:var(--panel);stroke:var(--unimpl);stroke-width:2}
svg .s-cov{fill:var(--accent);stroke:var(--accent)}
svg .link{fill:none;stroke-width:1.5;opacity:.55}
svg .first{fill:var(--panel);stroke:var(--muted);stroke-width:1.5}
svg .mid{fill:var(--muted);opacity:.45}
svg .last{fill:var(--ok)}
svg .span{stroke:var(--muted);stroke-width:1.5;opacity:.5}
.legend{display:flex;flex-wrap:wrap;gap:6px 16px;color:var(--muted);font-size:12px;margin:0;padding:0;list-style:none}
.legend li{display:flex;align-items:center;gap:6px}
.sw{width:10px;height:10px;border-radius:50%;display:inline-block;border:2px solid currentColor}
.tbl{overflow-x:auto;border:1px solid var(--rule);border-radius:6px;background:var(--panel)}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{padding:7px 10px;border-bottom:1px solid var(--rule);text-align:right;white-space:nowrap}
th{font-weight:600;color:var(--muted);font-size:12px;background:var(--panel);position:sticky;top:0}
td.t,th.t{text-align:left}
td{font-family:var(--f-num);font-variant-numeric:tabular-nums}
td.t{font-family:var(--f-body)}
tr:last-child td{border-bottom:0}
tr.cur td{background:color-mix(in srgb,var(--accent) 8%,var(--panel))}
.pill{display:inline-block;padding:0 6px;border-radius:9px;font-size:11px;font-family:var(--f-body)}
.pill.up{color:var(--problem);border:1px solid var(--problem)}
.pill.down{color:var(--ok);border:1px solid var(--ok)}
footer{color:var(--muted);font-size:12px;display:grid;gap:4px}
"""


def pct(v): return "—" if v is None else f"{v:.1f}%"


def round_plot(rounds):
    """구현도 by round: ● 구현도(OK+부분 OK) ○ OK only ○ 미구현, ▪ 실행률. y = 0..100%."""
    W, H, L, R, T, B = max(560, 92 * len(rounds) + 90), 300, 48, 44, 16, 64  # R: half a build label, so the last round is not clipped
    xw = (W - L - R) / max(1, len(rounds) - 1)
    x = lambda i: L + i * xw
    y = lambda v: T + (H - T - B) * (1 - v / 100)
    out = [f'<svg viewBox="0 0 {W} {H}" style="width:100%;min-width:560px;max-width:{W}px;height:auto" role="img" aria-label="회차별 구현도 점도표">']
    for g in range(0, 101, 20):
        out.append(f'<line class="grid" x1="{L}" x2="{W-R}" y1="{y(g):.1f}" y2="{y(g):.1f}"/><text x="{L-8}" y="{y(g)+4:.1f}" text-anchor="end">{g}%</text>')
    out.append(f'<line class="axis" x1="{L}" x2="{W-R}" y1="{y(0):.1f}" y2="{y(0):.1f}"/>')
    series = [("unimpl_rate", "s-unimpl", 4.5, "미구현"), ("ok_rate", "s-ok", 4.5, "OK"), ("impl_rate", "s-impl", 6, "구현도")]
    for key, cls, rad, name in series:
        pts = [(x(i), y(r[key])) for i, r in enumerate(rounds) if r[key] is not None]
        if len(pts) > 1:
            out.append(f'<polyline class="link {cls}" points="{" ".join(f"{a:.1f},{b:.1f}" for a, b in pts)}" style="fill:none"/>')
        for i, r in enumerate(rounds):
            if r[key] is None: continue
            out.append(f'<circle class="{cls}" cx="{x(i):.1f}" cy="{y(r[key]):.1f}" r="{rad}"><title>{E(r["lane"])} · {name} {r[key]:.1f}%</title></circle>')
    last = rounds[-1]
    out.append(f'<text x="{x(len(rounds)-1):.1f}" y="{y(last["impl_rate"])-12:.1f}" text-anchor="end" style="fill:var(--ok);font-weight:600">{last["impl_rate"]:.1f}%</text>')
    for i, r in enumerate(rounds):
        out.append(f'<text x="{x(i):.1f}" y="{H-B+18}" text-anchor="middle">{E(r["build"] or "pilot")}</text>'
                   f'<text x="{x(i):.1f}" y="{H-B+33}" text-anchor="middle">{E(r["end"][5:10])}</text>'
                   f'<text x="{x(i):.1f}" y="{H-B+48}" text-anchor="middle">{r["executed"]}/{r["target"]}</text>')
    out.append("</svg>")
    return "".join(out)


def menu_plot(rounds):
    """Per menu: hollow dot = first round with results, small dots = rounds between, filled dot = now."""
    last = rounds[-1]["menus"]
    order = sorted(last, key=lambda m: (last[m]["impl_rate"] or 0), reverse=True)
    W, row, L, R, T = 760, 24, 170, 60, 26
    H = T + row * len(order) + 24
    x = lambda v: L + (W - L - R) * v / 100
    out = [f'<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="메뉴별 구현도 이동">']
    for g in range(0, 101, 20):
        out.append(f'<line class="grid" x1="{x(g):.1f}" x2="{x(g):.1f}" y1="{T-8}" y2="{H-20}"/><text x="{x(g):.1f}" y="{T-12}" text-anchor="middle">{g}%</text>')
    for j, m in enumerate(order):
        cy = T + row * j + row / 2
        hist = [r["menus"][m]["impl_rate"] for r in rounds if m in r["menus"] and r["menus"][m]["impl_rate"] is not None]
        if not hist: continue
        name = last[m]["name"]
        out.append(f'<text class="lbl" x="{L-10}" y="{cy+4:.1f}" text-anchor="end">{E(name)}</text>')
        out.append(f'<line class="span" x1="{x(min(hist)):.1f}" x2="{x(max(hist)):.1f}" y1="{cy:.1f}" y2="{cy:.1f}"/>')
        for v in hist[1:-1]:
            out.append(f'<circle class="mid" cx="{x(v):.1f}" cy="{cy:.1f}" r="2.5"/>')
        out.append(f'<circle class="first" cx="{x(hist[0]):.1f}" cy="{cy:.1f}" r="5"><title>{E(name)} 첫 측정 {hist[0]:.1f}%</title></circle>')
        out.append(f'<circle class="last" cx="{x(hist[-1]):.1f}" cy="{cy:.1f}" r="5.5"><title>{E(name)} 현재 {hist[-1]:.1f}%</title></circle>')
        out.append(f'<text x="{W-R+8}" y="{cy+4:.1f}">{hist[-1]:.1f}%</text>')
    out.append("</svg>")
    return "".join(out)


def delta(a, b, unit=""):
    if a is None or b is None or a == b: return ""
    d = a - b
    return f'{"+" if d > 0 else ""}{d:.1f}{unit}' if isinstance(d, float) else f'{"+" if d > 0 else ""}{d}{unit}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("history"); ap.add_argument("out"); ap.add_argument("--notion-url", default="")
    a = ap.parse_args()
    h = json.load(open(a.history, encoding="utf-8"))
    rs = h["rounds"]; cur = rs[-1]; prev = rs[-2] if len(rs) > 1 else cur
    v = cur["verdicts"]
    cells = [
        ("대상 행", f'{cur["target"]:,}', f'실행 {cur["executed"]:,} · {pct(cur["coverage"])}', ""),
        ("구현도 (OK+부분 OK)", pct(cur["impl_rate"]), f'직전 대비 {delta(cur["impl_rate"], prev["impl_rate"], "p") or "변화 없음"}', ""),
        ("미구현", pct(cur["unimpl_rate"]), f'{v["미구현"]:,}행', ""),
        ("문제 (확정)", f'{cur["problem"]}', f'신규 {cur["problem_new"]} · 해소 {cur["problem_resolved"]}', "warn" if cur["problem"] else ""),
        ("권한 미적용", f'{cur["role_gap"]}', "역할 처리가 빠진 행", ""),
        ("쓰기 범위 밖", f'{cur["write_blocked"]}', f'이번 회차 신규 {len(cur["write_blocked_new"])}', ""),
    ]
    strip = "".join(f'<div class="cell {c}"><span class="k">{E(k)}</span><span class="v">{E(val)}</span><span class="d">{E(d)}</span></div>' for k, val, d, c in cells)

    vh = "".join(f'<th>{E(x)}</th>' for x in v)
    rows = []
    for r in rs:
        cls = ' class="cur"' if r is cur else ""
        vd = "".join(f'<td>{r["verdicts"][x]:,}</td>' for x in v)
        rows.append(f'<tr{cls}><td class="num">{r["round"]}</td><td class="t">{E(r["lane"])}</td><td>{E(r["build"] or "—")}</td><td>{E(r["end"].replace("T", " "))}</td>'
                    f'<td>{r["target"]:,}</td><td>{r["executed"]:,}</td><td>{pct(r["coverage"])}</td><td>{pct(r["impl_rate"])}</td><td>{pct(r["ok_rate"])}</td><td>{pct(r["unimpl_rate"])}</td>'
                    f'{vd}<td>{r["problem_new"]}</td><td>{r["problem_resolved"]}</td><td>{r["role_gap"]}</td><td>{r["write_blocked"]}</td></tr>')
    round_tbl = (f'<div class="tbl"><table><thead><tr><th>#</th><th class="t">레인</th><th>빌드</th><th>마친 시각</th><th>대상</th><th>실행</th><th>실행률</th>'
                 f'<th>구현도</th><th>OK율</th><th>미구현율</th>{vh}<th>문제 신규</th><th>문제 해소</th><th>권한 미적용</th><th>쓰기 범위 밖</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>')

    bk = list(cur["blocked"])
    CUR = ' class="cur"'
    brows = "".join(f'<tr{CUR if r is cur else ""}><td class="num">{r["round"]}</td><td class="t">{E(r["lane"])}</td>' + "".join(f'<td>{r["blocked"].get(k, 0)}</td>' for k in bk)
                    + f'<td>{sum(r["blocked"].values())}</td></tr>' for r in rs)
    block_tbl = (f'<div class="tbl"><table><thead><tr><th>#</th><th class="t">레인</th>{"".join(f"<th>{E(k)}</th>" for k in bk)}<th>합계</th></tr></thead><tbody>{brows}</tbody></table></div>')

    first_rate = {}
    for r in rs:
        for m, e in r["menus"].items():
            if e["impl_rate"] is not None: first_rate.setdefault(m, e["impl_rate"])
    mrows = []
    for m, e in sorted(cur["menus"].items(), key=lambda kv: int(kv[0])):
        d = delta(e["impl_rate"], first_rate.get(m), "p")
        pill = f'<span class="pill {"down" if d.startswith("+") else "up"}">{E(d)}</span>' if d else ""
        mrows.append(f'<tr><td class="t">{E(e["name"])}</td><td>{e["target"]}</td><td>{e["executed"]}</td><td>{e["impl"]}</td><td>{e["unimpl"]}</td><td>{e["problem"]}</td>'
                     f'<td>{pct(first_rate.get(m))}</td><td>{pct(e["impl_rate"])}</td><td>{pill}</td></tr>')
    menu_tbl = (f'<div class="tbl"><table><thead><tr><th class="t">메뉴</th><th>대상</th><th>실행</th><th>OK+부분 OK</th><th>미구현</th><th>문제</th>'
                f'<th>첫 측정</th><th>현재 구현도</th><th>변화</th></tr></thead><tbody>{"".join(mrows)}</tbody></table></div>')

    notion = f' · <a href="{E(a.notion_url)}">Notion 상황판</a>' if a.notion_url else ""
    page = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>WorxSales QA 진척판</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans+KR:wght@400;600&display=swap">
<style>*,*::before,*::after{{box-sizing:border-box}} body{{margin:0}} img{{max-width:100%}}
{CSS}</style></head><body>
<main class="wrap">
<header><h1>WorxSales QA 진척판</h1>
<p class="sub">최신 회차 {cur["round"]} · desktop <span class="num">{E(cur["build"])}</span> · {E(cur["end"].replace("T", " "))} 기준 · 생성 {E(h["generated_at"][:16].replace("T", " "))}{notion}</p></header>
<section aria-label="현재 요약"><div class="strip">{strip}</div></section>
<section><h2>회차별 구현도</h2>
<p class="note">구현도는 실행한 행 가운데 OK와 부분 OK의 비율입니다. 아래 축은 빌드, 마친 날짜, 실행/대상 행 수입니다.</p>
<ul class="legend"><li><span class="sw" style="color:var(--ok);background:var(--ok)"></span>구현도</li><li><span class="sw" style="color:var(--ok)"></span>OK만</li><li><span class="sw" style="color:var(--unimpl)"></span>미구현</li></ul>
<div class="panel">{round_plot(rs)}</div></section>
<section><h2>메뉴별 구현도 이동</h2>
<p class="note">빈 점은 그 메뉴를 처음 측정한 회차, 작은 점은 중간 회차, 채운 점은 현재입니다. 현재 구현도가 높은 메뉴부터 놓았습니다.</p>
<div class="panel">{menu_plot(rs)}</div></section>
<section><h2>회차 이력</h2>{round_tbl}</section>
<section><h2>실행 불가 사유</h2><p class="note">결과 문장의 표현으로 분류했습니다. 일시 장애로 막힌 행은 다시 실행해 바꿔 두었으므로 여기에는 남지 않습니다.</p>{block_tbl}</section>
<section><h2>메뉴별 현황</h2>{menu_tbl}</section>
<footer><span>대상 행은 시나리오의 생성 배치 날짜부터 셉니다. 범위 제외 날짜는 행마다 기록되지 않아, 지금 범위 제외인 행은 앞선 회차에서도 뺐습니다.</span>
<span>각 회차의 판정은 그 시점까지 끝난 레인 가운데 우선순위가 가장 높은 결과입니다. 마지막 회차는 Notion 시나리오 DB와 같습니다.</span></footer>
</main></body></html>"""
    open(a.out, "w", encoding="utf-8").write(page)
    print("wrote", a.out, len(page), "bytes")


if __name__ == "__main__":
    main()
