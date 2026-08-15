/**
 * Auditoría de áreas — pantalla de trabajo del equipo (no la ve el cliente).
 *
 * Para qué sirve
 * --------------
 * La superficie del padrón no cuadra con el catastro del GADM. Esta pantalla
 * muestra, predio por predio, dónde está la diferencia: el polígono catastral
 * contra las fichas que hay encima, sobre el mismo mapa base del resto de la
 * aplicación.
 *
 * De dónde salen los datos
 * ------------------------
 * De `public/geo/auditoria_areas.json`, que genera
 * `scripts/generar_auditoria_areas.py` leyendo el data.gpkg. Se regenera en
 * cada sincronización, así que lo que se ve aquí es el estado real: según se
 * depura, los casos van desapareciendo solos.
 *
 * Lo que más ahorra trabajo
 * -------------------------
 * Muchos predios compartidos traen el área real en las OBSERVACIONES del
 * técnico, no en el campo de área («…solo le corresponde 12.500 m2»). Cuando
 * esas observaciones suman el polígono, el caso se cierra copiando el dato y
 * la ficha aparece marcada como resuelta. Por eso las observaciones se
 * muestran completas y con el área resaltada.
 */
import { useEffect, useMemo, useState } from 'react';
import {
  MapContainer, TileLayer, LayersControl, Polygon, Polyline, CircleMarker,
  Tooltip, useMap,
} from 'react-leaflet';
import type { LatLngExpression } from 'leaflet';
import 'leaflet/dist/leaflet.css';   // cada pantalla con mapa lo importa (igual que MapPage)
import {
  AlertTriangle, CheckCircle2, Layers, MapPin, Phone, Ruler, Search, FileText,
  PanelLeftClose, PanelLeftOpen,
} from 'lucide-react';

type Ficha = {
  n: string; ced: string; tel: string;
  a: number; ar: number; asr: number;
  tec: string; f: string; p: number;
  lon: number | null; lat: number | null;
  obs?: string; oa?: number;
};
type Vecina = { com: string; lon: number; lat: number; d: number };
type Caso = {
  clave: string;
  tipo: 'exceso' | 'dividido' | 'triple' | 'clave_mala' | 'sin_comunidad' | 'cultivo';
  com: string; sec: string;
  pol: number; dec: number; exc: number; nf: number;
  fichas: Ficha[];
  // solo en los casos de producción: lo sembrado, cuántas veces el predio y qué
  cul?: number; factor?: number; items?: { t: string; m2: number }[];
  geo?: [number, number][];
  triple?: number;
  obs_n?: number; obs_suma?: number; resuelto_por_obs?: boolean; falta?: string;
  digitos?: number;
  // en qué quedó su análisis (claves inexistentes y fichas sin comunidad)
  estado?: string; propuesta?: string; dif?: string;
  area_confirma?: boolean; area_pol?: number; nota?: string;
  via?: string; vecinas?: Vecina[]; uid?: string;
};
type Datos = {
  generado: string; corte: string;
  corregido?: {
    total_fichas: number; con_comunidad: number;
    clave_valida: number; area_cuadra: number;
  };
  resumen: {
    fichas: number; exceso: number; dividido: number; triple: number;
    triple_solo: number; clave_mala: number; exc_ha: number;
    con_obs: number; resueltos_por_obs: number;
    sin_comunidad: number; com_propuesta: number; com_revisar: number;
    cultivo?: number; cultivo_exc_ha?: number;
  };
  casos: Caso[];
  canal: [number, number][][];
};

/** Identifica un caso sin ambigüedad: la clave no basta cuando el caso es una
 *  ficha suelta y hay varias sobre el mismo predio. */
const idCaso = (c?: Caso | null) => (c ? (c.uid || `${c.clave}|${c.tipo}`) : '');

