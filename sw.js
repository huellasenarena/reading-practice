// Offline support: keep a copy of the whole site (pages, data, images) in the browser's cache.
// Requests go to the network first, so updates arrive whenever the device is online;
// the cached copy answers when the network fails or is too slow.
"use strict";

const CACHE = "rp-site";
const SHELL = ["./", "index.html", "style.css", "app.js", "manifest.webmanifest",
               "icons/icon-180.png", "icons/icon-192.png", "icons/icon-512.png", "data/index.json"];
const TIMEOUT = 4000;

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET" || new URL(req.url).origin !== location.origin) return;
  e.respondWith(fromNetwork(req).catch(() => fromCache(req)));
});

async function fromNetwork(req) {
  const res = await Promise.race([
    fetch(req),
    new Promise((_, reject) => setTimeout(() => reject(new Error("timeout")), TIMEOUT)),
  ]);
  if (!res.ok) throw new Error(res.status);
  const copy = res.clone();
  caches.open(CACHE).then((c) => c.put(req.mode === "navigate" ? "./" : req, copy));
  return res;
}

async function fromCache(req) {
  const hit = await caches.match(req.mode === "navigate" ? "./" : req, { ignoreSearch: true });
  if (hit) return hit;
  return fetch(req);  // not cached yet: let the real error through
}

// The page asks for this on every load: download whatever data files and images are not cached
// yet, then report back so the footer can say the site is available offline.
self.addEventListener("message", (e) => {
  if (e.data === "precache") e.waitUntil(precache(e.source).catch(() => {}));  // offline: try again next load
});

async function precache(client) {
  const c = await caches.open(CACHE);
  const files = await (await fetch("data/index.json")).json();
  const urls = [...SHELL];
  for (const f of files) {
    const url = `data/${f}.json`;
    urls.push(url);
    const questions = await (await (await c.match(url)) || await fetch(url)).json();
    for (const q of questions) if (q.image) urls.push(...[].concat(q.image));
  }
  const missing = [];
  for (const url of new Set(urls)) if (!(await c.match(url))) missing.push(url);
  for (let i = 0; i < missing.length; i += 20) await c.addAll(missing.slice(i, i + 20));
  client.postMessage({ offline: true });
}
