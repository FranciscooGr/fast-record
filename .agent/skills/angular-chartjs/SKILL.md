---
name: angular-chartjs
description: Use when implementing data visualizations, charts or graphs in Angular using Chart.js. Covers bar charts, line charts, doughnut charts and responsive configurations for the financial dashboard. Do not use for non-chart UI components or backend data fetching.
---

# Chart.js en Angular — Visualización del Dashboard

## Use this skill when
- Implementando gráficos de gastos por categoría (doughnut/bar)
- Mostrando evolución del saldo en el tiempo (line chart)
- Configurando colores, tooltips y responsive para mobile
- Actualizando datos del gráfico dinámicamente con signals

## Instalación
```bash
npm install chart.js
```

## Componente base reutilizable
```typescript
// shared/components/chart/chart.component.ts
import {
  Component, Input, OnInit, OnDestroy,
  ElementRef, ViewChild, OnChanges, SimpleChanges
} from '@angular/core';
import { Chart, ChartConfiguration, ChartType, registerables } from 'chart.js';

Chart.register(...registerables);

@Component({
  selector: 'app-chart',
  standalone: true,
  template: `<canvas #chartCanvas></canvas>`,
  styles: [`canvas { width: 100% !important; }`]
})
export class ChartComponent implements OnInit, OnDestroy, OnChanges {
  @ViewChild('chartCanvas', { static: true }) canvasRef!: ElementRef<HTMLCanvasElement>;
  @Input() type: ChartType = 'doughnut';
  @Input() data: ChartConfiguration['data'] = { labels: [], datasets: [] };
  @Input() options: ChartConfiguration['options'] = {};

  private chart?: Chart;

  ngOnInit() { this.createChart(); }

  ngOnChanges(changes: SimpleChanges) {
    if (changes['data'] && this.chart) {
      this.chart.data = this.data;
      this.chart.update();
    }
  }

  private createChart() {
    this.chart = new Chart(this.canvasRef.nativeElement, {
      type: this.type,
      data: this.data,
      options: { responsive: true, maintainAspectRatio: true, ...this.options }
    });
  }

  ngOnDestroy() { this.chart?.destroy(); }
}
```

## Gráfico de Gastos por Categoría (Doughnut)
```typescript
// features/dashboard/gastos-categoria.component.ts
import { Component, Input, computed } from '@angular/core';
import { ChartComponent } from '@shared/components/chart/chart.component';
import { CategoriaItem } from '@core/models/dashboard.dto';

@Component({
  selector: 'app-gastos-categoria',
  standalone: true,
  imports: [ChartComponent],
  template: `
    <div class="chart-card">
      <h3>Gastos por categoría</h3>
      <app-chart
        type="doughnut"
        [data]="chartData()"
        [options]="chartOptions"
      />
    </div>
  `
})
export class GastosCategoriaComponent {
  @Input() categorias: CategoriaItem[] = [];

  // Signal computado — se actualiza automáticamente
  chartData = computed(() => ({
    labels: this.categorias.map(c => c.categoria),
    datasets: [{
      data: this.categorias.map(c => c.total),
      backgroundColor: [
        '#FF6384', '#36A2EB', '#FFCE56',
        '#4BC0C0', '#9966FF', '#FF9F40'
      ],
      borderWidth: 2,
      borderColor: '#1a1a2e'
    }]
  }));

  chartOptions = {
    plugins: {
      legend: {
        position: 'bottom' as const,
        labels: { color: '#ffffff', padding: 16 }
      },
      tooltip: {
        callbacks: {
          label: (ctx: any) => ` $${ctx.parsed.toLocaleString('es-AR')}`
        }
      }
    }
  };
}
```

## Gráfico de Evolución del Saldo (Line Chart)
```typescript
// features/dashboard/evolucion-saldo.component.ts
import { Component, Input, computed } from '@angular/core';
import { ChartComponent } from '@shared/components/chart/chart.component';

export interface PuntoSaldo {
  fecha: string;
  saldo_acumulado: number;
}

@Component({
  selector: 'app-evolucion-saldo',
  standalone: true,
  imports: [ChartComponent],
  template: `
    <div class="chart-card">
      <h3>Evolución del saldo</h3>
      <app-chart type="line" [data]="chartData()" [options]="chartOptions" />
    </div>
  `
})
export class EvolucionSaldoComponent {
  @Input() puntos: PuntoSaldo[] = [];

  chartData = computed(() => ({
    labels: this.puntos.map(p => p.fecha),
    datasets: [{
      label: 'Saldo',
      data: this.puntos.map(p => p.saldo_acumulado),
      borderColor: '#36A2EB',
      backgroundColor: 'rgba(54, 162, 235, 0.1)',
      fill: true,
      tension: 0.4,
      pointRadius: 4
    }]
  }));

  chartOptions = {
    scales: {
      y: {
        ticks: {
          color: '#ffffff',
          callback: (v: any) => `$${v.toLocaleString('es-AR')}`
        },
        grid: { color: 'rgba(255,255,255,0.1)' }
      },
      x: {
        ticks: { color: '#ffffff' },
        grid: { color: 'rgba(255,255,255,0.05)' }
      }
    },
    plugins: {
      legend: { labels: { color: '#ffffff' } }
    }
  };
}
```

## Gráfico de Ingresos vs Gastos (Bar Chart)
```typescript
chartData = computed(() => ({
  labels: ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun'],
  datasets: [
    {
      label: 'Ingresos',
      data: this.ingresos(),
      backgroundColor: 'rgba(75, 192, 192, 0.8)',
      borderRadius: 6
    },
    {
      label: 'Gastos',
      data: this.gastos(),
      backgroundColor: 'rgba(255, 99, 132, 0.8)',
      borderRadius: 6
    }
  ]
}));
```

## Do not
- No crear instancias de Chart directamente en componentes de feature — usar `ChartComponent`
- No olvidar `chart?.destroy()` en `ngOnDestroy` — causa memory leaks
- No hardcodear datos — siempre vienen del DTO del backend
- No usar `Chart.register()` en múltiples lugares — solo en el componente base
- El saldo mostrado viene del backend, NUNCA calcularlo en el frontend
