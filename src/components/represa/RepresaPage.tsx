/**
 * Cartografía de la represa de Porotog — vista interna de consultoría.
 *
 * Reúne lo que el consorcio entregó como planos PDF (límite de proyecto, presa,
 * túnel, bancos de materiales, obras) ya georreferenciado, sobre el relieve de
 * la zona. NO es una pantalla para el cliente: la ruta está restringida a los
 * roles `admin` y `tecnico` en App.tsx, igual que Reportes.
 *
 * Las capas se descargan solo cuando se encienden. Con todo activo son unos
 * 2,5 MB; cargarlo de golpe al abrir haría lenta una pantalla que casi siempre
 * se usa mirando dos o tres capas.
 *
 * Trazabilidad de los datos: `scripts/represa/` (numerados del 01 al 05) y el
 * detalle del ajuste en `CARTOGRAFIA REPRESA/procesado/georref_1000.json`.
 */
import { lazy, Suspense, useEffect, useMemo, useRef, useState } from 'react';
import {
  MapContainer, TileLayer, GeoJSON, LayersControl, CircleMarker, Tooltip, useMap,
} from 'react-leaflet';
import L, { type PathOptions } from 'leaflet';
import 'leaflet/dist/leaflet.css';   // cada pantalla con mapa lo importa (igual que MapPage)
import {
  Map as MapIcon, Mountain, Loader2, AlertTriangle, Info, Layers, Droplets, Maximize2,
} from 'lucide-react';
// Segundo corte de carga: quien entre a esta pantalla y se quede en el mapa 2D
// tampoco baja Three.js. Solo se descarga al pulsar «Relieve 3D».
const TerrenoVista3D = lazy(() => import('./TerrenoVista3D'));

interface Capa {
  id: string;
  archivo: string;
  nombre: string;
  estilo: PathOptions;
  activaPorDefecto?: boolean;
  nota?: string;
  /** Bloque del panel: la obra por un lado, el sistema de riego por otro. */
  grupo?: 'obra' | 'sistema';
  /** Colorea cada elemento según su sector de investigación. */
  porSector?: boolean;
  /** Geometría de puntos: se dibuja como círculo, no como marcador con icono. */
  puntos?: boolean;
}

// Colores de los sectores de investigación. Se eligieron fuera de la gama que
// ya usa la obra (rojo el límite, magenta los bancos, celeste las obras) para
// que al superponer ambas cosas se distingan sin tener que leer la leyenda.
const COLOR_SECTOR: Record<string, string> = {
  'Sector 1': '#6366f1',
  'Sector 2': '#14b8a6',
  'Sector 3': '#f472b6',
  'Sin asignar': '#94a3b8',
};

const colorDeSector = (s: unknown) => COLOR_SECTOR[String(s)] ?? COLOR_SECTOR['Sin asignar'];

