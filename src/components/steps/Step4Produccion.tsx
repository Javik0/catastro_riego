import { useFormContext, useFieldArray } from 'react-hook-form';

export function Step4Produccion() {
  const { register, control } = useFormContext();
  
  const { fields: cultivFields, append: appendCultivo, remove: removeCultivo } = useFieldArray({
    control,
    name: "cultivos"
  });

  const { fields: animFields, append: appendAnimal, remove: removeAnimal } = useFieldArray({
    control,
    name: "animales"
  });

  return (
    <div className="space-y-8">
      <div className="border-b border-gray-200 pb-4">
        <h2 className="text-xl font-semibold text-gray-800">4. Datos del Sistema de Producción</h2>
        <p className="text-sm text-gray-500 mt-1">Sistemas agrícolas y pecuarios de la unidad. Detalle superficie y destino por cada ítem.</p>
      </div>

      <div className="space-y-8">
        
        {/* Agrícola */}
        <div className="bg-green-50 p-4 md:p-6 rounded-xl border border-green-100 shadow-sm">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-bold text-green-800">1. Sistema de Producción Agrícola</h3>
            <button type="button" onClick={() => appendCultivo({ nombre: '', superficie: '', esPrincipal: false, destAuto: false, destMercado: false, destAgro: false, destExp: false })} className="text-sm bg-green-600 text-white px-3 py-1.5 rounded hover:bg-green-700 shadow transition-colors">
              + Agregar Cultivo
            </button>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse min-w-[700px]">
              <thead>
                <tr className="border-green-200 text-xs text-green-800 uppercase tracking-wider">
                  <th className="py-2 px-2 font-semibold align-bottom border-b" rowSpan={2}>Cultivo</th>
                  <th className="py-2 px-2 font-semibold align-bottom border-b" rowSpan={2}>Superficie (m²)</th>
                  <th className="py-2 px-2 font-semibold text-center align-bottom border-b" rowSpan={2}>Principal</th>
                  <th className="py-1 px-2 font-semibold text-center border-l border-b border-green-200" colSpan={4}>Destino Producción</th>
                  <th className="py-2 px-2 border-b" rowSpan={2}></th>
                </tr>
                <tr className="border-b border-green-200 text-[10px] text-green-700 uppercase tracking-wider h-28">
                  <th className="p-1 text-center border-l border-green-200 align-bottom w-10"><div className="mx-auto" style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}>Autoconsumo</div></th>
                  <th className="p-1 text-center align-bottom w-10"><div className="mx-auto" style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}>Mercado I.</div></th>
                  <th className="p-1 text-center align-bottom w-10"><div className="mx-auto" style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}>Agroindustria</div></th>
                  <th className="p-1 text-center align-bottom w-10"><div className="mx-auto" style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}>Exportación</div></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-green-100">
                {cultivFields.map((item, index) => (
                  <tr key={item.id} className="bg-white hover:bg-green-50/50 transition-colors">
                    <td className="p-2">
                      <input {...register(`cultivos.${index}.nombre`)} placeholder="Ej. Papas" className="w-full text-sm p-1.5 border border-gray-300 rounded focus:ring-green-500 focus:border-green-500" />
                    </td>
                    <td className="p-2 w-32">
                      <input type="number" {...register(`cultivos.${index}.superficie`)} placeholder="m²" className="w-full text-sm p-1.5 border border-gray-300 rounded focus:ring-green-500 focus:border-green-500" />
                    </td>
                    <td className="p-2 text-center">
                      <input type="checkbox" {...register(`cultivos.${index}.esPrincipal`)} className="h-4 w-4 text-green-600 rounded border-gray-300 focus:ring-green-500 cursor-pointer" />
                    </td>
                    <td className="p-2 text-center border-l border-green-100">
                      <input type="checkbox" {...register(`cultivos.${index}.destAuto`)} className="h-4 w-4 text-green-600 rounded border-gray-300 focus:ring-green-500 cursor-pointer" title="Autoconsumo" />
                    </td>
                    <td className="p-2 text-center">
                      <input type="checkbox" {...register(`cultivos.${index}.destMercado`)} className="h-4 w-4 text-green-600 rounded border-gray-300 focus:ring-green-500 cursor-pointer" title="Mercado Interno" />
                    </td>
                    <td className="p-2 text-center">
                      <input type="checkbox" {...register(`cultivos.${index}.destAgro`)} className="h-4 w-4 text-green-600 rounded border-gray-300 focus:ring-green-500 cursor-pointer" title="Agroindustria" />
                    </td>
                    <td className="p-2 text-center">
                      <input type="checkbox" {...register(`cultivos.${index}.destExp`)} className="h-4 w-4 text-green-600 rounded border-gray-300 focus:ring-green-500 cursor-pointer" title="Exportación" />
                    </td>
                    <td className="p-2 text-center">
                      <button type="button" onClick={() => removeCultivo(index)} className="text-red-500 font-bold p-1.5 hover:bg-red-100 rounded transition-colors" title="Eliminar">✕</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {cultivFields.length === 0 && <div className="p-4 text-sm text-green-700 italic text-center bg-white rounded-b-lg border-t border-green-100">No hay cultivos registrados. Presione "+ Agregar Cultivo".</div>}
          </div>
        </div>

        {/* Pecuario */}
        <div className="bg-amber-50 p-4 md:p-6 rounded-xl border border-amber-100 shadow-sm">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-bold text-amber-800">2. Sistema de Producción Pecuario</h3>
            <button type="button" onClick={() => appendAnimal({ tipo: '', cantidad: '', destAuto: false, destMercado: false, destAgro: false, destExp: false })} className="text-sm bg-amber-600 text-white px-3 py-1.5 rounded hover:bg-amber-700 shadow transition-colors">
              + Agregar Animales
            </button>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse min-w-[700px]">
              <thead>
                <tr className="border-amber-200 text-xs text-amber-800 uppercase tracking-wider">
                  <th className="py-2 px-2 font-semibold align-bottom border-b" rowSpan={2}>Animales</th>
                  <th className="py-2 px-2 font-semibold align-bottom border-b" rowSpan={2}>Número / Cantidad</th>
                  <th className="py-1 px-2 font-semibold text-center border-l border-b border-amber-200" colSpan={4}>Destino Producción</th>
                  <th className="py-2 px-2 border-b" rowSpan={2}></th>
                </tr>
                <tr className="border-b border-amber-200 text-[10px] text-amber-700 uppercase tracking-wider h-28">
                  <th className="p-1 text-center border-l border-amber-200 align-bottom w-10"><div className="mx-auto" style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}>Autoconsumo</div></th>
                  <th className="p-1 text-center align-bottom w-10"><div className="mx-auto" style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}>Mercado I.</div></th>
                  <th className="p-1 text-center align-bottom w-10"><div className="mx-auto" style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}>Agroindustria</div></th>
                  <th className="p-1 text-center align-bottom w-10"><div className="mx-auto" style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}>Exportación</div></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-amber-100">
                {animFields.map((item, index) => (
                  <tr key={item.id} className="bg-white hover:bg-amber-50/50 transition-colors">
                    <td className="p-2">
                      <input {...register(`animales.${index}.tipo`)} placeholder="Ej. Vacas, Cuyes" className="w-full text-sm p-1.5 border border-gray-300 rounded focus:ring-amber-500 focus:border-amber-500" />
                    </td>
                    <td className="p-2 w-32">
                      <input type="number" {...register(`animales.${index}.cantidad`)} placeholder="Cant." className="w-full text-sm p-1.5 border border-gray-300 rounded focus:ring-amber-500 focus:border-amber-500" />
                    </td>
                    <td className="p-2 text-center border-l border-amber-100">
                      <input type="checkbox" {...register(`animales.${index}.destAuto`)} className="h-4 w-4 text-amber-600 rounded border-gray-300 focus:ring-amber-500 cursor-pointer" title="Autoconsumo" />
                    </td>
                    <td className="p-2 text-center">
                      <input type="checkbox" {...register(`animales.${index}.destMercado`)} className="h-4 w-4 text-amber-600 rounded border-gray-300 focus:ring-amber-500 cursor-pointer" title="Mercado Interno" />
                    </td>
                    <td className="p-2 text-center">
                      <input type="checkbox" {...register(`animales.${index}.destAgro`)} className="h-4 w-4 text-amber-600 rounded border-gray-300 focus:ring-amber-500 cursor-pointer" title="Agroindustria" />
                    </td>
                    <td className="p-2 text-center">
                      <input type="checkbox" {...register(`animales.${index}.destExp`)} className="h-4 w-4 text-amber-600 rounded border-gray-300 focus:ring-amber-500 cursor-pointer" title="Exportación" />
                    </td>
                    <td className="p-2 text-center">
                      <button type="button" onClick={() => removeAnimal(index)} className="text-red-500 font-bold p-1.5 hover:bg-red-100 rounded transition-colors" title="Eliminar">✕</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {animFields.length === 0 && <div className="p-4 text-sm text-amber-700 italic text-center bg-white rounded-b-lg border-t border-amber-100">No hay animales registrados. Presione "+ Agregar Animales".</div>}
          </div>
        </div>

      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4 border-t border-gray-100">
        <div className="bg-blue-50 p-4 rounded-xl border border-blue-100">
           <label className="block text-sm font-bold text-blue-800 mb-3">3. Uso del Agua (%)</label>
           <div className="space-y-3">
             <div className="flex items-center justify-between text-sm bg-white p-2 border border-blue-100 rounded shadow-sm">
               <span className="text-blue-900 font-medium">Soberanía Alimentaria</span>
               <div className="flex items-center">
                 <input type="number" max="100" {...register('usoSoberania')} className="w-16 p-1 border border-gray-300 rounded text-right focus:ring-blue-500 focus:border-blue-500" />
                 <span className="ml-2 text-gray-500">%</span>
               </div>
             </div>
             <div className="flex items-center justify-between text-sm bg-white p-2 border border-blue-100 rounded shadow-sm">
               <span className="text-blue-900 font-medium">Actividades Productivas</span>
               <div className="flex items-center">
                 <input type="number" max="100" {...register('usoProductivas')} className="w-16 p-1 border border-gray-300 rounded text-right focus:ring-blue-500 focus:border-blue-500" />
                 <span className="ml-2 text-gray-500">%</span>
               </div>
             </div>
           </div>
        </div>
      </div>

    </div>
  );
}
