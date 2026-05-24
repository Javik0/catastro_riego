import { useFormContext } from 'react-hook-form';

export function Step5Encuesta() {
  const { register, watch } = useFormContext();

  const leGustariaCapacitacion = watch('leGustariaCapacitacion');

  return (
    <div className="space-y-6">
      <div className="border-b border-gray-200 pb-4">
        <h2 className="text-xl font-semibold text-gray-800">5. Datos de la Comunidad y Conocimiento de la Junta de Agua</h2>
        <p className="text-sm text-gray-500 mt-1">Encuesta sobre Guanguilqui Porotog.</p>
      </div>

      <div className="space-y-6">
        
        {/* Preguntas Cerradas */}
        <div className="bg-gray-50 p-5 rounded-lg border border-gray-200 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
            <span className="text-sm text-gray-700 font-medium md:col-span-2">¿Sabe Ud. si la Junta de Agua tiene estatutos?</span>
            <select {...register('tieneEstatutos')} className="p-2 border rounded-md text-sm">
              <option value="si">Sí</option>
              <option value="no">No</option>
              <option value="Nsc">No Sabe / No Contesta</option>
            </select>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
            <span className="text-sm text-gray-700 font-medium md:col-span-2">¿Y sabe Ud. si tiene reglamentos?</span>
            <select {...register('tieneReglamentos')} className="p-2 border rounded-md text-sm">
              <option value="si">Sí</option>
              <option value="no">No</option>
              <option value="Nsc">No Sabe / No Contesta</option>
            </select>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
            <span className="text-sm text-gray-700 font-medium md:col-span-2">¿Conoce sobre el Proyecto de la presa Río Porotog?</span>
            <select {...register('conocePresa')} className="p-2 border rounded-md text-sm">
              <option value="si">Sí</option>
              <option value="no">No</option>
              <option value="Nsc">No Sabe / No Contesta</option>
            </select>
          </div>
        </div>

        {/* Datos de la Comunidad */}
        <div className="bg-green-50 p-5 rounded-lg border border-green-200 space-y-6">
          <h3 className="text-sm font-bold text-green-800 uppercase tracking-wide border-b border-green-200 pb-2">Datos de la Comunidad</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">¿Cómo se elige a la directiva?</label>
              <input type="text" {...register('comoSeElige')} className="w-full p-2 border rounded-md text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">¿Cómo se llama el Presidente de la Junta de Agua?</label>
              <input type="text" {...register('nombrePresidente')} className="w-full p-2 border rounded-md text-sm" />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">¿Conoce quién es el operador del sistema en su sector?</label>
              <input type="text" {...register('quienOpera')} className="w-full p-2 border rounded-md text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">¿Cuántos años tiene este sistema de riego?</label>
              <input type="number" {...register('aniosSistema')} className="w-full p-2 border rounded-md text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">¿Conoce cuántos Km tiene el canal principal?</label>
              <input type="number" step="0.1" {...register('kmCanal')} className="w-full p-2 border rounded-md text-sm" />
            </div>
          </div>

          {/* Capacitación */}
          <div className="pt-4 border-t border-green-200">
            <h4 className="text-sm font-bold text-green-800 mb-3">Capacitación sobre riego eficiente</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-gray-700 mb-1">¿Ha recibido capacitación?</label>
                <div className="flex space-x-4">
                  <label className="flex items-center text-sm"><input type="radio" {...register('recibioCapacitacion')} value="si" className="mr-1 text-green-600 focus:ring-green-500" /> Sí</label>
                  <label className="flex items-center text-sm"><input type="radio" {...register('recibioCapacitacion')} value="no" className="mr-1 text-green-600 focus:ring-green-500" /> No</label>
                </div>
              </div>
              <div>
                <label className="block text-sm text-gray-700 mb-1">¿Le gustaría recibir capacitación?</label>
                <div className="flex space-x-4">
                  <label className="flex items-center text-sm"><input type="radio" {...register('leGustariaCapacitacion')} value="si" className="mr-1 text-green-600 focus:ring-green-500" /> Sí</label>
                  <label className="flex items-center text-sm"><input type="radio" {...register('leGustariaCapacitacion')} value="no" className="mr-1 text-green-600 focus:ring-green-500" /> No</label>
                </div>
              </div>
            </div>
            
            {leGustariaCapacitacion === 'si' && (
              <div className="mt-4 pt-4 border-t border-green-200 animate-in fade-in slide-in-from-top-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">¿En qué temas desearía recibir la capacitación?</label>
                <textarea {...register('temasCapacitacion')} rows={2} className="w-full p-2 border rounded-md text-sm" placeholder="Ej. Aspersión, mantenimiento de válvulas..."></textarea>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
