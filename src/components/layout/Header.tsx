import { LOGO_PICHINCHA, LOGO_CONSORCIO, PROJECT_SUBTITLE, PARROQUIAS, TECNICOS, SECTORES, COMUNIDADES, COMUNIDADES_POR_SECTOR_FILTRO, etiquetaComunidad } from '../../lib/constants';
import { useFiltros } from '../../hooks/useFiltros';
import { useTheme } from '../../hooks/useTheme';
import { useAuth } from '../../hooks/useAuth';
import { MobileMenuButton } from './Sidebar';
import { useLocation } from 'react-router-dom';
import { Filter, X, Search, Sun, Moon, LogOut, Printer } from 'lucide-react';
import { useData } from '../../App';

interface Props {
  onMobileMenuOpen: () => void;
}

export default function Header({ onMobileMenuOpen }: Props) {
  const { filtros, setFiltro, resetFiltros, hasActiveFilters } = useFiltros();
  const { toggleTheme, isDark } = useTheme();
  const { logout, isCliente } = useAuth();
  const location = useLocation();
  const { fichas: allFichas } = useData();

  // Conjunto de comunidades reales que tienen al menos 1 ficha levantada
  const comunidadesConFichas = new Set(
    allFichas.map((f) => (f.comunidad || '').trim().toUpperCase()).filter(Boolean)
  );

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

        <div className="flex items-center gap-3">
          {/* Theme toggle button */}
          <button
            onClick={toggleTheme}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer border"
            style={{
              background: isDark ? 'rgba(251,191,36,0.1)' : 'rgba(99,102,241,0.1)',
              borderColor: isDark ? 'rgba(251,191,36,0.25)' : 'rgba(99,102,241,0.25)',
              color: isDark ? '#fbbf24' : '#6366f1',
            }}
            title={isDark ? 'Cambiar a tema claro' : 'Cambiar a tema oscuro'}
          >
            {isDark ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
            <span className="hidden md:inline">{isDark ? 'Claro' : 'Oscuro'}</span>
          </button>

          {/* Logout button */}
          <button
            onClick={logout}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer border hover:bg-red-500/15"
            style={{
              background: 'rgba(239,68,68,0.06)',
              borderColor: 'rgba(239,68,68,0.2)',
              color: '#f87171',
            }}
            title="Cerrar sesión"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span className="hidden md:inline">Salir</span>
          </button>

          <img src={LOGO_CONSORCIO} alt="Consorcio Cayambe SPT" className="h-9 w-auto object-contain hidden sm:block" />
        </div>
      </div>

      {/* Filter bar — en /represa no aplica: esos filtros son del padrón */}
      {!location.pathname.startsWith('/represa') && (
      <div
        className="flex items-center gap-2 px-4 lg:px-6 py-2 border-t overflow-x-auto"
        style={{ borderColor: 'var(--border-color)' }}
      >
        <Filter className="w-4 h-4 shrink-0" style={{ color: 'var(--text-muted)' }} />

        {location.pathname !== '/mapa' && (
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
        )}

        <select value={filtros.parroquia} onChange={(e) => setFiltro('parroquia', e.target.value)}
          className={`${inputClass} min-w-[110px]`} style={inputStyle}>
          <option value="">Parroquia</option>
          {PARROQUIAS.map((p) => <option key={p} value={p}>{p}</option>)}
        </select>

        <select 
          value={filtros.sectorInv} 
          onChange={(e) => {
            const nuevoSec = e.target.value;
            setFiltro('sectorInv', nuevoSec);
            if (nuevoSec && filtros.comunidad) {
              const pertenecientes = COMUNIDADES_POR_SECTOR_FILTRO[nuevoSec] || [];
              if (!pertenecientes.includes(filtros.comunidad)) {
                setFiltro('comunidad', '');
              }
            }
          }}
          className={`${inputClass} min-w-[130px]`} 
          style={inputStyle}
        >
          <option value="">Sector Inv.</option>
          <option value="Sector 1">Sector 1</option>
          <option value="Sector 2">Sector 2</option>
          <option value="Sector 3">Sector 3</option>
        </select>

        <select value={filtros.sector} onChange={(e) => setFiltro('sector', e.target.value)}
          className={`${inputClass} min-w-[130px] hidden md:block`} style={inputStyle}>
          <option value="">Sector de Riego</option>
          {SECTORES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>

        <select value={filtros.comunidad} onChange={(e) => setFiltro('comunidad', e.target.value)}
          className={`${inputClass} min-w-[130px] hidden md:block`} style={inputStyle}>
          <option value="">Comunidad</option>
          {(filtros.sectorInv
            ? (COMUNIDADES_POR_SECTOR_FILTRO[filtros.sectorInv] || [])
            : COMUNIDADES
          ).map((c) => {
            // Se muestra el número y el nombre del listado oficial de Armando
            // ("15. ELIOT AVELLANEDA"), pero el valor sigue siendo el nombre
            // que está en los datos, que es con el que se filtra.
            const hasFichas = comunidadesConFichas.has(c.trim().toUpperCase());
            const label = etiquetaComunidad(c) + (hasFichas ? '' : ' (Sin investigar)');
            return <option key={c} value={c}>{label}</option>;
          })}
        </select>

        <select value={filtros.tecnico} onChange={(e) => setFiltro('tecnico', e.target.value)}
          className={`${inputClass} min-w-[130px] hidden md:block`} style={inputStyle}>
          <option value="">Técnico</option>
          {Array.from(new Set(Object.values(TECNICOS).map((t) => t.nombre)))
            .sort()
            .map((nombre) => (
              <option key={nombre} value={nombre}>{nombre}</option>
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

        {/* La composición cartográfica es herramienta de trabajo: el cliente no la ve */}
        {location.pathname === '/mapa' && !isCliente && (
          <button
            onClick={() => window.open('/mapa/impresion', '_blank')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs text-emerald-400 border border-emerald-500/20 bg-emerald-500/10 hover:bg-emerald-500/20 hover:scale-[1.02] transition-all cursor-pointer shrink-0 font-medium ml-auto shadow-sm"
            title="Abrir Vista de Composición y Diseño de Mapa estilo QGIS"
          >
            <Printer className="w-3.5 h-3.5" />
            Componer Mapa
          </button>
        )}
      </div>
      )}
    
    </header>
  );
}