const m2 = (v: number) => v.toLocaleString('es-EC') + ' m²';
const ha = (v: number) =>
  (v / 10000).toLocaleString('es-EC', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

// `corto` es para los chips del panel estrecho; `et` para el resto.
const TIPOS = {
  exceso: { et: 'Declaran más que el predio', corto: 'Declarado de más', color: '#d97706', bg: 'bg-amber-50', tx: 'text-amber-700' },
  triple: { et: 'Área triplicada', corto: 'Triplicada', color: '#b45309', bg: 'bg-orange-50', tx: 'text-orange-800' },
  clave_mala: { et: 'Clave inexistente', corto: 'Clave mala', color: '#7c3aed', bg: 'bg-violet-50', tx: 'text-violet-700' },
  sin_comunidad: { et: 'Sin comunidad', corto: 'Sin comunidad', color: '#0891b2', bg: 'bg-cyan-50', tx: 'text-cyan-700' },
  dividido: { et: 'Bien dividido', corto: 'Divididos', color: '#16a34a', bg: 'bg-green-50', tx: 'text-green-700' },
  cultivo: { et: 'Siembra más de lo que mide', corto: 'Producción', color: '#65a30d', bg: 'bg-lime-50', tx: 'text-lime-700' },
} as const;

// Los filtros van agrupados por lo que hay que hacer con cada cosa, no por
// tipo de dato: mezclar «sin comunidad» con «exceso de área» en una sola fila
// obliga a recordar cuál era cuál.
const GRUPOS: { titulo: string; pie: string; tipos: (keyof typeof TIPOS)[] }[] = [
  {
    // Hasta el 15-ago-2026 este grupo se llamaba «Afectan a la superficie»,
    // porque el padrón sumaba fichas y estos predios inflaban el total. Desde
    // que la superficie se mide por polígonos únicos ya no afectan a ninguna
    // cifra: lo que queda es la calidad de lo que se declaró en campo.
    titulo: 'Superficie declarada',
    pie: 'Calidad del dato de campo',
    tipos: ['exceso', 'triple', 'clave_mala', 'dividido'],
  },
  {
    titulo: 'Datos por completar',
    pie: 'No cambian la superficie',
    tipos: ['sin_comunidad'],
  },
  {
    // Va en su propio grupo porque no mira el predio sino lo sembrado, y
    // porque aquí lo raro no es necesariamente un error: sembrar en terreno
    // arrendado fuera del predio es corriente en la zona.
    titulo: 'La producción no cabe en el predio',
    pie: 'Cultivos, no superficie del predio',
    tipos: ['cultivo'],
  },
];

/** Lleva el mapa al caso elegido. */
function Encuadrar({ caso }: { caso: Caso | null }) {
  const map = useMap();
  useEffect(() => {
    if (!caso) return;
    const pts: LatLngExpression[] = [];
    caso.geo?.forEach(([lon, lat]) => pts.push([lat, lon]));
    caso.fichas.forEach((f) => { if (f.lat && f.lon) pts.push([f.lat, f.lon]); });
    caso.vecinas?.forEach((v) => pts.push([v.lat, v.lon]));
    if (pts.length === 1) map.setView(pts[0], 18);
    else if (pts.length) map.fitBounds(pts as [number, number][], { padding: [60, 60], maxZoom: 18 });
  }, [caso, map]);
  return null;
}

export default function AuditoriaAreasPage() {
  const [datos, setDatos] = useState<Datos | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filtro, setFiltro] = useState<keyof typeof TIPOS>('exceso');
  const [busca, setBusca] = useState('');
  const [sel, setSel] = useState<Caso | null>(null);
  // El panel se pliega para revisar el mapa a pantalla completa, que es como
  // se mira un predio en reunión.
  const [panel, setPanel] = useState(true);

  useEffect(() => {
    fetch('/geo/auditoria_areas.json')
      .then((r) => { if (!r.ok) throw new Error('no se pudo leer el archivo'); return r.json(); })
      .then((d: Datos) => {
        setDatos(d);
        const primero = d.casos.find((c) => c.tipo === 'exceso') || d.casos[0] || null;
        setSel(primero);
      })
      .catch((e) => setError(String(e.message || e)));
  }, []);

  const lista = useMemo(() => {
    if (!datos) return [];
    const q = busca.trim().toLowerCase();
    return datos.casos.filter((c) => {
      const porTipo = filtro === 'triple' ? (c.triple || 0) > 0 : c.tipo === filtro;
      if (!porTipo) return false;
      if (!q) return true;
      return c.clave.includes(q)
        || c.com.toLowerCase().includes(q)
        || c.fichas.some((f) => f.n.toLowerCase().includes(q) || f.ced.includes(q));
    });
  }, [datos, filtro, busca]);

  // Al cambiar de filtro o de búsqueda, el mapa seguía en el caso anterior
  // aunque ya no estuviera en la lista. Se salta al primero de lo que se ve.
  useEffect(() => {
    if (!lista.length) return;
    if (!sel || !lista.some((c) => idCaso(c) === idCaso(sel))) {
      setSel(lista[0]);
    }
  }, [lista, sel]);

  if (error) {
    return (
      <div className="p-8">
        <div className="max-w-lg rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          <b>No se pudieron cargar los datos de auditoría.</b>
          <p className="mt-1">{error}</p>
          <p className="mt-2 text-red-700">
            Generarlos con: <code className="rounded bg-white px-1">python scripts/generar_auditoria_areas.py</code>
          </p>
        </div>
      </div>
    );
  }
  if (!datos) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-7 w-7 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
      </div>
    );
  }

  const R = datos.resumen;
  const conteo = {
    exceso: R.exceso, triple: R.triple, clave_mala: R.clave_mala,
    sin_comunidad: R.sin_comunidad, dividido: R.dividido,
    cultivo: R.cultivo ?? 0,
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col">
      {/* ── cabecera ── */}
      <div className="border-b border-gray-200 bg-white px-5 py-3">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="flex items-center gap-2 text-lg font-semibold text-gray-900">
              <Ruler className="h-5 w-5 text-blue-600" />
              Auditoría de áreas
            </h1>
            <p className="mt-0.5 text-xs text-gray-500">
              Calidad de lo que declararon los regantes, contra el catastro del
              GADM · corte {datos.corte} · datos generados {datos.generado}
            </p>
          </div>
          <div className="flex flex-wrap gap-5 text-sm">
            <div>
              {/* Ya no en rojo: desde que la superficie del sistema se mide por
                  polígonos, estos predios no distorsionan ninguna cifra
                  publicada. Pintarlos de alarma haría pensar lo contrario. */}
              <div className="text-xl font-semibold tabular-nums text-amber-600">{R.exceso}</div>
              <div className="text-xs text-gray-500">predios por depurar</div>
            </div>
            <div>
              <div className="text-xl font-semibold tabular-nums text-amber-600">
                {R.exc_ha.toLocaleString('es-EC', { minimumFractionDigits: 2 })}
              </div>
              <div className="text-xs text-gray-500">ha declaradas de más</div>
            </div>
            <div>
              <div className="text-xl font-semibold tabular-nums text-blue-600">{R.con_obs}</div>
              <div className="text-xs text-gray-500">con área en observaciones</div>
            </div>
            <div>
              <div className="text-xl font-semibold tabular-nums text-lime-700">{R.cultivo ?? 0}</div>
              <div className="text-xs text-gray-500">siembran más de lo que miden</div>
            </div>
          </div>
        </div>

        {/* Qué significa hoy este exceso. Sin esta línea, las 1.859 ha de
            arriba se leen como un error pendiente en las cifras publicadas, y
            desde el 15-ago-2026 ya no lo son. */}
        <div className="mt-2.5 rounded border border-blue-100 bg-blue-50 px-3 py-2 text-xs text-blue-900">
          <b>Esto ya no afecta a la superficie del sistema.</b> El padrón mide sus{' '}
          hectáreas sumando <b>polígonos del catastro, cada predio una vez</b>, así
          que lo que se declara de más aquí no infla ninguna cifra publicada. Lo
          que esta pantalla muestra es <b>dónde el levantamiento no capturó el
          reparto real</b> entre coherederos: sirve para depurar el dato declarado
          y para saber a qué predios hay que volver, no para corregir la
          superficie.
        </div>

        {/* Cuánto del padrón está ya en regla. Sin esto la pantalla solo
            enseña lo que falta y no se ve el avance. */}
        {datos.corregido && (
          <div className="mt-3 flex flex-wrap gap-x-8 gap-y-2 border-t border-gray-100 pt-2.5">
            {([
              ['Con comunidad', datos.corregido.con_comunidad],
              ['Clave en el catastro', datos.corregido.clave_valida],
              ['Área que cuadra', datos.corregido.area_cuadra],
            ] as [string, number][]).map(([et, v]) => {
              const total = datos.corregido!.total_fichas;
              const pct = (100 * v) / total;
              return (
                <div key={et} className="min-w-[170px] flex-1">
                  <div className="flex items-baseline justify-between text-xs">
                    <span className="text-gray-600">{et}</span>
                    <span className="tabular-nums text-gray-500">
                      <b className="text-gray-800">{v.toLocaleString('es-EC')}</b>
                      {' / '}{total.toLocaleString('es-EC')}
                    </span>
                  </div>
                  <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-gray-200">
                    <div
                      className={`h-full rounded-full ${pct >= 99 ? 'bg-green-500' : 'bg-blue-500'}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
        {/* ── lista ── */}
        <aside
          className={`flex min-h-0 flex-col border-r border-gray-200 bg-white
                      transition-[width] duration-200
                      ${panel ? 'w-full lg:w-72' : 'w-full lg:w-0 lg:overflow-hidden lg:border-r-0'}`}
        >
          <div className="space-y-2 border-b border-gray-200 p-2.5">
            <div className="relative">
              <Search className="absolute left-2 top-2 h-3.5 w-3.5 text-gray-400" />
              <input
                value={busca}
                onChange={(e) => setBusca(e.target.value)}
                placeholder="Clave, comunidad, regante…"
                className="w-full rounded-md border border-gray-300 py-1.5 pl-7 pr-2 text-xs
                           focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            {GRUPOS.map((g) => (
              <div key={g.titulo}>
                <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-gray-400">
                  {g.titulo}
                  <span className="ml-1 font-normal normal-case tracking-normal text-gray-400">
                    · {g.pie}
                  </span>
                </p>
                <div className="flex flex-wrap gap-1">
                  {g.tipos.map((t) => (
                    <button
                      key={t}
                      onClick={() => setFiltro(t)}
                      aria-pressed={filtro === t}
                      title={TIPOS[t].et}
                      className={`rounded-full border px-2 py-0.5 text-[11px] transition
                        ${filtro === t
                          ? 'border-gray-900 bg-gray-900 text-white'
                          : 'border-gray-300 text-gray-600 hover:bg-gray-50'}`}
                    >
                      {TIPOS[t].corto}{' '}
                      <span className="tabular-nums opacity-70">{conteo[t]}</span>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto">
            {lista.length === 0 && (
              <p className="p-6 text-sm text-gray-500">Ningún predio coincide.</p>
            )}
            {lista.map((c) => {
              const T = TIPOS[c.tipo];
              // Los casos de superficie son un predio (la clave los identifica),
              // pero los de comunidad son una FICHA, y dos fichas pueden estar
              // sobre el mismo predio. Por eso manda el uid cuando lo hay.
              const activo = idCaso(sel) === idCaso(c);
              return (
                <button
                  key={idCaso(c)}
                  onClick={() => setSel(c)}
                  title={`${c.clave} · ${c.com}${c.sec ? ' · ' + c.sec : ''}`}
                  className={`flex w-full items-center gap-2 border-b border-gray-100 px-2 py-2
                              text-left transition hover:bg-blue-50/60
                              ${activo ? 'bg-blue-50' : ''}`}
                >
                  <span className="h-8 w-1 shrink-0 rounded" style={{ background: T.color }} />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-mono text-[11px] text-gray-900">{c.clave}</span>
                    <span className="block truncate text-[11px] text-gray-500">
                      {c.tipo === 'sin_comunidad' || c.tipo === 'cultivo'
                        ? (c.fichas[0]?.n || '—')
                        : `${c.com} · ${c.nf} ficha${c.nf !== 1 ? 's' : ''}`}
                    </span>
                  </span>
                  <span className="shrink-0 text-right">
                    {c.tipo === 'exceso' && (
                      <>
                        <span className="block text-xs font-semibold tabular-nums text-amber-700">
                          +{ha(c.exc)}
                        </span>
                        <span className="text-[9px] text-gray-500">ha</span>
                      </>
                    )}
                    {c.tipo === 'dividido' && <CheckCircle2 className="h-4 w-4 text-green-600" />}
                    {c.tipo === 'cultivo' && (
                      <>
                        <span className="block text-xs font-semibold tabular-nums text-lime-700">
                          ×{c.factor}
                        </span>
                        <span className="text-[9px] text-gray-500">del predio</span>
                      </>
                    )}
                    {c.tipo === 'sin_comunidad' && (
                      c.estado === 'propuesta'
                        ? <span className="block max-w-[92px] truncate text-[10px] font-medium text-green-700"
                                title={c.propuesta}>{c.propuesta}</span>
                        : <span className="text-[10px] text-gray-500">revisar</span>
                    )}
                    {c.tipo === 'triple' && (
                      <span className="text-[10px] text-amber-700">{c.triple} fic.</span>
                    )}
                    {c.tipo === 'clave_mala' && (
                      c.estado === 'propuesta'
                        ? <span className="text-[10px] font-medium text-green-700">propuesta</span>
                        : c.estado === 'del DMQ'
                          ? <span className="text-[10px] text-violet-700">del DMQ</span>
                          : <span className="text-[10px] text-gray-500">{c.digitos} díg.</span>
                    )}
                    {c.resuelto_por_obs && (
                      <span className="mt-0.5 block text-[9px] font-medium text-green-700">
                        ✓ en obs.
                      </span>
                    )}
                    {c.tipo === 'exceso' && !c.resuelto_por_obs && (c.obs_n || 0) > 0 && (
                      <span className="mt-0.5 block text-[9px] text-blue-600">
                        {c.obs_n} anotada{c.obs_n !== 1 ? 's' : ''}
                      </span>
                    )}
                  </span>
                </button>
              );
            })}
          </div>
        </aside>

        {/* ── mapa + detalle ── */}
        <div className="flex min-h-0 flex-1 flex-col">
          <div className="relative min-h-[300px] flex-1">
            <MapContainer center={[0.04, -78.15]} zoom={13} className="h-full w-full">
              <LayersControl position="topright">
                <LayersControl.BaseLayer checked name="ESRI Satélite">
                  <TileLayer
                    attribution="&copy; ESRI"
                    url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                    maxZoom={20}
                  />
                </LayersControl.BaseLayer>
                <LayersControl.BaseLayer name="ESRI Topográfico">
                  <TileLayer
                    attribution="&copy; ESRI"
                    url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}"
                    maxZoom={20}
                  />
                </LayersControl.BaseLayer>
                <LayersControl.Overlay checked name="Canal Guanguilquí">
                  <Polyline
                    positions={datos.canal.map((l) => l.map(([lon, lat]) => [lat, lon] as [number, number]))}
                    pathOptions={{ color: '#0ea5e9', weight: 2, dashArray: '6 5', opacity: 0.85 }}
                  />
                </LayersControl.Overlay>
              </LayersControl>

              {sel?.geo && (
                <Polygon
                  positions={sel.geo.map(([lon, lat]) => [lat, lon] as [number, number])}
                  pathOptions={{ color: '#facc15', weight: 2.5, fillColor: '#facc15', fillOpacity: 0.15 }}
                >
                  <Tooltip sticky>
                    Polígono del catastro · {m2(sel.pol)}
                  </Tooltip>
                </Polygon>
              )}
              {/* Las vecinas que sustentan la propuesta de comunidad. Verlas
                  alrededor es lo que hace evidente de dónde sale. */}
              {sel?.vecinas?.map((v, i) => {
                const apoya = v.com === sel.propuesta;
                return (
                  <CircleMarker
                    key={`v${i}`}
                    center={[v.lat, v.lon]}
                    radius={4}
                    pathOptions={{
                      color: apoya ? '#0891b2' : '#94a3b8', weight: 1.5,
                      fillColor: apoya ? '#0891b2' : '#cbd5e1',
                      fillOpacity: apoya ? 0.8 : 0.5,
                    }}
                  >
                    <Tooltip direction="top" offset={[0, -6]}>
                      {v.com} · a {v.d} m
                    </Tooltip>
                  </CircleMarker>
                );
              })}
              {sel?.fichas.map((f, i) =>
                f.lat && f.lon ? (
                  <CircleMarker
                    key={i}
                    center={[f.lat, f.lon]}
                    radius={7}
                    pathOptions={{
                      color: '#fff', weight: 2,
                      fillColor: TIPOS[sel.tipo].color, fillOpacity: 0.95,
                    }}
                  >
                    <Tooltip direction="top" offset={[0, -8]}>
                      <b>{f.n}</b><br />
                      Declara {m2(f.a)}
                      {f.oa ? <><br />Observación: {m2(f.oa)}</> : null}
                    </Tooltip>
                  </CircleMarker>
                ) : null,
              )}
              <Encuadrar caso={sel} />
            </MapContainer>

            {/* Plegar la lista para dejarle el mapa entero. Va bajo el control
                de zoom de Leaflet, que ocupa la esquina superior izquierda. */}
            <button
              onClick={() => setPanel((v) => !v)}
              title={panel ? 'Ocultar la lista' : 'Mostrar la lista'}
              aria-label={panel ? 'Ocultar la lista de predios' : 'Mostrar la lista de predios'}
              className="absolute left-3 top-[84px] z-[1001] hidden rounded-md border border-gray-300
                         bg-white/95 p-1.5 text-gray-600 shadow backdrop-blur
                         transition hover:bg-gray-50 hover:text-gray-900 lg:block"
            >
              {panel ? <PanelLeftClose className="h-4 w-4" /> : <PanelLeftOpen className="h-4 w-4" />}
            </button>

            {sel && (
              <div className="pointer-events-none absolute left-14 top-3 z-[1000] max-w-sm
                              rounded-lg border border-gray-200 bg-white/95 p-3 shadow-lg
                              backdrop-blur">
                <div className="flex items-center gap-2">
                  <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium
                                    ${TIPOS[sel.tipo].bg} ${TIPOS[sel.tipo].tx}`}>
                    {TIPOS[sel.tipo].et}
                  </span>
                  <span className="font-mono text-xs text-gray-700">{sel.clave}</span>
                </div>
                <p className="mt-1.5 text-xs text-gray-600">
                  <MapPin className="mr-1 inline h-3 w-3" />
                  {sel.com}{sel.sec ? ` · ${sel.sec}` : ''}
                </p>
                {sel.tipo === 'sin_comunidad' && (
                  <>
                    <p className="mt-1 text-xs text-gray-700">
                      {sel.fichas[0]?.n} — la ficha no dice a qué comunidad pertenece.
                    </p>
                    {sel.estado === 'propuesta' ? (
                      <p className="mt-1.5 rounded bg-green-50 px-2 py-1 text-xs text-green-800">
                        <CheckCircle2 className="mr-1 inline h-3 w-3" />
                        Es de <b>{sel.propuesta}</b>, según {sel.via}.
                      </p>
                    ) : (
                      <p className="mt-1.5 rounded bg-gray-100 px-2 py-1 text-xs text-gray-700">
                        Sin propuesta automática: {sel.nota}
                      </p>
                    )}
                    {sel.vecinas?.length ? (
                      <p className="mt-1 text-[11px] text-gray-500">
                        Los puntos pequeños del mapa son las fichas vecinas que ya tienen
                        comunidad; el grande es esta.
                      </p>
                    ) : null}
                  </>
                )}
                {sel.tipo !== 'clave_mala' && sel.tipo !== 'sin_comunidad'
                  && sel.tipo !== 'cultivo' && (
                  <p className="mt-1 text-xs text-gray-700">
                    {sel.nf} ficha{sel.nf !== 1 ? 's' : ''} declaran <b>{m2(sel.dec)}</b> sobre un
                    polígono de <b>{m2(sel.pol)}</b>
                    {sel.exc > 0 && <> · declaran <b className="text-amber-700">{ha(sel.exc)} ha</b> de más</>}
                  </p>
                )}
                {sel.tipo === 'cultivo' && (
                  <>
                    <p className="mt-1 text-xs text-gray-700">
                      {sel.fichas[0]?.n} declara <b className="text-lime-700">{m2(sel.cul || 0)}</b>
                      {' '}sembrados en un predio de <b>{m2(sel.dec)}</b> —
                      {' '}<b>{sel.factor} veces</b> su terreno.
                    </p>
                    {sel.items?.length ? (
                      <div className="mt-1.5 rounded border border-lime-200 bg-lime-50 px-2 py-1.5">
                        <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-lime-800">
                          Lo que declaró sembrado
                        </p>
                        {sel.items.map((it, i) => (
                          <div key={i} className="flex justify-between gap-3 text-[11px] text-gray-700">
                            <span className="truncate">{it.t}</span>
                            <span className="shrink-0 tabular-nums font-medium">{m2(it.m2)}</span>
                          </div>
                        ))}
                        <div className="mt-1 flex justify-between gap-3 border-t border-lime-200 pt-1
                                        text-[11px] font-semibold text-gray-900">
                          <span>Predio según el catastro</span>
                          <span className="tabular-nums">{m2(sel.pol)}</span>
                        </div>
                      </div>
                    ) : null}
                    <p className="mt-1.5 rounded bg-gray-100 px-2 py-1 text-[11px] text-gray-700">
                      <b>No siempre es un error.</b> Sembrar en terreno arrendado fuera del predio
                      propio es corriente aquí. Lo que hay que mirar es si la cifra tiene sentido:
                      un factor redondo (×10, ×100) suele ser el punto decimal; un factor pequeño,
                      terreno de fuera.
                    </p>
                  </>
                )}
                {sel.tipo === 'clave_mala' && (
                  <>
                    <p className="mt-1 text-xs text-gray-700">
                      Clave de <b>{sel.digitos} dígitos</b> que no existe en el catastro
                      de Cayambe.
                    </p>
                    {sel.estado === 'propuesta' && (
                      <p className="mt-1.5 rounded bg-green-50 px-2 py-1 text-xs text-green-800">
                        <CheckCircle2 className="mr-1 inline h-3 w-3" />
                        Debería ser <b className="font-mono">{sel.propuesta}</b>: es el predio
                        donde cae el punto y {sel.dif}.
                        {sel.area_confirma && (
                          <> El área declarada coincide con la del polígono, lo que lo confirma.</>
                        )}
                      </p>
                    )}
                    {sel.estado === 'del DMQ' && (
                      <p className="mt-1.5 rounded bg-violet-50 px-2 py-1 text-xs text-violet-800">
                        <b>No es una errata.</b> El técnico anotó que el predio pertenece al
                        Distrito Metropolitano de Quito: la clave es correcta, de otro catastro.
                      </p>
                    )}
                    {sel.estado === 'lo explica la observación' && (
                      <p className="mt-1.5 rounded bg-amber-50 px-2 py-1 text-xs text-amber-800">
                        La observación del técnico explica el caso; hay que leerla antes de
                        tocar nada.
                      </p>
                    )}
                    {sel.estado === 'sin resolver' && (
                      <p className="mt-1.5 rounded bg-gray-100 px-2 py-1 text-xs text-gray-700">
                        Sin propuesta automática: {sel.nota}
                      </p>
                    )}
                  </>
                )}
                {sel.resuelto_por_obs && (
                  <p className="mt-1.5 rounded bg-green-50 px-2 py-1 text-xs text-green-800">
                    <CheckCircle2 className="mr-1 inline h-3 w-3" />
                    Las observaciones traen las áreas y suman el polígono: se resuelve copiándolas.
                  </p>
                )}
                {sel.falta && (
                  <p className="mt-1.5 rounded bg-amber-50 px-2 py-1 text-xs text-amber-800">
                    <b>Qué falta para cerrarlo:</b> {sel.falta}.
                  </p>
                )}
              </div>
            )}
          </div>

          {/* ── fichas del predio ── */}
          {sel && (
            <div className="max-h-[38%] min-h-[150px] overflow-auto border-t border-gray-200 bg-white">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-gray-50 text-[10px] uppercase tracking-wide text-gray-500">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium">Regante</th>
                    <th className="px-3 py-2 text-left font-medium">Cédula</th>
                    <th className="px-3 py-2 text-left font-medium">Teléfono</th>
                    <th className="px-3 py-2 text-right font-medium">Declara</th>
                    {sel.tipo === 'triple' || sel.triple ? (
                      <>
                        <th className="px-3 py-2 text-right font-medium">Con riego</th>
                        <th className="px-3 py-2 text-right font-medium">Sin riego</th>
                      </>
                    ) : (
                      <th className="px-3 py-2 text-right font-medium">En observación</th>
                    )}
                    <th className="px-3 py-2 text-left font-medium">Levantó</th>
                    <th className="px-3 py-2 text-left font-medium">Observación del técnico</th>
                  </tr>
                </thead>
                <tbody>
                  {sel.fichas.map((f, i) => {
                    const triple = f.a > 0 && Math.abs(f.a - f.ar) < 1 && Math.abs(f.a - f.asr) < 1;
                    return (
                      <tr key={i} className={`border-b border-gray-100 ${triple ? 'bg-amber-50/50' : ''}`}>
                        <td className="whitespace-nowrap px-3 py-1.5 text-gray-900">
                          {f.n}
                          {f.p === 0 && <span className="ml-1 text-[10px] text-gray-400">adicional</span>}
                        </td>
                        <td className="whitespace-nowrap px-3 py-1.5 font-mono text-gray-600">{f.ced || '—'}</td>
                        <td className="whitespace-nowrap px-3 py-1.5 text-gray-600">
                          {f.tel ? (
                            <a href={`tel:${f.tel}`} className="text-blue-600 hover:underline">
                              <Phone className="mr-1 inline h-3 w-3" />{f.tel}
                            </a>
                          ) : '—'}
                        </td>
                        <td className="whitespace-nowrap px-3 py-1.5 text-right tabular-nums text-gray-900">
                          {m2(f.a)}
                        </td>
                        {sel.tipo === 'triple' || sel.triple ? (
                          <>
                            <td className="whitespace-nowrap px-3 py-1.5 text-right tabular-nums text-gray-600">
                              {m2(f.ar)}
                            </td>
                            <td className="whitespace-nowrap px-3 py-1.5 text-right tabular-nums text-gray-600">
                              {m2(f.asr)}
                            </td>
                          </>
                        ) : (
                          <td className="whitespace-nowrap px-3 py-1.5 text-right tabular-nums">
                            {f.oa ? (
                              <b className="text-green-700">{m2(f.oa)}</b>
                            ) : <span className="text-gray-300">—</span>}
                          </td>
                        )}
                        <td className="whitespace-nowrap px-3 py-1.5 text-gray-500">
                          {f.tec}<span className="ml-1 text-gray-400">{f.f}</span>
                        </td>
                        <td className="max-w-md px-3 py-1.5 text-gray-600">
                          {f.obs ? (
                            <span title={f.obs} className="line-clamp-2">
                              <FileText className="mr-1 inline h-3 w-3 text-gray-400" />
                              {f.obs}
                            </span>
                          ) : <span className="text-gray-300">—</span>}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {sel.obs_suma ? (
                <p className="border-t border-gray-100 bg-gray-50 px-3 py-2 text-xs text-gray-600">
                  <Layers className="mr-1 inline h-3 w-3" />
                  Las observaciones suman <b>{m2(sel.obs_suma)}</b> de {sel.obs_n} ficha
                  {sel.obs_n !== 1 ? 's' : ''}, sobre un polígono de <b>{m2(sel.pol)}</b>.
                  {sel.resuelto_por_obs
                    ? ' Cuadra: el dato correcto ya está escrito.'
                    : ' Todavía no cuadra; faltan fichas por revisar.'}
                </p>
              ) : null}
            </div>
          )}
        </div>
      </div>

      {/* ── nota al pie ── */}
      <div className="border-t border-gray-200 bg-gray-50 px-5 py-2 text-[11px] text-gray-500">
        <AlertTriangle className="mr-1 inline h-3 w-3 text-amber-500" />
        Pantalla de trabajo interno. Los datos se regeneran con
        <code className="mx-1 rounded bg-white px-1">scripts/generar_auditoria_areas.py</code>
        en cada sincronización del padrón.
      </div>
    </div>
  );
}
