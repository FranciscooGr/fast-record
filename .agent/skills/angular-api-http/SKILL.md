---
name: angular-api-http
description: Use when implementing HTTP services to consume the FastAPI backend REST endpoints, defining TypeScript DTOs, handling errors, or configuring HttpClient in Angular. Do not use for chart rendering, PWA config, or component styling.
---

# API HTTP + DTOs — Frontend Expert

## Use this skill when
- Creando servicios que consumen endpoints de `/api/v1/`
- Definiendo interfaces TypeScript (DTOs) para los contratos del backend
- Configurando interceptores de autenticación y errores
- Manejando estados de carga y error en el componente

## Regla fundamental
El frontend NUNCA sabe cómo se almacenan los datos en el backend.
Solo consume DTOs. Si necesitás un nuevo campo, solicitalo al Agente Backend
con el protocolo formal de contratos.

## Configuración de HttpClient (app.config.ts)
```typescript
// app.config.ts
import { ApplicationConfig } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { authInterceptor } from '@core/interceptors/auth.interceptor';
import { errorInterceptor } from '@core/interceptors/error.interceptor';
import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes),
    provideHttpClient(
      withInterceptors([authInterceptor, errorInterceptor])
    )
  ]
};
```

## Servicio base de API
```typescript
// core/services/api.service.ts
import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { environment } from '@environments/environment';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);
  private baseUrl = environment.apiUrl; // http://localhost:8000

  async get<T>(path: string): Promise<T> {
    return firstValueFrom(
      this.http.get<T>(`${this.baseUrl}${path}`)
    );
  }

  async post<T>(path: string, body: unknown): Promise<T> {
    return firstValueFrom(
      this.http.post<T>(`${this.baseUrl}${path}`, body)
    );
  }
}
```

## Servicio del Dashboard
```typescript
// core/services/dashboard.service.ts
import { Injectable, inject } from '@angular/core';
import { ApiService } from './api.service';
import { DashboardResponse } from '@core/models/dashboard.dto';

@Injectable({ providedIn: 'root' })
export class DashboardService {
  private api = inject(ApiService);

  getSummary(): Promise<DashboardResponse> {
    return this.api.get<DashboardResponse>('/api/v1/dashboard/');
  }
}
```

## Error Interceptor
```typescript
// core/interceptors/error.interceptor.ts
import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const router = inject(Router);

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status === 401) {
        router.navigate(['/login']);
      }
      return throwError(() => error);
    })
  );
};
```

## DTOs TypeScript — Contratos con el Backend
```typescript
// core/models/transaccion.dto.ts
// ⚠️ Coordinado con Agente Backend — no modificar sin consenso

export interface TransaccionDTO {
  id: number;
  cuenta_id: number;
  monto: number;
  tipo: 'ingreso' | 'gasto';
  categoria: string;
  descripcion: string;
  proveedor_llm: 'gemini' | 'groq' | 'fallback_otros';
  created_at: string;  // ISO 8601
}

export interface CrearTransaccionDTO {
  monto: number;
  tipo: 'ingreso' | 'gasto';
  descripcion: string;
}

export interface DashboardResponse {
  saldo: number;                          // calculado en backend
  total_ingresos: number;
  total_gastos: number;
  gastos_por_categoria: { categoria: string; total: number }[];
  evolucion_saldo: { fecha: string; saldo_acumulado: number }[];
  ultimas_transacciones: TransaccionDTO[];
}
```

## Uso en componente con signals
```typescript
// features/dashboard/dashboard.component.ts
import { Component, OnInit, inject, signal } from '@angular/core';
import { DashboardService } from '@core/services/dashboard.service';
import { DashboardResponse } from '@core/models/dashboard.dto';

@Component({ standalone: true, ... })
export class DashboardComponent implements OnInit {
  private service = inject(DashboardService);

  data    = signal<DashboardResponse | null>(null);
  loading = signal(false);
  error   = signal<string | null>(null);

  async ngOnInit() {
    this.loading.set(true);
    try {
      this.data.set(await this.service.getSummary());
    } catch {
      this.error.set('No se pudo cargar el dashboard. Intente de nuevo.');
    } finally {
      this.loading.set(false);
    }
  }
}
```

## Environments
```typescript
// environments/environment.ts
export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000'
};

// environments/environment.prod.ts
export const environment = {
  production: true,
  apiUrl: 'https://tu-backend-en-produccion.com'
};
```

## Do not
- No hacer llamadas HTTP directamente desde componentes — siempre via services
- No inventar estructuras de datos — solo usar DTOs acordados con el backend
- No calcular el saldo en el frontend — viene calculado del backend
- No hardcodear URLs — siempre desde `environment.apiUrl`
- No usar `subscribe()` donde `firstValueFrom()` es más claro
