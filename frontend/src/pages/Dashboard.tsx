import { useEffect, useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import {
  LogOut,
  Wallet,
  ShoppingBag,
  Trash2,
  ArrowUpRight,
  ArrowDownRight,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';

/* ═══════════════════════════════════════════════════════════════
   Types
   ═══════════════════════════════════════════════════════════════ */
interface Movement {
  id: number;
  name: string;
  category: string;
  fecha: string;
  amount: number;
  tipo: string;
}

interface CategoryExpense {
  name: string;
  value: number;
  color: string;
}

interface DashboardData {
  saldo_historico_global: number;
  saldo_periodo: number;
  ingresos_totales: number;
  egresos_totales: number;
  movimientos_recientes: Movement[];
  gastos_por_categoria: CategoryExpense[];
  periodo: { start_date: string; end_date: string };
}

type Periodo = 'day' | 'month' | 'year';

/* ═══════════════════════════════════════════════════════════════
   Date helpers (plain JS — no external deps)
   ═══════════════════════════════════════════════════════════════ */

/** Format a Date as YYYY-MM-DD (ISO date only). */
function toISODate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

/** Return [startDate, endDate] for the given period + reference date. */
function getDateRange(periodo: Periodo, ref: Date): [string, string] {
  const year = ref.getFullYear();
  const month = ref.getMonth();
  const day = ref.getDate();

  switch (periodo) {
    case 'day':
      return [toISODate(ref), toISODate(ref)];
    case 'month': {
      const start = new Date(year, month, 1);
      const end = new Date(year, month + 1, 0); // last day of month
      return [toISODate(start), toISODate(end)];
    }
    case 'year': {
      const start = new Date(year, 0, 1);
      const end = new Date(year, 11, 31);
      return [toISODate(start), toISODate(end)];
    }
    default: {
      const start = new Date(year, month, 1);
      const end = new Date(year, month + 1, 0);
      return [toISODate(start), toISODate(end)];
    }
  }
}

/** Shift the reference date by ±1 unit based on the active period. */
function shiftDate(ref: Date, periodo: Periodo, direction: -1 | 1): Date {
  const d = new Date(ref);
  switch (periodo) {
    case 'day':
      d.setDate(d.getDate() + direction);
      break;
    case 'month':
      d.setMonth(d.getMonth() + direction);
      break;
    case 'year':
      d.setFullYear(d.getFullYear() + direction);
      break;
  }
  return d;
}

/** Human-readable label for the current period. */
const MONTHS_ES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
];
const MONTHS_SHORT_ES = [
  'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
  'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic',
];

function getPeriodLabel(periodo: Periodo, ref: Date): string {
  switch (periodo) {
    case 'day':
      return `${ref.getDate()} ${MONTHS_SHORT_ES[ref.getMonth()]} ${ref.getFullYear()}`;
    case 'month':
      return `${MONTHS_ES[ref.getMonth()]} ${ref.getFullYear()}`;
    case 'year':
      return `${ref.getFullYear()}`;
  }
}

/* ═══════════════════════════════════════════════════════════════
   Component
   ═══════════════════════════════════════════════════════════════ */
export default function Dashboard() {
  const navigate = useNavigate();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // ── Period filter state ─────────────────────────────────────
  const [periodo, setPeriodo] = useState<Periodo>('month');
  const [fechaReferencia, setFechaReferencia] = useState<Date>(new Date());

  // ── Fetch dashboard data ────────────────────────────────────
  const fetchDashboard = useCallback(async () => {
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/login', { replace: true });
      return;
    }

    setLoading(true);
    setError(null);

    const [startDate, endDate] = getDateRange(periodo, fechaReferencia);

    try {
      const res = await fetch(
        `http://127.0.0.1:8000/api/v1/dashboard/summary?start_date=${startDate}&end_date=${endDate}`,
        { headers: { Authorization: `Bearer ${token}` } },
      );

      if (res.status === 401) {
        localStorage.removeItem('token');
        navigate('/login', { replace: true });
        return;
      }

      if (!res.ok) throw new Error('Error fetching dashboard data');

      const json = await res.json();
      setData(json);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message || 'Ocurrió un error al cargar.');
      } else {
        setError('Ocurrió un error al cargar.');
      }
    } finally {
      setLoading(false);
    }
  }, [navigate, periodo, fechaReferencia]);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  // ── WebSocket: real-time updates from backend ───────────────
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) return;

    // Decode the JWT payload to get the usuario_id (sub claim)
    let usuarioId: string | null = null;
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      usuarioId = payload.sub;
    } catch {
      return; // malformed token — skip WS
    }
    if (!usuarioId) return;

    const ws = new WebSocket(`ws://127.0.0.1:8000/api/v1/dashboard/ws/${usuarioId}`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      if (event.data === 'update_dashboard') {
        // Silent re-fetch without showing the loading spinner
        fetchDashboard();
      }
    };

    ws.onerror = () => {
      // Non-critical; the dashboard still works via manual refresh
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [fetchDashboard]);

  // ── Handlers ────────────────────────────────────────────────
  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login', { replace: true });
  };

  /** True when the active period already contains today (can't go forward). */
  const isAtPresent = (() => {
    const now = new Date();
    switch (periodo) {
      case 'day':
        return toISODate(fechaReferencia) >= toISODate(now);
      case 'month':
        return (
          fechaReferencia.getFullYear() >= now.getFullYear() &&
          fechaReferencia.getMonth() >= now.getMonth()
        );
      case 'year':
        return fechaReferencia.getFullYear() >= now.getFullYear();
    }
  })();

  const handlePrev = () => setFechaReferencia((prev) => shiftDate(prev, periodo, -1));
  const handleNext = () => {
    if (isAtPresent) return;
    setFechaReferencia((prev) => shiftDate(prev, periodo, 1));
  };

  const handlePeriodoChange = (p: Periodo) => {
    setPeriodo(p);
    setFechaReferencia(new Date()); // reset to today when switching tabs
  };

  const handleResetData = async () => {
    if (!window.confirm('¿ESTÁS SEGURO? Esta acción borrará todo tu historial financiero y no se puede deshacer.')) return;

    const token = localStorage.getItem('token');
    if (!token) return;

    try {
      const res = await fetch('http://127.0.0.1:8000/api/v1/movimientos/reset', {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) throw new Error('Error al resetear la cuenta');

      // Re-fetch the dashboard to reflect the empty state
      fetchDashboard();
    } catch (err) {
      alert('No se pudo resetear la cuenta. Intentá de nuevo.');
    }
  };

  // ── Formatting helpers ──────────────────────────────────────
  const formatCurrency = (val: number) =>
    new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(val);

  const formatTimeAgo = (fechaIso: string) => {
    const date = new Date(fechaIso);
    return date.toLocaleDateString('es-ES', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  /* ── Early returns ─────────────────────────────────────────── */
  if (loading) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center font-sans">
        <div className="w-10 h-10 border-4 border-brand-200 border-t-brand-600 rounded-full animate-spin"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center font-sans p-6 text-center">
        <div className="text-red-600 bg-red-50 p-4 rounded-xl font-medium">{error}</div>
      </div>
    );
  }

  const safeData: DashboardData = data || {
    saldo_historico_global: 0,
    saldo_periodo: 0,
    ingresos_totales: 0,
    egresos_totales: 0,
    gastos_por_categoria: [],
    movimientos_recientes: [],
    periodo: { start_date: '', end_date: '' },
  };

  const { saldo_historico_global, saldo_periodo, gastos_por_categoria, movimientos_recientes } = safeData;

  /* ── Tab config ────────────────────────────────────────────── */
  const TABS: { key: Periodo; label: string }[] = [
    { key: 'day', label: 'Día' },
    { key: 'month', label: 'Mes' },
    { key: 'year', label: 'Año' },
  ];

  /* ═══════════════════════════════════════════════════════════
     Render
     ═══════════════════════════════════════════════════════════ */
  return (
    <div className="min-h-screen bg-surface pb-16 font-sans">

      {/* HEADER */}
      <header className="bg-white px-5 pt-8 pb-6 shadow-[0_4px_24px_rgba(0,0,0,0.02)] sticky top-0 z-20 rounded-b-3xl mb-6">
        <div className="flex justify-between items-center mb-8">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand-600 flex items-center justify-center text-white font-bold text-sm shadow-md">
              <ShoppingBag size={20} strokeWidth={2.5} />
            </div>
            <div>
              <h1 className="font-bold text-ink leading-tight text-lg">Fast Record</h1>
              <p className="text-[10px] uppercase font-bold tracking-widest text-ink-muted">Management</p>
            </div>
          </div>
          <div className="flex items-center gap-4">

            <button
              onClick={handleLogout}
              className="text-ink-muted hover:text-red-600 transition bg-surface-muted p-2.5 rounded-full"
            >
              <LogOut size={18} />
            </button>
          </div>
        </div>

        {/* Balance Section */}
        <div className="bg-surface-muted/50 rounded-2xl p-5 border border-surface-muted">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-7 h-7 bg-brand-100 rounded-lg flex justify-center items-center text-brand-600">
              <Wallet size={14} />
            </div>
            <p className="text-xs font-semibold text-ink-muted uppercase tracking-wider">Balance total</p>
          </div>
          <div className="flex items-end gap-3 px-1">
            <h2 className="text-4xl font-extrabold text-ink tracking-tight">{formatCurrency(saldo_historico_global)}</h2>
          </div>
        </div>
      </header>

      <main className="px-5 space-y-6">

        {/* ══════ PERIOD FILTER ══════════════════════════════════ */}
        <section id="period-filter" className="bg-white rounded-[2rem] p-5 shadow-card border border-brand-50/50">

          {/* Tabs: Día | Mes | Año */}
          <div className="flex rounded-2xl bg-surface-muted p-1.5 gap-1">
            {TABS.map((tab) => (
              <button
                key={tab.key}
                id={`tab-${tab.key}`}
                onClick={() => handlePeriodoChange(tab.key)}
                className={`flex-1 py-3 text-sm font-bold rounded-xl transition-all duration-200
                  ${periodo === tab.key
                    ? 'bg-brand-600 text-white shadow-md shadow-brand-600/30'
                    : 'text-ink-muted hover:text-ink hover:bg-white/60'
                  }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Navigator: < Label > */}
          <div className="flex items-center justify-between mt-4">
            <button
              id="period-prev"
              onClick={handlePrev}
              className="w-12 h-12 rounded-2xl bg-surface-muted flex items-center justify-center text-ink-muted hover:text-ink hover:bg-brand-50 active:scale-95 transition-all"
            >
              <ChevronLeft size={22} strokeWidth={2.5} />
            </button>

            <span className="text-base font-bold text-ink select-none tracking-wide">
              {getPeriodLabel(periodo, fechaReferencia)}
            </span>

            <button
              id="period-next"
              onClick={handleNext}
              disabled={isAtPresent}
              className={`w-12 h-12 rounded-2xl bg-surface-muted flex items-center justify-center transition-all
                ${isAtPresent
                  ? 'text-ink-muted/30 cursor-not-allowed'
                  : 'text-ink-muted hover:text-ink hover:bg-brand-50 active:scale-95'
                }`}
            >
              <ChevronRight size={22} strokeWidth={2.5} />
            </button>
          </div>
        </section>

        {/* ══════ PIE CHART ══════════════════════════════════════ */}
        <section className="bg-white rounded-[2rem] p-6 shadow-card border border-brand-50/50 relative overflow-hidden">
          <div className="flex justify-between items-center mb-2">
            <div>
              <h2 className="text-lg font-bold text-ink">Distribución de gastos</h2>
              <p className="text-xs font-medium text-ink-muted">Por categoría en el período</p>
            </div>
          </div>

          <div className="h-64 relative mt-4">
            {gastos_por_categoria.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={gastos_por_categoria}
                    cx="50%"
                    cy="50%"
                    innerRadius="65%"
                    outerRadius="95%"
                    paddingAngle={3}
                    stroke="none"
                    dataKey="value"
                    cornerRadius={4}
                  >
                    {gastos_por_categoria.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="w-full h-full flex justify-center items-center">
                <div className="w-56 h-56 rounded-full border-[1.25rem] border-surface-muted/40"></div>
              </div>
            )}

            {/* Center label */}
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none mt-1">
              <span className="text-sm font-semibold text-ink-muted text-center leading-tight mb-1">
                Saldo del Período
              </span>
              <span className="text-xl font-extrabold text-ink tracking-tight bg-white px-2 rounded-lg">
                {formatCurrency(saldo_periodo)}
              </span>
            </div>
          </div>

          {/* Legend */}
          <div className="grid grid-cols-2 gap-y-4 gap-x-6 mt-6 pt-6 border-t border-surface-muted/60">
            {gastos_por_categoria.map((item, idx) => (
              <div key={idx} className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-md flex-shrink-0"
                  style={{ backgroundColor: item.color }}
                />
                <div className="flex items-center gap-1.5 truncate">
                  <span className="text-xs text-ink-muted font-medium truncate">{item.name}</span>
                  <span className="text-xs font-bold text-ink truncate">${Math.round(item.value)}</span>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ══════ RECENT ACTIVITY ════════════════════════════════ */}
        <section className="bg-white rounded-[2rem] p-6 shadow-card border border-brand-50/50">
          <div className="flex justify-between items-end mb-6">
            <h2 className="text-lg font-bold text-ink">Actividad Reciente</h2>
            <button className="text-[11px] font-bold text-brand-600 tracking-widest uppercase hover:underline">
              Ver Todos
            </button>
          </div>

          <div className="space-y-5">
            {movimientos_recientes.map((tx) => (
              <div key={tx.id} className="flex items-center justify-between group cursor-pointer">
                <div className="flex items-center gap-4 flex-1">
                  <div className={`w-12 h-12 rounded-2xl flex items-center justify-center transition border ${tx.tipo === 'INGRESO'
                    ? 'bg-brand-50 text-brand-600 border-brand-100'
                    : 'bg-surface text-ink-muted border-transparent group-hover:border-surface-muted'
                    }`}>
                    {tx.tipo === 'INGRESO' ? <ArrowUpRight size={20} className="text-brand-600" /> : <ArrowDownRight size={20} className="text-red-500" />}
                  </div>
                  <div className="flex-1 min-w-0 pr-4">
                    <p className="text-sm font-bold text-ink line-clamp-1 mb-0.5">{tx.name}</p>
                    <p className="text-[11px] font-medium text-ink-muted truncate">{tx.category} • {formatTimeAgo(tx.fecha)}</p>
                  </div>
                </div>
                <span className={`text-sm font-extrabold whitespace-nowrap pl-2 ${tx.tipo === 'INGRESO' ? 'text-brand-600' : 'text-ink'}`}>
                  {tx.tipo === 'INGRESO' ? '+' : '-'}{formatCurrency(Math.abs(tx.amount))}
                </span>
              </div>
            ))}
            {movimientos_recientes.length === 0 && (
              <p className="text-sm text-center text-ink-muted py-4">No hay movimientos en este período.</p>
            )}
          </div>
        </section>

      </main>

      {/* FAB — Reset account */}
      <button
        onClick={handleResetData}
        className="fixed bottom-6 right-6 w-14 h-14 bg-red-500 text-white rounded-2xl shadow-[0_8px_20px_rgba(239,68,68,0.4)] flex items-center justify-center hover:bg-red-600 hover:scale-105 transition-all active:scale-95 z-50"
      >
        <Trash2 size={24} strokeWidth={2.5} />
      </button>

    </div>
  );
}
