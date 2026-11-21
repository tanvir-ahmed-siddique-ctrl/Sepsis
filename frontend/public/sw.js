/* Notification-only service worker.
 *
 * Older builds cached HTML + Next.js chunks under auralis-shell-v3. After a
 * Render redeploy that left browsers flashing the previous ICU board (no
 * Advance/Reset) whenever the network was slow, then swapping back once the
 * new bundle loaded. We keep the worker only for SHOW_ALERT push-style
 * messages and wipe every Cache Storage entry on activate.
 */
const CACHE_EPOCH = "auralis-notify-v1";

self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(caches.keys().then((keys) => Promise.all(keys.map((key) => caches.delete(key)))));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE_EPOCH).map((key) => caches.delete(key)))).then(() => self.clients.claim()),
  );
});

// Intentionally no fetch handler: navigations and /_next/* always hit the network.

self.addEventListener("message", (event) => {
  if (event.data?.type !== "SHOW_ALERT") return;
  const { title, body, url, alertId } = event.data;
  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      icon: "/app-icon.png",
      badge: "/app-icon-192.png",
      tag: alertId,
      renotify: false,
      requireInteraction: true,
      data: { url: url || "/app/alerts" },
      actions: [{ action: "open", title: "Open alert queue" }],
    }),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = event.notification.data?.url || "/app/alerts";
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
