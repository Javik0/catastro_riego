import { useState, useEffect } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { LOGO_PICHINCHA, LOGO_CONSORCIO, PROJECT_TITLE } from '../../lib/constants';
import { LogIn, Mail, Lock, AlertCircle, Loader2, Droplets, Shield } from 'lucide-react';

export default function LoginPage() {
  const { login, loading, sessionExpired } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  // Se muestran en blanco hasta que llegan los de verdad: unos valores por
  // defecto del arranque del proyecto (777 fichas, 640 predios) se quedaron
  // meses en pantalla y no se distinguían de los reales.
  const [stats, setStats] = useState({ fichas: '—', predios: '—', tecnicos: '—' });

  useEffect(() => {
    fetch(`/geo/stats.json?t=${Date.now()}`)
      .then((r) => r.json())
      .then((data) => {
        if (data && data.fichas && data.predios && data.tecnicos) {
          setStats({
            // sin «+»: son cifras exactas del último corte, no un mínimo
            fichas: Number(data.fichas).toLocaleString('es-EC'),
            predios: Number(data.predios).toLocaleString('es-EC'),
            tecnicos: String(data.tecnicos),
          });
        }
      })
      .catch(() => {});
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      await login(email, password);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al iniciar sesión');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex" style={{ background: '#060d1b' }}>

      {/* ══ LEFT PANEL — Brand Visual ══ */}
      <div className="hidden lg:flex lg:w-[55%] relative overflow-hidden items-center justify-center"
        style={{ background: 'linear-gradient(135deg, #0a1628 0%, #0f2847 40%, #0d3a5c 100%)' }}>

        {/* Animated background circles */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute w-[500px] h-[500px] rounded-full opacity-[0.04] animate-pulse"
            style={{ top: '-10%', right: '-10%', background: 'radial-gradient(circle, #38bdf8, transparent 70%)' }} />
          <div className="absolute w-[400px] h-[400px] rounded-full opacity-[0.05]"
            style={{ bottom: '-15%', left: '-8%', background: 'radial-gradient(circle, #10b981, transparent 70%)', animation: 'pulse 4s ease-in-out infinite' }} />
          <div className="absolute w-[300px] h-[300px] rounded-full opacity-[0.03]"
            style={{ top: '40%', left: '50%', background: 'radial-gradient(circle, #f59e0b, transparent 70%)', animation: 'pulse 6s ease-in-out infinite' }} />

          {/* Grid pattern */}
          <div className="absolute inset-0 opacity-[0.03]"
            style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)', backgroundSize: '60px 60px' }} />

          {/* Diagonal lines */}
          <div className="absolute inset-0 opacity-[0.02]"
            style={{ backgroundImage: 'repeating-linear-gradient(-45deg, transparent, transparent 80px, rgba(56,189,248,0.3) 80px, rgba(56,189,248,0.3) 81px)' }} />
        </div>

        {/* Content */}
        <div className="relative z-10 max-w-lg px-12">
          {/* Water icon */}
          <div className="mb-8">
            <div className="w-16 h-16 rounded-2xl flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, rgba(56,189,248,0.15), rgba(16,185,129,0.15))', border: '1px solid rgba(56,189,248,0.2)' }}>
              <Droplets className="w-8 h-8 text-sky-400" />
            </div>
          </div>

          {/* Title */}
          <h1 className="text-3xl font-bold leading-tight mb-3"
            style={{ color: '#e2e8f0' }}>
            Padrón de Usuarios
            <br />
            <span style={{ color: '#38bdf8' }}>Sistema de Riego</span>
          </h1>
          <p className="text-base mb-8" style={{ color: 'rgba(148,163,184,0.8)' }}>
            Plataforma de gestión para el catastro de riego comunitario Guanguilqui Porotog
          </p>

          {/* Stats cards */}
          <div className="grid grid-cols-3 gap-3 mb-10">
            {[
              // «Fichas» confundía: stats.fichas son las PRINCIPALES (una por
              // regante) y el padrón tiene 6.831 fichas contando los predios
              // adicionales. Se etiqueta por lo que de verdad cuenta cada cifra.
              { value: stats.fichas, label: 'Regantes', color: '#38bdf8' },
              { value: stats.predios, label: 'Predios', color: '#10b981' },
              { value: stats.tecnicos, label: 'Técnicos', color: '#f59e0b' },
            ].map(({ value, label, color }) => (
              <div key={label} className="rounded-xl p-3 text-center"
                style={{ background: `${color}08`, border: `1px solid ${color}15` }}>
                <p className="text-xl font-bold" style={{ color }}>{value}</p>
                <p className="text-[10px] uppercase tracking-wider mt-0.5" style={{ color: 'rgba(148,163,184,0.6)' }}>{label}</p>
              </div>
            ))}
          </div>

          {/* Logos row */}
          <div className="flex items-center gap-6">
            <img src={LOGO_PICHINCHA} alt="Prefectura de Pichincha" className="h-10 w-auto object-contain opacity-70" />
            <div className="w-px h-8" style={{ background: 'rgba(148,163,184,0.15)' }} />
            <img src={LOGO_CONSORCIO} alt="Consorcio Cayambe SPT" className="h-8 w-auto object-contain opacity-70" />
          </div>
        </div>

        {/* Bottom gradient fade */}
        <div className="absolute bottom-0 left-0 right-0 h-24"
          style={{ background: 'linear-gradient(to top, #060d1b, transparent)' }} />
      </div>

      {/* ══ RIGHT PANEL — Login Form ══ */}
      <div className="flex-1 flex items-center justify-center relative overflow-hidden px-6">
        {/* Subtle glow */}
        <div className="absolute top-0 right-0 w-[400px] h-[400px] rounded-full opacity-[0.06]"
          style={{ background: 'radial-gradient(circle, #3b82f6, transparent 70%)' }} />

        <div className="w-full max-w-[400px] relative z-10">
          {/* Mobile-only header */}
          <div className="lg:hidden text-center mb-8">
            <div className="flex items-center justify-center gap-4 mb-5">
              <img src={LOGO_PICHINCHA} alt="" className="h-12 w-auto object-contain" />
              <img src={LOGO_CONSORCIO} alt="" className="h-10 w-auto object-contain" />
            </div>
            <h2 className="text-lg font-bold text-amber-400">{PROJECT_TITLE}</h2>
            <p className="text-xs text-slate-400 mt-1">Sistema de Riego Comunitario</p>
          </div>

          {/* Form Card */}
          <div className="rounded-2xl p-8 border"
            style={{ background: 'rgba(15,23,42,0.6)', borderColor: 'rgba(148,163,184,0.08)', backdropFilter: 'blur(20px)' }}>

            {/* Icon + Title */}
            <div className="text-center mb-7">
              <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl mb-4"
                style={{ background: 'linear-gradient(135deg, rgba(59,130,246,0.12), rgba(99,102,241,0.12))', border: '1px solid rgba(59,130,246,0.15)' }}>
                <Shield className="w-6 h-6 text-blue-400" />
              </div>
              <h2 className="text-xl font-bold text-white">Bienvenido</h2>
              <p className="text-sm text-slate-400 mt-1">Ingresa tus credenciales para continuar</p>
            </div>

            {/* Session expired */}
            {sessionExpired && (
              <div className="flex items-center gap-3 px-4 py-3 rounded-xl mb-5"
                style={{ background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.15)' }}>
                <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
                <span className="text-xs text-amber-300/90">Tu sesión expiró por inactividad</span>
              </div>
            )}

            {/* Error */}
            {error && (
              <div className="flex items-center gap-3 px-4 py-3 rounded-xl mb-5"
                style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.15)' }}>
                <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
                <span className="text-xs text-red-300/90">{error}</span>
              </div>
            )}

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-2">Correo electrónico</label>
                <div className="relative group">
                  <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 group-focus-within:text-blue-400 transition-colors" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full pl-11 pr-4 py-3 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none transition-all"
                    style={{ background: 'rgba(30,41,59,0.5)', border: '1px solid rgba(148,163,184,0.1)' }}
                    placeholder="usuario@ejemplo.com"
                    required
                    autoComplete="email"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-2">Contraseña</label>
                <div className="relative group">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 group-focus-within:text-blue-400 transition-colors" />
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full pl-11 pr-4 py-3 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none transition-all"
                    style={{ background: 'rgba(30,41,59,0.5)', border: '1px solid rgba(148,163,184,0.1)' }}
                    placeholder="••••••••"
                    required
                    autoComplete="current-password"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={submitting || loading}
                className="w-full flex items-center justify-center gap-2.5 py-3 rounded-xl font-semibold text-sm text-white transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                style={{
                  background: submitting
                    ? 'rgba(71,85,105,0.5)'
                    : 'linear-gradient(135deg, #2563eb, #3b82f6, #1d4ed8)',
                  boxShadow: submitting ? 'none' : '0 8px 24px rgba(37, 99, 235, 0.3), inset 0 1px 0 rgba(255,255,255,0.1)',
                }}
              >
                {submitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Verificando...
                  </>
                ) : (
                  <>
                    <LogIn className="w-4 h-4" />
                    Ingresar al Sistema
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Footer */}
          <p className="text-center text-[10px] text-slate-600 mt-6">
            Consorcio Cayambe SPT © {new Date().getFullYear()} — Prefectura de Pichincha
          </p>
        </div>
      </div>

      {/* Global CSS for pulse animation */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 0.04; transform: scale(1); }
          50% { opacity: 0.07; transform: scale(1.05); }
        }
      `}</style>
    </div>
  );
}
