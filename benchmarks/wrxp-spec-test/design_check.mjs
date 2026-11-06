// Automated accessibility/spec checks for design-form/signup.html.
// Usage: node design_check.mjs path/to/signup.html  -> prints JSON
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
import { pathToFileURL } from 'url';
import fs from 'fs';

const file = process.argv[2];
const out = { exists: fs.existsSync(file) };
if (!out.exists) { console.log(JSON.stringify(out)); process.exit(0); }
const html = fs.readFileSync(file, 'utf8');
const PALETTE = ['#ffffff', '#1f2328', '#1f5fd1', '#c62828', '#8c959f', '#a0a7b0'];
const hexes = [...html.matchAll(/#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b/g)].map(m => {
  let h = m[0].toLowerCase();
  if (h.length === 4) h = '#' + [...h.slice(1)].map(c => c + c).join('');
  return h;
});
out.off_palette_hex = [...new Set(hexes.filter(h => !PALETTE.includes(h)))];
out.external_resources = /<(script|link)[^>]+(src|href)=["']https?:/i.test(html);

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 360, height: 800 } });
let navigations = 0;
page.on('framenavigated', f => { if (f === page.mainFrame()) navigations++; });
await page.goto(pathToFileURL(file).href);
navigations = 0;

const lum = c => {
  const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null;
  const [r, g, b, a] = m[1].split(',').map(Number);
  if (a === 0) return null;
  const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
};

async function contrastFailures() {
  const items = await page.evaluate(() => {
    const res = [];
    const bgOf = el => {
      while (el) {
        const c = getComputedStyle(el).backgroundColor;
        if (c && !c.startsWith('rgba(0, 0, 0, 0)') && c !== 'transparent') return c;
        el = el.parentElement;
      }
      return 'rgb(255, 255, 255)';
    };
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const t = walker.currentNode; const el = t.parentElement;
      if (!t.textContent.trim() || !el) continue;
      const cs = getComputedStyle(el); const r = el.getBoundingClientRect();
      if (cs.visibility === 'hidden' || cs.display === 'none' || r.width === 0 || r.height === 0) continue;
      if (el.closest('[aria-hidden="true"]')) continue;
      res.push({ text: t.textContent.trim().slice(0, 40), fg: cs.color, bg: bgOf(el), size: parseFloat(cs.fontSize), weight: cs.fontWeight });
    }
    // placeholders count as text too
    document.querySelectorAll('input[placeholder]').forEach(i => {
      const cs = getComputedStyle(i, '::placeholder');
      res.push({ text: 'placeholder:' + i.placeholder.slice(0, 30), fg: cs.color, bg: bgOf(i), size: parseFloat(cs.fontSize), weight: cs.fontWeight });
    });
    return res;
  });
  const fails = [];
  for (const it of items) {
    const L1 = lum(it.fg), L2 = lum(it.bg); if (L1 == null || L2 == null) continue;
    const ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
    const large = it.size >= 24 || (it.size >= 18.66 && Number(it.weight) >= 700);
    if (ratio < (large ? 3 : 4.5)) fails.push({ text: it.text, ratio: Math.round(ratio * 100) / 100 });
  }
  return { checked: items.length, fails };
}

out.contrast_initial = await contrastFailures();
out.hscroll_360 = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);

const fields = await page.evaluate(() => {
  const inputs = [...document.querySelectorAll('input:not([type=hidden]), select, textarea')];
  return inputs.map(i => {
    let name = i.getAttribute('aria-label') || '';
    if (i.labels && i.labels.length) name = name || [...i.labels].map(l => l.textContent.trim()).join(' ');
    const lb = i.getAttribute('aria-labelledby');
    if (lb) name = name || lb.split(/\s+/).map(id => document.getElementById(id)?.textContent || '').join(' ').trim();
    return { type: i.type, name: name.trim(), required: i.required || i.getAttribute('aria-required') === 'true' };
  });
});
out.fields = fields;
out.unlabeled_inputs = fields.filter(f => !f.name).length;
out.has_email = fields.some(f => f.type === 'email' || /이메일|email/i.test(f.name));
out.has_password = fields.some(f => f.type === 'password');
out.has_checkbox = fields.some(f => f.type === 'checkbox');

// keyboard focus visibility: tab to first input and compare style with blurred style
out.focus_visible = await page.evaluate(() => true);
const before = await page.evaluate(() => { const i = document.querySelector('input'); const s = getComputedStyle(i); return [s.outlineStyle, s.outlineWidth, s.boxShadow, s.borderColor].join('|'); });
await page.keyboard.press('Tab');
const focusInfo = await page.evaluate(() => { const a = document.activeElement; const s = getComputedStyle(a); return { tag: a.tagName, style: [s.outlineStyle, s.outlineWidth, s.boxShadow, s.borderColor].join('|') }; });
out.first_tab_target = focusInfo.tag;
out.focus_visible = focusInfo.tag !== 'BODY' && (focusInfo.style !== before || !/^none\|/.test(focusInfo.style));

// submit empty form via button click
const btn = page.locator('button, input[type=submit]').filter({ hasText: /가입/ }).first();
let btnCount = await btn.count();
if (!btnCount) { out.submit_button = false; } else {
  out.submit_button = true;
  const disabled = await btn.isDisabled();
  out.button_disabled_initially = disabled;
  if (!disabled) await btn.click({ timeout: 3000 }).catch(() => {});
  await page.waitForTimeout(300);
  out.navigated_on_invalid_submit = navigations > 0;
  const err = await page.evaluate(() => {
    const inputs = [...document.querySelectorAll('input:not([type=hidden])')];
    return inputs.map(i => {
      const ids = (i.getAttribute('aria-describedby') || '') + ' ' + (i.getAttribute('aria-errormessage') || '');
      const txt = ids.split(/\s+/).filter(Boolean).map(id => { const e = document.getElementById(id); if (!e) return ''; const cs = getComputedStyle(e); return (cs.display === 'none' || cs.visibility === 'hidden') ? '' : e.textContent.trim(); }).join(' ');
      return { type: i.type, invalid: i.getAttribute('aria-invalid') === 'true', linked_error: txt };
    });
  });
  out.after_submit = err;
  out.fields_with_linked_error = err.filter(e => e.invalid && e.linked_error.length > 0).length;
  out.contrast_after_submit = await contrastFailures();
}
await browser.close();
console.log(JSON.stringify(out));
