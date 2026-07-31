import { useState, useEffect } from 'react';
import { submitEncuestaPublica } from '../../lib/firestoreService';
import { NIVELES_INSTRUCCION, TIPOS_CULTIVO, ESPECIES_ANIMALES, MATERIALES_CONSTRUCCION, PROJECT_SUBTITLE, LOGO_PICHINCHA, LOGO_CONSORCIO, PARROQUIAS, COMUNIDADES_POR_SECTOR_FILTRO, etiquetaComunidad } from '../../lib/constants';
import { 
  User, Home, Sprout, Map, 
  ArrowRight, ArrowLeft, Plus, Trash2, CheckCircle2, AlertCircle, Loader2
} from 'lucide-react';

export default function EncuestaPublicaPage() {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form State
  const [nombres, setNombres] = useState('');
  const [apellidos, setApellidos] = useState('');
  const [cedula, setCedula] = useState('');
  const [telefono, setTelefono] = useState('');
  const [comunidad, setComunidad] = useState('');
  const [parroquia, setParroquia] = useState('');
  const [sectorInv, setSectorInv] = useState('');
  const [areaRiego, setAreaRiego] = useState<number | ''>('');
  const [tieneReservorio, setTieneReservorio] = useState('No');
  const [metodoGravedad, setMetodoGravedad] = useState(0);
  const [metodoAspersion, setMetodoAspersion] = useState(0);
  const [metodoGoteo, setMetodoGoteo] = useState(0);
  const [hijosHombres, setHijosHombres] = useState(0);
  const [hijosMujeres, setHijosMujeres] = useState(0);
  const [tenencia, setTenencia] = useState('Escritura');
  const [nivelInstruccion, setNivelInstruccion] = useState('Ninguno');
  const [tieneConstruccion, setTieneConstruccion] = useState(false);
  const [claveCatastral, setClaveCatastral] = useState('');

  // Step 2 State (Mi Vivienda)
  const [aguaConsumo, setAguaConsumo] = useState(false);
  const [energiaElectrica, setEnergiaElectrica] = useState(false);
  const [materialConstruccion, setMaterialConstruccion] = useState('');
  const [materialOtro, setMaterialOtro] = useState('');

  // Step 3 State (Producción - Cultivos & Animales)
  const [cultivos, setCultivos] = useState<{ tipo_cultivo: string; tipo_cultivo_otro?: string; superficie_m2: number; es_principal: boolean }[]>([]);
  const [animales, setAnimales] = useState<{ especie: string; especie_otro?: string; cantidad: number }[]>([]);
  const [soberaniaPct, setSoberaniaPct] = useState(50);
  const [actividadProductiva, setActividadProductiva] = useState('Particular');

  // Step 4 State (Otros Predios)
  // v4.3: cada predio adicional puede llevar su propia producción (opcional) —
  // si el regante la llena, alimenta la ficha hija; si no, queda pendiente para campo.
  type PredioAdicionalEncuesta = {
    clave_catastral_otro: string;
    area_riego_otro: number;
    cultivos?: { tipo_cultivo: string; superficie_m2: number }[];
    animales?: { especie: string; cantidad: number }[];
  };
  const [tieneOtrosPredios, setTieneOtrosPredios] = useState(false);
  const [prediosAdicionales, setPrediosAdicionales] = useState<PredioAdicionalEncuesta[]>([]);

  // v4.3: validación de clave catastral contra el catastro oficial (carga diferida)
  // Nota: objeto plano (no Map) porque el ícono 'Map' de lucide-react opaca al Map nativo aquí
  const [clavesCatastro, setClavesCatastro] = useState<Record<string, number> | null>(null);
  const [cargandoCatastro, setCargandoCatastro] = useState(false);
  useEffect(() => {
    if (tieneOtrosPredios && !clavesCatastro && !cargandoCatastro) {
      setCargandoCatastro(true);
      fetch('/geo/catastro_busqueda.json')
        .then((r) => r.json())
        .then((data: { clave_cata: string; area_predi: number }[]) => {
          const m: Record<string, number> = {};
          for (const d of data) if (d.clave_cata) m[String(d.clave_cata).trim()] = d.area_predi || 0;
          setClavesCatastro(m);
        })
        .catch(() => setClavesCatastro(null)) // sin catálogo → no se bloquea la encuesta
        .finally(() => setCargandoCatastro(false));
    }
  }, [tieneOtrosPredios, clavesCatastro, cargandoCatastro]);

  // Producción temporal del predio adicional que se está agregando (opcional)
  const [tempPredioCultivos, setTempPredioCultivos] = useState<{ tipo_cultivo: string; superficie_m2: number }[]>([]);
  const [tempPredioAnimales, setTempPredioAnimales] = useState<{ especie: string; cantidad: number }[]>([]);
  const [tempPCultivo, setTempPCultivo] = useState('');
  const [tempPCultivoArea, setTempPCultivoArea] = useState('');
  const [tempPAnimal, setTempPAnimal] = useState('');
  const [tempPAnimalCant, setTempPAnimalCant] = useState('');

  // Temp item states for adding
  const [tempCultivo, setTempCultivo] = useState('');
  const [tempCultivoOtro, setTempCultivoOtro] = useState('');
  const [tempCultivoArea, setTempCultivoArea] = useState('');
  const [tempCultivoPrincipal, setTempCultivoPrincipal] = useState(false);

  const [tempAnimal, setTempAnimal] = useState('');
  const [tempAnimalOtro, setTempAnimalOtro] = useState('');
  const [tempAnimalCant, setTempAnimalCant] = useState('');

  const [tempPredioClave, setTempPredioClave] = useState('');
  const [tempPredioArea, setTempPredioArea] = useState('');

  // Functions to add/remove dynamic items
  const addCultivo = () => {
    if (!tempCultivo) return;
    const area = parseFloat(tempCultivoArea) || 0;
    if (area <= 0) {
      alert("Por favor ingrese una superficie válida mayor a 0 m²");
      return;
    }
    // Si este es principal, desmarcar los otros
    const updatedCultivos = tempCultivoPrincipal 
      ? cultivos.map(c => ({ ...c, es_principal: false }))
      : cultivos;

    setCultivos([...updatedCultivos, {
      tipo_cultivo: tempCultivo,
      tipo_cultivo_otro: tempCultivo === 'Otros' ? tempCultivoOtro : undefined,
      superficie_m2: area,
      es_principal: cultivos.length === 0 ? true : tempCultivoPrincipal
    }]);
    setTempCultivo('');
    setTempCultivoOtro('');
    setTempCultivoArea('');
    setTempCultivoPrincipal(false);
  };

  const removeCultivo = (index: number) => {
    const newCultivos = cultivos.filter((_, i) => i !== index);
    // Asegurar que al menos uno sea principal si queda alguno
    if (newCultivos.length > 0 && !newCultivos.some(c => c.es_principal)) {
      newCultivos[0].es_principal = true;
    }
    setCultivos(newCultivos);
  };

  const addAnimal = () => {
    if (!tempAnimal) return;
    const cant = parseInt(tempAnimalCant) || 0;
    if (cant <= 0) {
      alert("Por favor ingrese una cantidad mayor a 0");
      return;
    }
    setAnimales([...animales, {
      especie: tempAnimal,
      especie_otro: tempAnimal === 'Otros' ? tempAnimalOtro : undefined,
      cantidad: cant
    }]);
    setTempAnimal('');
    setTempAnimalOtro('');
    setTempAnimalCant('');
  };

  const removeAnimal = (index: number) => {
    setAnimales(animales.filter((_, i) => i !== index));
  };

  // v4.3: estado de validación de la clave que se está escribiendo
  const claveTrim = tempPredioClave.trim();
  const claveValidada: 'vacia' | 'valida' | 'invalida' | 'sin_catalogo' =
    !claveTrim ? 'vacia'
      : !clavesCatastro ? 'sin_catalogo'
      : claveTrim in clavesCatastro ? 'valida' : 'invalida';

  const addPredioAdicional = () => {
    if (!claveTrim) return;
    // Solo se bloquea si el catálogo cargó y la clave NO existe en el catastro
    if (claveValidada === 'invalida') return;
    const area = parseFloat(tempPredioArea) || 0;
    setPrediosAdicionales([...prediosAdicionales, {
      clave_catastral_otro: claveTrim,
      area_riego_otro: area,
      cultivos: tempPredioCultivos.length > 0 ? tempPredioCultivos : undefined,
      animales: tempPredioAnimales.length > 0 ? tempPredioAnimales : undefined,
    }]);
    setTempPredioClave('');
    setTempPredioArea('');
    setTempPredioCultivos([]);
    setTempPredioAnimales([]);
  };

  const removePredioAdicional = (index: number) => {
    setPrediosAdicionales(prediosAdicionales.filter((_, i) => i !== index));
  };

  // Step Validation & Navigation
  const validateStep1 = () => {
    if (!nombres.trim()) return 'Por favor escriba sus Nombres';
    if (!apellidos.trim()) return 'Por favor escriba sus Apellidos';
    if (!cedula.trim() || cedula.length !== 10) return 'La Cédula de Identidad debe tener 10 números';
    if (!sectorInv) return 'Por favor seleccione su Sector de Investigación';
    if (!comunidad) return 'Por favor seleccione su Comunidad';
    if (!parroquia) return 'Por favor seleccione su Parroquia';
    if (!telefono.trim() || telefono.length < 9) return 'Por favor ingrese un número de teléfono celular válido';
    
    // Validación de Riego y sus porcentajes
    const totalMetodos = (metodoGravedad || 0) + (metodoAspersion || 0) + (metodoGoteo || 0);
    const hasRiego = areaRiego !== '' && parseFloat(String(areaRiego)) > 0;
    if (hasRiego && totalMetodos !== 100) {
      return 'Los porcentajes de Métodos de Riego (Gravedad, Aspersión y Goteo) deben sumar exactamente 100% si ingresó un Área con Riego.';
    }
    if (!hasRiego && totalMetodos > 0) {
      return 'Si ingresó porcentajes de métodos de riego, debe ingresar un Área con Riego mayor a 0 m².';
    }
    return null;
  };

  const nextStep = () => {
    if (step === 1) {
      const err = validateStep1();
      if (err) {
        setError(err);
        return;
      }
    }
    setError(null);
    setStep(s => s + 1);
  };

  const prevStep = () => {
    setError(null);
    setStep(s => s - 1);
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = {
        nombres: nombres.trim().toUpperCase(),
        apellidos: apellidos.trim().toUpperCase(),
        cedula: cedula.trim(),
        telefono_celular: telefono.trim(),
        comunidad,
        parroquia,
        sector_investigacion: sectorInv,
        hijos_hombres: hijosHombres,
        hijos_mujeres: hijosMujeres,
        tenencia_predio: tenencia,
        nivel_instruccion: nivelInstruccion,
        tiene_construccion: tieneConstruccion,
        clave_catastral: claveCatastral.trim(),
        
        area_riego: areaRiego !== '' ? parseFloat(String(areaRiego)) : 0,
        tiene_reservorio: tieneReservorio,
        metodo_gravedad_pct: metodoGravedad || 0,
        metodo_aspersion_pct: metodoAspersion || 0,
        metodo_goteo_pct: metodoGoteo || 0,
        
        // Pestaña 3 (solo si tiene construcción)
        agua_consumo: tieneConstruccion ? aguaConsumo : false,
        energia_electrica: tieneConstruccion ? energiaElectrica : false,
        material_construccion: tieneConstruccion ? materialConstruccion : '',
        material_constr_otro: tieneConstruccion && materialConstruccion === 'Otros' ? materialOtro.trim().toUpperCase() : '',
        
        // Pestaña 4
        cultivos,
        animales,
        soberania_aliment_pct: soberaniaPct,
        act_productivas_pct: 100 - soberaniaPct,
        actividad_productiva: actividadProductiva,
        
        // Pestaña 7
        predios_adicionales: tieneOtrosPredios ? prediosAdicionales : []
      };

      await submitEncuestaPublica(payload);
      setSubmitted(true);
    } catch (err: any) {
      console.error(err);
      setError("Ocurrió un error al enviar la encuesta. Por favor intente de nuevo.");
    } finally {
      setLoading(false);
    }
  };

  // Header progress visual indicators
  const stepsConfig = [
    { num: 1, label: 'Mis Datos', icon: User },
    { num: 2, label: 'Mi Vivienda', icon: Home },
    { num: 3, label: 'Producción', icon: Sprout },
    { num: 4, label: 'Otros Lotes', icon: Map },
  ];

  if (submitted) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900 p-4 font-sans text-slate-100">
        <div className="max-w-md w-full bg-slate-800/80 backdrop-blur-md rounded-2xl p-8 border border-emerald-500/30 text-center shadow-xl">
          <CheckCircle2 className="w-16 h-16 text-emerald-400 mx-auto mb-4 animate-bounce" />
          <h2 className="text-2xl font-bold text-white mb-2">¡Muchas Gracias!</h2>
          <p className="text-slate-300 text-sm mb-6 leading-relaxed">
            Tu información ha sido registrada con éxito. Un técnico revisará tus respuestas para asociarlas a la clave catastral en el mapa de la junta de riego.
          </p>
          <button 
            onClick={() => {
              setStep(1);
              setNombres('');
              setApellidos('');
              setCedula('');
              setTelefono('');
              setComunidad('');
              setParroquia('');
              setSectorInv('');
              setAreaRiego('');
              setTieneReservorio('No');
              setMetodoGravedad(0);
              setMetodoAspersion(0);
              setMetodoGoteo(0);
              setHijosHombres(0);
              setHijosMujeres(0);
              setTenencia('Escritura');
              setNivelInstruccion('Ninguno');
              setTieneConstruccion(false);
              setClaveCatastral('');
              setAguaConsumo(false);
              setEnergiaElectrica(false);
              setMaterialConstruccion('');
              setMaterialOtro('');
              setCultivos([]);
              setAnimales([]);
              setSoberaniaPct(50);
              setTieneOtrosPredios(false);
              setPrediosAdicionales([]);
              setSubmitted(false);
            }}
            className="w-full bg-emerald-500 hover:bg-emerald-600 text-white py-3 px-4 rounded-xl font-bold transition-all shadow-lg shadow-emerald-500/20"
          >
            Llenar otra encuesta
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col font-sans text-slate-100">
      {/* Header bar */}
      <header className="bg-slate-900/60 border-b border-slate-800 backdrop-blur-md py-3 px-4 lg:px-8">
        <div className="max-w-4xl mx-auto flex items-center justify-between gap-4">
          <img src={LOGO_PICHINCHA} alt="Pichincha" className="h-10 w-auto object-contain" />
          <div className="text-center min-w-0">
            <h1 className="text-xs font-bold text-amber-500 tracking-wider truncate uppercase">
              Encuesta de Regantes
            </h1>
            <p className="text-[10px] text-slate-400 truncate">{PROJECT_SUBTITLE}</p>
          </div>
          <img src={LOGO_CONSORCIO} alt="Cayambe SPT" className="h-10 w-auto object-contain" />
        </div>
      </header>

      {/* Main wizard body */}
      <main className="flex-1 max-w-2xl w-full mx-auto p-4 md:py-8 flex flex-col justify-start">
        {/* Stepper bar */}
        <div className="mb-6 flex justify-between items-center relative">
          <div className="absolute left-0 right-0 h-0.5 bg-slate-800 top-1/2 -translate-y-1/2 z-0" />
          {stepsConfig.map((s) => {
            const isCompleted = step > s.num;
            const isActive = step === s.num;
            return (
              <div key={s.num} className="flex flex-col items-center z-10">
                <div 
                  className={`w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold transition-all border ${
                    isCompleted 
                      ? 'bg-emerald-500 text-white border-emerald-400' 
                      : isActive 
                        ? 'bg-blue-600 text-white border-blue-400 ring-4 ring-blue-500/20' 
                        : 'bg-slate-900 text-slate-400 border-slate-700'
                  }`}
                >
                  {isCompleted ? '✓' : s.num}
                </div>
                <span className={`text-[10px] mt-1 font-medium hidden sm:inline ${isActive ? 'text-blue-400 font-bold' : 'text-slate-400'}`}>
                  {s.label}
                </span>
              </div>
            );
          })}
        </div>

        {/* Error notification */}
        {error && (
          <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/30 flex items-center gap-3 text-red-300 text-xs">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Form panel container */}
        <div className="bg-slate-900/60 border border-slate-800 backdrop-blur-md rounded-2xl p-6 shadow-xl flex-1 flex flex-col justify-between">
          <div className="space-y-6">
            
            {/* 👤 STEP 1: PERSONAL INFORMATION */}
            {step === 1 && (
              <div className="space-y-4">
                <div className="border-b border-slate-800 pb-3">
                  <h3 className="text-md font-bold text-white flex items-center gap-2">
                    <User className="w-5 h-5 text-blue-400" />
                    Paso 1: Mis Datos Personales
                  </h3>
                  <p className="text-[11px] text-slate-400 mt-1">Escriba su información básica de identificación.</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[11px] text-slate-400 font-medium mb-1">Cédula de Identidad (10 números) *</label>
                    <input 
                      type="text" 
                      maxLength={10}
                      value={cedula}
                      onChange={(e) => setCedula(e.target.value.replace(/\D/g, ''))}
                      placeholder="Ej: 1709999999"
                      className="w-full bg-slate-950 border border-slate-800 focus:border-blue-500 rounded-xl px-3 py-2 text-sm focus:outline-none transition-colors"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] text-slate-400 font-medium mb-1">Clave Catastral (Impuesto Predial - Opcional)</label>
                    <input 
                      type="text" 
                      value={claveCatastral}
                      onChange={(e) => setClaveCatastral(e.target.value)}
                      placeholder="Ej: 1702521010087"
                      className="w-full bg-slate-950 border border-slate-800 focus:border-blue-500 rounded-xl px-3 py-2 text-sm focus:outline-none transition-colors"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[11px] text-slate-400 font-medium mb-1">Apellidos Completos *</label>
                    <input 
                      type="text" 
                      value={apellidos}
                      onChange={(e) => setApellidos(e.target.value)}
                      placeholder="Escriba sus apellidos"
                      className="w-full bg-slate-950 border border-slate-800 focus:border-blue-500 rounded-xl px-3 py-2 text-sm focus:outline-none transition-colors"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] text-slate-400 font-medium mb-1">Nombres Completos *</label>
                    <input 
                      type="text" 
                      value={nombres}
                      onChange={(e) => setNombres(e.target.value)}
                      placeholder="Escriba sus nombres"
                      className="w-full bg-slate-950 border border-slate-800 focus:border-blue-500 rounded-xl px-3 py-2 text-sm focus:outline-none transition-colors"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] text-slate-400 font-medium mb-1.5">Sector de Investigación *</label>
                  <div className="grid grid-cols-3 gap-2">
                    {['Sector 1', 'Sector 2', 'Sector 3'].map((sec) => (
                      <button
                        key={sec}
                        type="button"
                        onClick={() => {
                          setSectorInv(sec);
                          setComunidad(''); // Limpiar comunidad al cambiar de sector
                        }}
                        className={`py-2.5 rounded-xl text-xs font-bold border transition-all cursor-pointer ${
                          sectorInv === sec 
                            ? 'bg-blue-600/20 text-blue-300 border-blue-500 shadow-md ring-2 ring-blue-500/20' 
                            : 'bg-slate-950 text-slate-400 border-slate-800 hover:bg-slate-900'
                        }`}
                      >
                        {sec}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[11px] text-slate-400 font-medium mb-1">Comunidad a la que pertenece *</label>
                    <select 
                      value={comunidad}
                      onChange={(e) => setComunidad(e.target.value)}
                      disabled={!sectorInv}
                      className="w-full bg-slate-950 border border-slate-800 focus:border-blue-500 rounded-xl px-3 py-2 text-sm focus:outline-none transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <option value="">{sectorInv ? 'Seleccione su comunidad' : 'Seleccione primero su sector'}</option>
                      {sectorInv && (COMUNIDADES_POR_SECTOR_FILTRO[sectorInv] || []).map(c => <option key={c} value={c}>{etiquetaComunidad(c)}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-[11px] text-slate-400 font-medium mb-1">Parroquia *</label>
                    <select 
                      value={parroquia}
                      onChange={(e) => setParroquia(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 focus:border-blue-500 rounded-xl px-3 py-2 text-sm focus:outline-none transition-colors cursor-pointer"
                    >
                      <option value="">Seleccione su parroquia</option>
                      {PARROQUIAS.map(p => <option key={p} value={p}>{p}</option>)}
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] text-slate-400 font-medium mb-1">Teléfono Celular *</label>
                  <input 
                    type="text" 
                    value={telefono}
                    onChange={(e) => setTelefono(e.target.value.replace(/\D/g, ''))}
                    placeholder="Ej: 0991234567"
                    className="w-full bg-slate-950 border border-slate-800 focus:border-blue-500 rounded-xl px-3 py-2 text-sm focus:outline-none transition-colors"
                  />
                </div>

                <div className="border-t border-slate-800/60 pt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[11px] text-slate-400 font-medium mb-1">¿Tiene Escrituras o Título del Terreno?</label>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {['Escritura', 'Sin Escritura'].map((opt) => (
                        <button
                          key={opt}
                          type="button"
                          onClick={() => setTenencia(opt)}
                          className={`py-2 rounded-xl text-xs font-semibold border transition-all cursor-pointer ${
                            tenencia === opt 
                              ? 'bg-blue-600/20 text-blue-300 border-blue-500' 
                              : 'bg-slate-950 text-slate-400 border-slate-800 hover:bg-slate-900'
                          }`}
                        >
                          {opt === 'Escritura' ? 'SÍ (Tengo Escrituras)' : 'NO (Sin Escrituras)'}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="block text-[11px] text-slate-400 font-medium mb-1">Área con Riego (m²)</label>
                    <input 
                      type="number" 
                      min={0}
                      value={areaRiego}
                      onChange={(e) => {
                        const val = e.target.value === '' ? '' : parseFloat(e.target.value);
                        setAreaRiego(val);
                        if (val === '' || val <= 0) {
                          setMetodoGravedad(0);
                          setMetodoAspersion(0);
                          setMetodoGoteo(0);
                        }
                      }}
                      placeholder="Ej: 1500"
                      className="w-full bg-slate-950 border border-slate-800 focus:border-blue-500 rounded-xl px-3 py-2 text-sm focus:outline-none transition-colors"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[11px] text-slate-400 font-medium mb-1">¿Tiene Reservorio?</label>
                    <div className="grid grid-cols-3 gap-2">
                      {['No', 'Privado', 'Comunitario'].map((opt) => (
                        <button
                          key={opt}
                          type="button"
                          onClick={() => setTieneReservorio(opt)}
                          className={`py-2 rounded-xl text-xs font-semibold border transition-all cursor-pointer ${
                            tieneReservorio === opt 
                              ? 'bg-blue-600/20 text-blue-300 border-blue-500' 
                              : 'bg-slate-950 text-slate-400 border-slate-800 hover:bg-slate-900'
                          }`}
                        >
                          {opt === 'No' ? 'NO' : opt === 'Privado' ? 'Privado' : 'Comunidad'}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="block text-[11px] text-slate-400 font-medium mb-1">Nivel de Instrucción Escolar</label>
                    <select 
                      value={nivelInstruccion}
                      onChange={(e) => setNivelInstruccion(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 focus:border-blue-500 rounded-xl px-3 py-2 text-sm focus:outline-none transition-colors cursor-pointer"
                    >
                      {NIVELES_INSTRUCCION.map(lvl => <option key={lvl} value={lvl}>{lvl}</option>)}
                    </select>
                  </div>
                </div>

                {areaRiego !== '' && parseFloat(String(areaRiego)) > 0 && (
                  <div className="border-t border-slate-800/60 pt-4 animate-fadeIn">
                    <label className="block text-[11px] text-slate-400 font-medium mb-2">Método de Riego (%) — Debe sumar 100%</label>
                    <div className="grid grid-cols-3 gap-3">
                      <div>
                        <span className="text-[10px] text-slate-500 block mb-1">Gravedad %</span>
                        <input 
                          type="number" 
                          min={0}
                          max={100}
                          value={metodoGravedad}
                          onChange={(e) => setMetodoGravedad(Math.min(100, Math.max(0, parseInt(e.target.value) || 0)))}
                          className="w-full bg-slate-950 border border-slate-800 focus:border-blue-500 rounded-xl px-3 py-1.5 text-xs text-center focus:outline-none transition-colors"
                        />
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-500 block mb-1">Aspersión %</span>
                        <input 
                          type="number" 
                          min={0}
                          max={100}
                          value={metodoAspersion}
                          onChange={(e) => setMetodoAspersion(Math.min(100, Math.max(0, parseInt(e.target.value) || 0)))}
                          className="w-full bg-slate-950 border border-slate-800 focus:border-blue-500 rounded-xl px-3 py-1.5 text-xs text-center focus:outline-none transition-colors"
                        />
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-500 block mb-1">Goteo %</span>
                        <input 
                          type="number" 
                          min={0}
                          max={100}
                          value={metodoGoteo}
                          onChange={(e) => setMetodoGoteo(Math.min(100, Math.max(0, parseInt(e.target.value) || 0)))}
                          className="w-full bg-slate-950 border border-slate-800 focus:border-blue-500 rounded-xl px-3 py-1.5 text-xs text-center focus:outline-none transition-colors"
                        />
                      </div>
                    </div>
                  </div>
                )}

                <div className="border-t border-slate-800/60 pt-4 space-y-5">
                  <div>
                    <label className="block text-[11px] text-slate-400 font-medium mb-1.5">Hijos que viven con usted</label>
                    <div className="flex flex-col sm:flex-row gap-3">
                      <div className="flex-1 flex items-center justify-between bg-slate-950 border border-slate-800 rounded-xl p-2 px-3.5">
                        <span className="text-xs text-slate-400">Hijos Varones</span>
                        <div className="flex items-center gap-2">
                          <button type="button" onClick={() => setHijosHombres(Math.max(0, hijosHombres - 1))} className="w-7 h-7 bg-slate-800 hover:bg-slate-700 rounded-full flex items-center justify-center font-bold text-slate-200 cursor-pointer select-none">-</button>
                          <span className="text-xs font-bold w-5 text-center">{hijosHombres}</span>
                          <button type="button" onClick={() => setHijosHombres(hijosHombres + 1)} className="w-7 h-7 bg-slate-800 hover:bg-slate-700 rounded-full flex items-center justify-center font-bold text-slate-200 cursor-pointer select-none">+</button>
                        </div>
                      </div>
                      <div className="flex-1 flex items-center justify-between bg-slate-950 border border-slate-800 rounded-xl p-2 px-3.5">
                        <span className="text-xs text-slate-400">Hijas Mujeres</span>
                        <div className="flex items-center gap-2">
                          <button type="button" onClick={() => setHijosMujeres(Math.max(0, hijosMujeres - 1))} className="w-7 h-7 bg-slate-800 hover:bg-slate-700 rounded-full flex items-center justify-center font-bold text-slate-200 cursor-pointer select-none">-</button>
                          <span className="text-xs font-bold w-5 text-center">{hijosMujeres}</span>
                          <button type="button" onClick={() => setHijosMujeres(hijosMujeres + 1)} className="w-7 h-7 bg-slate-800 hover:bg-slate-700 rounded-full flex items-center justify-center font-bold text-slate-200 cursor-pointer select-none">+</button>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div>
                    <label className="block text-[11px] text-slate-400 font-medium mb-2">¿Tiene alguna casa o construcción en su terreno?</label>
                    <div className="flex flex-col sm:flex-row gap-2">
                      <button
                        type="button"
                        onClick={() => setTieneConstruccion(true)}
                        className={`flex-1 py-2.5 rounded-xl text-xs font-semibold border transition-all cursor-pointer ${
                          tieneConstruccion 
                            ? 'bg-blue-600/20 text-blue-300 border-blue-500' 
                            : 'bg-slate-950 text-slate-400 border-slate-800 hover:bg-slate-900'
                        }`}
                      >
                        Sí, hay una casa
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setTieneConstruccion(false);
                          setAguaConsumo(false);
                          setEnergiaElectrica(false);
                          setMaterialConstruccion('');
                          setMaterialOtro('');
                        }}
                        className={`flex-1 py-2.5 rounded-xl text-xs font-semibold border transition-all cursor-pointer ${
                          !tieneConstruccion 
                            ? 'bg-blue-600/20 text-blue-300 border-blue-500' 
                            : 'bg-slate-950 text-slate-400 border-slate-800 hover:bg-slate-900'
                        }`}
                      >
                        No hay ninguna casa
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* 🏠 STEP 2: HOUSE SERVICES (Only editable if has construction) */}
            {step === 2 && (
              <div className="space-y-4">
                <div className="border-b border-slate-800 pb-3">
                  <h3 className="text-md font-bold text-white flex items-center gap-2">
                    <Home className="w-5 h-5 text-blue-400" />
                    Paso 2: Mi Casa y Servicios Básicos
                  </h3>
                  <p className="text-[11px] text-slate-400 mt-1">Indique los servicios y material de su vivienda principal.</p>
                </div>

                {!tieneConstruccion ? (
                  <div className="text-center py-12 px-4 bg-slate-950/40 rounded-xl border border-dashed border-slate-800">
                    <p className="text-slate-400 text-xs">
                      En el paso anterior indicaste que **No tienes una construcción o vivienda** en el terreno.
                    </p>
                    <p className="text-[11px] text-slate-500 mt-2">
                      Puedes hacer clic en "Siguiente" para continuar, o "Atrás" si deseas modificarlo.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
                        <div>
                          <p className="text-xs font-semibold text-white">Agua de Consumo Humano</p>
                          <p className="text-[10px] text-slate-500">¿Tiene agua potable en la vivienda?</p>
                        </div>
                        <input
                          type="checkbox"
                          checked={aguaConsumo}
                          onChange={(e) => setAguaConsumo(e.target.checked)}
                          className="w-5 h-5 rounded border-slate-800 text-blue-600 focus:ring-0 cursor-pointer"
                        />
                      </div>
                      <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
                        <div>
                          <p className="text-xs font-semibold text-white">Energía Eléctrica</p>
                          <p className="text-[10px] text-slate-500">¿Tiene medidor de luz eléctrica?</p>
                        </div>
                        <input
                          type="checkbox"
                          checked={energiaElectrica}
                          onChange={(e) => setEnergiaElectrica(e.target.checked)}
                          className="w-5 h-5 rounded border-slate-800 text-blue-600 focus:ring-0 cursor-pointer"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-[11px] text-slate-400 font-medium mb-1">Material predominante de la casa</label>
                      <select 
                        value={materialConstruccion}
                        onChange={(e) => setMaterialConstruccion(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 focus:border-blue-500 rounded-xl px-3 py-2 text-sm focus:outline-none transition-colors cursor-pointer"
                      >
                        <option value="">Seleccione un material</option>
                        {MATERIALES_CONSTRUCCION.map(m => m ? <option key={m} value={m}>{m}</option> : null)}
                      </select>
                    </div>

                    {materialConstruccion === 'Otros' && (
                      <div className="animate-fadeIn">
                        <label className="block text-[11px] text-slate-400 font-medium mb-1">Especifique el material</label>
                        <input 
                          type="text" 
                          value={materialOtro}
                          onChange={(e) => setMaterialOtro(e.target.value)}
                          placeholder="¿De qué material es su casa?"
                          className="w-full bg-slate-950 border border-slate-800 focus:border-blue-500 rounded-xl px-3 py-2 text-sm focus:outline-none transition-colors"
                        />
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* 🌾 STEP 3: PRODUCTION (CULTIVOS, ANIMALES, SOBERANIA) */}
            {step === 3 && (
              <div className="space-y-6">
                <div className="border-b border-slate-800 pb-3">
                  <h3 className="text-md font-bold text-white flex items-center gap-2">
                    <Sprout className="w-5 h-5 text-blue-400" />
                    Paso 3: Mis Cultivos y Crianza de Animales
                  </h3>
                  <p className="text-[11px] text-slate-400 mt-1">Llene los cultivos principales y animales que produce en su lote.</p>
                </div>

                {/* Cultivos Section */}
                <div className="bg-slate-950/40 border border-slate-800 rounded-2xl p-4 space-y-4">
                  <p className="text-xs font-bold text-white border-b border-slate-800/80 pb-2">🌾 Mis Cultivos</p>
                  
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[10px] text-slate-400 mb-0.5">Tipo de Cultivo</label>
                      <select 
                        value={tempCultivo}
                        onChange={(e) => setTempCultivo(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-850 rounded-lg px-2.5 py-1.5 text-xs focus:outline-none cursor-pointer"
                      >
                        <option value="">Seleccione cultivo</option>
                        {TIPOS_CULTIVO.map(tc => <option key={tc} value={tc}>{tc}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="block text-[10px] text-slate-400 mb-0.5">Superficie sembrada (m²)</label>
                      <input 
                        type="number"
                        value={tempCultivoArea}
                        onChange={(e) => setTempCultivoArea(e.target.value)}
                        placeholder="Ej: 500"
                        className="w-full bg-slate-950 border border-slate-850 rounded-lg px-2.5 py-1.5 text-xs focus:outline-none"
                      />
                    </div>
                  </div>

                  <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 pt-1">
                    <label className="flex items-center gap-1.5 text-[10px] text-slate-400 cursor-pointer select-none">
                      <input
                        type="checkbox"
                        checked={tempCultivoPrincipal}
                        onChange={(e) => setTempCultivoPrincipal(e.target.checked)}
                        className="w-4 h-4 rounded text-blue-600 focus:ring-0"
                      />
                      <span>¿Es el principal?</span>
                    </label>
                    <button 
                      type="button" 
                      onClick={addCultivo}
                      className="w-full sm:w-auto bg-blue-600 hover:bg-blue-700 text-white font-bold py-1.5 px-3 rounded-lg text-xs transition-colors flex items-center justify-center gap-1 cursor-pointer whitespace-nowrap"
                    >
                      <Plus className="w-3.5 h-3.5" /> Agregar cultivo
                    </button>
                  </div>

                  {tempCultivo === 'Otros' && (
                    <div className="animate-fadeIn">
                      <label className="block text-[10px] text-slate-400 mb-0.5">Especifique el cultivo</label>
                      <input 
                        type="text"
                        value={tempCultivoOtro}
                        onChange={(e) => setTempCultivoOtro(e.target.value)}
                        placeholder="Nombre del cultivo"
                        className="w-full bg-slate-950 border border-slate-850 rounded-lg px-2.5 py-1.5 text-xs focus:outline-none"
                      />
                    </div>
                  )}

                  {/* List of added crops */}
                  {cultivos.length === 0 ? (
                    <p className="text-[11px] text-slate-500 italic text-center py-2">No ha agregado cultivos aún.</p>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs text-left">
                        <thead>
                          <tr className="border-b border-slate-850 text-slate-400 text-[10px]">
                            <th className="py-2">Cultivo</th>
                            <th className="py-2">Superficie</th>
                            <th className="py-2">Principal</th>
                            <th className="py-2 text-right">Acción</th>
                          </tr>
                        </thead>
                        <tbody>
                          {cultivos.map((c, idx) => (
                            <tr key={idx} className="border-b border-slate-900/60 hover:bg-slate-900/20">
                              <td className="py-2 font-medium">
                                {c.tipo_cultivo === 'Otros' ? `Otros (${c.tipo_cultivo_otro})` : c.tipo_cultivo}
                              </td>
                              <td className="py-2">{c.superficie_m2} m²</td>
                              <td className="py-2">
                                {c.es_principal ? (
                                  <span className="bg-emerald-500/20 text-emerald-300 text-[9px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider">Sí</span>
                                ) : (
                                  <span className="text-slate-500 text-[10px]">No</span>
                                )}
                              </td>
                              <td className="py-2 text-right">
                                <button type="button" onClick={() => removeCultivo(idx)} className="text-red-400 hover:text-red-300 cursor-pointer">
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

                {/* Animales Section */}
                <div className="bg-slate-950/40 border border-slate-800 rounded-2xl p-4 space-y-4">
                  <p className="text-xs font-bold text-white border-b border-slate-800/80 pb-2">🐄 Mis Animales (Crianza)</p>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[10px] text-slate-400 mb-0.5">Especie</label>
                      <select 
                        value={tempAnimal}
                        onChange={(e) => setTempAnimal(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-850 rounded-lg px-2.5 py-1.5 text-xs focus:outline-none cursor-pointer"
                      >
                        <option value="">Seleccione especie</option>
                        {ESPECIES_ANIMALES.map(ea => <option key={ea} value={ea}>{ea}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="block text-[10px] text-slate-400 mb-0.5">Cantidad</label>
                      <input 
                        type="number"
                        value={tempAnimalCant}
                        onChange={(e) => setTempAnimalCant(e.target.value)}
                        placeholder="Ej: 15"
                        className="w-full bg-slate-950 border border-slate-850 rounded-lg px-2.5 py-1.5 text-xs focus:outline-none"
                      />
                    </div>
                  </div>

                  <div className="flex justify-end pt-1">
                    <button 
                      type="button" 
                      onClick={addAnimal}
                      className="w-full sm:w-auto bg-blue-600 hover:bg-blue-700 text-white font-bold py-1.5 px-3 rounded-lg text-xs transition-colors flex items-center justify-center gap-1 cursor-pointer whitespace-nowrap"
                    >
                      <Plus className="w-3.5 h-3.5" /> Agregar animal
                    </button>
                  </div>

                  {tempAnimal === 'Otros' && (
                    <div className="animate-fadeIn">
                      <label className="block text-[10px] text-slate-400 mb-0.5">Especifique especie</label>
                      <input 
                        type="text"
                        value={tempAnimalOtro}
                        onChange={(e) => setTempAnimalOtro(e.target.value)}
                        placeholder="Especie de animal"
                        className="w-full bg-slate-950 border border-slate-850 rounded-lg px-2.5 py-1.5 text-xs focus:outline-none"
                      />
                    </div>
                  )}

                  {/* List of added animals */}
                  {animales.length === 0 ? (
                    <p className="text-[11px] text-slate-500 italic text-center py-2">No ha agregado animales aún.</p>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs text-left">
                        <thead>
                          <tr className="border-b border-slate-850 text-slate-400 text-[10px]">
                            <th className="py-2">Especie</th>
                            <th className="py-2">Cantidad</th>
                            <th className="py-2 text-right">Acción</th>
                          </tr>
                        </thead>
                        <tbody>
                          {animales.map((a, idx) => (
                            <tr key={idx} className="border-b border-slate-900/60 hover:bg-slate-900/20">
                              <td className="py-2 font-medium">
                                {a.especie === 'Otros' ? `Otros (${a.especie_otro})` : a.especie}
                              </td>
                              <td className="py-2">{a.cantidad}</td>
                              <td className="py-2 text-right">
                                <button type="button" onClick={() => removeAnimal(idx)} className="text-red-400 hover:text-red-300 cursor-pointer">
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

                {/* Simplificación del uso del agua y destino de la producción */}
                <div className="bg-slate-950/40 border border-slate-800 rounded-2xl p-5 space-y-4">
                  <div>
                    <p className="text-xs font-bold text-white border-b border-slate-800/80 pb-2 flex items-center gap-1.5">
                      <span>💧</span> ¿Qué hace principalmente con lo que siembra o produce?
                    </p>
                    <p className="text-[10px] text-slate-500 mt-1 leading-normal">
                      Seleccione la opción que mejor describa el uso de sus cultivos y animales en su lote.
                    </p>
                  </div>

                  <div className="space-y-2.5 pt-1">
                    {[
                      {
                        id: 'consumo',
                        label: 'Todo es para comer en casa (Autoconsumo)',
                        desc: 'Toda nuestra producción sirve para alimentar a mi familia.',
                        icon: '🏠',
                        sobVal: 100,
                        actVal: 'Particular'
                      },
                      {
                        id: 'mixto',
                        label: 'Una parte para comer y otra parte para vender',
                        desc: 'Consumimos en el hogar y vendemos los excedentes en ferias locales.',
                        icon: '⚖️',
                        sobVal: 50,
                        actVal: 'Particular'
                      },
                      {
                        id: 'comercial',
                        label: 'La gran mayoría es para la venta comercial',
                        desc: 'Producimos principalmente para vender a mercados, ferias grandes o empresas.',
                        icon: '💰',
                        sobVal: 10,
                        actVal: 'Empresarial'
                      }
                    ].map((opt) => {
                      // Determinamos si está seleccionada esta opción
                      const isSelected = 
                        opt.id === 'consumo' ? soberaniaPct === 100 :
                        opt.id === 'mixto' ? soberaniaPct === 50 :
                        opt.id === 'comercial' ? soberaniaPct === 10 : false;
                      
                      return (
                        <button
                          key={opt.id}
                          type="button"
                          onClick={() => {
                            setSoberaniaPct(opt.sobVal);
                            setActividadProductiva(opt.actVal);
                          }}
                          className={`w-full p-3.5 rounded-xl border text-left transition-all flex items-start gap-3.5 cursor-pointer ${
                            isSelected
                              ? 'bg-blue-600/10 border-blue-500 ring-2 ring-blue-500/20'
                              : 'bg-slate-950 text-slate-400 border-slate-800 hover:bg-slate-900/60 hover:text-slate-200'
                          }`}
                        >
                          <span className="text-2xl pt-0.5 select-none">{opt.icon}</span>
                          <div className="min-w-0 flex-1">
                            <p className={`text-xs font-bold ${isSelected ? 'text-blue-300' : 'text-slate-300'}`}>
                              {opt.label}
                            </p>
                            <p className="text-[10px] text-slate-500 mt-0.5 leading-normal">
                              {opt.desc}
                            </p>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}

            {/* 🗺️ STEP 4: OTHER PLOTS (OPTIONAL) */}
            {step === 4 && (
              <div className="space-y-4">
                <div className="border-b border-slate-800 pb-3">
                  <h3 className="text-md font-bold text-white flex items-center gap-2">
                    <Map className="w-5 h-5 text-blue-400" />
                    Paso 4: Otros Terrenos o Predios Adicionales
                  </h3>
                  <p className="text-[11px] text-slate-400 mt-1">¿Tiene otros terrenos bajo su nombre en esta junta de riego?</p>
                </div>

                <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold text-white">¿Tiene predios o terrenos adicionales?</p>
                    <p className="text-[10px] text-slate-500">Registre otros terrenos que le pertenecen.</p>
                  </div>
                  <div className="flex gap-2 w-full sm:w-auto">
                    <button
                      type="button"
                      onClick={() => setTieneOtrosPredios(true)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all cursor-pointer ${
                        tieneOtrosPredios 
                          ? 'bg-blue-600/20 text-blue-300 border-blue-500' 
                          : 'bg-slate-900 text-slate-400 border-slate-800 hover:bg-slate-950'
                      }`}
                    >
                      Sí tengo
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setTieneOtrosPredios(false);
                        setPrediosAdicionales([]);
                      }}
                      className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all cursor-pointer ${
                        !tieneOtrosPredios 
                          ? 'bg-blue-600/20 text-blue-300 border-blue-500' 
                          : 'bg-slate-900 text-slate-400 border-slate-800 hover:bg-slate-950'
                      }`}
                    >
                      No tengo
                    </button>
                  </div>
                </div>

                {tieneOtrosPredios && (
                  <div className="bg-slate-950/40 border border-slate-800 rounded-2xl p-4 space-y-4 animate-fadeIn">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label className="block text-[10px] text-slate-400 mb-0.5">Clave Catastral de la otra parcela</label>
                        <input
                          type="text"
                          value={tempPredioClave}
                          onChange={(e) => setTempPredioClave(e.target.value)}
                          placeholder="Ej: 1702521010088"
                          className={`w-full bg-slate-950 border rounded-lg px-2.5 py-1.5 text-xs focus:outline-none ${
                            claveValidada === 'valida' ? 'border-emerald-600'
                              : claveValidada === 'invalida' ? 'border-red-600'
                              : 'border-slate-850'
                          }`}
                        />
                        {/* v4.3: validación en vivo contra el catastro oficial */}
                        {cargandoCatastro && (
                          <p className="text-[10px] text-slate-500 mt-0.5">Cargando catálogo catastral…</p>
                        )}
                        {claveValidada === 'valida' && (
                          <p className="text-[10px] text-emerald-400 mt-0.5">
                            ✓ Clave encontrada en el catastro{clavesCatastro?.[claveTrim] ? ` — ${Math.round(clavesCatastro[claveTrim]).toLocaleString('es-EC')} m²` : ''}
                          </p>
                        )}
                        {claveValidada === 'invalida' && (
                          <p className="text-[10px] text-red-400 mt-0.5">
                            ✗ Esta clave no existe en el catastro. Verifique el número (13 dígitos, sin espacios).
                          </p>
                        )}
                      </div>
                      <div>
                        <label className="block text-[10px] text-slate-400 mb-0.5">Área de Riego de esa parcela (m²)</label>
                        <input 
                          type="number"
                          value={tempPredioArea}
                          onChange={(e) => setTempPredioArea(e.target.value)}
                          placeholder="Ej: 1200"
                          className="w-full bg-slate-950 border border-slate-850 rounded-lg px-2.5 py-1.5 text-xs focus:outline-none"
                        />
                      </div>
                    </div>

                    {/* v4.3: Producción de ESTA parcela (opcional) */}
                    <div className="border border-slate-800 rounded-xl p-3 space-y-3 bg-slate-900/30">
                      <p className="text-[10px] text-slate-400">
                        🌱 <span className="font-semibold text-slate-300">¿Qué produce en esta parcela?</span> (opcional — si no lo llena, un técnico lo investigará en campo)
                      </p>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div className="space-y-1.5">
                          <div className="flex gap-1.5">
                            <select
                              value={tempPCultivo}
                              onChange={(e) => setTempPCultivo(e.target.value)}
                              className="flex-1 bg-slate-950 border border-slate-850 rounded-lg px-2 py-1.5 text-xs focus:outline-none"
                            >
                              <option value="">Cultivo…</option>
                              {TIPOS_CULTIVO.map((tc) => <option key={tc} value={tc}>{tc}</option>)}
                            </select>
                            <input
                              type="number"
                              value={tempPCultivoArea}
                              onChange={(e) => setTempPCultivoArea(e.target.value)}
                              placeholder="m²"
                              className="w-16 bg-slate-950 border border-slate-850 rounded-lg px-2 py-1.5 text-xs focus:outline-none"
                            />
                            <button
                              type="button"
                              onClick={() => {
                                if (!tempPCultivo) return;
                                setTempPredioCultivos([...tempPredioCultivos, { tipo_cultivo: tempPCultivo, superficie_m2: parseFloat(tempPCultivoArea) || 0 }]);
                                setTempPCultivo(''); setTempPCultivoArea('');
                              }}
                              className="px-2 rounded-lg bg-emerald-700 hover:bg-emerald-600 text-white text-xs cursor-pointer"
                            >+</button>
                          </div>
                          {tempPredioCultivos.map((c, i) => (
                            <div key={i} className="flex items-center justify-between text-[10px] text-slate-300 bg-slate-950/60 rounded px-2 py-1">
                              <span>🌾 {c.tipo_cultivo}{c.superficie_m2 ? ` — ${c.superficie_m2} m²` : ''}</span>
                              <button type="button" onClick={() => setTempPredioCultivos(tempPredioCultivos.filter((_, j) => j !== i))} className="text-red-400 cursor-pointer">✗</button>
                            </div>
                          ))}
                        </div>
                        <div className="space-y-1.5">
                          <div className="flex gap-1.5">
                            <select
                              value={tempPAnimal}
                              onChange={(e) => setTempPAnimal(e.target.value)}
                              className="flex-1 bg-slate-950 border border-slate-850 rounded-lg px-2 py-1.5 text-xs focus:outline-none"
                            >
                              <option value="">Animal…</option>
                              {ESPECIES_ANIMALES.map((ea) => <option key={ea} value={ea}>{ea}</option>)}
                            </select>
                            <input
                              type="number"
                              value={tempPAnimalCant}
                              onChange={(e) => setTempPAnimalCant(e.target.value)}
                              placeholder="Cant."
                              className="w-16 bg-slate-950 border border-slate-850 rounded-lg px-2 py-1.5 text-xs focus:outline-none"
                            />
                            <button
                              type="button"
                              onClick={() => {
                                if (!tempPAnimal) return;
                                setTempPredioAnimales([...tempPredioAnimales, { especie: tempPAnimal, cantidad: parseInt(tempPAnimalCant) || 1 }]);
                                setTempPAnimal(''); setTempPAnimalCant('');
                              }}
                              className="px-2 rounded-lg bg-emerald-700 hover:bg-emerald-600 text-white text-xs cursor-pointer"
                            >+</button>
                          </div>
                          {tempPredioAnimales.map((a, i) => (
                            <div key={i} className="flex items-center justify-between text-[10px] text-slate-300 bg-slate-950/60 rounded px-2 py-1">
                              <span>🐄 {a.especie} — {a.cantidad}</span>
                              <button type="button" onClick={() => setTempPredioAnimales(tempPredioAnimales.filter((_, j) => j !== i))} className="text-red-400 cursor-pointer">✗</button>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>

                    <div className="flex justify-end pt-1">
                      <button
                        type="button"
                        onClick={addPredioAdicional}
                        disabled={claveValidada === 'invalida' || !claveTrim}
                        className="w-full sm:w-auto bg-blue-600 hover:bg-blue-700 disabled:bg-slate-800 disabled:text-slate-500 disabled:cursor-not-allowed text-white font-bold py-1.5 px-3 rounded-lg text-xs transition-colors flex items-center justify-center gap-1.5 cursor-pointer whitespace-nowrap"
                      >
                        <Plus className="w-3.5 h-3.5" /> Agregar terreno
                      </button>
                    </div>

                    {prediosAdicionales.length === 0 ? (
                      <p className="text-[11px] text-slate-500 italic text-center py-2">No ha agregado predios adicionales.</p>
                    ) : (
                      <div className="overflow-x-auto">
                        <table className="w-full text-xs text-left">
                          <thead>
                            <tr className="border-b border-slate-850 text-slate-400 text-[10px]">
                              <th className="py-2">Clave Catastral</th>
                              <th className="py-2">Área Riego</th>
                              <th className="py-2 text-right">Acción</th>
                            </tr>
                          </thead>
                          <tbody>
                            {prediosAdicionales.map((p, idx) => (
                              <tr key={idx} className="border-b border-slate-900/60 hover:bg-slate-900/20">
                                <td className="py-2 font-medium">
                                  {p.clave_catastral_otro}
                                  {(p.cultivos?.length || p.animales?.length) ? (
                                    <span className="block text-[9px] text-emerald-400 mt-0.5">
                                      🌱 {p.cultivos?.length || 0} cultivo(s) · 🐄 {p.animales?.length || 0} animal(es)
                                    </span>
                                  ) : (
                                    <span className="block text-[9px] text-slate-500 mt-0.5">Producción pendiente (campo)</span>
                                  )}
                                </td>
                                <td className="py-2">{p.area_riego_otro} m²</td>
                                <td className="py-2 text-right">
                                  <button type="button" onClick={() => removePredioAdicional(idx)} className="text-red-400 hover:text-red-300 cursor-pointer">
                                    <Trash2 className="w-3.5 h-3.5" />
                                  </button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

          </div>

          {/* Stepper navigation buttons */}
          <div className="border-t border-slate-800/80 pt-4 mt-6 flex justify-between gap-4">
            {step > 1 ? (
              <button 
                type="button" 
                onClick={prevStep}
                className="flex items-center gap-1 px-4 py-2 border border-slate-800 hover:bg-slate-900 text-slate-300 rounded-xl text-xs font-semibold cursor-pointer transition-colors"
              >
                <ArrowLeft className="w-4 h-4" /> Atrás
              </button>
            ) : <div />}

            {step < 4 ? (
              <button 
                type="button" 
                onClick={nextStep}
                className="bg-blue-600 hover:bg-blue-700 text-white flex items-center gap-1 px-5 py-2.5 rounded-xl text-xs font-bold cursor-pointer transition-all shadow-md shadow-blue-500/10"
              >
                Siguiente <ArrowRight className="w-4 h-4" />
              </button>
            ) : (
              <button 
                type="button" 
                onClick={handleSubmit}
                disabled={loading}
                className="bg-emerald-500 hover:bg-emerald-600 disabled:bg-slate-800 disabled:text-slate-500 text-white flex items-center justify-center gap-1 px-6 py-2.5 rounded-xl text-xs font-bold cursor-pointer transition-all shadow-md shadow-emerald-500/10 min-w-[120px]"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" /> Enviando...
                  </>
                ) : (
                  <>
                    Enviar Encuesta
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </main>

      {/* Footer copyright */}
      <footer className="py-4 text-center text-[10px] text-slate-500 border-t border-slate-900">
        © 2026 Consorcio Cayambe SPT — Prefectura de Pichincha. Todos los derechos reservados.
      </footer>
    </div>
  );
}
