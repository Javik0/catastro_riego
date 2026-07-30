import { useState } from 'react';
import { Sprout, PawPrint, Ruler, FileText, MapPin } from 'lucide-react';
import { type FichaPredio, type CultivoAgricola, type AnimalEspecie, esFichaHija, esHijaPendiente, esLoteFraccionamiento } from '../../lib/types';
import { getNombreTecnico } from '../../lib/constants';

/**
 * Tarjeta de Predio (v4.4) — contenido del popup al hacer clic en un polígono
 * catastral del mapa web. Muestra los datos relevantes de la(s) ficha(s) del
 * predio: superficies con barra de riego, cultivos con áreas y animales.
 */

interface PredioCatastral {
  clave_cata: string;
  area_predi?: number;
  apellidos?: string;
  nombres?: string;
  cedula?: string;
  comunidad?: string;
}

interface Props {
  predio: PredioCatastral;
  fichas: FichaPredio[];              // fichas asociadas a esta clave catastral
  cultivosPorFicha: Map<string, CultivoAgricola[]>;
  animalesPorFicha: Map<string, AnimalEspecie[]>;
  onVerFicha: (f: FichaPredio) => void;
  /** v4.6: resuelve la ficha madre de una adicional (por ficha_madre_id) */
  resolverMadre?: (f: FichaPredio) => FichaPredio | undefined;
  /** v4.6: resuelve los predios adicionales declarados por una ficha principal */
  resolverHijas?: (f: FichaPredio) => FichaPredio[];
  /** v4.6: navegar en el mapa hacia otra ficha (madre o adicional) */
  onIrAMadre?: (madre: FichaPredio) => void;
}

const fmt = (n: number | undefined | null) =>
  n != null && isFinite(n) ? Math.round(n).toLocaleString('es-EC') : '—';

