// Reading Practice: random questions from data/*.json, progress kept in localStorage.
"use strict";

const LETTERS = "ABCDEFGH";
const STORE = "rp-progress-v1";
const PREFS = "rp-prefs-v1";
const $ = (id) => document.getElementById(id);

let all = [];           // every question
let current = null;     // question on screen
let progress = load(STORE, {});   // id -> {r: "c" | "w" | "u", a: answer given, t: time}
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

function next() {
  const list = candidates().filter((q) => !current || q.id !== current.id || candidates().length === 1);
  if (!list.length) {
    current = null;
    history.replaceState(null, "", location.pathname);
    $("main").className = "split single";
    $("left").innerHTML = "";
    $("right").innerHTML = prefs.wrongOnly
      ? `<p>No incorrect questions left for this filter.</p>`
      : `<p>You have done every question for this filter.</p><p class="muted">Tick “include done” to see them again.</p>`;
    return;
  }
  show(list[Math.floor(Math.random() * list.length)]);
}

function showById(id) {
  const q = id && all.find((x) => x.id === id);
  if (q) show(q, true);
  return !!q;
}

// ---- rendering one question
function show(q, fromHash) {
  current = q;
  delete $("right").dataset.answered;
  if (!fromHash) history.replaceState(null, "", "#" + q.id);
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
  html += `<div id="after"></div>`;
  html += `<div class="nav"><button type="button" id="next">Next</button></div>`;
  $("right").innerHTML = html;
  window.scrollTo(0, 0);

  for (const b of $("right").querySelectorAll(".choice")) b.addEventListener("click", () => answer(b.dataset.letter));
  const form = $("tita");
  if (form) form.addEventListener("submit", (e) => { e.preventDefault(); answer($("titaInput").value); });
  $("next").addEventListener("click", next);

  const prev = progress[q.id];
  if (prev && prev.a != null && !prefs.redo && !prefs.wrongOnly) reveal(prev.a, false);
}

function norm(s) {
  return String(s).toUpperCase().replace(/[^A-Z0-9]/g, "");
}

function answer(given) {
  if (!current || $("right").dataset.answered === current.id) return;
  if (!current.choices?.length && !String(given).trim()) return;
  reveal(given, true);
}

function reveal(given, record) {
  const q = current;
  $("right").dataset.answered = q.id;
  const has = q.answer != null && q.answer !== "";
  const ok = has && norm(given) === norm(q.answer);
  if (record) {
    progress[q.id] = { r: has ? (ok ? "c" : "w") : "u", a: given, t: Date.now() };
    save(STORE, progress);
    renderProgress();
  }
  for (const b of $("right").querySelectorAll(".choice")) {
    b.disabled = true;
    const L = b.dataset.letter;
    if (L === given) b.classList.add("picked");
    if (has && L === q.answer) {
      b.classList.add("correct");
      b.insertAdjacentHTML("beforeend", `<span class="mark">✓ answer</span>`);
    } else if (L === given && has) {
      b.insertAdjacentHTML("beforeend", `<span class="mark">✗</span>`);
    }
  }
  const input = $("titaInput");
  if (input) { input.value = given; input.disabled = true; }

  let out = "";
  if (!has) out += `<p class="result">Recorded. This source has no answer key.</p>`;
  else if (ok) out += `<p class="result">Correct.</p>`;
  else out += `<p class="result">Incorrect. The answer is ${esc(q.answer)}.</p>`;
  if (q.note) out += `<p class="note">${esc(q.note)}</p>`;
  if (q.explanation) out += `<div class="explanation" lang="${q.lang || "en"}">${paras(q.explanation)}</div>`;
  $("after").innerHTML = out;
  $("next").focus({ preventScroll: true });
}

function onKey(e) {
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  const t = e.target;
  if (t && (t.tagName === "INPUT" || t.tagName === "SELECT" || t.tagName === "TEXTAREA")) return;
  const k = e.key.toUpperCase();
  if (current?.choices?.length && k.length === 1 && LETTERS.indexOf(k) >= 0 && LETTERS.indexOf(k) < current.choices.length) {
    answer(k);
  } else if (e.key === "Enter" && t?.tagName !== "BUTTON") {
    next();
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
