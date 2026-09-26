// Reading Practice: random questions from data/*.json, progress kept in localStorage.
"use strict";

const LETTERS = "ABCDEFGH";
const STORE = "rp-progress-v1";
const PREFS = "rp-prefs-v1";
const FLAGS = "rp-flags-v1";
const STARS = "rp-stars-v1";
const HISTORY = "rp-history-v1";
const HISTORY_MAX = 200;
const $ = (id) => document.getElementById(id);

let all = [];           // every question
let current = null;     // question on screen
let progress = load(STORE, {});   // id -> {r: "c" | "w" | "u", a: answer given, t: time}
let flags = load(FLAGS, {});      // id -> {t: time, note: text}: questions the owner thinks are wrong
let stars = load(STARS, {});      // id -> time starred
let seen = load(HISTORY, []);     // [{id, t}], newest first: questions shown, across visits
let prefs = load(PREFS, { test: "", type: "", verbalOnly: false, redo: false, wrongOnly: false, starredOnly: false });
let listView = null;              // "recent" or "starred" while the history page is open

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
  for (const id of ["verbalOnly", "redo", "wrongOnly", "starredOnly"]) {
    $(id).checked = !!prefs[id];
    $(id).addEventListener("change", () => { prefs[id] = $(id).checked; save(PREFS, prefs); refresh(true); });
  }
  $("test").addEventListener("change", () => { prefs.test = $("test").value; prefs.type = ""; save(PREFS, prefs); buildTypeSelect(); refresh(true); });
  $("type").addEventListener("change", () => { prefs.type = $("type").value; save(PREFS, prefs); refresh(true); });
  $("reset").addEventListener("click", resetProgress);
  $("exportFlags").addEventListener("click", exportFlags);
  $("historyLink").addEventListener("click", () => showList("recent"));
  renderFlagCount();
  document.addEventListener("keydown", onKey);
  // #<id> opens that question; the address bar is then cleared so a bookmark or home-screen icon
  // saved later is the plain site, not the question that happened to be open.
  window.addEventListener("hashchange", () => { showById(location.hash.slice(1)); clearHash(); });
  buildTypeSelect();
  renderProgress();
  if (!showById(location.hash.slice(1))) refresh(true);
  clearHash();
  offline();
}

function clearHash() {
  if (location.hash) history.replaceState(null, "", location.pathname + location.search);
}

