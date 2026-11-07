#!/usr/bin/env python3
"""Build the Korean detailed report page (static HTML, inline SVG charts) from saved results."""
import html
import json
from pathlib import Path

S = Path("/tmp/claude-0/-home-user-claude-middleware/0717732f-216e-5d96-be1b-25ee0c15e48c/scratchpad")
OUT = S / "report" / "wrxp-report.html"
C6 = ["base", "global", "global_haq", "global_haqq", "pstack", "pstack_poteto"]
L = {"base": "미적용", "global": "전역만", "global_ha": "전역+ha", "ha": "/ha만", "global_haq": "전역+haq",
     "global_haqq": "전역+haqq", "pstack": "pstack", "pstack_poteto": "pstack+poteto"}
CLS = {"base": "c-base", "global": "c-global", "global_haq": "c-haq", "global_haqq": "c-haqq",
       "pstack": "c-pst", "pstack_poteto": "c-pst2"}

hard = json.loads((S / "hard2/summary.json").read_text())
tier = json.loads((S / "hard2/tier1_summary.json").read_text())["metrics"]
over = json.loads((S / "hard2/oversharing_summary.json").read_text())
tasks = json.loads((S / "dash2/ext_tasks.json").read_text())
CI = {"global": (0.026, -0.021, 0.090), "global_haq": (0.221, 0.096, 0.347), "global_haqq": (0.278, 0.134, 0.423),
      "pstack": (0.008, -0.042, 0.068), "pstack_poteto": (0.054, -0.001, 0.124)}

e = html.escape


def pct(v, d=0):
    return "—" if v is None else f"{v*100:.{d}f}%"


def table(head, rows, cls="", num_from=1, highlight=None):
    th = "".join(f'<th class="{"num" if i >= num_from else ""}">{h}</th>' for i, h in enumerate(head))
    body = []
    for r in rows:
        tds = []
        for i, c in enumerate(r):
            k = "num" if i >= num_from else ""
            if highlight and (i, c) in highlight:
                k += " hl"
            tds.append(f'<td class="{k}">{c}</td>')
        body.append("<tr>" + "".join(tds) + "</tr>")
    return f'<div class="tbl {cls}"><table><thead><tr>{th}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


# ---------- chart 1: first-delivery score with 95% CI of difference vs base
def chart_delivery():
    vals = {c: hard["overall"]["delivery"][c] for c in C6}
    W, rowh, left, right, top = 640, 34, 120, 70, 24
    H = top + rowh * len(C6) + 34
    x = lambda v: left + (W - left - right) * v
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="조건별 첫 납품 점수">']
    for t in [0, 0.25, 0.5, 0.75, 1.0]:
        out.append(f'<line class="grid" x1="{x(t):.1f}" x2="{x(t):.1f}" y1="{top-6}" y2="{H-26}"/>'
                   f'<text class="tick" x="{x(t):.1f}" y="{H-8}" text-anchor="middle">{int(t*100)}%</text>')
    for i, c in enumerate(C6):
        y = top + i * rowh
        v = vals[c]
        out.append(f'<text class="lab" x="{left-10}" y="{y+15}" text-anchor="end">{L[c]}</text>')
        out.append(f'<rect class="bar {CLS[c]}" x="{left}" y="{y+4}" width="{x(v)-left:.1f}" height="16" rx="3"/>')
        if c in CI:
            d, lo, hi = CI[c]
            b = vals["base"]
            out.append(f'<line class="ci" x1="{x(b+lo):.1f}" x2="{x(b+hi):.1f}" y1="{y+12}" y2="{y+12}"/>'
                       f'<line class="ci" x1="{x(b+lo):.1f}" x2="{x(b+lo):.1f}" y1="{y+7}" y2="{y+17}"/>'
                       f'<line class="ci" x1="{x(b+hi):.1f}" x2="{x(b+hi):.1f}" y1="{y+7}" y2="{y+17}"/>')
        end = max(x(v), x(vals["base"] + CI[c][2]) if c in CI else 0)
        out.append(f'<text class="val" x="{end+8:.1f}" y="{y+16}">{v*100:.0f}%</text>')
    out.append(f'<line class="ref" x1="{x(vals["base"]):.1f}" x2="{x(vals["base"]):.1f}" y1="{top-6}" y2="{H-26}"/>')
    out.append("</svg>")
    return "".join(out)


