import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search, ChevronLeft, ChevronRight, ArrowUpDown,
  Eye, Loader2, X, MapPin,
} from 'lucide-react';
import { type FichaPredio, safeToDate, esFichaHija, esHijaPendiente, esHijaCompletada } from '../../lib/types';
import { getNombreTecnico, getColorTecnico } from '../../lib/constants';
import { useMapNav } from '../../hooks/useMapNav';
import FichaDetailModal from './FichaDetailModal';

interface Props {
  fichas: FichaPredio[];
  loading: boolean;
}

const PAGE_SIZES = [25, 50, 100];

const COLUMNS: { key: keyof FichaPredio; label: string; width?: string }[] = [
  { key: 'es_ficha_hija', label: 'Tipo', width: '70px' },
  { key: 'codigo_final', label: 'Código', width: '90px' },
  { key: 'propietario', label: 'Propietario' },
  { key: 'cedula', label: 'Cédula', width: '100px' },
  { key: 'parroquia', label: 'Parroquia', width: '110px' },
  { key: 'sector', label: 'Sector', width: '110px' },
  { key: 'comunidad', label: 'Comunidad', width: '110px' },
  { key: 'area_total', label: 'Área Total (m²)', width: '110px' },
  { key: 'frecuencia_riego', label: 'Frec. Riego', width: '100px' },
  { key: 'creado_por', label: 'Técnico', width: '130px' },
  { key: 'fecha_creacion', label: 'Fecha', width: '90px' },
];

