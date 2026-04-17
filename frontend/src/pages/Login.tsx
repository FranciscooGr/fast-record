import { MessageSquare, ShieldAlert } from 'lucide-react';

export default function Login() {
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
            <span className="leading-snug pt-0.5">Registrá un movimiento, por ejemplo: <strong className="text-brand-600 bg-brand-50 px-1.5 py-0.5 rounded-md font-semibold">cobré 5000 de sueldo</strong>.</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="w-6 h-6 rounded-full bg-brand-50 text-brand-600 flex items-center justify-center flex-shrink-0 text-xs font-bold shadow-sm">3</span>
            <span className="leading-snug pt-0.5">Hacé clic en el enlace del panel que te envía el bot.</span>
          </li>
        </ol>


        <a
          href="https://wa.me/+15055816239"
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
