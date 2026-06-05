import { useEffect, useState, useRef, useMemo, useCallback } from 'react';
import {
  MapContainer, TileLayer, GeoJSON, CircleMarker, Popup,
  LayersControl, useMap, Tooltip, Marker,
} from 'react-leaflet';
import L from 'leaflet';
import type { CircleMarker as LeafletCircleMarker, LeafletMouseEvent } from 'leaflet';
import type { FeatureCollection, Geometry } from 'geojson';
import { Loader2, MapPin, Eye, EyeOff, Search, X } from 'lucide-react';
import { type FichaPredio, safeToDate } from '../../lib/types';
import { getNombreTecnico, getColorTecnico, TECNICOS } from '../../lib/constants';
import { useMapNav } from '../../hooks/useMapNav';
import { wgs84ToUtm17S, type CRS } from '../../lib/utm';
import 'leaflet/dist/leaflet.css';

interface Props {
  fichas: FichaPredio[];
  prediosAdicionalesData?: any[];
  loading: boolean;
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
function MapLegend({ showAll, onToggleAll, allLoaded }: {
  showAll: boolean;
  onToggleAll: () => void;
  allLoaded: boolean;
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

  const color = getColorTecnico(ficha.creado_por);
  const lat = coords[0];
  const lng = coords[1];
  const utm = wgs84ToUtm17S(lat, lng);

  return (
    <CircleMarker
      ref={markerRef}
      center={coords}
      radius={isSelected ? 11 : 6}
      pathOptions={{
        fillColor: color, fillOpacity: 0.9,
        color: isSelected ? '#fff' : 'rgba(255,255,255,0.5)',
        weight: isSelected ? 3 : 1,
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
          <div className="grid grid-cols-2 gap-x-3 gap-y-0.5">
            {([
              ['Código', ficha.codigo_final],
              ['Cédula', ficha.cedula],
              ['Parroquia', ficha.parroquia],
              ['Sector', ficha.sector],
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

export default function MapPage({ fichas, prediosAdicionalesData, loading }: Props) {
  const { selectedFichaMap, clearMapSelection } = useMapNav();
  const [catastroData, setCatastroData] = useState<FeatureCollection | null>(null);
  const [ramalesData, setRamalesData] = useState<FeatureCollection | null>(null);
  const [layerInfo, setLayerInfo] = useState({ catastro: 0, ramales: 0 });
  const [catastroBusqueda, setCatastroBusqueda] = useState<CatastroBusqueda[]>([]);
  const [searchTarget, setSearchTarget] = useState<CatastroBusqueda | null>(null);
  const poligonosRef = useRef<Record<string, Geometry> | null>(null);
  const [poligonosLoaded, setPoligonosLoaded] = useState(false);
  const [searchPolygonGeo, setSearchPolygonGeo] = useState<FeatureCollection | null>(null);
  const [showAllCatastro, setShowAllCatastro] = useState(false);
  const [currentZoom, setCurrentZoom] = useState(13);

  // FeatureCollection memoizado de las geometrías de los predios adicionales (Polígonos Azules)
  const prediosAdicionalesFC = useMemo<FeatureCollection | null>(() => {
    if (!prediosAdicionalesData || !catastroBusqueda.length || !poligonosRef.current) return null;
    
    const polRef = poligonosRef.current; // Capturar la referencia antes del forEach para TS
    const features: any[] = [];
    prediosAdicionalesData.forEach(pa => {
      const cat = catastroBusqueda.find(c => c.clave_cata === pa.clave_catastral_otro);
      if (cat) {
        const geom = polRef[String(cat.fid)];
        if (geom) {
          const mainFicha = fichas.find(f => f.id === pa.ficha_id);
          features.push({
            type: 'Feature' as const,
            properties: {
              ...pa,
              fid: cat.fid,
              propietario_principal: mainFicha ? (mainFicha.propietario || `${mainFicha.apellidos} ${mainFicha.nombres}`) : '—',
              comunidad: cat.comunidad || '—',
              area_predi: cat.area_predi || 0,
            },
            geometry: geom,
          });
        }
      }
    });
    return { type: 'FeatureCollection', features } as FeatureCollection;
  }, [prediosAdicionalesData, catastroBusqueda, poligonosLoaded, fichas]);

  useEffect(() => {
    fetch('/geo/catastro_busqueda.json')
      .then(r => r.json())
      .then(d => setCatastroBusqueda(d))
      .catch(() => {});
  }, []);

  const prediosAdicionalesMarkers = useMemo(() => {
    if (!prediosAdicionalesData || !catastroBusqueda.length) return [];
    const markers: any[] = [];
    prediosAdicionalesData.forEach(pa => {
      const cat = catastroBusqueda.find(c => c.clave_cata === pa.clave_catastral_otro);
      if (cat && cat.lat && cat.lng) {
        const mainFicha = fichas.find(f => f.id === pa.ficha_id);
        if (mainFicha) {
          markers.push({ ...pa, lat: cat.lat, lng: cat.lng, mainFicha });
        }
      }
    });
    return markers;
  }, [prediosAdicionalesData, catastroBusqueda, fichas]);

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

      {/* Stats overlay */}
      <div className="absolute top-16 left-3 z-[1000] rounded-lg border px-3 py-2 shadow-lg backdrop-blur-sm"
        style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}>
        <div className="flex items-center gap-2 text-xs">
          <MapPin className="w-4 h-4 text-blue-400" />
          <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{fichasConGeo.length} fichas</span>
        </div>
        {layerInfo.catastro > 0 && (
          <div className="flex items-center gap-1.5 text-[10px] mt-1" style={{ color: 'var(--text-muted)' }}>
            <div className="w-2 h-2 rounded-sm border border-orange-400" style={{ background: 'rgba(249,115,22,0.2)' }} />
            {layerInfo.catastro} polígonos
          </div>
        )}
        {prediosAdicionalesMarkers.length > 0 && (
          <div className="flex items-center gap-1.5 text-[10px] mt-1" style={{ color: 'var(--text-muted)' }}>
            <div className="w-2 h-2 rounded-full border border-orange-600 bg-orange-500" />
            {prediosAdicionalesMarkers.length} otros predios
          </div>
        )}
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

      <MapContainer center={[0.04, -78.15]} zoom={13} className="h-full w-full">
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
                  // Resaltar el polígono buscado
                  const isHighlighted = searchTarget &&
                    feature?.properties?.clave_cata === searchTarget.clave_cata;
                  return isHighlighted
                    ? { color: '#facc15', weight: 3, fillColor: '#facc15', fillOpacity: 0.25, opacity: 1 }
                    : { color: '#f97316', weight: 1.5, fillColor: '#f97316', fillOpacity: 0.08, opacity: 0.7 };
                }}
                onEachFeature={(feature, layer) => {
                  const p = feature.properties;
                  if (p) {
                    layer.bindTooltip(
                      `<b>${p.apellidos || ''} ${p.nombres || ''}</b><br/>
                       Clave: ${p.clave_cata || '—'}<br/>
                       Área: ${p.area_predi ? Number(p.area_predi).toLocaleString('es-EC') + ' m²' : '—'}`,
                      { sticky: true, opacity: 0.9 }
                    );
                  }
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
        </LayersControl>

        {/* ── Fichas: NO dentro de LayersControl para evitar checkboxes ── */}
        <ZoomTracker onChange={setCurrentZoom} />
        <FitBounds fichas={fichasConGeo} skip={!!selectedFichaMap || !!searchTarget} />
        <FlyToFicha ficha={selectedFichaMap} />
        <FlyToSearch searchTarget={searchTarget} polygonData={searchPolygonGeo} />

        {/* ── Fichas: Se ocultan en zoom amplio (< 14) para evitar contaminación visual, excepto la seleccionada ── */}
        {(currentZoom >= 14 || selectedFichaMap) && fichasConGeo.map((ficha) => {
          if (currentZoom < 14 && selectedFichaMap?.id !== ficha.id) return null;
          return <FichaMarker key={ficha.id} ficha={ficha} coords={getCoords(ficha)} />;
        })}

        {/* ── Marcadores Naranjas: Otros Predios (se ocultan en zoom amplio) ── */}
        {currentZoom >= 14 && prediosAdicionalesMarkers.map((pa, i) => (
          <CircleMarker
            key={`pa-${pa.id_adicional}-${i}`}
            center={[pa.lat, pa.lng]}
            radius={5}
            pathOptions={{
              color: '#ea580c', // naranja oscuro
              fillColor: '#f97316', // naranja brillante
              fillOpacity: 0.8,
              weight: 2
            }}
          >
            <Tooltip sticky>
              <div className="text-xs">
                <b>Predio Adicional</b><br/>
                <b>De:</b> {pa.mainFicha?.apellidos} {pa.mainFicha?.nombres}<br/>
                <b>Clave:</b> {pa.clave_catastral_otro}<br/>
                <b>Área Total:</b> {pa.area_total_otro} m²
              </div>
            </Tooltip>
          </CircleMarker>
        ))}

        {/* ── Polígonos Azules: Otros Predios (se dibujan siempre para impacto territorial) ── */}
        {prediosAdicionalesFC && prediosAdicionalesFC.features.length > 0 && (
          <GeoJSON
            key={`adicionales-poly-${poligonosLoaded ? 'loaded' : 'loading'}`}
            data={prediosAdicionalesFC}
            style={{
              color: '#2563eb', // Azul fuerte (royal blue)
              weight: 2,
              fillColor: '#3b82f6', // Azul claro
              fillOpacity: 0.15,
              opacity: 0.85,
            }}
            onEachFeature={(feature, layer) => {
              const p = feature.properties;
              if (p) {
                layer.bindTooltip(
                  `<b>Predio Adicional (Polígono Azul)</b><br/>
                   <b>Propietario Principal:</b> ${p.propietario_principal || '—'}<br/>
                   <b>Clave Catastral:</b> ${p.clave_catastral_otro || '—'}<br/>
                   <b>Comunidad:</b> ${p.comunidad || '—'}<br/>
                   <b>Área del Lote:</b> ${p.area_predi ? Number(p.area_predi).toLocaleString('es-EC') + ' m²' : '—'}`,
                  { sticky: true, opacity: 0.95 }
                );
              }
            }}
          />
        )}

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
        />
        <MouseCoordinates />
      </MapContainer>
    </div>
  );
}