const CAPAS: Capa[] = [
  {
    id: 'limite', archivo: 'limite_proyecto', nombre: 'Límite de proyecto',
    estilo: { color: '#ef4444', weight: 3, fillOpacity: 0.06 },
    activaPorDefecto: true,
    nota: '63,59 ha · tabla oficial del plano, con el vértice 23 corregido',
  },
  {
    id: 'bancos_sup', archivo: 'bancos_superficie', nombre: 'Bancos de materiales',
    estilo: { color: '#d946ef', weight: 2, fillOpacity: 0.18 },
    activaPorDefecto: true,
    nota: 'superficie estimada por envolvente del sombreado del plano',
  },
  {
    id: 'obras', archivo: 'obras', nombre: 'Obras (captación, túnel, vertedero)',
    estilo: { color: '#38bdf8', weight: 1.5 }, activaPorDefecto: true,
  },
  {
    id: 'area_prot', archivo: 'area_protegida', nombre: 'Parque Nacional Cayambe Coca',
    estilo: { color: '#22c55e', weight: 2, dashArray: '6 4', fillOpacity: 0.05 },
    activaPorDefecto: true,
  },
  {
    id: 'curvas', archivo: 'curvas_cota', nombre: 'Curvas de nivel (con cota)',
    estilo: { color: '#a16207', weight: 0.8 },
    nota: 'solo las curvas cuya cota se pudo determinar sin ambigüedad',
  },
  {
    id: 'hidro', archivo: 'hidrografia', nombre: 'Río, canal y pantanos',
    estilo: { color: '#0ea5e9', weight: 1.6 },
  },
  { id: 'vial', archivo: 'vialidad', nombre: 'Caminos', estilo: { color: '#e5e7eb', weight: 1.4 } },
  { id: 'tuberia', archivo: 'tuberia', nombre: 'Tubería y derecho de paso', estilo: { color: '#f59e0b', weight: 1.4 } },
  {
    id: 'bancos_hatch', archivo: 'bancos_materiales', nombre: 'Sombreado de los bancos (detalle)',
    estilo: { color: '#d946ef', weight: 0.5, opacity: 0.55 },
  },
  { id: 'ejes', archivo: 'ejes', nombre: 'Ejes de replanteo', estilo: { color: '#94a3b8', weight: 0.8 } },
  {
    id: 'gnss', archivo: 'control_gnss', nombre: 'Puntos de control GNSS',
    estilo: { color: '#facc15', weight: 1.5 },
  },
  {
    id: 'dibujado', archivo: 'limite_dibujado', nombre: 'Límite tal como lo dibuja el plano',
    estilo: { color: '#fb7185', weight: 1, dashArray: '3 3' },
    nota: 'para contrastar contra la tabla de coordenadas',
  },

  // ── el sistema de riego al que va a servir la obra ──
  {
    id: 'huella', archivo: 'sectores_huella', nombre: 'Huella de los sectores',
    grupo: 'sistema', porSector: true,
    estilo: { weight: 1.5, fillOpacity: 0.14 },
    nota: 'superficie levantada, por sector de investigación',
  },
  {
    id: 'predios', archivo: 'predios_por_sector', nombre: 'Predios investigados',
    grupo: 'sistema', porSector: true, puntos: true,
    estilo: { weight: 0, fillOpacity: 0.75 },
    nota: '6.825 predios, pintados por sector',
  },
  {
    // única capa que no es del módulo de la represa: es la red de riego que ya
    // exporta el padrón (`export_geojson.py`), y no tiene sentido duplicarla
    id: 'canales', archivo: '/geo/ramales_riego.geojson', nombre: 'Canales de riego',
    grupo: 'sistema',
    estilo: { color: '#22d3ee', weight: 2.5 },
    nota: '41,5 km de la red existente',
  },
];

// Encuadre inicial. No se fija a ojo: en cuanto llega el límite de proyecto el
// mapa se ajusta a su extensión real, así que basta con un punto de partida
// razonable dentro de la zona mientras carga.
const CENTRO: [number, number] = [-0.1447, -78.135];

interface Magnitud {
  represa_ha: number;
  riego_ha: number;
  predios: number;
  ha_regadas_por_ha_de_represa: number;
  sectores: Array<{ sector: string; predios: number; area_riego_ha: number }>;
}

/**
 * Ajusta el encuadre a la extensión del límite de proyecto, una sola vez.
 *
 * El `invalidateSize()` antes del `fitBounds()` no es adorno: el mapa se monta
 * dentro de un contenedor flex que todavía se está midiendo, así que Leaflet
 * cree que es más pequeño de lo que acabará siendo y encuadra mal — el proyecto
 * termina arrinconado en una esquina. Se reajusta también cuando cambia el
 * tamaño del contenedor (al plegar el panel de capas, por ejemplo).
 */
