// ═══════════════════════════════════════════════════════════════════════════
// Asignar comunidad a mano, mirando el mapa
//
// Las fichas que quedan sin comunidad son las que ningún criterio automático
// puede cerrar: están en la frontera entre dos o tres comunidades, o aisladas.
// El script prefiere no asignar antes que asignar mal, y eso las mandaba a
// campo — cuando en realidad una persona que ve el mapa las resuelve mirando.
//
// Esta pantalla pone delante lo único que hace falta para decidir: dónde cae
// el punto, qué comunidades tiene alrededor, a cuántos metros está cada una y
// cuántas de sus fichas vecinas son de cada cual.
//
// No escribe en el data.gpkg —la web es estática—. Las decisiones se guardan
// en el navegador y se exportan con el botón de abajo, para aplicarlas con
// `scripts/aplicar_comunidad_manual.py`.
// ═══════════════════════════════════════════════════════════════════════════
import { useEffect, useMemo, useState } from 'react';
import { MapContainer, TileLayer, LayersControl, GeoJSON, CircleMarker, Tooltip, useMap } from 'react-leaflet';
import { Check, Copy, MapPin, Users, X } from 'lucide-react';
import 'leaflet/dist/leaflet.css';

type Candidata = {
  nombre: string; sector: string; dist: number; dentro: boolean;
  vecinas: number; geo: GeoJSON.Geometry;
};
type ComunaOficial = { nombre: string; dist: number; dentro: boolean; geo: GeoJSON.Geometry };
type Ficha = {
  uid: string; clave: string; nombre: string; ced: string; tel: string;
  sec: string; tec: string; area: number; obs: string;
  lon?: number; lat?: number; sin_gps?: boolean;
  comuna_oficial?: string; candidatas: Candidata[];
  comunas_oficiales?: ComunaOficial[];
};

const CLAVE_GUARDADO = 'asignar-comunidad-decisiones';
// Un color por candidata, en el orden en que se listan (más cerca primero).
const COLORES = ['#2563eb', '#16a34a', '#d97706', '#dc2626', '#7c3aed', '#0891b2'];

function fmt(n: number) {
  return n.toLocaleString('es-EC');
}

/** Encuadra el mapa sobre la ficha y sus candidatas cada vez que cambia. */
function Encuadrar({ ficha }: { ficha: Ficha | null }) {
  const map = useMap();
  useEffect(() => {
    if (!ficha?.lat || !ficha?.lon) return;
    // el zoom sale de la distancia a la candidata más lejana que se dibuja:
    // si están todas pegadas conviene acercarse, si hay una a 1 km no.
    const lejos = Math.max(...ficha.candidatas.map((c) => c.dist), 50);
    const zoom = lejos > 800 ? 14 : lejos > 300 ? 15 : lejos > 100 ? 16 : 17;
    map.setView([ficha.lat, ficha.lon], zoom, { animate: true });
  }, [ficha, map]);
  return null;
}

