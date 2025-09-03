// Service Worker for Kizuna Dashboard caching
const CACHE_NAME = 'kizuna-dashboard-v1';
const STATIC_CACHE = 'kizuna-static-v1';
const API_CACHE = 'kizuna-api-v1';

const urlsToCache = [
    '/static/css/style.css',
    '/static/css/custom.css',
    '/static/js/script.js',
    '/static/js/dashboard-enhancement.js',
    '/static/js/chart.js'
];

const staticUrlsToCache = [
    '/static/css/',
    '/static/js/',
    '/static/images/'
];

self.addEventListener('install', event => {
    console.log('Service Worker installing...');
    event.waitUntil(
        Promise.all([
            caches.open(CACHE_NAME)
                .then(cache => {
                    console.log('Caching dashboard resources');
                    return cache.addAll(urlsToCache);
                }),
            caches.open(STATIC_CACHE)
                .then(cache => {
                    console.log('Caching static resources');
                    return cache.addAll(staticUrlsToCache);
                })
        ])
    );
});

self.addEventListener('activate', event => {
    console.log('Service Worker activating...');
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== CACHE_NAME && 
                        cacheName !== STATIC_CACHE && 
                        cacheName !== API_CACHE) {
                        console.log('Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
});

self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Handle API requests
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(handleApiRequest(request));
        return;
    }
    
    // Handle static files
    if (url.pathname.startsWith('/static/')) {
        event.respondWith(handleStaticRequest(request));
        return;
    }
    
    // Handle dashboard page
    if (url.pathname === '/' || url.pathname.startsWith('/analytics/')) {
        event.respondWith(handleDashboardRequest(request));
        return;
    }
    
    // Default: network first, fallback to cache
    event.respondWith(
        fetch(request)
            .then(response => {
                // Cache successful responses
                if (response.status === 200) {
                    const responseClone = response.clone();
                    caches.open(CACHE_NAME)
                        .then(cache => cache.put(request, responseClone));
                }
                return response;
            })
            .catch(() => {
                return caches.match(request);
            })
    );
});

async function handleApiRequest(request) {
    const cache = await caches.open(API_CACHE);
    
    try {
        // Try network first for API requests
        const response = await fetch(request);
        
        if (response.status === 200) {
            // Cache successful API responses for 1 minute
            const responseClone = response.clone();
            cache.put(request, responseClone);
        }
        
        return response;
    } catch (error) {
        // Fallback to cached version
        const cachedResponse = await cache.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Return offline response
        return new Response(
            JSON.stringify({ error: 'Offline - No cached data available' }),
            {
                status: 503,
                headers: { 'Content-Type': 'application/json' }
            }
        );
    }
}

async function handleStaticRequest(request) {
    const cache = await caches.open(STATIC_CACHE);
    
    // Cache first for static files
    const cachedResponse = await cache.match(request);
    if (cachedResponse) {
        return cachedResponse;
    }
    
    try {
        const response = await fetch(request);
        if (response.status === 200) {
            const responseClone = response.clone();
            cache.put(request, responseClone);
        }
        return response;
    } catch (error) {
        // Return offline response for static files
        return new Response('Offline', { status: 503 });
    }
}

async function handleDashboardRequest(request) {
    const cache = await caches.open(CACHE_NAME);
    
    try {
        // Network first for dashboard pages
        const response = await fetch(request);
        
        if (response.status === 200) {
            const responseClone = response.clone();
            cache.put(request, responseClone);
        }
        
        return response;
    } catch (error) {
        // Fallback to cached version
        const cachedResponse = await cache.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Return offline page
        return new Response(
            `
            <!DOCTYPE html>
            <html>
            <head>
                <title>Kizuna Analytics - Offline</title>
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                    .offline-message { color: #666; }
                </style>
            </head>
            <body>
                <h1>Kizuna Analytics</h1>
                <div class="offline-message">
                    <p>You are currently offline.</p>
                    <p>Please check your internet connection and try again.</p>
                </div>
            </body>
            </html>
            `,
            {
                status: 200,
                headers: { 'Content-Type': 'text/html' }
            }
        );
    }
}

// Background sync for offline actions
self.addEventListener('sync', event => {
    if (event.tag === 'background-sync') {
        event.waitUntil(doBackgroundSync());
    }
});

async function doBackgroundSync() {
    try {
        // Sync any pending data when connection is restored
        console.log('Performing background sync...');
        
        // You can add specific sync logic here
        // For example, syncing offline form submissions
        
    } catch (error) {
        console.error('Background sync failed:', error);
    }
}

// Push notifications (if needed)
self.addEventListener('push', event => {
    const options = {
        body: event.data ? event.data.text() : 'New update available',
        icon: '/static/images/icon-192x192.png',
        badge: '/static/images/badge-72x72.png',
        vibrate: [100, 50, 100],
        data: {
            dateOfArrival: Date.now(),
            primaryKey: 1
        },
        actions: [
            {
                action: 'explore',
                title: 'View Dashboard',
                icon: '/static/images/checkmark.png'
            },
            {
                action: 'close',
                title: 'Close',
                icon: '/static/images/xmark.png'
            }
        ]
    };
    
    event.waitUntil(
        self.registration.showNotification('Kizuna Analytics', options)
    );
});

self.addEventListener('notificationclick', event => {
    event.notification.close();
    
    if (event.action === 'explore') {
        event.waitUntil(
            clients.openWindow('/')
        );
    }
});