function EncuadrarAlLimite(
  { limite, sistema, modo }: { limite: unknown; sistema: unknown; modo: 'obra' | 'sistema' },
) {
  const mapa = useMap();
  const aplicado = useRef<string | null>(null);

  useEffect(() => {
    // en modo «sistema» se espera a que llegue la huella: encuadrar a la obra y
    // saltar después sería un tirón innecesario
    const objetivo = modo === 'sistema' ? (sistema ?? null) : (limite ?? null);
    if (!objetivo || aplicado.current === modo) return;

    let cancelado = false;
    const encuadrar = () => {
      if (cancelado) return;
      try {
        const caja = L.geoJSON(objetivo as never).getBounds();
        if (modo === 'sistema' && limite) {
          caja.extend(L.geoJSON(limite as never).getBounds());  // que la obra entre
        }
        if (!caja.isValid()) return;
        mapa.invalidateSize();
        // margen corto: con 40 px el contenido quedaba nadando en el mapa,
        // sobre todo en la vista de la obra, que es lo primero que se ve
        mapa.fitBounds(caja, { padding: [12, 12] });
        aplicado.current = modo;
      } catch { /* si falla, se queda el encuadre anterior */ }
    };
    // un frame de margen para que el contenedor tenga ya su tamaño definitivo
    const t = setTimeout(encuadrar, 120);
    return () => { cancelado = true; clearTimeout(t); };
  }, [limite, sistema, modo, mapa]);

  useEffect(() => {
    const contenedor = mapa.getContainer();
    const obs = new ResizeObserver(() => mapa.invalidateSize());
    obs.observe(contenedor);
    return () => obs.disconnect();
  }, [mapa]);

  return null;
}

