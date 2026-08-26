self.addEventListener("push", (event) => {
    let payload = {};
    try {
        payload = event.data ? event.data.json() : {};
    } catch (error) {
        payload = {
            title: "Nouveau message Pro Consulting",
            body: event.data ? event.data.text() : "Ouvrez le chat collectif.",
        };
    }

    const notificationTitle = payload.title || "Nouveau message Pro Consulting";
    const notificationOptions = {
        body: payload.body || "Ouvrez le chat collectif.",
        data: {
            url: payload.url || "/?page=chat",
        },
        tag: payload.tag || "pro-consulting-chat",
        renotify: true,
        vibrate: [180, 80, 180],
    };

    event.waitUntil(
        self.registration.showNotification(
            notificationTitle,
            notificationOptions,
        ),
    );
});

self.addEventListener("notificationclick", (event) => {
    event.notification.close();
    const targetUrl = new URL(
        event.notification.data?.url || "/?page=chat",
        self.location.origin,
    ).href;

    event.waitUntil(
        self.clients
            .matchAll({ type: "window", includeUncontrolled: true })
            .then(async (clientList) => {
                for (const client of clientList) {
                    if ("navigate" in client) {
                        await client.navigate(targetUrl);
                    }
                    if ("focus" in client) {
                        return client.focus();
                    }
                }
                if (self.clients.openWindow) {
                    return self.clients.openWindow(targetUrl);
                }
                return undefined;
            }),
    );
});
