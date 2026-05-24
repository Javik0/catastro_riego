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

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 bg-gray-50 p-5 rounded-lg border border-gray-200">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Investigado Por:</label>
            <input type="text" {...register('investigadoPor')} className="w-full p-2 border rounded-md text-sm" placeholder="Nombre del encuestador" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Fecha de Registro:</label>
            <input type="date" {...register('fecha')} className="w-full p-2 border rounded-md text-sm" />
          </div>
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1">Observaciones Finales:</label>
            <textarea {...register('observaciones')} rows={2} className="w-full p-2 border rounded-md text-sm"></textarea>
          </div>
        </div>

        <div className="bg-blue-50 border-l-4 border-blue-400 p-4 mt-6">
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