export default function RepresaPage() {
  const [vista, setVista] = useState<'mapa' | 'relieve'>('mapa');
  const [activas, setActivas] = useState<Set<string>>(
    () => new Set(CAPAS.filter((c) => c.activaPorDefecto).map((c) => c.id)),
  );
  const [datos, setDatos] = useState<Record<string, unknown>>({});
  const [rotulos, setRotulos] = useState<Array<{ nombre: string; lat: number; lon: number }>>([]);
  const [cargando, setCargando] = useState<Set<string>>(new Set());
  const [fallos, setFallos] = useState<Record<string, string>>({});
  const [magnitud, setMagnitud] = useState<Magnitud | null>(null);
  const [encuadre, setEncuadre] = useState<'obra' | 'sistema'>('obra');

  // Descarga perezosa: cada capa se pide la primera vez que se enciende.
  //
  // El registro de «ya pedida» va en un ref y no en el estado a propósito: el
  // estado se aplica en el siguiente render, así que si el efecto vuelve a
  // correr antes (y lo hace: React 19 monta los efectos dos veces en
  // desarrollo) la misma capa se descarga varias veces. Con el ref queda
  // marcada en el acto y cada archivo se pide una sola vez.
  const solicitadas = useRef<Set<string>>(new Set());

  useEffect(() => {
    const pendientes = [...activas].filter((id) => !solicitadas.current.has(id));
    if (!pendientes.length) return;
    pendientes.forEach((id) => solicitadas.current.add(id));
    setCargando((prev) => new Set([...prev, ...pendientes]));

    pendientes.forEach(async (id) => {
      const capa = CAPAS.find((c) => c.id === id);
      if (!capa) return;
      try {
        const ruta = capa.archivo.startsWith('/')
          ? capa.archivo                                   // capa de otro módulo
          : `/geo/represa/${capa.archivo}.geojson`;
        const r = await fetch(ruta);
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const gj = await r.json();
        setDatos((prev) => ({ ...prev, [id]: gj }));
      } catch (e) {
        solicitadas.current.delete(id);   // permitir reintento al reactivarla
        setFallos((prev) => ({
          ...prev, [id]: e instanceof Error ? e.message : 'no se pudo cargar',
        }));
      } finally {
        setCargando((prev) => {
          const s = new Set(prev);
          s.delete(id);
          return s;
        });
      }
    });
  }, [activas]);

  // Los rótulos de obra van siempre: son los que hacen legible el plano.
  useEffect(() => {
    if (solicitadas.current.has('__rotulos')) return;   // ver nota de arriba
    solicitadas.current.add('__rotulos');
    fetch('/geo/represa/rotulos_obra.geojson')
      .then((r) => r.json())
      .then((gj) => {
        const vistos = new Set<string>();
        const pts: Array<{ nombre: string; lat: number; lon: number }> = [];
        for (const f of gj.features ?? []) {
          const nombre = f.properties?.nombre ?? '';
          if (!nombre || vistos.has(nombre)) continue;
          vistos.add(nombre);
          pts.push({ nombre, lat: f.geometry.coordinates[1], lon: f.geometry.coordinates[0] });
        }
        setRotulos(pts);
      })
      .catch(() => setRotulos([]));

    fetch('/geo/represa/magnitud.json')
      .then((r) => r.json())
      .then(setMagnitud)
      .catch(() => setMagnitud(null));
  }, []);

  const alternar = (id: string) => {
    setActivas((prev) => {
      const s = new Set(prev);
      if (s.has(id)) s.delete(id);
      else s.add(id);
      return s;
    });
  };

  const capasVisibles = useMemo(
    () => CAPAS.filter((c) => activas.has(c.id) && datos[c.id]),
    [activas, datos],
  );

  const fila = (c: Capa) => (
    <li key={c.id}>
      <label className="flex items-start gap-2 px-2 py-1.5 rounded-md cursor-pointer hover:bg-white/5">
        <input
          type="checkbox"
          checked={activas.has(c.id)}
          onChange={() => alternar(c.id)}
          className="mt-0.5 cursor-pointer"
        />
        <span className="flex-1 min-w-0">
          <span className="flex items-center gap-2 text-sm" style={{ color: 'var(--text-primary)' }}>
            {c.porSector ? (
              // esta capa no tiene un color: tiene uno por sector
              <span className="flex shrink-0 rounded-sm overflow-hidden">
                {['Sector 1', 'Sector 2', 'Sector 3'].map((s) => (
                  <span key={s} className="w-2 h-3" style={{ background: COLOR_SECTOR[s] }} />
                ))}
              </span>
            ) : (
              <span className="inline-block w-3 h-3 rounded-sm shrink-0"
                    style={{ background: String(c.estilo.color) }} />
            )}
            <span className="truncate">{c.nombre}</span>
            {cargando.has(c.id) && <Loader2 className="w-3 h-3 animate-spin shrink-0" />}
          </span>
          {c.nota && (
            <span className="block text-[11px] mt-0.5" style={{ color: 'var(--text-muted)' }}>
              {c.nota}
            </span>
          )}
          {fallos[c.id] && (
            <span className="block text-[11px] mt-0.5 text-red-400">
              no se pudo cargar ({fallos[c.id]})
            </span>
          )}
        </span>
      </label>
    </li>
  );

  return (
    // Altura explícita, igual que MapPage: el <main> del layout no la fija, y
    // sin esto el mapa y el canvas 3D se quedan en 0 px de alto.
    <div className="flex flex-col rounded-xl overflow-hidden border"
         style={{ height: 'calc(100vh - 180px)', borderColor: 'var(--border-color)' }}>
      {/* Cabecera */}
      <div className="px-4 py-3 border-b flex flex-wrap items-center justify-between gap-3"
           style={{ borderColor: 'var(--border-color)' }}>
        <div>
          <h1 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>
            Represa de Porotog — cartografía del proyecto
          </h1>
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            Planos del Consorcio CCSPT georreferenciados · uso interno de consultoría
          </p>
        </div>
        <div className="flex rounded-lg overflow-hidden border" style={{ borderColor: 'var(--border-color)' }}>
          <button
            onClick={() => setVista('mapa')}
            className={`flex items-center gap-2 px-3 py-1.5 text-sm cursor-pointer ${
              vista === 'mapa' ? 'bg-blue-500/20 text-blue-300' : 'hover:bg-white/5'}`}
            style={{ color: vista === 'mapa' ? undefined : 'var(--text-secondary)' }}
          >
            <MapIcon className="w-4 h-4" /> Mapa
          </button>
          <button
            onClick={() => setVista('relieve')}
            className={`flex items-center gap-2 px-3 py-1.5 text-sm cursor-pointer ${
              vista === 'relieve' ? 'bg-blue-500/20 text-blue-300' : 'hover:bg-white/5'}`}
            style={{ color: vista === 'relieve' ? undefined : 'var(--text-secondary)' }}
          >
            <Mountain className="w-4 h-4" /> Relieve 3D
          </button>
        </div>
      </div>

      <div className="flex-1 flex min-h-0">
        {/* Panel de capas */}
        {vista === 'mapa' && (
          <aside className="w-72 shrink-0 border-r overflow-y-auto hidden md:block"
                 style={{ borderColor: 'var(--border-color)', background: 'var(--bg-secondary)' }}>
            <div className="p-3">
              <div className="flex items-center gap-2 mb-2 text-xs font-semibold uppercase tracking-wider"
                   style={{ color: 'var(--text-muted)' }}>
                <Layers className="w-3.5 h-3.5" /> Capas
              </div>
              <ul className="space-y-1">
                {CAPAS.filter((c) => c.grupo !== 'sistema').map(fila)}
              </ul>

              {/* El sistema de riego al que servirá la obra: es lo que da la
                  medida de la represa. Apagado por defecto — encenderlo cambia
                  la escala del mapa de 1 km a 20 km. */}
              <div className="flex items-center justify-between gap-2 mt-4 mb-2">
                <span className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider"
                      style={{ color: 'var(--text-muted)' }}>
                  <Droplets className="w-3.5 h-3.5" /> Sistema de riego
                </span>
                <button
                  onClick={() => {
                    // «Ver todo» sin la huella encendida no enseñaría nada:
                    // se activa sola y el encuadre espera a que cargue
                    if (encuadre === 'obra') {
                      setActivas((prev) => new Set([...prev, 'huella']));
                      setEncuadre('sistema');
                    } else {
                      setEncuadre('obra');
                    }
                  }}
                  className="flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-md cursor-pointer hover:bg-white/10"
                  style={{ color: 'var(--text-secondary)' }}
                  title="Alternar el encuadre entre la obra y todo el sistema"
                >
                  <Maximize2 className="w-3 h-3" />
                  {encuadre === 'obra' ? 'Ver todo' : 'Ver la obra'}
                </button>
              </div>
              <ul className="space-y-1">
                {CAPAS.filter((c) => c.grupo === 'sistema').map(fila)}
              </ul>

              {magnitud && (
                <div className="mt-3 rounded-lg p-3 text-[11px] leading-relaxed"
                     style={{ background: 'var(--bg-primary)', color: 'var(--text-muted)' }}>
                  <div className="font-semibold mb-1.5" style={{ color: 'var(--text-secondary)' }}>
                    Magnitud del proyecto
                  </div>
                  <div className="flex justify-between"><span>Represa</span>
                    <b>{magnitud.represa_ha.toLocaleString('es-EC')} ha</b></div>
                  <div className="flex justify-between"><span>Superficie bajo riego</span>
                    <b>{magnitud.riego_ha.toLocaleString('es-EC')} ha</b></div>
                  <div className="flex justify-between"><span>Predios investigados</span>
                    <b>{magnitud.predios.toLocaleString('es-EC')}</b></div>
                  <div className="mt-1.5 pt-1.5 border-t" style={{ borderColor: 'var(--border-color)' }}>
                    Por cada hectárea de represa se riegan
                    <b className="text-emerald-400"> {magnitud.ha_regadas_por_ha_de_represa} ha</b>.
                  </div>
                  <ul className="mt-1.5 space-y-0.5">
                    {magnitud.sectores.map((s) => (
                      <li key={s.sector} className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-sm shrink-0"
                              style={{ background: colorDeSector(s.sector) }} />
                        <span className="flex-1">{s.sector}</span>
                        <span>{s.predios.toLocaleString('es-EC')} predios ·
                          {' '}{s.area_riego_ha.toLocaleString('es-EC')} ha</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Ficha de procedencia: quien mire esto tiene que saber de dónde sale */}
              <div className="mt-4 rounded-lg p-3 text-[11px] leading-relaxed"
                   style={{ background: 'var(--bg-primary)', color: 'var(--text-muted)' }}>
                <div className="flex items-center gap-1.5 mb-1.5 font-semibold"
                     style={{ color: 'var(--text-secondary)' }}>
                  <Info className="w-3.5 h-3.5" /> Procedencia y precisión
                </div>
                <p className="mb-1.5">
                  Los planos PDF no traen georreferencia. Se calculó a partir de la tabla
                  de coordenadas del propio plano: <b>RMS 0,216 m</b>, y la escala que
                  resulta del ajuste (1:1.998) coincide con la declarada (1:2.000).
                </p>
                <p className="mb-1.5">
                  Contraste independiente contra las curvas de nivel regionales de 5 m:
                  <b> 3,4 m de diferencia mediana</b> sobre 708 puntos.
                </p>
                <p className="text-amber-400/90 flex gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                  <span>
                    La fila 23 de la tabla del consorcio está equivocada: sitúa el
                    vértice a 2,5 km de donde el propio plano lo dibuja. Aquí se usa la
                    coordenada corregida. Conviene reportárselo.
                  </span>
                </p>
              </div>
            </div>
          </aside>
        )}

        {/* Vista */}
        <div className="flex-1 min-w-0 min-h-0">
          {vista === 'relieve' ? (
            <Suspense fallback={
              <div className="w-full h-full flex items-center justify-center"
                   style={{ background: '#0b1220' }}>
                <Loader2 className="w-7 h-7 text-blue-400 animate-spin" />
              </div>
            }>
              <TerrenoVista3D />
            </Suspense>
          ) : (
            <MapContainer
              center={CENTRO}
              zoom={15}
              // Las obras del plano son más de 3.000 trazos. En SVG eso son
              // 3.000 nodos en el DOM y el mapa se arrastra al hacer zoom; en
              // canvas se dibujan de una pasada y va fluido.
              preferCanvas
              className="h-full w-full"
            >
              <EncuadrarAlLimite
                limite={datos['limite']}
                sistema={datos['huella']}
                modo={encuadre}
              />
              <LayersControl position="topright">
                <LayersControl.BaseLayer checked name="Satélite">
                  <TileLayer
                    attribution="&copy; ESRI"
                    url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                  />
                </LayersControl.BaseLayer>
                <LayersControl.BaseLayer name="Topográfico">
                  <TileLayer
                    attribution="&copy; ESRI"
                    url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}"
                  />
                </LayersControl.BaseLayer>
              </LayersControl>

              {capasVisibles.map((c) => (
                <GeoJSON
                  key={c.id}
                  data={datos[c.id] as never}
                  style={(f) => (c.porSector
                    ? { ...c.estilo,
                        color: colorDeSector(f?.properties?.sector),
                        fillColor: colorDeSector(f?.properties?.sector) }
                    : c.estilo)}
                  pointToLayer={(f, latlng) => L.circleMarker(latlng, {
                    ...c.estilo,
                    radius: 2.5,
                    color: colorDeSector(f?.properties?.sector),
                    fillColor: colorDeSector(f?.properties?.sector),
                  })}
                  onEachFeature={(f, layer) => {
                    const p = (f.properties ?? {}) as Record<string, unknown>;
                    const filas = ['nombre', 'sector', 'comunidad', 'predios',
                                   'area_riego_ha', 'cota', 'area_ha', 'nota', 'fuente']
                      .filter((k) => p[k] !== undefined && p[k] !== null && p[k] !== '')
                      .map((k) => `<div><b>${k}:</b> ${String(p[k])}</div>`);
                    if (filas.length) layer.bindPopup(filas.join(''));
                  }}
                />
              ))}

              {rotulos.map((r) => (
                <CircleMarker
                  key={r.nombre}
                  center={[r.lat, r.lon]}
                  radius={4}
                  pathOptions={{ color: '#facc15', fillColor: '#facc15', fillOpacity: 1 }}
                >
                  <Tooltip direction="top" offset={[0, -4]}>{r.nombre}</Tooltip>
                </CircleMarker>
              ))}
            </MapContainer>
          )}
        </div>
      </div>
    </div>
  );
}
