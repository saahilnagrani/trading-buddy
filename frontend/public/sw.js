// Service Worker for Trading Buddy PWA
// Handles push notifications

self.addEventListener("push", (event) => {
  if (!event.data) return;

  try {
    const data = event.data.json();
    const options = {
      body: data.body || "",
      icon: "/icons/icon-192.png",
      badge: "/icons/icon-192.png",
      tag: data.type || "default",
      data: {
        notification_id: data.notification_id,
        type: data.type,
      },
    };

    event.waitUntil(self.registration.showNotification(data.title, options));
  } catch {
    // Fallback for plain text
    event.waitUntil(
      self.registration.showNotification("Trading Buddy", {
        body: event.data.text(),
        icon: "/icons/icon-192.png",
      })
    );
  }
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  const type = event.notification.data?.type;
  let url = "/";
  if (type === "ORDER_FILL" || type === "ORDER_REJECT") {
    url = "/orders";
  } else if (type === "MARGIN_ALERT") {
    url = "/portfolio";
  } else if (type === "TOKEN_EXPIRY") {
    url = "/login";
  }

  event.waitUntil(
    clients.matchAll({ type: "window" }).then((windowClients) => {
      for (const client of windowClients) {
        if (client.url.includes(self.location.origin)) {
          client.navigate(url);
          return client.focus();
        }
      }
      return clients.openWindow(url);
    })
  );
});

// Basic cache for offline shell
const CACHE_NAME = "trading-buddy-v1";

self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(clients.claim());
});
