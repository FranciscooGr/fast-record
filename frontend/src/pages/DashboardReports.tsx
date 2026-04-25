/**
 * DashboardReports — Financial Reports view.
 *
 * Renders KPI cards, expense analysis, ant-expense impact,
 * and a trends placeholder. Data comes from the SWR-powered
 * useReportsData hook.
 */

import { useParams } from 'react-router-dom';
import {
  TrendingUp,
  TrendingDown,
  PiggyBank,
  CalendarDays,
  BarChart3,
  Bug,
  ArrowUpRight,
  Activity,
} from 'lucide-react';

import { useReportsData } from '../hooks/useReportsData';
import type { CategoriaGasto } from '../hooks/useReportsData';
import Navbar from '../components/Navbar';

/* ═══════════════════════════════════════════════════════════════
   Utility — format numbers as local currency
   ═══════════════════════════════════════════════════════════════ */
function formatCurrency(val: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(val);
}

/* ═══════════════════════════════════════════════════════════════
   Skeleton loader
   ═══════════════════════════════════════════════════════════════ */
function SkeletonCard({ className = '' }: { className?: string }) {
  return (
    <div className={`bg-surface-card rounded-2xl p-6 shadow-card animate-pulse ${className}`}>
      <div className="h-3 w-24 bg-surface-muted rounded mb-4" />
      <div className="h-8 w-36 bg-surface-muted rounded mb-2" />
      <div className="h-3 w-20 bg-surface-muted/60 rounded" />
    </div>
  );
}

