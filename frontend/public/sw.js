const CACHE_NAME = "retromind-v2";
const API_CACHE = "retromind-api-v2";
const DB_NAME = "retromind_offline";
const DB_VERSION = 1;
const STORE_NAME = "pending_captures";

function openDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: "id", autoIncrement: true });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function getAllCaptures() {
  return openDB().then(
    (db) =>
      new Promise((resolve, reject) => {
        const tx = db.transaction(STORE_NAME, "readonly");
        const req = tx.objectStore(STORE_NAME).getAll();
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
      })
  );
}

function deleteCapture(id) {
  return openDB().then(
    (db) =>
      new Promise((resolve, reject) => {
        const tx = db.transaction(STORE_NAME, "readwrite");
        const req = tx.objectStore(STORE_NAME).delete(id);
        req.onsuccess = () => resolve();
        req.onerror = () => reject(req.error);
      })
  );
}

self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Never cache HTML documents — always go to network
  if (request.mode === "navigate") return;

  // Never cache Next.js RSC payloads
  if (url.searchParams.has("__next_f")) return;

  // Skip non-GET and API calls
  if (request.method !== "GET") return;
  if (url.origin === self.location.origin && url.pathname.startsWith("/api/")) return;

  // Cache static assets (JS, CSS, fonts, images from _next/)
  if (url.pathname.startsWith("/_next/") || url.pathname.startsWith("/__nextjs_font/")) {
    event.respondWith(
      caches.open(CACHE_NAME).then((cache) =>
        fetch(request)
          .then((response) => {
            if (response.ok) cache.put(request, response.clone());
            return response;
          })
          .catch(() => caches.match(request))
      )
    );
    return;
  }
});

self.addEventListener("sync", (event) => {
  if (event.tag === "sync-captures") {
    event.waitUntil(syncCaptures());
  }
});

async function syncCaptures() {
  try {
    const pending = await getAllCaptures();
    for (const capture of pending) {
      try {
        const fd = new FormData();
        fd.append("workshop_id", "demo-workshop");
        fd.append(capture.slotKey, capture.blob, `${capture.slotKey}.jpg`);

        const res = await fetch("http://localhost:8000/api/v1/intake", {
          method: "POST",
          body: fd,
        });

        if (res.ok) {
          await deleteCapture(capture.id);
        }
      } catch {
        /* retry later */
      }
    }
  } catch {
    /* sw */
  }
}

self.addEventListener("message", (event) => {
  if (event.data === "sync-now") {
    self.registration.sync.register("sync-captures");
  }
});
