import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import { 
  LogOut, 
  Wallet,
  ShoppingBag,
  Bell,
  Plus,
  ArrowUpRight,
  ArrowDownRight
} from 'lucide-react';

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
  saldo_actual: number;
  ingresos_totales: number;
  egresos_totales: number;
  movimientos_recientes: Movement[];
  gastos_por_categoria: CategoryExpense[];
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/login', { replace: true });
      return;
    }

    const fetchDashboard = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/v1/dashboard/summary', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (res.status === 401) {
          localStorage.removeItem('token');
          navigate('/login', { replace: true });
          return;
        }

        if (!res.ok) throw new Error("Error fetching dashboard data");

        const json = await res.json();
        setData(json);
      } catch (err: unknown) {
        if (err instanceof Error) {
            setError(err.Message || "Ocurrió un error al cargar.");
        } else {
            setError("Ocurrió un error al cargar.");
        }
      } finally {
        setLoading(false);
      }
    };

    fetchDashboard();
  }, [navigate]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login', { replace: true });
  };

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(val);
  };

  // Helper para generar fechas legibles "Hace 2 mins", "Hoy", "Ayer", etc.
  const formatTimeAgo = (fechaIso: string) => {
    const date = new Date(fechaIso);
    return date.toLocaleDateString('es-ES', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  if (loading) {
     return <div className="min-h-screen bg-surface flex items-center justify-center font-sans">
       <div className="w-10 h-10 border-4 border-brand-200 border-t-brand-600 rounded-full animate-spin"></div>
     </div>;
  }

  if (error) {
     return <div className="min-h-screen bg-surface flex items-center justify-center font-sans p-6 text-center">
       <div className="text-red-600 bg-red-50 p-4 rounded-xl font-medium">{error}</div>
     </div>;
  }

  // Fallback si no hay ningún dato
  const safeData = data || {
     saldo_actual: 0,
     ingresos_totales: 0,
     egresos_totales: 0,
     gastos_por_categoria: [],
     movimientos_recientes: []
  };

  const { saldo_actual, gastos_por_categoria, movimientos_recientes } = safeData;

  return (
    <div className="min-h-screen bg-surface pb-16 font-sans">
      
      {/* HEADER (Mobile First) */}
      <header className="bg-white px-5 pt-8 pb-6 shadow-[0_4px_24px_rgba(0,0,0,0.02)] sticky top-0 z-20 rounded-b-3xl mb-6">
        <div className="flex justify-between items-center mb-8">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand-600 flex items-center justify-center text-white font-bold text-sm shadow-md">
              <ShoppingBag size={20} strokeWidth={2.5}/>
            </div>
            <div>
               <h1 className="font-bold text-ink leading-tight text-lg">Fast Record</h1>
               <p className="text-[10px] uppercase font-bold tracking-widest text-ink-muted">Management</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
             <button className="text-ink-muted hover:text-ink transition relative bg-surface-muted p-2.5 rounded-full">
               <Bell size={18} />
             </button>
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
            <p className="text-xs font-semibold text-ink-muted uppercase tracking-wider">Total Balance</p>
          </div>
          <div className="flex items-end gap-3 px-1">
            <h2 className="text-4xl font-extrabold text-ink tracking-tight">{formatCurrency(saldo_actual)}</h2>
          </div>
        </div>
      </header>

      <main className="px-5 space-y-6">
        
        {/* GRÁFICO DONA */}
        <section className="bg-white rounded-[2rem] p-6 shadow-card border border-brand-50/50 relative overflow-hidden">
          <div className="flex justify-between items-center mb-2">
            <div>
              <h2 className="text-lg font-bold text-ink">Expense Distribution</h2>
              <p className="text-xs font-medium text-ink-muted">Historical performance by category</p>
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
                <div className="w-full h-full flex flex-col justify-center items-center rounded-full border-[1.5rem] border-surface-muted">
                </div>
            )}
            
            {/* Etiqueta Central del Gráfico */}
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none mt-1">
              <span className="text-sm font-semibold text-ink-muted text-center leading-tight mb-1">
                Saldo Restante
              </span>
              <span className="text-xl font-extrabold text-ink tracking-tight bg-white px-2 rounded-lg">
                {formatCurrency(saldo_actual)}
              </span>
            </div>
          </div>
          
          {/* Leyenda Dinámica Mobile */}
          <div className="grid grid-cols-2 gap-y-4 gap-x-2 mt-6 pt-6 border-t border-surface-muted/60">
             {gastos_por_categoria.map((item, idx) => (
                 <div key={idx} className="flex items-center gap-2">
                   <div 
                      className="w-3 h-3 rounded-md flex-shrink-0" 
                      style={{ backgroundColor: item.color }}
                   />
                   <span className="text-xs text-ink-muted font-medium truncate flex-1 min-w-0">{item.name}</span>
                   <span className="text-xs text-ink font-bold pl-1">{Math.round(item.value)}</span>
                 </div>
             ))}
             {gastos_por_categoria.length === 0 && (
                <p className="text-center w-full col-span-2 text-sm text-ink-muted">No hay gastos registrados aún.</p>
             )}
          </div>
        </section>


        {/* LISTA DE MOVIMIENTOS DINÁMICA */}
        <section className="bg-white rounded-[2rem] p-6 shadow-card border border-brand-50/50">
          <div className="flex justify-between items-end mb-6">
            <h2 className="text-lg font-bold text-ink">Recent Activity</h2>
            <button className="text-[11px] font-bold text-brand-600 tracking-widest uppercase hover:underline">
              View All
            </button>
          </div>
          
          <div className="space-y-5">
             {movimientos_recientes.map((tx) => (
                 <div key={tx.id} className="flex items-center justify-between group cursor-pointer">
                   <div className="flex items-center gap-4 flex-1">
                     <div className={`w-12 h-12 rounded-2xl flex items-center justify-center transition border ${
                         tx.tipo === 'INGRESO' 
                           ? 'bg-brand-50 text-brand-600 border-brand-100' 
                           : 'bg-surface text-ink-muted border-transparent group-hover:border-surface-muted'
                     }`}>
                       {tx.tipo === 'INGRESO' ? <ArrowUpRight size={20} className="text-brand-600"/> : <ArrowDownRight size={20} className="text-red-500" />}
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
                <p className="text-sm text-center text-ink-muted py-4">No hay movimientos recientes.</p>
             )}
          </div>
        </section>

      </main>

      {/* Floating Action Button (FAB) */}
      <button className="fixed bottom-6 right-6 w-14 h-14 bg-brand-600 text-white rounded-2xl shadow-[0_8px_20px_rgba(45,138,45,0.4)] flex items-center justify-center hover:bg-brand-700 hover:scale-105 transition-all active:scale-95 z-50">
         <Plus size={24} strokeWidth={2.5}/>
      </button>

    </div>
  );
}
