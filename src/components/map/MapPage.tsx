import { useEffect, useState, useRef, useMemo, useCallback } from 'react';
import {
  MapContainer, TileLayer, GeoJSON, CircleMarker, Popup,
  LayersControl, useMap, Tooltip, Marker,
} from 'react-leaflet';
import L from 'leaflet';
import type { CircleMarker as LeafletCircleMarker, LeafletMouseEvent } from 'leaflet';
import type { FeatureCollection, Geometry } from 'geojson';
import { Loader2, MapPin, Eye, EyeOff, Search, X, Download } from 'lucide-react';
import { type FichaPredio, safeToDate, esFichaHija, esHijaPendiente, esLoteFraccionamiento, usuarioDeFicha } from '../../lib/types';
import { getNombreTecnico, getColorTecnico, TECNICOS } from '../../lib/constants';
import PredioPopupCard from './PredioPopupCard';
import FichaDetailModal from '../fichas/FichaDetailModal';
import { useMapNav } from '../../hooks/useMapNav';
import { useFiltros } from '../../hooks/useFiltros';
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

// ── Vista «Condición de riego» ───────────────────────────────────────
// Simbología y etiquetas de la clasificación por predio (decisiones de
// JAVIKO, 3-sep-2026): con riego / sin riego / mixto / sin dato.
const CLASES_RIEGO = {
  con_riego: { stroke: '#15803d', fill: '#22c55e', label: 'Con riego' },
  mixto:     { stroke: '#a16207', fill: '#facc15', label: 'Mixto (riega una parte)' },
  sin_riego: { stroke: '#7c2d12', fill: '#c2410c', label: 'Sin riego' },
  sin_dato:  { stroke: '#475569', fill: '#94a3b8', label: 'Sin dato de riego' },
} as const;
type ClaseRiego = keyof typeof CLASES_RIEGO;
type ResumenRiego = Record<ClaseRiego, { predios: number; ha: number }>;

// Relleno de los predios MIXTOS: el polígono se DIVIDE en dos colores según
// el % declarado con riego (aclaración de JAVIKO, 3-sep-2026: no un tono
// intermedio, sino «el 80 % de un color y lo demás de otro»). Se logra con un
// degradado SVG de corte duro: verde desde abajo hasta el % regado, tomate el
// resto. Los <linearGradient> viven en un <svg> oculto (los url(#id) de SVG
// resuelven contra el documento completo) y el fill del polígono los referencia.
function fillMixto(pct: number | null | undefined): string {
  const p = Math.max(0, Math.min(100, Math.round(pct ?? 50)));
  return `url(#mixriego-${p})`;
}
// Swatch de la leyenda: la misma división vertical, al 50 % de ejemplo
const SWATCH_MIXTO = 'linear-gradient(to top, #22c55e 50%, #f97316 50%)';