export default function PredioPopupCard({ predio, fichas, cultivosPorFicha, animalesPorFicha, onVerFicha, resolverMadre, resolverHijas, onIrAMadre }: Props) {
  const [idx, setIdx] = useState(0);
  const [filtro, setFiltro] = useState('');
  const ficha = fichas[Math.min(idx, fichas.length - 1)];

  // ── Polígono SIN ficha de riego (v4.5): datos básicos del catastro para
  // identificarlo y planificar el alcance de investigación ──
  if (!ficha) {
    const dueno = `${predio.apellidos || ''} ${predio.nombres || ''}`.trim();
    return (
      <div className="text-xs min-w-[240px] max-w-[290px]">
        <div className="border-b pb-1.5 mb-2">
          <div className="flex items-start justify-between gap-2">
            <div className="font-bold text-sm leading-tight">
              {dueno || 'Propietario no registrado en catastro'}
            </div>
            <span className="shrink-0 px-1.5 py-0.5 rounded-full text-[9px] font-bold border whitespace-nowrap bg-amber-50 text-amber-700 border-amber-300">
              Sin investigar
            </span>
          </div>
          <div className="text-[10px] opacity-70 font-mono mt-0.5 flex items-center gap-1">
            <MapPin className="w-3 h-3" /> {predio.clave_cata}
          </div>
        </div>
        <div className="space-y-1 mb-2">
          {[
            ['Cédula / RUC', predio.cedula || '—'],
            ['Comunidad', predio.comunidad || '—'],
            ['Área catastral', predio.area_predi ? `${fmt(predio.area_predi)} m²` : '—'],
          ].map(([k, v]) => (
            <div key={k} className="flex justify-between gap-2">
              <span className="opacity-60">{k}:</span>
              <span className="font-medium text-right">{v}</span>
            </div>
          ))}
        </div>
        <div className="rounded-lg border border-dashed border-amber-300 bg-amber-50 px-2 py-1.5 text-[10px] text-amber-800 text-center">
          📋 Predio sin ficha de riego — candidato a investigación de alcance
        </div>
      </div>
    );
  }

  const hijaPend = esHijaPendiente(ficha);
  const esHija = esFichaHija(ficha);
  const madre = esHija && resolverMadre ? resolverMadre(ficha) : undefined;
  const otrosPredios = !esHija && resolverHijas ? resolverHijas(ficha) : [];

  // v4.6: lista compacta — conservar el índice original para la selección
  const totalPend = fichas.filter(esHijaPendiente).length;
  const q = filtro.trim().toLowerCase();
  const fichasVisibles = fichas
    .map((f, i) => ({ f, i }))
    .filter(({ f }) =>
      !q ||
      `${f.apellidos || ''} ${f.nombres || ''} ${f.propietario || ''} ${f.codigo_final || ''}`
        .toLowerCase()
        .includes(q)
    );
  const cultivos = (cultivosPorFicha.get(ficha.id) || [])
    .slice()
    .sort((a, b) => (b.superficie_m2 || 0) - (a.superficie_m2 || 0));
  const animales = animalesPorFicha.get(ficha.id) || [];

  const areaTotal = ficha.area_total || predio.area_predi || 0;
  const areaRiego = Math.min(ficha.area_riego || 0, areaTotal || Infinity);
  const pctRiego = areaTotal > 0 ? Math.round((areaRiego / areaTotal) * 100) : 0;
  const maxCultivo = Math.max(...cultivos.map((c) => c.superficie_m2 || 0), 1);

  return (
    <div className="text-xs min-w-[250px] max-w-[290px]">
      {/* Encabezado */}
      <div className="border-b pb-1.5 mb-2">
        <div className="flex items-start justify-between gap-2">
          <div className="font-bold text-sm leading-tight">
            {ficha.propietario || `${ficha.apellidos || ''} ${ficha.nombres || ''}`.trim()}
          </div>
          <span className={`shrink-0 px-1.5 py-0.5 rounded-full text-[9px] font-bold border whitespace-nowrap ${
            hijaPend
              ? 'bg-slate-100 text-slate-600 border-slate-300'
              : esHija
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                : 'bg-blue-50 text-blue-700 border-blue-200'
          }`}>
            {hijaPend ? '⚪ Pendiente S4' : esHija ? '✅ Adicional completada' : 'Investigado'}
          </span>
        </div>
        <div className="text-[10px] opacity-70 font-mono mt-0.5">
          {predio.clave_cata}{ficha.comunidad ? ` · ${ficha.comunidad}` : ''}
        </div>
        {/* Varias fichas en el mismo polígono (multi-declarante / herencias / fraccionamiento) */}
        {fichas.length > 1 && (
          <div className="mt-1.5">
            {/* v4.6: resumen del predio */}
            <div className="text-[9px] opacity-70 mb-1">
              <b>{fichas.length}</b> fichas en este predio
              {totalPend > 0 && <> · <b>{totalPend}</b> pendientes S4 · <b>{fichas.length - totalPend}</b> investigadas</>}
            </div>
            {/* v4.6: buscador cuando la lista es larga */}
            {fichas.length > 15 && (
              <input
                type="text"
                value={filtro}
                onChange={(e) => setFiltro(e.target.value)}
                onClick={(e) => e.stopPropagation()}
                placeholder={`Filtrar ${fichas.length} fichas por apellido...`}
                className="w-full mb-1 px-1.5 py-1 text-[10px] rounded border border-gray-300 outline-none focus:border-blue-400"
              />
            )}
            {/* v4.6: contenedor con scroll — el popup ya no se desborda */}
            <div className="flex flex-wrap gap-1 max-h-[104px] overflow-y-auto pr-1">
              {fichasVisibles.map(({ f, i }) => (
                <button
                  key={f.id}
                  onClick={(e) => { e.stopPropagation(); setIdx(i); }}
                  className={`px-1.5 py-0.5 rounded text-[9px] font-semibold border cursor-pointer ${
                    i === Math.min(idx, fichas.length - 1)
                      ? 'bg-blue-600 text-white border-blue-600'
                      : esHijaPendiente(f)
                        ? 'bg-slate-50 text-slate-500 border-slate-300 border-dashed hover:bg-slate-100'
                        : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
                  }`}
                  title={f.propietario || f.codigo_final}
                >
                  {i + 1}. {(f.apellidos || f.codigo_final || '').split(' ')[0]}
                </button>
              ))}
              {fichasVisibles.length === 0 && (
                <span className="text-[9px] opacity-60 py-1">Sin coincidencias para «{filtro}»</span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* v4.6: vínculo con el regante principal (ficha madre) */}
      {esHija && madre && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 px-2 py-1.5 mb-2">
          <div className="text-[9px] font-semibold uppercase tracking-wider text-blue-500 mb-0.5">
            Regante principal (ficha madre)
          </div>
          <div className="flex items-center justify-between gap-2">
            <div className="min-w-0">
              <div className="text-[11px] font-semibold text-blue-900 leading-tight truncate">
                {madre.propietario || `${madre.apellidos || ''} ${madre.nombres || ''}`.trim() || madre.codigo_final}
              </div>
              {madre.clave_catastral && (
                <div className="font-mono text-[10px] text-blue-700">{madre.clave_catastral}</div>
              )}
            </div>
            {onIrAMadre && (
              <button
                onClick={(e) => { e.stopPropagation(); onIrAMadre(madre); }}
                className="shrink-0 flex items-center gap-1 px-1.5 py-1 rounded bg-blue-600 hover:bg-blue-700 text-white text-[9px] font-bold cursor-pointer"
                title="Ver el predio del regante principal en el mapa"
              >
                <MapPin className="w-3 h-3" /> Ir al predio
              </button>
            )}
          </div>
        </div>
      )}

      {/* v4.6: lote de fraccionamiento — producción asignada, no levantada en campo */}
      {esLoteFraccionamiento(ficha) && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 px-2 py-1.5 mb-2">
          <div className="text-[10px] font-bold text-amber-800">📦 Lote de fraccionamiento</div>
          <div className="text-[9px] text-amber-700 mt-0.5">
            Digitalizado del plano comunal. La producción fue asignada por criterio
            técnico y está pendiente de verificación en campo.
          </div>
        </div>
      )}

      {/* v4.6: navegación inversa — otros predios declarados por este regante */}
      {otrosPredios.length > 0 && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 px-2 py-1.5 mb-2">
          <div className="text-[9px] font-semibold uppercase tracking-wider text-blue-500 mb-1">
            Otros predios declarados ({otrosPredios.length})
          </div>
          <div className="space-y-1 max-h-[104px] overflow-y-auto pr-0.5">
            {otrosPredios.map((h, i) => (
              <button
                key={h.id}
                onClick={(e) => { e.stopPropagation(); onIrAMadre?.(h); }}
                className="w-full flex items-center justify-between gap-2 px-1.5 py-1 rounded border border-blue-200 bg-white hover:bg-blue-100 cursor-pointer text-left"
                title="Ver este predio en el mapa"
              >
                <span className="text-[10px] text-blue-900 truncate">
                  {i + 1}. {h.comunidad || h.sector || h.codigo_final}
                  {h.area_total ? ` — ${fmt(h.area_total)} m²` : ''}
                </span>
                <span className="shrink-0 text-[9px]">{esHijaPendiente(h) ? '⚪' : '✅'}</span>
              </button>
            ))}
          </div>
          <div className="text-[8px] text-blue-600 mt-1">
            Declarados en la Sección 7 · clic para ubicarlos
          </div>
        </div>
      )}

      {/* Superficies con barra de riego */}
      <div className="mb-2">
        <div className="flex justify-between items-center mb-1">
          <span className="flex items-center gap-1 opacity-70">
            <Ruler className="w-3 h-3" /> Superficie
          </span>
          <span className="font-semibold">{fmt(areaTotal)} m²</span>
        </div>
        <div className="h-2 rounded-full bg-gray-200 overflow-hidden">
          <div className="h-full rounded-full bg-blue-500" style={{ width: `${pctRiego}%` }} />
        </div>
        <div className="flex justify-between text-[10px] mt-0.5">
          <span className="text-blue-700 font-medium">Con riego {fmt(areaRiego)} m² ({pctRiego}%)</span>
          <span className="opacity-60">Sin riego {fmt(Math.max(areaTotal - areaRiego, 0))} m²</span>
        </div>
      </div>

      {/* Producción */}
      {hijaPend ? (
        <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 px-2 py-2 mb-2 text-[11px] text-slate-600 text-center">
          🔍 Producción pendiente de investigación en campo
          <span className="block text-[9px] opacity-70 mt-0.5">
            Ficha adicional generada desde la Sección 7 del regante
          </span>
        </div>
      ) : (
        <>
          {/* Cultivos con mini-barras */}
          {cultivos.length > 0 && (
            <div className="mb-2">
              <div className="flex items-center gap-1 opacity-70 mb-1">
                <Sprout className="w-3 h-3 text-green-600" /> Cultivos
              </div>
              <div className="space-y-1">
                {cultivos.slice(0, 5).map((c, i) => (
                  <div key={i} className="grid items-center gap-1.5" style={{ gridTemplateColumns: '85px 1fr 58px' }}>
                    <span className="truncate" title={c.tipo_cultivo}>
                      {c.tipo_cultivo || c.tipo_cultivo_otro || '—'}
                      {c.es_principal ? <span className="ml-1 text-[8px] px-1 rounded-full bg-green-100 text-green-700 border border-green-200">ppal</span> : null}
                    </span>
                    <div className="h-1.5 rounded-full bg-gray-200 overflow-hidden">
                      <div className="h-full rounded-full bg-green-500"
                        style={{ width: `${Math.max(((c.superficie_m2 || 0) / maxCultivo) * 100, 4)}%` }} />
                    </div>
                    <span className="text-right text-[10px] opacity-70">{fmt(c.superficie_m2)} m²</span>
                  </div>
                ))}
                {cultivos.length > 5 && (
                  <div className="text-[9px] opacity-60 text-right">+ {cultivos.length - 5} cultivo(s) más en la ficha</div>
                )}
              </div>
            </div>
          )}

          {/* Especies pecuarias — mismo tratamiento visual que los cultivos:
              ordenadas por cantidad, con mini-barra proporcional */}
          {animales.length > 0 && (() => {
            const ordenados = animales.slice().sort((a, b) => (b.cantidad || 0) - (a.cantidad || 0));
            const maxAnimal = Math.max(...ordenados.map((a) => a.cantidad || 0), 1);
            return (
              <div className="mb-2">
                <div className="flex items-center gap-1 opacity-70 mb-1">
                  <PawPrint className="w-3 h-3 text-pink-600" /> Especies pecuarias
                </div>
                <div className="space-y-1">
                  {ordenados.slice(0, 6).map((a, i) => (
                    <div key={i} className="grid items-center gap-1.5" style={{ gridTemplateColumns: '85px 1fr 58px' }}>
                      <span className="truncate" title={a.especie || a.especie_otro || undefined}>
                        {a.especie || a.especie_otro || '—'}
                      </span>
                      <div className="h-1.5 rounded-full bg-gray-200 overflow-hidden">
                        <div className="h-full rounded-full bg-pink-500"
                          style={{ width: `${Math.max(((a.cantidad || 0) / maxAnimal) * 100, 4)}%` }} />
                      </div>
                      <span className="text-right text-[10px] opacity-70">
                        {(a.cantidad ?? 0).toLocaleString('es-EC')} {(a.cantidad ?? 0) === 1 ? 'cabeza' : 'cabezas'}
                      </span>
                    </div>
                  ))}
                  {ordenados.length > 6 && (
                    <div className="text-[9px] opacity-60 text-right">+ {ordenados.length - 6} especie(s) más en la ficha</div>
                  )}
                </div>
              </div>
            );
          })()}

          {cultivos.length === 0 && animales.length === 0 && (
            <div className="rounded-lg border border-dashed border-gray-300 px-2 py-1.5 mb-2 text-[10px] text-gray-500 text-center">
              Sin cultivos ni animales registrados en esta ficha
            </div>
          )}
        </>
      )}

      {/* Pie: técnico + acción */}
      <div className="flex items-center justify-between border-t pt-1.5">
        <span className="text-[10px] opacity-60">
          {hijaPend ? 'Por asignar en campo' : `Téc. ${getNombreTecnico(ficha.completado_por || ficha.creado_por)}`}
        </span>
        <button
          onClick={(e) => { e.stopPropagation(); onVerFicha(ficha); }}
          className="flex items-center gap-1 px-2 py-1 rounded-md bg-blue-600 hover:bg-blue-700 text-white text-[10px] font-semibold cursor-pointer"
        >
          <FileText className="w-3 h-3" /> Ver ficha completa
        </button>
      </div>
    </div>
  );
}
