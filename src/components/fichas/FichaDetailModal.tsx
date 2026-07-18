import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { 
  X, User, MapPin, Droplets, Sprout, ClipboardList, Building, Image as ImageIcon, Printer,
  Hash, CreditCard, Phone, Users, Award, BookOpen, Ruler, Waves, Calendar, Percent, 
  DollarSign, Lightbulb, Compass, Activity, FileText 
} from 'lucide-react';
import { type FichaPredio, safeToDate, type CultivoAgricola, type AnimalEspecie, type PredioAdicional } from '../../lib/types';
import { getNombreTecnico } from '../../lib/constants';
import FichaImpresion from './FichaImpresion';

const BUCKET_NAME = 'invs-riego-comunitario.firebasestorage.app';

interface Props {
  ficha: FichaPredio;
  onClose: () => void;
}

const TABS = [
  { id: 'propietario', label: '1. Propietario', icon: User },
  { id: 'predio', label: '2. Predio y Riego', icon: Droplets },
  { id: 'servicios', label: '3. Servicios', icon: Building },
  { id: 'produccion', label: '4. Producción', icon: Sprout },
  { id: 'regante', label: '5. Otros Pedidos', icon: ClipboardList },
  { id: 'encuesta', label: '6. Encuesta', icon: ClipboardList },
  { id: 'auditoria', label: '7. Auditoría', icon: MapPin },
] as const;

interface FieldProps {
  label: string;
  value: unknown;
  icon?: React.ComponentType<{ className?: string }>;
}

function Field({ label, value, icon: Icon }: FieldProps) {
  if (value == null || value === '') return null;
  const display = typeof value === 'boolean' ? (value ? 'Sí' : 'No') : String(value);
  return (
    <div className="flex items-start gap-3 p-3 rounded-xl border border-slate-800 bg-slate-900/40 hover:border-slate-700/50 hover:bg-slate-800/30 transition-all duration-200 group">
      {Icon && (
        <div className="flex-shrink-0 p-1.5 rounded-lg bg-slate-800/80 text-blue-400 group-hover:text-blue-300 group-hover:bg-slate-800/50 transition-colors">
          <Icon className="w-3.5 h-3.5" />
        </div>
      )}
      <div className="flex flex-col min-w-0">
        <span className="text-[9px] text-slate-500 uppercase tracking-wider font-semibold">{label}</span>
        <span className="text-xs text-slate-100 font-medium break-words mt-0.5">{display}</span>
      </div>
    </div>
  );
}