# ---------- chart 2: where the user's revealed decisions came from
def chart_sources():
    conds = ["base", "global", "global_haq", "global_haqq", "pstack", "pstack_poteto"]
    W, rowh, left, right, top = 640, 34, 120, 16, 10
    H = top + rowh * len(conds) + 4
    x = lambda v: left + (W - left - right) * v
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="사용자가 드러낸 숨은 결정의 출처">']
    for i, c in enumerate(conds):
        o = over[c]
        parts = [(o["revealed_asked"] / o["revealed"], "s-asked"), (o["revealed_mentioned"] / o["revealed"], "s-shown"),
                 (o["revealed_unprompted"] / o["revealed"], "s-over")]
        y = top + i * rowh
        out.append(f'<text class="lab" x="{left-10}" y="{y+15}" text-anchor="end">{L[c]}</text>')
        acc = 0
        for f, k in parts:
            out.append(f'<rect class="{k}" x="{x(acc):.1f}" y="{y+3}" width="{(W-left-right)*f:.1f}" height="18"/>')
            if f >= 0.09:
                out.append(f'<text class="seg" x="{x(acc + f/2):.1f}" y="{y+16}" text-anchor="middle">{f*100:.0f}%</text>')
            acc += f
        out.append(f'<text class="tick" x="{W-right}" y="{y+16}" text-anchor="end"></text>')
    out.append("</svg>")
    return "".join(out)


# ---------- per-task heat table
def heat_cell(v):
    lvl = 0 if v < 0.4 else 1 if v < 0.7 else 2 if v < 0.95 else 3
    return f'<span class="heat h{lvl}">{v*100:.0f}%</span>'


task_rows = [[e(t["task"])] + [heat_cell(t[c]) for c in C6] for t in tasks]

tier_order = [("q_count", "의도", "num"), ("hidden_asked", "의도", "pct"), ("q_precision", "의도", "pct"),
              ("q_waste", "의도", "pct"), ("hidden_recall", "투명성", "pct"), ("disclosure", "투명성", "pct"),
              ("fidelity", "정직성", "pct"), ("claims", "정직성", "num"), ("false_completion", "결과", "pct"),
              ("one_shot", "결과", "pct"), ("cost_per_success", "효율", "usd"), ("data_def", "트랙", "pct")]


def tv(m, c, unit):
    v = tier[m][c]["value"]
    if v is None:
        return "—"
    s = f"{v:.2f}" if unit == "num" else (f"${v:.2f}" if unit == "usd" else f"{v*100:.0f}%")
    ci = tier[m][c]["ci_vs_base"]
    if ci and not (ci[0] <= 0 <= ci[1]) and ci[0] != ci[1]:
        s = f'<b class="sig">{s}</b>'
    return s


tier_rows = [[ax, e(tier[m]["label"])] + [tv(m, c, u) for c in C6] for m, ax, u in tier_order]

over_rows = []
for c in C6:
    o = over[c]
    over_rows.append([L[c], str(o["runs"]), f'{o["revealed"]/o["runs"]:.1f}', pct(o["revealed_asked"] / o["revealed"]),
                      pct(o["revealed_mentioned"] / o["revealed"]), f'<b>{pct(o["revealed_unprompted"] / o["revealed"])}</b>'])

head6 = [L[c] for c in C6]

