import { useEffect, useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  PieChart, Pie, Cell, ResponsiveContainer, LineChart, Line, LabelList,
} from 'recharts';
import {
  ClipboardList, Map as MapIcon, Sprout, PawPrint,
  Users, Droplets, TrendingUp, Loader2, Link, Copy, Check, ExternalLink, MapPin
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
    <div className="flex-1 min-w-[260px] p-3 rounded-xl border flex flex-col justify-between gap-2.5 transition-all hover:bg-black/5 dark:hover:bg-white/5"
      style={{
        background: 'var(--bg-input)',
        borderColor: 'var(--border-color)'
      }}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-semibold truncate" style={{ color: 'var(--text-primary)' }}>{title}</span>
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${badgeColor}`}>
          {badgeText}
        </span>
      </div>
      
      <div className="flex items-center gap-2 p-1.5 rounded-lg border" style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
        <span className="text-[10px] truncate flex-1 select-all font-mono" style={{ color: 'var(--text-secondary)' }}>
          {url}
        </span>
        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={handleCopy}
            className="p-1 rounded-md transition-colors cursor-pointer hover:bg-black/5 dark:hover:bg-white/10"
            style={{ color: 'var(--text-secondary)' }}
            title="Copiar enlace"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="p-1 rounded-md transition-colors hover:bg-black/5 dark:hover:bg-white/10"
            style={{ color: 'var(--text-secondary)' }}
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
          {sub && <p className="text-[11px] font-medium mt-1" style={{ color: 'var(--text-secondary)' }}>{sub}</p>}
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
  cultivosData: any[];
  animalesData?: any[];
  prediosAdicionalesData?: any[];
}

export default function DashboardHome({ fichas, loading, cultivosData, animalesData = [], prediosAdicionalesData = [] }: Props) {
  const [stats, setStats] = useState<EstadisticasResumen | null>(null);
  const { isAdmin } = useAuth();

  useEffect(() => {
    if (fichas.length > 0) {
      const s = calcularEstadisticas(fichas);

      // Calcular cultivos frecuentes desde datos filtrados
      const cultivoCount: Record<string, number> = {};
      const fIds = new Set(fichas.map(f => f.id));
      const fCultivos = cultivosData.filter((c: any) => fIds.has(c.ficha_id));

      for (const c of fCultivos) {
        const tipo = c.tipo_cultivo || 'Sin dato';
        cultivoCount[tipo] = (cultivoCount[tipo] || 0) + 1;
      }
      s.cultivosFrecuentes = cultivoCount;
      s.totalCultivos = fCultivos.length;

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

  // Filtrar subtablas por las fichas actualmente filtradas
  const filteredFichaIds = new Set(fichas.map(f => f.id));
  const filteredAnimales = animalesData.filter((a: any) => filteredFichaIds.has(a.ficha_id));
  const filteredPrediosAdicionales = prediosAdicionalesData.filter((pa: any) => filteredFichaIds.has(pa.ficha_id));
  const totalAnimales = filteredAnimales.reduce((acc: number, a: any) => acc + (Number(a.cantidad) || 0), 0);

  // Claves catastrales principales activas
  const clavesPrincipales = new Set(fichas.map(f => (f.clave_catastral || '').trim()).filter(Boolean));

  // Claves declaradas verbalmente únicas (otros predios del regante sin encuesta propia)
  const clavesDeclaradasUnicas = new Set(
    filteredPrediosAdicionales
      .map((pa: any) => (pa.clave_catastral_otro || '').trim())
      .filter(Boolean)
  );

  // Filtrar para obtener solo las "Adicionales Puras" (claves únicas sin encuesta de ningún tipo)
  const clavesDeclaradasPuras = Array.from(clavesDeclaradasUnicas).filter(k =>
    !clavesPrincipales.has(k)
  );

  const totalDeclaradosPuros = clavesDeclaradasPuras.length;

  const fichasPorTecnico = Object.entries(stats.fichasPorTecnico)
    .map(([nombre, principales]) => ({
      nombre,
      principales,
    }))
    .sort((a, b) => b.principales - a.principales);

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

  // ── Cálculos dinámicos sectoriales para los gráficos Recharts ──
  // 1. Cobertura de Riego (Riego vs Secano en ha)
  const areaRiegoTotalM2 = fichas.reduce((acc, f) => acc + (Number(f.area_riego) || 0), 0);
  const areaSinRiegoTotalM2 = fichas.reduce((acc, f) => acc + (Number(f.area_sin_riego) || 0), 0);
  const areaRiegoHa = areaRiegoTotalM2 / 10000;
  const areaSinRiegoHa = areaSinRiegoTotalM2 / 10000;

  const coberturaRiegoData = [
    { name: 'Con Riego', value: Number(areaRiegoHa.toFixed(2)), color: '#3b82f6' },
    { name: 'Secano (Sin Riego)', value: Number(areaSinRiegoHa.toFixed(2)), color: '#f59e0b' }
  ].filter(item => item.value > 0);

  // 2. Distribución de Especies Pecuarias (Animales)
  const animalesPorEspecieMap: Record<string, number> = {};
  for (const a of filteredAnimales) {
    const esp = a.especie || 'Sin clasificar';
    animalesPorEspecieMap[esp] = (animalesPorEspecieMap[esp] || 0) + (Number(a.cantidad) || 0);
  }
  const animalesPorEspecieData = Object.entries(animalesPorEspecieMap)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 5);

  // 3. Propósito de Cultivos (Autoconsumo vs Venta)
  let autoconsumoCount = 0;
  let mercadoCount = 0;
  let agroindustriaCount = 0;
  let exportacionCount = 0;

  const fIds = new Set(fichas.map(f => f.id));
  const fCultivos = cultivosData.filter((c: any) => fIds.has(c.ficha_id));
  for (const c of fCultivos) {
    if (c.es_autoconsumo) autoconsumoCount++;
    if (c.es_mercado) mercadoCount++;
    if (c.es_agroindustria) agroindustriaCount++;
    if (c.es_exportacion) exportacionCount++;
  }

  const destinoCultivosData = [
    { name: 'Autoconsumo', value: autoconsumoCount, color: '#10b981' },
    { name: 'Mercado / Venta', value: mercadoCount, color: '#3b82f6' },
    { name: 'Agroindustria', value: agroindustriaCount, color: '#8b5cf6' },
    { name: 'Exportación', value: exportacionCount, color: '#ec4899' }
  ].filter(item => item.value > 0);

  return (
    <div className="space-y-6">
      {/* Enlaces Rápidos de Compartición */}
      {isAdmin && (
        <div
          className="p-5 rounded-2xl border relative overflow-hidden transition-all duration-300"
          style={{
            background: 'var(--bg-card)',
            borderColor: 'var(--border-color)',
            boxShadow: 'var(--shadow-card)',
            backdropFilter: 'blur(12px)',
          }}
        >
          {/* Decoración de fondo */}
          <div className="absolute -right-10 -top-10 w-40 h-40 rounded-full opacity-10 dark:opacity-20 bg-blue-500 blur-3xl pointer-events-none" />
          <div className="absolute -left-10 -bottom-10 w-40 h-40 rounded-full opacity-10 dark:opacity-20 bg-emerald-500 blur-3xl pointer-events-none" />

          <div className="relative z-10 flex flex-col xl:flex-row xl:items-center justify-between gap-6">
            <div>
              <h2 className="text-sm font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                <Link className="w-4.5 h-4.5 text-amber-500" />
                Enlaces Rápidos de Compartición
              </h2>
              <p className="text-xs mt-1 max-w-xl leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                Utiliza estos enlaces para que los comuneros regantes registren sus datos (formulario público) o para que los técnicos ingresen directamente a auditar y procesar las respuestas.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row gap-4 w-full xl:w-auto shrink-0">
              <LinkCard
                title="Formulario para Regantes (Público)"
                url={`${window.location.origin}/encuesta`}
                badgeText="Comuneros"
                badgeColor="bg-emerald-500/10 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border border-emerald-500/20 dark:border-emerald-500/30"
              />
              <LinkCard
                title="Módulo de Revisión (Técnicos)"
                url={`${window.location.origin}/encuestas`}
                badgeText="Técnicos"
                badgeColor="bg-blue-500/10 dark:bg-blue-500/20 text-blue-700 dark:text-blue-300 border border-blue-500/20 dark:border-blue-500/30"
              />
            </div>
          </div>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-7 gap-3">
        <KPICard 
          icon={ClipboardList} 
          label="Fichas Levantadas" 
          value={stats.totalFichas} 
          color="#3b82f6" 
          sub={`Total de fichas registradas en el catastro`}
        />
        <KPICard 
          icon={MapPin} 
          label="Otros Predios del Regante" 
          value={totalDeclaradosPuros} 
          color="#06b6d4" 
          sub={`${totalDeclaradosPuros.toLocaleString('es-EC')} predios únicos sin encuesta`}
        />
        <KPICard icon={MapIcon} label="Polígonos Catastro" value={stats.totalPoligonos} color="#10b981" sub="Base catastral completa" />
        <KPICard icon={TrendingUp} label="Área Total (m²)" value={Math.round(stats.areaTotal).toLocaleString('es-EC')} color="#f59e0b" />
        <KPICard icon={Users} label="Técnicos Activos" value={stats.tecnicosActivos} color="#8b5cf6" />
        <KPICard icon={Sprout} label="Cultivos Registrados" value={stats.totalCultivos} color="#22c55e" />
        <KPICard icon={PawPrint} label="Animales Registrados" value={totalAnimales} color="#ec4899" sub={`${filteredAnimales.length} registros`} />
      </div>

      {/* Sección Análisis Sectorial */}
      <div className="space-y-3">
        <h3 className="text-sm font-bold tracking-wide uppercase text-blue-500 flex items-center gap-2">
          <TrendingUp className="w-4 h-4" />
          Análisis del Sector Seleccionado
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Tarjeta % Cultivos */}
          <div className="rounded-2xl border p-5 flex flex-col justify-between relative overflow-hidden transition-all duration-300 hover:border-emerald-500/30"
               style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)', boxShadow: 'var(--shadow-card)' }}>
            <div className="flex justify-between items-start">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Cultivos en el Sector</p>
                <h4 className="text-3xl font-black mt-2" style={{ color: 'var(--text-heading)' }}>{((stats.totalCultivos / (cultivosData.length || 1)) * 100).toFixed(1)}%</h4>
                <p className="text-[11px] mt-1 leading-normal" style={{ color: 'var(--text-secondary)' }}>
                  {stats.totalCultivos.toLocaleString('es-EC')} de {(cultivosData.length).toLocaleString('es-EC')} parcelas agrícolas del sistema
                </p>
              </div>
              <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 shrink-0">
                <Sprout className="w-5 h-5" />
              </div>
            </div>
            {/* Barra de progreso */}
            <div className="w-full bg-black/5 dark:bg-white/10 h-2 rounded-full mt-4 overflow-hidden">
              <div className="bg-emerald-500 h-full rounded-full transition-all duration-500" style={{ width: `${Math.min((stats.totalCultivos / (cultivosData.length || 1)) * 100, 100)}%` }} />
            </div>
          </div>

          {/* Tarjeta % Animales */}
          <div className="rounded-2xl border p-5 flex flex-col justify-between relative overflow-hidden transition-all duration-300 hover:border-pink-500/30"
               style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)', boxShadow: 'var(--shadow-card)' }}>
            <div className="flex justify-between items-start">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Animales en el Sector</p>
                <h4 className="text-3xl font-black mt-2" style={{ color: 'var(--text-heading)' }}>{((totalAnimales / (animalesData.reduce((acc: number, a: any) => acc + (Number(a.cantidad) || 0), 0) || 1)) * 100).toFixed(1)}%</h4>
                <p className="text-[11px] mt-1 leading-normal" style={{ color: 'var(--text-secondary)' }}>
                  {totalAnimales.toLocaleString('es-EC')} de {(animalesData.reduce((acc: number, a: any) => acc + (Number(a.cantidad) || 0), 0)).toLocaleString('es-EC')} cabezas registradas
                </p>
              </div>
              <div className="p-3 rounded-xl bg-pink-500/10 border border-pink-500/20 text-pink-500 shrink-0">
                <PawPrint className="w-5 h-5" />
              </div>
            </div>
            {/* Barra de progreso */}
            <div className="w-full bg-black/5 dark:bg-white/10 h-2 rounded-full mt-4 overflow-hidden">
              <div className="bg-pink-500 h-full rounded-full transition-all duration-500" style={{ width: `${Math.min((totalAnimales / (animalesData.reduce((acc: number, a: any) => acc + (Number(a.cantidad) || 0), 0) || 1)) * 100, 100)}%` }} />
            </div>
          </div>

          {/* Tarjeta ha Sin Riego */}
          <div className="rounded-2xl border p-5 flex flex-col justify-between relative overflow-hidden transition-all duration-300 hover:border-amber-500/30"
               style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)', boxShadow: 'var(--shadow-card)' }}>
            <div className="flex justify-between items-start">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Superficie Sin Riego</p>
                <h4 className="text-3xl font-black mt-2" style={{ color: 'var(--text-heading)' }}>{(fichas.reduce((acc, f) => acc + (Number(f.area_sin_riego) || 0), 0) / 10000).toFixed(2)} ha</h4>
                <p className="text-[11px] mt-1 leading-normal" style={{ color: 'var(--text-secondary)' }}>
                  Equivalente a {(fichas.reduce((acc, f) => acc + (Number(f.area_sin_riego) || 0), 0)).toLocaleString('es-EC')} m² de secano en este sector
                </p>
              </div>
              <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-500 shrink-0">
                <Droplets className="w-5 h-5" />
              </div>
            </div>
            {/* Mensaje informativo */}
            <div className="text-[10px] mt-4 font-semibold text-amber-600 dark:text-amber-400 flex items-center gap-1">
              <span>Hectáreas de secano registradas en fichas</span>
            </div>
          </div>
        </div>
      </div>

      {/* Sección Gráficos Sectoriales Dinámicos */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        {/* Cobertura de Riego */}
        <div className="rounded-xl border p-4 flex flex-col justify-between"
             style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)', boxShadow: 'var(--shadow-card)' }}>
          <h4 className="text-xs font-bold uppercase tracking-wider text-blue-500 mb-4 flex items-center gap-2">
            <Droplets className="w-4 h-4 text-blue-500" />
            Uso del Suelo: Riego vs Secano (ha)
          </h4>
          <div className="h-[180px] flex items-center justify-center">
            {coberturaRiegoData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={coberturaRiegoData}
                    cx="50%"
                    cy="50%"
                    innerRadius={45}
                    outerRadius={70}
                    paddingAngle={3}
                    dataKey="value"
                    label={({ name, value }) => `${name}: ${value} ha`}
                  >
                    {coberturaRiegoData.map((entry, index) => (
                      <Cell key={index} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)', borderRadius: 8 }}
                    itemStyle={{ color: 'var(--text-primary)' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Sin datos de área</span>
            )}
          </div>
        </div>

        {/* Especies Pecuarias */}
        <div className="rounded-xl border p-4 flex flex-col justify-between"
             style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)', boxShadow: 'var(--shadow-card)' }}>
          <h4 className="text-xs font-bold uppercase tracking-wider text-pink-500 mb-4 flex items-center gap-2">
            <PawPrint className="w-4 h-4 text-pink-500" />
            Especies Pecuarias Principales (Cabezas)
          </h4>
          <div className="h-[180px]">
            {animalesPorEspecieData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={animalesPorEspecieData} layout="vertical" margin={{ left: 10, right: 10, top: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                  <XAxis type="number" tick={{ fill: 'var(--text-secondary)', fontSize: 10 }} />
                  <YAxis type="category" dataKey="name" tick={{ fill: 'var(--text-secondary)', fontSize: 10 }} width={70} />
                  <Tooltip
                    contentStyle={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)', borderRadius: 8 }}
                    itemStyle={{ color: 'var(--text-primary)' }}
                  />
                  <Bar dataKey="value" fill="#ec4899" radius={[0, 4, 4, 0]} name="Animales">
                    {animalesPorEspecieData.map((_, index) => (
                      <Cell key={index} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                    <LabelList dataKey="value" position="right" fill="var(--text-primary)" fontSize={10} fontWeight="bold" />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center">
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Sin registros pecuarios</span>
              </div>
            )}
          </div>
        </div>

        {/* Propósito de Cultivos */}
        <div className="rounded-xl border p-4 flex flex-col justify-between"
             style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)', boxShadow: 'var(--shadow-card)' }}>
          <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-500 mb-4 flex items-center gap-2">
            <Sprout className="w-4 h-4 text-emerald-500" />
            Destino de la Producción Agrícola
          </h4>
          <div className="h-[180px]">
            {destinoCultivosData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={destinoCultivosData} margin={{ left: 10, right: 10, top: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                  <XAxis dataKey="name" tick={{ fill: 'var(--text-secondary)', fontSize: 9 }} />
                  <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 10 }} />
                  <Tooltip
                    contentStyle={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)', borderRadius: 8 }}
                    itemStyle={{ color: 'var(--text-primary)' }}
                  />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]} name="Cultivos">
                    {destinoCultivosData.map((entry, index) => (
                      <Cell key={index} fill={entry.color} />
                    ))}
                    <LabelList dataKey="value" position="top" fill="var(--text-primary)" fontSize={10} fontWeight="bold" />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center">
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Sin registros agrícolas</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Fichas por Técnico */}
        <div
          className="rounded-xl border p-4"
          style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)', boxShadow: 'var(--shadow-card)' }}
        >
          <h3 className="text-sm font-semibold mb-4 flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
            <Users className="w-4 h-4 text-blue-400" />
            Fichas por Técnico
          </h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={fichasPorTecnico} layout="vertical" margin={{ left: 80, right: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
              <XAxis type="number" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
              <YAxis type="category" dataKey="nombre" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} width={80} />
              <Tooltip
                contentStyle={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)', borderRadius: 8 }}
                itemStyle={{ color: 'var(--text-primary)' }}
                labelStyle={{ color: 'var(--text-primary)' }}
              />
              <Bar dataKey="principales" name="Fichas Investigadas" radius={[0, 4, 4, 0]}>
                {fichasPorTecnico.map((entry, index) => {
                  const tecKey = Object.entries(TECNICOS).find(([, v]) => v.nombre === entry.nombre)?.[0];
                  return <Cell key={index} fill={tecKey ? getColorTecnico(tecKey) : PIE_COLORS[index % PIE_COLORS.length]} />;
                })}
                <LabelList dataKey="principales" position="right" fill="var(--text-primary)" fontSize={11} fontWeight="bold" />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Método de Riego */}
        <div
          className="rounded-xl border p-4"
          style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)', boxShadow: 'var(--shadow-card)' }}
        >
          <h3 className="text-sm font-semibold mb-4 flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
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
                contentStyle={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)', borderRadius: 8 }}
                itemStyle={{ color: 'var(--text-primary)' }}
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
          <h3 className="text-sm font-semibold mb-4 flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
            <TrendingUp className="w-4 h-4 text-green-400" />
            Fichas Investigadas por Día
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={fichasPorFecha} margin={{ left: 10, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
              <XAxis dataKey="fecha" tick={{ fill: 'var(--text-secondary)', fontSize: 10 }} />
              <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)', borderRadius: 8 }}
                itemStyle={{ color: 'var(--text-primary)' }}
                labelStyle={{ color: 'var(--text-primary)' }}
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
          <h3 className="text-sm font-semibold mb-4 flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
            <Sprout className="w-4 h-4 text-emerald-400" />
            Cultivos Más Frecuentes
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={cultivosTop} margin={{ left: 10, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
              <XAxis dataKey="name" tick={{ fill: 'var(--text-secondary)', fontSize: 9 }} angle={-45} textAnchor="end" height={60} />
              <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)', borderRadius: 8 }}
                itemStyle={{ color: 'var(--text-primary)' }}
              />
              <Bar dataKey="value" name="Registros" fill="#22c55e" radius={[4, 4, 0, 0]}>
                {cultivosTop.map((_, index) => (
                  <Cell key={index} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                ))}
                <LabelList dataKey="value" position="top" fill="var(--text-primary)" fontSize={10} fontWeight="bold" />
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
          <h3 className="text-sm font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>
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
              <Tooltip
                contentStyle={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)', borderRadius: 8 }}
                itemStyle={{ color: 'var(--text-primary)' }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Por parroquia */}
        <div
          className="rounded-xl border p-4"
          style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)', boxShadow: 'var(--shadow-card)' }}
        >
          <h3 className="text-sm font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>
            Fichas por Parroquia
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={fichasPorParroquia} margin={{ left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
              <XAxis dataKey="name" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
              <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)', borderRadius: 8 }}
                itemStyle={{ color: 'var(--text-primary)' }}
              />
              <Bar dataKey="value" name="Fichas" fill="#8b5cf6" radius={[4, 4, 0, 0]}>
                <LabelList dataKey="value" position="top" fill="var(--text-primary)" fontSize={10} fontWeight="bold" />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
