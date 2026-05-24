import { useState } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { LOGO_PICHINCHA, LOGO_CONSORCIO, PROJECT_TITLE } from '../../lib/constants';
import { LogIn, Mail, Lock, AlertCircle, Loader2 } from 'lucide-react';

export default function LoginPage() {
  const { login, loading } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

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
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden"
      style={{
        background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%)',
      }}
    >
      {/* Decorative elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 rounded-full opacity-10"
          style={{ background: 'radial-gradient(circle, #3b82f6, transparent)' }} />
        <div className="absolute -bottom-40 -left-40 w-96 h-96 rounded-full opacity-10"
          style={{ background: 'radial-gradient(circle, #10b981, transparent)' }} />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full opacity-5"
          style={{ background: 'radial-gradient(circle, #f59e0b, transparent)' }} />
      </div>

      <div className="relative z-10 w-full max-w-md mx-4">
        {/* Card */}
        <div className="backdrop-blur-xl rounded-2xl shadow-2xl border border-white/10 overflow-hidden"
          style={{ background: 'rgba(15, 23, 42, 0.8)' }}
        >
          {/* Header with logos */}
          <div className="px-8 pt-8 pb-4">
            <div className="flex items-center justify-between mb-6">
              <img src={LOGO_PICHINCHA} alt="Prefectura de Pichincha" className="h-16 w-auto object-contain" />
              <img src={LOGO_CONSORCIO} alt="Consorcio Cayambe SPT" className="h-16 w-auto object-contain" />
            </div>
            <div className="text-center">
              <h1 className="text-sm font-bold tracking-wider text-amber-400/90 mb-1">
                {PROJECT_TITLE}
              </h1>
              <p className="text-xs text-slate-400 tracking-wide">
                Sistema de Riego Comunitario Guanguilqui Porotog
              </p>
              <p className="text-[10px] text-slate-500 mt-1">
                Provincia Pichincha — Cantón Cayambe
              </p>
            </div>
          </div>

          <div className="h-px bg-gradient-to-r from-transparent via-slate-600/50 to-transparent" />

          {/* Form */}
          <form onSubmit={handleSubmit} className="px-8 py-6 space-y-5">
            <div className="text-center mb-2">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-blue-500/10 border border-blue-500/20 mb-3">
                <LogIn className="w-5 h-5 text-blue-400" />
              </div>
              <h2 className="text-lg font-semibold text-white">Iniciar Sesión</h2>
              <p className="text-xs text-slate-400 mt-1">Accede al panel de administración</p>
            </div>

            {error && (
              <div className="flex items-center gap-2 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20">
                <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
                <span className="text-sm text-red-300">{error}</span>
              </div>
            )}

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">
                  Correo electrónico
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-slate-800/50 border border-slate-700/50 text-white text-sm placeholder-slate-500 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/25 transition-all"
                    placeholder="usuario@ejemplo.com"
                    required
                    autoComplete="email"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">
                  Contraseña
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-slate-800/50 border border-slate-700/50 text-white text-sm placeholder-slate-500 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/25 transition-all"
                    placeholder="••••••••"
                    required
                    autoComplete="current-password"
                  />
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={submitting || loading}
              className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg font-medium text-sm text-white transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
              style={{
                background: submitting ? '#475569' : 'linear-gradient(135deg, #3b82f6, #2563eb)',
                boxShadow: submitting ? 'none' : '0 4px 14px rgba(59, 130, 246, 0.3)',
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

          {/* Footer */}
          <div className="px-8 pb-6">
            <p className="text-center text-[10px] text-slate-600">
              Consorcio Cayambe SPT © 2026 — Prefectura de Pichincha
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
