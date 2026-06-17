const CACHE = 'xfei-chef-v1'
const ASSETS = ['/', '/index.html', '/manifest.json', '/icon.svg']

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(ASSETS))
  )
})

self.addEventListener('fetch', (e) => {
  if (e.request.url.startsWith(self.location.origin) && !e.request.url.includes('/api/')) {
    e.respondWith(
      caches.open(CACHE).then((c) =>
        c.match(e.request).then((r) => r || fetch(e.request))
      )
    )
  }
})