function ReportsSkeleton() {
  return (
    <div className="min-h-screen bg-surface font-sans">
      <Navbar />
      <div className="max-w-6xl mx-auto px-5 py-8 space-y-6">
        {/* Header skeleton */}
        <div className="animate-pulse space-y-2">
          <div className="h-7 w-64 bg-surface-muted rounded" />
          <div className="h-4 w-96 bg-surface-muted/60 rounded" />
        </div>

        {/* KPI row */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>

        {/* Analysis grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <SkeletonCard className="lg:col-span-2 h-72" />
          <div className="space-y-4">
            <SkeletonCard className="h-32" />
            <SkeletonCard className="h-32" />
          </div>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Bar chart colors — functional hierarchy
   ═══════════════════════════════════════════════════════════════ */
const BAR_COLORS = [
  'bg-brand-600',
  'bg-chart-2',
  'bg-chart-4',
];

const BAR_BG_COLORS = [
  'bg-brand-100',
  'bg-blue-100',
  'bg-orange-100',
];

/* ═══════════════════════════════════════════════════════════════
   Component
   ═══════════════════════════════════════════════════════════════ */
export default function DashboardReports() {
  const { publicId } = useParams<{ publicId: string }>();

  const { reports, isLoading, isError } = useReportsData(publicId);

  /* ── Loading ─────────────────────────────────────────────── */
  if (isLoading) return <ReportsSkeleton />;

  /* ── Error ───────────────────────────────────────────────── */
  if (isError || !reports) {
    return (
      <div className="min-h-screen bg-surface font-sans">
        <Navbar />
        <div className="flex items-center justify-center p-6 pt-20">
          <div className="text-red-600 bg-red-50 p-5 rounded-2xl font-semibold text-center max-w-sm shadow-card">
            No se pudieron cargar los reportes. Verificá tu conexión e intentá de nuevo.
          </div>
        </div>
      </div>
    );
  }

  /* ── Destructure ─────────────────────────────────────────── */
  const {
    balance_neto,
    tasa_ahorro,
    gasto_promedio_diario,
    top_categorias,
    gastos_hormiga,
    periodo,
  } = reports;

  /* ── Top categories analysis ─────────────────────────────── */
  const categorias = top_categorias.categorias;
  const maxCatTotal = categorias.length > 0
    ? Math.max(...categorias.map((c: CategoriaGasto) => c.total))
    : 0;

  /* ── Balance trend indicator ─────────────────────────────── */
  const balancePositive = balance_neto.balance >= 0;

  /* ═══════════════════════════════════════════════════════════
     Render
     ═══════════════════════════════════════════════════════════ */
  return (
    <div className="min-h-screen bg-surface font-sans pb-16">
      <Navbar />
      <div className="max-w-6xl mx-auto px-5 py-8 space-y-6">

        {/* ══════════════════════════════════════════════════════
           HEADER
           ══════════════════════════════════════════════════════ */}
        <header className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-ink tracking-tight">
              Reportes Financieros
            </h1>
            <p className="text-sm text-ink-muted font-medium mt-1">
              Resumen estadístico de tu actividad reciente
            </p>
          </div>

          <div className="flex items-center gap-3">
            {/* Date range badge */}
            <div className="inline-flex items-center gap-2 bg-surface-card border border-surface-muted rounded-xl px-4 py-2.5 shadow-sm">
              <CalendarDays size={15} className="text-ink-faint" />
              <span className="text-xs font-semibold text-ink-muted">
                {periodo.start_date && periodo.end_date
                  ? `${periodo.start_date} — ${periodo.end_date}`
                  : 'Últimos 30 días'}
              </span>
            </div>

            {/* Export button */}
            {/* <button
              id="btn-export-report"
              className="inline-flex items-center gap-2 bg-brand-600 text-white text-xs font-bold px-4 py-2.5 rounded-xl shadow-md shadow-brand-600/20 hover:bg-brand-700 active:scale-[0.97] transition-all"
            >
              <Download size={14} strokeWidth={2.5} />
              Exportar
            </button>*/}
          </div>
        </header>

        {/* ══════════════════════════════════════════════════════
           KPI CARDS — 3-column grid
           ══════════════════════════════════════════════════════ */}
        <section id="kpi-cards" className="grid grid-cols-1 md:grid-cols-3 gap-4">

          {/* ── Balance Neto ────────────────────────────────── */}
          <div className="bg-surface-card rounded-2xl p-6 shadow-card border border-brand-50/50 relative overflow-hidden group hover:shadow-card-hover transition-shadow">
            <div className="flex items-center gap-2 mb-3">
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${balancePositive
                ? 'bg-brand-50 text-brand-600'
                : 'bg-red-50 text-red-500'
                }`}>
                {balancePositive
                  ? <TrendingUp size={16} strokeWidth={2.5} />
                  : <TrendingDown size={16} strokeWidth={2.5} />
                }
              </div>
              <span className="text-xs font-semibold text-ink-muted uppercase tracking-wider">
                Balance Neto
              </span>
            </div>
            <p className={`text-3xl font-extrabold tracking-tight ${balancePositive ? 'text-brand-700' : 'text-red-600'
              }`}>
              {formatCurrency(balance_neto.balance)}
            </p>
            <div className="flex items-center gap-3 mt-2 text-xs font-medium text-ink-muted">
              <span className="text-brand-600">+{formatCurrency(balance_neto.ingresos_total)}</span>
              <span className="text-red-500">-{formatCurrency(balance_neto.egresos_total)}</span>
            </div>
            {/* Decorative gradient */}
            <div className={`absolute -top-6 -right-6 w-24 h-24 rounded-full opacity-[0.06] ${balancePositive ? 'bg-brand-500' : 'bg-red-500'
              }`} />
          </div>

          {/* ── Tasa de Ahorro ──────────────────────────────── */}
          <div className="bg-surface-card rounded-2xl p-6 shadow-card border border-brand-50/50 relative overflow-hidden group hover:shadow-card-hover transition-shadow">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-8 h-8 rounded-lg bg-brand-50 text-brand-600 flex items-center justify-center">
                <PiggyBank size={16} strokeWidth={2.5} />
              </div>
              <span className="text-xs font-semibold text-ink-muted uppercase tracking-wider">
                Tasa de Ahorro
              </span>
            </div>
            <p className="text-3xl font-extrabold text-ink tracking-tight">
              {tasa_ahorro.tasa_porcentaje.toFixed(1)}
              <span className="text-lg font-bold text-ink-muted ml-0.5">%</span>
            </p>
            <p className="text-xs font-medium text-ink-faint mt-2">
              {tasa_ahorro.tasa_porcentaje >= 20
                ? '¡Buen ritmo de ahorro!'
                : tasa_ahorro.tasa_porcentaje > 0
                  ? 'Podés mejorar tu tasa de ahorro'
                  : 'Sin margen de ahorro en este período'
              }
            </p>
            <div className="absolute -top-6 -right-6 w-24 h-24 rounded-full bg-brand-500 opacity-[0.06]" />
          </div>

          {/* ── Gasto Promedio Diario ───────────────────────── */}
          <div className="bg-surface-card rounded-2xl p-6 shadow-card border border-brand-50/50 relative overflow-hidden group hover:shadow-card-hover transition-shadow">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-8 h-8 rounded-lg bg-orange-50 text-orange-600 flex items-center justify-center">
                <CalendarDays size={16} strokeWidth={2.5} />
              </div>
              <span className="text-xs font-semibold text-ink-muted uppercase tracking-wider">
                Gasto Promedio Diario
              </span>
            </div>
            <p className="text-3xl font-extrabold text-ink tracking-tight">
              {formatCurrency(gasto_promedio_diario.promedio)}
            </p>
            <p className="text-xs font-medium text-ink-faint mt-2">
              Calculado sobre {gasto_promedio_diario.dias_periodo} días
            </p>
            <div className="absolute -top-6 -right-6 w-24 h-24 rounded-full bg-orange-400 opacity-[0.06]" />
          </div>

        </section>

        {/* ══════════════════════════════════════════════════════
           ANALYSIS GRID — asymmetric 2-col (wide + narrow)
           ══════════════════════════════════════════════════════ */}
        <section id="analysis-grid" className="grid grid-cols-1 lg:grid-cols-3 gap-4">

          {/* ── Left: Expense Analysis (wide — 2/3) ────────── */}
          <div className="lg:col-span-2 bg-surface-card rounded-2xl p-6 shadow-card border border-brand-50/50">
            <div className="flex items-center gap-2.5 mb-6">
              <div className="w-9 h-9 bg-brand-50 rounded-xl flex items-center justify-center text-brand-600">
                <BarChart3 size={18} strokeWidth={2.5} />
              </div>
              <div>
                <h2 className="text-lg font-bold text-ink leading-tight">Análisis de Gastos</h2>
                <p className="text-xs font-medium text-ink-muted">Top 3 Categorías de Gasto</p>
              </div>
            </div>

            {categorias.length > 0 ? (
              <div className="space-y-5">
                {categorias.map((cat: CategoriaGasto, idx: number) => {
                  const pct = maxCatTotal > 0
                    ? Math.round((cat.total / maxCatTotal) * 100)
                    : 0;

                  const totalGastos = categorias.reduce((sum: number, c: CategoriaGasto) => sum + c.total, 0);
                  const share = totalGastos > 0
                    ? ((cat.total / totalGastos) * 100).toFixed(1)
                    : '0.0';

                  return (
                    <div key={cat.categoria} className="group">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2.5">
                          <span className="w-6 h-6 rounded-lg bg-surface-muted flex items-center justify-center text-[10px] font-bold text-ink-muted">
                            {idx + 1}
                          </span>
                          <span className="text-sm font-bold text-ink">{cat.categoria}</span>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-xs font-semibold text-ink-muted">{share}%</span>
                          <span className="text-sm font-extrabold text-ink tabular-nums">
                            {formatCurrency(cat.total)}
                          </span>
                        </div>
                      </div>
                      {/* Progress bar */}
                      <div className={`h-3 rounded-full overflow-hidden ${BAR_BG_COLORS[idx % BAR_BG_COLORS.length]}`}>
                        <div
                          className={`h-full rounded-full transition-all duration-700 ease-out ${BAR_COLORS[idx % BAR_COLORS.length]}`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <div className="w-14 h-14 rounded-2xl bg-surface-muted flex items-center justify-center mb-4">
                  <BarChart3 size={24} className="text-ink-faint" />
                </div>
                <p className="text-sm font-semibold text-ink-muted">No hay suficientes datos</p>
                <p className="text-xs text-ink-faint mt-1">Registrá movimientos para ver el análisis</p>
              </div>
            )}
          </div>

          {/* ── Right: Stacked cards (narrow — 1/3) ────────── */}
          <div className="space-y-4">

            {/* — Mayor Crecimiento (design-only placeholder) — */}
            <div className="bg-surface-card rounded-2xl p-5 shadow-card border border-brand-50/50 relative overflow-hidden">
              <span className="text-[10px] font-bold uppercase tracking-widest text-brand-600 mb-3 block">
                Mayor Crecimiento
              </span>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-brand-50 flex items-center justify-center text-brand-600">
                  <ArrowUpRight size={18} strokeWidth={2.5} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-bold text-ink truncate">Ingresos Freelance</p>
                  <p className="text-xs text-ink-faint mt-0.5">Tendencia al alza este mes</p>
                </div>
                <span className="text-sm font-extrabold text-brand-600">+24%</span>
              </div>
              {/* Decorative accent */}
              <div className="absolute -bottom-3 -right-3 w-16 h-16 rounded-full bg-brand-500 opacity-[0.05]" />
            </div>

            {/* — Impacto Gastos Hormiga — */}
            <div className="bg-surface-card rounded-2xl p-5 shadow-card border border-brand-50/50 relative overflow-hidden">
              <span className="text-[10px] font-bold uppercase tracking-widest text-orange-600 mb-3 block">
                Impacto Gastos Hormiga
              </span>

              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-xl bg-orange-50 flex items-center justify-center text-orange-600">
                  <Bug size={18} strokeWidth={2.5} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xl font-extrabold text-ink tracking-tight">
                    {formatCurrency(gastos_hormiga.total)}
                  </p>
                  <p className="text-xs text-ink-faint mt-0.5">
                    {gastos_hormiga.cantidad} transacciones pequeñas (&lt;$5.000)
                  </p>
                </div>
              </div>

              {/* <button
                id="btn-gastos-hormiga-detail"
                className="w-full flex items-center justify-center gap-1.5 text-xs font-bold text-orange-600 bg-orange-50 hover:bg-orange-100 rounded-xl py-2.5 transition-colors active:scale-[0.98]"
              >
                Ver detalle
                <ChevronRight size={14} strokeWidth={2.5} />
              </button>*/}

              <div className="absolute -bottom-3 -right-3 w-16 h-16 rounded-full bg-orange-400 opacity-[0.05]" />
            </div>

          </div>
        </section>

        {/* ══════════════════════════════════════════════════════
           COMPARATIVAS Y TENDENCIAS
           ══════════════════════════════════════════════════════ */}
        <section id="trends-section" className="bg-surface-card rounded-2xl p-6 shadow-card border border-brand-50/50">
          <div className="flex items-center gap-2.5 mb-6">
            <div className="w-9 h-9 bg-brand-50 rounded-xl flex items-center justify-center text-brand-600">
              <Activity size={18} strokeWidth={2.5} />
            </div>
            <div>
              <h2 className="text-lg font-bold text-ink leading-tight">Comparativas y Tendencias</h2>
              <p className="text-xs font-medium text-ink-muted">Evolución mensual de tus finanzas</p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Chart placeholder — wide */}
            <div className="lg:col-span-2 h-56 rounded-xl bg-surface-muted/40 border-2 border-dashed border-surface-muted flex flex-col items-center justify-center">
              <BarChart3 size={32} className="text-ink-faint mb-2" />
              <p className="text-sm font-semibold text-ink-muted">Gráfico en construcción</p>
              <p className="text-xs text-ink-faint mt-1">Próximamente: barras comparativas por mes</p>
            </div>

            {/* Variation card placeholder — narrow */}
            <div className="h-56 rounded-xl bg-surface-muted/40 border-2 border-dashed border-surface-muted flex flex-col items-center justify-center">
              <TrendingUp size={28} className="text-ink-faint mb-2" />
              <p className="text-sm font-semibold text-ink-muted">Variación mensual</p>
              <p className="text-xs text-ink-faint mt-1">Próximamente</p>
            </div>
          </div>
        </section>

      </div>
    </div>
  );
}
