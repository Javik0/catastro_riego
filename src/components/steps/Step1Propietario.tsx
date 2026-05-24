import { useFormContext } from 'react-hook-form';

export function Step1Propietario() {
  const { register } = useFormContext();

  return (
    <div className="space-y-6">
      <div className="border-b border-gray-200 pb-4">
        <h2 className="text-xl font-semibold text-gray-800">1. Datos del Propietario</h2>
        <p className="text-sm text-gray-500 mt-1">Ingrese la información personal y catastral del usuario.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Catastro */}
        <div className="space-y-4 md:col-span-2 bg-agri-50 p-4 rounded-lg border border-agri-100">
          <h3 className="text-md font-medium text-agri-800 mb-3">Ubicación y Catastro</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Clave Catastral</label>
              <input type="text" {...register('claveCatastral')} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-agri-500 focus:ring-agri-500 sm:text-sm p-2 border" placeholder="Ej. 170..."/>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Parroquia</label>
              <select {...register('parroquia')} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-agri-500 focus:ring-agri-500 sm:text-sm p-2 border">
                <option value="CANGAHUA">CANGAHUA</option>
                <option value="OTÓN">OTÓN</option>
                <option value="CUSUBAMBA">CUSUBAMBA</option>
                <option value="ASCÁZUBI">ASCÁZUBI</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Comunidad</label>
              <input type="text" {...register('comunidad')} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-agri-500 focus:ring-agri-500 sm:text-sm p-2 border" />
            </div>
          </div>
          
          <div className="mt-3">
            <label className="block text-sm font-medium text-gray-700 mb-2">Sector</label>
            <div className="flex space-x-6">
              <label className="flex items-center">
                <input type="radio" {...register('sector')} value="Porotog" className="text-agri-600 focus:ring-agri-500" />
                <span className="ml-2 text-sm text-gray-700">Porotog</span>
              </label>
              <label className="flex items-center">
                <input type="radio" {...register('sector')} value="Guanguilqui" className="text-agri-600 focus:ring-agri-500" />
                <span className="ml-2 text-sm text-gray-700">Guanguilqui</span>
              </label>
              <label className="flex items-center">
                <input type="radio" {...register('sector')} value="Guang-Portog" className="text-agri-600 focus:ring-agri-500" />
                <span className="ml-2 text-sm text-gray-700">Guang-Portog</span>
              </label>
            </div>
          </div>
        </div>

        {/* Datos Personales */}
        <div>
          <label className="block text-sm font-medium text-gray-700">Nombres</label>
          <input type="text" {...register('nombres')} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-agri-500 focus:ring-agri-500 sm:text-sm p-2 border" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Apellidos</label>
          <input type="text" {...register('apellidos')} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-agri-500 focus:ring-agri-500 sm:text-sm p-2 border" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Número de Cédula</label>
          <input type="text" {...register('cedula')} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-agri-500 focus:ring-agri-500 sm:text-sm p-2 border" />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Tenencia del Predio</label>
          <select {...register('tenencia')} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-agri-500 focus:ring-agri-500 sm:text-sm p-2 border">
            <option value="Escritura">Escritura</option>
            <option value="Sin Escritura">Sin Escritura</option>
          </select>
        </div>

        {/* Contacto */}
        <div>
          <label className="block text-sm font-medium text-gray-700">Teléfono Celular</label>
          <input type="text" {...register('telefonoCelular')} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-agri-500 focus:ring-agri-500 sm:text-sm p-2 border" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Teléfono Casa</label>
          <input type="text" {...register('telefonoCasa')} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-agri-500 focus:ring-agri-500 sm:text-sm p-2 border" />
        </div>

        {/* Familia */}
        <div className="md:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-6 border-t border-gray-100 pt-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Número de Hijos</label>
            <div className="flex space-x-4">
              <div className="flex-1">
                <div className="flex items-center border rounded-md border-gray-300 overflow-hidden">
                  <span className="bg-gray-50 px-3 py-2 text-gray-500 text-sm border-r">Hombres</span>
                  <input type="number" min="0" {...register('hijosHombres')} className="w-full p-2 focus:outline-none" />
                </div>
              </div>
              <div className="flex-1">
                <div className="flex items-center border rounded-md border-gray-300 overflow-hidden">
                  <span className="bg-gray-50 px-3 py-2 text-gray-500 text-sm border-r">Mujeres</span>
                  <input type="number" min="0" {...register('hijosMujeres')} className="w-full p-2 focus:outline-none" />
                </div>
              </div>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Nivel de Instrucción</label>
            <select {...register('instruccion')} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-agri-500 focus:ring-agri-500 sm:text-sm p-2 border">
              <option value="ninguno">Ninguno</option>
              <option value="alfabetizado">Alfabetizado</option>
              <option value="primaria">Primaria</option>
              <option value="secundaria">Secundaria</option>
              <option value="superior">Superior</option>
            </select>
          </div>
        </div>

      </div>
    </div>
  );
}
