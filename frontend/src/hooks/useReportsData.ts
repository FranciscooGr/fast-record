/**
 * useReportsData — SWR-powered hook for the Financial Reports endpoint.
 *
 * Fetches GET /api/v1/users/{publicId}/reports with optional date params.
 * Leverages SWR for automatic request deduplication (client-swr-dedup)
 * and stale-while-revalidate caching.
 */

import useSWR from 'swr';

/* ═══════════════════════════════════════════════════════════════
   Types (matching the backend InformesResponse schema)
   ═══════════════════════════════════════════════════════════════ */

export interface BalanceNeto {
  ingresos_total: number;
  egresos_total: number;
  balance: number;
}

export interface TasaAhorro {
  tasa_porcentaje: number;
}

export interface GastoPromedioDiario {
  promedio: number;
  dias_periodo: number;
}

export interface CategoriaGasto {
  categoria: string;
  total: number;
}

export interface TopCategorias {
  categorias: CategoriaGasto[];
}

export interface GastosHormiga {
  total: number;
  cantidad: number;
  porcentaje_impacto: number;
}

export interface PeriodoInfo {
  start_date: string;
  end_date: string;
}

export interface MayorCrecimiento {
  categoria: string;
  porcentaje: number;
  tendencia: string;
}

export interface ReportsData {
  ok: boolean;
  balance_neto: BalanceNeto;
  tasa_ahorro: TasaAhorro;
  gasto_promedio_diario: GastoPromedioDiario;
  top_categorias: TopCategorias;
  gastos_hormiga: GastosHormiga;
  mayor_crecimiento: MayorCrecimiento | null;
  periodo: PeriodoInfo;
}

/* ═══════════════════════════════════════════════════════════════
   Fetcher
   ═══════════════════════════════════════════════════════════════ */

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

async function fetcher(url: string): Promise<ReportsData> {
  const res = await fetch(url);
  if (!res.ok) {
    const error = new Error('Error al cargar los reportes');
    throw error;
  }
  return res.json();
}

/* ═══════════════════════════════════════════════════════════════
   Hook
   ═══════════════════════════════════════════════════════════════ */

interface UseReportsDataOptions {
  startDate?: string | null;
  endDate?: string | null;
}

export function useReportsData(
  publicId: string | undefined,
  options: UseReportsDataOptions = {},
) {
  const { startDate, endDate } = options;

  // Build URL with optional query params
  const key = publicId
    ? (() => {
        const base = `${API_URL}/api/v1/users/${publicId}/reports`;
        const params = new URLSearchParams();
        if (startDate) params.set('start_date', startDate);
        if (endDate) params.set('end_date', endDate);
        const qs = params.toString();
        return qs ? `${base}?${qs}` : base;
      })()
    : null; // null key → SWR won't fetch

  const { data, error, isLoading, mutate } = useSWR<ReportsData>(key, fetcher, {
    revalidateOnFocus: false,
    dedupingInterval: 5000,
  });

  return {
    reports: data ?? null,
    isLoading,
    isError: !!error,
    error,
    mutate,
  };
}
