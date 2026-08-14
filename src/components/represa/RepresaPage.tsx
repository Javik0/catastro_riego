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
import { useData } from '../../App';
import { type FichaPredio, esFichaHija, esHijaPendiente } from '../../lib/types';
import { getNombreTecnico } from '../../lib/constants';
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
  /** Colorea cada predio según el tipo de ficha, igual que el mapa del padrón. */
  porEstadoDeFicha?: boolean;
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

// Simbología de los predios: la misma del mapa del padrón y del proyecto QGIS,
// para que quien mire las dos pantallas lea lo mismo sin volver a aprenderla.
//   TOMATE  → el predio tiene ficha principal (es el predio de un regante)
//   AZUL    → solo tiene predios adicionales, todos completados
//   CELESTE → tiene alguna ficha adicional pendiente de la Sección 4
const COLOR_PREDIO = {
  principal: { borde: '#ea580c', relleno: '#f97316' },
  adicional: { borde: '#2563eb', relleno: '#3b82f6' },
  pendiente: { borde: '#0ea5e9', relleno: '#7dd3fc' },
} as const;

type EstadoPredio = keyof typeof COLOR_PREDIO;

const ETIQUETA_PREDIO: Record<EstadoPredio, string> = {
  principal: 'Predio de regante (ficha principal)',
  adicional: 'Predio adicional investigado',
  pendiente: 'Predio adicional pendiente',
};

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
  {
    // el hallazgo que nadie ve mirando solo el plano: parte de la obra se
    // levanta sobre predios que el padrón ya investigó
    id: 'vaso', archivo: 'predios_en_vaso', nombre: 'Predios bajo el área de proyecto',
    estilo: { color: '#f59e0b', weight: 2.5, fillOpacity: 0.35 },
    activaPorDefecto: true,
    nota: 'catastro del GADM · rojo si además tiene ficha del padrón',
  },

  // ── el sistema de riego al que va a servir la obra ──
  {
    // capa del padrón, no del módulo de la represa: es la misma que dibuja el
    // mapa web, y así el predio se lee igual en las dos pantallas
    id: 'predios_poly', archivo: '/geo/catastro_geo.geojson',
    nombre: 'Predios investigados y adicionales',
    grupo: 'sistema', porEstadoDeFicha: true,
    estilo: { weight: 1.2, fillOpacity: 0.35 },
    nota: 'polígono catastral · color según el tipo de ficha · clic para el detalle',
  },
  {
    id: 'predios', archivo: 'predios_por_sector', nombre: 'Punto GPS de cada ficha',
    grupo: 'sistema', porSector: true, puntos: true,
    estilo: { weight: 0, fillOpacity: 0.75 },
    nota: 'donde se levantó la encuesta, pintado por sector',
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

/** Un predio catastral sobre el que se levanta la obra (`06_capas_padron.py`). */
interface PredioEnVaso {
  clave: string;
  /** Del catastro del GADM; solo lo tienen los predios ya consultados. */
  nombre_predio: string | null;
  tipo_predio: string | null;
  condicion: string | null;
  detalle_condicion: string | null;
  /** Si el padrón levantó ficha sobre este predio. */
  investigado: boolean;
  propietario: string | null;
  cedula: string | null;
  comunidad: string | null;
  codigo_ficha: string | null;
  tenencia: string | null;
  caudal_ls: number | null;
  observaciones: string | null;
  fichas_en_el_predio: number;
  area_predio_ha: number;
  ha_en_vaso: number;
  pct_del_vaso: number;
  pct_del_predio: number;
  /** Del punto GPS de la ficha al límite de proyecto. Ver nota del panel. */
  distancia_punto_m: number | null;
}

interface Magnitud {
  represa_ha: number;
  riego_ha: number;
  predios: number;
  ha_regadas_por_ha_de_represa: number;
  sectores: Array<{ sector: string; predios: number; area_riego_ha: number }>;
  vaso?: {
    area_ha: number;
    cubierta_ha: number;
    cubierta_pct: number;
    libre_ha: number;
    /** Superficie de la obra sobre predios con ficha del padrón. */
    investigada_ha: number;
    predios: PredioEnVaso[];
  } | null;
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
    // en modo «sistema» se esperan los predios: encuadrar a la obra y
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

/** Un dato del popup, omitido cuando viene vacío. */
const linea = (etiqueta: string, valor: unknown) =>
  (valor === null || valor === undefined || valor === '' || valor === 0)
    ? ''
    : `<div style="display:flex;gap:8px;justify-content:space-between">
         <span style="opacity:.65">${etiqueta}</span><b>${String(valor)}</b></div>`;

const num = (v: number, dec = 0) =>
  v.toLocaleString('es-EC', { minimumFractionDigits: dec, maximumFractionDigits: dec });

interface Indices {
  fichasPorClave: Map<string, FichaPredio[]>;
  estadoDePredio: Map<string, EstadoPredio>;
}

/**
 * Detalle de un predio investigado, con los mismos datos que el mapa del padrón.
 *
 * El propietario sale de la ficha y no del polígono: `catastro_geo.geojson`
 * arrastra los campos del catastro municipal, que en los predios grandes vienen
 * vacíos — el predio que ocupa la represa es justamente uno de esos.
 */
function popupDePredio(p: Record<string, unknown>, idx: Indices) {
  const clave = String(p.clave_cata ?? '').trim();
  const fichas = idx.fichasPorClave.get(clave) ?? [];
  const ficha = fichas.find((f) => !esFichaHija(f)) ?? fichas[0];
  const estado = idx.estadoDePredio.get(clave) ?? 'principal';
  const col = COLOR_PREDIO[estado];

  const nombre = (ficha
    ? `${ficha.apellidos ?? ''} ${ficha.nombres ?? ''}`.trim()
    : `${p.apellidos ?? ''} ${p.nombres ?? ''}`.trim()) || 'Sin propietario en la ficha';
  const m2 = Number(p.area_predi ?? ficha?.area_total ?? 0);
  const obs = String(ficha?.observaciones ?? '').trim();

  return `
    <div style="font-size:12px;line-height:1.5;min-width:230px">
      <div style="font-weight:700;font-size:13px;margin-bottom:2px">${nombre}</div>
      <div style="display:inline-block;font-size:10px;padding:1px 6px;border-radius:99px;
                  margin-bottom:6px;background:${col.relleno}33;color:${col.borde};
                  border:1px solid ${col.borde}66">${ETIQUETA_PREDIO[estado]}</div>
      ${linea('Clave catastral', clave || '—')}
      ${linea('Cédula', ficha?.cedula ?? p.cedula)}
      ${linea('Comunidad', ficha?.comunidad ?? p.comunidad)}
      ${linea('Ficha', ficha?.codigo_final)}
      ${linea('Área del predio', m2 ? `${num(m2)} m² · ${num(m2 / 10000, 2)} ha` : null)}
      ${linea('Superficie con riego', ficha?.area_riego ? `${num(Number(ficha.area_riego))} m²` : null)}
      ${linea('Tenencia', ficha?.tenencia_predio)}
      ${/* «declarado»: es el dato de esta ficha, no el caudal del sistema, que
            solo sale de caudal_por_comunidad.json (regla 3 del proyecto) */''}
      ${linea('Caudal declarado', ficha?.caudal_valor
        ? `${num(Number(ficha.caudal_valor), 1)} l/s` : null)}
      ${linea('Técnico', ficha?.creado_por ? getNombreTecnico(String(ficha.creado_por)) : null)}
      ${fichas.length > 1
        ? `<div style="margin-top:4px;opacity:.7">${fichas.length} fichas declaran este predio</div>`
        : ''}
      ${obs
        ? `<div style="margin-top:6px;padding-top:6px;border-top:1px solid currentColor;
                       opacity:.85"><b>Observaciones:</b> ${obs}</div>`
        : ''}
    </div>`;
}

/** Detalle del solape entre un predio catastral y el área de proyecto. */
function popupDeVaso(p: Record<string, unknown>) {
  const esSolape = p.tipo === 'solape';
  const investigado = p.investigado === true;
  const color = investigado ? '#dc2626' : '#f59e0b';
  return `
    <div style="font-size:12px;line-height:1.5;min-width:230px">
      <div style="font-weight:700;font-size:13px;color:${color};margin-bottom:2px">
        ${esSolape ? 'Superficie que ocupa la obra' : 'Predio bajo el área de proyecto'}
      </div>
      <div style="font-weight:600;margin-bottom:4px">
        ${p.nombre_predio ?? `Predio ${p.clave ?? '—'}`}
      </div>
      ${linea('Clave catastral', p.clave)}
      ${linea('Condición', p.condicion)}
      ${linea('Predio completo', `${num(Number(p.area_predio_ha ?? 0), 2)} ha`)}
      ${linea('Dentro del proyecto', `${num(Number(p.ha_en_vaso ?? 0), 2)} ha`)}
      ${linea('Del área de proyecto', `${p.pct_del_vaso}%`)}
      ${investigado
        ? `${linea('Ficha del padrón', p.codigo_ficha)}${linea('Titular', p.propietario)}`
        : '<div style="margin-top:4px;opacity:.8">Sin ficha en el padrón.</div>'}
      <div style="margin-top:6px;padding-top:6px;border-top:1px solid currentColor;opacity:.75">
        Catastro rural del GADM cruzado con el límite de proyecto, medido en UTM 17S.
      </div>
    </div>`;
}

/**
 * Encuadra al predio que ocupa la obra cuando se pulsa «Ver en el mapa».
 *
 * El `trigger` es un contador y no un booleano a propósito: pulsar dos veces
 * seguidas tiene que volver a encuadrar, aunque ya se estuviera ahí.
 */
function IrAlPredioOcupado({ trigger, datos }: { trigger: number; datos: unknown }) {
  const mapa = useMap();
  const ultimo = useRef(0);

  useEffect(() => {
    if (!trigger || trigger === ultimo.current || !datos) return;
    try {
      const caja = L.geoJSON(datos as never).getBounds();
      if (!caja.isValid()) return;
      mapa.fitBounds(caja, { padding: [40, 40] });
      ultimo.current = trigger;
    } catch { /* si falla, se queda donde estaba */ }
  }, [trigger, datos, mapa]);

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
  /** Contador: cada pulsación de «Ver en el mapa» encuadra al predio ocupado. */
  const [irAlVaso, setIrAlVaso] = useState(0);

  // Las fichas del padrón ya están cargadas para toda la aplicación: aquí no se
  // vuelven a pedir, solo se indexan por clave catastral. Son las que dicen de
  // quién es cada polígono — el catastro municipal deja ese dato vacío en los
  // predios grandes, justamente en el que ocupa la represa.
  const { fichas } = useData();

  const fichasPorClave = useMemo(() => {
    const m = new Map<string, FichaPredio[]>();
    for (const f of fichas) {
      for (const c of new Set([f.clave_catastral, f.cod_poligono]
        .map((v) => String(v || '').trim()).filter(Boolean))) {
        const arr = m.get(c);
        if (arr) arr.push(f); else m.set(c, [f]);
      }
    }
    return m;
  }, [fichas]);

  /** Estado del predio, con la misma regla que el mapa del padrón y QGIS. */
  const estadoDePredio = useMemo(() => {
    const m = new Map<string, EstadoPredio>();
    for (const [clave, arr] of fichasPorClave) {
      if (arr.some((f) => !esFichaHija(f))) m.set(clave, 'principal');
      else if (arr.some((f) => esHijaPendiente(f))) m.set(clave, 'pendiente');
      else m.set(clave, 'adicional');
    }
    return m;
  }, [fichasPorClave]);

  // Los popups se arman al abrirlos, no al montar la capa: son 6.000 polígonos
  // y componer el HTML de todos por adelantado congela la pantalla.
  const indices = useRef({ fichasPorClave, estadoDePredio });
  indices.current = { fichasPorClave, estadoDePredio };

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
            ) : c.porEstadoDeFicha ? (
              <span className="flex shrink-0 rounded-sm overflow-hidden">
                {(Object.keys(COLOR_PREDIO) as EstadoPredio[]).map((e) => (
                  <span key={e} className="w-2 h-3" style={{ background: COLOR_PREDIO[e].relleno }} />
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
                    // «Ver todo» sin predios encendidos no enseñaría nada: se
                    // activan solos y el encuadre espera a que carguen
                    if (encuadre === 'obra') {
                      setActivas((prev) => new Set([...prev, 'predios_poly']));
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

              {/* Sobre qué se levanta la obra. Va antes de la procedencia porque
                  es lo que obliga a tomar una decisión, no un dato de contexto. */}
              {magnitud?.vaso && magnitud.vaso.predios.length > 0 && (
                <div className="mt-3 rounded-lg p-3 text-[11px] leading-relaxed border"
                     style={{ background: 'var(--bg-primary)',
                              borderColor: magnitud.vaso.investigada_ha > 0 ? '#dc262666' : '#f59e0b66',
                              color: 'var(--text-muted)' }}>
                  <div className={`flex items-center gap-1.5 mb-1.5 font-semibold ${
                    magnitud.vaso.investigada_ha > 0 ? 'text-red-400' : 'text-amber-400'}`}>
                    <AlertTriangle className="w-3.5 h-3.5" /> Sobre qué se levanta la obra
                  </div>
                  <p className="mb-2">
                    El área de proyecto se apoya sobre{' '}
                    <b>{magnitud.vaso.predios.length} predios catastrales</b>
                    {magnitud.vaso.investigada_ha > 0
                      ? ', y parte de esa superficie está investigada por el padrón.'
                      : '. Ninguno tiene ficha en el padrón: la obra no se levanta sobre el predio de ningún regante.'}
                  </p>
                  <div className="flex justify-between"><span>Área de proyecto</span>
                    <b>{num(magnitud.vaso.area_ha, 2)} ha</b></div>
                  <div className="flex justify-between"><span>Sobre predio catastrado</span>
                    <b>{num(magnitud.vaso.cubierta_ha, 2)} ha ({magnitud.vaso.cubierta_pct}%)</b></div>
                  <div className="flex justify-between"><span>Sin predio catastrado</span>
                    <b>{num(magnitud.vaso.libre_ha, 2)} ha</b></div>
                  <div className="flex justify-between"><span>Sobre predio del padrón</span>
                    <b className={magnitud.vaso.investigada_ha > 0
                      ? 'text-red-400' : 'text-emerald-400'}>
                      {num(magnitud.vaso.investigada_ha, 2)} ha</b></div>

                  {magnitud.vaso.predios
                    .filter((r) => r.ha_en_vaso >= 0.1)
                    .map((r) => (
                    <div key={r.clave} className="mt-2 pt-2 border-t"
                         style={{ borderColor: 'var(--border-color)' }}>
                      <div className="font-semibold" style={{ color: 'var(--text-secondary)' }}>
                        {r.nombre_predio ?? `Predio ${r.clave}`}
                      </div>
                      <div className="mb-1">
                        clave {r.clave}
                        {r.tipo_predio ? ` · ${r.tipo_predio}` : ''}
                      </div>
                      <div>
                        <b>{num(r.ha_en_vaso, 2)} ha</b> dentro del proyecto — el
                        {' '}{r.pct_del_vaso}% del área de la obra y el {r.pct_del_predio}% de sus
                        {' '}{num(r.area_predio_ha, 2)} ha.
                      </div>
                      {r.condicion && (
                        <div className="mt-1 text-emerald-400">{r.condicion}</div>
                      )}
                      {r.detalle_condicion && (
                        <div style={{ color: 'var(--text-secondary)' }}>{r.detalle_condicion}</div>
                      )}
                      {r.investigado ? (
                        <div className="mt-1 text-red-400">
                          ⚠ Investigado por el padrón: ficha {r.codigo_ficha} de {r.propietario}
                          {r.tenencia ? ` · ${r.tenencia}` : ''}
                        </div>
                      ) : (
                        <div className="mt-1">Sin ficha en el padrón.</div>
                      )}
                      {!r.condicion && !r.investigado && (
                        <div className="text-amber-400/90">
                          Su condición jurídica no se ha consultado al GADM.
                        </div>
                      )}
                    </div>
                  ))}

                  <button
                    onClick={() => {
                      setActivas((prev) => new Set([...prev, 'vaso']));
                      setIrAlVaso((n) => n + 1);
                    }}
                    className="mt-2 w-full flex items-center justify-center gap-1 px-2 py-1
                               rounded-md cursor-pointer hover:bg-white/10 border"
                    style={{ borderColor: 'var(--border-color)', color: 'var(--text-secondary)' }}
                  >
                    <Maximize2 className="w-3 h-3" /> Ver en el mapa
                  </button>

                  <p className="mt-2 pt-2 border-t" style={{ borderColor: 'var(--border-color)' }}>
                    Cómo se calcula: los polígonos del catastro rural del GADM cruzados con el
                    límite de proyecto (con el vértice 23 corregido), medidos en UTM 17S. La
                    condición de cada predio la aporta la ficha catastral del municipio, no el
                    archivo. Se recalcula en cada sincronización.
                  </p>
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
                sistema={datos['predios_poly'] ?? datos['predios']}
                modo={encuadre}
              />
              <IrAlPredioOcupado trigger={irAlVaso} datos={datos['vaso']} />
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
                  // los predios se recolorean cuando llegan las fichas: sin la
                  // clave en el key, Leaflet conserva el estilo del primer render
                  key={c.porEstadoDeFicha ? `${c.id}-${estadoDePredio.size}` : c.id}
                  data={datos[c.id] as never}
                  style={(f) => {
                    if (c.porSector) {
                      return { ...c.estilo,
                               color: colorDeSector(f?.properties?.sector),
                               fillColor: colorDeSector(f?.properties?.sector) };
                    }
                    if (c.porEstadoDeFicha) {
                      const clave = String(f?.properties?.clave_cata ?? '').trim();
                      const col = COLOR_PREDIO[indices.current.estadoDePredio.get(clave)
                                               ?? 'principal'];
                      return { ...c.estilo, color: col.borde, fillColor: col.relleno };
                    }
                    if (c.id === 'vaso') {
                      // el predio entero con borde punteado; la parte que la obra
                      // ocupa, rellena. Rojo solo si es un predio del padrón: ahí
                      // hay alguien con quien negociar
                      const col = f?.properties?.investigado ? '#dc2626' : '#f59e0b';
                      return f?.properties?.tipo === 'solape'
                        ? { color: col, weight: 1, fillColor: col, fillOpacity: 0.5 }
                        : { color: col, weight: 2, dashArray: '5 4', fillOpacity: 0.04 };
                    }
                    return c.estilo;
                  }}
                  pointToLayer={(f, latlng) => L.circleMarker(latlng, {
                    ...c.estilo,
                    radius: 2.5,
                    color: colorDeSector(f?.properties?.sector),
                    fillColor: colorDeSector(f?.properties?.sector),
                  })}
                  onEachFeature={(f, layer) => {
                    const p = (f.properties ?? {}) as Record<string, unknown>;

                    if (c.porEstadoDeFicha) {
                      // Popup perezoso: 6.000 polígonos y solo se abre uno
                      layer.bindPopup(() => popupDePredio(p, indices.current), {
                        maxWidth: 320,
                      });
                      layer.bindTooltip(() => {
                        const clave = String(p.clave_cata ?? '').trim();
                        const fs = indices.current.fichasPorClave.get(clave) ?? [];
                        const quien = fs[0]
                          ? `${fs[0].apellidos ?? ''} ${fs[0].nombres ?? ''}`.trim()
                          : `${p.apellidos ?? ''} ${p.nombres ?? ''}`.trim();
                        return `<b>${quien || 'Sin propietario en la ficha'}</b><br/>
                                ${clave || '—'} · clic para el detalle`;
                      }, { sticky: true, opacity: 0.9 });
                      return;
                    }

                    if (c.id === 'vaso') {
                      layer.bindPopup(popupDeVaso(p), { maxWidth: 320 });
                      return;
                    }

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