export default function FichaDetailModal({ ficha, onClose }: Props) {
  const [activeTab, setActiveTab] = useState<string>('propietario');
  const [cultivos, setCultivos] = useState<CultivoAgricola[]>([]);
  const [animales, setAnimales] = useState<AnimalEspecie[]>([]);
  const [prediosAdicionales, setPrediosAdicionales] = useState<PredioAdicional[]>([]);
  const [loadingRelational, setLoadingRelational] = useState(true);

  useEffect(() => {
    const timestamp = Date.now();
    Promise.all([
      fetch(`/geo/cultivos.json?t=${timestamp}`).then(r => r.json()),
      fetch(`/geo/animales.json?t=${timestamp}`).then(r => r.json()),
      fetch(`/geo/predios_adicionales.json?t=${timestamp}`).then(r => r.json())
    ]).then(([allCultivos, allAnimales, allAdicionales]) => {
      const cleanId = (id: string) => id.replace(/[{}]/g, '').toLowerCase().trim();
      const targetId = cleanId(ficha.id);
      
      const filteredCultivos = (allCultivos as CultivoAgricola[]).filter(
        c => c.ficha_id && cleanId(c.ficha_id) === targetId
      );
      const filteredAnimales = (allAnimales as AnimalEspecie[]).filter(
        a => a.ficha_id && cleanId(a.ficha_id) === targetId
      );
      const filteredAdicionales = (allAdicionales as PredioAdicional[]).filter(
        pa => pa.ficha_id && cleanId(pa.ficha_id) === targetId
      );

      setCultivos(filteredCultivos);
      setAnimales(filteredAnimales);
      setPrediosAdicionales(filteredAdicionales);
      setLoadingRelational(false);
    }).catch(err => {
      console.error("Error al cargar datos relacionales:", err);
      setLoadingRelational(false);
    });
  }, [ficha.id]);
 
  useEffect(() => {
    const originalTitle = document.title;
    const cleanName = (ficha.propietario || `${ficha.apellidos}_${ficha.nombres}`)
      .trim()
      .replace(/\s+/g, '_')
      .replace(/[^a-zA-Z0-9_À-ÿ-]/g, '');
    const cleanClave = (ficha.clave_catastral || ficha.codigo_final || 'Predio')
      .trim()
      .replace(/\s+/g, '_')
      .replace(/[^a-zA-Z0-9_-]/g, '');
    
    document.title = `Ficha_Catastral_${cleanClave}_${cleanName}`;
    
    return () => {
      document.title = originalTitle;
    };
  }, [ficha]);

  const obtenerDestino = (item: { es_autoconsumo?: boolean | number; es_mercado?: boolean | number; es_agroindustria?: boolean | number; es_exportacion?: boolean | number }) => {
    const destinos = [];
    if (item.es_autoconsumo) destinos.push('Autoconsumo');
    if (item.es_mercado) destinos.push('Mercado');
    if (item.es_agroindustria) destinos.push('Agroindustria');
    if (item.es_exportacion) destinos.push('Exportación');
    return destinos.length > 0 ? destinos.join(', ') : 'No especificado';
  };

  const renderContent = () => {
    switch (activeTab) {
      case 'propietario':
        return (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Código del Predio" value={ficha.codigo_final} icon={Hash} />
            <Field label="Clave Catastral" value={ficha.clave_catastral} icon={CreditCard} />
            <Field label="Apellidos" value={ficha.apellidos} icon={User} />
            <Field label="Nombres" value={ficha.nombres} icon={User} />
            <Field label="Cédula" value={ficha.cedula} icon={CreditCard} />
            <Field label="Parroquia" value={ficha.parroquia} icon={MapPin} />
            <Field label="Sector" value={ficha.sector} icon={MapPin} />
            <Field label="Comunidad" value={ficha.comunidad} icon={MapPin} />
            <Field label="Sector Comunidad" value={ficha.sector_comunidad} icon={MapPin} />
            <Field label="Teléfono Celular" value={ficha.telefono_celular} icon={Phone} />
            <Field label="Teléfono Casa" value={ficha.telefono_casa} icon={Phone} />
            <Field label="Hijos (Hombres)" value={ficha.hijos_hombres} icon={Users} />
            <Field label="Hijos (Mujeres)" value={ficha.hijos_mujeres} icon={Users} />
            <Field label="Tenencia del Predio" value={ficha.tenencia_predio} icon={Award} />
            <Field label="Nivel de Instrucción" value={ficha.nivel_instruccion} icon={BookOpen} />
          </div>
        );
      case 'predio':
        return (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Org. de Riego" value={ficha.org_riego} icon={Waves} />
            <Field label="Canal" value={ficha.canal} icon={Ruler} />
            <Field label="Caudal (l/s)" value={ficha.caudal_valor} icon={Waves} />
            <Field label="Tipo de Caudal" value={ficha.caudal_tipo} icon={Waves} />
            <Field label="Área Total (m²)" value={ficha.area_total?.toLocaleString('es-EC')} icon={Ruler} />
            <Field label="Área con Riego (m²)" value={ficha.area_riego?.toLocaleString('es-EC')} icon={Droplets} />
            <Field label="Área sin Riego (m²)" value={ficha.area_sin_riego?.toLocaleString('es-EC')} icon={Droplets} />
            <Field label="Frecuencia de Riego" value={ficha.frecuencia_riego} icon={Calendar} />
            <Field label="Gravedad (%)" value={ficha.metodo_gravedad_pct} icon={Percent} />
            <Field label="Aspersión (%)" value={ficha.metodo_aspersion_pct} icon={Percent} />
            <Field label="Goteo (%)" value={ficha.metodo_goteo_pct} icon={Percent} />
            <Field label="Días de Riego" value={ficha.dias_riego} icon={Calendar} />
            <Field label="Horas por Turno" value={ficha.horas_turno} icon={Calendar} />
            <Field label="Valor Tarifa ($)" value={ficha.valor_tarifa} icon={DollarSign} />
            <Field label="Tipo de Tarifa" value={ficha.tipo_tarifa} icon={DollarSign} />
            <Field label="¿Tiene Reservorio?" value={ficha.tiene_reservorio} icon={Droplets} />
          </div>
        );
      case 'servicios':
        return (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="Agua Consumo" value={ficha.agua_consumo} icon={Droplets} />
              <Field label="Energía Eléctrica" value={ficha.energia_electrica} icon={Lightbulb} />
              <Field label="Material Construcción" value={ficha.material_construccion} icon={Building} />
              <Field label="Material (otro)" value={ficha.material_constr_otro} icon={Building} />
              <Field label="COTA (msnm)" value={ficha.cota_msnm} icon={Compass} />
              <Field label="Coordenada X (UTM Este)" value={ficha.coord_x_utm} icon={Compass} />
              <Field label="Coordenada Y (UTM Norte)" value={ficha.coord_y_utm} icon={Compass} />
              <Field label="Datum" value={(ficha as any).datum || 'WGS 84'} icon={Compass} />
              <Field label="Zona UTM" value={(ficha as any).zona_utm || '17S'} icon={Compass} />
            </div>
            <div className="mt-3 p-3 rounded-xl border border-blue-800/30 bg-blue-950/20">
              <p className="text-[9px] text-blue-400 font-bold uppercase tracking-wider mb-1">📍 Referencia Cartográfica</p>
              <p className="text-xs text-blue-300">
                Polígono del predio referenciado a la capa <strong className="text-white">Catastro Rural – GADM Cayambe</strong> (insumo municipal). Datum WGS 84 · Zona 17S.
              </p>
            </div>
          </>
        );
      case 'produccion':
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="Soberanía Alimentaria (%)" value={ficha.soberania_aliment_pct} icon={Percent} />
              <Field label="Act. Productivas (%)" value={ficha.act_productivas_pct} icon={Percent} />
              <Field label="Actividad Productiva" value={ficha.actividad_productiva} icon={Activity} />
            </div>
 
            {loadingRelational ? (
              <div className="text-center py-4 text-xs text-slate-400">Cargando producción...</div>
            ) : (
              <>
                {/* Tabla Cultivos */}
                <div className="border border-slate-700/40 rounded-xl overflow-hidden">
                  <div className="bg-slate-800/40 px-4 py-2 border-b border-slate-700/40 flex items-center gap-2">
                    <Sprout className="w-4 h-4 text-blue-400" />
                    <span className="text-xs font-semibold text-white uppercase tracking-wider">Cultivos Agrícolas ({cultivos.length})</span>
                  </div>
                  {cultivos.length === 0 ? (
                    <div className="p-4 text-center text-xs text-slate-500">No hay cultivos registrados en esta ficha.</div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs border-collapse">
                        <thead>
                          <tr className="bg-slate-800/20 text-slate-400 font-medium">
                            <th className="p-2.5">Cultivo</th>
                            <th className="p-2.5">Superficie</th>
                            <th className="p-2.5">Tipo</th>
                            <th className="p-2.5">Destino</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-700/20 text-slate-300">
                          {cultivos.map((c, i) => (
                            <tr key={i} className="hover:bg-slate-800/10">
                              <td className="p-2.5 font-medium text-white">{c.tipo_cultivo === 'Otros' ? c.tipo_cultivo_otro : c.tipo_cultivo}</td>
                              <td className="p-2.5">{c.superficie_m2 ? `${c.superficie_m2.toLocaleString('es-EC')} m²` : '—'}</td>
                              <td className="p-2.5">
                                {c.es_principal ? (
                                  <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-green-500/10 text-green-400 border border-green-500/20">Principal</span>
                                ) : (
                                  <span className="text-slate-500">Secundario</span>
                                )}
                              </td>
                              <td className="p-2.5">{obtenerDestino(c)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
 
                {/* Tabla Animales */}
                <div className="border border-slate-700/40 rounded-xl overflow-hidden">
                  <div className="bg-slate-800/40 px-4 py-2 border-b border-slate-700/40 flex items-center gap-2">
                    <ClipboardList className="w-4 h-4 text-emerald-400" />
                    <span className="text-xs font-semibold text-white uppercase tracking-wider">Especies Pecuarias ({animales.length})</span>
                  </div>
                  {animales.length === 0 ? (
                    <div className="p-4 text-center text-xs text-slate-500">No hay animales registrados en esta ficha.</div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs border-collapse">
                        <thead>
                          <tr className="bg-slate-800/20 text-slate-400 font-medium">
                            <th className="p-2.5">Especie</th>
                            <th className="p-2.5">Cantidad</th>
                            <th className="p-2.5">Destino</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-700/20 text-slate-300">
                          {animales.map((a, i) => (
                            <tr key={i} className="hover:bg-slate-800/10">
                              <td className="p-2.5 font-medium text-white">{a.especie === 'Otros' ? a.especie_otro : a.especie}</td>
                              <td className="p-2.5">{a.cantidad}</td>
                              <td className="p-2.5">{obtenerDestino(a)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        );
      case 'regante':
        return (
          <div className="space-y-4">
            <div className="bg-slate-800/30 p-3 rounded-lg border border-slate-700/20">
              <p className="text-xs text-slate-400 leading-relaxed">
                Aquí se registran los predios adicionales que forman parte del regante y el prorrateo/asignación de áreas correspondiente.
              </p>
            </div>
            {loadingRelational ? (
              <div className="text-center py-4 text-xs text-slate-400">Cargando predios adicionales...</div>
            ) : prediosAdicionales.length === 0 ? (
              <div className="text-center py-6 text-xs text-slate-500 border border-dashed border-slate-700/40 rounded-xl">
                No hay predios adicionales registrados para este regante.
              </div>
            ) : (
              <div className="space-y-4">
                {prediosAdicionales.map((pa, idx) => (
                  <div key={idx} className="border border-slate-700/40 rounded-xl p-4 bg-slate-800/10 space-y-3">
                    <div className="flex items-center justify-between border-b border-slate-700/20 pb-2">
                      <span className="text-xs font-bold text-blue-400 font-mono">Predio Adicional #{idx + 1}</span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                        Clave: {pa.clave_catastral_otro || '—'}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                      <div className="flex flex-col">
                        <span className="text-[9px] text-slate-500 uppercase tracking-wider font-semibold">Área Total</span>
                        <span className="text-xs font-semibold text-white mt-0.5">{pa.area_total_otro?.toLocaleString('es-EC')} m²</span>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-[9px] text-slate-500 uppercase tracking-wider font-semibold">Lote Asignado</span>
                        <span className="text-xs font-semibold text-white mt-0.5">{pa.area_lote_asignado_otro?.toLocaleString('es-EC')} m²</span>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-[9px] text-slate-500 uppercase tracking-wider font-semibold">Área Riego</span>
                        <span className="text-xs font-semibold text-white mt-0.5">{pa.area_riego_otro?.toLocaleString('es-EC')} m²</span>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-[9px] text-slate-500 uppercase tracking-wider font-semibold">Área Sin Riego</span>
                        <span className="text-xs font-semibold text-white mt-0.5">{pa.area_sin_riego_otro?.toLocaleString('es-EC')} m²</span>
                      </div>
                    </div>
                    {pa.tiene_observaciones && pa.observaciones_otro && (
                      <div className="mt-2 pt-2 border-t border-slate-700/10 flex flex-col gap-0.5">
                        <span className="text-[9px] text-amber-500/80 uppercase tracking-wider font-semibold">Observaciones</span>
                        <p className="text-xs text-slate-300 italic">"{pa.observaciones_otro}"</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      case 'encuesta':
        return (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="¿Conoce el Proyecto Presa?" value={ficha.conoce_presa} icon={Lightbulb} />
            <Field label="¿Cómo se elige la directiva?" value={ficha.como_elige_dir} icon={Users} />
            <Field label="Otro método" value={ficha.como_elige_dir_otro} icon={Users} />
            <Field label="Presidente Junta de Agua" value={ficha.nom_presidente} icon={User} />
            <Field label="Operador del Sistema" value={ficha.operador_sector} icon={User} />
            <Field label="Años del Sistema" value={ficha.anios_sistema} icon={Calendar} />
            <Field label="Km del Canal Principal" value={ficha.km_canal} icon={Ruler} />
            <Field label="¿Recibió Capacitación?" value={ficha.recibio_capacitacion} icon={BookOpen} />
            <Field label="¿Le gustaría Capacitación?" value={ficha.le_gustaria_cap} icon={BookOpen} />
            <Field label="Temas de Capacitación" value={ficha.temas_capacitacion} icon={BookOpen} />
          </div>
        );
        case 'auditoria':
        return (
          <div className="space-y-6">

            {/* Consentimiento informado */}
            <div className="flex items-start gap-3 p-3 rounded-xl border border-amber-800/30 bg-amber-950/20">
              <span className="text-lg mt-0.5">
                {(ficha as any).consentimiento_informado ? '☑️' : '☐'}
              </span>
              <div>
                <p className="text-[9px] text-amber-400 font-bold uppercase tracking-wider mb-1">Consentimiento Informado</p>
                <p className="text-xs text-amber-200/80 leading-relaxed">
                  El/la informante autoriza el uso institucional de los datos recopilados en esta ficha
                  por parte del proyecto de Catastro de Riego – Cayambe.
                </p>
              </div>
            </div>

            {/* 4 Responsables */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="Informante" value={(ficha as any).informante || ficha.propietario || `${ficha.apellidos} ${ficha.nombres}`} icon={User} />
              <Field label="Investigador / Encuestador" value={getNombreTecnico(ficha.creado_por)} icon={User} />
              <Field label="Supervisor" value={(ficha as any).supervisor || 'Téc. Steven Proaño / AP CATASTROS'} icon={Award} />
              <Field label="Fecha de Registro" value={safeToDate(ficha.fecha_creacion).toLocaleString('es-EC')} icon={Calendar} />
              <Field label="ID" value={ficha.id} icon={Hash} />
              <Field label="Nombre Archivo Foto" value={ficha.foto_predio} icon={ImageIcon} />
              <div className="col-span-full">
                <Field label="Observaciones" value={ficha.observaciones} icon={FileText} />
              </div>
            </div>
 
            {/* Foto del Predio */}
            <div className="border border-slate-700/40 rounded-xl overflow-hidden">
              <div className="bg-slate-800/40 px-4 py-2 border-b border-slate-700/40 flex items-center gap-2">
                <ImageIcon className="w-4 h-4 text-sky-400" />
                <span className="text-xs font-semibold text-white uppercase tracking-wider font-semibold">Fotografía Evidencia</span>
              </div>
              <div className="p-4 flex justify-center bg-slate-950/40">
                {ficha.foto_predio ? (
                  <img
                    src={`https://firebasestorage.googleapis.com/v0/b/${BUCKET_NAME}/o/fotos_predios%2F${encodeURIComponent(ficha.foto_predio.replace(/\\/g, '/').split('/').pop() || '')}?alt=media`}
                    alt="Evidencia Predio"
                    className="max-h-[300px] w-auto rounded-lg object-contain border border-slate-800 shadow-md"
                    onError={(e) => {
                      const target = e.target as HTMLImageElement;
                      target.src = '';
                      target.style.display = 'none';
                      const sibling = target.nextElementSibling as HTMLElement;
                      if (sibling) sibling.style.display = 'flex';
                    }}
                  />
                ) : null}
                <div
                  className="flex flex-col items-center justify-center py-10 px-4 text-slate-500"
                  style={{ display: ficha.foto_predio ? 'none' : 'flex' }}
                >
                  <ImageIcon className="w-10 h-10 mb-2 opacity-40" />
                  <span className="text-xs">No hay fotografía disponible en esta ficha</span>
                </div>
              </div>
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Overlay con blur fino */}
      <div className="absolute inset-0 bg-slate-950/60 backdrop-blur-sm" onClick={onClose} />
 
      {/* Modal con Glassmorphism Premium */}
      <div className="relative bg-slate-950/95 backdrop-blur-xl rounded-2xl border border-slate-800/80 shadow-2xl shadow-blue-500/5 w-full max-w-2xl max-h-[85vh] flex flex-col transition-all duration-300">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-slate-800/60 bg-slate-900/10">
          <div>
            <h2 className="text-base font-bold text-white tracking-wide">
              {ficha.propietario || `${ficha.apellidos} ${ficha.nombres}`}
            </h2>
            <p className="text-xs text-slate-400 mt-1 flex items-center gap-1.5">
              <span className="px-1.5 py-0.5 rounded bg-blue-900/20 text-blue-400 border border-blue-500/10 font-mono text-[10px]">{ficha.codigo_final}</span>
              <span className="text-slate-600">•</span>
              <span>{ficha.parroquia}</span>
              <span className="text-slate-600">•</span>
              <span className="truncate max-w-[150px] sm:max-w-none">{ficha.sector}</span>
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => window.print()}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-xs font-semibold text-white transition-all duration-200 cursor-pointer shadow-lg shadow-blue-600/15 hover:shadow-blue-500/20 hover:scale-[1.02]"
              title="Imprimir Ficha Técnica A4"
            >
              <Printer className="w-3.5 h-3.5" />
              <span>Imprimir</span>
            </button>
            <button 
              onClick={onClose} 
              className="p-2 rounded-xl border border-slate-800 bg-slate-900/40 text-slate-400 hover:text-white hover:bg-slate-800/60 hover:border-slate-700/50 transition-all duration-150 cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
 
        {/* Tabs Modernas en Píldoras */}
        <div className="flex overflow-x-auto gap-1 border-b border-slate-800/60 px-6 py-3 scrollbar-thin scrollbar-track-transparent scrollbar-thumb-slate-800">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold whitespace-nowrap transition-all duration-200 cursor-pointer border ${
                activeTab === id
                  ? 'bg-blue-600/10 text-blue-400 border-blue-500/20 shadow-inner'
                  : 'bg-transparent text-slate-400 border-transparent hover:text-white hover:bg-slate-900/50 hover:border-slate-800/40'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{label.split('. ')[1]}</span>
            </button>
          ))}
        </div>
 
        {/* Content con Scrollbar Estilizado */}
        <div className="flex-1 overflow-y-auto p-6 scrollbar-thin scrollbar-track-transparent scrollbar-thumb-slate-850">
          {renderContent()}
        </div>
      </div>

      {/* Reporte de impresión invisible en pantalla, visible solo en papel */}
      {createPortal(
        <div 
          className="print-container-portal"
          style={{
            position: 'absolute',
            left: '-9999px',
            top: '-9999px',
            width: '820px',
            height: 'auto',
            overflow: 'hidden',
            opacity: 0,
            pointerEvents: 'none'
          }}
        >
          <FichaImpresion
            ficha={ficha}
            cultivos={cultivos}
            animales={animales}
            prediosAdicionales={prediosAdicionales}
          />
        </div>,
        document.body
      )}
    </div>
  );
}