// ── Leyenda ──────────────────────────────────────────────────────────
function MapLegend({ showAll, onToggleAll, allLoaded, showHijas, onToggleHijas, totalHijasPendientes, tecnicosOcultos, onToggleTecnico, onTodosTecnicos, conteoPorTecnico, modoMapa, resumenRiego, clasesOcultas, onToggleClase }: {
  showAll: boolean;
  onToggleAll: () => void;
  allLoaded: boolean;
  showHijas: boolean;
  onToggleHijas: () => void;
  totalHijasPendientes: number;
  /** v4.6: técnicos cuyos puntos están apagados */
  tecnicosOcultos: Set<string>;
  onToggleTecnico: (nombre: string) => void;
  onTodosTecnicos: (visibles: boolean) => void;
  conteoPorTecnico: Map<string, number>;
  /** Vista activa del catastro: estado de investigación o condición de riego */
  modoMapa: 'estado' | 'riego';
  /** Conteo y superficie catastral por clase de riego (de lo visible) */
  resumenRiego: ResumenRiego;
  /** Clases de riego apagadas por el usuario (solo aplica en vista riego) */
  clasesOcultas: Set<ClaseRiego>;
  onToggleClase: (clase: ClaseRiego) => void;
}) {
  const [show, setShow] = useState(true);
  // En la vista de riego los técnicos no aportan: el grupo arranca plegado
  // (pedido de JAVIKO, 3-sep-2026). El usuario puede desplegarlo a mano.
  const [tecnicosAbiertos, setTecnicosAbiertos] = useState(modoMapa !== 'riego');
  useEffect(() => { setTecnicosAbiertos(modoMapa !== 'riego'); }, [modoMapa]);
  const nombres = Array.from(new Set(Object.values(TECNICOS).map((t) => t.nombre))).sort();
  const algunoOculto = tecnicosOcultos.size > 0;
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
          {/* v4.6: cada técnico se puede apagar y prender. El grupo entero se
              pliega (y arranca plegado en la vista de riego). */}
          <div className="flex items-center justify-between mb-2">
            <button
              onClick={() => setTecnicosAbiertos(!tecnicosAbiertos)}
              className="text-[10px] font-semibold uppercase tracking-wider cursor-pointer flex items-center gap-1"
              style={{ color: 'var(--text-muted)' }}
              title={tecnicosAbiertos ? 'Plegar el grupo de técnicos' : 'Desplegar el grupo de técnicos'}
            >
              <span className="inline-block w-2">{tecnicosAbiertos ? '▾' : '▸'}</span>Técnicos
            </button>
            {tecnicosAbiertos && (
              <button
                onClick={() => onTodosTecnicos(algunoOculto)}
                className="text-[9px] px-1.5 py-0.5 rounded border cursor-pointer hover:brightness-125"
                style={{ borderColor: 'var(--border-color)', color: 'var(--text-secondary)' }}
                title={algunoOculto ? 'Mostrar todos los técnicos' : 'Ocultar todos los técnicos'}
              >
                {algunoOculto ? 'Todos' : 'Ninguno'}
              </button>
            )}
          </div>
          <div className="space-y-1.5" hidden={!tecnicosAbiertos}>
            {nombres.map((nombre) => {
              const tec = Object.values(TECNICOS).find((t) => t.nombre === nombre);
              if (!tec) return null;
              const visible = !tecnicosOcultos.has(nombre);
              const n = conteoPorTecnico.get(nombre) || 0;
              return (
                <label key={nombre} className="flex items-center gap-2 cursor-pointer"
                  title={`${n.toLocaleString('es-EC')} fichas — clic para ${visible ? 'ocultar' : 'mostrar'}`}>
                  <input
                    type="checkbox"
                    checked={visible}
                    onChange={() => onToggleTecnico(nombre)}
                    className="w-3 h-3 rounded cursor-pointer shrink-0"
                    style={{ accentColor: tec.color }}
                  />
                  <div className="w-3 h-3 rounded-full shrink-0 border border-white/20"
                    style={{ background: tec.color, opacity: visible ? 1 : 0.25 }} />
                  <span className="text-[10px] truncate flex-1"
                    style={{ color: 'var(--text-secondary)', opacity: visible ? 1 : 0.45 }}>{nombre}</span>
                  {n > 0 && (
                    <span className="text-[8px] shrink-0" style={{ color: 'var(--text-muted)', opacity: visible ? 1 : 0.45 }}>
                      {n.toLocaleString('es-EC')}
                    </span>
                  )}
                </label>
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
                    Fichas adicionales pendientes
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
            {modoMapa === 'estado' ? (<>
              <div className="flex items-center gap-2">
                <div className="w-3 h-2 rounded-sm border border-orange-400/60" style={{ background: 'rgba(249,115,22,0.35)' }} />
                <span className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>Predio investigado (ficha principal)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-2 rounded-sm border border-blue-500/60" style={{ background: 'rgba(59,130,246,0.35)' }} />
                <span className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>Predio adicional (investigado)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-2 rounded-sm" style={{ background: 'rgba(125,211,252,0.45)', border: '1px solid rgba(14,165,233,0.7)' }} />
                <span className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>Predio adicional (pendiente S4)</span>
              </div>
            </>) : (<>
              {(Object.keys(CLASES_RIEGO) as ClaseRiego[]).map((c) => {
                const info = CLASES_RIEGO[c];
                const r = resumenRiego[c];
                if (c === 'sin_dato' && r.predios === 0) return null;
                const visible = !clasesOcultas.has(c);
                return (
                  <label key={c} className="flex items-center gap-2 cursor-pointer"
                    title={`${r.predios.toLocaleString('es-EC')} predios · ${r.ha.toLocaleString('es-EC', { maximumFractionDigits: 1 })} ha de superficie catastral — clic para ${visible ? 'ocultar' : 'mostrar'} esta clase`}>
                    <input
                      type="checkbox"
                      checked={visible}
                      onChange={() => onToggleClase(c)}
                      className="w-3 h-3 rounded cursor-pointer shrink-0"
                      style={{ accentColor: info.fill }}
                    />
                    <div className="w-3 h-2 rounded-sm shrink-0"
                      style={{
                        background: c === 'mixto' ? SWATCH_MIXTO : info.fill,
                        opacity: visible ? 0.85 : 0.3,
                        border: `1px solid ${info.stroke}`,
                      }} />
                    <span className="text-[10px] flex-1 truncate"
                      style={{ color: 'var(--text-secondary)', opacity: visible ? 1 : 0.45 }}>{info.label}</span>
                    <span className="text-[9px] shrink-0 text-right leading-tight"
                      style={{ color: 'var(--text-muted)', opacity: visible ? 1 : 0.45 }}>
                      {r.predios.toLocaleString('es-EC')}<br />{r.ha.toLocaleString('es-EC', { maximumFractionDigits: 1 })} ha
                    </span>
                  </label>
                );
              })}
              <p className="text-[8px] leading-snug" style={{ color: 'var(--text-muted)' }}>
                Mixto: el polígono se divide según el % declarado — verde la
                parte regada, tomate la parte sin riego.
                Clasificación según lo declarado en las fichas de campo ·
                hectáreas de superficie catastral (polígonos del GAD)
              </p>
            </>)}
            <div className="flex items-center gap-2">
              <div className="w-5 h-0.5 rounded" style={{ background: '#38bdf8' }} />
              <span className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>Canales de riego</span>
            </div>
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
                  {allLoaded ? '24K polígonos — clic para identificar' : 'Cargando...'}
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
// v4.5: clicable — al tocar un polígono sin investigar se muestran sus datos
// básicos del catastro para identificarlo y planificar el alcance.
function AllCatastroLayer({ data, onPolyClick }: {
  data: FeatureCollection;
  onPolyClick?: (fid: number, latlng: [number, number]) => void;
}) {
  const map = useMap();
  const layerRef = useRef<L.GeoJSON | null>(null);
  const clickRef = useRef(onPolyClick);
  useEffect(() => { clickRef.current = onPolyClick; }, [onPolyClick]);

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
      onEachFeature: (feature: any, layer: L.Layer) => {
        layer.on('click', (e: LeafletMouseEvent) => {
          const fid = feature.properties?.fid;
          if (fid != null && clickRef.current) {
            clickRef.current(Number(fid), [e.latlng.lat, e.latlng.lng]);
          }
        });
      },
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
// v4.7: colapsado a un ícono por defecto — desplegado tapaba los popups de los
// predios. Se expande al tocarlo y se repliega al cerrar o al perder el foco
// sin texto.
function MapSearchBar({ onSelect }: { onSelect: (item: CatastroBusqueda) => void }) {
  const [abierto, setAbierto] = useState(false);
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

  useEffect(() => {
    if (abierto) inputRef.current?.focus();
  }, [abierto]);

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
    setAbierto(false);
    inputRef.current?.blur();
  }, []);

  // Colapsado: solo el ícono de lupa
  if (!abierto) {
    return (
      <div className="absolute top-3 left-14 z-[1000]">
        <button
          onClick={() => setAbierto(true)}
          className="p-2.5 rounded-lg border shadow-lg backdrop-blur-md cursor-pointer hover:brightness-110 transition-all"
          style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
          title="Buscar predio por nombre, cédula o clave catastral"
        >
          <Search className="w-4 h-4" style={{ color: 'var(--text-secondary)' }} />
        </button>
      </div>
    );
  }

  return (
    <div
      className="absolute top-3 left-14 z-[1000] w-[340px] max-w-[calc(100vw-120px)]"
      onFocus={() => setFocused(true)}
      onBlur={(e) => {
        // Delay para permitir click en resultado
        setTimeout(() => {
          if (!e.currentTarget.contains(document.activeElement)) {
            setFocused(false);
            // sin texto ni resultado activo, volver al ícono para no tapar el mapa
            if (!inputRef.current?.value) setAbierto(false);
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

// ── Descarga de la entrega cartográfica (v4.6) ──────────────
// Paquete con el GeoPackage y el proyecto QGIS listos para revisar. Se genera
// con scripts/generar_gpkg_cliente.py + generar_proyecto_qgis_cliente.py.
function DescargaGeoPackage() {
  const [info, setInfo] = useState<{ mb: number; fecha: string } | null>(null);
  const [abierto, setAbierto] = useState(false);

  useEffect(() => {
    fetch('/descargas/padron_riego_porotog.zip', { method: 'HEAD' })
      .then((r) => {
        if (!r.ok) return;
        const len = Number(r.headers.get('content-length') || 0);
        const mod = r.headers.get('last-modified');
        setInfo({
          mb: len ? len / (1024 * 1024) : 0,
          fecha: mod ? new Date(mod).toLocaleDateString('es-EC') : '',
        });
      })
      .catch(() => {});
  }, []);

  if (!info) return null;

  return (
    <div className="absolute top-3 right-16 z-[1000]">
      <button
        onClick={() => setAbierto(!abierto)}
        className="flex items-center gap-1.5 px-3 py-2 rounded-lg border shadow-lg backdrop-blur-md text-xs font-medium cursor-pointer hover:brightness-110 transition-all"
        style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)', color: 'var(--text-secondary)' }}
        title="Descargar la cartografía para revisarla en QGIS"
      >
        <Download className="w-3.5 h-3.5 text-emerald-400" />
        QGIS
      </button>

      {abierto && (
        <div className="absolute right-0 mt-1 w-[290px] rounded-lg border shadow-xl p-3"
          style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}>
          <p className="text-xs font-bold mb-1" style={{ color: 'var(--text-primary)' }}>
            Entrega cartográfica
          </p>
          <p className="text-[10px] leading-relaxed mb-2" style={{ color: 'var(--text-muted)' }}>
            Predios con la información de las fichas incorporada, listos para abrir en
            QGIS con su simbología. Incluye el catastro completo, la condición de
            riego por predio, comunas oficiales, sectores y canales de riego.
          </p>
          <div className="text-[10px] mb-2 space-y-0.5" style={{ color: 'var(--text-secondary)' }}>
            <div className="flex justify-between"><span className="opacity-60">Formato:</span><span>GeoPackage + proyecto QGIS</span></div>
            <div className="flex justify-between"><span className="opacity-60">Sistema:</span><span>UTM 17S (EPSG:32717)</span></div>
            {info.mb > 0 && (
              <div className="flex justify-between"><span className="opacity-60">Tamaño:</span><span>{info.mb.toFixed(1)} MB</span></div>
            )}
            {info.fecha && (
              <div className="flex justify-between"><span className="opacity-60">Actualizado:</span><span>{info.fecha}</span></div>
            )}
          </div>
          <a
            href="/descargas/padron_riego_porotog.zip"
            download
            onClick={() => setAbierto(false)}
            className="flex items-center justify-center gap-1.5 w-full px-3 py-2 rounded-md bg-emerald-600 hover:bg-emerald-700 text-white text-[11px] font-bold cursor-pointer"
          >
            <Download className="w-3.5 h-3.5" /> Descargar paquete
          </a>
          <p className="text-[9px] mt-1.5 text-center" style={{ color: 'var(--text-muted)' }}>
            Descomprimir y abrir el archivo .qgz
          </p>
        </div>
      )}
    </div>
  );
}

// ── Marcador de ficha ──
function FichaMarker({ ficha, coords, madre, hijas, onIrAFicha }: {
  ficha: FichaPredio;
  coords: [number, number];
  /** v4.6: ficha madre resuelta (solo para fichas adicionales) */
  madre?: FichaPredio;
  /** v4.6: predios adicionales que declaró este regante (solo fichas principales) */
  hijas?: FichaPredio[];
  onIrAFicha?: (f: FichaPredio) => void;
}) {
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
  // Mismo criterio de autoría que usa la leyenda para apagar técnicos, si no
  // el punto se apagaría con uno y se pintaría con el color de otro.
  const color = hijaPendiente ? '#ffffff' : getColorTecnico(usuarioDeFicha(ficha, madre));
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
                ? '⚪ FICHA ADICIONAL — Pendiente Sección 4 (Producción)'
                : '✅ FICHA ADICIONAL — Completada'}
            </div>
          )}
          {/* v4.6: vínculo con el regante principal (ficha madre) */}
          {esFichaHija(ficha) && madre && (
            <div className="rounded border border-blue-200 bg-blue-50 px-2 py-1.5 mb-1">
              <div className="text-[9px] font-semibold uppercase tracking-wider text-blue-500 mb-0.5">
                Regante principal (ficha madre)
              </div>
              <div className="text-[11px] font-semibold text-blue-900 leading-tight">
                {madre.propietario || `${madre.apellidos || ''} ${madre.nombres || ''}`.trim() || madre.codigo_final}
              </div>
              {madre.clave_catastral && (
                <div className="font-mono text-[10px] text-blue-700">
                  Clave: {madre.clave_catastral}
                </div>
              )}
              <button
                onClick={(e) => { e.stopPropagation(); onIrAFicha?.(madre); }}
                className="mt-1 w-full px-2 py-1 rounded bg-blue-600 hover:bg-blue-700 text-white text-[10px] font-bold cursor-pointer"
              >
                📍 Ir al predio principal
              </button>
            </div>
          )}
          {/* v4.6: lote de fraccionamiento — producción asignada, no levantada */}
          {esLoteFraccionamiento(ficha) && (
            <div className="px-2 py-1 rounded text-[10px] font-bold mb-1 bg-amber-100 text-amber-800">
              📦 LOTE DE FRACCIONAMIENTO
              <span className="block font-normal text-[9px] mt-0.5">
                Producción asignada por criterio técnico — verificar en campo
              </span>
            </div>
          )}
          {/* v4.6: navegación inversa — otros predios declarados por este regante */}
          {!esFichaHija(ficha) && hijas && hijas.length > 0 && (
            <div className="rounded border border-blue-200 bg-blue-50 px-2 py-1.5 mb-1">
              <div className="text-[9px] font-semibold uppercase tracking-wider text-blue-500 mb-1">
                Otros predios declarados ({hijas.length})
              </div>
              <div className="space-y-1 max-h-[112px] overflow-y-auto pr-0.5">
                {hijas.map((h, i) => (
                  <button
                    key={h.id}
                    onClick={(e) => { e.stopPropagation(); onIrAFicha?.(h); }}
                    className="w-full flex items-center justify-between gap-2 px-1.5 py-1 rounded border border-blue-200 bg-white hover:bg-blue-100 cursor-pointer text-left"
                    title="Ver este predio en el mapa"
                  >
                    <span className="text-[10px] text-blue-900 truncate">
                      {i + 1}. {h.comunidad || h.sector || h.codigo_final}
                      {h.area_total ? ` — ${Math.round(h.area_total).toLocaleString('es-EC')} m²` : ''}
                    </span>
                    <span className="shrink-0 text-[9px]">
                      {esHijaPendiente(h) ? '⚪' : '✅'}
                    </span>
                  </button>
                ))}
              </div>
              <div className="text-[8px] text-blue-600 mt-1">
                Declarados en la Sección 7 · clic para ubicarlos
              </div>
            </div>
          )}
          <div className="grid grid-cols-2 gap-x-3 gap-y-0.5">
            {([
              ['Código', ficha.codigo_final],
              ['Clave catastral', ficha.clave_catastral || ficha.cod_poligono],
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
  const { selectedFichaMap, navigateToFichaMap, clearMapSelection } = useMapNav();
  const { hasActiveFilters } = useFiltros();

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

  // v4.6: índice id → ficha (para resolver la ficha madre de una adicional)
  const fichasPorId = useMemo(() => {
    const m = new Map<string, FichaPredio>();
    for (const f of fichasBase) m.set(f.id, f);
    return m;
  }, [fichasBase]);

  // v4.6: índice madre → predios adicionales que declaró (navegación inversa)
  const hijasPorMadre = useMemo(() => {
    const m = new Map<string, FichaPredio[]>();
    for (const f of fichasBase) {
      if (!esFichaHija(f) || !f.ficha_madre_id) continue;
      const arr = m.get(f.ficha_madre_id);
      if (arr) arr.push(f); else m.set(f.ficha_madre_id, [f]);
    }
    return m;
  }, [fichasBase]);

  // v4.6: simbología de predios, igual que QGIS.
  //   TOMATE  → tiene al menos una ficha principal (incluye los predios mixtos)
  //   AZUL    → solo fichas adicionales, todas completadas
  //   CELESTE → solo fichas adicionales y alguna sigue pendiente de Sección 4
  // En los predios con varias adicionales manda lo pendiente: si queda trabajo
  // por hacer el predio no debe leerse como cerrado.
  const estadoPorClave = useMemo(() => {
    const comp = new Map<string, { principal: boolean; pendiente: boolean; completada: boolean }>();
    for (const f of fichasBase) {
      const claves = new Set(
        [f.clave_catastral, f.cod_poligono]
          .map((c) => String(c || '').trim())
          .filter(Boolean)
      );
      for (const clave of claves) {
        const c = comp.get(clave) || { principal: false, pendiente: false, completada: false };
        if (!esFichaHija(f)) c.principal = true;
        else if (esHijaPendiente(f)) c.pendiente = true;
        else c.completada = true;
        comp.set(clave, c);
      }
    }
    const m = new Map<string, 'azul' | 'celeste'>();
    for (const [clave, c] of comp) {
      if (c.principal) continue;              // tomate
      if (c.pendiente) m.set(clave, 'celeste');
      else if (c.completada) m.set(clave, 'azul');
    }
    return m;
  }, [fichasBase]);

  // v4.7: los filtros de la barra (sector, comunidad, técnico, fechas) también
  // apagan los POLÍGONOS, no solo los puntos. Si no hay filtro activo se
  // muestra el catastro completo.
  const clavesFiltradas = useMemo(() => {
    if (fichas.length === fichasBase.length) return null;   // sin filtros
    const s = new Set<string>();
    for (const f of fichas) {
      for (const c of [f.clave_catastral, f.cod_poligono]) {
        const k = String(c || '').trim();
        if (k) s.add(k);
      }
    }
    return s;
  }, [fichas, fichasBase]);

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

  // v4.5: índice catastral fid → atributos (para la tarjeta de predios SIN investigar)
  const busquedaPorFidRef = useRef<Map<number, CatastroBusqueda> | null>(null);
  useEffect(() => {
    fetch(`/geo/catastro_busqueda.json?t=${Date.now()}`)
      .then((r) => r.json())
      .then((d: CatastroBusqueda[]) => {
        busquedaPorFidRef.current = new Map(d.map((item) => [Number(item.fid), item]));
      })
      .catch(() => { busquedaPorFidRef.current = null; });
  }, []);

  // Clic en un polígono de la capa "Todos los predios" (24K): resolver sus
  // atributos catastrales y abrir la Tarjeta de Predio (investigado o no)
  const handleAllCatastroClick = useCallback((fid: number, latlng: [number, number]) => {
    const rec = busquedaPorFidRef.current?.get(fid);
    setPredioSeleccionado({
      props: rec
        ? {
            clave_cata: rec.clave_cata,
            area_predi: rec.area_predi,
            apellidos: rec.apellidos,
            nombres: rec.nombres,
            cedula: rec.cedula,
            comunidad: rec.comunidad,
          }
        : { clave_cata: `(fid ${fid})` },
      latlng,
    });
  }, []);
  const [catastroData, setCatastroData] = useState<FeatureCollection | null>(null);
  const [ramalesData, setRamalesData] = useState<FeatureCollection | null>(null);
  const [sectoresData, setSectoresData] = useState<FeatureCollection | null>(null);
  const [comunasOficialesData, setComunasOficialesData] = useState<FeatureCollection | null>(null);
  const [layerInfo, setLayerInfo] = useState({ catastro: 0, ramales: 0 });

  // v4.7: catastro que se dibuja = catastro cargado ∩ filtros activos
  const catastroVisible = useMemo<FeatureCollection | null>(() => {
    if (!catastroData) return null;
    if (!clavesFiltradas) return catastroData;
    return {
      type: 'FeatureCollection',
      features: catastroData.features.filter((f) =>
        clavesFiltradas.has(String(f.properties?.clave_cata || '').trim())),
    } as FeatureCollection;
  }, [catastroData, clavesFiltradas]);

  // ── Vista «Condición de riego» (decisiones de JAVIKO, 3-sep-2026) ──
  // OJO: estos hooks deben quedar ANTES del `return` por loading de más abajo
  // (un hook después de ese return deja la página en blanco).
  const [modoMapa, setModoMapa] = useState<'estado' | 'riego'>('estado');

  // La clase de cada predio (con_riego / mixto / sin_riego / sin_dato) viene
  // CALCULADA desde el export en catastro_geo.geojson (`clase_riego`, junto a
  // `riego_pct`, `riego_m2` y `sin_riego_m2`): una sola implementación de la
  // regla para la web y el proyecto QGIS del cliente. Umbral de «mixto»: cada
  // lado cuenta solo si alcanza el 5 % del área declarada del predio y 100 m².

  // Clases apagadas desde la leyenda (solo afecta a la vista de riego)
  const [clasesOcultas, setClasesOcultas] = useState<Set<ClaseRiego>>(new Set());
  const toggleClase = useCallback((c: ClaseRiego) => {
    setClasesOcultas((prev) => {
      const n = new Set(prev);
      if (n.has(c)) n.delete(c); else n.add(c);
      return n;
    });
  }, []);

  // Conteo y superficie CATASTRAL (area_predi de los polígonos, la familia que
  // ve el cliente) por clase, sobre lo visible con los filtros de la barra —
  // alimenta la leyenda. Se calcula ANTES de apagar clases, para que el conteo
  // de una clase no desaparezca al ocultarla.
  const resumenRiego = useMemo<ResumenRiego>(() => {
    const r: ResumenRiego = {
      con_riego: { predios: 0, ha: 0 }, mixto: { predios: 0, ha: 0 },
      sin_riego: { predios: 0, ha: 0 }, sin_dato: { predios: 0, ha: 0 },
    };
    if (!catastroVisible) return r;
    for (const f of catastroVisible.features) {
      const c = (f.properties?.clase_riego ?? 'sin_dato') as ClaseRiego;
      r[c].predios += 1;
      r[c].ha += Number(f.properties?.area_predi || 0) / 10000;
    }
    return r;
  }, [catastroVisible]);

  // Lo que de verdad se dibuja: lo visible por filtros menos las clases apagadas
  const catastroDibujado = useMemo<FeatureCollection | null>(() => {
    if (!catastroVisible) return null;
    if (modoMapa !== 'riego' || clasesOcultas.size === 0) return catastroVisible;
    return {
      type: 'FeatureCollection',
      features: catastroVisible.features.filter(
        (f) => !clasesOcultas.has((f.properties?.clase_riego ?? 'sin_dato') as ClaseRiego)),
    } as FeatureCollection;
  }, [catastroVisible, modoMapa, clasesOcultas]);

  // La capa «Comunidades» (dissolve de los predios investigados) se RETIRÓ del
  // control de capas el 3-sep-2026 (decisión de JAVIKO): su límite no era claro
  // y para el territorio ya está «Límites de comunas (oficial)». El archivo
  // comunidades.geojson se sigue generando — lo usan el Diseñador de Impresión
  // y los agregados por comunidad — pero el mapa ya no lo carga.

  const [searchTarget, setSearchTarget] = useState<CatastroBusqueda | null>(null);
  const poligonosRef = useRef<Record<string, Geometry> | null>(null);
  const [poligonosLoaded, setPoligonosLoaded] = useState(false);
  const [searchPolygonGeo, setSearchPolygonGeo] = useState<FeatureCollection | null>(null);
  const [showAllCatastro, setShowAllCatastro] = useState(false);
  const [showHijasPendientes, setShowHijasPendientes] = useState(true); // Fichas hijas ⚪ visibles por defecto
  // v4.6: técnicos apagados desde la leyenda (por nombre, no por usuario).
  // Arrancan TODOS apagados: al entrar, el mapa se lee por los polígonos de
  // predios y no por la nube de puntos de autoría, que satura la vista. Quien
  // necesite ver quién levantó cada ficha los enciende desde la leyenda.
  const [tecnicosOcultos, setTecnicosOcultos] = useState<Set<string>>(
    () => new Set(Object.values(TECNICOS).map((t) => t.nombre))
  );
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

    // Cargar capa de Sectores (generada por el script GIS)
    fetch(`/geo/sectores.geojson?t=${timestamp}`)
      .then((r) => r.json())
      .then((data: FeatureCollection) => {
        const valid = data.features?.filter((f) => f.geometry != null) || [];
        setSectoresData({ type: 'FeatureCollection', features: valid });
      }).catch(() => {});

    // Límite comunal oficial entregado por el contratante. Es OTRA cosa que
    // "Comunidades": ahí el polígono sale del dissolve de los predios
    // investigados; aquí es el límite territorial de la comuna, y una sola
    // comuna puede contener varias de nuestras organizaciones de riego.
    fetch(`/geo/comunas_oficiales.geojson?t=${timestamp}`)
      .then((r) => r.json())
      .then((data: FeatureCollection) => {
        const valid = data.features?.filter((f) => f.geometry != null) || [];
        setComunasOficialesData({ type: 'FeatureCollection', features: valid });
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

  // v4.6: apagar/prender los puntos de cada investigador
  const toggleTecnico = useCallback((nombre: string) => {
    setTecnicosOcultos((prev) => {
      const s = new Set(prev);
      if (s.has(nombre)) s.delete(nombre); else s.add(nombre);
      return s;
    });
  }, []);

  const todosTecnicos = useCallback((visibles: boolean) => {
    setTecnicosOcultos(visibles
      ? new Set()
      : new Set(Object.values(TECNICOS).map((t) => t.nombre)));
  }, []);

  // La ficha es del técnico que la levantó (ver usuarioDeFicha en lib/types).
  // Sin la herencia de la ficha madre, las 732 adicionales generadas por script
  // caían en un autor fantasma 'AUTO-SECCION7' que la leyenda no podía apagar.
  const tecnicoDeFicha = useCallback((f: FichaPredio) => getNombreTecnico(
    usuarioDeFicha(f, f.ficha_madre_id ? fichasPorId.get(f.ficha_madre_id) : undefined)
  ), [fichasPorId]);

  const conteoPorTecnico = useMemo(() => {
    const m = new Map<string, number>();
    for (const f of fichas) {
      const n = tecnicoDeFicha(f);
      m.set(n, (m.get(n) || 0) + 1);
    }
    return m;
  }, [fichas, tecnicoDeFicha]);

  // Desglose para la tarjeta de resumen: "6.826 fichas" solo no dice mucho — el
  // padrón lista regantes (fichas principales) y sus predios adicionales por
  // separado, y son universos que NO se suman entre sí al analizar.
  // Va aquí arriba a propósito: debajo hay un `return` por loading y un hook
  // después de ese return rompe las reglas de hooks (deja la página en blanco).
  const resumenFichas = useMemo(() => {
    let principales = 0, adicionales = 0, pendientes = 0;
    for (const f of fichas) {
      if (!(f.geo?.lat || f._geojson?.coordinates)) continue;
      if (esFichaHija(f)) {
        adicionales++;
        if (esHijaPendiente(f)) pendientes++;
      } else principales++;
    }
    return { principales, adicionales, pendientes };
  }, [fichas]);

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

      {/* Degradados de corte duro para los predios MIXTOS: mixriego-N pinta el
          N % inferior del polígono en verde (parte regada) y el resto en
          tomate. Los referencia fillMixto() vía url(#...); un url de SVG
          resuelve contra el documento, por eso basta este <svg> oculto. */}
      {modoMapa === 'riego' && (
        <svg width="0" height="0" style={{ position: 'absolute' }} aria-hidden="true" focusable="false">
          <defs>
            {Array.from({ length: 101 }, (_, p) => (
              <linearGradient key={p} id={`mixriego-${p}`} x1="0" y1="1" x2="0" y2="0">
                <stop offset={`${p}%`} stopColor="#22c55e" />
                <stop offset={`${p}%`} stopColor="#f97316" />
              </linearGradient>
            ))}
          </defs>
        </svg>
      )}

      {/* Resumen de lo que se está viendo. Va en top-24 y no en top-16: los
          botones de zoom de Leaflet llegan hasta ~70 px y se pisaban. */}
      <div className="absolute top-24 left-3 z-[1000] rounded-lg border px-3 py-2 shadow-lg backdrop-blur-sm max-w-[215px]"
        style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}>

        {/* ── Selector de vista del catastro: investigación vs riego ── */}
        <div className="flex rounded-md overflow-hidden border mb-2 text-[10px] font-medium"
          style={{ borderColor: 'var(--border-color)' }}>
          <button
            onClick={() => setModoMapa('estado')}
            className="flex-1 px-1.5 py-1 cursor-pointer transition-colors"
            style={modoMapa === 'estado'
              ? { background: '#2563eb', color: '#fff' }
              : { background: 'transparent', color: 'var(--text-secondary)' }}
            title="Colorear los predios por su estado de investigación (simbología QGIS)"
          >
            Investigación
          </button>
          <button
            onClick={() => setModoMapa('riego')}
            className="flex-1 px-1.5 py-1 cursor-pointer transition-colors"
            style={modoMapa === 'riego'
              ? { background: '#15803d', color: '#fff' }
              : { background: 'transparent', color: 'var(--text-secondary)' }}
            title="Colorear los predios según su condición de riego declarada en campo: con riego, sin riego o mixto"
          >
            💧 Riego
          </button>
        </div>

        <p className="text-[9px] font-semibold uppercase tracking-wider mb-1.5" style={{ color: 'var(--text-muted)' }}>
          {hasActiveFilters ? 'Resultado del filtro' : 'Padrón levantado'}
        </p>

        {/* ── Fichas: el total y de qué se compone ── */}
        <div className="flex items-baseline gap-1.5" title="Cada ficha es una encuesta levantada en campo con su punto GPS.">
          <MapPin className="w-3.5 h-3.5 text-blue-400 shrink-0 self-center" />
          <span className="text-sm font-bold leading-none" style={{ color: 'var(--text-primary)' }}>
            {fichasConGeo.length.toLocaleString('es-EC')}
          </span>
          <span className="text-[10px] leading-none" style={{ color: 'var(--text-secondary)' }}>
            fichas en el mapa
          </span>
        </div>
        <div className="text-[10px] mt-1 pl-5 leading-snug" style={{ color: 'var(--text-muted)' }}
          title="Los regantes se cuentan por ficha principal. Los predios adicionales son otros lotes del mismo regante: no son personas nuevas y no se suman a las principales.">
          <span style={{ color: 'var(--text-secondary)' }}>{resumenFichas.principales.toLocaleString('es-EC')}</span> de regantes
          {' · '}
          <span style={{ color: 'var(--text-secondary)' }}>{resumenFichas.adicionales.toLocaleString('es-EC')}</span> de predios adicionales
          {resumenFichas.pendientes > 0 && (
            <><br /><span className="inline-block w-1.5 h-1.5 rounded-full bg-white mr-1 align-middle" />
            {resumenFichas.pendientes.toLocaleString('es-EC')} sin producción registrada</>
          )}
        </div>

        {/* ── Leyenda del catastro investigado, con el conteo de vuelta ──
            Se había retirado (9-ago, pedido del contratante: «no cuadra con
            nada»): contaba LOTES mientras el resto del panel cuenta FICHAS,
            y sin esa aclaración el número parecía descuadrado. Vuelve el
            19-ago nombrando la unidad en la misma línea — el mismo criterio
            que ya se usa en el Dashboard para catastral vs declarada. */}
        {layerInfo.catastro > 0 && (
          <div className="mt-2 pt-2 border-t" style={{ borderColor: 'var(--border-color)' }}>
            <div className="flex items-center gap-1.5"
              title="En naranja, los lotes del catastro que tienen al menos una ficha levantada.">
              <div className="w-2.5 h-2.5 rounded-sm border border-orange-400 shrink-0" style={{ background: 'rgba(249,115,22,0.2)' }} />
              <span className="text-sm font-bold leading-none" style={{ color: 'var(--text-primary)' }}>
                {(catastroVisible?.features.length ?? 0).toLocaleString('es-EC')}
              </span>
              <span className="text-[10px] leading-none" style={{ color: 'var(--text-secondary)' }}>
                predios investigados
              </span>
            </div>
            <div className="text-[9px] mt-0.5 pl-4 leading-snug" style={{ color: 'var(--text-muted)' }}>
              {fichasConGeo.length.toLocaleString('es-EC')} fichas sobre {(catastroVisible?.features.length ?? 0).toLocaleString('es-EC')} predios: en los terrenos
              familiares cada heredero llena la suya.
            </div>
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

      {/* v4.6: entrega cartográfica para revisar en QGIS */}
      <DescargaGeoPackage />

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

          {/* ── Overlay: Catastro (respeta los filtros de la barra) ── */}
          {catastroVisible && catastroVisible.features.length > 0 && (
            <LayersControl.Overlay checked name="Catastro Rural">
              <GeoJSON
                key={`catastro-${modoMapa}-${estadoPorClave.size}-${Array.from(clasesOcultas).join('.')}-${catastroDibujado?.features.length ?? 0}`}
                data={catastroDibujado ?? catastroVisible}
                style={(feature) => {
                  const isHighlighted = searchTarget &&
                    feature?.properties?.clave_cata === searchTarget.clave_cata;
                  if (isHighlighted) {
                    return { color: '#facc15', weight: 3, fillColor: '#facc15', fillOpacity: 0.50, opacity: 1 };
                  }
                  const clave = String(feature?.properties?.clave_cata || '').trim();
                  // Vista «Condición de riego»: pinta por clase del predio.
                  // Los mixtos llevan degradado tomate→verde según su % regado.
                  if (modoMapa === 'riego') {
                    const cls = (feature?.properties?.clase_riego ?? 'sin_dato') as ClaseRiego;
                    const c = CLASES_RIEGO[cls];
                    const fill = cls === 'mixto' ? fillMixto(feature?.properties?.riego_pct) : c.fill;
                    return { color: c.stroke, weight: 1.5, fillColor: fill, fillOpacity: 0.5, opacity: 0.9 };
                  }
                  // v4.6: simbología QGIS — azul/celeste según el estado de las adicionales
                  const est = estadoPorClave.get(clave);
                  if (est === 'celeste') {
                    return { color: '#0ea5e9', weight: 1.5, fillColor: '#7dd3fc', fillOpacity: 0.35, opacity: 0.85 };
                  }
                  if (est === 'azul') {
                    return { color: '#2563eb', weight: 1.5, fillColor: '#3b82f6', fillOpacity: 0.35, opacity: 0.85 };
                  }
                  return { color: '#ea580c', weight: 1.5, fillColor: '#f97316', fillOpacity: 0.35, opacity: 0.85 };
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
                        extra = `<br/><span style="color:#64748b">⚪ Ficha adicional — pendiente producción</span>`;
                      } else {
                        const cs = (cpf.get(f0.id) || []);
                        const ppal = cs.find((c: any) => c.es_principal) || cs[0];
                        if (ppal?.tipo_cultivo) extra = `<br/>🌱 ${ppal.tipo_cultivo}`;
                      }
                      if (fichasPredio.length > 1) extra += `<br/><span style="color:#64748b">${fichasPredio.length} fichas en este predio</span>`;
                    }
                    // En la vista de riego el tooltip nombra la clase del predio
                    // (la capa se remonta al cambiar de modo: la clausura es fresca).
                    // En los mixtos detalla cuánto se riega y cuánto no (declarado).
                    let lineaRiego = '';
                    if (modoMapa === 'riego') {
                      const cls = (p.clase_riego ?? 'sin_dato') as ClaseRiego;
                      const cr = CLASES_RIEGO[cls];
                      lineaRiego = `<br/><span style="color:${cr.stroke}">💧 ${cr.label}</span>`;
                      if (cls === 'mixto') {
                        const rm = Number(p.riego_m2 || 0);
                        const sm = Number(p.sin_riego_m2 || 0);
                        const pct = Number(p.riego_pct ?? 0);
                        lineaRiego += `<br/><span style="font-size:10px;color:#64748b">Riega el ${pct.toLocaleString('es-EC', { maximumFractionDigits: 0 })} % de lo declarado</span>` +
                          `<br/><span style="font-size:10px;color:#64748b">Con riego: ${rm.toLocaleString('es-EC', { maximumFractionDigits: 0 })} m² · Sin riego: ${sm.toLocaleString('es-EC', { maximumFractionDigits: 0 })} m² (declarado en ficha)</span>`;
                      }
                    }
                    return `<b>${p.apellidos || ''} ${p.nombres || ''}</b><br/>
                       Clave: ${p.clave_cata || '—'}<br/>
                       Área: ${p.area_predi ? Number(p.area_predi).toLocaleString('es-EC') + ' m²' : '—'}${lineaRiego}${extra}<br/>
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

          {/* La capa «Comunidades» (dissolve) se retiró de aquí el 3-sep-2026:
              ver la nota junto a los estados de capas, más arriba. */}

          {/* ── Overlay: Límites de comunas (capa oficial del contratante) ── */}
          {comunasOficialesData && comunasOficialesData.features.length > 0 && (
            <LayersControl.Overlay name="Límites de comunas (oficial)">
              <GeoJSON
                key="comunas-oficiales-layer"
                data={comunasOficialesData}
                style={{
                  color: '#facc15',
                  weight: 2,
                  fillColor: '#facc15',
                  fillOpacity: 0.05,
                  opacity: 0.9,
                  dashArray: '8 4',
                }}
                onEachFeature={(feature, layer) => {
                  const p = feature.properties;
                  if (!p) return;
                  const area = Number(p.area_comuna_ha || 0).toLocaleString('es-EC', { maximumFractionDigits: 1 });
                  const dentro = Number(p.area_dentro_ha || 0).toLocaleString('es-EC', { maximumFractionDigits: 1 });
                  layer.bindTooltip(
                    `<b style="font-size:13px">${p.comuna || '—'}</b><br/>
                     <span style="color:#9ca3af">Límite comunal oficial</span><br/>
                     <span style="color:#9ca3af">Área de la comuna:</span> <b>${area} ha</b><br/>
                     <span style="color:#9ca3af">Dentro del sistema:</span> <b>${dentro} ha (${p.pct_dentro ?? '—'}%)</b>`,
                    { sticky: true, opacity: 0.97 }
                  );
                  layer.on('mouseover', function (e: any) {
                    (e.target as any).setStyle({ fillOpacity: 0.18, weight: 3 });
                  });
                  layer.on('mouseout', function (e: any) {
                    (e.target as any).setStyle({ fillOpacity: 0.05, weight: 2 });
                  });
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
          // v4.6: técnico apagado en la leyenda (la ficha seleccionada siempre se ve).
          // Las pendientes (punto blanco) tienen su propio interruptor separado
          // ("Fichas adicionales pendientes") y deben seguir visibles aunque se
          // apague el técnico que las levantó.
          if (!esHijaPendiente(ficha) && tecnicosOcultos.has(tecnicoDeFicha(ficha)) && selectedFichaMap?.id !== ficha.id) return null;
          const madre = esFichaHija(ficha) && ficha.ficha_madre_id
            ? fichasPorId.get(ficha.ficha_madre_id)
            : undefined;
          return (
            <FichaMarker
              key={ficha.id}
              ficha={ficha}
              coords={getCoords(ficha)}
              madre={madre}
              hijas={hijasPorMadre.get(ficha.id)}
              onIrAFicha={navigateToFichaMap}
            />
          );
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
                   Área: ${p.area_predi ? Number(p.area_predi).toLocaleString('es-EC') + ' m²' : '—'}<br/>
                   <span style="color:#3b82f6;font-size:10px">Clic para ver detalles</span>`,
                  { sticky: true, opacity: 0.95 }
                );
                // v4.6: el resaltado de búsqueda queda ENCIMA del polígono catastral
                // e intercepta el clic — abrir también la Tarjeta de Predio desde aquí
                layer.on('click', (e: LeafletMouseEvent) => {
                  setPredioSeleccionado({
                    props: p,
                    latlng: [e.latlng.lat, e.latlng.lng],
                  });
                });
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
        {showAllCatastro && allCatastroFC && (
          <AllCatastroLayer data={allCatastroFC} onPolyClick={handleAllCatastroClick} />
        )}

        <MapLegend
          showAll={showAllCatastro}
          onToggleAll={() => setShowAllCatastro(!showAllCatastro)}
          allLoaded={poligonosLoaded}
          showHijas={showHijasPendientes}
          onToggleHijas={() => setShowHijasPendientes(!showHijasPendientes)}
          totalHijasPendientes={fichas.filter(esHijaPendiente).length}
          tecnicosOcultos={tecnicosOcultos}
          onToggleTecnico={toggleTecnico}
          onTodosTecnicos={todosTecnicos}
          conteoPorTecnico={conteoPorTecnico}
          modoMapa={modoMapa}
          resumenRiego={resumenRiego}
          clasesOcultas={clasesOcultas}
          onToggleClase={toggleClase}
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
              resolverMadre={(f) => (f.ficha_madre_id ? fichasPorId.get(f.ficha_madre_id) : undefined)}
              resolverHijas={(f) => hijasPorMadre.get(f.id) || []}
              onIrAMadre={(m) => { setPredioSeleccionado(null); navigateToFichaMap(m); }}
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
