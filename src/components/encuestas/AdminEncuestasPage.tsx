import { useState, useEffect } from 'react';
import { getEncuestasPublicas, updateEstadoEncuesta } from '../../lib/firestoreService';
import type { EncuestaPublica } from '../../lib/types';
import { useAuth } from '../../hooks/useAuth';
import { 
  ClipboardList, Search, Eye, CheckCircle2, XCircle, Clock, 
  Copy, Check, FileText, Calendar, User, MapPin, Loader2, RefreshCw,
  Home, Sprout, Link, ExternalLink
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
  const [copiedRegantesLink, setCopiedRegantesLink] = useState(false);

  const handleCopyRegantesLink = async () => {
    const url = `${window.location.origin}/encuesta`;
    try {
      await navigator.clipboard.writeText(url);
      setCopiedRegantesLink(true);
      setTimeout(() => setCopiedRegantesLink(false), 2000);
    } catch (err) {
      console.error(err);
    }
  };

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
    <div className="space-y-6" style={{ color: 'var(--text-primary)' }}>
      {/* Title & Top Action bar */}
      <div className="flex flex-col xl:flex-row justify-between items-start xl:items-center gap-4 border-b pb-4" style={{ borderBottomColor: 'var(--border-color)' }}>
        <div>
          <h2 className="text-xl font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
            <ClipboardList className="w-6 h-6 text-amber-500" />
            Control de Encuestas Públicas
          </h2>
          <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>
            Gestión y revisión de fichas enviadas en línea por los comuneros para digitar en QField.
          </p>
        </div>
        
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 w-full xl:w-auto">
          {/* Botón para copiar enlace público de regantes */}
          <button
            onClick={handleCopyRegantesLink}
            className={`flex items-center justify-center gap-2 px-3.5 py-1.5 rounded-lg border text-xs font-bold transition-all cursor-pointer ${
              copiedRegantesLink
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                : 'bg-amber-500/10 border-amber-500/20 hover:border-amber-500/40 text-amber-300 hover:bg-amber-500/15'
            }`}
          >
            {copiedRegantesLink ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-400" />
                ¡Enlace Copiado!
              </>
            ) : (
              <>
                <Link className="w-3.5 h-3.5 text-amber-400" />
                Copiar Enlace Regantes
              </>
            )}
          </button>

          <a
            href="/encuesta"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-semibold hover:opacity-90 transition-colors shadow-sm"
            style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}
          >
            <ExternalLink className="w-3.5 h-3.5" />
            Abrir Encuesta
          </a>

          <button 
            onClick={() => fetchEncuestas(true)}
            disabled={refreshing}
            className="flex items-center justify-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-semibold cursor-pointer disabled:opacity-50 hover:opacity-90 transition-colors shrink-0 shadow-sm"
            style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
            {refreshing ? 'Actualizando...' : 'Refrescar'}
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="rounded-xl border p-4 shadow-sm" style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
          <p className="text-[10px] uppercase font-bold tracking-wider" style={{ color: 'var(--text-secondary)' }}>Total Recibidas</p>
          <p className="text-2xl font-bold mt-1" style={{ color: 'var(--text-primary)' }}>{total}</p>
        </div>
        <div className="rounded-xl border p-4 flex justify-between items-start shadow-sm" style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
          <div>
            <p className="text-[10px] uppercase font-bold tracking-wider" style={{ color: 'var(--text-secondary)' }}>Pendientes</p>
            <p className="text-2xl font-bold text-amber-550 mt-1">{pendientes}</p>
          </div>
          <Clock className="w-5 h-5 text-amber-500/55" />
        </div>
        <div className="rounded-xl border p-4 flex justify-between items-start shadow-sm" style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
          <div>
            <p className="text-[10px] uppercase font-bold tracking-wider" style={{ color: 'var(--text-secondary)' }}>Procesadas</p>
            <p className="text-2xl font-bold text-emerald-550 mt-1">{procesadas}</p>
          </div>
          <CheckCircle2 className="w-5 h-5 text-emerald-500/55" />
        </div>
        <div className="rounded-xl border p-4 flex justify-between items-start shadow-sm" style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
          <div>
            <p className="text-[10px] uppercase font-bold tracking-wider" style={{ color: 'var(--text-secondary)' }}>Rechazadas</p>
            <p className="text-2xl font-bold text-red-550 mt-1">{rechazadas}</p>
          </div>
          <XCircle className="w-5 h-5 text-red-500/55" />
        </div>
      </div>

      {/* Filter panel */}
      <div className="rounded-xl border p-4 flex flex-col md:flex-row gap-3 items-center shadow-sm" style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
        {/* Search */}
        <div className="relative flex-1 w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: 'var(--text-secondary)' }} />
          <input 
            type="text" 
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            placeholder="Buscar por regante, cédula o clave..."
            className="w-full border rounded-lg pl-9 pr-3 py-2 text-xs focus:outline-none transition-colors"
            style={{ background: 'var(--bg-input)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}
          />
        </div>

        {/* Status Filter */}
        <div className="w-full md:w-auto">
          <select 
            value={estadoFiltro}
            onChange={(e) => setEstadoFiltro(e.target.value)}
            className="w-full border rounded-lg px-3 py-2 text-xs focus:outline-none cursor-pointer"
            style={{ background: 'var(--bg-input)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}
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
            className="w-full border rounded-lg px-3 py-2 text-xs focus:outline-none cursor-pointer"
            style={{ background: 'var(--bg-input)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}
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
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Cargando encuestas...</p>
        </div>
      ) : listadoFiltrado.length === 0 ? (
        <div className="py-20 text-center border border-dashed rounded-xl" style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)', color: 'var(--text-secondary)' }}>
          <p className="text-sm">No se encontraron encuestas con los filtros seleccionados.</p>
        </div>
      ) : (
        <div className="rounded-xl overflow-hidden shadow-lg border animate-fadeIn" style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="border-b font-semibold uppercase tracking-wider text-[10px]" style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)', color: 'var(--text-secondary)' }}>
                  <th className="p-4">Regante</th>
                  <th className="p-4">Cédula</th>
                  <th className="p-4">Comunidad</th>
                  <th className="p-4">Celular</th>
                  <th className="p-4">Fecha Envío</th>
                  <th className="p-4">Estado</th>
                  <th className="p-4 text-right">Ver</th>
                </tr>
              </thead>
              <tbody className="divide-y" style={{ borderColor: 'var(--border-color)' }}>
                {listadoFiltrado.map((enc) => {
                  const dateStr = enc.fecha_envio ? new Date(enc.fecha_envio).toLocaleDateString('es-EC', {
                    day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit'
                  }) : 'Sin fecha';
                  return (
                    <tr key={enc.id} className="transition-colors hover:bg-slate-400/5" style={{ backgroundColor: 'var(--row-alt)' }}>
                      <td className="p-4 font-semibold" style={{ color: 'var(--text-primary)' }}>
                        {enc.apellidos} {enc.nombres}
                      </td>
                      <td className="p-4 font-mono">{enc.cedula}</td>
                      <td className="p-4">{enc.comunidad}</td>
                      <td className="p-4 font-mono">{enc.telefono_celular}</td>
                      <td className="p-4" style={{ color: 'var(--text-secondary)' }}>{dateStr}</td>
                      <td className="p-4">
                        <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                          enc.estado === 'procesada' 
                            ? 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-300' 
                            : enc.estado === 'rechazada' 
                              ? 'bg-red-500/20 text-red-600 dark:text-red-300' 
                              : 'bg-amber-500/20 text-amber-600 dark:text-amber-300'
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
                          className="p-1 px-2.5 bg-blue-600/10 hover:bg-blue-600/20 border border-blue-500/30 text-blue-600 dark:text-blue-300 rounded-md transition-all inline-flex items-center gap-1 font-semibold cursor-pointer"
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
          <div className="p-4 border-t flex justify-between items-center text-[10px]" style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)', color: 'var(--text-secondary)' }}>
            <span>Mostrando {listadoFiltrado.length} de {total} encuestas</span>
          </div>
        </div>
      )}

      {/* Detail Modal */}
      {selectedEncuesta && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
          <div className="border rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col justify-between shadow-2xl animate-scaleIn" style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}>
            {/* Modal Header */}
            <div className="p-5 border-b flex justify-between items-center" style={{ background: 'var(--bg-primary)', borderBottomColor: 'var(--border-color)' }}>
              <div>
                <h3 className="text-md font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                  <FileText className="w-5 h-5 text-amber-500" />
                  Detalle de Entrevista: {selectedEncuesta.apellidos} {selectedEncuesta.nombres}
                </h3>
                <p className="text-[10px] mt-1 flex items-center gap-4" style={{ color: 'var(--text-secondary)' }}>
                  <span className="flex items-center gap-1"><Calendar className="w-3.5 h-3.5" /> Recibido: {new Date(selectedEncuesta.fecha_envio).toLocaleString('es-EC')}</span>
                  <span className="flex items-center gap-1"><User className="w-3.5 h-3.5" /> ID: {selectedEncuesta.id}</span>
                </p>
              </div>
              <button 
                onClick={() => {
                  setSelectedEncuesta(null);
                  setObservacionesInput('');
                }}
                className="p-1 rounded-md transition-colors cursor-pointer hover:bg-black/5 dark:hover:bg-white/10"
                style={{ color: 'var(--text-secondary)' }}
              >
                ✕
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-6 flex-1 text-xs">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                
                {/* PESTAÑA 1: DATOS DEL PROPIETARIO */}
                <div className="rounded-xl p-4 space-y-3 border shadow-sm animate-scaleIn" style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
                  <h4 className="font-bold text-xs pb-1.5 flex items-center gap-1.5 border-b" style={{ color: 'var(--text-primary)', borderBottomColor: 'var(--border-color)' }}>
                    <User className="w-4 h-4 text-blue-500" />
                    1. DATOS DEL PROPIETARIO
                  </h4>
                  
                  <div className="space-y-2.5">
                    {/* Clave catastral */}
                    <div className="flex justify-between items-center p-2 rounded-lg border shadow-sm" style={{ background: 'var(--bg-input)', borderColor: 'var(--border-color)' }}>
                      <div>
                        <span className="text-[10px] block" style={{ color: 'var(--text-secondary)' }}>Clave Catastral (Impuesto)</span>
                        <span className="font-mono text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>{selectedEncuesta.clave_catastral || 'Sin especificar'}</span>
                      </div>
                      {selectedEncuesta.clave_catastral && (
                        <button 
                          onClick={() => handleCopy(selectedEncuesta.clave_catastral, 'cc')}
                          className="p-1 rounded transition-colors cursor-pointer hover:bg-black/5 dark:hover:bg-white/10"
                          style={{ color: 'var(--text-secondary)' }}
                        >
                          {copySuccess['cc'] ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>
                      )}
                    </div>

                    {/* Cédula */}
                    <div className="flex justify-between items-center p-2 rounded-lg border shadow-sm" style={{ background: 'var(--bg-input)', borderColor: 'var(--border-color)' }}>
                      <div>
                        <span className="text-[10px] block" style={{ color: 'var(--text-secondary)' }}>Cédula de Identidad</span>
                        <span className="font-mono text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>{selectedEncuesta.cedula}</span>
                      </div>
                      <button 
                        onClick={() => handleCopy(selectedEncuesta.cedula, 'ced')}
                        className="p-1 rounded transition-colors cursor-pointer hover:bg-black/5 dark:hover:bg-white/10"
                        style={{ color: 'var(--text-secondary)' }}
                      >
                        {copySuccess['ced'] ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                    </div>

                    {/* Nombres y Apellidos */}
                    <div className="grid grid-cols-2 gap-2">
                      <div className="p-2 rounded-lg border flex justify-between items-center shadow-sm" style={{ background: 'var(--bg-input)', borderColor: 'var(--border-color)' }}>
                        <div className="min-w-0">
                          <span className="text-[10px] block" style={{ color: 'var(--text-secondary)' }}>Apellidos</span>
                          <span className="font-semibold truncate block" style={{ color: 'var(--text-primary)' }}>{selectedEncuesta.apellidos}</span>
                        </div>
                        <button 
                          onClick={() => handleCopy(selectedEncuesta.apellidos, 'ap')}
                          className="p-1 rounded transition-colors cursor-pointer hover:bg-black/5 dark:hover:bg-white/10"
                          style={{ color: 'var(--text-secondary)' }}
                        >
                          {copySuccess['ap'] ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                      <div className="p-2 rounded-lg border flex justify-between items-center shadow-sm" style={{ background: 'var(--bg-input)', borderColor: 'var(--border-color)' }}>
                        <div className="min-w-0">
                          <span className="text-[10px] block" style={{ color: 'var(--text-secondary)' }}>Nombres</span>
                          <span className="font-semibold truncate block" style={{ color: 'var(--text-primary)' }}>{selectedEncuesta.nombres}</span>
                        </div>
                        <button 
                          onClick={() => handleCopy(selectedEncuesta.nombres, 'nom')}
                          className="p-1 rounded transition-colors cursor-pointer hover:bg-black/5 dark:hover:bg-white/10"
                          style={{ color: 'var(--text-secondary)' }}
                        >
                          {copySuccess['nom'] ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                    </div>

                    {/* Comunidad, Sector Inv y Parroquia */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                      <div className="p-2 rounded-lg border flex justify-between items-center shadow-sm" style={{ background: 'var(--bg-input)', borderColor: 'var(--border-color)' }}>
                        <div className="min-w-0">
                          <span className="text-[10px] block" style={{ color: 'var(--text-secondary)' }}>Comunidad</span>
                          <span className="font-semibold truncate block" style={{ color: 'var(--text-primary)' }}>{selectedEncuesta.comunidad}</span>
                        </div>
                        <button 
                          onClick={() => handleCopy(selectedEncuesta.comunidad, 'com')}
                          className="p-1 rounded transition-colors cursor-pointer hover:bg-black/5 dark:hover:bg-white/10"
                          style={{ color: 'var(--text-secondary)' }}
                        >
                          {copySuccess['com'] ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>
                      </div>

                      <div className="p-2 rounded-lg border flex justify-between items-center shadow-sm" style={{ background: 'var(--bg-input)', borderColor: 'var(--border-color)' }}>
                        <div className="min-w-0">
                          <span className="text-[10px] block" style={{ color: 'var(--text-secondary)' }}>Sector Inv.</span>
                          <span className="font-semibold truncate block" style={{ color: 'var(--text-primary)' }}>{selectedEncuesta.sector_investigacion || 'Sin especificar'}</span>
                        </div>
                        {selectedEncuesta.sector_investigacion && (
                          <button 
                            onClick={() => handleCopy(selectedEncuesta.sector_investigacion, 'sec_inv')}
                            className="p-1 rounded transition-colors cursor-pointer hover:bg-black/5 dark:hover:bg-white/10"
                            style={{ color: 'var(--text-secondary)' }}
                          >
                            {copySuccess['sec_inv'] ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                          </button>
                        )}
                      </div>

                      <div className="p-2 rounded-lg border flex justify-between items-center shadow-sm" style={{ background: 'var(--bg-input)', borderColor: 'var(--border-color)' }}>
                        <div className="min-w-0">
                          <span className="text-[10px] block" style={{ color: 'var(--text-secondary)' }}>Parroquia</span>
                          <span className="font-semibold truncate block" style={{ color: 'var(--text-primary)' }}>{selectedEncuesta.parroquia || 'Sin especificar'}</span>
                        </div>
                        {selectedEncuesta.parroquia && (
                          <button 
                            onClick={() => handleCopy(selectedEncuesta.parroquia, 'parr')}
                            className="p-1 rounded transition-colors cursor-pointer hover:bg-black/5 dark:hover:bg-white/10"
                            style={{ color: 'var(--text-secondary)' }}
                          >
                            {copySuccess['parr'] ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Celular y Área de Riego */}
                    <div className="grid grid-cols-2 gap-2">
                      <div className="p-2 rounded-lg border flex justify-between items-center shadow-sm" style={{ background: 'var(--bg-input)', borderColor: 'var(--border-color)' }}>
                        <div className="min-w-0">
                          <span className="text-[10px] block" style={{ color: 'var(--text-secondary)' }}>Celular</span>
                          <span className="font-mono truncate block" style={{ color: 'var(--text-primary)' }}>{selectedEncuesta.telefono_celular}</span>
                        </div>
                        <button 
                          onClick={() => handleCopy(selectedEncuesta.telefono_celular, 'tel')}
                          className="p-1 rounded transition-colors cursor-pointer hover:bg-black/5 dark:hover:bg-white/10"
                          style={{ color: 'var(--text-secondary)' }}
                        >
                          {copySuccess['tel'] ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>
                      </div>

                      <div className="p-2 rounded-lg border flex justify-between items-center shadow-sm" style={{ background: 'var(--bg-input)', borderColor: 'var(--border-color)' }}>
                        <div className="min-w-0">
                          <span className="text-[10px] block" style={{ color: 'var(--text-secondary)' }}>Área con Riego</span>
                          <span className="font-mono truncate block" style={{ color: 'var(--text-primary)' }}>{selectedEncuesta.area_riego !== undefined ? `${selectedEncuesta.area_riego} m²` : '0 m²'}</span>
                        </div>
                        {selectedEncuesta.area_riego !== undefined && (
                          <button 
                            onClick={() => handleCopy(String(selectedEncuesta.area_riego), 'area_riego')}
                            className="p-1 rounded transition-colors cursor-pointer hover:bg-black/5 dark:hover:bg-white/10"
                            style={{ color: 'var(--text-secondary)' }}
                          >
                            {copySuccess['area_riego'] ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Reservorio y Métodos de Riego */}
                    <div className="p-2.5 rounded-lg border shadow-sm space-y-1.5" style={{ background: 'var(--bg-input)', borderColor: 'var(--border-color)' }}>
                      <div className="flex justify-between border-b pb-1" style={{ borderColor: 'var(--border-color)' }}>
                        <span className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>Reservorio: <span className="font-bold" style={{ color: 'var(--text-primary)' }}>{selectedEncuesta.tiene_reservorio || 'No'}</span></span>
                        <span className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>Método de Riego:</span>
                      </div>
                      <div className="grid grid-cols-3 text-center text-[10px] font-semibold">
                        <span style={{ color: selectedEncuesta.metodo_gravedad_pct ? 'var(--text-primary)' : 'var(--text-muted)' }}>Gravedad: {selectedEncuesta.metodo_gravedad_pct || 0}%</span>
                        <span className="border-x" style={{ borderColor: 'var(--border-color)', color: selectedEncuesta.metodo_aspersion_pct ? 'var(--text-primary)' : 'var(--text-muted)' }}>Aspersión: {selectedEncuesta.metodo_aspersion_pct || 0}%</span>
                        <span style={{ color: selectedEncuesta.metodo_goteo_pct ? 'var(--text-primary)' : 'var(--text-muted)' }}>Goteo: {selectedEncuesta.metodo_goteo_pct || 0}%</span>
                      </div>
                    </div>

                    {/* Demographics */}
                    <div className="grid grid-cols-3 gap-2 p-2.5 rounded-lg border text-center shadow-sm" style={{ background: 'var(--bg-input)', borderColor: 'var(--border-color)' }}>
                      <div>
                        <span className="text-[9px] block" style={{ color: 'var(--text-secondary)' }}>Hijos Varones</span>
                        <span className="font-bold text-xs" style={{ color: 'var(--text-primary)' }}>{selectedEncuesta.hijos_hombres}</span>
                      </div>
                      <div className="border-x" style={{ borderColor: 'var(--border-color)' }}>
                        <span className="text-[9px] block" style={{ color: 'var(--text-secondary)' }}>Hijos Mujeres</span>
                        <span className="font-bold text-xs" style={{ color: 'var(--text-primary)' }}>{selectedEncuesta.hijos_mujeres}</span>
                      </div>
                      <div>
                        <span className="text-[9px] block" style={{ color: 'var(--text-secondary)' }}>Tenencia Terreno</span>
                        <span className="font-bold text-blue-500 dark:text-blue-300 text-[10px]">{selectedEncuesta.tenencia_predio}</span>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-2 p-2.5 rounded-lg border shadow-sm" style={{ background: 'var(--bg-input)', borderColor: 'var(--border-color)' }}>
                      <div>
                        <span className="text-[9px] block" style={{ color: 'var(--text-secondary)' }}>Instrucción</span>
                        <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{selectedEncuesta.nivel_instruccion}</span>
                      </div>
                      <div>
                        <span className="text-[9px] block" style={{ color: 'var(--text-secondary)' }}>¿Tiene Vivienda?</span>
                        <span className={`font-bold text-[10px] ${selectedEncuesta.tiene_construccion ? 'text-emerald-500 dark:text-emerald-400' : 'text-slate-500'}`}>
                          {selectedEncuesta.tiene_construccion ? 'SÍ, TIENE CASA' : 'NO TIENE CASA'}
                        </span>
                      </div>
                    </div>

                  </div>
                </div>

                {/* PESTAÑA 3: SERVICIOS BÁSICOS */}
                <div className="rounded-xl p-4 space-y-3 border shadow-sm" style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
                  <h4 className="font-bold text-xs pb-1.5 flex items-center gap-1.5 border-b" style={{ color: 'var(--text-primary)', borderBottomColor: 'var(--border-color)' }}>
                    <Home className="w-4 h-4 text-emerald-500" />
                    3. SERVICIOS Y CONSTRUCCIÓN
                  </h4>

                  {!selectedEncuesta.tiene_construccion ? (
                    <p className="italic py-8 text-center rounded-lg border" style={{ background: 'var(--bg-input)', borderColor: 'var(--border-color)', color: 'var(--text-secondary)' }}>
                      Sin construcción en el lote. No aplican servicios.
                    </p>
                  ) : (
                    <div className="space-y-3">
                      <div className="grid grid-cols-2 gap-2 text-center">
                        <div className={`p-2.5 rounded-lg border ${selectedEncuesta.agua_consumo ? 'bg-blue-500/10 border-blue-500/30 text-blue-600 dark:text-blue-300 font-semibold' : 'text-slate-500'}`} style={!selectedEncuesta.agua_consumo ? { background: 'var(--bg-input)', borderColor: 'var(--border-color)' } : undefined}>
                          <span className="block text-[9px] uppercase tracking-wider font-bold">Agua Potable</span>
                          <span className="font-bold text-xs">{selectedEncuesta.agua_consumo ? 'CON SERVICIO' : 'SIN SERVICIO'}</span>
                        </div>
                        <div className={`p-2.5 rounded-lg border ${selectedEncuesta.energia_electrica ? 'bg-amber-500/10 border-amber-500/30 text-amber-600 dark:text-amber-300 font-semibold' : 'text-slate-500'}`} style={!selectedEncuesta.energia_electrica ? { background: 'var(--bg-input)', borderColor: 'var(--border-color)' } : undefined}>
                          <span className="block text-[9px] uppercase tracking-wider font-bold">Luz Eléctrica</span>
                          <span className="font-bold text-xs">{selectedEncuesta.energia_electrica ? 'CON SERVICIO' : 'SIN SERVICIO'}</span>
                        </div>
                      </div>

                      <div className="p-2.5 rounded-lg border flex justify-between items-center shadow-sm" style={{ background: 'var(--bg-input)', borderColor: 'var(--border-color)' }}>
                        <div>
                          <span className="text-[9px] block" style={{ color: 'var(--text-secondary)' }}>Material predominante</span>
                          <span className="font-semibold uppercase text-xs" style={{ color: 'var(--text-primary)' }}>
                            {selectedEncuesta.material_construccion === 'Otros' 
                              ? `Otros (${selectedEncuesta.material_constr_otro})` 
                              : selectedEncuesta.material_construccion || 'Sin especificar'}
                          </span>
                        </div>
                        {selectedEncuesta.material_construccion && (
                          <button 
                            onClick={() => handleCopy(selectedEncuesta.material_construccion === 'Otros' ? selectedEncuesta.material_constr_otro || '' : selectedEncuesta.material_construccion, 'mat')}
                            className="p-1 rounded transition-colors cursor-pointer hover:bg-black/5 dark:hover:bg-white/10"
                            style={{ color: 'var(--text-secondary)' }}
                          >
                            {copySuccess['mat'] ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                          </button>
                        )}
                      </div>
                    </div>
                  )}
                </div>

              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 animate-scaleIn">
                {/* PESTAÑA 4: PRODUCCIÓN (CULTIVOS Y ANIMALES) */}
                <div className="rounded-xl p-4 space-y-4 border shadow-sm" style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
                  <h4 className="font-bold text-xs pb-1.5 flex items-center gap-1.5 border-b" style={{ color: 'var(--text-primary)', borderBottomColor: 'var(--border-color)' }}>
                    <Sprout className="w-4 h-4 text-amber-500" />
                    4. PRODUCCIÓN AGRÍCOLA Y PECUARIA
                  </h4>

                  {/* Cultivos list */}
                  <div className="space-y-2">
                    <span className="text-[10px] font-bold block" style={{ color: 'var(--text-secondary)' }}>🌾 Cultivos Reportados</span>
                    {!selectedEncuesta.cultivos || selectedEncuesta.cultivos.length === 0 ? (
                      <p className="text-[10px] italic p-2 rounded-lg text-center border" style={{ background: 'var(--bg-input)', borderColor: 'var(--border-color)', color: 'var(--text-muted)' }}>No reportó cultivos.</p>
                    ) : (
                      <div className="space-y-1.5">
                        {selectedEncuesta.cultivos.map((c, i) => (
                          <div key={i} className="flex justify-between items-center p-2 rounded-lg border shadow-sm" style={{ background: 'var(--bg-input)', borderColor: 'var(--border-color)' }}>
                            <div>
                              <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>
                                {c.tipo_cultivo === 'Otros' ? `Otros (${c.tipo_cultivo_otro})` : c.tipo_cultivo}
                              </span>
                              {c.es_principal && <span className="ml-2 bg-emerald-500/20 text-emerald-600 dark:text-emerald-300 text-[8px] font-bold px-1.5 py-0.5 rounded-full uppercase">Principal</span>}
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="font-mono font-semibold" style={{ color: 'var(--text-primary)' }}>{c.superficie_m2} m²</span>
                              <button 
                                onClick={() => handleCopy(String(c.superficie_m2), `c_sup_${i}`)}
                                className="p-0.5 rounded transition-colors cursor-pointer hover:bg-black/5 dark:hover:bg-white/10"
                                style={{ color: 'var(--text-secondary)' }}
                                title="Copiar área del cultivo"
                              >
                                {copySuccess[`c_sup_${i}`] ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Animales list */}
                  <div className="space-y-2">
                    <span className="text-[10px] font-bold block" style={{ color: 'var(--text-secondary)' }}>🐄 Animales / Especies</span>
                    {!selectedEncuesta.animales || selectedEncuesta.animales.length === 0 ? (
                      <p className="text-[10px] italic p-2 rounded-lg text-center border" style={{ background: 'var(--bg-input)', borderColor: 'var(--border-color)', color: 'var(--text-muted)' }}>No reportó animales.</p>
                    ) : (
                      <div className="space-y-1.5">
                        {selectedEncuesta.animales.map((a, i) => (
                          <div key={i} className="flex justify-between items-center p-2 rounded-lg border shadow-sm" style={{ background: 'var(--bg-input)', borderColor: 'var(--border-color)' }}>
                            <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>
                              {a.especie === 'Otros' ? `Otros (${a.especie_otro})` : a.especie}
                            </span>
                            <div className="flex items-center gap-2">
                              <span className="font-mono font-bold px-2 py-0.5 rounded border shadow-sm" style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}>{a.cantidad} cabezas</span>
                              <button 
                                onClick={() => handleCopy(String(a.cantidad), `a_cant_${i}`)}
                                className="p-0.5 rounded transition-colors cursor-pointer hover:bg-black/5 dark:hover:bg-white/10"
                                style={{ color: 'var(--text-secondary)' }}
                              >
                                {copySuccess[`a_cant_${i}`] ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Water usage */}
                  <div className="grid grid-cols-2 gap-2 p-2.5 rounded-lg border shadow-sm" style={{ background: 'var(--bg-input)', borderColor: 'var(--border-color)' }}>
                    <div>
                      <span className="text-[9px] block" style={{ color: 'var(--text-secondary)' }}>Consumo Familiar</span>
                      <span className="font-mono text-emerald-600 dark:text-emerald-400 font-bold text-xs">{selectedEncuesta.soberania_aliment_pct}%</span>
                    </div>
                    <div>
                      <span className="text-[9px] block" style={{ color: 'var(--text-secondary)' }}>Actividad Productiva</span>
                      <span className="font-semibold text-xs" style={{ color: 'var(--text-primary)' }}>{selectedEncuesta.actividad_productiva}</span>
                    </div>
                  </div>
                </div>

                {/* PESTAÑA 7: OTROS PREDIOS (OPCIONAL) */}
                <div className="rounded-xl p-4 space-y-3 border shadow-sm" style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
                  <h4 className="font-bold text-xs pb-1.5 flex items-center gap-1.5 border-b" style={{ color: 'var(--text-primary)', borderBottomColor: 'var(--border-color)' }}>
                    <MapPin className="w-4 h-4 text-blue-500" />
                    7. OTROS PREDIOS DEL REGANTE
                  </h4>

                  {!selectedEncuesta.predios_adicionales || selectedEncuesta.predios_adicionales.length === 0 ? (
                    <p className="italic py-12 text-center rounded-lg border" style={{ background: 'var(--bg-input)', borderColor: 'var(--border-color)', color: 'var(--text-secondary)' }}>
                      No reportó otros predios adicionales.
                    </p>
                  ) : (
                    <div className="space-y-2">
                      {selectedEncuesta.predios_adicionales.map((p, i) => (
                        <div key={i} className="p-2.5 rounded-lg border space-y-2 shadow-sm" style={{ background: 'var(--bg-input)', borderColor: 'var(--border-color)' }}>
                          <div className="flex justify-between items-center">
                            <div>
                              <span className="text-[9px] block" style={{ color: 'var(--text-secondary)' }}>Clave Catastral Adicional</span>
                              <span className="font-mono text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>{p.clave_catastral_otro}</span>
                            </div>
                            <button 
                              onClick={() => handleCopy(p.clave_catastral_otro, `pa_cc_${i}`)}
                              className="p-1 rounded transition-colors cursor-pointer hover:bg-black/5 dark:hover:bg-white/10"
                              style={{ color: 'var(--text-secondary)' }}
                            >
                              {copySuccess[`pa_cc_${i}`] ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                            </button>
                          </div>
                          <div className="flex justify-between items-center border-t pt-1.5" style={{ borderTopColor: 'var(--border-color)' }}>
                            <div>
                              <span className="text-[9px] block" style={{ color: 'var(--text-secondary)' }}>Área de Riego Adicional</span>
                              <span className="font-mono text-xs" style={{ color: 'var(--text-primary)' }}>{p.area_riego_otro} m²</span>
                            </div>
                            <button
                              onClick={() => handleCopy(String(p.area_riego_otro), `pa_area_${i}`)}
                              className="p-1 rounded transition-colors cursor-pointer hover:bg-black/5 dark:hover:bg-white/10"
                              style={{ color: 'var(--text-secondary)' }}
                            >
                              {copySuccess[`pa_area_${i}`] ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                            </button>
                          </div>
                          {/* v4.3: Producción declarada por el regante para este predio (Sección 4) */}
                          {(p.cultivos?.length || p.animales?.length) ? (
                            <div className="border-t pt-1.5 space-y-1" style={{ borderTopColor: 'var(--border-color)' }}>
                              <span className="text-[9px] block font-semibold text-emerald-500">🌱 Producción declarada (para Sección 4 de la ficha adicional)</span>
                              {p.cultivos?.map((c, ci) => (
                                <span key={`c${ci}`} className="text-[10px] block" style={{ color: 'var(--text-primary)' }}>
                                  🌾 {c.tipo_cultivo}{c.superficie_m2 ? ` — ${c.superficie_m2.toLocaleString('es-EC')} m²` : ''}
                                </span>
                              ))}
                              {p.animales?.map((a, ai) => (
                                <span key={`a${ai}`} className="text-[10px] block" style={{ color: 'var(--text-primary)' }}>
                                  🐄 {a.especie} — {a.cantidad}
                                </span>
                              ))}
                            </div>
                          ) : (
                            <div className="border-t pt-1.5" style={{ borderTopColor: 'var(--border-color)' }}>
                              <span className="text-[9px] italic" style={{ color: 'var(--text-secondary)' }}>Sin producción declarada — la ficha adicional quedará pendiente de investigación en campo</span>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Status and auditing log */}
              {selectedEncuesta.estado !== 'pendiente' && (
                <div className="border rounded-xl p-4 flex flex-col md:flex-row gap-4 items-start md:items-center justify-between" style={{ background: 'var(--bg-input)', borderColor: 'var(--border-color)' }}>
                  <div>
                    <span className="text-[10px] uppercase font-bold tracking-wider block" style={{ color: 'var(--text-secondary)' }}>Bitácora de Auditoría</span>
                    <p className="text-xs mt-1" style={{ color: 'var(--text-primary)' }}>
                      Encuesta marcada como <span className={selectedEncuesta.estado === 'procesada' ? 'text-emerald-600 dark:text-emerald-400 font-bold' : 'text-red-600 dark:text-red-400 font-bold'}>{selectedEncuesta.estado.toUpperCase()}</span> por <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{selectedEncuesta.procesado_por}</span> en <span style={{ color: 'var(--text-secondary)' }}>{selectedEncuesta.fecha_procesado ? new Date(selectedEncuesta.fecha_procesado).toLocaleString('es-EC') : 'sin fecha'}.</span>
                    </p>
                  </div>
                  {selectedEncuesta.observaciones && (
                    <div className="p-2.5 rounded-lg border flex-1 max-w-md w-full" style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
                      <span className="text-[9px] block" style={{ color: 'var(--text-secondary)' }}>Observaciones / Notas:</span>
                      <p className="text-xs mt-0.5 italic" style={{ color: 'var(--text-primary)' }}>"{selectedEncuesta.observaciones}"</p>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Modal Actions Panel */}
            <div className="p-5 border-t space-y-4" style={{ borderTopColor: 'var(--border-color)', background: 'var(--bg-card)' }}>
              {/* Observaciones input */}
              <div>
                <label className="block text-[10px] font-semibold mb-1" style={{ color: 'var(--text-secondary)' }}>Notas de Revisión / Observaciones para digitar en QField</label>
                <textarea 
                  value={observacionesInput}
                  onChange={(e) => setObservacionesInput(e.target.value)}
                  placeholder="Escriba comentarios, errores encontrados o indicaciones para el ingreso del polígono en QGIS..."
                  rows={2}
                  className="w-full rounded-lg px-3 py-2 text-xs focus:outline-none transition-colors resize-none border focus:border-blue-500"
                  style={{ background: 'var(--bg-input)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}
                />
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row justify-between gap-3">
                <button
                  onClick={() => {
                    setSelectedEncuesta(null);
                    setObservacionesInput('');
                  }}
                  className="px-4 py-2 border rounded-lg text-xs font-semibold transition-colors cursor-pointer hover:bg-black/5 dark:hover:bg-white/5"
                  style={{ borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}
                >
                  Cerrar Ventana
                </button>

                <div className="flex gap-2">
                  {/* Rechazar button */}
                  <button
                    onClick={() => handleUpdateStatus(selectedEncuesta.id, 'rechazada')}
                    disabled={savingAction}
                    className="px-4 py-2 bg-red-500/10 dark:bg-red-500/20 hover:bg-red-500/20 dark:hover:bg-red-500/30 border border-red-500/30 dark:border-red-500/40 text-red-600 dark:text-red-400 rounded-lg text-xs font-semibold transition-all inline-flex items-center gap-1 cursor-pointer disabled:opacity-50"
                  >
                    <XCircle className="w-4 h-4" />
                    Marcar como Rechazada
                  </button>

                  {/* Procesar button */}
                  <button
                    onClick={() => handleUpdateStatus(selectedEncuesta.id, 'procesada')}
                    disabled={savingAction}
                    className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold transition-all inline-flex items-center justify-center gap-1 cursor-pointer disabled:opacity-50 min-w-[150px]"
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