export default function AsignarComunidad({ onCerrar }: { onCerrar: () => void }) {
  const [fichas, setFichas] = useState<Ficha[]>([]);
  const [sel, setSel] = useState<Ficha | null>(null);
  const [decisiones, setDecisiones] = useState<Record<string, string>>({});
  const [copiado, setCopiado] = useState(false);

  useEffect(() => {
    fetch('/geo/asignar_comunidad.json')
      .then((r) => r.json())
      .then((d) => {
        setFichas(d.fichas || []);
        setSel((d.fichas || [])[0] || null);
      })
      .catch(() => setFichas([]));
    try {
      const g = localStorage.getItem(CLAVE_GUARDADO);
      if (g) setDecisiones(JSON.parse(g));
    } catch { /* si el navegador lo bloquea, se trabaja sin memoria */ }
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem(CLAVE_GUARDADO, JSON.stringify(decisiones));
    } catch { /* idem */ }
  }, [decisiones]);

  const decididas = Object.keys(decisiones).length;

  const texto = useMemo(() => {
    const filas = fichas
      .filter((f) => decisiones[f.uid])
      .map((f) => `${f.uid}\t${f.clave}\t${f.nombre}\t${decisiones[f.uid]}`);
    return filas.join('\n');
  }, [fichas, decisiones]);

  function elegir(uid: string, comunidad: string) {
    setDecisiones((d) => {
      const n = { ...d };
      if (n[uid] === comunidad) delete n[uid];   // volver a pulsar la quita
      else n[uid] = comunidad;
      return n;
    });
  }

  async function copiar() {
    try {
      await navigator.clipboard.writeText(texto);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2000);
    } catch { /* si no hay permiso, queda el textarea de abajo */ }
  }

  return (
    <div className="fixed inset-0 z-[3000] flex flex-col bg-white">
      <div className="flex items-center justify-between border-b bg-gray-50 px-4 py-2.5">
        <div>
          <h2 className="text-sm font-semibold text-gray-900">
            Asignar comunidad a mano
          </h2>
          <p className="text-[11px] text-gray-600">
            {fichas.length} fichas sin comunidad · {decididas} decidida{decididas === 1 ? '' : 's'}
            {' · '}el mapa muestra el punto y las comunidades de alrededor
          </p>
        </div>
        <button onClick={onCerrar}
                className="rounded p-1.5 text-gray-500 hover:bg-gray-200 hover:text-gray-900">
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="flex min-h-0 flex-1">
        {/* lista de fichas */}
        <div className="w-[300px] shrink-0 overflow-y-auto border-r">
          {fichas.map((f) => {
            const activa = sel?.uid === f.uid;
            const elegida = decisiones[f.uid];
            return (
              <button key={f.uid} onClick={() => setSel(f)}
                      className={`w-full border-b px-3 py-2 text-left transition
                                  ${activa ? 'bg-blue-50' : 'hover:bg-gray-50'}`}>
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="font-mono text-[10px] text-gray-500">{f.clave}</div>
                    <div className="truncate text-xs font-medium text-gray-900">{f.nombre}</div>
                  </div>
                  {elegida && <Check className="h-3.5 w-3.5 shrink-0 text-green-600" />}
                </div>
                {elegida ? (
                  <div className="mt-0.5 truncate text-[10px] font-semibold text-green-700">
                    → {elegida}
                  </div>
                ) : f.sin_gps ? (
                  <div className="mt-0.5 text-[10px] text-red-600">sin coordenadas</div>
                ) : (
                  <div className="mt-0.5 text-[10px] text-gray-500">
                    {f.candidatas[0]?.nombre} a {f.candidatas[0]?.dist} m
                  </div>
                )}
              </button>
            );
          })}
        </div>

        {/* mapa */}
        <div className="relative min-w-0 flex-1">
          {sel?.lat && sel?.lon ? (
            <MapContainer center={[sel.lat, sel.lon]} zoom={16} className="h-full w-full">
              <LayersControl position="topright">
                <LayersControl.BaseLayer checked name="Satélite">
                  <TileLayer
                    url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                    attribution="Esri" />
                </LayersControl.BaseLayer>
                <LayersControl.BaseLayer name="Calles">
                  <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                             attribution="OpenStreetMap" />
                </LayersControl.BaseLayer>
              </LayersControl>
              <Encuadrar ficha={sel} />
              {/* Debajo de todo, el límite comunal territorial que entregó el
                  contratante (comunas_cy.shp). No es lo que se elige —el padrón
                  guarda organizaciones de riego— pero es el territorio que la
                  gente reconoce, y ayuda a situarse. Mismo amarillo punteado
                  que en el mapa del padrón. */}
              {(sel.comunas_oficiales || []).map((c) => (
                <GeoJSON key={`of-${sel.uid}-${c.nombre}`} data={c.geo as never}
                         style={{ color: '#eab308', weight: 2, dashArray: '6 4',
                                  fillOpacity: 0.04 }}>
                  <Tooltip sticky>
                    Comuna <b>{c.nombre}</b>
                    <br />
                    <span className="text-[10px]">límite territorial (GAD), no es la comunidad de riego</span>
                  </Tooltip>
                </GeoJSON>
              ))}
              {sel.candidatas.map((c, i) => (
                <GeoJSON key={`${sel.uid}-${c.nombre}`} data={c.geo as never}
                         style={{ color: COLORES[i % COLORES.length], weight: 2,
                                  fillOpacity: decisiones[sel.uid] === c.nombre ? 0.35 : 0.12 }}>
                  <Tooltip sticky>
                    <b>{c.nombre}</b><br />
                    {c.dentro ? 'el punto cae dentro' : `a ${c.dist} m`} · {c.vecinas} de 12 vecinas
                  </Tooltip>
                </GeoJSON>
              ))}
              <CircleMarker center={[sel.lat, sel.lon]} radius={8}
                            pathOptions={{ color: '#fff', weight: 3, fillColor: '#ef4444', fillOpacity: 1 }}>
                <Tooltip permanent direction="top" offset={[0, -8]}>
                  <b>{sel.nombre}</b>
                </Tooltip>
              </CircleMarker>
              <div className="pointer-events-none absolute bottom-3 left-3 z-[1000] rounded
                              border border-gray-300 bg-white/95 px-2.5 py-1.5 text-[10px]
                              leading-relaxed text-gray-700 shadow">
                <div className="mb-1 font-semibold uppercase tracking-wide text-gray-500">
                  Qué se ve
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-full bg-red-500 ring-2 ring-white" />
                  la ficha sin comunidad
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="h-2.5 w-3.5 border-2 border-blue-600 bg-blue-600/20" />
                  comunidades de riego · <b>son las que se eligen</b>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="h-2.5 w-3.5 border-2 border-dashed border-yellow-500" />
                  comuna del GAD · solo referencia
                </div>
              </div>
            </MapContainer>
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-gray-500">
              {sel ? 'Esta ficha no tiene coordenadas: no se puede ubicar en el mapa.'
                   : 'Elige una ficha de la lista.'}
            </div>
          )}
        </div>

        {/* panel de decisión */}
        <div className="w-[330px] shrink-0 overflow-y-auto border-l">
          {sel && (
            <div className="p-3">
              <div className="rounded border bg-gray-50 px-2.5 py-2">
                <div className="text-xs font-semibold text-gray-900">{sel.nombre}</div>
                <div className="mt-0.5 font-mono text-[10px] text-gray-500">{sel.clave}</div>
                <div className="mt-1.5 space-y-0.5 text-[11px] text-gray-700">
                  {sel.ced && <div>Cédula: {sel.ced}</div>}
                  {sel.tel && <div>Teléfono: {sel.tel}</div>}
                  <div>Área declarada: {fmt(sel.area)} m²</div>
                  {sel.sec && <div>Sector: {sel.sec}</div>}
                  {sel.comuna_oficial && (
                    <div className="text-cyan-800">
                      Comuna oficial: <b>{sel.comuna_oficial}</b>
                    </div>
                  )}
                </div>
                {sel.obs && (
                  <p className="mt-1.5 border-t pt-1.5 text-[10px] italic text-gray-600">
                    «{sel.obs}»
                  </p>
                )}
              </div>

              <p className="mt-3 mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-gray-500">
                ¿A qué comunidad pertenece?
              </p>
              <div className="space-y-1.5">
                {sel.candidatas.map((c, i) => {
                  const activa = decisiones[sel.uid] === c.nombre;
                  return (
                    <button key={c.nombre} onClick={() => elegir(sel.uid, c.nombre)}
                            className={`w-full rounded border px-2.5 py-2 text-left transition
                                        ${activa ? 'border-green-500 bg-green-50 ring-1 ring-green-500'
                                                 : 'border-gray-200 hover:border-gray-400 hover:bg-gray-50'}`}>
                      <div className="flex items-center gap-2">
                        <span className="h-3 w-3 shrink-0 rounded-sm"
                              style={{ background: COLORES[i % COLORES.length] }} />
                        <span className="min-w-0 flex-1 truncate text-xs font-medium text-gray-900">
                          {c.nombre}
                        </span>
                        {activa && <Check className="h-3.5 w-3.5 shrink-0 text-green-600" />}
                      </div>
                      <div className="mt-1 flex gap-3 pl-5 text-[10px] text-gray-600">
                        <span className="inline-flex items-center gap-1">
                          <MapPin className="h-3 w-3" />
                          {c.dentro ? 'cae dentro' : `${c.dist} m`}
                        </span>
                        <span className="inline-flex items-center gap-1">
                          <Users className="h-3 w-3" />
                          {c.vecinas} de 12 vecinas
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>

              {decisiones[sel.uid] && (
                <button onClick={() => elegir(sel.uid, decisiones[sel.uid])}
                        className="mt-2 w-full rounded border border-gray-200 px-2 py-1 text-[11px]
                                   text-gray-600 hover:bg-gray-50">
                  Quitar la decisión
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* exportar */}
      <div className="border-t bg-gray-50 px-4 py-2.5">
        <div className="flex items-center justify-between gap-3">
          <p className="text-[11px] text-gray-600">
            {decididas === 0
              ? 'Las decisiones se guardan solas en este navegador. Al terminar, cópialas para aplicarlas.'
              : `${decididas} de ${fichas.length} decididas. Cópialas y pásaselas a quien las aplique con el script.`}
          </p>
          <button onClick={copiar} disabled={decididas === 0}
                  className="inline-flex shrink-0 items-center gap-1.5 rounded bg-blue-600 px-3 py-1.5
                             text-xs font-medium text-white hover:bg-blue-700
                             disabled:cursor-not-allowed disabled:bg-gray-300">
            <Copy className="h-3.5 w-3.5" />
            {copiado ? 'Copiado' : 'Copiar decisiones'}
          </button>
        </div>
        {decididas > 0 && (
          <textarea readOnly value={texto} rows={Math.min(decididas, 4)}
                    className="mt-2 w-full rounded border border-gray-300 bg-white p-1.5
                               font-mono text-[10px] text-gray-700" />
        )}
      </div>
    </div>
  );
}
