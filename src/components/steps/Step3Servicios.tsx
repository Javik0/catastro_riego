import { useFormContext } from 'react-hook-form';
import { MapPin } from 'lucide-react';

export function Step3Servicios() {
  const { register, setValue } = useFormContext();

  const getGeolocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition((position) => {
        // Simple conversion or just raw lat/lng. For a real app, convert Lat/Lng to UTM if strictly needed,
        // or just store lat/lng. 
        setValue('coordX', position.coords.longitude.toFixed(6));
        setValue('coordY', position.coords.latitude.toFixed(6));
        setValue('cota', position.coords.altitude ? position.coords.altitude.toFixed(2) : '');
      });
    } else {
      alert("Geolocalización no soportada en este navegador.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="border-b border-gray-200 pb-4">
        <h2 className="text-xl font-semibold text-gray-800">3. Servicios Básicos y Ubicación</h2>
        <p className="text-sm text-gray-500 mt-1">Detalles de servicios del predio y coordenadas geográficas.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        
        {/* Servicios */}
        <div className="space-y-6">
          <h3 className="text-md font-medium text-gray-800">Servicios e Infraestructura</h3>
          
          <div className="flex space-x-6">
            <label className="flex items-center space-x-3 bg-white p-3 border border-gray-200 rounded-lg shadow-sm flex-1 cursor-pointer hover:border-agri-400">
              <input type="checkbox" {...register('aguaConsumo')} className="h-5 w-5 text-agri-600 rounded focus:ring-agri-500" />
              <span className="text-gray-700 font-medium text-sm">Agua de consumo humano</span>
            </label>
            <label className="flex items-center space-x-3 bg-white p-3 border border-gray-200 rounded-lg shadow-sm flex-1 cursor-pointer hover:border-agri-400">
              <input type="checkbox" {...register('energiaElectrica')} className="h-5 w-5 text-agri-600 rounded focus:ring-agri-500" />
              <span className="text-gray-700 font-medium text-sm">Energía eléctrica</span>
            </label>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Vivienda - Material Construcción</label>
            <select {...register('materialVivienda')} className="block w-full rounded-md border-gray-300 shadow-sm focus:border-agri-500 focus:ring-agri-500 sm:text-sm p-2 border">
              <option value="">Seleccione una opción...</option>
              <option value="HORMIGON ARMADO">HORMIGÓN ARMADO</option>
              <option value="ESTRUCTURA METÁLICA">ESTRUCTURA METÁLICA</option>
              <option value="LADRILLO">LADRILLO</option>
              <option value="BLOQUE">BLOQUE</option>
              <option value="MADERA">MADERA</option>
              <option value="MIXTA">MIXTA</option>
              <option value="Otros">Otros</option>
            </select>
          </div>

        </div>

        {/* Coordenadas */}
        <div className="bg-blue-50 p-6 rounded-xl border border-blue-100">
          <div className="flex justify-between items-center mb-4">
             <h3 className="text-md font-medium text-blue-800">Coordenadas (UTM / GPS)</h3>
             <button type="button" onClick={getGeolocation} className="text-xs bg-blue-600 hover:bg-blue-700 text-white py-1 px-3 rounded flex items-center shadow">
               <MapPin className="w-3 h-3 mr-1" />
               Obtener GPS
             </button>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-blue-800 uppercase tracking-wider">Coord. X (Este)</label>
              <input type="text" {...register('coordX')} placeholder="Ej. 812350" className="mt-1 block w-full rounded-md border-blue-200 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2 border" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-blue-800 uppercase tracking-wider">Coord. Y (Norte)</label>
              <input type="text" {...register('coordY')} placeholder="Ej. 9987450" className="mt-1 block w-full rounded-md border-blue-200 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2 border" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-blue-800 uppercase tracking-wider">COTA (msnm)</label>
              <input type="text" {...register('cota')} placeholder="msnm" className="mt-1 block w-full rounded-md border-blue-200 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2 border" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 mt-3">
            <div>
              <label className="block text-xs font-semibold text-blue-800 uppercase tracking-wider">Datum</label>
              <select {...register('datum')} className="mt-1 block w-full rounded-md border-blue-200 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2 border bg-white">
                <option value="WGS84">WGS 84</option>
                <option value="PSAD56">PSAD 56</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-blue-800 uppercase tracking-wider">Zona UTM</label>
              <select {...register('zonaUTM')} className="mt-1 block w-full rounded-md border-blue-200 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2 border bg-white">
                <option value="17S">17S (Ecuador Sierra)</option>
                <option value="17N">17N</option>
                <option value="18S">18S</option>
              </select>
            </div>
          </div>

          <div className="mt-4 p-3 bg-blue-100 border border-blue-200 rounded-lg">
            <p className="text-xs text-blue-800 font-semibold mb-1">📍 Referencia Cartográfica</p>
            <p className="text-xs text-blue-700">
              Polígono del predio referenciado a la capa:&nbsp;
              <strong>Catastro Rural – GADM Cayambe</strong> (insumo municipal). Datum: WGS 84 · Zona 17S.
            </p>
          </div>

          <p className="text-xs text-blue-600 mt-2 opacity-80">
            * Coordenadas UTM. Puede ingresar manualmente o usar GPS.
          </p>
        </div>

      </div>
    </div>
  );
}
