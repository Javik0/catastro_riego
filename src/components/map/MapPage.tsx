import { useEffect, useState, useRef, useMemo, useCallback } from 'react';
import {
  MapContainer, TileLayer, GeoJSON, CircleMarker, Popup,
  LayersControl, useMap, Tooltip, Marker,
} from 'react-leaflet';
import L from 'leaflet';
import type { CircleMarker as LeafletCircleMarker, LeafletMouseEvent } from 'leaflet';
import type { FeatureCollection, Geometry } from 'geojson';
import { Loader2, MapPin, Eye, EyeOff, Search, X } from 'lucide-react';
import { type FichaPredio, safeToDate, esFichaHija, esHijaPendiente } from '../../lib/types';
import { getNombreTecnico, getColorTecnico, TECNICOS } from '../../lib/constants';
import PredioPopupCard from './PredioPopupCard';
import FichaDetailModal from '../fichas/FichaDetailModal';
import { useMapNav } from '../../hooks/useMapNav';
import { wgs84ToUtm17S, type CRS } from '../../lib/utm';
import 'leaflet/dist/leaflet.css';

interface Props {
  fichas: FichaPredio[];
  loading: boolean;
  /** v4.4: datos para la Tarjeta de Predio (clic en polígono) */
  allFichas?: FichaPredio[];
  cultivosData?: any[];
  animalesData?: any[];
}

// ── Tipo para el índice de búsqueda catastral ──
interface CatastroBusqueda {
  fid: number;
  clave_cata: string;
  area_predi: number;
  apellidos: string;
  nombres: string;
  cedula: string;
  comunidad: string;
  lat: number | null;
  lng: number | null;
}

// ── Icono pulsante para el marcador de búsqueda ──
const pulseIcon = L.divIcon({
  className: '',
  html: `<div class="search-pulse-marker">
    <div class="search-pulse-ring"></div>
    <div class="search-pulse-dot"></div>
  </div>`,
  iconSize: [24, 24],
  iconAnchor: [12, 12],
});