// Offline copy of the site (sw.js). The footer says so once every file is cached.
function offline() {
  if (!("serviceWorker" in navigator)) return;
  navigator.serviceWorker.addEventListener("message", (e) => {
    if (e.data?.offline) $("offline").textContent = "available offline";
  });
  navigator.serviceWorker.register("sw.js")
    .then(() => navigator.serviceWorker.ready)
    .then((reg) => reg.active.postMessage("precache"))
    .catch(() => {});
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
  if (prefs.starredOnly && !stars[q.id]) return false;
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
    return prefs.redo || prefs.starredOnly || !p;
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
    listView = null;
    $("main").className = "split single";
    $("left").innerHTML = "";
    $("right").innerHTML = (prefs.wrongOnly ? `<p>No incorrect questions left for this filter.</p>`
      : prefs.starredOnly ? `<p>No starred questions for this filter.</p>`
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
  seen = [{ id: q.id, t: Date.now() }, ...seen.filter((h) => h.id !== q.id)].slice(0, HISTORY_MAX);
  save(HISTORY, seen);
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
  listView = null;
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
    `<span class="marks"><button type="button" id="star" class="link"></button>` +
    `<button type="button" id="flag" class="link"></button></span></div>`;
  html += `<div id="flagNote" hidden><input type="text" id="flagText" placeholder="What looks wrong? (optional)" aria-label="Flag note"></div>`;
  html += `<div id="more"></div>`;
  $("right").innerHTML = html;
  $("right").scrollTop = 0;
  $("main").scrollTop = 0;

  for (const b of $("right").querySelectorAll(".choice")) b.addEventListener("click", () => answer(b.dataset.letter));
  const form = $("tita");
  if (form) form.addEventListener("submit", (e) => { e.preventDefault(); answer($("titaInput").value); });
  $("prev").addEventListener("click", previous);
  $("next").addEventListener("click", next);
  $("star").addEventListener("click", () => toggleStar(q));
  $("flag").addEventListener("click", () => toggleFlag(q));
  $("flagText").addEventListener("input", () => {
    if (flags[q.id]) { flags[q.id].note = $("flagText").value; save(FLAGS, flags); }
  });
  paintStar(q);
  paintFlag(q);
  if ($("reveal")) $("reveal").addEventListener("click", () => { entry.shown = true; paint(entry); $("next").focus({ preventScroll: true }); });
  paint(entry);
}

function toggleStar(q) {
  if (stars[q.id]) delete stars[q.id];
  else stars[q.id] = Date.now();
  save(STARS, stars);
  paintStar(q);
  if (prefs.starredOnly) renderProgress();
}

function paintStar(q) {
  $("star").textContent = stars[q.id] ? "starred" : "star";
  $("star").title = stars[q.id] ? "Remove the star" : "Keep this question in your starred list";
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

// ---- history page: recently seen questions, or every starred one
function showList(which) {
  listView = which;
  const byId = new Map(all.map((q) => [q.id, q]));
  const rows = which === "recent"
    ? seen.map((h) => ({ q: byId.get(h.id), t: h.t }))
    : Object.entries(stars).sort((a, b) => b[1] - a[1]).map(([id, t]) => ({ q: byId.get(id), t }));
  const plain = (s) => (s || "").replace(/\*\*|\+\+|\*/g, "").replace(/\s+/g, " ").trim();
  const when = (t) => new Date(t).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  const result = (id) => {
    const p = progress[id];
    return !p ? "not answered" : p.r === "c" ? "correct" : p.r === "w" ? "incorrect" : "unchecked";
  };
  const items = rows.filter((r) => r.q).map(({ q, t }) => {
    const info = [when(t), q.test, q.type, result(q.id), which === "recent" && stars[q.id] ? "starred" : null].filter(Boolean).join(" · ");
    return `<li><button type="button" data-id="${esc(q.id)}"><span class="row">${esc(info)}</span>` +
      `<span class="ex" lang="${q.lang || "en"}">${esc(plain(q.question).slice(0, 200))}</span>` +
      (q.passage ? `<span class="ex passage" lang="${q.lang || "en"}">${esc(plain(q.passage).slice(0, 200))}</span>` : "") +
      `</button></li>`;
  });
  $("main").className = "split single";
  $("left").innerHTML = "";
  $("right").innerHTML =
    `<div class="list-head"><h2>History</h2>` +
    `<button type="button" class="link ${which === "recent" ? "on" : ""}" id="listRecent">recent</button>` +
    `<button type="button" class="link ${which === "starred" ? "on" : ""}" id="listStarred">starred (${Object.keys(stars).length})</button>` +
    `<button type="button" class="link back" id="listBack">back</button></div>` +
    (items.length ? `<ul class="list">${items.join("")}</ul>`
      : `<p class="muted">${which === "recent" ? "No questions seen yet." : "No starred questions yet."}</p>`);
  $("right").scrollTop = 0;
  $("main").scrollTop = 0;
  $("listRecent").addEventListener("click", () => showList("recent"));
  $("listStarred").addEventListener("click", () => showList("starred"));
  $("listBack").addEventListener("click", closeList);
  for (const b of $("right").querySelectorAll(".list button")) b.addEventListener("click", () => visit(byId.get(b.dataset.id)));
}

function closeList() {
  if (pos >= 0) show(trail[pos]); else next();
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
  if (listView) {
    if (e.key === "Escape") closeList();
    return;
  }
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
