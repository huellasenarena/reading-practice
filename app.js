// Reading Practice: random questions from data/*.json, progress kept in localStorage.
"use strict";

const LETTERS = "ABCDEFGH";
const STORE = "rp-progress-v1";
const PREFS = "rp-prefs-v1";
const FLAGS = "rp-flags-v1";
const $ = (id) => document.getElementById(id);

let all = [];           // every question
let current = null;     // question on screen
let progress = load(STORE, {});   // id -> {r: "c" | "w" | "u", a: answer given, t: time}
let flags = load(FLAGS, {});      // id -> {t: time, note: text}: questions the owner thinks are wrong
let prefs = load(PREFS, { test: "", type: "", verbalOnly: false, redo: false, wrongOnly: false });

function load(key, fallback) {
  try { return JSON.parse(localStorage.getItem(key)) || fallback; } catch { return fallback; }
}
function save(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* private mode: progress lasts for this visit only */ }
}

// ---- text formatting: escape, then **bold**, *italic*, ++underline++, paragraphs on blank lines
function esc(s) {
  return s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}
function inline(s) {
  return esc(s)
    .replace(/\*\*(.+?)\*\*/g, "<b>$1</b>")
    .replace(/\+\+(.+?)\+\+/g, "<u>$1</u>")
    .replace(/(^|[\s(“"])\*(?!\s)(.+?)(?<!\s)\*(?=[\s.,;:!?)”"]|$)/g, "$1<i>$2</i>");
}
function paras(s) {
  if (!s) return "";
  return s.split(/\n\s*\n/).map((p) => `<p>${inline(p)}</p>`).join("");
}

// ---- data
async function init() {
  const getJSON = (url) => fetch(url).then((r) => r.json()).catch(() => fetch(url).then((r) => r.json())); // one retry
  const files = await getJSON("data/index.json");
  const sets = await Promise.all(files.map((f) => getJSON(`data/${f}.json`)));
  all = sets.flat();
  buildTestSelect();
  for (const id of ["verbalOnly", "redo", "wrongOnly"]) {
    $(id).checked = !!prefs[id];
    $(id).addEventListener("change", () => { prefs[id] = $(id).checked; save(PREFS, prefs); refresh(true); });
  }
  $("test").addEventListener("change", () => { prefs.test = $("test").value; prefs.type = ""; save(PREFS, prefs); buildTypeSelect(); refresh(true); });
  $("type").addEventListener("change", () => { prefs.type = $("type").value; save(PREFS, prefs); refresh(true); });
  $("reset").addEventListener("click", resetProgress);
  $("exportFlags").addEventListener("click", exportFlags);
  renderFlagCount();
  document.addEventListener("keydown", onKey);
  window.addEventListener("hashchange", () => showById(location.hash.slice(1)));
  buildTypeSelect();
  renderProgress();
  if (!showById(location.hash.slice(1))) refresh(true);
}

function buildTestSelect() {
  const tests = [...new Set(all.map((q) => q.test))].sort();
  $("test").innerHTML = `<option value="">All tests</option>` +
    tests.map((t) => `<option ${t === prefs.test ? "selected" : ""}>${esc(t)}</option>`).join("");
}

function buildTypeSelect() {
  const pool = all.filter((q) => !prefs.test || q.test === prefs.test);
  const bySection = new Map();
  for (const q of pool) {
    const sec = prefs.test ? (q.section || "") : q.test;
    if (!bySection.has(sec)) bySection.set(sec, new Set());
    bySection.get(sec).add(q.type);
  }
  let html = `<option value="">All types</option>`;
  for (const [sec, types] of [...bySection].sort()) {
    const opts = [...types].sort().map((t) => {
      const v = `${sec}|${t}`;
      return `<option value="${esc(v)}" ${v === prefs.type ? "selected" : ""}>${esc(t)}</option>`;
    }).join("");
    html += sec ? `<optgroup label="${esc(sec)}">${opts}</optgroup>` : opts;
  }
  $("type").innerHTML = html;
  if (prefs.type && !$("type").value) prefs.type = "";
}

function matchesFilters(q) {
  if (prefs.test && q.test !== prefs.test) return false;
  if (prefs.verbalOnly && q.verbal === false) return false;
  if (prefs.type) {
    const [sec, type] = prefs.type.split("|");
    const qsec = prefs.test ? (q.section || "") : q.test;
    if (qsec !== sec || q.type !== type) return false;
  }
  return true;
}

function pool() {
  return all.filter(matchesFilters);
}

function candidates() {
  return pool().filter((q) => {
    const p = progress[q.id];
    if (prefs.wrongOnly) return p && p.r === "w";
    return prefs.redo || !p;
  });
}

function refresh(pickNew) {
  renderProgress();
  if (pickNew) next();
}

function renderProgress() {
  const qs = pool();
  let done = 0, c = 0, w = 0, u = 0;
  for (const q of qs) {
    const p = progress[q.id];
    if (!p) continue;
    done++;
    if (p.r === "c") c++; else if (p.r === "w") w++; else u++;
  }
  $("progress").textContent = `${qs.length} questions · ${done} done · ${c} correct · ${w} incorrect · ${u} unchecked`;
}

// Questions seen this visit, so Previous can go back. Each entry keeps its state:
// tries = letters/answers tried, done = answered correctly, shown = answer revealed.
const trail = [];
let pos = -1;

function next() {
  if (pos < trail.length - 1) { pos++; show(trail[pos]); return; }
  const list = candidates().filter((q) => !current || q.id !== current.id || candidates().length === 1);
  if (!list.length) {
    current = null;
    history.replaceState(null, "", location.pathname);
    $("main").className = "split single";
    $("left").innerHTML = "";
    $("right").innerHTML = (prefs.wrongOnly
      ? `<p>No incorrect questions left for this filter.</p>`
      : `<p>You have done every question for this filter.</p><p class="muted">Tick “include done” to see them again.</p>`) +
      (pos > 0 ? `<div class="nav"><button type="button" id="prev">Previous</button></div>` : "");
    if ($("prev")) $("prev").addEventListener("click", previous);
    return;
  }
  visit(list[Math.floor(Math.random() * list.length)]);
}

function previous() {
  if (pos > 0) { pos--; show(trail[pos]); }
}

function visit(q) {
  trail.splice(pos + 1);
  trail.push({ q, tries: [], done: false, shown: false });
  pos = trail.length - 1;
  show(trail[pos]);
}

function showById(id) {
  const q = id && all.find((x) => x.id === id);
  if (q && (!current || current.id !== q.id)) visit(q);
  return !!q;
}

// ---- rendering one question
function show(entry) {
  const q = entry.q;
  current = q;
  history.replaceState(null, "", "#" + q.id);
  const images = q.image ? [].concat(q.image) : [];
  const hasLeft = !!q.passage || images.length > 0;
  $("main").className = hasLeft ? "split" : "split single";
  const lang = q.lang || "en";

  $("left").lang = lang;
  $("left").innerHTML = images.map((src) => `<img src="${esc(src)}" alt="Figure for this question">`).join("") + paras(q.passage);
  $("left").scrollTop = 0;

  const meta = [q.test, q.source, q.section && q.section !== q.type ? q.section : null, q.type].filter(Boolean).join(" · ");
  let html = `<div class="meta">${esc(meta)}</div>`;
  html += `<div class="stem" lang="${lang}">${paras(q.question || "")}</div>`;
  if (q.choices && q.choices.length) {
    html += `<ul class="choices">` + q.choices.map((c, i) =>
      `<li><button type="button" class="choice" data-letter="${LETTERS[i]}" lang="${lang}"><b>${LETTERS[i]}</b><span>${inline(c)}</span></button></li>`
    ).join("") + `</ul>`;
  } else {
    html += `<form class="tita" id="tita"><input type="text" id="titaInput" autocomplete="off" aria-label="Your answer" placeholder="answer"><button type="submit">Check</button></form>`;
  }
  const hasKey = q.answer != null && q.answer !== "";
  html += `<p class="result" id="result"></p>`;
  html += `<div class="nav"><button type="button" id="prev" ${pos > 0 ? "" : "disabled"}>Previous</button>` +
    `<button type="button" id="next">Next</button>` +
    (hasKey ? `<button type="button" id="reveal" hidden>${q.explanation ? "Show explanation" : "Show answer"}</button>` : "") +
    `<button type="button" id="flag" class="link flag"></button></div>`;
  html += `<div id="flagNote" hidden><input type="text" id="flagText" placeholder="What looks wrong? (optional)" aria-label="Flag note"></div>`;
  html += `<div id="more"></div>`;
  $("right").innerHTML = html;
  window.scrollTo(0, 0);

  for (const b of $("right").querySelectorAll(".choice")) b.addEventListener("click", () => answer(b.dataset.letter));
  const form = $("tita");
  if (form) form.addEventListener("submit", (e) => { e.preventDefault(); answer($("titaInput").value); });
  $("prev").addEventListener("click", previous);
  $("next").addEventListener("click", next);
  $("flag").addEventListener("click", () => toggleFlag(q));
  $("flagText").addEventListener("input", () => {
    if (flags[q.id]) { flags[q.id].note = $("flagText").value; save(FLAGS, flags); }
  });
  paintFlag(q);
  if ($("reveal")) $("reveal").addEventListener("click", () => { entry.shown = true; paint(entry); $("next").focus({ preventScroll: true }); });
  paint(entry);
}

function toggleFlag(q) {
  if (flags[q.id]) delete flags[q.id];
  else flags[q.id] = { t: Date.now(), note: "" };
  save(FLAGS, flags);
  paintFlag(q);
  if (flags[q.id]) $("flagText").focus();
}

function paintFlag(q) {
  const f = flags[q.id];
  $("flag").textContent = f ? "flagged (undo)" : "flag";
  $("flag").title = "Mark this question if the answer or text looks wrong";
  $("flagNote").hidden = !f;
  $("flagText").value = f ? f.note : "";
  renderFlagCount();
}

function renderFlagCount() {
  const n = Object.keys(flags).length;
  $("exportFlags").hidden = !n;
  $("exportFlags").textContent = `export flags (${n})`;
}

function exportFlags() {
  const byId = new Map(all.map((q) => [q.id, q]));
  const rows = Object.entries(flags).map(([id, f]) => {
    const q = byId.get(id) || {};
    return { id, test: q.test, source: q.source, note: f.note, flagged: new Date(f.t).toISOString(),
             question: (q.question || "").slice(0, 200), answer: q.answer };
  });
  const url = URL.createObjectURL(new Blob([JSON.stringify(rows, null, 2)], { type: "application/json" }));
  const a = Object.assign(document.createElement("a"), { href: url, download: "flags.json" });
  document.body.append(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
}

function norm(s) {
  return String(s).toUpperCase().replace(/[^A-Z0-9]/g, "");
}

function isRight(q, given) {
  return q.answer != null && q.answer !== "" && norm(given) === norm(q.answer);
}

function answer(given) {
  const entry = trail[pos];
  if (!entry || entry.q !== current || entry.done || entry.shown) return;
  const q = entry.q;
  if (!q.choices?.length && !String(given).trim()) return;
  if (entry.tries.some((t) => norm(t) === norm(given))) return;
  const hasKey = q.answer != null && q.answer !== "";
  if (!entry.tries.length) {  // only the first try counts
    progress[q.id] = { r: hasKey ? (isRight(q, given) ? "c" : "w") : "u", a: given, t: Date.now() };
    save(STORE, progress);
    renderProgress();
  }
  entry.tries.push(given);
  if (!hasKey || isRight(q, given)) entry.done = true;
  paint(entry);
  if (entry.done) $("next").focus({ preventScroll: true });
}

// Draw the entry's state: tried choices, Yes/No, and the answer + explanation once revealed.
function paint(entry) {
  const q = entry.q;
  const hasKey = q.answer != null && q.answer !== "";
  const locked = entry.done || entry.shown;
  for (const b of $("right").querySelectorAll(".choice")) {
    const L = b.dataset.letter;
    const tried = entry.tries.includes(L);
    const correct = hasKey && L === q.answer && (tried || entry.shown);
    b.classList.toggle("picked", tried);
    b.classList.toggle("correct", correct);
    b.disabled = locked || tried;
    b.querySelector(".mark")?.remove();
    const mark = correct ? (tried ? "✓" : "✓ answer") : (tried && hasKey ? "✗" : "");
    if (mark) b.insertAdjacentHTML("beforeend", `<span class="mark">${mark}</span>`);
  }
  const input = $("titaInput");
  if (input) {
    if (entry.tries.length) input.value = entry.tries[entry.tries.length - 1];
    input.disabled = locked;
    if (!locked && entry.tries.length) input.select();
  }
  const last = entry.tries[entry.tries.length - 1];
  let result = "";
  if (entry.tries.length) result = !hasKey ? "Recorded (this source has no answer key)." : isRight(q, last) ? "Yes." : "No.";
  if (entry.shown && !entry.done) result = (result ? result + " " : "") + (q.choices?.length ? "" : `Answer: ${q.answer}`);
  $("result").textContent = result;
  if ($("reveal")) $("reveal").hidden = !entry.tries.length || entry.shown;
  let more = "";
  if (entry.shown || (entry.done && !hasKey)) {
    if (q.note) more += `<p class="note">${esc(q.note)}</p>`;
    if (q.explanation) more += `<div class="explanation" lang="${q.lang || "en"}">${paras(q.explanation)}</div>`;
  }
  $("more").innerHTML = more;
}

function onKey(e) {
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  const t = e.target;
  if (t && (t.tagName === "INPUT" || t.tagName === "SELECT" || t.tagName === "TEXTAREA")) return;
  const k = e.key.toUpperCase();
  if (current?.choices?.length && k.length === 1 && LETTERS.indexOf(k) >= 0 && LETTERS.indexOf(k) < current.choices.length) {
    answer(k);
  } else if (e.key === "ArrowRight" || (e.key === "Enter" && t?.tagName !== "BUTTON")) {
    next();
  } else if (e.key === "ArrowLeft") {
    previous();
  }
}

function resetProgress() {
  if (!confirm("Erase your record of done questions on this device?")) return;
  progress = {};
  save(STORE, progress);
  refresh(true);
}

init().catch((err) => {
  $("right").innerHTML = `<p>Could not load the questions: ${esc(String(err))}</p>`;
});
