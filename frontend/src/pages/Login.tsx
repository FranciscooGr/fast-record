import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { MessageSquare, ShieldAlert } from 'lucide-react';

export default function Login() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  useEffect(() => {
    // 1. Atrapar el token mágico de la URL
    const token = searchParams.get('token');

    // 2. Si hay token, lo guardamos y hacemos redirección limpia
    if (token) {
      localStorage.setItem('token', token);
      navigate('/dashboard', { replace: true });
    }
  }, [searchParams, navigate]);

  return (
    <div className="min-h-screen bg-surface flex flex-col items-center justify-center p-6 sm:p-12 text-center selection:bg-brand-200">

      {/* Icono de advertencia */}
      <div className="w-20 h-20 bg-brand-50 text-brand-600 rounded-full flex items-center justify-center mb-6 shadow-[0_0_40px_rgba(45,138,45,0.15)] ring-4 ring-white">
        <ShieldAlert size={36} strokeWidth={1.5} />
      </div>

      <h1 className="text-3xl font-bold tracking-tight text-ink mb-3">Sesión Requerida</h1>
      <p className="text-ink-muted mb-10 max-w-[280px] leading-relaxed">
        Para mantener tus datos financieros seguros, necesitas un nuevo enlace de acceso.
      </p>

      {/* Tarjeta de instrucciones */}
      <div className="bg-white p-7 rounded-3xl shadow-card w-full max-w-sm border border-brand-50 text-left">
        <p className="text-sm font-semibold text-ink mb-5 uppercase tracking-wide">¿Cómo ingresar?</p>

        <ol className="text-sm text-ink-muted space-y-5 mb-8">
          <li className="flex items-start gap-3">
            <span className="w-6 h-6 rounded-full bg-brand-50 text-brand-600 flex items-center justify-center flex-shrink-0 text-xs font-bold shadow-sm">1</span>
            <span className="leading-snug pt-0.5">Abre tu chat de FastRecord en WhatsApp.</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="w-6 h-6 rounded-full bg-brand-50 text-brand-600 flex items-center justify-center flex-shrink-0 text-xs font-bold shadow-sm">2</span>
            <span className="leading-snug pt-0.5">Escribe la palabra <strong className="text-brand-600 bg-brand-50 px-1.5 py-0.5 rounded-md font-semibold">link</strong>.</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="w-6 h-6 rounded-full bg-brand-50 text-brand-600 flex items-center justify-center flex-shrink-0 text-xs font-bold shadow-sm">3</span>
            <span className="leading-snug pt-0.5">Haz clic en el enlace mágico para continuar.</span>
          </li>
        </ol>

        {/* Enlace estático al bot, reemplazar '1234567890' con el num de WP */}
        <a
          href="https://wa.me/+15551398533"
          target="_blank"
          rel="noopener noreferrer"
          className="w-full bg-brand-600 text-white font-medium py-3.5 px-4 rounded-xl flex items-center justify-center gap-2.5 hover:bg-brand-700 transition duration-200 active:scale-[0.98] shadow-[0_4px_14px_0_rgba(45,138,45,0.39)] hover:shadow-[0_6px_20px_rgba(45,138,45,0.23)]"
        >
          <MessageSquare size={18} strokeWidth={2.5} />
          <span>Ir a WhatsApp</span>
        </a>
      </div>

    </div>
  );
}
