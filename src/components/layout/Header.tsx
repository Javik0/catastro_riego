import { LOGO_PICHINCHA, LOGO_CONSORCIO, PROJECT_SUBTITLE, PARROQUIAS, TECNICOS, SECTORES } from '../../lib/constants';
import { useFiltros } from '../../hooks/useFiltros';
import { MobileMenuButton } from './Sidebar';
import { Filter, X, Search } from 'lucide-react';

interface Props {
  onMobileMenuOpen: () => void;
}

export default function Header({ onMobileMenuOpen }: Props) {
  const { filtros, setFiltro, resetFiltros, hasActiveFilters } = useFiltros();

  const inputClass = "px-2 py-1.5 rounded-md text-xs focus:outline-none focus:ring-1 focus:ring-blue-500/40 cursor-pointer transition-colors";
  const inputStyle = {
    background: 'var(--bg-input)',
    border: '1px solid var(--border-input)',
    color: 'var(--text-primary)',
  };

  return (
    <header
      className="backdrop-blur-md border-b sticky top-0 z-40"
      style={{
        background: 'var(--bg-header)',
        borderColor: 'var(--border-color)',
      }}
    >
      {/* Top bar */}
      <div className="flex items-center justify-between px-4 lg:px-6 h-14">
        <div className="flex items-center gap-3">
          <MobileMenuButton onClick={onMobileMenuOpen} />
          <img src={LOGO_PICHINCHA} alt="Prefectura de Pichincha" className="h-9 w-auto object-contain hidden sm:block" />
        </div>

        <div className="text-center flex-1 min-w-0 px-2">
          <h1 className="text-[11px] sm:text-xs font-bold text-amber-500 tracking-wider truncate">
            {PROJECT_SUBTITLE}
          </h1>
          <p className="text-[9px] hidden sm:block" style={{ color: 'var(--text-muted)' }}>
            Provincia Pichincha — Cantón Cayambe
          </p>
        </div>

        <img src={LOGO_CONSORCIO} alt="Consorcio Cayambe SPT" className="h-9 w-auto object-contain hidden sm:block" />
      </div>

      {/* Filter bar */}
      <div
        className="flex items-center gap-2 px-4 lg:px-6 py-2 border-t overflow-x-auto"
        style={{ borderColor: 'var(--border-color)' }}
      >
        <Filter className="w-4 h-4 shrink-0" style={{ color: 'var(--text-muted)' }} />

        {/* Search */}
        <div className="relative min-w-[160px]">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5" style={{ color: 'var(--text-muted)' }} />
          <input
            type="text"
            value={filtros.busqueda}
            onChange={(e) => setFiltro('busqueda', e.target.value)}
            placeholder="Buscar propietario, cédula..."
            className={`w-full pl-7 pr-3 ${inputClass}`}
            style={{ ...inputStyle, minWidth: 170 }}
          />
        </div>

        <select value={filtros.parroquia} onChange={(e) => setFiltro('parroquia', e.target.value)}
          className={`${inputClass} min-w-[110px]`} style={inputStyle}>
          <option value="">Parroquia</option>
          {PARROQUIAS.map((p) => <option key={p} value={p}>{p}</option>)}
        </select>

        <select value={filtros.sector} onChange={(e) => setFiltro('sector', e.target.value)}
          className={`${inputClass} min-w-[110px] hidden md:block`} style={inputStyle}>
          <option value="">Sector</option>
          {SECTORES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>

        <select value={filtros.tecnico} onChange={(e) => setFiltro('tecnico', e.target.value)}
          className={`${inputClass} min-w-[130px] hidden md:block`} style={inputStyle}>
          <option value="">Técnico</option>
          {Object.entries(TECNICOS).map(([key, { nombre }]) => (
            <option key={key} value={key}>{nombre}</option>
          ))}
        </select>

        <input type="date" value={filtros.fechaDesde} onChange={(e) => setFiltro('fechaDesde', e.target.value)}
          className={`${inputClass} hidden lg:block`} style={inputStyle} title="Fecha desde" />
        <input type="date" value={filtros.fechaHasta} onChange={(e) => setFiltro('fechaHasta', e.target.value)}
          className={`${inputClass} hidden lg:block`} style={inputStyle} title="Fecha hasta" />

        {hasActiveFilters && (
          <button onClick={resetFiltros}
            className="flex items-center gap-1 px-2 py-1.5 rounded-md text-xs text-red-400 border border-red-500/20 bg-red-500/10 hover:bg-red-500/20 transition-colors cursor-pointer shrink-0">
            <X className="w-3 h-3" />
            Limpiar
          </button>
        )}
      </div>
    </header>
  );
}
