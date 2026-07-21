import { useState, useMemo } from 'react';
import { Loader2, Search, X, GitBranch } from 'lucide-react';
import { type FichaPredio, esFichaHija, esHijaPendiente, safeToDate } from '../../lib/types';
import { getNombreTecnico } from '../../lib/constants';
import FichaDetailModal from './FichaDetailModal';

interface Props {
  fichas: FichaPredio[];
  loading: boolean;
}

type FiltroEstado = 'todos' | 'pendiente_produccion' | 'completada' | 'en_revision';

function estadoDe(f: FichaPredio): string {
  return f.estado_investigacion || 'pendiente_produccion';
}

const ESTADO_BADGE: Record<string, { label: string; cls: string }> = {
  pendiente_produccion: { label: '⚪ Pendiente S4', cls: 'bg-white/10 border-slate-400/40 text-slate-200' },
  completada: { label: '✅ Completada', cls: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' },
  en_revision: { label: '🔄 En Revisión', cls: 'bg-amber-500/10 border-amber-500/30 text-amber-400' },
};

export default function AdminAuditoriaFichasHijas({ fichas, loading }: Props) {
  const [filtroEstado, setFiltroEstado] = useState<FiltroEstado>('todos');
  const [filtroSector, setFiltroSector] = useState('todos');
  const [search, setSearch] = useState('');
  const [selectedFicha, setSelectedFicha] = useState<FichaPredio | null>(null);

  const hijas = useMemo(() => fichas.filter(esFichaHija), [fichas]);
  const madresPorId = useMemo(() => {
    const m = new Map<string, FichaPredio>();
    for (const f of fichas) if (!esFichaHija(f) && f.id) m.set(f.id, f);
    return m;
  }, [fichas]);

  const sectores = useMemo(
    () => Array.from(new Set(hijas.map((h) => h.sector_investigacion || 'Sin sector'))).sort(),
    [hijas]
  );

  // Resumen por sector para las barras de avance
  const resumenSectores = useMemo(() => {
    const r: Record<string, { total: number; completadas: number }> = {};
    for (const h of hijas) {
      const s = h.sector_investigacion || 'Sin sector';
      r[s] = r[s] || { total: 0, completadas: 0 };
      r[s].total += 1;
      if (!esHijaPendiente(h)) r[s].completadas += 1;
    }
    return r;
  }, [hijas]);

  const filtradas = useMemo(() => {
    let base = hijas;
    if (filtroEstado !== 'todos') base = base.filter((h) => estadoDe(h) === filtroEstado);
    if (filtroSector !== 'todos') base = base.filter((h) => (h.sector_investigacion || 'Sin sector') === filtroSector);
    if (search.trim()) {
      const q = search.toLowerCase();
      base = base.filter(
        (h) =>
          h.propietario?.toLowerCase().includes(q) ||
          h.codigo_final?.toLowerCase().includes(q) ||
          h.clave_catastral?.includes(q) ||
          madresPorId.get(h.ficha_madre_id || '')?.codigo_final?.toLowerCase().includes(q)
      );
    }
    return [...base].sort((a, b) => (a.codigo_final || '').localeCompare(b.codigo_final || ''));
  }, [hijas, filtroEstado, filtroSector, search, madresPorId]);

  const totales = useMemo(() => ({
    total: hijas.length,
    pendientes: hijas.filter(esHijaPendiente).length,
    completadas: hijas.filter((h) => estadoDe(h) === 'completada').length,
    enRevision: hijas.filter((h) => estadoDe(h) === 'en_revision').length,
  }), [hijas]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    );
  }

  const inputStyle = {
    background: 'var(--bg-input)',
    border: '1px solid var(--border-input)',
    color: 'var(--text-primary)',
  };

  const pctAvance = totales.total > 0 ? Math.round((totales.completadas / totales.total) * 100) : 0;

  return (
    <div className="space-y-5">
      {/* Encabezado */}
      <div className="flex items-center gap-2">
        <GitBranch className="w-5 h-5 text-blue-500" />
        <div>
          <h2 className="text-sm font-bold" style={{ color: 'var(--text-heading)' }}>
            Auditoría de Fichas Adicionales
          </h2>
          <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
            Control de predios de la Sección 7 convertidos en fichas — avance de investigación de la Sección 4 (Producción)
          </p>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: 'Total Fichas Adicionales', value: totales.total, color: '#3b82f6' },
          { label: '⚪ Pendientes S4', value: totales.pendientes, color: '#94a3b8' },
          { label: '✅ Completadas', value: totales.completadas, color: '#10b981' },
          { label: '% de Avance', value: `${pctAvance}%`, color: '#f59e0b' },
        ].map(({ label, value, color }) => (
          <div key={label} className="rounded-xl border p-3"
            style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
            <p className="text-[10px] mb-1" style={{ color: 'var(--text-muted)' }}>{label}</p>
            <p className="text-xl font-bold" style={{ color }}>{typeof value === 'number' ? value.toLocaleString('es-EC') : value}</p>
          </div>
        ))}
      </div>

      {/* Avance por sector */}
      <div className="rounded-xl border p-4 space-y-3"
        style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
        <p className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
          Avance por Sector
        </p>
        {Object.entries(resumenSectores).sort().map(([sector, r]) => {
          const pct = r.total > 0 ? Math.round((r.completadas / r.total) * 100) : 0;
          return (
            <div key={sector}>
              <div className="flex justify-between text-[11px] mb-1">
                <span style={{ color: 'var(--text-secondary)' }}>{sector}</span>
                <span style={{ color: 'var(--text-muted)' }}>{r.completadas} / {r.total} ({pct}%)</span>
              </div>
              <div className="w-full h-2 rounded-full overflow-hidden bg-black/10 dark:bg-white/10">
                <div className="h-full rounded-full bg-emerald-500 transition-all" style={{ width: `${pct}%` }} />
              </div>
            </div>
          );
        })}
      </div>

      {/* Filtros */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: 'var(--text-muted)' }} />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar por propietario, código, clave, ficha madre..."
            className="w-full pl-9 pr-8 py-2 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-blue-500/40"
            style={inputStyle}
          />
          {search && (
            <button onClick={() => setSearch('')} className="absolute right-2 top-1/2 -translate-y-1/2 cursor-pointer" style={{ color: 'var(--text-muted)' }}>
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
        <select value={filtroEstado} onChange={(e) => setFiltroEstado(e.target.value as FiltroEstado)}
          className="py-2 px-2 rounded-lg text-xs focus:outline-none cursor-pointer" style={inputStyle}>
          <option value="todos">Todos los estados</option>
          <option value="pendiente_produccion">⚪ Pendientes S4</option>
          <option value="completada">✅ Completadas</option>
          <option value="en_revision">🔄 En Revisión</option>
        </select>
        <select value={filtroSector} onChange={(e) => setFiltroSector(e.target.value)}
          className="py-2 px-2 rounded-lg text-xs focus:outline-none cursor-pointer" style={inputStyle}>
          <option value="todos">Todos los sectores</option>
          {sectores.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{filtradas.length} fichas adicionales</span>
      </div>

      {/* Tabla madre → hija */}
      <div className="rounded-xl border overflow-hidden"
        style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)', boxShadow: 'var(--shadow-card)' }}>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b" style={{ borderColor: 'var(--border-color)' }}>
                {['Ficha Adicional', 'Estado', 'Propietario', 'Clave Catastral', 'Sector', 'Ficha Principal', 'Completada por', 'Fecha S4'].map((h) => (
                  <th key={h} className="px-3 py-3 text-left text-[10px] font-semibold uppercase tracking-wider"
                    style={{ color: 'var(--text-muted)' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtradas.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-3 py-10 text-center text-xs" style={{ color: 'var(--text-muted)' }}>
                    {hijas.length === 0
                      ? 'Aún no se han generado fichas adicionales — se crean con generar_fichas_hijas.py en QGIS.'
                      : 'Sin resultados con los filtros actuales.'}
                  </td>
                </tr>
              )}
              {filtradas.map((h) => {
                const madre = madresPorId.get(h.ficha_madre_id || '');
                const badge = ESTADO_BADGE[estadoDe(h)] || ESTADO_BADGE.pendiente_produccion;
                return (
                  <tr key={h.id} className="border-b transition-colors hover:bg-black/5 dark:hover:bg-white/5"
                    style={{ borderColor: 'var(--border-color)' }}>
                    <td className="px-3 py-2">
                      <button onClick={() => setSelectedFicha(h)}
                        className="text-xs font-mono font-semibold text-blue-500 hover:underline cursor-pointer">
                        {h.codigo_final}
                      </button>
                    </td>
                    <td className="px-3 py-2">
                      <span className={`inline-flex px-1.5 py-0.5 rounded-full text-[10px] font-semibold border ${badge.cls}`}>
                        {badge.label}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-xs" style={{ color: 'var(--text-primary)' }}>{h.propietario || '—'}</td>
                    <td className="px-3 py-2 text-xs font-mono" style={{ color: 'var(--text-secondary)' }}>{h.clave_catastral || '—'}</td>
                    <td className="px-3 py-2 text-xs" style={{ color: 'var(--text-secondary)' }}>{h.sector_investigacion || 'Sin sector'}</td>
                    <td className="px-3 py-2">
                      {madre ? (
                        <button onClick={() => setSelectedFicha(madre)}
                          className="text-xs font-mono text-cyan-500 hover:underline cursor-pointer">
                          {madre.codigo_final}
                        </button>
                      ) : (
                        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>—</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-xs" style={{ color: 'var(--text-secondary)' }}>
                      {h.completado_por ? getNombreTecnico(h.completado_por) : '—'}
                    </td>
                    <td className="px-3 py-2 text-xs" style={{ color: 'var(--text-secondary)' }}>
                      {h.fecha_completado
                        ? safeToDate(h.fecha_completado).toLocaleDateString('es-EC', { day: '2-digit', month: '2-digit', year: '2-digit' })
                        : '—'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {selectedFicha && (
        <FichaDetailModal
          ficha={selectedFicha}
          onClose={() => setSelectedFicha(null)}
          todasFichas={fichas}
          onSelectFicha={(f) => setSelectedFicha(f)}
        />
      )}
    </div>
  );
}
