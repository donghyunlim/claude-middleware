// Raw CDP on one page of a Chromium/Electron process (the user's browser, or a WorxSales slot read-only).
// Playwright connectOverCDP can hang on a browser with many tabs; this talks to one tab's websocket only.
// Needs Node >= 22 (global WebSocket). Always exits with process.exit so no connection stays attached.
//
// Usage: node cdp_tab.mjs <port> <command> [args...]
//   list                              id, type, url of every page
//   eval <urlPrefix> <js>             Runtime.evaluate on the first page whose url starts with urlPrefix
//                                     (awaitPromise, returnByValue; prints JSON up to 3000 chars)
//   open <url>                        /json/new: a temporary tab; prints its id. Close it with `close` when done
//   close <id>                        /json/close/<id>
//   shot <id> <out.png>               screenshot of that page
// Examples:
//   node cdp_tab.mjs 9222 list
//   node cdp_tab.mjs 9333 eval worxsales:// "window.worxDesktop.gws.getConnection()"     # read-only bridge check
//   node cdp_tab.mjs 9222 open "https://calendar.google.com/calendar/r/eventedit?text=QA-..."
const [port, cmd, ...args] = process.argv.slice(2);
const base = `http://127.0.0.1:${port}`;
const out = (s) => { console.log(typeof s === "string" ? s : JSON.stringify(s, null, 0).slice(0, 3000)); process.exit(0); };
const fail = (s) => { console.error(s); process.exit(1); };
if (!port || !cmd) fail("usage: node cdp_tab.mjs <port> list|eval|open|close|shot ...");
setTimeout(() => fail("timeout after 45 s"), 45000);

async function session(target) {
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((ok, no) => { ws.onopen = ok; ws.onerror = () => no(new Error("websocket error")); });
  let id = 0; const pend = {};
  ws.onmessage = (m) => { const d = JSON.parse(m.data); if (pend[d.id]) { pend[d.id](d); delete pend[d.id]; } };
  return (method, params = {}) => new Promise((ok) => { pend[++id] = ok; ws.send(JSON.stringify({ id, method, params })); });
}
const pages = async () => (await (await fetch(`${base}/json/list`)).json()).filter((t) => t.type === "page");

if (cmd === "list") out((await pages()).map((t) => `${t.id}\t${t.url.slice(0, 120)}`).join("\n"));
if (cmd === "eval") {
  const [prefix, js] = args;
  const t = (await pages()).find((x) => x.url.startsWith(prefix));
  if (!t) fail(`no page starting with ${prefix}`);
  const send = await session(t);
  const r = await send("Runtime.evaluate", { expression: js, awaitPromise: true, returnByValue: true });
  out(r.result?.result?.value ?? r.result?.exceptionDetails ?? r.result);
}
if (cmd === "open") {
  const r = await fetch(`${base}/json/new?${encodeURI(args[0])}`, { method: "PUT" });
  out((await r.json()).id);
}
if (cmd === "close") out(await (await fetch(`${base}/json/close/${args[0]}`)).text());
if (cmd === "shot") {
  const t = (await pages()).find((x) => x.id === args[0]);
  if (!t) fail(`no page ${args[0]}`);
  const send = await session(t);
  const r = await send("Page.captureScreenshot", { format: "png" });
  (await import("node:fs")).writeFileSync(args[1], Buffer.from(r.result.data, "base64"));
  out(args[1]);
}
fail(`unknown command ${cmd}`);
