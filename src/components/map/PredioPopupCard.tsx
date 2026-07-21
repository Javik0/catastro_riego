import { useState } from 'react';
import { Sprout, PawPrint, Ruler, FileText, MapPin } from 'lucide-react';
import { type FichaPredio, type CultivoAgricola, type AnimalEspecie, esFichaHija, esHijaPendiente } from '../../lib/types';
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
  comunidad?: string;
}

interface Props {
  predio: PredioCatastral;
  fichas: FichaPredio[];              // fichas asociadas a esta clave catastral
  cultivosPorFicha: Map<string, CultivoAgricola[]>;
  animalesPorFicha: Map<string, AnimalEspecie[]>;
  onVerFicha: (f: FichaPredio) => void;
}

const fmt = (n: number | undefined | null) =>
  n != null && isFinite(n) ? Math.round(n).toLocaleString('es-EC') : '—';

export default function PredioPopupCard({ predio, fichas, cultivosPorFicha, animalesPorFicha, onVerFicha }: Props) {
  const [idx, setIdx] = useState(0);
  const ficha = fichas[Math.min(idx, fichas.length - 1)];

  // ── Polígono sin ficha asociada ──
  if (!ficha) {
    return (
      <div className="text-xs min-w-[230px] max-w-[280px]">
        <div className="font-bold text-sm border-b pb-1.5 mb-2">
          {`${predio.apellidos || ''} ${predio.nombres || ''}`.trim() || 'Predio catastral'}
        </div>
        <div className="flex items-center gap-1 text-[11px] opacity-70 font-mono mb-2">
          <MapPin className="w-3 h-3" /> {predio.clave_cata}
        </div>
        <div className="rounded-lg border border-dashed border-gray-300 px-2 py-2 text-[11px] text-gray-500 text-center">
          Sin ficha de riego asociada — {fmt(predio.area_predi)} m² según catastro
        </div>
      </div>
    );
  }

  const hijaPend = esHijaPendiente(ficha);
  const esHija = esFichaHija(ficha);
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
            {hijaPend ? '⚪ Pendiente S4' : esHija ? '✅ Hija completada' : 'Investigado'}
          </span>
        </div>
        <div className="text-[10px] opacity-70 font-mono mt-0.5">
          {predio.clave_cata}{ficha.comunidad ? ` · ${ficha.comunidad}` : ''}
        </div>
        {/* Varias fichas en el mismo polígono (multi-declarante / herencias) */}
        {fichas.length > 1 && (
          <div className="flex flex-wrap gap-1 mt-1.5">
            {fichas.map((f, i) => (
              <button
                key={f.id}
                onClick={(e) => { e.stopPropagation(); setIdx(i); }}
                className={`px-1.5 py-0.5 rounded text-[9px] font-semibold border cursor-pointer ${
                  i === Math.min(idx, fichas.length - 1)
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
                }`}
                title={f.propietario || f.codigo_final}
              >
                {i + 1}. {(f.apellidos || f.codigo_final || '').split(' ')[0]}
              </button>
            ))}
          </div>
        )}
      </div>

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
            Ficha hija generada desde la Sección 7 del regante
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

          {/* Animales como chips */}
          {animales.length > 0 && (
            <div className="mb-2">
              <div className="flex items-center gap-1 opacity-70 mb-1">
                <PawPrint className="w-3 h-3 text-pink-600" /> Animales
              </div>
              <div className="flex flex-wrap gap-1">
                {animales.map((a, i) => (
                  <span key={i} className="px-1.5 py-0.5 rounded-full border border-gray-300 bg-gray-50 text-[10px]">
                    {(a.especie || a.especie_otro || '—')} · {a.cantidad ?? '—'}
                  </span>
                ))}
              </div>
            </div>
          )}

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