// ── Leyenda ──────────────────────────────────────────────────────────
function MapLegend({ showAll, onToggleAll, allLoaded, showOtros, onToggleOtros, showHijas, onToggleHijas, totalHijasPendientes }: {
  showAll: boolean;
  onToggleAll: () => void;
  allLoaded: boolean;
  showOtros: boolean;
  onToggleOtros: () => void;
  showHijas: boolean;
  onToggleHijas: () => void;
  totalHijasPendientes: number;
}) {
  const [show, setShow] = useState(true);
  return (
    <div className="absolute bottom-4 right-4 z-[1000]">
      <button
        onClick={() => setShow(!show)}
        className="mb-1 p-1.5 rounded-md border cursor-pointer shadow"
        style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)', color: 'var(--text-secondary)' }}
      >
        {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
      </button>
      {show && (
        <div className="rounded-lg border p-3 max-w-[210px] shadow-lg"
          style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}>
          <p className="text-[10px] font-semibold mb-2 uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Técnicos</p>
          <div className="space-y-1.5">
            {Array.from(new Set(Object.values(TECNICOS).map((t) => t.nombre)))
              .sort()
              .map((nombre) => {
                const tec = Object.values(TECNICOS).find((t) => t.nombre === nombre);
                if (!tec) return null;
                return (
                  <div key={nombre} className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full shrink-0 border border-white/20" style={{ background: tec.color }} />
                    <span className="text-[10px] truncate" style={{ color: 'var(--text-secondary)' }}>{nombre}</span>
                  </div>
                );
              })}
          </div>
          {totalHijasPendientes > 0 && (
            <div className="mt-2 pt-2 border-t" style={{ borderColor: 'var(--border-color)' }}>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showHijas}
                  onChange={onToggleHijas}
                  className="w-3 h-3 rounded accent-slate-300 cursor-pointer"
                />
                <div className="w-3 h-3 rounded-full shrink-0 bg-white" style={{ border: '1.5px dashed #334155' }} />
                <div>
                  <span className="text-[10px] font-medium" style={{ color: 'var(--text-secondary)' }}>
                    Fichas hijas pendientes
                  </span>
                  <span className="text-[8px] block" style={{ color: 'var(--text-muted)' }}>
                    {totalHijasPendientes.toLocaleString('es-EC')} pendientes de Sección 4
                  </span>
                </div>
              </label>
            </div>
          )}
          <div className="mt-3 pt-2 border-t space-y-1.5" style={{ borderColor: 'var(--border-color)' }}>
            <p className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Capas</p>
            <div className="flex items-center gap-2">
              <div className="w-3 h-2 rounded-sm border border-orange-400/60" style={{ background: 'rgba(249,115,22,0.15)' }} />
              <span className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>Catastro investigado</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-5 h-0.5 rounded" style={{ background: '#38bdf8' }} />
              <span className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>Canales de riego</span>
            </div>
            <label className="flex items-center gap-2 cursor-pointer mt-1 pt-1 border-t" style={{ borderColor: 'var(--border-color)' }}>
              <input
                type="checkbox"
                checked={showOtros}
                onChange={onToggleOtros}
                className="w-3 h-3 rounded accent-blue-400 cursor-pointer"
              />
              <div>
                <span className="text-[10px] font-medium" style={{ color: showOtros ? '#3b82f6' : 'var(--text-secondary)' }}>
                  Otros Predios del Regante
                </span>
                <span className="text-[8px] block" style={{ color: 'var(--text-muted)' }}>
                  Polígonos adicionales del catastro
                </span>
              </div>
            </label>
            {/* Toggle: Todos los predios */}
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={showAll}
                onChange={onToggleAll}
                disabled={!allLoaded}
                className="w-3 h-3 rounded accent-cyan-400 cursor-pointer"
              />
              <div>
                <span className="text-[10px] font-medium" style={{ color: showAll ? '#06b6d4' : 'var(--text-secondary)' }}>
                  Todos los predios
                </span>
                <span className="text-[8px] block" style={{ color: 'var(--text-muted)' }}>
                  {allLoaded ? '24K polígonos (Canvas)' : 'Cargando...'}
                </span>
              </div>
            </label>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Capa de TODOS los polígonos catastrales (24K, Canvas renderer) ──
function AllCatastroLayer({ data }: { data: FeatureCollection }) {
  const map = useMap();
  const layerRef = useRef<L.GeoJSON | null>(null);

  useEffect(() => {
    // Crear capa con Canvas renderer para rendimiento óptimo
    layerRef.current = L.geoJSON(data as any, {
      renderer: L.canvas({ padding: 0.5 }),
      style: {
        color: '#94a3b8',
        weight: 0.8,
        fillColor: '#e2e8f0',
        fillOpacity: 0.04,
        opacity: 0.5,
      },
      interactive: false, // Sin eventos = máximo rendimiento
    } as any);
    layerRef.current.addTo(map);
    // Insertar debajo de las demás capas
    layerRef.current.bringToBack();

    return () => {
      if (layerRef.current) {
        map.removeLayer(layerRef.current);
        layerRef.current = null;
      }
    };
  }, [data, map]);

  return null;
}

// ── FlyTo: volar al predio seleccionado (zoom 18 = escala de predio) ──
function FlyToFicha({ ficha }: { ficha: FichaPredio | null }) {
  const map = useMap();
  const hasFlown = useRef<string | null>(null);

  useEffect(() => {
    if (!ficha) { hasFlown.current = null; return; }
    if (hasFlown.current === ficha.id) return;

    let lat: number | undefined, lng: number | undefined;
    if (ficha.geo && ficha.geo.lat != null && ficha.geo.lng != null) {
      lat = ficha.geo.lat;
      lng = ficha.geo.lng;
    } else if (ficha._geojson?.coordinates) {
      lng = ficha._geojson.coordinates[0] as number;
      lat = ficha._geojson.coordinates[1] as number;
    }

    if (lat == null || lng == null) return;

    hasFlown.current = ficha.id;

    const timer = setTimeout(() => {
      try {
        map.setView([lat!, lng!], 18, { animate: false });
        setTimeout(() => {
          map.flyTo([lat!, lng!], 18, { duration: 1.2 });
        }, 100);
      } catch {
        map.setView([lat!, lng!], 18);
      }
    }, 400);

    return () => clearTimeout(timer);
  }, [ficha, map]);

  return null;
}

// ── FitBounds: ajuste inicial solo si NO hay ficha seleccionada ──
function FitBounds({ fichas, skip }: { fichas: FichaPredio[]; skip: boolean }) {
  const map = useMap();
  const fitted = useRef(false);

  useEffect(() => {
    if (skip) return;
    if (fitted.current || fichas.length === 0) return;

    const timer = setTimeout(() => {
      if (skip) return;
      const pts = fichas
        .filter((f) => (f.geo && f.geo.lat != null) || f._geojson?.coordinates)
        .map((f): [number, number] | null => {
          if (f.geo) return [f.geo.lat, f.geo.lng];
          if (f._geojson?.coordinates) return [f._geojson.coordinates[1] as number, f._geojson.coordinates[0] as number];
          return null;
        }).filter(Boolean) as [number, number][];
      if (pts.length > 0) {
        try { map.fitBounds(pts as any, { padding: [60, 60] }); fitted.current = true; } catch {}
      }
    }, 200);

    return () => clearTimeout(timer);
  }, [fichas, map, skip]);

  return null;
}

// ── Visor de coordenadas del mouse ───────────────────────────
function MouseCoordinates() {
  const map = useMap();
  const [pos, setPos] = useState<{ lat: number; lng: number } | null>(null);
  const [crs, setCrs] = useState<CRS>('wgs84');

  useEffect(() => {
    const handler = (e: LeafletMouseEvent) => setPos(e.latlng);
    map.on('mousemove', handler);
    map.on('mouseout', () => setPos(null));
    return () => { map.off('mousemove', handler); map.off('mouseout'); };
  }, [map]);

  if (!pos) return null;

  const utmCoords = wgs84ToUtm17S(pos.lat, pos.lng);

  return (
    <div
      className="absolute bottom-3 left-3 z-[1000] rounded-lg border px-3 py-1.5 shadow-lg backdrop-blur-sm flex items-center gap-3"
      style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
    >
      <div className="text-[11px] font-mono" style={{ color: 'var(--text-primary)' }}>
        {crs === 'utm17s' ? (
          <span>E <b>{utmCoords.este.toFixed(1)}</b>  N <b>{utmCoords.norte.toFixed(1)}</b></span>
        ) : (
          <span>
            <b>{Math.abs(pos.lat).toFixed(6)}°</b> {pos.lat >= 0 ? 'N' : 'S'}{' '}
            <b>{Math.abs(pos.lng).toFixed(6)}°</b> {pos.lng >= 0 ? 'E' : 'W'}
          </span>
        )}
      </div>
      <button
        onClick={() => setCrs(crs === 'wgs84' ? 'utm17s' : 'wgs84')}
        className="px-1.5 py-0.5 rounded text-[9px] font-bold border cursor-pointer transition-colors"
        style={{
          background: 'var(--bg-input)',
          borderColor: 'var(--border-input)',
          color: 'var(--text-secondary)',
        }}
        title={crs === 'wgs84' ? 'Cambiar a UTM 17S' : 'Cambiar a WGS84'}
      >
        {crs === 'wgs84' ? 'WGS84' : 'UTM 17S'}
      </button>
    </div>
  );
}

// ── FlyToSearch: volar al resultado de búsqueda ──
function FlyToSearch(
  { searchTarget, polygonData }: {
    searchTarget: CatastroBusqueda | null;
    polygonData: FeatureCollection | null;
  }
) {
  const map = useMap();

  // Volar cuando hay polígono disponible (prioridad)
  useEffect(() => {
    if (!searchTarget || !polygonData || polygonData.features.length === 0) return;
    try {
      const geoLayer = L.geoJSON(polygonData);
      const bounds = geoLayer.getBounds();
      if (bounds.isValid()) {
        map.fitBounds(bounds, { padding: [60, 60], maxZoom: 18, animate: true });
      }
    } catch {}
  }, [polygonData, map]); // Solo cuando polygonData cambia

  // Fallback: volar al centroide si no hay polígono
  useEffect(() => {
    if (!searchTarget || searchTarget.lat == null || searchTarget.lng == null) return;
    // Dar tiempo a que se cargue el polígono, si no llegó, volar al centroide
    const timer = setTimeout(() => {
      try {
        map.flyTo([searchTarget.lat!, searchTarget.lng!], 18, { duration: 1.5 });
      } catch {
        map.setView([searchTarget.lat!, searchTarget.lng!], 18);
      }
    }, 500);
    return () => clearTimeout(timer);
  }, [searchTarget, map]); // Solo cuando searchTarget cambia

  return null;
}

// ── Buscador de predios catastrales ──────────────────────────
function MapSearchBar({ onSelect }: { onSelect: (item: CatastroBusqueda) => void }) {
  const [query, setQuery] = useState('');
  const [data, setData] = useState<CatastroBusqueda[]>([]);
  const [focused, setFocused] = useState(false);
  const [loading, setLoading] = useState(true);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetch(`/geo/catastro_busqueda.json?t=${Date.now()}`)
      .then((r) => r.json())
      .then((d: CatastroBusqueda[]) => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const results = useMemo(() => {
    if (!query || query.length < 2) return [];
    const q = query.toLowerCase().trim();
    const matches: CatastroBusqueda[] = [];
    for (const item of data) {
      if (matches.length >= 10) break;
      if (
        item.clave_cata?.toLowerCase().includes(q) ||
        item.apellidos?.toLowerCase().includes(q) ||
        item.nombres?.toLowerCase().includes(q) ||
        item.cedula?.includes(q) ||
        item.comunidad?.toLowerCase().includes(q)
      ) {
        if (item.lat != null && item.lng != null) {
          matches.push(item);
        }
      }
    }
    return matches;
  }, [query, data]);

  const handleSelect = useCallback((item: CatastroBusqueda) => {
    setQuery(`${item.apellidos} ${item.nombres}`.trim());
    setFocused(false);
    onSelect(item);
  }, [onSelect]);

  const clearSearch = useCallback(() => {
    setQuery('');
    setFocused(false);
    inputRef.current?.blur();
  }, []);

  return (
    <div
      className="absolute top-3 left-14 z-[1000] w-[340px] max-w-[calc(100vw-120px)]"
      onFocus={() => setFocused(true)}
      onBlur={(e) => {
        // Delay para permitir click en resultado
        setTimeout(() => {
          if (!e.currentTarget.contains(document.activeElement)) {
            setFocused(false);
          }
        }, 200);
      }}
    >
      {/* Campo de búsqueda */}
      <div
        className="flex items-center gap-2 rounded-lg border px-3 py-2 shadow-lg backdrop-blur-md"
        style={{
          background: 'var(--bg-secondary)',
          borderColor: focused ? 'rgba(59,130,246,0.5)' : 'var(--border-color)',
          transition: 'border-color 0.2s',
        }}
      >
        <Search className="w-4 h-4 shrink-0" style={{ color: 'var(--text-muted)' }} />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={loading ? 'Cargando predios...' : 'Buscar predio: nombre, cédula, clave...'}
          disabled={loading}
          className="flex-1 text-xs bg-transparent outline-none placeholder-opacity-60"
          style={{ color: 'var(--text-primary)' }}
        />
        {query && (
          <button
            onClick={clearSearch}
            className="p-0.5 rounded hover:bg-white/10 cursor-pointer transition-colors"
          >
            <X className="w-3.5 h-3.5" style={{ color: 'var(--text-muted)' }} />
          </button>
        )}
      </div>

      {/* Resultados desplegables */}
      {focused && results.length > 0 && (
        <div
          className="mt-1 rounded-lg border shadow-xl overflow-hidden max-h-[320px] overflow-y-auto"
          style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
        >
          {results.map((item, i) => (
            <button
              key={`${item.fid}-${i}`}
              className="w-full text-left px-3 py-2.5 border-b cursor-pointer transition-colors hover:brightness-125"
              style={{
                borderColor: 'var(--border-color)',
                background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)',
              }}
              onMouseDown={(e) => { e.preventDefault(); handleSelect(item); }}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="text-xs font-semibold truncate" style={{ color: 'var(--text-primary)' }}>
                    {item.apellidos} {item.nombres}
                  </div>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded" style={{
                      background: 'rgba(249,115,22,0.12)',
                      color: '#fb923c',
                    }}>
                      {item.clave_cata}
                    </span>
                    {item.cedula && (
                      <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
                        CI: {item.cedula}
                      </span>
                    )}
                  </div>
                  {item.comunidad && (
                    <div className="text-[10px] mt-0.5" style={{ color: 'var(--text-muted)' }}>
                      📍 {item.comunidad} — {item.area_predi?.toLocaleString('es-EC')} m²
                    </div>
                  )}
                </div>
                <MapPin className="w-3.5 h-3.5 shrink-0 mt-0.5 text-blue-400" />
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Sin resultados */}
      {focused && query.length >= 2 && results.length === 0 && !loading && (
        <div
          className="mt-1 rounded-lg border px-3 py-3 shadow-xl text-center"
          style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
        >
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>No se encontraron predios</p>
        </div>
      )}
    </div>
  );
}

// ── Marcador de ficha ──
function FichaMarker({ ficha, coords }: { ficha: FichaPredio; coords: [number, number] }) {
  const markerRef = useRef<LeafletCircleMarker | null>(null);
  const { selectedFichaMap } = useMapNav();
  const isSelected = selectedFichaMap?.id === ficha.id;
  const [popupCrs, setPopupCrs] = useState<CRS>('utm17s');

  useEffect(() => {
    if (isSelected && markerRef.current) {
      setTimeout(() => { markerRef.current?.openPopup(); }, 1600);
    }
  }, [isSelected]);

  // Fichas hijas (v4.3): pendiente = BLANCO con borde negro discontinuo;
  // completada = color del técnico que llenó la S4, con borde azul.
  const hijaPendiente = esHijaPendiente(ficha);
  const hijaCompletada = esFichaHija(ficha) && !hijaPendiente;
  const color = hijaPendiente
    ? '#ffffff'
    : getColorTecnico((hijaCompletada && ficha.completado_por) || ficha.creado_por);
  const lat = coords[0];
  const lng = coords[1];
  const utm = wgs84ToUtm17S(lat, lng);

  return (
    <CircleMarker
      ref={markerRef}
      center={coords}
      radius={isSelected ? 11 : 6}
      pathOptions={{
        fillColor: color, fillOpacity: hijaPendiente ? 0.95 : 0.9,
        color: hijaPendiente ? '#1e293b' : hijaCompletada ? '#2563eb' : (isSelected ? '#fff' : 'rgba(255,255,255,0.5)'),
        weight: isSelected ? 3 : (esFichaHija(ficha) ? 1.5 : 1),
        dashArray: hijaPendiente ? '3 3' : undefined,
      }}
    >
      <Tooltip direction="top" offset={[0, -8]} opacity={0.9}>
        <span className="text-xs font-medium">{ficha.propietario || ficha.codigo_final}</span>
      </Tooltip>
      <Popup maxWidth={320}>
        <div className="text-xs space-y-1 min-w-[220px]">
          <div className="font-bold text-sm border-b pb-1 mb-2">
            {ficha.propietario || `${ficha.apellidos} ${ficha.nombres}`}
          </div>
          {esFichaHija(ficha) && (
            <div className={`px-2 py-1 rounded text-[10px] font-bold mb-1 ${
              hijaPendiente ? 'bg-slate-200 text-slate-700' : 'bg-emerald-100 text-emerald-700'
            }`}>
              {hijaPendiente
                ? '⚪ FICHA HIJA — Pendiente Sección 4 (Producción)'
                : '✅ FICHA HIJA — Completada'}
            </div>
          )}
          <div className="grid grid-cols-2 gap-x-3 gap-y-0.5">
            {([
              ['Código', ficha.codigo_final],
              ['Cédula', ficha.cedula],
              ['Parroquia', ficha.parroquia],
              ['Sector', ficha.sector],
              ['Comunidad', ficha.comunidad],
              ['Área', ficha.area_total ? `${ficha.area_total.toLocaleString('es-EC')} m²` : null],
              ['Caudal', ficha.caudal_valor ? `${ficha.caudal_valor} l/s` : null],
              ['Cota', ficha.cota_msnm ? `${ficha.cota_msnm} msnm` : null],
              ['Técnico', getNombreTecnico(ficha.creado_por)],
              ['Fecha', safeToDate(ficha.fecha_creacion).toLocaleDateString('es-EC')],
            ] as [string, string | null][]).filter(([, v]) => v).map(([label, val]) => (
              <div key={label} className="contents">
                <span className="opacity-60">{label}:</span>
                <span className="font-medium">{val}</span>
              </div>
            ))}
          </div>

          {/* ── Coordenadas con toggle UTM/WGS84 ── */}
          <div className="mt-2 pt-2 border-t" style={{ borderColor: '#e5e7eb40' }}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] font-semibold uppercase tracking-wider opacity-60">Coordenadas</span>
              <button
                onClick={(e) => { e.stopPropagation(); setPopupCrs(popupCrs === 'wgs84' ? 'utm17s' : 'wgs84'); }}
                className="px-1.5 py-0.5 rounded text-[9px] font-bold border cursor-pointer hover:opacity-80"
                style={{ borderColor: '#9ca3af40' }}
              >
                {popupCrs === 'utm17s' ? 'UTM 17S' : 'WGS84'}
              </button>
            </div>
            {popupCrs === 'utm17s' ? (
              <div className="font-mono text-[11px] grid grid-cols-2 gap-x-2">
                <span className="opacity-50">Este:</span>
                <span className="font-semibold">{utm.este.toFixed(2)} m</span>
                <span className="opacity-50">Norte:</span>
                <span className="font-semibold">{utm.norte.toFixed(2)} m</span>
              </div>
            ) : (
              <div className="font-mono text-[11px] grid grid-cols-2 gap-x-2">
                <span className="opacity-50">Latitud:</span>
                <span className="font-semibold">{lat.toFixed(6)}°</span>
                <span className="opacity-50">Longitud:</span>
                <span className="font-semibold">{lng.toFixed(6)}°</span>
              </div>
            )}
          </div>
        </div>
      </Popup>
    </CircleMarker>
  );
}

// ── ZoomTracker: escucha y actualiza el nivel de zoom del mapa ──
function ZoomTracker({ onChange }: { onChange: (zoom: number) => void }) {
  const map = useMap();
  useEffect(() => {
    const handler = () => {
      onChange(map.getZoom());
    };
    map.on('zoomend', handler);
    handler(); // Inicializar
    return () => {
      map.off('zoomend', handler);
    };
  }, [map, onChange]);
  return null;
}

// ══════════════════════════════════════════════════════════════
// Componente Principal del Mapa
// ══════════════════════════════════════════════════════════════

export default function MapPage({ fichas, loading, allFichas, cultivosData = [], animalesData = [] }: Props) {
  const { selectedFichaMap, clearMapSelection } = useMapNav();

  // ── v4.4: Índices en memoria para la Tarjeta de Predio ──
  // Se calculan una sola vez por cambio de datos; el clic sobre cualquiera de
  // los 5.310 polígonos resuelve en O(1) sin recorrer listas.
  const fichasBase = allFichas && allFichas.length > 0 ? allFichas : fichas;
  const fichasPorClave = useMemo(() => {
    const m = new Map<string, FichaPredio[]>();
    for (const f of fichasBase) {
      const clave = (f.clave_catastral || '').trim();
      if (!clave) continue;
      const arr = m.get(clave);
      if (arr) arr.push(f); else m.set(clave, [f]);
    }
    // Fichas principales primero, hijas después (orden de presentación)
    for (const arr of m.values()) {
      arr.sort((a, b) => Number(esFichaHija(a)) - Number(esFichaHija(b)));
    }
    return m;
  }, [fichasBase]);

  const cultivosPorFicha = useMemo(() => {
    const m = new Map<string, any[]>();
    for (const c of cultivosData) {
      if (!c.ficha_id) continue;
      const arr = m.get(c.ficha_id);
      if (arr) arr.push(c); else m.set(c.ficha_id, [c]);
    }
    return m;
  }, [cultivosData]);

  const animalesPorFicha = useMemo(() => {
    const m = new Map<string, any[]>();
    for (const a of animalesData) {
      if (!a.ficha_id) continue;
      const arr = m.get(a.ficha_id);
      if (arr) arr.push(a); else m.set(a.ficha_id, [a]);
    }
    return m;
  }, [animalesData]);

  // Refs para que los handlers de Leaflet (ligados una sola vez) lean datos frescos
  const indicesRef = useRef({ fichasPorClave, cultivosPorFicha, animalesPorFicha });
  useEffect(() => {
    indicesRef.current = { fichasPorClave, cultivosPorFicha, animalesPorFicha };
  }, [fichasPorClave, cultivosPorFicha, animalesPorFicha]);

  // Predio seleccionado (clic en polígono) y ficha abierta en modal
  const [predioSeleccionado, setPredioSeleccionado] = useState<{
    props: any; latlng: [number, number];
  } | null>(null);
  const [fichaModal, setFichaModal] = useState<FichaPredio | null>(null);
  const [catastroData, setCatastroData] = useState<FeatureCollection | null>(null);
  const [ramalesData, setRamalesData] = useState<FeatureCollection | null>(null);
  const [comunidadesData, setComunidadesData] = useState<FeatureCollection | null>(null);
  const [sectoresData, setSectoresData] = useState<FeatureCollection | null>(null);
  const [layerInfo, setLayerInfo] = useState({ catastro: 0, ramales: 0 });

  const [searchTarget, setSearchTarget] = useState<CatastroBusqueda | null>(null);
  const poligonosRef = useRef<Record<string, Geometry> | null>(null);
  const [poligonosLoaded, setPoligonosLoaded] = useState(false);
  const [searchPolygonGeo, setSearchPolygonGeo] = useState<FeatureCollection | null>(null);
  const [showAllCatastro, setShowAllCatastro] = useState(false);
  const [showOtrosPredios, setShowOtrosPredios] = useState(true); // Visible por defecto
  const [showHijasPendientes, setShowHijasPendientes] = useState(true); // Fichas hijas ⚪ visibles por defecto
  const [currentZoom, setCurrentZoom] = useState(13);

  // FeatureCollection memoizado de TODOS los polígonos (para capa Canvas)
  const allCatastroFC = useMemo<FeatureCollection | null>(() => {
    if (!poligonosRef.current) return null;
    const features = Object.entries(poligonosRef.current).map(([fid, geom]) => ({
      type: 'Feature' as const,
      properties: { fid: Number(fid) },
      geometry: geom,
    }));
    return { type: 'FeatureCollection', features } as FeatureCollection;
  }, [poligonosLoaded]); // eslint-disable-line react-hooks/exhaustive-deps

  // Cargar capas base (catastro investigado + ramales)
  useEffect(() => {
    const timestamp = Date.now();
    fetch(`/geo/catastro_geo.geojson?t=${timestamp}`)
      .then((r) => r.json())
      .then((data: FeatureCollection) => {
        const valid = data.features?.filter((f) => f.geometry != null) || [];
        setCatastroData({ type: 'FeatureCollection', features: valid });
        setLayerInfo((p) => ({ ...p, catastro: valid.length }));
      }).catch(() => {});

    fetch(`/geo/ramales_riego.geojson?t=${timestamp}`)
      .then((r) => r.json())
      .then((data: FeatureCollection) => {
        const valid = data.features?.filter((f) => f.geometry != null) || [];
        setRamalesData({ type: 'FeatureCollection', features: valid });
        setLayerInfo((p) => ({ ...p, ramales: valid.length }));
      }).catch(() => {});

    // Cargar capas de Comunidades y Sectores (generadas por el script GIS)
    fetch(`/geo/comunidades.geojson?t=${timestamp}`)
      .then((r) => r.json())
      .then((data: FeatureCollection) => {
        const valid = data.features?.filter((f) => f.geometry != null) || [];
        setComunidadesData({ type: 'FeatureCollection', features: valid });
      }).catch(() => {});

    fetch(`/geo/sectores.geojson?t=${timestamp}`)
      .then((r) => r.json())
      .then((data: FeatureCollection) => {
        const valid = data.features?.filter((f) => f.geometry != null) || [];
        setSectoresData({ type: 'FeatureCollection', features: valid });
      }).catch(() => {});

    // Cargar polígonos catastrales en background (lazy, ~4MB gzip)
    fetch(`/geo/catastro_poligonos.json?t=${timestamp}`)
      .then((r) => r.json())
      .then((data: Record<string, Geometry>) => {
        poligonosRef.current = data;
        setPoligonosLoaded(true);
      }).catch(() => {});

    return () => clearMapSelection();
  }, []);

  // Cuando se selecciona un resultado de búsqueda, buscar su polígono
  useEffect(() => {
    if (!searchTarget || !poligonosRef.current) {
      setSearchPolygonGeo(null);
      return;
    }
    const geom = poligonosRef.current[String(searchTarget.fid)];
    if (geom) {
      setSearchPolygonGeo({
        type: 'FeatureCollection',
        features: [{
          type: 'Feature',
          properties: {
            fid: searchTarget.fid,
            clave_cata: searchTarget.clave_cata,
            apellidos: searchTarget.apellidos,
            nombres: searchTarget.nombres,
            comunidad: searchTarget.comunidad,
            area_predi: searchTarget.area_predi,
          },
          geometry: geom,
        }],
      });
    } else {
      setSearchPolygonGeo(null);
    }
  }, [searchTarget, poligonosLoaded]);

  const handleSearchSelect = useCallback((item: CatastroBusqueda) => {
    setSearchTarget(item);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-180px)]">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    );
  }

  const fichasConGeo = fichas.filter((f) => f.geo?.lat || f._geojson?.coordinates);
  const getCoords = (f: FichaPredio): [number, number] => {
    if (f.geo?.lat && f.geo?.lng) return [f.geo.lat, f.geo.lng];
    if (f._geojson?.coordinates) return [f._geojson.coordinates[1] as number, f._geojson.coordinates[0] as number];
    return [0, 0];
  };

  return (
    <div className="relative rounded-xl overflow-hidden border"
      style={{ height: 'calc(100vh - 180px)', borderColor: 'var(--border-color)' }}>

      {/* Stats overlay — dos bloques visuales separados para evitar confusión */}
      <div className="absolute top-16 left-3 z-[1000] rounded-lg border px-3 py-2 shadow-lg backdrop-blur-sm"
        style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}>

        {/* ── Bloque 1: Catastro investigado ── */}
        <p className="text-[9px] font-semibold uppercase tracking-wider mb-1" style={{ color: 'var(--text-muted)' }}>
          Catastro investigado
        </p>
        <div className="flex items-center gap-2 text-xs">
          <MapPin className="w-4 h-4 text-blue-400" />
          <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{fichasConGeo.length} fichas</span>
        </div>
        {layerInfo.catastro > 0 && (
          <div className="flex items-center gap-1.5 text-[10px] mt-1" style={{ color: 'var(--text-muted)' }}>
            <div className="w-2 h-2 rounded-sm border border-orange-400" style={{ background: 'rgba(249,115,22,0.2)' }} />
            {layerInfo.catastro} polígonos en mapa
          </div>
        )}



        {/* ── Ficha seleccionada actualmente ── */}
        {selectedFichaMap && (
          <div className="mt-1.5 pt-1.5 border-t flex items-center gap-1" style={{ borderColor: 'var(--border-color)' }}>
            <MapPin className="w-3 h-3 text-emerald-400" />
            <span className="text-[10px] text-emerald-400 max-w-[160px] truncate">
              {selectedFichaMap.propietario || selectedFichaMap.codigo_final}
            </span>
          </div>
        )}
      </div>

      {/* Buscador de predios catastrales */}
      <MapSearchBar onSelect={handleSearchSelect} />

      <MapContainer center={[0.04, -78.15]} zoom={14} className="h-full w-full">
        {/* ── Basemaps ── */}
        <LayersControl position="topright">
          <LayersControl.BaseLayer checked name="ESRI Satélite">
            <TileLayer
              attribution='&copy; ESRI'
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
              maxZoom={20}
            />
          </LayersControl.BaseLayer>
          <LayersControl.BaseLayer name="ESRI Topográfico">
            <TileLayer
              attribution='&copy; ESRI'
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}"
              maxZoom={20}
            />
          </LayersControl.BaseLayer>

          {/* ── Overlay: Catastro ── */}
          {catastroData && catastroData.features.length > 0 && (
            <LayersControl.Overlay checked name="Catastro Rural">
              <GeoJSON
                data={catastroData}
                style={(feature) => {
                  const isHighlighted = searchTarget &&
                    feature?.properties?.clave_cata === searchTarget.clave_cata;
                  return isHighlighted
                    ? { color: '#facc15', weight: 3, fillColor: '#facc15', fillOpacity: 0.25, opacity: 1 }
                    : { color: '#f97316', weight: 1.5, fillColor: '#f97316', fillOpacity: 0.08, opacity: 0.7 };
                }}
                onEachFeature={(feature, layer) => {
                  const p = feature.properties;
                  if (!p) return;
                  // Tooltip perezoso: se arma al momento de mostrarlo, con los
                  // índices actuales (estado + cultivo principal si existen)
                  layer.bindTooltip(() => {
                    const clave = String(p.clave_cata || '').trim();
                    const { fichasPorClave: fpc, cultivosPorFicha: cpf } = indicesRef.current;
                    const fichasPredio = fpc.get(clave) || [];
                    const f0 = fichasPredio[0];
                    let extra = '';
                    if (f0) {
                      if (esHijaPendiente(f0)) {
                        extra = `<br/><span style="color:#64748b">⚪ Ficha hija — pendiente producción</span>`;
                      } else {
                        const cs = (cpf.get(f0.id) || []);
                        const ppal = cs.find((c: any) => c.es_principal) || cs[0];
                        if (ppal?.tipo_cultivo) extra = `<br/>🌱 ${ppal.tipo_cultivo}`;
                      }
                      if (fichasPredio.length > 1) extra += `<br/><span style="color:#64748b">${fichasPredio.length} fichas en este predio</span>`;
                    }
                    return `<b>${p.apellidos || ''} ${p.nombres || ''}</b><br/>
                       Clave: ${p.clave_cata || '—'}<br/>
                       Área: ${p.area_predi ? Number(p.area_predi).toLocaleString('es-EC') + ' m²' : '—'}${extra}<br/>
                       <span style="color:#3b82f6;font-size:10px">Clic para ver detalles</span>`;
                  }, { sticky: true, opacity: 0.9 });
                  // Clic → abrir la Tarjeta de Predio
                  layer.on('click', (e: LeafletMouseEvent) => {
                    setPredioSeleccionado({
                      props: p,
                      latlng: [e.latlng.lat, e.latlng.lng],
                    });
                  });
                }}
              />
            </LayersControl.Overlay>
          )}

          {/* ── Overlay: Ramales ── */}
          {ramalesData && ramalesData.features.length > 0 && (
            <LayersControl.Overlay checked name="Canales de Riego">
              <GeoJSON
                data={ramalesData}
                style={{ color: '#38bdf8', weight: 2.5, opacity: 0.85, dashArray: '6 3' }}
                onEachFeature={(feature, layer) => {
                  const p = feature.properties;
                  if (p) {
                    const nombre = p.nombre || p.NOMBRE || p.name || p.ramal || Object.values(p)[0];
                    if (nombre) layer.bindTooltip(String(nombre), { sticky: true });
                  }
                }}
              />
            </LayersControl.Overlay>
          )}

          {/* ── Overlay: Sectores de Investigación ── */}
          {sectoresData && sectoresData.features.length > 0 && (
            <LayersControl.Overlay name="Sectores de Investigación">
              <GeoJSON
                key="sectores-layer"
                data={sectoresData}
                style={(feature) => {
                  const sectorColors: Record<string, string> = {
                    'Sector 1': '#8b5cf6',
                    'Sector 2': '#06b6d4',
                    'Sector 3': '#10b981',
                  };
                  const sec = feature?.properties?.sector || '';
                  const color = sectorColors[sec] || '#6b7280';
                  return {
                    color,
                    weight: 2.5,
                    fillColor: color,
                    fillOpacity: 0.10,
                    opacity: 0.85,
                    dashArray: '8 4',
                  };
                }}
                onEachFeature={(feature, layer) => {
                  const p = feature.properties;
                  if (p) {
                    const areaHa = Number(p.area_dissolve_ha || 0).toLocaleString('es-EC', { maximumFractionDigits: 1 });
                    const areaRiego = Number(p.area_riego_ha || 0).toLocaleString('es-EC', { maximumFractionDigits: 1 });
                    const caudal = Number(p.caudal_total_ls || 0).toLocaleString('es-EC', { maximumFractionDigits: 1 });
                    layer.bindTooltip(
                      `<b style="font-size:13px">${p.sector || '—'}</b><br/>
                       <span style="color:#9ca3af">Fichas investigadas:</span> <b>${p.total_fichas || p.fichas_validas || '—'}</b><br/>
                       <span style="color:#9ca3af">Predios en catastro:</span> <b>${p.predios_catastro || '—'}</b><br/>
                       <span style="color:#9ca3af">Área geográfica:</span> <b>${areaHa} ha</b><br/>
                       <span style="color:#9ca3af">Área con riego:</span> <b>${areaRiego} ha</b><br/>
                       <span style="color:#9ca3af">Caudal total:</span> <b>${caudal} l/s</b>`,
                      { sticky: true, opacity: 0.97 }
                    );
                    layer.on('mouseover', function (e: any) {
                      (e.target as any).setStyle({ fillOpacity: 0.25, weight: 3.5 });
                    });
                    layer.on('mouseout', function (e: any) {
                      (e.target as any).setStyle({ fillOpacity: 0.10, weight: 2.5 });
                    });
                  }
                }}
              />
            </LayersControl.Overlay>
          )}

          {/* ── Overlay: Comunidades ── */}
          {comunidadesData && comunidadesData.features.length > 0 && (
            <LayersControl.Overlay name="Comunidades">
              <GeoJSON
                key="comunidades-layer"
                data={comunidadesData}
                style={(feature) => {
                  const sectorColors: Record<string, string> = {
                    'Sector 1': '#f59e0b',
                    'Sector 2': '#ec4899',
                    'Sector 3': '#14b8a6',
                  };
                  const sec = feature?.properties?.sector || '';
                  const color = sectorColors[sec] || '#94a3b8';
                  return {
                    color,
                    weight: 1.8,
                    fillColor: color,
                    fillOpacity: 0.08,
                    opacity: 0.75,
                    dashArray: '4 3',
                  };
                }}
                onEachFeature={(feature, layer) => {
                  const p = feature.properties;
                  if (p) {
                    const areaHa = Number(p.area_dissolve_ha || 0).toLocaleString('es-EC', { maximumFractionDigits: 1 });
                    const areaRiego = Number(p.area_riego_ha || 0).toLocaleString('es-EC', { maximumFractionDigits: 1 });
                    const caudal = Number(p.caudal_total_ls || 0).toLocaleString('es-EC', { maximumFractionDigits: 1 });
                    layer.bindTooltip(
                      `<b style="font-size:13px">${p.comunidad || '—'}</b><br/>
                       <span style="color:#9ca3af">Sector:</span> <b>${p.sector || '—'}</b><br/>
                       <span style="color:#9ca3af">Fichas investigadas:</span> <b>${p.total_fichas || p.fichas_validas || '—'}</b><br/>
                       <span style="color:#9ca3af">Predios en catastro:</span> <b>${p.predios_catastro || '—'}</b><br/>
                       <span style="color:#9ca3af">Área geográfica:</span> <b>${areaHa} ha</b><br/>
                       <span style="color:#9ca3af">Área con riego declarada:</span> <b>${areaRiego} ha</b><br/>
                       <span style="color:#9ca3af">Caudal total:</span> <b>${caudal} l/s</b>`,
                      { sticky: true, opacity: 0.97 }
                    );
                    layer.on('mouseover', function (e: any) {
                      (e.target as any).setStyle({ fillOpacity: 0.22, weight: 3 });
                    });
                    layer.on('mouseout', function (e: any) {
                      (e.target as any).setStyle({ fillOpacity: 0.08, weight: 1.8 });
                    });
                  }
                }}
              />
            </LayersControl.Overlay>
          )}
        </LayersControl>

        {/* ── Fichas: NO dentro de LayersControl para evitar checkboxes ── */}
        <ZoomTracker onChange={setCurrentZoom} />
        <FitBounds fichas={fichasConGeo} skip={!!selectedFichaMap || !!searchTarget} />
        <FlyToFicha ficha={selectedFichaMap} />
        <FlyToSearch searchTarget={searchTarget} polygonData={searchPolygonGeo} />

        {/* ── Fichas: Se ocultan en zoom amplio (< 13) para evitar contaminación visual, excepto la seleccionada ── */}
        {(currentZoom >= 13 || selectedFichaMap) && fichasConGeo.map((ficha) => {
          if (currentZoom < 13 && selectedFichaMap?.id !== ficha.id) return null;
          if (!showHijasPendientes && esHijaPendiente(ficha) && selectedFichaMap?.id !== ficha.id) return null;
          return <FichaMarker key={ficha.id} ficha={ficha} coords={getCoords(ficha)} />;
        })}


        {/* ── Polígono resaltado del resultado de búsqueda ── */}
        {searchPolygonGeo && (
          <GeoJSON
            key={`search-poly-${searchTarget?.fid}`}
            data={searchPolygonGeo}
            style={{
              color: '#06b6d4',
              weight: 3,
              fillColor: '#06b6d4',
              fillOpacity: 0.2,
              opacity: 1,
              dashArray: '0',
            }}
            onEachFeature={(feature, layer) => {
              const p = feature.properties;
              if (p) {
                layer.bindTooltip(
                  `<b>${p.apellidos || ''} ${p.nombres || ''}</b><br/>
                   Clave: ${p.clave_cata || '—'}<br/>
                   Comunidad: ${p.comunidad || '—'}<br/>
                   Área: ${p.area_predi ? Number(p.area_predi).toLocaleString('es-EC') + ' m²' : '—'}`,
                  { sticky: true, opacity: 0.95 }
                );
              }
            }}
          />
        )}

        {/* ── Marcador pulsante del resultado de búsqueda ── */}
        {searchTarget && searchTarget.lat != null && searchTarget.lng != null && (
          <Marker position={[searchTarget.lat, searchTarget.lng]} icon={pulseIcon}>
            <Popup maxWidth={280}>
              <div className="text-xs space-y-1 min-w-[200px]">
                <div className="font-bold text-sm border-b pb-1 mb-2">
                  {searchTarget.apellidos} {searchTarget.nombres}
                </div>
                <div className="grid grid-cols-2 gap-x-3 gap-y-0.5">
                  <span className="opacity-60">Clave:</span>
                  <span className="font-medium font-mono">{searchTarget.clave_cata}</span>
                  {searchTarget.cedula && <>
                    <span className="opacity-60">Cédula:</span>
                    <span className="font-medium">{searchTarget.cedula}</span>
                  </>}
                  <span className="opacity-60">Comunidad:</span>
                  <span className="font-medium">{searchTarget.comunidad || '—'}</span>
                  <span className="opacity-60">Área:</span>
                  <span className="font-medium">{searchTarget.area_predi?.toLocaleString('es-EC')} m²</span>
                </div>
              </div>
            </Popup>
          </Marker>
        )}

        {/* ── Capa de TODOS los 24K polígonos (Canvas renderer, toggle en leyenda) ── */}
        {showAllCatastro && allCatastroFC && <AllCatastroLayer data={allCatastroFC} />}

        <MapLegend
          showAll={showAllCatastro}
          onToggleAll={() => setShowAllCatastro(!showAllCatastro)}
          allLoaded={poligonosLoaded}
          showOtros={showOtrosPredios}
          onToggleOtros={() => setShowOtrosPredios(!showOtrosPredios)}
          showHijas={showHijasPendientes}
          onToggleHijas={() => setShowHijasPendientes(!showHijasPendientes)}
          totalHijasPendientes={fichas.filter(esHijaPendiente).length}
        />
        <MouseCoordinates />

        {/* ── v4.4: Tarjeta de Predio (clic en polígono catastral) ── */}
        {predioSeleccionado && (
          <Popup
            key={`predio-${predioSeleccionado.props.clave_cata}-${predioSeleccionado.latlng.join(',')}`}
            position={predioSeleccionado.latlng}
            maxWidth={310}
            eventHandlers={{ remove: () => setPredioSeleccionado(null) }}
          >
            <PredioPopupCard
              predio={predioSeleccionado.props}
              fichas={fichasPorClave.get(String(predioSeleccionado.props.clave_cata || '').trim()) || []}
              cultivosPorFicha={cultivosPorFicha}
              animalesPorFicha={animalesPorFicha}
              onVerFicha={(f) => setFichaModal(f)}
            />
          </Popup>
        )}
      </MapContainer>

      {/* Modal de ficha completa abierto desde la Tarjeta de Predio */}
      {fichaModal && (
        <FichaDetailModal
          ficha={fichaModal}
          onClose={() => setFichaModal(null)}
          todasFichas={fichasBase}
          onSelectFicha={(f) => setFichaModal(f)}
        />
      )}
    </div>
  );
}
