const CACHE_NAME = "retromind-v1";
const SHELL_URLS = ["/", "/capture", "/history", "/settings", "/manifest.json"];
const API_CACHE = "retromind-api-v1";
const DB_NAME = "retromind_offline";
const DB_VERSION = 1;
const STORE_NAME = "pending_captures";

function openDB(): Promise<IDBDatabase> {
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

function getAllCaptures(): Promise<any[]> {
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

function deleteCapture(id: number): Promise<void> {
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

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_URLS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((k) => k !== CACHE_NAME && k !== API_CACHE)
            .map((k) => caches.delete(k))
        )
      )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  if (url.origin === self.location.origin && url.pathname.startsWith("/api/")) {
    return;
  }

  if (request.method !== "GET") return;

  if (
    url.origin === self.location.origin &&
    !url.pathname.startsWith("/_next/")
  ) {
    event.respondWith(
      caches.match(request).then((cached) => cached || fetch(request))
    );
    return;
  }

  event.respondWith(
    caches.open(API_CACHE).then((cache) =>
      fetch(request)
        .then((response) => {
          if (response.ok) cache.put(request, response.clone());
          return response;
        })
        .catch(() => caches.match(request))
    )
  );
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
