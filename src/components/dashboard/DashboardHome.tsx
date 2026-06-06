import { useEffect, useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  PieChart, Pie, Cell, ResponsiveContainer, LineChart, Line,
} from 'recharts';
import {
  ClipboardList, Map as MapIcon, Sprout, PawPrint,
  Users, Droplets, TrendingUp, Loader2, Link, Copy, Check, ExternalLink,
} from 'lucide-react';
import { type FichaPredio, type EstadisticasResumen } from '../../lib/types';
import { calcularEstadisticas } from '../../lib/firestoreService';
import { getColorTecnico, TECNICOS } from '../../lib/constants';
import { useAuth } from '../../hooks/useAuth';

// ── Link Card para Enlaces Rápidos ──
function LinkCard({ title, url, badgeText, badgeColor }: { title: string; url: string; badgeText: string; badgeColor: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Error al copiar el enlace', err);
    }
  };

  return (
    <div className="flex-1 min-w-[260px] p-3 rounded-xl border flex flex-col justify-between gap-2.5 transition-all hover:bg-white/[0.02]"
      style={{
        background: 'rgba(30,41,59,0.3)',
        borderColor: 'rgba(148,163,184,0.1)'
      }}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-semibold text-slate-200 truncate">{title}</span>
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${badgeColor}`}>
          {badgeText}
        </span>
      </div>
      
      <div className="flex items-center gap-2 bg-slate-950/40 p-1.5 rounded-lg border border-slate-800">
        <span className="text-[10px] text-slate-400 truncate flex-1 select-all font-mono">
          {url}
        </span>
        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={handleCopy}
            className="p-1 rounded-md transition-colors cursor-pointer text-slate-400 hover:text-white hover:bg-slate-800"
            title="Copiar enlace"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="p-1 rounded-md transition-colors text-slate-400 hover:text-white hover:bg-slate-850"
            title="Abrir enlace"
          >
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>
    </div>
  );
}

// ── KPI Card ──
function KPICard({ icon: Icon, label, value, color, sub }: {
  icon: React.ElementType; label: string; value: string | number; color: string; sub?: string;
}) {
  return (
    <div
      className="rounded-xl border p-4 transition-all group hover:border-blue-500/30"
      style={{
        background: 'var(--bg-card)',
        borderColor: 'var(--border-color)',
        boxShadow: 'var(--shadow-card)',
      }}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>{label}</p>
          <p className="text-2xl font-bold" style={{ color: 'var(--text-heading)' }}>{typeof value === 'number' ? value.toLocaleString('es-EC') : value}</p>
          {sub && <p className="text-[10px] mt-1" style={{ color: 'var(--text-muted)' }}>{sub}</p>}
        </div>
        <div className="w-10 h-10 rounded-lg flex items-center justify-center opacity-80 group-hover:opacity-100 transition-opacity"
          style={{ background: `${color}15`, border: `1px solid ${color}30` }}
        >
          <Icon className="w-5 h-5" style={{ color }} />
        </div>
      </div>
    </div>
  );
}

// ── Colores para gráficos ──
const PIE_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];

// ── Componente Principal ──
interface Props {
  fichas: FichaPredio[];
  loading: boolean;
  cultivosData: { tipo_cultivo: string }[];
  prediosAdicionalesData?: any[];
}

export default function DashboardHome({ fichas, loading, cultivosData }: Props) {
  const [stats, setStats] = useState<EstadisticasResumen | null>(null);
  const { isAdmin } = useAuth();

  useEffect(() => {
    if (fichas.length > 0) {
      const s = calcularEstadisticas(fichas);

      // Calcular cultivos frecuentes desde datos exportados
      const cultivoCount: Record<string, number> = {};
      for (const c of cultivosData) {
        const tipo = c.tipo_cultivo || 'Sin dato';
        cultivoCount[tipo] = (cultivoCount[tipo] || 0) + 1;
      }
      s.cultivosFrecuentes = cultivoCount;
      s.totalCultivos = cultivosData.length;

      setStats(s);
    }
  }, [fichas, cultivosData]);

  if (loading || !stats) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    );
  }

  // Procesar predios unificados para asociar las fichas secundarias al técnico correspondiente
  const unificadosPorTecnico: Record<string, number> = {};
  const prediosUnificados = prediosAdicionalesData
    ? prediosAdicionalesData.filter((pa) => pa.observaciones_otro?.includes('Unificación automática'))
    : [];

  prediosUnificados.forEach((pa) => {
    const match = pa.observaciones_otro?.match(/Técnico:\s*(.*?)\s*en/);
    const tec = match ? match[1].trim() : 'Sin técnico';
    unificadosPorTecnico[tec] = (unificadosPorTecnico[tec] || 0) + 1;
  });

  const fichasPorTecnico = Object.entries(stats.fichasPorTecnico)
    .map(([nombre, principales]) => {
      const unificadas = unificadosPorTecnico[nombre] || 0;
      return {
        nombre,
        principales,
        unificadas,
        total: principales + unificadas,
      };
    })
    .sort((a, b) => b.total - a.total);

  const metodoRiego = [
    { name: 'Aspersión', value: stats.metodoRiego.aspersion, color: '#3b82f6' },
    { name: 'Gravedad', value: stats.metodoRiego.gravedad, color: '#10b981' },
    { name: 'Goteo', value: stats.metodoRiego.goteo, color: '#f59e0b' },
  ].filter((m) => m.value > 0);

  const tenencia = Object.entries(stats.tenenciaPredioCounts)
    .map(([name, value]) => ({ name, value }));

  const cultivosTop = Object.entries(stats.cultivosFrecuentes)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 12);

  const fichasPorFecha = Object.entries(stats.fichasPorFecha)
    .map(([fecha, count]) => ({ fecha, count }))
    .sort((a, b) => a.fecha.localeCompare(b.fecha));

  const fichasPorParroquia = Object.entries(stats.fichasPorParroquia)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);

  return (
    <div className="space-y-6">
      {/* Enlaces Rápidos de Compartición */}
      {isAdmin && (
        <div
          className="p-5 rounded-2xl border relative overflow-hidden transition-all duration-300 hover:border-slate-700/50"
          style={{
            background: 'linear-gradient(135deg, rgba(30,41,59,0.7) 0%, rgba(15,23,42,0.8) 100%)',
            borderColor: 'var(--border-color)',
            boxShadow: 'var(--shadow-card)',
            backdropFilter: 'blur(12px)',
          }}
        >
          {/* Decoración de fondo */}
          <div className="absolute -right-10 -top-10 w-40 h-40 rounded-full opacity-10 bg-blue-500 blur-3xl pointer-events-none" />
          <div className="absolute -left-10 -bottom-10 w-40 h-40 rounded-full opacity-10 bg-emerald-500 blur-3xl pointer-events-none" />

          <div className="relative z-10 flex flex-col xl:flex-row xl:items-center justify-between gap-6">
            <div>
              <h2 className="text-sm font-bold text-white flex items-center gap-2">
                <Link className="w-4.5 h-4.5 text-amber-400" />
                Enlaces Rápidos de Compartición
              </h2>
              <p className="text-xs text-slate-400 mt-1 max-w-xl leading-relaxed">
                Utiliza estos enlaces para que los comuneros regantes registren sus datos (formulario público) o para que los técnicos ingresen directamente a auditar y procesar las respuestas.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row gap-4 w-full xl:w-auto shrink-0">
              <LinkCard
                title="Formulario para Regantes (Público)"
                url={`${window.location.origin}/encuesta`}
                badgeText="Comuneros"
                badgeColor="bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
              />
              <LinkCard
                title="Módulo de Revisión (Técnicos)"
                url={`${window.location.origin}/encuestas`}
                badgeText="Técnicos"
                badgeColor="bg-blue-500/20 text-blue-300 border border-blue-500/30"
              />
            </div>
          </div>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
        <KPICard 
          icon={ClipboardList} 
          label="Fichas Levantadas" 
          value={stats.totalFichas + prediosUnificados.length} 
          color="#3b82f6" 
          sub={`${stats.totalFichas.toLocaleString('es-EC')} principales + ${prediosUnificados.length} unificadas`}
        />
        <KPICard icon={MapIcon} label="Polígonos Catastro" value={stats.totalPoligonos} color="#10b981" sub="Base catastral completa" />
        <KPICard icon={TrendingUp} label="Área Total (m²)" value={Math.round(stats.areaTotal).toLocaleString('es-EC')} color="#f59e0b" />
        <KPICard icon={Users} label="Técnicos Activos" value={stats.tecnicosActivos} color="#8b5cf6" />
        <KPICard icon={Sprout} label="Cultivos Registrados" value={stats.totalCultivos} color="#22c55e" />
        <KPICard icon={PawPrint} label="Animales Registrados" value={713} color="#ec4899" />
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Fichas por Técnico */}
        <div
          className="rounded-xl border p-4"
          style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)', boxShadow: 'var(--shadow-card)' }}
        >
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Users className="w-4 h-4 text-blue-400" />
            Fichas por Técnico
          </h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={fichasPorTecnico} layout="vertical" margin={{ left: 80, right: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <YAxis type="category" dataKey="nombre" tick={{ fill: '#94a3b8', fontSize: 11 }} width={80} />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                labelStyle={{ color: '#e2e8f0' }}
              />
              <Bar dataKey="principales" name="Fichas Principales" stackId="a">
                {fichasPorTecnico.map((entry, index) => {
                  const tecKey = Object.entries(TECNICOS).find(([, v]) => v.nombre === entry.nombre)?.[0];
                  return <Cell key={index} fill={tecKey ? getColorTecnico(tecKey) : PIE_COLORS[index % PIE_COLORS.length]} />;
                })}
              </Bar>
              <Bar dataKey="unificadas" name="Fichas Unificadas (Predios Adic.)" stackId="a" radius={[0, 4, 4, 0]}>
                {fichasPorTecnico.map((entry, index) => {
                  const tecKey = Object.entries(TECNICOS).find(([, v]) => v.nombre === entry.nombre)?.[0];
                  const color = tecKey ? getColorTecnico(tecKey) : PIE_COLORS[index % PIE_COLORS.length];
                  return <Cell key={index} fill={`${color}80`} />; // Color con 50% de opacidad para diferenciar las fichas unificadas
                })}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Método de Riego */}
        <div
          className="rounded-xl border p-4"
          style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)', boxShadow: 'var(--shadow-card)' }}
        >
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Droplets className="w-4 h-4 text-cyan-400" />
            Método de Riego (promedio %)
          </h3>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={metodoRiego}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={4}
                dataKey="value"
                label={({ name, value }) => `${name}: ${value}%`}
              >
                {metodoRiego.map((entry, index) => (
                  <Cell key={index} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Progreso temporal */}
        <div
          className="rounded-xl border p-4"
          style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)', boxShadow: 'var(--shadow-card)' }}
        >
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-green-400" />
            Fichas Investigadas por Día
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={fichasPorFecha} margin={{ left: 10, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="fecha" tick={{ fill: '#94a3b8', fontSize: 10 }} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                labelStyle={{ color: '#e2e8f0' }}
              />
              <Line type="monotone" dataKey="count" stroke="#10b981" strokeWidth={2} dot={{ r: 4, fill: '#10b981' }} name="Fichas" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Cultivos más frecuentes */}
        <div
          className="rounded-xl border p-4"
          style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)', boxShadow: 'var(--shadow-card)' }}
        >
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Sprout className="w-4 h-4 text-emerald-400" />
            Cultivos Más Frecuentes
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={cultivosTop} margin={{ left: 10, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 9 }} angle={-45} textAnchor="end" height={60} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
              />
              <Bar dataKey="value" name="Registros" fill="#22c55e" radius={[4, 4, 0, 0]}>
                {cultivosTop.map((_, index) => (
                  <Cell key={index} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Charts Row 3 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Tenencia del predio */}
        <div
          className="rounded-xl border p-4"
          style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)', boxShadow: 'var(--shadow-card)' }}
        >
          <h3 className="text-sm font-semibold text-white mb-4">
            Tenencia del Predio
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={tenencia} cx="50%" cy="50%" innerRadius={40} outerRadius={75} dataKey="value"
                label={({ name, value }) => `${name}: ${value}`} paddingAngle={3}>
                {tenencia.map((_, i) => (
                  <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Por parroquia */}
        <div className="bg-slate-800/40 rounded-xl border border-slate-700/30 p-4">
          <h3 className="text-sm font-semibold text-white mb-4">
            Fichas por Parroquia
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={fichasPorParroquia} margin={{ left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }} />
              <Bar dataKey="value" name="Fichas" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
