---
name: angular-architecture
description: Use when scaffolding new Angular components, services, modules, routes or project structure in ./frontend. Expert in standalone components, signals, lazy loading and Angular best practices. Do not use for backend, styling, charts or PWA configuration.
---

# Angular Architecture — Frontend Expert

## Use this skill when
- Creando nuevos componentes, servicios o directivas
- Configurando rutas y lazy loading
- Estructurando módulos por feature
- Implementando guards de autenticación
- Definiendo DTOs TypeScript para consumir la API del backend

## Estructura de carpetas estricta
```
./frontend/src/app/
├── core/                        → singleton services, guards, interceptors
│   ├── services/
│   │   ├── auth.service.ts
│   │   └── api.service.ts       → HttpClient base
│   ├── interceptors/
│   │   ├── auth.interceptor.ts  → agrega JWT a cada request
│   │   └── error.interceptor.ts → manejo global de errores HTTP
│   ├── guards/
│   │   └── auth.guard.ts
│   └── models/                  → DTOs TypeScript (contratos con backend)
│       ├── transaccion.dto.ts
│       └── dashboard.dto.ts
├── shared/                      → componentes, pipes, directivas reutilizables
│   ├── components/
│   ├── pipes/
│   └── directives/
├── features/                    → módulos lazy loaded por feature
│   ├── dashboard/
│   │   ├── dashboard.component.ts
│   │   ├── dashboard.component.html
│   │   ├── dashboard.component.scss
│   │   └── dashboard.routes.ts
│   └── transacciones/
│       ├── transacciones.component.ts
│       └── transacciones.routes.ts
├── layout/
│   ├── navbar/
│   └── sidebar/
└── app.routes.ts                → rutas principales con lazy loading
```

## Standalone Component — Pattern base
```typescript
// features/dashboard/dashboard.component.ts
import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DashboardService } from '@core/services/dashboard.service';
import { DashboardResponse } from '@core/models/dashboard.dto';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss'
})
export class DashboardComponent implements OnInit {
  private dashboardService = inject(DashboardService);

  // Signals — estado reactivo moderno
  dashboard = signal<DashboardResponse | null>(null);
  loading = signal<boolean>(false);
  error = signal<string | null>(null);

  async ngOnInit() {
    this.loading.set(true);
    try {
      const data = await this.dashboardService.getSummary();
      this.dashboard.set(data);
    } catch (e) {
      this.error.set('Error al cargar el dashboard');
    } finally {
      this.loading.set(false);
    }
  }
}
```

## DTOs TypeScript — Contratos con el Backend
```typescript
// core/models/dashboard.dto.ts
// NUNCA modificar sin coordinar con el Agente Backend

export interface TransaccionDTO {
  id: number;
  monto: number;
  tipo: 'ingreso' | 'gasto';
  categoria: string;
  descripcion: string;
  created_at: string;
}

export interface DashboardResponse {
  saldo: number;                           // calculado en backend, nunca local
  total_ingresos: number;
  total_gastos: number;
  gastos_por_categoria: CategoriaItem[];  // para Chart.js
  ultimas_transacciones: TransaccionDTO[];
}

export interface CategoriaItem {
  categoria: string;
  total: number;
}
```

## Rutas con Lazy Loading
```typescript
// app.routes.ts
import { Routes } from '@angular/router';
import { authGuard } from '@core/guards/auth.guard';

export const routes: Routes = [
  {
    path: 'dashboard',
    loadComponent: () =>
      import('./features/dashboard/dashboard.component')
        .then(m => m.DashboardComponent),
    canActivate: [authGuard]
  },
  {
    path: 'transacciones',
    loadComponent: () =>
      import('./features/transacciones/transacciones.component')
        .then(m => m.TransaccionesComponent),
    canActivate: [authGuard]
  },
  { path: '', redirectTo: 'dashboard', pathMatch: 'full' }
];
```

## Auth Interceptor — JWT automático
```typescript
// core/interceptors/auth.interceptor.ts
import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { AuthService } from '@core/services/auth.service';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);
  const token = authService.getToken();

  if (token) {
    req = req.clone({
      setHeaders: { Authorization: `Bearer ${token}` }
    });
  }
  return next(req);
};
```

## Path Aliases — tsconfig.json
```json
{
  "compilerOptions": {
    "paths": {
      "@core/*": ["src/app/core/*"],
      "@shared/*": ["src/app/shared/*"],
      "@features/*": ["src/app/features/*"]
    }
  }
}
```

## Do not
- No poner lógica de negocio en los componentes — va en services
- No asumir estructura de la DB — solo consumir DTOs del backend
- No modificar DTOs sin coordinar con el Agente Backend
- No usar `NgModules` clásicos — usar standalone components
- No tocar nada fuera de `./frontend`
