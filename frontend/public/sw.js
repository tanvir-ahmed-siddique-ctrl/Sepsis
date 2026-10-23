const CACHE = "predictrx-shell-v2";
const SHELL = ["/", "/chart", "/ward", "/login", "/presentation", "/model", "/readiness"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key)))));
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin || url.pathname.startsWith("/v1/")) return;
  event.respondWith(
    fetch(request)
      .then((response) => {
        if (response.ok) {
          const copy = response.clone();
          void caches.open(CACHE).then((cache) => cache.put(request, copy));
        }
        return response;
      })
      .catch(() => caches.match(request).then((cached) => cached || caches.match("/chart"))),
  );
});

self.addEventListener("message", (event) => {
  if (event.data?.type !== "SHOW_ALERT") return;
  const { title, body, url, alertId } = event.data;
  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      icon: "/app-icon.svg",
      badge: "/app-icon.svg",
      tag: alertId,
      renotify: false,
      requireInteraction: true,
      data: { url: url || "/alerts" },
      actions: [{ action: "open", title: "Open alert queue" }],
    }),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = event.notification.data?.url || "/alerts";
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clients) => {
      const existing = clients.find((client) => "focus" in client);
      if (existing) {
        existing.navigate(url);
        return existing.focus();
      }
      return self.clients.openWindow(url);
    }),
  );
});
