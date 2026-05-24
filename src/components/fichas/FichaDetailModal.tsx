import { useState } from 'react';
import { X, User, MapPin, Droplets, Sprout, ClipboardList, Building } from 'lucide-react';
import { type FichaPredio, safeToDate } from '../../lib/types';
import { getNombreTecnico } from '../../lib/constants';

interface Props {
  ficha: FichaPredio;
  onClose: () => void;
}

const TABS = [
  { id: 'propietario', label: '1. Propietario', icon: User },
  { id: 'predio', label: '2. Predio y Riego', icon: Droplets },
  { id: 'servicios', label: '3. Servicios', icon: Building },
  { id: 'produccion', label: '4. Producción', icon: Sprout },
  { id: 'encuesta', label: '5. Encuesta', icon: ClipboardList },
  { id: 'auditoria', label: '6. Auditoría', icon: MapPin },
] as const;

function Field({ label, value }: { label: string; value: unknown }) {
  if (value == null || value === '') return null;
  const display = typeof value === 'boolean' ? (value ? 'Sí' : 'No') : String(value);
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[10px] text-slate-500 uppercase tracking-wider">{label}</span>
      <span className="text-sm text-white">{display}</span>
    </div>
  );
}

export default function FichaDetailModal({ ficha, onClose }: Props) {
  const [activeTab, setActiveTab] = useState<string>('propietario');

  const renderContent = () => {
    switch (activeTab) {
      case 'propietario':
        return (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Código del Predio" value={ficha.codigo_final} />
            <Field label="Clave Catastral" value={ficha.clave_catastral} />
            <Field label="Apellidos" value={ficha.apellidos} />
            <Field label="Nombres" value={ficha.nombres} />
            <Field label="Cédula" value={ficha.cedula} />
            <Field label="Parroquia" value={ficha.parroquia} />
            <Field label="Sector" value={ficha.sector} />
            <Field label="Sector Comunidad" value={ficha.sector_comunidad} />
            <Field label="Teléfono Celular" value={ficha.telefono_celular} />
            <Field label="Teléfono Casa" value={ficha.telefono_casa} />
            <Field label="Hijos (Hombres)" value={ficha.hijos_hombres} />
            <Field label="Hijos (Mujeres)" value={ficha.hijos_mujeres} />
            <Field label="Tenencia del Predio" value={ficha.tenencia_predio} />
            <Field label="Nivel de Instrucción" value={ficha.nivel_instruccion} />
          </div>
        );
      case 'predio':
        return (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Org. de Riego" value={ficha.org_riego} />
            <Field label="Canal" value={ficha.canal} />
            <Field label="Caudal (l/s)" value={ficha.caudal_valor} />
            <Field label="Tipo de Caudal" value={ficha.caudal_tipo} />
            <Field label="Área Total (m²)" value={ficha.area_total?.toLocaleString('es-EC')} />
            <Field label="Área con Riego (m²)" value={ficha.area_riego?.toLocaleString('es-EC')} />
            <Field label="Área sin Riego (m²)" value={ficha.area_sin_riego?.toLocaleString('es-EC')} />
            <Field label="Frecuencia de Riego" value={ficha.frecuencia_riego} />
            <Field label="Gravedad (%)" value={ficha.metodo_gravedad_pct} />
            <Field label="Aspersión (%)" value={ficha.metodo_aspersion_pct} />
            <Field label="Goteo (%)" value={ficha.metodo_goteo_pct} />
            <Field label="Días de Riego" value={ficha.dias_riego} />
            <Field label="Horas por Turno" value={ficha.horas_turno} />
            <Field label="Valor Tarifa ($)" value={ficha.valor_tarifa} />
            <Field label="Tipo de Tarifa" value={ficha.tipo_tarifa} />
            <Field label="¿Tiene Reservorio?" value={ficha.tiene_reservorio} />
          </div>
        );
      case 'servicios':
        return (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Agua Consumo" value={ficha.agua_consumo} />
            <Field label="Energía Eléctrica" value={ficha.energia_electrica} />
            <Field label="Material Construcción" value={ficha.material_construccion} />
            <Field label="Material (otro)" value={ficha.material_constr_otro} />
            <Field label="COTA (msnm)" value={ficha.cota_msnm} />
            <Field label="Coordenada X (UTM)" value={ficha.coord_x_utm} />
            <Field label="Coordenada Y (UTM)" value={ficha.coord_y_utm} />
          </div>
        );
      case 'produccion':
        return (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Soberanía Alimentaria (%)" value={ficha.soberania_aliment_pct} />
            <Field label="Act. Productivas (%)" value={ficha.act_productivas_pct} />
            <Field label="Actividad Productiva" value={ficha.actividad_productiva} />
            <div className="col-span-full mt-2">
              <p className="text-xs text-slate-400 italic">
                Los cultivos y animales se cargarán desde subcolecciones de Firestore (pendiente sincronización)
              </p>
            </div>
          </div>
        );
      case 'encuesta':
        return (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="¿Conoce el Proyecto Presa?" value={ficha.conoce_presa} />
            <Field label="¿Cómo se elige la directiva?" value={ficha.como_elige_dir} />
            <Field label="Otro método" value={ficha.como_elige_dir_otro} />
            <Field label="Presidente Junta de Agua" value={ficha.nom_presidente} />
            <Field label="Operador del Sistema" value={ficha.operador_sector} />
            <Field label="Años del Sistema" value={ficha.anios_sistema} />
            <Field label="Km del Canal Principal" value={ficha.km_canal} />
            <Field label="¿Recibió Capacitación?" value={ficha.recibio_capacitacion} />
            <Field label="¿Le gustaría Capacitación?" value={ficha.le_gustaria_cap} />
            <Field label="Temas de Capacitación" value={ficha.temas_capacitacion} />
          </div>
        );
      case 'auditoria':
        return (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="ID" value={ficha.id} />
            <Field label="Investigado por" value={getNombreTecnico(ficha.creado_por)} />
            <Field label="Fecha de Registro" value={safeToDate(ficha.fecha_creacion).toLocaleString('es-EC')} />
            <Field label="Dispositivo" value={ficha.dispositivo} />
            <Field label="Foto" value={ficha.foto_predio} />
            <Field label="Observaciones" value={ficha.observaciones} />
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Overlay */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative bg-slate-900 rounded-2xl border border-slate-700/50 shadow-2xl w-full max-w-2xl max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700/30">
          <div>
            <h2 className="text-lg font-bold text-white">
              {ficha.propietario || `${ficha.apellidos} ${ficha.nombres}`}
            </h2>
            <p className="text-xs text-slate-400">
              {ficha.codigo_final} · {ficha.parroquia} · {ficha.sector}
            </p>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white cursor-pointer">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex overflow-x-auto border-b border-slate-700/30 px-4">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex items-center gap-1.5 px-3 py-2.5 text-xs font-medium whitespace-nowrap border-b-2 transition-colors cursor-pointer ${
                activeTab === id
                  ? 'border-blue-400 text-blue-400'
                  : 'border-transparent text-slate-400 hover:text-white'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">{label}</span>
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {renderContent()}
        </div>
      </div>
    </div>
  );
}
