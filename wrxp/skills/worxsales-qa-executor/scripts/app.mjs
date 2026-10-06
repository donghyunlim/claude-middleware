// Drive the running WorxSales Electron app over CDP. One command per invocation.
// Never closes the browser: the app session lives only in memory and must survive.
//
// Env:
//   QA_HOME   QA workspace (has config.json). Default: cwd.
//   CDP       CDP endpoint. Default: config.cdp or http://127.0.0.1:9333
//   PW_FROM   package.json whose node_modules has playwright-core. Default: config.desktop_worktree/package.json
//
// Commands:
//   text [scope]                 visible text of the active work page (or whole body with scope=body)
//   tree [scope]                 visible interactive elements: role<TAB>name[<TAB>disabled]
//   click <target-json>          click one element
//   fill <target-json> <value>   fill one textbox
//   press <key>                  keyboard key (Enter, Escape, ...)
//   scroll <target-json|page> <dy>
//   shot <out.png>               plain screenshot
//   mark <out.png> <marks-json>  numbered red boxes + optional zoom crop (<out>-zoom.png)
//
// target-json: {"role":"tab","name":"회원 ID"} | {"label":"이름"} | {"text":"저장"} | {"css":"..."}
//   optional: "exact":true, "nth":0, "scope":"page"|"body"|"<css>"  (default scope "page" = active work page,
//   so sidebar items with the same name are not picked by mistake)
// marks-json: [{"n":1,"target":{...},"label":"메모 입력란"}, ...]  (a file path or inline JSON)
import { createRequire } from "node:module";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

const home = process.env.QA_HOME || process.cwd();
const cfgPath = path.join(home, "config.json");
const cfg = existsSync(cfgPath) ? JSON.parse(readFileSync(cfgPath, "utf8")) : {};
const pwFrom = process.env.PW_FROM || (cfg.desktop_worktree && path.join(cfg.desktop_worktree, "package.json"));
if (!pwFrom) throw new Error("set PW_FROM or config.json desktop_worktree");
const { chromium } = createRequire(pwFrom)("playwright-core");
const CDP = process.env.CDP || cfg.cdp || "http://127.0.0.1:9333";
const PAGE_SCOPE = ".workspace-page:not([hidden])";

const browser = await chromium.connectOverCDP(CDP);
const page = browser.contexts().flatMap(c => c.pages()).find(p => p.url().startsWith("worxsales://"));
if (!page) { console.error("WorxSales renderer page not found"); process.exit(2); }

const parse = s => (existsSync(s) ? JSON.parse(readFileSync(s, "utf8")) : JSON.parse(s));
async function root(scope = "page") {
  if (scope === "body") return page.locator("body");
  const css = scope === "page" ? PAGE_SCOPE : scope;
  const r = page.locator(css).first();
  return (await r.count()) ? r : page.locator("body");
}
async function locate(t) {
  const r = await root(t.scope);
  const o = { exact: !!t.exact };
  let l = t.role ? r.getByRole(t.role, { name: t.name, ...o })
    : t.label ? r.getByLabel(t.label, o)
    : t.text ? r.getByText(t.text, o)
    : r.locator(t.css);
  return l.nth(t.nth ?? 0);
}

async function drawMarks(marks) {
  const found = [];
  for (const m of marks) {
    const l = await locate(m.target);
    await l.scrollIntoViewIfNeeded({ timeout: 3000 }).catch(() => {});
  }
  for (const m of marks) {
    const b = await (await locate(m.target)).boundingBox().catch(() => null);
    found.push({ n: m.n, label: m.label || "", box: b });
  }
  await page.evaluate(items => {
    const circled = n => (n >= 1 && n <= 20 ? String.fromCodePoint(0x2460 + n - 1) : String(n));
    for (const it of items) {
      if (!it.box) continue;
      const { x, y, width, height } = it.box;
      const box = document.createElement("div");
      box.className = "__qa_mark";
      Object.assign(box.style, { position: "fixed", left: x - 4 + "px", top: y - 4 + "px", width: width + 8 + "px", height: height + 8 + "px",
        border: "3px solid #e5121b", borderRadius: "6px", zIndex: 2147483646, pointerEvents: "none", boxSizing: "border-box" });
      const tag = document.createElement("div");
      tag.className = "__qa_mark";
      tag.textContent = circled(it.n);
      const top = y - 30 < 0 ? y + height + 6 : y - 30;
      Object.assign(tag.style, { position: "fixed", left: Math.max(0, x - 4) + "px", top: top + "px", minWidth: "24px", height: "24px",
        padding: "0 6px", background: "#e5121b", color: "#fff", font: "700 16px/24px -apple-system,sans-serif", textAlign: "center",
        borderRadius: "12px", zIndex: 2147483647, pointerEvents: "none", boxShadow: "0 1px 3px rgba(0,0,0,.35)" });
      document.body.append(box, tag);
    }
  }, found);
  return found;
}
const clearMarks = () => page.evaluate(() => document.querySelectorAll(".__qa_mark").forEach(e => e.remove()));