export default function FichasPage({ fichas, loading }: Props) {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(25);
  const [sortKey, setSortKey] = useState<keyof FichaPredio>('fecha_creacion');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [selectedFicha, setSelectedFicha] = useState<FichaPredio | null>(null);
  const [filtroTipo, setFiltroTipo] = useState<'todas' | 'principales' | 'hijas' | 'hijas_pendientes'>('todas');
  const { navigateToFichaMap } = useMapNav();
  const navigate = useNavigate();

  const totalHijas = useMemo(() => fichas.filter(esFichaHija).length, [fichas]);
  const totalHijasPendientes = useMemo(() => fichas.filter(esHijaPendiente).length, [fichas]);

  const filtered = useMemo(() => {
    let base = fichas;
    if (filtroTipo === 'principales') base = fichas.filter((f) => !esFichaHija(f));
    else if (filtroTipo === 'hijas') base = fichas.filter(esFichaHija);
    else if (filtroTipo === 'hijas_pendientes') base = fichas.filter(esHijaPendiente);

    if (!search.trim()) return base;
    const q = search.toLowerCase();
    return base.filter(
      (f) =>
        f.propietario?.toLowerCase().includes(q) ||
        f.apellidos?.toLowerCase().includes(q) ||
        f.nombres?.toLowerCase().includes(q) ||
        f.cedula?.includes(q) ||
        f.codigo_final?.toLowerCase().includes(q) ||
        f.clave_catastral?.includes(q)
    );
  }, [fichas, search, filtroTipo]);

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      const va = a[sortKey];
      const vb = b[sortKey];
      if (va == null && vb == null) return 0;
      if (va == null) return 1;
      if (vb == null) return -1;

      let cmp: number;
      if (sortKey === 'fecha_creacion') {
        cmp = safeToDate(va).getTime() - safeToDate(vb).getTime();
      } else if (typeof va === 'number' && typeof vb === 'number') {
        cmp = va - vb;
      } else {
        cmp = String(va).localeCompare(String(vb), 'es');
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [filtered, sortKey, sortDir]);

  const totalPages = Math.ceil(sorted.length / pageSize);
  const paged = sorted.slice(page * pageSize, (page + 1) * pageSize);

  const handleSort = (key: keyof FichaPredio) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  // Navegar al mapa centrado en esta ficha
  const handleVerEnMapa = (ficha: FichaPredio) => {
    const hasGeo = ficha.geo?.lat || ficha._geojson?.coordinates;
    if (!hasGeo) return;
    navigateToFichaMap(ficha);
    navigate('/mapa');
  };

  const formatCell = (ficha: FichaPredio, key: keyof FichaPredio): React.ReactNode => {
    const val = ficha[key];
    // 'es_ficha_hija' es null en las fichas principales — el badge lo resuelve
    if (val == null && key !== 'es_ficha_hija') return '—';

    switch (key) {
      case 'es_ficha_hija': {
        if (esHijaPendiente(ficha)) {
          return (
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-semibold bg-white/10 border border-slate-400/40 text-slate-200"
              title="Ficha adicional — pendiente Sección 4 (Producción)">
              ⚪ Adicional
            </span>
          );
        }
        if (esHijaCompletada(ficha)) {
          return (
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 border border-emerald-500/30 text-emerald-400"
              title="Ficha adicional — Sección 4 completada">
              ✅ Adicional
            </span>
          );
        }
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-semibold bg-blue-500/10 border border-blue-500/20 text-blue-400"
            title="Ficha principal investigada en campo">
            🔵 Ppal.
          </span>
        );
      }
      case 'creado_por':
        return (
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: getColorTecnico(val as string) }} />
            <span className="truncate">{getNombreTecnico(val as string)}</span>
          </span>
        );
      case 'fecha_creacion':
        return safeToDate(val).toLocaleDateString('es-EC', { day: '2-digit', month: '2-digit', year: '2-digit' });
      case 'area_total':
        return typeof val === 'number' ? val.toLocaleString('es-EC', { maximumFractionDigits: 0 }) : String(val);
      default:
        return String(val);
    }
  };

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

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: 'var(--text-muted)' }} />
          <input
            type="text"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(0); }}
            placeholder="Buscar por propietario, cédula, código..."
            className="w-full pl-9 pr-8 py-2 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-blue-500/40"
            style={inputStyle}
          />
          {search && (
            <button onClick={() => setSearch('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 cursor-pointer"
              style={{ color: 'var(--text-muted)' }}>
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {totalHijas > 0 && (
          <select
            value={filtroTipo}
            onChange={(e) => { setFiltroTipo(e.target.value as typeof filtroTipo); setPage(0); }}
            className="py-2 px-2 rounded-lg text-xs focus:outline-none cursor-pointer"
            style={inputStyle}
            title="Filtrar por tipo de ficha"
          >
            <option value="todas">Todas las fichas</option>
            <option value="principales">🔵 Solo principales</option>
            <option value="hijas">Solo fichas adicionales</option>
            <option value="hijas_pendientes">⚪ Adicionals pendientes S4 ({totalHijasPendientes})</option>
          </select>
        )}

        <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
          {sorted.length} de {fichas.length} registros
        </div>
      </div>

      {/* Table */}
      <div
        className="rounded-xl border overflow-hidden shadow-sm"
        style={{
          background: 'var(--bg-card)',
          borderColor: 'var(--border-color)',
          boxShadow: 'var(--shadow-card)',
        }}
      >
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b" style={{ borderColor: 'var(--border-color)' }}>
                <th className="px-3 py-3 text-left text-[10px] font-semibold uppercase tracking-wider w-10"
                  style={{ color: 'var(--text-muted)' }}>#</th>
                {COLUMNS.map(({ key, label, width }) => (
                  <th
                    key={key}
                    className="px-3 py-3 text-left text-[10px] font-semibold uppercase tracking-wider cursor-pointer hover:text-blue-400 transition-colors"
                    style={{ width, color: 'var(--text-muted)' }}
                    onClick={() => handleSort(key)}
                  >
                    <span className="flex items-center gap-1">
                      {label}
                      {sortKey === key && (
                        <ArrowUpDown className="w-3 h-3 text-blue-400" />
                      )}
                    </span>
                  </th>
                ))}
                {/* Columnas de acción */}
                <th className="px-3 py-3 text-center text-[10px] font-semibold uppercase tracking-wider w-24"
                  style={{ color: 'var(--text-muted)' }}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {paged.map((ficha, idx) => {
                const hasGeo = !!(ficha.geo?.lat || ficha._geojson?.coordinates);
                return (
                  <tr
                    key={ficha.id}
                    className="border-b transition-colors"
                    style={{
                      borderColor: 'var(--border-color)',
                      background: idx % 2 !== 0 ? 'var(--row-alt)' : undefined,
                    }}
                    onMouseEnter={(e) => {
                      (e.currentTarget as HTMLElement).style.background = 'var(--row-hover)';
                    }}
                    onMouseLeave={(e) => {
                      (e.currentTarget as HTMLElement).style.background = idx % 2 !== 0 ? 'var(--row-alt)' : '';
                    }}
                  >
                    <td className="px-3 py-2 text-xs" style={{ color: 'var(--text-muted)' }}>
                      {page * pageSize + idx + 1}
                    </td>
                    {COLUMNS.map(({ key }) => (
                      <td key={key} className="px-3 py-2 text-xs truncate max-w-[200px]"
                        style={{ color: 'var(--text-secondary)' }}>
                        {formatCell(ficha, key)}
                      </td>
                    ))}
                    <td className="px-3 py-2">
                      <div className="flex items-center justify-center gap-1">
                        {/* Ver en mapa */}
                        <button
                          onClick={() => handleVerEnMapa(ficha)}
                          disabled={!hasGeo}
                          title={hasGeo ? `Ver ${ficha.propietario || ficha.codigo_final} en el mapa` : 'Sin coordenadas GPS'}
                          className={`inline-flex items-center justify-center w-7 h-7 rounded-md transition-colors cursor-pointer ${
                            hasGeo
                              ? 'hover:bg-emerald-500/10 text-emerald-500 hover:text-emerald-400'
                              : 'opacity-25 cursor-not-allowed'
                          }`}
                          style={{ color: hasGeo ? undefined : 'var(--text-muted)' }}
                        >
                          <MapPin className="w-4 h-4" />
                        </button>
                        {/* Ver detalle */}
                        <button
                          onClick={() => setSelectedFicha(ficha)}
                          title="Ver detalle de la ficha"
                          className="inline-flex items-center justify-center w-7 h-7 rounded-md hover:bg-blue-500/10 transition-colors cursor-pointer"
                          style={{ color: 'var(--text-muted)' }}
                        >
                          <Eye className="w-4 h-4 hover:text-blue-400" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {paged.length === 0 && (
                <tr>
                  <td colSpan={COLUMNS.length + 2} className="px-4 py-12 text-center text-sm"
                    style={{ color: 'var(--text-muted)' }}>
                    No se encontraron fichas con los filtros actuales
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div
          className="flex items-center justify-between px-4 py-3 border-t"
          style={{ borderColor: 'var(--border-color)' }}
        >
          <div className="flex items-center gap-2">
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Mostrar</span>
            <select
              value={pageSize}
              onChange={(e) => { setPageSize(Number(e.target.value)); setPage(0); }}
              className="px-2 py-1 rounded-md text-xs cursor-pointer focus:outline-none"
              style={{
                background: 'var(--bg-input)',
                border: '1px solid var(--border-input)',
                color: 'var(--text-primary)',
              }}
            >
              {PAGE_SIZES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
              Página {page + 1} de {totalPages || 1}
            </span>
            <button onClick={() => setPage((p) => Math.max(0, p - 1))} disabled={page === 0}
              className="p-1 rounded-md transition-colors cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed hover:bg-blue-500/10"
              style={{ color: 'var(--text-secondary)' }}>
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1}
              className="p-1 rounded-md transition-colors cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed hover:bg-blue-500/10"
              style={{ color: 'var(--text-secondary)' }}>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
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
