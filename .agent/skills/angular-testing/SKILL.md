---
name: angular-testing
description: Use when writing unit tests for Angular components, services or pipes with Jest, or E2E tests with Cypress. Do not use for backend testing, PWA config or chart implementation.
---

# Angular Testing — Frontend Expert

## Use this skill when
- Escribiendo unit tests de componentes con Jest
- Testeando servicios HTTP con mocks
- Escribiendo tests E2E con Cypress para flujos del dashboard
- Verificando que los DTOs se renderizan correctamente en el template

## Setup Jest
```bash
npm install -D jest @jest/globals jest-environment-jsdom \
  @angular-builders/jest ts-jest jest-preset-angular
```

```javascript
// jest.config.js
module.exports = {
  preset: 'jest-preset-angular',
  setupFilesAfterFramework: ['<rootDir>/setup-jest.ts'],
  testEnvironment: 'jsdom',
  moduleNameMapper: {
    '@core/(.*)': '<rootDir>/src/app/core/$1',
    '@shared/(.*)': '<rootDir>/src/app/shared/$1',
    '@features/(.*)': '<rootDir>/src/app/features/$1',
  }
};
```

## Test de Componente — Dashboard
```typescript
// features/dashboard/dashboard.component.spec.ts
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { DashboardComponent } from './dashboard.component';
import { DashboardService } from '@core/services/dashboard.service';
import { DashboardResponse } from '@core/models/dashboard.dto';

const mockDashboard: DashboardResponse = {
  saldo: 750.0,
  total_ingresos: 1000,
  total_gastos: 250,
  gastos_por_categoria: [{ categoria: 'Comida', total: 250 }],
  evolucion_saldo: [],
  ultimas_transacciones: []
};

describe('DashboardComponent', () => {
  let component: DashboardComponent;
  let fixture: ComponentFixture<DashboardComponent>;
  let mockService: jest.Mocked<DashboardService>;

  beforeEach(async () => {
    mockService = {
      getSummary: jest.fn().mockResolvedValue(mockDashboard)
    } as any;

    await TestBed.configureTestingModule({
      imports: [DashboardComponent],
      providers: [{ provide: DashboardService, useValue: mockService }]
    }).compileComponents();

    fixture = TestBed.createComponent(DashboardComponent);
    component = fixture.componentInstance;
  });

  it('debe mostrar el saldo calculado del backend', async () => {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    const saldoEl = fixture.nativeElement.querySelector('[data-testid="saldo"]');
    expect(saldoEl.textContent).toContain('750');
    // El saldo viene del backend, nunca calculado en el frontend
  });

  it('debe mostrar loading mientras carga', () => {
    // No resolver la promesa aún
    mockService.getSummary.mockReturnValue(new Promise(() => {}));
    fixture.detectChanges();

    const loader = fixture.nativeElement.querySelector('[data-testid="loading"]');
    expect(loader).toBeTruthy();
  });

  it('debe mostrar error si el servicio falla', async () => {
    mockService.getSummary.mockRejectedValue(new Error('Network error'));
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    const error = fixture.nativeElement.querySelector('[data-testid="error"]');
    expect(error).toBeTruthy();
  });
});
```

## Test de Servicio HTTP
```typescript
// core/services/dashboard.service.spec.ts
import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { DashboardService } from './dashboard.service';

describe('DashboardService', () => {
  let service: DashboardService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [DashboardService, provideHttpClient(), provideHttpClientTesting()]
    });
    service = TestBed.inject(DashboardService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('debe hacer GET a /api/v1/dashboard/', async () => {
    const promise = service.getSummary();
    const req = httpMock.expectOne('http://localhost:8000/api/v1/dashboard/');
    expect(req.request.method).toBe('GET');
    req.flush({ saldo: 750, total_ingresos: 1000, total_gastos: 250 });
    const result = await promise;
    expect(result.saldo).toBe(750);
  });
});
```

## Tests E2E con Cypress
```typescript
// cypress/e2e/dashboard.cy.ts
describe('Dashboard', () => {
  beforeEach(() => {
    // Interceptar API para no depender del backend real
    cy.intercept('GET', '/api/v1/dashboard/', {
      fixture: 'dashboard.json'
    }).as('getDashboard');

    cy.visit('/dashboard');
    cy.wait('@getDashboard');
  });

  it('muestra el saldo correctamente', () => {
    cy.get('[data-testid="saldo"]').should('contain', '750');
  });

  it('muestra el gráfico de categorías', () => {
    cy.get('app-gastos-categoria canvas').should('exist');
  });

  it('funciona offline (PWA)', () => {
    cy.intercept('GET', '/api/v1/dashboard/', { forceNetworkError: true });
    cy.reload();
    // Debe mostrar datos del caché del service worker
    cy.get('[data-testid="saldo"]').should('exist');
  });
});
```

## Fixtures para Cypress
```json
// cypress/fixtures/dashboard.json
{
  "saldo": 750.00,
  "total_ingresos": 1000.00,
  "total_gastos": 250.00,
  "gastos_por_categoria": [
    { "categoria": "Comida", "total": 150 },
    { "categoria": "Transporte", "total": 100 }
  ],
  "evolucion_saldo": [],
  "ultimas_transacciones": []
}
```

## Atributos data-testid — Convención
```html
<!-- Siempre agregar data-testid para selectores de test -->
<div data-testid="saldo">{{ dashboard()?.saldo | currency:'ARS' }}</div>
<div data-testid="loading" *ngIf="loading()">Cargando...</div>
<div data-testid="error"   *ngIf="error()">{{ error() }}</div>
```

## Do not
- No usar selectores CSS frágiles en tests (`.card > div > span`) — usar `data-testid`
- No hacer llamadas HTTP reales en unit tests — siempre mockear
- No testear implementación interna — testear comportamiento visible
- No olvidar `httpMock.verify()` — verifica que no queden requests sin resolver
