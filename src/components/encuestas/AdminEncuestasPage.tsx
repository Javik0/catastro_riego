import { useState, useEffect } from 'react';
import { getEncuestasPublicas, updateEstadoEncuesta } from '../../lib/firestoreService';
import type { EncuestaPublica } from '../../lib/types';
import { useAuth } from '../../hooks/useAuth';
import { 
  ClipboardList, Search, Eye, CheckCircle2, XCircle, Clock, 
  Copy, Check, FileText, Calendar, User, MapPin, Loader2, RefreshCw,
  Home, Sprout
} from 'lucide-react';

export default function AdminEncuestasPage() {
  const { userProfile } = useAuth();
  const [encuestas, setEncuestas] = useState<EncuestaPublica[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedEncuesta, setSelectedEncuesta] = useState<EncuestaPublica | null>(null);
  
  // Filter States
  const [busqueda, setBusqueda] = useState('');
  const [estadoFiltro, setEstadoFiltro] = useState<string>('pendiente'); // Default to pending
  const [comunidadFiltro, setComunidadFiltro] = useState('');

  // UI States
  const [copySuccess, setCopySuccess] = useState<Record<string, boolean>>({});
  const [observacionesInput, setObservacionesInput] = useState('');
  const [savingAction, setSavingAction] = useState(false);

  // Load surveys
  const fetchEncuestas = async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    try {
      const data = await getEncuestasPublicas();
      setEncuestas(data);
    } catch (err) {
      console.error("Error loading surveys:", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchEncuestas();
  }, []);

  // Copy to clipboard helper
  const handleCopy = async (text: string, fieldId: string) => {
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopySuccess(prev => ({ ...prev, [fieldId]: true }));
      setTimeout(() => {
        setCopySuccess(prev => ({ ...prev, [fieldId]: false }));
      }, 2000);
    } catch (err) {
      console.error("Error copying text:", err);
    }
  };

  // Update survey status
  const handleUpdateStatus = async (id: string, nuevoEstado: 'procesada' | 'rechazada') => {
    setSavingAction(true);
    try {
      const email = userProfile?.email || 'Técnico';
      await updateEstadoEncuesta(id, nuevoEstado, observacionesInput, email);
      
      // Update local state
      setEncuestas(prev => 
        prev.map(e => e.id === id ? { 
          ...e, 
          estado: nuevoEstado, 
          observaciones: observacionesInput,
          procesado_por: email,
          fecha_procesado: new Date().toISOString()
        } : e)
      );
      
      // Close modal or update selected
      if (selectedEncuesta?.id === id) {
        setSelectedEncuesta(prev => prev ? {
          ...prev,
          estado: nuevoEstado,
          observaciones: observacionesInput,
          procesado_por: email,
          fecha_procesado: new Date().toISOString()
        } : null);
      }
      setObservacionesInput('');
    } catch (err) {
      console.error(err);
      alert("Error al actualizar el estado de la encuesta.");
    } finally {
      setSavingAction(false);
    }
  };

  // KPIs
  const total = encuestas.length;
  const pendientes = encuestas.filter(e => e.estado === 'pendiente').length;
  const procesadas = encuestas.filter(e => e.estado === 'procesada').length;
  const rechazadas = encuestas.filter(e => e.estado === 'rechazada').length;

  // Filtered surveys list
  const listadoFiltrado = encuestas.filter(e => {
    const q = busqueda.toLowerCase().trim();
    const matchesSearch = q === '' || 
      `${e.nombres} ${e.apellidos}`.toLowerCase().includes(q) ||
      e.cedula.includes(q) ||
      e.clave_catastral?.includes(q);
      
    const matchesEstado = estadoFiltro === '' || e.estado === estadoFiltro;
    const matchesComunidad = comunidadFiltro === '' || e.comunidad === comunidadFiltro;

    return matchesSearch && matchesEstado && matchesComunidad;
  });

  const uniqueComunidades = Array.from(new Set(encuestas.map(e => e.comunidad))).filter(Boolean).sort();

  return (
    <div className="space-y-6 text-slate-200">
      {/* Title & Top Action bar */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <ClipboardList className="w-6 h-6 text-amber-500" />
            Control de Encuestas Públicas
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Gestión y revisión de fichas enviadas en línea por los comuneros para digitar en QField.
          </p>
        </div>
        <button 
          onClick={() => fetchEncuestas(true)}
          disabled={refreshing}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 hover:bg-slate-700 text-xs font-semibold cursor-pointer disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
          {refreshing ? 'Actualizando...' : 'Refrescar'}
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-4">
          <p className="text-[10px] uppercase font-bold tracking-wider text-slate-400">Total Recibidas</p>
          <p className="text-2xl font-bold text-white mt-1">{total}</p>
        </div>
        <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-4 flex justify-between items-start">
          <div>
            <p className="text-[10px] uppercase font-bold tracking-wider text-slate-400">Pendientes</p>
            <p className="text-2xl font-bold text-amber-400 mt-1">{pendientes}</p>
          </div>
          <Clock className="w-5 h-5 text-amber-500/50" />
        </div>
        <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-4 flex justify-between items-start">
          <div>
            <p className="text-[10px] uppercase font-bold tracking-wider text-slate-400">Procesadas</p>
            <p className="text-2xl font-bold text-emerald-400 mt-1">{procesadas}</p>
          </div>
          <CheckCircle2 className="w-5 h-5 text-emerald-500/50" />
        </div>
        <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-4 flex justify-between items-start">
          <div>
            <p className="text-[10px] uppercase font-bold tracking-wider text-slate-400">Rechazadas</p>
            <p className="text-2xl font-bold text-red-400 mt-1">{rechazadas}</p>
          </div>
          <XCircle className="w-5 h-5 text-red-500/50" />
        </div>
      </div>

      {/* Filter panel */}
      <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-4 flex flex-col md:flex-row gap-3 items-center">
        {/* Search */}
        <div className="relative flex-1 w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input 
            type="text" 
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            placeholder="Buscar por regante, cédula o clave..."
            className="w-full bg-slate-950 border border-slate-800 focus:border-blue-500 rounded-lg pl-9 pr-3 py-2 text-xs focus:outline-none transition-colors"
          />
        </div>

        {/* Status Filter */}
        <div className="w-full md:w-auto">
          <select 
            value={estadoFiltro}
            onChange={(e) => setEstadoFiltro(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 focus:border-blue-500 rounded-lg px-3 py-2 text-xs focus:outline-none cursor-pointer"
          >
            <option value="">Todos los Estados</option>
            <option value="pendiente">⏳ Pendientes</option>
            <option value="procesada">✓ Procesadas</option>
            <option value="rechazada">✗ Rechazadas</option>
          </select>
        </div>

        {/* Community Filter */}
        <div className="w-full md:w-auto">
          <select 
            value={comunidadFiltro}
            onChange={(e) => setComunidadFiltro(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 focus:border-blue-500 rounded-lg px-3 py-2 text-xs focus:outline-none cursor-pointer"
          >
            <option value="">Todas las Comunidades</option>
            {uniqueComunidades.map(com => <option key={com} value={com}>{com}</option>)}
          </select>
        </div>
      </div>

      {/* Data Table */}
      {loading ? (
        <div className="py-20 text-center flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
          <p className="text-sm text-slate-400">Cargando encuestas...</p>
        </div>
      ) : listadoFiltrado.length === 0 ? (
        <div className="py-20 text-center bg-slate-900/20 border border-slate-800 border-dashed rounded-xl">
          <p className="text-slate-400 text-sm">No se encontraron encuestas con los filtros seleccionados.</p>
        </div>
      ) : (
        <div className="bg-slate-900/40 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="bg-slate-950/60 border-b border-slate-850 text-slate-300 font-semibold uppercase tracking-wider text-[10px]">
                  <th className="p-4">Regante</th>
                  <th className="p-4">Cédula</th>
                  <th className="p-4">Comunidad</th>
                  <th className="p-4">Celular</th>
                  <th className="p-4">Fecha Envío</th>
                  <th className="p-4">Estado</th>
                  <th className="p-4 text-right">Ver</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-850">
                {listadoFiltrado.map((enc) => {
                  const dateStr = enc.fecha_envio ? new Date(enc.fecha_envio).toLocaleDateString('es-EC', {
                    day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit'
                  }) : 'Sin fecha';
                  return (
                    <tr key={enc.id} className="hover:bg-slate-900/30 transition-colors">
                      <td className="p-4 font-semibold text-white">
                        {enc.apellidos} {enc.nombres}
                      </td>
                      <td className="p-4 font-mono">{enc.cedula}</td>
                      <td className="p-4">{enc.comunidad}</td>
                      <td className="p-4 font-mono">{enc.telefono_celular}</td>
                      <td className="p-4 text-slate-400">{dateStr}</td>
                      <td className="p-4">
                        <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                          enc.estado === 'procesada' 
                            ? 'bg-emerald-500/20 text-emerald-300' 
                            : enc.estado === 'rechazada' 
                              ? 'bg-red-500/20 text-red-300' 
                              : 'bg-amber-500/20 text-amber-300'
                        }`}>
                          {enc.estado === 'procesada' ? 'Procesada' : enc.estado === 'rechazada' ? 'Rechazada' : 'Pendiente'}
                        </span>
                      </td>
                      <td className="p-4 text-right">
                        <button 
                          onClick={() => {
                            setSelectedEncuesta(enc);
                            setObservacionesInput(enc.observaciones || '');
                          }}
                          className="p-1 px-2.5 bg-blue-600/20 hover:bg-blue-600/35 border border-blue-500/20 hover:border-blue-500/30 text-blue-300 rounded-md transition-all inline-flex items-center gap-1 font-semibold cursor-pointer"
                        >
                          <Eye className="w-3.5 h-3.5" /> Detalle
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="p-4 bg-slate-950/20 border-t border-slate-850 flex justify-between items-center text-[10px] text-slate-400">
            <span>Mostrando {listadoFiltrado.length} de {total} encuestas</span>
          </div>
        </div>
      )}

      {/* Detail Modal */}
      {selectedEncuesta && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col justify-between shadow-2xl">
            {/* Modal Header */}
            <div className="p-5 border-b border-slate-800 bg-slate-950/40 flex justify-between items-center">
              <div>
                <h3 className="text-md font-bold text-white flex items-center gap-2">
                  <FileText className="w-5 h-5 text-amber-500" />
                  Detalle de Entrevista: {selectedEncuesta.apellidos} {selectedEncuesta.nombres}
                </h3>
                <p className="text-[10px] text-slate-400 mt-1 flex items-center gap-4">
                  <span className="flex items-center gap-1"><Calendar className="w-3.5 h-3.5" /> Recibido: {new Date(selectedEncuesta.fecha_envio).toLocaleString('es-EC')}</span>
                  <span className="flex items-center gap-1"><User className="w-3.5 h-3.5" /> ID: {selectedEncuesta.id}</span>
                </p>
              </div>
              <button 
                onClick={() => {
                  setSelectedEncuesta(null);
                  setObservacionesInput('');
                }}
                className="text-slate-400 hover:text-white p-1 hover:bg-white/10 rounded-md transition-colors cursor-pointer"
              >
                ✕
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-6 flex-1 text-xs">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                
                {/* PESTAÑA 1: DATOS DEL PROPIETARIO */}
                <div className="bg-slate-950/30 border border-slate-850 rounded-xl p-4 space-y-3">
                  <h4 className="font-bold text-white text-xs border-b border-slate-800 pb-1.5 flex items-center gap-1.5">
                    <User className="w-4 h-4 text-blue-400" />
                    1. DATOS DEL PROPIETARIO
                  </h4>
                  
                  <div className="space-y-2.5">
                    {/* Clave catastral */}
                    <div className="flex justify-between items-center bg-slate-950/50 p-2 rounded-lg border border-slate-900">
                      <div>
                        <span className="text-[10px] text-slate-500 block">Clave Catastral (Impuesto)</span>
                        <span className="font-mono text-white text-xs font-semibold">{selectedEncuesta.clave_catastral || 'Sin especificar'}</span>
                      </div>
                      {selectedEncuesta.clave_catastral && (
                        <button 
                          onClick={() => handleCopy(selectedEncuesta.clave_catastral, 'cc')}
                          className="p-1 hover:bg-white/10 rounded text-slate-400 hover:text-white transition-colors cursor-pointer"
                        >
                          {copySuccess['cc'] ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>
                      )}
                    </div>

                    {/* Cédula */}
                    <div className="flex justify-between items-center bg-slate-950/50 p-2 rounded-lg border border-slate-900">
                      <div>
                        <span className="text-[10px] text-slate-500 block">Cédula de Identidad</span>
                        <span className="font-mono text-white text-xs font-semibold">{selectedEncuesta.cedula}</span>
                      </div>
                      <button 
                        onClick={() => handleCopy(selectedEncuesta.cedula, 'ced')}
                        className="p-1 hover:bg-white/10 rounded text-slate-400 hover:text-white transition-colors cursor-pointer"
                      >
                        {copySuccess['ced'] ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                    </div>

                    {/* Nombres y Apellidos */}
                    <div className="grid grid-cols-2 gap-2">
                      <div className="bg-slate-950/50 p-2 rounded-lg border border-slate-900 flex justify-between items-center">
                        <div className="min-w-0">
                          <span className="text-[10px] text-slate-500 block">Apellidos</span>
                          <span className="font-semibold text-white truncate block">{selectedEncuesta.apellidos}</span>
                        </div>
                        <button 
                          onClick={() => handleCopy(selectedEncuesta.apellidos, 'ap')}
                          className="p-1 hover:bg-white/10 rounded text-slate-400 hover:text-white transition-colors cursor-pointer"
                        >
                          {copySuccess['ap'] ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                      <div className="bg-slate-950/50 p-2 rounded-lg border border-slate-900 flex justify-between items-center">
                        <div className="min-w-0">
                          <span className="text-[10px] text-slate-500 block">Nombres</span>
                          <span className="font-semibold text-white truncate block">{selectedEncuesta.nombres}</span>
                        </div>
                        <button 
                          onClick={() => handleCopy(selectedEncuesta.nombres, 'nom')}
                          className="p-1 hover:bg-white/10 rounded text-slate-400 hover:text-white transition-colors cursor-pointer"
                        >
                          {copySuccess['nom'] ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                    </div>

                    {/* Comunidad y Celular */}
                    <div className="grid grid-cols-2 gap-2">
                      <div className="bg-slate-950/50 p-2 rounded-lg border border-slate-900 flex justify-between items-center">
                        <div className="min-w-0">
                          <span className="text-[10px] text-slate-500 block">Comunidad</span>
                          <span className="font-semibold text-white truncate block">{selectedEncuesta.comunidad}</span>
                        </div>
                        <button 
                          onClick={() => handleCopy(selectedEncuesta.comunidad, 'com')}
                          className="p-1 hover:bg-white/10 rounded text-slate-400 hover:text-white transition-colors cursor-pointer"
                        >
                          {copySuccess['com'] ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                      <div className="bg-slate-950/50 p-2 rounded-lg border border-slate-900 flex justify-between items-center">
                        <div className="min-w-0">
                          <span className="text-[10px] text-slate-500 block">Celular</span>
                          <span className="font-mono text-white truncate block">{selectedEncuesta.telefono_celular}</span>
                        </div>
                        <button 
                          onClick={() => handleCopy(selectedEncuesta.telefono_celular, 'tel')}
                          className="p-1 hover:bg-white/10 rounded text-slate-400 hover:text-white transition-colors cursor-pointer"
                        >
                          {copySuccess['tel'] ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                    </div>

                    {/* Demographics */}
                    <div className="grid grid-cols-3 gap-2 bg-slate-950/50 p-2.5 rounded-lg border border-slate-900 text-center">
                      <div>
                        <span className="text-[9px] text-slate-500 block">Hijos Varones</span>
                        <span className="font-bold text-white text-xs">{selectedEncuesta.hijos_hombres}</span>
                      </div>
                      <div className="border-x border-slate-850">
                        <span className="text-[9px] text-slate-500 block">Hijos Mujeres</span>
                        <span className="font-bold text-white text-xs">{selectedEncuesta.hijos_mujeres}</span>
                      </div>
                      <div>
                        <span className="text-[9px] text-slate-500 block">Tenencia Terreno</span>
                        <span className="font-bold text-blue-300 text-[10px]">{selectedEncuesta.tenencia_predio}</span>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-2 bg-slate-950/50 p-2.5 rounded-lg border border-slate-900">
                      <div>
                        <span className="text-[9px] text-slate-500 block">Instrucción</span>
                        <span className="font-semibold text-white">{selectedEncuesta.nivel_instruccion}</span>
                      </div>
                      <div>
                        <span className="text-[9px] text-slate-500 block">¿Tiene Vivienda?</span>
                        <span className={`font-bold text-[10px] ${selectedEncuesta.tiene_construccion ? 'text-emerald-400' : 'text-slate-500'}`}>
                          {selectedEncuesta.tiene_construccion ? 'SÍ, TIENE CASA' : 'NO TIENE CASA'}
                        </span>
                      </div>
                    </div>

                  </div>
                </div>

                {/* PESTAÑA 3: SERVICIOS BÁSICOS */}
                <div className="bg-slate-950/30 border border-slate-850 rounded-xl p-4 space-y-3">
                  <h4 className="font-bold text-white text-xs border-b border-slate-800 pb-1.5 flex items-center gap-1.5">
                    <Home className="w-4 h-4 text-emerald-400" />
                    3. SERVICIOS Y CONSTRUCCIÓN
                  </h4>

                  {!selectedEncuesta.tiene_construccion ? (
                    <p className="text-slate-500 italic py-8 text-center bg-slate-950/45 rounded-lg border border-slate-900">
                      Sin construcción en el lote. No aplican servicios.
                    </p>
                  ) : (
                    <div className="space-y-3">
                      <div className="grid grid-cols-2 gap-2 text-center">
                        <div className={`p-2.5 rounded-lg border ${selectedEncuesta.agua_consumo ? 'bg-blue-500/10 border-blue-500/30 text-blue-300' : 'bg-slate-950/40 border-slate-900 text-slate-500'}`}>
                          <span className="block text-[9px] uppercase tracking-wider font-bold">Agua Potable</span>
                          <span className="font-bold text-xs">{selectedEncuesta.agua_consumo ? 'CON SERVICIO' : 'SIN SERVICIO'}</span>
                        </div>
                        <div className={`p-2.5 rounded-lg border ${selectedEncuesta.energia_electrica ? 'bg-amber-500/10 border-amber-500/30 text-amber-300' : 'bg-slate-950/40 border-slate-900 text-slate-500'}`}>
                          <span className="block text-[9px] uppercase tracking-wider font-bold">Luz Eléctrica</span>
                          <span className="font-bold text-xs">{selectedEncuesta.energia_electrica ? 'CON SERVICIO' : 'SIN SERVICIO'}</span>
                        </div>
                      </div>

                      <div className="bg-slate-950/50 p-2.5 rounded-lg border border-slate-900 flex justify-between items-center">
                        <div>
                          <span className="text-[9px] text-slate-500 block">Material predominante</span>
                          <span className="font-semibold text-white uppercase text-xs">
                            {selectedEncuesta.material_construccion === 'Otros' 
                              ? `Otros (${selectedEncuesta.material_constr_otro})` 
                              : selectedEncuesta.material_construccion || 'Sin especificar'}
                          </span>
                        </div>
                        {selectedEncuesta.material_construccion && (
                          <button 
                            onClick={() => handleCopy(selectedEncuesta.material_construccion === 'Otros' ? selectedEncuesta.material_constr_otro || '' : selectedEncuesta.material_construccion, 'mat')}
                            className="p-1 hover:bg-white/10 rounded text-slate-400 hover:text-white transition-colors cursor-pointer"
                          >
                            {copySuccess['mat'] ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                          </button>
                        )}
                      </div>
                    </div>
                  )}
                </div>

              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* PESTAÑA 4: PRODUCCIÓN (CULTIVOS Y ANIMALES) */}
                <div className="bg-slate-950/30 border border-slate-850 rounded-xl p-4 space-y-4">
                  <h4 className="font-bold text-white text-xs border-b border-slate-800 pb-1.5 flex items-center gap-1.5">
                    <Sprout className="w-4 h-4 text-amber-400" />
                    4. PRODUCCIÓN AGRÍCOLA Y PECUARIA
                  </h4>

                  {/* Cultivos list */}
                  <div className="space-y-2">
                    <span className="text-[10px] text-slate-400 font-bold block">🌾 Cultivos Reportados</span>
                    {!selectedEncuesta.cultivos || selectedEncuesta.cultivos.length === 0 ? (
                      <p className="text-[10px] text-slate-500 italic bg-slate-950/30 p-2 rounded-lg text-center">No reportó cultivos.</p>
                    ) : (
                      <div className="space-y-1.5">
                        {selectedEncuesta.cultivos.map((c, i) => (
                          <div key={i} className="flex justify-between items-center bg-slate-950/50 p-2 rounded-lg border border-slate-900">
                            <div>
                              <span className="font-semibold text-white">
                                {c.tipo_cultivo === 'Otros' ? `Otros (${c.tipo_cultivo_otro})` : c.tipo_cultivo}
                              </span>
                              {c.es_principal && <span className="ml-2 bg-emerald-500/20 text-emerald-300 text-[8px] font-bold px-1.5 py-0.5 rounded-full uppercase">Principal</span>}
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="font-mono text-slate-300 font-semibold">{c.superficie_m2} m²</span>
                              <button 
                                onClick={() => handleCopy(String(c.superficie_m2), `c_sup_${i}`)}
                                className="p-0.5 hover:bg-white/10 rounded text-slate-500 hover:text-white transition-colors cursor-pointer"
                                title="Copiar área del cultivo"
                              >
                                {copySuccess[`c_sup_${i}`] ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Animales list */}
                  <div className="space-y-2">
                    <span className="text-[10px] text-slate-400 font-bold block">🐄 Animales / Especies</span>
                    {!selectedEncuesta.animales || selectedEncuesta.animales.length === 0 ? (
                      <p className="text-[10px] text-slate-500 italic bg-slate-950/30 p-2 rounded-lg text-center">No reportó animales.</p>
                    ) : (
                      <div className="space-y-1.5">
                        {selectedEncuesta.animales.map((a, i) => (
                          <div key={i} className="flex justify-between items-center bg-slate-950/50 p-2 rounded-lg border border-slate-900">
                            <span className="font-semibold text-white">
                              {a.especie === 'Otros' ? `Otros (${a.especie_otro})` : a.especie}
                            </span>
                            <div className="flex items-center gap-2">
                              <span className="font-mono text-slate-300 font-bold bg-slate-900 px-2 py-0.5 rounded border border-slate-800">{a.cantidad} cabezas</span>
                              <button 
                                onClick={() => handleCopy(String(a.cantidad), `a_cant_${i}`)}
                                className="p-0.5 hover:bg-white/10 rounded text-slate-500 hover:text-white transition-colors cursor-pointer"
                              >
                                {copySuccess[`a_cant_${i}`] ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Water usage */}
                  <div className="grid grid-cols-2 gap-2 bg-slate-950/50 p-2.5 rounded-lg border border-slate-900">
                    <div>
                      <span className="text-[9px] text-slate-500 block">Consumo Familiar</span>
                      <span className="font-mono text-emerald-400 font-bold text-xs">{selectedEncuesta.soberania_aliment_pct}%</span>
                    </div>
                    <div>
                      <span className="text-[9px] text-slate-500 block">Actividad Productiva</span>
                      <span className="font-semibold text-white text-xs">{selectedEncuesta.actividad_productiva}</span>
                    </div>
                  </div>
                </div>

                {/* PESTAÑA 7: OTROS PREDIOS (OPCIONAL) */}
                <div className="bg-slate-950/30 border border-slate-850 rounded-xl p-4 space-y-3">
                  <h4 className="font-bold text-white text-xs border-b border-slate-800 pb-1.5 flex items-center gap-1.5">
                    <MapPin className="w-4 h-4 text-blue-400" />
                    7. OTROS PREDIOS DEL REGANTE
                  </h4>

                  {!selectedEncuesta.predios_adicionales || selectedEncuesta.predios_adicionales.length === 0 ? (
                    <p className="text-slate-500 italic py-12 text-center bg-slate-950/45 rounded-lg border border-slate-900">
                      No reportó otros predios adicionales.
                    </p>
                  ) : (
                    <div className="space-y-2">
                      {selectedEncuesta.predios_adicionales.map((p, i) => (
                        <div key={i} className="bg-slate-950/50 p-2.5 rounded-lg border border-slate-900 space-y-2">
                          <div className="flex justify-between items-center">
                            <div>
                              <span className="text-[9px] text-slate-500 block">Clave Catastral Adicional</span>
                              <span className="font-mono text-white text-xs font-semibold">{p.clave_catastral_otro}</span>
                            </div>
                            <button 
                              onClick={() => handleCopy(p.clave_catastral_otro, `pa_cc_${i}`)}
                              className="p-1 hover:bg-white/10 rounded text-slate-400 hover:text-white transition-colors cursor-pointer"
                            >
                              {copySuccess[`pa_cc_${i}`] ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                            </button>
                          </div>
                          <div className="flex justify-between items-center border-t border-slate-900/60 pt-1.5">
                            <div>
                              <span className="text-[9px] text-slate-500 block">Área de Riego Adicional</span>
                              <span className="font-mono text-white text-xs">{p.area_riego_otro} m²</span>
                            </div>
                            <button 
                              onClick={() => handleCopy(String(p.area_riego_otro), `pa_area_${i}`)}
                              className="p-1 hover:bg-white/10 rounded text-slate-400 hover:text-white transition-colors cursor-pointer"
                            >
                              {copySuccess[`pa_area_${i}`] ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Status and auditing log */}
              {selectedEncuesta.estado !== 'pendiente' && (
                <div className="bg-slate-950/20 border border-slate-805 rounded-xl p-4 flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
                  <div>
                    <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider block">Bitácora de Auditoría</span>
                    <p className="text-xs mt-1">
                      Encuesta marcada como <span className={selectedEncuesta.estado === 'procesada' ? 'text-emerald-400 font-bold' : 'text-red-400 font-bold'}>{selectedEncuesta.estado.toUpperCase()}</span> por <span className="font-semibold text-slate-200">{selectedEncuesta.procesado_por}</span> en <span className="text-slate-400">{selectedEncuesta.fecha_procesado ? new Date(selectedEncuesta.fecha_procesado).toLocaleString('es-EC') : 'sin fecha'}.</span>
                    </p>
                  </div>
                  {selectedEncuesta.observaciones && (
                    <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-900 flex-1 max-w-md w-full">
                      <span className="text-[9px] text-slate-500 block">Observaciones / Notas:</span>
                      <p className="text-slate-300 text-xs mt-0.5 italic">"{selectedEncuesta.observaciones}"</p>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Modal Actions Panel */}
            <div className="p-5 border-t border-slate-800 bg-slate-950/40 space-y-4">
              {/* Observaciones input */}
              <div>
                <label className="block text-[10px] text-slate-400 font-semibold mb-1">Notas de Revisión / Observaciones para digitar en QField</label>
                <textarea 
                  value={observacionesInput}
                  onChange={(e) => setObservacionesInput(e.target.value)}
                  placeholder="Escriba comentarios, errores encontrados o indicaciones para el ingreso del polígono en QGIS..."
                  rows={2}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-blue-500 rounded-lg px-3 py-2 text-xs focus:outline-none transition-colors resize-none"
                />
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row justify-between gap-3">
                <button
                  onClick={() => {
                    setSelectedEncuesta(null);
                    setObservacionesInput('');
                  }}
                  className="px-4 py-2 border border-slate-800 hover:bg-slate-800 text-slate-300 rounded-lg text-xs font-semibold transition-colors cursor-pointer"
                >
                  Cerrar Ventana
                </button>

                <div className="flex gap-2">
                  {/* Rechazar button */}
                  <button
                    onClick={() => handleUpdateStatus(selectedEncuesta.id, 'rechazada')}
                    disabled={savingAction}
                    className="px-4 py-2 bg-red-600/20 hover:bg-red-600/35 border border-red-500/20 hover:border-red-500/30 text-red-300 rounded-lg text-xs font-semibold transition-all inline-flex items-center gap-1 cursor-pointer disabled:opacity-50"
                  >
                    <XCircle className="w-4 h-4" />
                    Marcar como Rechazada
                  </button>

                  {/* Procesar button */}
                  <button
                    onClick={() => handleUpdateStatus(selectedEncuesta.id, 'procesada')}
                    disabled={savingAction}
                    className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-800 text-white rounded-lg text-xs font-bold transition-all inline-flex items-center justify-center gap-1 cursor-pointer disabled:opacity-50 min-w-[150px]"
                  >
                    {savingAction ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" /> Guardando...
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="w-4 h-4" />
                        Marcar como Procesada
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>

          </div>
        </div>
      )}
    </div>
  );
}
