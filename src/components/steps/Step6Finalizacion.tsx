import { useFormContext } from 'react-hook-form';

export function Step6Finalizacion() {
  const { register } = useFormContext();

  return (
    <div className="space-y-6">
      <div className="border-b border-gray-200 pb-4">
        <h2 className="text-xl font-semibold text-gray-800">6. Finalización y Emplazamiento</h2>
        <p className="text-sm text-gray-500 mt-1">Revisión final y firma del formulario.</p>
      </div>

      <div className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Emplazamiento (Croquis / Referencias)</label>
          <textarea
            {...register('emplazamiento')}
            rows={4}
            className="w-full p-3 border rounded-md text-sm border-gray-300 shadow-sm focus:ring-agri-500 focus:border-agri-500"
            placeholder="Describa cómo llegar o detalles del croquis..."
          ></textarea>
        </div>

        {/* ── Consentimiento informado ── */}
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
          <p className="text-sm font-semibold text-amber-800 mb-2">Consentimiento Informado</p>
          <label className="flex items-start space-x-3 cursor-pointer">
            <input
              type="checkbox"
              {...register('consentimientoInformado')}
              className="mt-0.5 h-5 w-5 text-agri-600 rounded border-amber-300 focus:ring-agri-500"
            />
            <span className="text-sm text-amber-900">
              El/la informante autoriza el uso institucional de los datos recopilados en esta ficha por parte del
              proyecto de Catastro de Riego – Cayambe, conforme a la normativa vigente de protección de datos
              personales.
            </span>
          </label>
        </div>

        {/* ── Sección de responsables (4 partes) ── */}
        <div className="border border-gray-200 rounded-lg overflow-hidden">
          <div className="bg-gray-100 px-4 py-2 border-b border-gray-200">
            <p className="text-sm font-semibold text-gray-700">Responsables de la Ficha</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-0 divide-y md:divide-y-0 md:divide-x divide-gray-200">

            {/* Informante */}
            <div className="p-4 space-y-2">
              <p className="text-xs font-bold text-gray-500 uppercase tracking-wider">Informante</p>
              <p className="text-xs text-gray-400 italic">El mismo propietario / regante</p>
              <input
                type="text"
                {...register('informante')}
                placeholder="Nombre del informante"
                className="w-full p-2 border rounded-md text-sm border-gray-300 focus:ring-agri-500 focus:border-agri-500"
              />
            </div>

            {/* Investigador */}
            <div className="p-4 space-y-2">
              <p className="text-xs font-bold text-gray-500 uppercase tracking-wider">Investigador / Encuestador</p>
              <input
                type="text"
                {...register('investigadoPor')}
                placeholder="Nombre del encuestador"
                className="w-full p-2 border rounded-md text-sm border-gray-300 focus:ring-agri-500 focus:border-agri-500"
              />
            </div>

            {/* Supervisor */}
            <div className="p-4 space-y-2">
              <p className="text-xs font-bold text-gray-500 uppercase tracking-wider">Supervisor</p>
              <input
                type="text"
                {...register('supervisor')}
                defaultValue="Téc. Steven Proaño / AP CATASTROS"
                className="w-full p-2 border rounded-md text-sm border-gray-300 focus:ring-agri-500 focus:border-agri-500 bg-gray-50"
              />
            </div>

            {/* Fecha */}
            <div className="p-4 space-y-2">
              <p className="text-xs font-bold text-gray-500 uppercase tracking-wider">Fecha de Registro</p>
              <input
                type="date"
                {...register('fecha')}
                className="w-full p-2 border rounded-md text-sm border-gray-300 focus:ring-agri-500 focus:border-agri-500"
              />
            </div>

          </div>
        </div>

        {/* Observaciones */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Observaciones Finales:</label>
          <textarea {...register('observaciones')} rows={2} className="w-full p-2 border rounded-md text-sm border-gray-300"></textarea>
        </div>

        <div className="bg-blue-50 border-l-4 border-blue-400 p-4 mt-2">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-blue-700">
                Ha completado todos los pasos. Haga clic en <strong>Generar Padrón (PDF)</strong> para descargar la ficha consolidada lista para su socialización.
              </p>
            </div>
          </div>
        </div>
      </div>

    </div>
  );
}