const [cmd, ...a] = process.argv.slice(2);
try {
  if (cmd === "text") {
    console.log((await (await root(a[0] || "page")).innerText()).slice(0, 6000));
  } else if (cmd === "tree") {
    const r = await root(a[0] || "page");
    const items = await r.evaluate(el => {
      const sel = "button,a,input,select,textarea,[role=button],[role=tab],[role=combobox],[role=option],[role=menuitem],[role=link],[role=checkbox],[role=radio]";
      return [...el.querySelectorAll(sel)].filter(e => { const b = e.getBoundingClientRect(); return b.width && b.height; })
        .map(e => `${e.getAttribute("role") || e.tagName.toLowerCase()}\t${(e.getAttribute("aria-label") || e.innerText || e.placeholder || e.value || "").trim().replace(/\s+/g, " ").slice(0, 60)}${e.disabled || e.getAttribute("aria-disabled") === "true" ? "\tdisabled" : ""}`);
    });
    console.log(items.join("\n"));
  } else if (cmd === "click") {
    await (await locate(parse(a[0]))).click({ timeout: 5000 }); await page.waitForTimeout(700); console.log("clicked");
  } else if (cmd === "fill") {
    await (await locate(parse(a[0]))).fill(a[1], { timeout: 5000 }); console.log("filled");
  } else if (cmd === "press") {
    await page.keyboard.press(a[0]); await page.waitForTimeout(500); console.log("pressed");
  } else if (cmd === "scroll") {
    if (a[0] === "page") await page.mouse.wheel(0, Number(a[1]));
    else await (await locate(parse(a[0]))).evaluate((e, dy) => e.scrollBy(0, dy), Number(a[1]));
    await page.waitForTimeout(400); console.log("scrolled");
  } else if (cmd === "shot") {
    await page.screenshot({ path: a[0] }); console.log(a[0]);
  } else if (cmd === "mark") {
    const marks = parse(a[1]);
    const found = await drawMarks(marks);
    await page.screenshot({ path: a[0] });
    const boxes = found.filter(f => f.box).map(f => f.box);
    if (boxes.length) {
      const vp = page.viewportSize() || await page.evaluate(() => ({ width: innerWidth, height: innerHeight }));
      const x0 = Math.max(0, Math.min(...boxes.map(b => b.x)) - 60), y0 = Math.max(0, Math.min(...boxes.map(b => b.y)) - 70);
      const x1 = Math.min(vp.width, Math.max(...boxes.map(b => b.x + b.width)) + 60), y1 = Math.min(vp.height, Math.max(...boxes.map(b => b.y + b.height)) + 60);
      if ((x1 - x0) * (y1 - y0) < vp.width * vp.height * 0.45) {
        await page.screenshot({ path: a[0].replace(/\.png$/, "-zoom.png"), clip: { x: x0, y: y0, width: x1 - x0, height: y1 - y0 } });
      }
    }
    await clearMarks();
    console.log(JSON.stringify({ file: a[0], marks: found.map(f => ({ n: f.n, label: f.label, found: !!f.box })) }));
    if (found.some(f => !f.box)) process.exitCode = 3;
  } else {
    console.error("unknown command"); process.exitCode = 1;
  }
} catch (e) {
  await clearMarks().catch(() => {});
  console.error(String(e.message || e).split("\n")[0]); process.exitCode = 1;
}
process.exit(process.exitCode ?? 0); // never browser.close(): keep the logged-in app alive