page = f"""<title>wrxp 효과 실측 보고서</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=IBM+Plex+Sans+KR:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: a report column with a sticky table of contents on wide screens; figures first, method last. */
:root {{
  --paper: #f5f7f6; --panel: #ffffff; --ink: #1c2321; --muted: #5a6662; --rule: #d7dedb;
  --accent: #1b6b5e; --accent-soft: #dcebe7; --copper: #a85f2b; --copper-soft: #f1e1d4;
  --good: #2c7a49; --bad: #b0372f; --warn: #8a6400; --grey: #8d9894; --grey-soft: #e6ebe9;
  --h0: #f3dcd8; --h1: #f2ead2; --h2: #dcebe2; --h3: #bfe0d1;
  --f-display: "Gowun Batang", "Nanum Myeongjo", "AppleMyungjo", serif;
  --f-body: "IBM Plex Sans KR", "Apple SD Gothic Neo", "Malgun Gothic", system-ui, sans-serif;
  --f-mono: "IBM Plex Mono", ui-monospace, "SFMono-Regular", Menlo, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --paper: #111615; --panel: #181e1d; --ink: #e4eae7; --muted: #9aa6a1; --rule: #2a3330;
  --accent: #5fb7a6; --accent-soft: #1d3530; --copper: #e09a62; --copper-soft: #3a2a1d;
  --good: #73c491; --bad: #ec7a71; --warn: #e2b44c; --grey: #7c8884; --grey-soft: #252d2b;
  --h0: #4a2622; --h1: #3d3620; --h2: #213a2e; --h3: #1f5242; color-scheme: dark; }} }}
:root[data-theme="dark"] {{
  --paper: #111615; --panel: #181e1d; --ink: #e4eae7; --muted: #9aa6a1; --rule: #2a3330;
  --accent: #5fb7a6; --accent-soft: #1d3530; --copper: #e09a62; --copper-soft: #3a2a1d;
  --good: #73c491; --bad: #ec7a71; --warn: #e2b44c; --grey: #7c8884; --grey-soft: #252d2b;
  --h0: #4a2622; --h1: #3d3620; --h2: #213a2e; --h3: #1f5242; color-scheme: dark; }}
body {{ background: var(--paper); color: var(--ink); font-family: var(--f-body); font-size: 15.5px; line-height: 1.7; }}
.wrap {{ max-width: 1120px; margin: 0 auto; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 40px 80px;
  display: grid; grid-template-columns: 200px minmax(0, 1fr); gap: 48px; }}
nav.toc {{ position: sticky; top: calc(env(safe-area-inset-top, 0px) + 24px); align-self: start; font-size: 13px; }}
nav.toc p {{ margin: 0 0 10px; color: var(--muted); letter-spacing: .08em; font-size: 11.5px; font-weight: 600; }}
nav.toc ol {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; counter-reset: s; }}
nav.toc a {{ color: var(--muted); text-decoration: none; display: block; padding: 2px 0 2px 10px; border-left: 2px solid var(--rule); }}
nav.toc a:hover, nav.toc a:focus-visible {{ color: var(--accent); border-left-color: var(--accent); outline: none; }}
main {{ min-width: 0; }}
h1, h2, h3 {{ font-family: var(--f-display); font-weight: 700; text-wrap: balance; letter-spacing: -0.01em; }}
h1 {{ font-size: clamp(30px, 4.4vw, 44px); line-height: 1.2; margin: 6px 0 16px; }}
h2 {{ font-size: 26px; line-height: 1.3; margin: 0 0 14px; }}
h3 {{ font-size: 18.5px; margin: 28px 0 8px; }}
p, li {{ max-width: 68ch; }}
p {{ margin: 0 0 14px; }}
.kicker {{ font-family: var(--f-mono); font-size: 12px; color: var(--accent); letter-spacing: .06em; }}
.lede {{ font-size: 18px; color: var(--ink); max-width: 60ch; }}
.meta {{ color: var(--muted); font-size: 13.5px; }}
section {{ padding-top: 44px; margin-top: 44px; border-top: 1px solid var(--rule); scroll-margin-top: 24px; }}
.figs {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 190px), 1fr)); gap: 12px; margin: 26px 0 8px; }}
.fig {{ background: var(--panel); border: 1px solid var(--rule); border-radius: 6px; padding: 14px 16px; display: grid; gap: 4px; align-content: start; }}
.fig .n {{ font-family: var(--f-display); font-size: 30px; line-height: 1.1; font-variant-numeric: tabular-nums; }}
.fig .n.acc {{ color: var(--accent); }} .fig .n.cop {{ color: var(--copper); }}
.fig .t {{ font-size: 13px; color: var(--muted); line-height: 1.5; }}
.callout {{ border-left: 3px solid var(--copper); background: var(--copper-soft); padding: 12px 16px; margin: 18px 0; border-radius: 0 6px 6px 0; max-width: 72ch; }}
.callout.ok {{ border-left-color: var(--accent); background: var(--accent-soft); }}
.callout p:last-child {{ margin-bottom: 0; }}
.tbl {{ overflow-x: auto; margin: 14px 0 18px; border: 1px solid var(--rule); border-radius: 6px; background: var(--panel); }}
table {{ border-collapse: collapse; width: 100%; font-size: 13.5px; }}
th, td {{ padding: 8px 12px; border-bottom: 1px solid var(--rule); text-align: left; vertical-align: top; }}
th {{ font-weight: 600; color: var(--muted); font-size: 12.5px; white-space: nowrap; background: var(--grey-soft); }}
tr:last-child td {{ border-bottom: none; }}
td.num, th.num {{ text-align: right; font-family: var(--f-mono); font-variant-numeric: tabular-nums; white-space: nowrap; }}
td.hl {{ background: var(--accent-soft); }}
b.sig {{ color: var(--accent); }}
.heat {{ display: inline-block; min-width: 44px; padding: 1px 6px; border-radius: 4px; text-align: right; color: var(--ink); }}
.h0 {{ background: var(--h0); }} .h1 {{ background: var(--h1); }} .h2 {{ background: var(--h2); }} .h3 {{ background: var(--h3); }}
figure {{ margin: 18px 0 22px; background: var(--panel); border: 1px solid var(--rule); border-radius: 6px; padding: 16px 16px 10px; }}
figure svg {{ width: 100%; height: auto; display: block; max-width: 100%; }}
figcaption {{ font-size: 13px; color: var(--muted); margin-top: 8px; }}
svg .grid {{ stroke: var(--rule); stroke-width: 1; }}
svg .ref {{ stroke: var(--muted); stroke-width: 1; stroke-dasharray: 3 3; }}
svg .tick {{ fill: var(--muted); font: 11px var(--f-mono); }}
svg .lab {{ fill: var(--ink); font: 13px var(--f-body); }}
svg .val {{ fill: var(--ink); font: 12px var(--f-mono); }}
svg .seg {{ fill: var(--paper); font: 600 11.5px var(--f-mono); }}
svg .ci {{ stroke: var(--ink); stroke-width: 1.4; }}
svg .bar.c-base, svg .bar.c-global {{ fill: var(--grey); }}
svg .bar.c-haq, svg .bar.c-haqq {{ fill: var(--accent); }}
svg .bar.c-pst, svg .bar.c-pst2 {{ fill: var(--copper); }}
svg .s-asked {{ fill: var(--accent); }} svg .s-shown {{ fill: var(--good); opacity: .65; }} svg .s-over {{ fill: var(--bad); opacity: .8; }}
.legend {{ display: flex; flex-wrap: wrap; gap: 14px; font-size: 12.5px; color: var(--muted); margin-top: 6px; }}
.legend i {{ display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px; vertical-align: -1px; }}
.pill {{ display: inline-block; font-size: 12px; padding: 0 8px; border-radius: 999px; border: 1px solid var(--rule); color: var(--muted); }}
.pill.good {{ color: var(--good); border-color: var(--good); }} .pill.bad {{ color: var(--bad); border-color: var(--bad); }} .pill.warn {{ color: var(--warn); border-color: var(--warn); }}
ol.steps, ul.plain {{ padding-left: 20px; }}
ol.steps li, ul.plain li {{ margin-bottom: 8px; }}
code {{ font-family: var(--f-mono); font-size: 0.88em; background: var(--grey-soft); padding: 1px 5px; border-radius: 4px; }}
a {{ color: var(--accent); }}
a:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
@media (max-width: 860px) {{ .wrap {{ grid-template-columns: minmax(0, 1fr); gap: 8px; }} nav.toc {{ position: static; }} nav.toc ol {{ grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); }} }}
</style>

<div class="wrap">
<nav class="toc" aria-label="목차">
  <p>목차</p>
  <ol>
    <li><a href="#summary">요약과 사용법</a></li>
    <li><a href="#setup">무엇을 비교했나</a></li>
    <li><a href="#ability">모델 능력: 표준 벤치마크</a></li>
    <li><a href="#work">실무 효과: 부서 시나리오</a></li>
    <li><a href="#interaction">상호작용의 질</a></li>
    <li><a href="#costs">약점과 비용</a></li>
    <li><a href="#corrections">정정한 결론</a></li>
    <li><a href="#recommend">권고</a></li>
    <li><a href="#limits">한계와 다음 단계</a></li>
    <li><a href="#method">방법과 재현</a></li>
  </ol>
</nav>
<main>
<header>
  <div class="kicker">wrxp 0.1.78 · pstack 0.9.132 · claude-opus-5-5 · 2026-11-06 ~ 11-07</div>
  <h1>wrxp 효과 실측 보고서</h1>
  <p class="lede">wrxp는 모델을 더 똑똑하게 만들지 않습니다. 대신 요구가 덜 정해진 일에서 처음 넘기는 결과물이 맞을 가능성을 크게 높입니다. 그 효과는 질문 tier(haq, haqq)에서 나오고, 비용은 실행당 약 50% 늘어납니다.</p>
  <p class="meta">실행 약 2,200회 · 실행 비용 약 850달러 · 표준 벤치마크 10종, 공개 에이전트 벤치마크 3종, 부서 시나리오 15개</p>
  <div class="figs">
    <div class="fig"><span class="n acc">+22~28%p</span><span class="t">요구가 덜 정해진 부서 업무에서 첫 납품 점수 향상(haq·haqq, 95% 구간이 0을 넘음)</span></div>
    <div class="fig"><span class="n acc">0~1%</span><span class="t">haq·haqq 질문 중 이미 파일에 있던 것을 물은 비율</span></div>
    <div class="fig"><span class="n acc">$1.99</span><span class="t">첫 납품 성공 1건당 비용(haqq). 미적용은 $3.21</span></div>
    <div class="fig"><span class="n">±0</span><span class="t">표준 벤치마크와 SWE-bench Verified 정답률 차이</span></div>
    <div class="fig"><span class="n cop">약 30%</span><span class="t">향상분 가운데 모의 사용자가 묻지 않은 것까지 말해 준 몫. 그래서 위 향상은 상한값입니다.</span></div>
  </div>
</header>

<section id="summary">
  <h2>요약과 사용법</h2>
  <ol class="steps">
    <li><b>모델 능력은 그대로입니다.</b> MMLU-Pro, GPQA Diamond, MATH-500, HumanEval, SWE-bench Verified 등에서 조건 간 차이는 표본 오차 안이었습니다. Opus 5.5가 이미 천장에 가깝습니다.</li>
    <li><b>요구가 덜 정해진 실무에서는 첫 결과물이 확실히 좋아집니다.</b> haq·haqq는 15개 부서 과제 중 10개에서 첫 납품 점수를 올렸고, 사용자의 수정 요청을 과제당 0.45~0.57회 줄였습니다.</li>
    <li><b>실제 작동 방식은 "질문 몇 개와 기본값 미리 보여 주기"입니다.</b> 직접 묻는 숨은 결정은 12~16%뿐입니다. 대신 작업 전에 "따로 말씀 없으면 이렇게 하겠다"는 목록을 보여 주고, 사용자가 그 목록을 고칩니다.</li>
    <li><b>전역 CLAUDE.md 블록의 효과는 응답 언어입니다.</b> 켠 조건은 한국어 질문에 모두 한국어로 답했습니다. 정확도 효과는 없습니다.</li>
    <li><b>pstack은 부서 업무에서 효과가 없었습니다.</b> 코드·터미널 과제에서는 비슷하거나 약간 빨랐고, 보고 충실도는 유의하게 낮았습니다.</li>
  </ol>
  <h3>언제 무엇을 쓰나</h3>
  {table(["상황", "추천", "근거"], [
      ["요구가 분명하고 정답이 정해진 작업(버그 수정, 명세가 있는 구현)", "그냥 요청하거나 <code>/ha</code>", "정답률 차이가 없고, 질문 tier는 비용만 늘립니다."],
      ["원하는 그림은 있는데 세부를 다 말하지 않았을 때(문서 형식, 계산 기준, 대상 범위)", "<code>/haq</code>", "첫 납품 +22%p, 수정 요청 −0.45회"],
      ["정할 게 많을 때(우선순위 기준, 여러 조건이 얽힌 기획)", "<code>/haqq</code>", "첫 납품 +28%p. RICE, 캠페인, 내보내기에서 haq보다 높았습니다."],
      ["아직 뭘 원하는지 모를 때", "<code>/haqq</code>로 정리해 볼 만함", "측정하지 않았습니다(다음 단계)."],
      ["형식·길이·금지어 제약이 있는 결과물을 채팅으로 받을 때", "<code>/ha</code> 계열은 피함", "덧붙이는 결과 틀이 제약을 깹니다(IFEval −7.5%p)."],
  ], num_from=9)}
</section>

<section id="setup">
  <h2>무엇을 비교했나</h2>
  <p>모든 조건은 같은 모델(claude-opus-5-5, Claude Code 2.1.318), 같은 권한, 같은 과제 문장을 썼습니다. 조건마다 별도의 설정 폴더를 써서 차이가 조건 정의에서만 나도록 했습니다.</p>
  {table(["조건", "전역 CLAUDE.md(wrxp:setup)", "플러그인", "첫 메시지 앞"], [
      ["미적용", "없음", "없음", "—"], ["전역만", "있음", "wrxp", "—"], ["/ha만", "없음", "wrxp", "<code>/wrxp:ha</code>"],
      ["전역+ha", "있음", "wrxp", "<code>/wrxp:ha</code>"], ["전역+haq", "있음", "wrxp", "<code>/wrxp:haq</code>"],
      ["전역+haqq", "있음", "wrxp", "<code>/wrxp:haqq</code>"], ["pstack", "없음", "pstack", "— (훅이 poteto-mode로 라우팅)"],
      ["pstack+poteto", "없음", "pstack", "<code>/pstack:poteto-mode</code>"]], num_from=9)}
  <h3>실험 일정</h3>
  {table(["차수", "내용", "조건", "실행 수", "비용"], [
      ["1차", "부서 실무 과제 14개(사용자 없음)", "미적용 / /ha", "84", "$24"],
      ["2차", "2×2 설계 + 표준 벤치마크 10종", "미적용 / 전역만 / /ha만 / 전역+ha", "964", "$177"],
      ["3차", "숨은 의도 과제 5개 + 모의 사용자", "미적용 / 전역 / ha / haq / haqq", "75", "$83"],
      ["4차", "부서 시나리오 15개 + τ²-bench + SWE-bench Verified + Terminal-Bench 2", "미적용 / 전역 / haq / haqq / pstack ×2", "648", "약 $560"],
      ["재분석", "4차 부서 기록 360회로 상호작용 지표 계산", "4차와 같음", "판정 약 500회", "약 $16"]], num_from=3)}
</section>

<section id="ability">
  <h2>모델 능력: 표준 벤치마크</h2>
  <p>정답이 정해진 문항에서는 어느 조건도 점수를 바꾸지 못했습니다. 차이가 난 것은 형식 제약을 지키는 IFEval과 검색 순위 정도였고, 그마저도 문항이 적어 대부분 표본 오차 안입니다.</p>
  {table(["벤치마크", "지표", "미적용", "전역만", "/ha만", "전역+ha"], [
      ["MMLU-Pro", "정확도", "95%", "95%", "95%", "95%"], ["GPQA Diamond", "정확도", "100%", "100%", "100%", "100%"],
      ["MATH-500", "정확도", "100%", "100%", "100%", "100%"], ["GSM8K", "정확도", "90%", "95%", "95%", "95%"],
      ["BIG-Bench Hard", "정확 일치", "95%", "95%", "95%", "95%"], ["HumanEval · MBPP", "pass@1", "100%", "100%", "100%", "100%"],
      ["TruthfulQA MC1", "정확도", "100%", "100%", "100%", "100%"], ["IFEval", "프롬프트 strict", "90%", "95%", "85%", "85%"],
      ["SciFact", "Recall@5", "93%", "93%", "88%", "88%"], ["SciFact", "MRR@10", "0.853", "0.845", "0.911", "0.864"],
      ["10종 평균", "", "96.3%", "97.3%", "95.8%", "95.8%"]], num_from=2)}
  <p class="meta">벤치마크당 약 20문항, 2차 실험(2026-11-06).</p>
  <h3>공개 에이전트 벤치마크 (4차)</h3>
  {table(["벤치마크", "지표"] + head6, [
      ["τ²-bench (retail+airline)", "pass^1", "88%", "88%", "75%", "81%", "88%", "88%"],
      ["τ²-bench", "pass^2", "75%", "75%", "62%", "75%", "75%", "75%"],
      ["SWE-bench Verified", "해결률", "100%", "100%", "100%", "100%", "100%", "100%"],
      ["Terminal-Bench 2", "해결률", "88%", "81%", "88%", "88%", "94%", "94%"]], num_from=2)}
  <p>τ²-bench는 8과제 × 2회라 1~2과제 차이입니다. SWE-bench Verified는 고른 8문항이 모두 천장이었습니다. Terminal-Bench 2의 차이는 부하에 민감한 성능 측정 과제 하나에서만 났습니다. 이 세 벤치마크에서는 어느 쪽에도 유의한 효과가 없었습니다.</p>
</section>

<section id="work">
  <h2>실무 효과: 부서 시나리오</h2>
  <p>15개 과제마다 숨은 의도를 아는 모의 사용자(Sonnet 5.5)가 같은 세션에서 질문에 답하고, 결과 보고에서 어긋난 점이 보이면 수정을 요청합니다. 사용자 턴은 최대 3회입니다. 조건마다 과제당 4회, 모두 360회 실행했습니다.</p>
  <figure>
    {chart_delivery()}
    <figcaption>첫 납품 점수 평균. 막대 위 가로선은 미적용 대비 차이의 95% 구간(과제 단위 부트스트랩)이고, 점선은 미적용 수준입니다.</figcaption>
  </figure>
  {table(["지표"] + head6, [
      ["첫 납품 점수", "64%", "66%", "<b class='sig'>86%</b>", "<b class='sig'>92%</b>", "65%", "69%"],
      ["최종 점수", "98%", "97%", "98%", "97%", "99%", "98%"],
      ["수정 요청(과제당)", "0.9", "0.8", "<b class='sig'>0.5</b>", "<b class='sig'>0.3</b>", "0.9", "0.8"],
      ["미적용 대비 첫 납품", "—", "+3%p", "+22%p", "+28%p", "+1%p", "+5%p"],
      ["좋아진 과제 / 나빠진 과제", "—", "4 / 5", "10 / 1", "10 / 1", "2 / 5", "5 / 1"],
      ["1건 비용", "$0.75", "$0.85", "$1.14", "$1.16", "$0.95", "$1.02"]], num_from=1)}
  <h3>과제별 첫 납품 점수</h3>
  {table(["과제"] + head6, task_rows, cls="heat-table", num_from=1)}
  <p>숨은 결정이 있는 과제(견적서, 코호트, 계약 검토, 온보딩, 내보내기, 쿠폰)에서 차이가 컸습니다. 질문으로 풀리지 않는 과제(재고 버그, API 이전, 성능 개선, CS 매크로)는 조건 간 차이가 없거나 작았습니다.</p>
</section>

<section id="interaction">
  <h2>상호작용의 질</h2>
  <p>4차 부서 기록 360회를 다시 판정해, 결과의 정답률이 아니라 대화의 질을 숫자로 만들었습니다. 과제마다 숨은 결정과 파일에서 찾을 수 있는 사실의 목록을 만들고, 각 실행의 질문과 보고를 그 목록에 대응시켰습니다. 굵은 녹색은 미적용 대비 95% 구간이 0을 넘는 값입니다.</p>
  {table(["축", "지표"] + head6, tier_rows, num_from=2)}
  <p class="meta">질문 정밀도와 낭비율은 질문이 적은 조건(60회 합계: 미적용 4개, 전역만 13개, pstack 13개, pstack+poteto 16개)에서 불안정합니다. haq 50개, haqq 63개입니다.</p>
  <h3>사용자가 드러낸 숨은 결정은 어디서 나왔나</h3>
  <figure>
    {chart_sources()}
    <div class="legend"><span><i style="background:var(--accent)"></i>에이전트가 물은 것</span><span><i style="background:var(--good);opacity:.65"></i>에이전트가 기본값으로 먼저 보여 주고 사용자가 고친 것</span><span><i style="background:var(--bad);opacity:.8"></i>묻지도 보여 주지도 않았는데 사용자가 먼저 말한 것</span></div>
    <figcaption>첫 납품 전에 사용자가 답한 실행만 셌습니다.</figcaption>
  </figure>
  {table(["조건", "답변이 있었던 실행", "실행당 드러난 결정", "물은 것", "기본값을 고친 것", "과잉 공개"], over_rows, num_from=1)}
  <div class="callout ok"><p><b>해석.</b> haq·haqq가 첫 결과물을 맞히는 주된 경로는 작업 전 기본값 공개였습니다. 드러난 결정의 절반이 이 경로에서 나왔고, 직접 질문은 17~24%였습니다. 질문은 정확했습니다. 94~98%가 실제 숨은 결정을 짚었고, 파일에 이미 있는 것을 물은 경우는 거의 없었습니다.</p></div>
  <div class="callout"><p><b>주의.</b> haq·haqq 실행에서 드러난 결정의 약 30%는 에이전트가 묻지도 보여 주지도 않았는데 모의 사용자가 먼저 말했습니다. "묻지 않은 세부를 먼저 알려 주지 않는다"는 지시를 Sonnet이 어긴 것입니다. 그래서 첫 납품 향상은 상한값으로 봐야 하고, 엄격한 모의 사용자로 다시 재야 합니다.</p></div>
  <p>그 밖의 발견은 이렇습니다.</p>
  <ul class="plain">
    <li><b>가정 공개율은 조건 간 차이가 없습니다(68~79%).</b> Opus 5.5는 원래 자기가 정한 값을 보고에 적습니다. wrxp는 그 시점을 결과물 앞으로 옮깁니다.</li>
    <li><b>보고 충실도는 pstack이 유의하게 낮았습니다(78~80%).</b> 도구 기록에 없는 "다시 계산해 확인했다"류 주장이 많았습니다. haq·haqq(86~87%)와 미적용(91%)의 차이는 유의하지 않습니다.</li>
    <li><b>수정 1회 해결률은 모든 조건이 79~88%로 비슷합니다.</b> 지적받은 뒤 고치는 능력은 모델 자체의 능력입니다.</li>
  </ul>
</section>

<section id="costs">
  <h2>약점과 비용</h2>
  {table(["항목", "측정값", "판단"], [
      ["실행 1건 비용", "부서 업무 +$0.39~0.41(+52%), 코드·터미널 +$0.10~0.17(+30~75%)", "<span class='pill warn'>비용 증가</span>"],
      ["형식 제약 산출물", "IFEval 90% → 85%(/ha). 덧붙인 확인 문장이 금지어를 쓰거나 글머리표 개수를 깸", "<span class='pill bad'>고쳐야 함</span>"],
      ["응답 언어", "/ha만 쓰면 영어 응답이 늘었고, 전역 블록과 함께 쓰면 100% 한국어", "<span class='pill good'>전역 블록으로 해결</span>"],
      ["범위 확장 앞 멈춤", "같은 원인 버그 두 곳을 9회 중 9회 '함께 고칠까요?'로 묻고 멈춤", "<span class='pill warn'>규칙 재검토</span>"],
      ["답 길이", "미적용 대비 1.4배", "<span class='pill warn'>정보 밀도 확인 필요</span>"],
      ["pstack 보고 충실도", "도구 기록으로 뒷받침된 검증 주장 78~80%(미적용 91%)", "<span class='pill bad'>pstack 약점</span>"]], num_from=9)}
</section>

<section id="corrections">
  <h2>정정한 결론</h2>
  <p>표본을 늘리거나 다시 분석하면서 앞서 보고한 내용 중 세 가지를 바로잡았습니다.</p>
  {table(["앞선 보고", "정정"], [
      ["문서에 지어낸 사실이 −67% 줄었다(1차)", "2차에서 재현되지 않았습니다(미적용 2건, /ha 5건). 채점자 판정의 변동이 조건 차이보다 컸습니다."],
      ["질문 tier는 비용이 늘지 않는다(3차, 5과제)", "15과제에서는 건당 +52%로 유의했습니다. 대신 첫 납품 성공 1건당 비용은 더 낮습니다."],
      ["haq·haqq 첫 납품 +22~28%p", "약 30%가 모의 사용자의 과잉 공개 덕분이므로 상한값입니다."]], num_from=9)}
</section>

<section id="recommend">
  <h2>권고</h2>
  <h3>wrxp에 반영할 것</h3>
  <ol class="steps">
    <li><b>결과 틀을 산출물에서 분리합니다.</b> 형식·길이·금지어 제약이 있는 결과물에서는 "제가 정한 것·확인한 것"을 빼거나 산출물 밖으로 옮깁니다.</li>
    <li><b>같은 원인의 버그는 함께 고치고 보고하는 쪽을 기본으로 합니다.</b> 9회 중 9회가 같은 질문으로 멈췄고, 미적용은 묻지 않고 모두 고쳤습니다.</li>
    <li><b>작업 전 기본값 공개를 명시적인 강점으로 다듬습니다.</b> 효과의 주된 경로이므로 /ha(질문 0개)에서도 쓸 수 있는지 검토할 만합니다.</li>
    <li><b>README의 논문 인용 수치를 실측값으로 바꿉니다.</b> "모호한 요청 정확도 33.3%→100%" 같은 수치는 이번 실측으로 재현되지 않았습니다.</li>
  </ol>
  <h3>사용자에게</h3>
  <ul class="plain">
    <li>전역 블록(<code>/wrxp:setup</code>)은 켜 둡니다. 비용이 작고 언어 일관성 효과가 분명합니다.</li>
    <li>요구가 덜 정해진 기획·영업·HR·데이터·법무 작업은 <code>/haqq</code>로 시작합니다.</li>
    <li>정답이 정해진 코드 수정은 그냥 진행합니다.</li>
    <li>wrxp와 pstack을 함께 쓸 근거는 이번 데이터에 없습니다(함께 설치한 조건은 측정하지 않음).</li>
  </ul>
</section>

<section id="limits">
  <h2>한계와 다음 단계</h2>
  <ul class="plain">
    <li><b>모의 사용자는 실제 사용자가 아닙니다.</b> 의도를 정확히 알고, 지시를 어기고 먼저 말하기도 했습니다.</li>
    <li><b>판정자는 Sonnet 5.5 하나입니다.</b> 과제별 정답지와 일부 표본만 사람이 검토했습니다.</li>
    <li><b>τ²-bench는 DB 상태 보상만 썼습니다.</b> 사용자 모델도 공식과 달라 리더보드와 직접 비교할 수 없습니다.</li>
    <li><b>Terminal-Bench 2는 컨테이너 네트워크 없이 돌렸습니다.</b> SWE-bench는 쉬운 문항만 들어갔습니다.</li>
    <li><b>측정하지 못한 것:</b> 불필요한 질문 비율, 과잉 차단율, "모르겠다"는 사용자, 수정 5·10회 점검, 사람 독자의 이해도.</li>
  </ul>
  <h3>다음 실험(제안, 약 150~250달러)</h3>
  <ol class="steps">
    <li>질문받은 것과 보여 준 기본값에만 답하는 엄격한 모의 사용자로 부서 시나리오를 다시 측정합니다.</li>
    <li>숨은 결정이 없는 쌍둥이 과제로 불필요한 질문 비율을 잽니다.</li>
    <li>위험·안전 시나리오 각 8개로 무단 위험 행동률과 과잉 차단율을 잽니다.</li>
    <li>"모르겠다"고 답하는 사용자 조건을 추가합니다.</li>
    <li>결과 틀을 고친 뒤 IFEval을 다시 잽니다.</li>
  </ol>
</section>

<section id="method">
  <h2>방법과 재현</h2>
  <p>코드와 원자료는 <code>donghyunlim/claude-middleware</code> 저장소의 <code>ccr-19908822-0fhs21</code> 브랜치, <code>benchmarks/wrxp-spec-test/</code>에 있습니다.</p>
  {table(["구성", "경로", "내용"], [
      ["조건 정의", "<code>conditions.py</code>", "조건마다 별도 설정 폴더. 전역 조건은 setup 스크립트의 실제 출력 사용"],
      ["부서 시나리오", "<code>hard/</code>", "fixture, 숨은 의도, 숨긴 테스트, 모의 사용자 실행기, 채점기"],
      ["상호작용 지표", "<code>hard/metrics_tier1.py</code> 외", "과제별 정답지, 실행별 판정, 과잉 공개 검사"],
      ["표준 벤치마크", "<code>std/</code>", "원 배포처에서 받아 고정 시드 표본, IFEval 공식 채점 코드"],
      ["τ²-bench", "<code>tau2/</code>", "도메인 도구를 MCP로 노출, τ²-bench DB 평가기로 채점"],
      ["SWE-bench Verified", "<code>swebench/</code>", "공개 실행 로그에서 문항 재구성, 공식 Docker 이미지로 채점"],
      ["Terminal-Bench 2", "<code>tbench/</code>", "공식 이미지, 오프라인 테스트 키트"],
      ["결과 문서", "<code>results/</code>", "차수별 RESULTS.md, 표, 실행별 원자료"]], num_from=9)}
  <p class="meta">통계: 차이의 구간은 과제 단위(부서 시나리오) 또는 문항 단위(표준 벤치마크) 부트스트랩 95% 구간입니다. 표본이 작아 구간이 0을 포함하는 차이는 효과로 해석하지 않았습니다.</p>
</section>
</main>
</div>
"""
OUT.write_text(page)
print(OUT, len(page))
