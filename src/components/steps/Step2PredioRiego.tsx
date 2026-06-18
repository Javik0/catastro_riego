import { useFormContext } from 'react-hook-form';

export function Step2PredioRiego() {
  const { register, watch, setValue } = useFormContext();

  const areaTotal = Number(watch('areaTotal') || 0);
  const areaRiego = Number(watch('areaRiego') || 0);
  const unidadArea = watch('unidadArea') || 'ha';
  const inundacion = Number(watch('metodoInundacion') || 0);
  const aspersion = Number(watch('metodoAspersion') || 0);
  const goteo = Number(watch('metodoGoteo') || 0);
  const totalMetodo = inundacion + aspersion + goteo;

  const toggleUnidad = (u: 'ha' | 'm2') => {
    if (u === unidadArea) return;
    setValue('unidadArea', u);
    if (u === 'm2') {
      setValue('areaTotal', areaTotal ? +(areaTotal * 10000).toFixed(0) : 0);
      setValue('areaRiego', areaRiego ? +(areaRiego * 10000).toFixed(0) : 0);
    } else {
      setValue('areaTotal', areaTotal ? +(areaTotal / 10000).toFixed(4) : 0);
      setValue('areaRiego', areaRiego ? +(areaRiego / 10000).toFixed(4) : 0);
    }
  };

  const pctRiego = areaTotal > 0 ? Math.min(100, Math.round((areaRiego / areaTotal) * 100)) : 0;

  return (
    <div className="space-y-6">
      <div className="border-b border-gray-200 pb-4">
        <h2 className="text-xl font-semibold text-gray-800">2. Datos del Predio (UPA) y Riego</h2>
        <p className="text-sm text-gray-500 mt-1">Información sobre el predio, acceso al agua y sistema de riego.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700">Nombre de la Organización de Riego</label>
          <input type="text" {...register('organizacionRiego')} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-agri-500 focus:ring-agri-500 sm:text-sm p-2 border" />
        </div>

        {/* Identificación del Predio */}
        <div className="md:col-span-2 bg-agri-50 p-4 rounded-lg border border-agri-100 space-y-4">
          <h3 className="text-sm font-semibold text-agri-800 uppercase tracking-wider">📍 Identificación del Predio (UPA)</h3>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Código Predio</label>
              <input type="text" {...register('codigoPredio')} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm sm:text-sm p-2 border" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">N° Predio</label>
              <input type="text" {...register('numPredio')} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm sm:text-sm p-2 border" />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700">Sector dentro de la comunidad</label>
              <input type="text" {...register('sectorComunidad')} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm sm:text-sm p-2 border" />
            </div>
          </div>
        </div>

        {/* Canal y Caudal */}
        <div>
          <label className="block text-sm font-medium text-gray-700">Canal (Nombre)</label>
          <input type="text" {...register('canal')} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm sm:text-sm p-2 border" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Caudal (litros/segundo)</label>
          <div className="flex gap-2 mt-1">
            <input type="text" {...register('caudal')} placeholder="Valor (ej. 1.2 o NSC)" className="block w-1/2 rounded-md border-gray-300 shadow-sm sm:text-sm p-2 border" />
            <select {...register('tipoCaudal')} className="block w-1/2 rounded-md border-gray-300 shadow-sm sm:text-sm p-2 border">
              <option value="">-- Seleccionar --</option>
              <option value="Recibe la Comunidad">Recibe la Comunidad</option>
              <option value="Recibe individual">Recibe individual</option>
            </select>
          </div>
        </div>

        {/* Áreas con toggle */}
        <div className="md:col-span-2">
          <div className="flex items-center justify-between mb-3">
            <label className="block text-sm font-medium text-gray-700">Superficies del Predio</label>
            <div className="flex rounded-lg border border-gray-300 overflow-hidden text-sm shadow-sm">
              <button type="button" onClick={() => toggleUnidad('ha')}
                className={`px-4 py-1.5 font-medium transition-colors ${unidadArea === 'ha' ? 'bg-agri-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}>
                Hectáreas (Ha)
              </button>
              <button type="button" onClick={() => toggleUnidad('m2')}
                className={`px-4 py-1.5 font-medium transition-colors border-l border-gray-300 ${unidadArea === 'm2' ? 'bg-agri-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}>
                Metros² (m²)
              </button>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm text-gray-600 mb-1">
                Área Total <span className="font-semibold text-agri-700">({unidadArea === 'ha' ? 'Ha' : 'm²'})</span>
              </label>
              <input type="number" step={unidadArea === 'ha' ? '0.0001' : '1'} {...register('areaTotal')}
                className="block w-full rounded-md border-gray-300 shadow-sm sm:text-sm p-2 border" />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">
                Área con Riego <span className="font-semibold text-agri-700">({unidadArea === 'ha' ? 'Ha' : 'm²'})</span>
              </label>
              <input type="number" step={unidadArea === 'ha' ? '0.0001' : '1'} {...register('areaRiego')}
                className="block w-full rounded-md border-gray-300 shadow-sm sm:text-sm p-2 border" />
              {areaRiego > areaTotal && areaTotal > 0 && (
                <p className="text-red-500 text-xs mt-1">⚠️ El área de riego no puede ser mayor al área total.</p>
              )}
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">
                Área sin Riego <span className="font-semibold text-agri-700">({unidadArea === 'ha' ? 'Ha' : 'm²'})</span>
              </label>
              <input type="number" step={unidadArea === 'ha' ? '0.0001' : '1'} {...register('areaSinRiego')}
                className="block w-full rounded-md border-gray-300 shadow-sm sm:text-sm p-2 border" />
            </div>
          </div>
          {areaTotal > 0 && (
            <div className="mt-3">
              <div className="flex justify-between text-xs text-gray-500 mb-1">
                <span>% del predio con riego</span>
                <span className="font-semibold text-agri-700">{pctRiego}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-agri-500 h-2 rounded-full transition-all duration-300" style={{ width: `${pctRiego}%` }}></div>
              </div>
            </div>
          )}
        </div>

        {/* Método de Riego */}
        <div className="md:col-span-2">
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-gray-700">Método de Riego (%)</label>
            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${totalMetodo === 100 ? 'bg-green-100 text-green-700' : totalMetodo > 100 ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'}`}>
              Total: {totalMetodo}% {totalMetodo === 100 ? '✓' : totalMetodo > 100 ? '⚠ excede 100%' : '(debe sumar 100%)'}
            </span>
          </div>
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: 'Gravedad', field: 'metodoInundacion' },
              { label: 'Aspersión', field: 'metodoAspersion' },
              { label: 'Goteo', field: 'metodoGoteo' },
            ].map(({ label, field }) => (
              <div key={field} className="flex items-center border rounded-md border-gray-300 overflow-hidden bg-white">
                <span className="bg-gray-50 px-3 py-2 text-gray-600 text-sm border-r flex-1">{label}</span>
                <input type="number" min="0" max="100" {...register(field)} className="w-16 p-2 text-right focus:outline-none text-sm" />
                <span className="bg-gray-50 px-2 py-2 text-gray-500 text-sm border-l">%</span>
              </div>
            ))}
          </div>
        </div>

        {/* Turno de Riego */}
        <div className="md:col-span-2 grid grid-cols-2 md:grid-cols-4 gap-4 bg-gray-50 p-4 rounded-lg border border-gray-200">
          <div className="col-span-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Turno de Riego y Reservorio</div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Frecuencia</label>
            <select {...register('frecuenciaRiego')} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm sm:text-sm p-2 border">
              <option value="permanente">Permanente</option>
              <option value="mensual">Mensual</option>
              <option value="quincenal">Quincenal</option>
              <option value="semanal">Semanal</option>
              <option value="no tiene riego">No tiene riego</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">N° Días</label>
            <input type="number" min="0" {...register('diasRiego')} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm sm:text-sm p-2 border" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Horas/Turno</label>
            <input type="number" min="0" {...register('horasTurno')} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm sm:text-sm p-2 border" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Valor Tarifa ($)</label>
            <div className="flex mt-1">
              <input type="number" step="0.01" {...register('valorTarifa')} className="block w-full rounded-l-md border-gray-300 shadow-sm sm:text-sm p-2 border" />
              <select {...register('tipoTarifa')} className="block rounded-r-md border-l-0 border-gray-300 bg-gray-50 text-gray-500 sm:text-sm p-2 border">
                <option value="por turno">x turno</option>
                <option value="fijo mensual">fijo mes</option>
                <option value="fijo anual">fijo anual</option>
                <option value="por hectárea">x Ha.</option>
              </select>
            </div>
          </div>
          <div className="col-span-2">
            <label className="block text-sm font-medium text-gray-700">¿Tiene reservorio? (privado o comunitario)</label>
            <select {...register('tieneReservorio')} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm sm:text-sm p-2 border">
              <option value="No">No tiene</option>
              <option value="Privado">Privado</option>
              <option value="Comunitario">Comunitario</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  );
}
