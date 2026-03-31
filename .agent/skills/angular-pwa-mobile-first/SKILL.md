---
name: angular-pwa-mobile-first
description: Use when configuring Angular PWA features, service workers, offline caching, app manifest, or implementing Mobile First responsive design with SCSS. Do not use for chart visualization, routing, or backend communication.
---

# PWA + Mobile First — Frontend Expert

## Use this skill when
- Configurando el service worker (`ngsw-config.json`)
- Habilitando la app para instalación en el home screen
- Implementando caché offline para el dashboard
- Escribiendo SCSS con enfoque Mobile First
- Optimizando para pantallas pequeñas (< 400px primero)

## Habilitar PWA en Angular
```bash
# Agregar soporte PWA al proyecto
ng add @angular/pwa --project frontend
```

## ngsw-config.json — Configuración de caché
```json
{
  "$schema": "./node_modules/@angular/service-worker/config/schema.json",
  "index": "/index.html",
  "assetGroups": [
    {
      "name": "app-shell",
      "installMode": "prefetch",
      "resources": {
        "files": ["/favicon.ico", "/index.html", "/*.css", "/*.js"]
      }
    },
    {
      "name": "assets",
      "installMode": "lazy",
      "updateMode": "prefetch",
      "resources": {
        "files": ["/assets/**"]
      }
    }
  ],
  "dataGroups": [
    {
      "name": "dashboard-api",
      "urls": ["/api/v1/dashboard/**"],
      "cacheConfig": {
        "strategy": "freshness",
        "maxSize": 10,
        "maxAge": "5m",
        "timeout": "3s"
      }
    },
    {
      "name": "transacciones-api",
      "urls": ["/api/v1/transacciones/**"],
      "cacheConfig": {
        "strategy": "freshness",
        "maxSize": 50,
        "maxAge": "1m",
        "timeout": "5s"
      }
    }
  ]
}
```

## manifest.webmanifest — Instalación en home screen
```json
{
  "name": "Fast Record",
  "short_name": "FastRecord",
  "description": "Registro rápido de gastos e ingresos por WhatsApp",
  "theme_color": "#1a1a2e",
  "background_color": "#ffffff",
  "display": "standalone",
  "scope": "/",
  "start_url": "/dashboard",
  "orientation": "portrait",
  "icons": [
    { "src": "assets/icons/icon-72x72.png",   "sizes": "72x72",   "type": "image/png" },
    { "src": "assets/icons/icon-192x192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "assets/icons/icon-512x512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

## Mobile First SCSS — Breakpoints
```scss
// shared/styles/_breakpoints.scss

// Mobile First: escribir estilos base para mobile,
// luego sobrescribir para pantallas más grandes

$breakpoints: (
  'sm': 576px,
  'md': 768px,
  'lg': 992px,
  'xl': 1200px
);

@mixin respond-to($breakpoint) {
  @media (min-width: map-get($breakpoints, $breakpoint)) {
    @content;
  }
}

// USO:
// .card {
//   padding: 12px;         ← mobile (base)
//   @include respond-to('md') {
//     padding: 24px;       ← tablet y desktop
//   }
// }
```

## Componente Mobile First — Ejemplo
```scss
// features/dashboard/dashboard.component.scss

.dashboard {
  display: flex;
  flex-direction: column;    // mobile: columna
  gap: 16px;
  padding: 16px;

  @include respond-to('md') {
    flex-direction: row;     // tablet: fila
    flex-wrap: wrap;
  }

  @include respond-to('lg') {
    padding: 32px;           // desktop: más espacio
  }
}

.card-saldo {
  width: 100%;               // mobile: full width
  border-radius: 12px;
  padding: 20px;
  background: var(--color-primary);

  @include respond-to('md') {
    width: calc(50% - 8px);  // tablet: mitad
  }

  @include respond-to('lg') {
    width: calc(33% - 12px); // desktop: tercio
  }
}
```

## Detectar estado online/offline
```typescript
// core/services/network.service.ts
import { Injectable, signal } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class NetworkService {
  isOnline = signal<boolean>(navigator.onLine);

  constructor() {
    window.addEventListener('online',  () => this.isOnline.set(true));
    window.addEventListener('offline', () => this.isOnline.set(false));
  }
}
```

```html
<!-- Mostrar banner cuando está offline -->
@if (!networkService.isOnline()) {
  <div class="offline-banner">
    📵 Sin conexión — mostrando datos en caché
  </div>
}
```

## Checklist PWA antes de deploy
- [ ] `ngsw-config.json` configurado con rutas de la API
- [ ] `manifest.webmanifest` con iconos en todos los tamaños
- [ ] `index.html` referencia el manifest
- [ ] Todos los estilos escritos Mobile First (base → responsive)
- [ ] Testeado en Chrome DevTools → modo offline
- [ ] Lighthouse PWA score > 90

## Do not
- No escribir estilos desktop-first y luego sobreescribir con `max-width`
- No cachear endpoints de autenticación (JWT)
- No usar `px` fijos para fuentes — usar `rem`
- No olvidar el meta `viewport` en `index.html`
