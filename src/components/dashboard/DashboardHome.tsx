import { useEffect, useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  PieChart, Pie, Cell, ResponsiveContainer, LineChart, Line, LabelList,
} from 'recharts';
import {
  ClipboardList, Map as MapIcon, Sprout, PawPrint,
  Users, Droplets, TrendingUp, Loader2, Link, Copy, Check, ExternalLink, MapPin,
  GraduationCap, Baby, Lightbulb
} from 'lucide-react';
import { type FichaPredio, type EstadisticasResumen, esFichaHija, esHijaPendiente, safeToDate } from '../../lib/types';
import { calcularEstadisticas } from '../../lib/firestoreService';
import { getColorTecnico, TECNICOS } from '../../lib/constants';
import { useAuth } from '../../hooks/useAuth';

// ── Link Card para Enlaces Rápidos ──
function LinkCard({ title, url, badgeText, badgeColor }: { title: string; url: string; badgeText: string; badgeColor: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Error al copiar el enlace', err);
    }
  };

  return (
    <div className="flex-1 min-w-[260px] p-3 rounded-xl border flex flex-col justify-between gap-2.5 transition-all hover:bg-black/5 dark:hover:bg-white/5"
      style={{
        background: 'var(--bg-input)',
        borderColor: 'var(--border-color)'
      }}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-semibold truncate" style={{ color: 'var(--text-primary)' }}>{title}</span>
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${badgeColor}`}>
          {badgeText}
        </span>
      </div>
      
      <div className="flex items-center gap-2 p-1.5 rounded-lg border" style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)' }}>
        <span className="text-[10px] truncate flex-1 select-all font-mono" style={{ color: 'var(--text-secondary)' }}>
          {url}
        </span>
        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={handleCopy}
            className="p-1 rounded-md transition-colors cursor-pointer hover:bg-black/5 dark:hover:bg-white/10"
            style={{ color: 'var(--text-secondary)' }}
            title="Copiar enlace"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="p-1 rounded-md transition-colors hover:bg-black/5 dark:hover:bg-white/10"
            style={{ color: 'var(--text-secondary)' }}
            title="Abrir enlace"
          >
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>
    </div>
  );
}

// ── KPI Card ──
function KPICard({ icon: Icon, label, value, color, sub }: {
  icon: React.ElementType; label: string; value: string | number; color: string; sub?: string;
}) {
  // El área total en m² son 11 caracteres («102.949.873») y a text-2xl se salía
  // de la tarjeta. El tamaño baja según el largo del número en vez de recortarlo:
  // en un dashboard de superficies, un dígito escondido es un dato equivocado.
  const textoValor = typeof value === 'number' ? value.toLocaleString('es-EC') : value;
  const tamanoValor = textoValor.length > 10 ? 'text-lg' : textoValor.length > 7 ? 'text-xl' : 'text-2xl';
  return (
    <div
      className="rounded-xl border p-4 transition-all group hover:border-blue-500/30"
      style={{
        background: 'var(--bg-card)',
        borderColor: 'var(--border-color)',
        boxShadow: 'var(--shadow-card)',
      }}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>{label}</p>
          <p className={`${tamanoValor} font-bold leading-tight`} style={{ color: 'var(--text-heading)' }}>{textoValor}</p>
          {sub && <p className="text-[11px] font-medium mt-1" style={{ color: 'var(--text-secondary)' }}>{sub}</p>}
        </div>
        <div className="w-10 h-10 rounded-lg flex items-center justify-center opacity-80 group-hover:opacity-100 transition-opacity"
          style={{ background: `${color}15`, border: `1px solid ${color}30` }}
        >
          <Icon className="w-5 h-5" style={{ color }} />
        </div>
      </div>
    </div>
  );
}

// ── Colores para gráficos ──
const PIE_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];

// ── Componente Principal ──
interface Props {
  fichas: FichaPredio[];
  loading: boolean;
  cultivosData: any[];
  animalesData?: any[];
  prediosAdicionalesData?: any[];
}

/** Cifras de superficie del sistema (`generar_superficie_por_comunidad.py`). */
interface Superficie {
  total: {
    fichas: number;
    predios_catastrales: number;
    superficie_catastral_ha: number;
    superficie_declarada_ha: number;
    riego_declarado_ha: number;
    riego_ajustado_ha: number;
    predios_compartidos: number;
  };
}

export default function DashboardHome({ fichas, loading, cultivosData, animalesData = [], prediosAdicionalesData = [] }: Props) {
  const [stats, setStats] = useState<EstadisticasResumen | null>(null);
  // Fuente única de superficie: ningún cálculo de hectáreas se rehace aquí.
  const [superficie, setSuperficie] = useState<Superficie | null>(null);

  useEffect(() => {
    fetch('/geo/superficie_por_comunidad.json')
      .then((r) => (r.ok ? r.json() : null))
      .then(setSuperficie)
      .catch(() => setSuperficie(null));
  }, []);
  const { isAdmin, isTecnico } = useAuth();
  // Los gráficos de seguimiento del equipo (por técnico y por día) son de uso
  // interno: el contratante ve el padrón, no cómo se reparte el trabajo.
  const esInterno = isAdmin || isTecnico;

  useEffect(() => {
    if (fichas.length > 0) {
      // Las fichas hijas PENDIENTES (Sección 4 sin investigar) se excluyen de
      // las estadísticas para no duplicar datos heredados de la ficha madre.
      // Las hijas COMPLETADAS sí cuentan: ya fueron investigadas en campo.
      const s = calcularEstadisticas(fichas.filter((f) => !esHijaPendiente(f)));

      // Calcular cultivos frecuentes desde datos filtrados
      const cultivoCount: Record<string, number> = {};
      const fIds = new Set(fichas.map(f => f.id));
      const fCultivos = cultivosData.filter((c: any) => fIds.has(c.ficha_id));

      // Se agrupa por el nombre normalizado, igual que los informes: el padrón
      // traía «Cebolla» y «CEBOLLA» como si fueran cultivos distintos y el
      // Dashboard los pintaba en dos filas. El dato ya se unificó en origen
      // (`depurar_cultivos_y_animales.py`), pero esto lo deja a prueba de que
      // una sincronización futura vuelva a traer las dos escrituras.
      const etiquetas: Record<string, string> = {};
      for (const c of fCultivos) {
        const bruto = String(c.tipo_cultivo || 'Sin dato').trim().replace(/\s+/g, ' ');
        const clave = bruto.toLocaleUpperCase('es-EC');
        // la primera forma que aparece manda, salvo que sea toda en mayúsculas
        if (!etiquetas[clave] || etiquetas[clave] === clave) etiquetas[clave] = bruto;
        cultivoCount[clave] = (cultivoCount[clave] || 0) + 1;
      }
      for (const [clave, etiqueta] of Object.entries(etiquetas)) {
        if (etiqueta !== clave) {
          cultivoCount[etiqueta] = cultivoCount[clave];
          delete cultivoCount[clave];
        }
      }
      s.cultivosFrecuentes = cultivoCount;
      s.totalCultivos = fCultivos.length;

      setStats(s);
    }
  }, [fichas, cultivosData]);

  if (loading || !stats) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    );
  }

  // Filtrar subtablas por las fichas actualmente filtradas
  const filteredFichaIds = new Set(fichas.map(f => f.id));
  const filteredAnimales = animalesData.filter((a: any) => filteredFichaIds.has(a.ficha_id));
  const filteredPrediosAdicionales = prediosAdicionalesData.filter((pa: any) => filteredFichaIds.has(pa.ficha_id));
  const totalAnimales = filteredAnimales.reduce((acc: number, a: any) => acc + (Number(a.cantidad) || 0), 0);

  // Claves catastrales principales activas
  const clavesPrincipales = new Set(fichas.map(f => (f.clave_catastral || '').trim()).filter(Boolean));

  // Claves declaradas verbalmente únicas (otros predios del regante sin encuesta propia)
  const clavesDeclaradasUnicas = new Set(
    filteredPrediosAdicionales
      .map((pa: any) => (pa.clave_catastral_otro || '').trim())
      .filter(Boolean)
  );

  // Filtrar para obtener solo las "Adicionales Puras" (claves únicas sin encuesta de ningún tipo)
  const clavesDeclaradasPuras = Array.from(clavesDeclaradasUnicas).filter(k =>
    !clavesPrincipales.has(k)
  );

  const totalDeclaradosPuros = clavesDeclaradasPuras.length;

  // ── Métricas de Fichas Hijas (v4.3 — generadas desde Sección 7) ──
  const fichasHijas = fichas.filter(esFichaHija);
  const hijasPendientes = fichasHijas.filter(esHijaPendiente).length;
  const hijasCompletadas = fichasHijas.length - hijasPendientes;
  const totalPrincipales = fichas.length - fichasHijas.length;

  const fichasPorTecnico = Object.entries(stats.fichasPorTecnico)
    .filter(([nombre]) => nombre !== 'AUTO-SECCION7') // generador automático, no es un técnico
    .map(([nombre, principales]) => ({
      nombre,
      principales,
    }))
    .sort((a, b) => b.principales - a.principales);

  const metodoRiego = [
    { name: 'Aspersión', value: stats.metodoRiego.aspersion, color: '#3b82f6' },
    { name: 'Gravedad', value: stats.metodoRiego.gravedad, color: '#10b981' },
    { name: 'Goteo', value: stats.metodoRiego.goteo, color: '#f59e0b' },
  ].filter((m) => m.value > 0);

  const tenencia = Object.entries(stats.tenenciaPredioCounts)
    .map(([name, value]) => ({ name, value }));

  const cultivosTop = Object.entries(stats.cultivosFrecuentes)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 12);

  // ── Avance diario (v4.8) ──
  // No se usa stats.fichasPorFecha: mete en el mismo saco el levantamiento de
  // campo y la generación automática de la Sección 7, y esta última se creó en
  // bloque (2.400 fichas el 19-jul con AUTO-SECCION7, 118 más el 23-jun). Ese
  // pico aplastaba la escala — el mejor día real de campo son 497 fichas — y
  // hacía leer como trabajo de un día lo que fue una operación de escritorio.
  //
  // Se separan las dos cosas que sí son trabajo de campo:
  //   · lo levantado con la ficha nueva  → fecha_creacion
  //   · la Sección 4 de las adicionales  → fecha_completado (julio y agosto)
  // Sin esa segunda serie el gráfico quedaría plano desde el 30 de junio, como
  // si el equipo hubiera dejado de trabajar.
  const diaDe = (v: unknown) => safeToDate(v).toISOString().split('T')[0];
  const generadaEnBloque = (f: FichaPredio) => esFichaHija(f) || f.creado_por === 'AUTO-SECCION7';

  const avanceMap = new Map<string, { fecha: string; campo: number; completadas: number }>();
  const diaSlot = (fecha: string) => {
    let d = avanceMap.get(fecha);
    if (!d) { d = { fecha, campo: 0, completadas: 0 }; avanceMap.set(fecha, d); }
    return d;
  };
  for (const f of fichas) {
    if (generadaEnBloque(f)) continue;
    if (!f.fecha_creacion) continue;
    diaSlot(diaDe(f.fecha_creacion)).campo++;
  }
  for (const f of fichas) {
    // Solo las adicionales llevan fecha_completado: es el día en que el técnico
    // fue a campo a levantar la producción de ese lote.
    if (!esFichaHija(f) || !f.fecha_completado) continue;
    diaSlot(diaDe(f.fecha_completado)).completadas++;
  }
  const avancePorDia = Array.from(avanceMap.values()).sort((a, b) => a.fecha.localeCompare(b.fecha));
  const totalCampoDiario = avancePorDia.reduce((acc, d) => acc + d.campo, 0);
  const totalCompletadasDiario = avancePorDia.reduce((acc, d) => acc + d.completadas, 0);
  const generadasEnBloque = fichas.filter(generadaEnBloque).length;

  const fichasPorParroquia = Object.entries(stats.fichasPorParroquia)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);

  // ── Cálculos dinámicos sectoriales para los gráficos Recharts ──
  // 1. Cobertura de Riego (Riego vs Secano en ha)
  // Con la barra de filtros puesta, las cifras del sistema (que son del total)
  // ya no describen lo que se está viendo y hay que volver a lo declarado.
  const hayFiltro = !!superficie && fichas.length < superficie.total.fichas;
  const areaRiegoTotalM2 = fichas.reduce((acc, f) => acc + (Number(f.area_riego) || 0), 0);
  const areaSinRiegoTotalM2 = fichas.reduce((acc, f) => acc + (Number(f.area_sin_riego) || 0), 0);
  const areaRiegoHa = areaRiegoTotalM2 / 10000;
  const areaSinRiegoHa = areaSinRiegoTotalM2 / 10000;

  // «Secano» se cambió por «Sin riego» en toda la pantalla (pedido de JAVIKO,
  // 12-ago): es el término que entiende cualquier lector, no solo el técnico.
  const coberturaRiegoData = [
    { name: 'Con riego', value: Number(areaRiegoHa.toFixed(2)), color: '#3b82f6' },
    { name: 'Sin riego', value: Number(areaSinRiegoHa.toFixed(2)), color: '#f59e0b' }
  ].filter(item => item.value > 0);

  // 2. Distribución de Especies Pecuarias (Animales)
  const animalesPorEspecieMap: Record<string, number> = {};
  for (const a of filteredAnimales) {
    const esp = a.especie || 'Sin clasificar';
    animalesPorEspecieMap[esp] = (animalesPorEspecieMap[esp] || 0) + (Number(a.cantidad) || 0);
  }
  const animalesPorEspecieData = Object.entries(animalesPorEspecieMap)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 5);

  // 3. Propósito de Cultivos (Autoconsumo vs Venta)
  let autoconsumoCount = 0;
  let mercadoCount = 0;
  let agroindustriaCount = 0;
  let exportacionCount = 0;

  const fIds = new Set(fichas.map(f => f.id));
  const fCultivos = cultivosData.filter((c: any) => fIds.has(c.ficha_id));
  for (const c of fCultivos) {
    if (c.es_autoconsumo) autoconsumoCount++;
    if (c.es_mercado) mercadoCount++;
    if (c.es_agroindustria) agroindustriaCount++;
    if (c.es_exportacion) exportacionCount++;
  }

  const destinoCultivosData = [
    { name: 'Autoconsumo', value: autoconsumoCount, color: '#10b981' },
    { name: 'Mercado / Venta', value: mercadoCount, color: '#3b82f6' },
    { name: 'Agroindustria', value: agroindustriaCount, color: '#8b5cf6' },
    { name: 'Exportación', value: exportacionCount, color: '#ec4899' }
  ].filter(item => item.value > 0);

  // ── Perfil de las familias del padrón (v4.8) ──
  // Regla 6 del proyecto: personas ≠ predios. Escolaridad, hijos y las
  // preguntas de la encuesta comunitaria salen SOLO de las fichas principales.
  // Las adicionales son otros lotes del mismo regante: sumarlas contaría a la
  // misma familia tantas veces como predios tenga.
  const fichasPersonas = fichas.filter((f) => !esFichaHija(f));

  // Escala de escolaridad en orden pedagógico, no por cantidad: así se lee de
  // menor a mayor instrucción aunque cambien los conteos.
  const NIVELES_INSTRUCCION = ['Ninguno', 'Alfabetizado', 'Primaria', 'Secundaria', 'Superior'];
  const COLORES_INSTRUCCION: Record<string, string> = {
    'Ninguno': '#94a3b8', 'Alfabetizado': '#22d3ee', 'Primaria': '#3b82f6',
    'Secundaria': '#6366f1', 'Superior': '#8b5cf6',
  };
  const instruccionCount: Record<string, number> = {};
  let sinDatoInstruccion = 0;
  for (const f of fichasPersonas) {
    const nivel = (f.nivel_instruccion || '').trim();
    if (!nivel) { sinDatoInstruccion++; continue; }
    instruccionCount[nivel] = (instruccionCount[nivel] || 0) + 1;
  }
  const instruccionData = [
    ...NIVELES_INSTRUCCION.filter((n) => instruccionCount[n] > 0)
      .map((name) => ({ name, value: instruccionCount[name] })),
    // Cualquier valor que no esté en la escala (erratas de digitación) se
    // muestra igual al final: es preferible verlo que perderlo en silencio.
    ...Object.entries(instruccionCount)
      .filter(([name]) => !NIVELES_INSTRUCCION.includes(name))
      .map(([name, value]) => ({ name, value })),
  ];
  const conDatoInstruccion = fichasPersonas.length - sinDatoInstruccion;

  // Hijos declarados. Una familia puede tener dato en un solo campo (dos hijos
  // hombres y ninguna mujer se registra como 2 y vacío), así que basta con que
  // uno de los dos venga lleno para contarla.
  let hijosHombres = 0, hijosMujeres = 0, familiasConDatoHijos = 0;
  for (const f of fichasPersonas) {
    const tieneDato = f.hijos_hombres != null || f.hijos_mujeres != null;
    if (!tieneDato) continue;
    familiasConDatoHijos++;
    hijosHombres += Number(f.hijos_hombres) || 0;
    hijosMujeres += Number(f.hijos_mujeres) || 0;
  }
  const hijosData = [
    { name: 'Hombres', value: hijosHombres, color: '#3b82f6' },
    { name: 'Mujeres', value: hijosMujeres, color: '#ec4899' },
  ];
  const totalHijos = hijosHombres + hijosMujeres;
  const promedioHijos = familiasConDatoHijos > 0 ? totalHijos / familiasConDatoHijos : 0;

  // Preguntas Sí/No de la encuesta comunitaria. El campo llega como texto
  // ('Sí', 'No'), con y sin tilde según el dispositivo.
  const contarSiNo = (campo: keyof FichaPredio) => {
    let si = 0, no = 0;
    for (const f of fichasPersonas) {
      const v = String(f[campo] ?? '').trim().toUpperCase();
      if (!v) continue;
      if (v.startsWith('S')) si++;
      else if (v.startsWith('N')) no++;
    }
    return { si, no };
  };
  const presa = contarSiNo('conoce_presa');
  const capacitado = contarSiNo('recibio_capacitacion');
  const quiereCap = contarSiNo('le_gustaria_cap');
  const comunitariaData = [
    { name: 'Conoce la represa', si: presa.si, no: presa.no },
    { name: 'Recibió capacitación', si: capacitado.si, no: capacitado.no },
    { name: 'Quiere capacitarse', si: quiereCap.si, no: quiereCap.no },
  ].filter((d) => d.si + d.no > 0);

  // Superficies en hectáreas: es la unidad en la que trabaja el contratante.
  // Los m² se conservan porque son el dato crudo de la ficha.
  const areaTotalHa = stats.areaTotal / 10000;

  return (
    <div className="space-y-6">
      {/* Enlaces Rápidos de Compartición */}
      {isAdmin && (
        <div
          className="p-5 rounded-2xl border relative overflow-hidden transition-all duration-300"
          style={{
            background: 'var(--bg-card)',
            borderColor: 'var(--border-color)',
            boxShadow: 'var(--shadow-card)',
            backdropFilter: 'blur(12px)',
          }}
        >
          {/* Decoración de fondo */}
          <div className="absolute -right-10 -top-10 w-40 h-40 rounded-full opacity-10 dark:opacity-20 bg-blue-500 blur-3xl pointer-events-none" />
          <div className="absolute -left-10 -bottom-10 w-40 h-40 rounded-full opacity-10 dark:opacity-20 bg-emerald-500 blur-3xl pointer-events-none" />

          <div className="relative z-10 flex flex-col xl:flex-row xl:items-center justify-between gap-6">
            <div>
              <h2 className="text-sm font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                <Link className="w-4.5 h-4.5 text-amber-500" />
                Enlaces Rápidos de Compartición
              </h2>
              <p className="text-xs mt-1 max-w-xl leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                Utiliza estos enlaces para que los comuneros regantes registren sus datos (formulario público) o para que los técnicos ingresen directamente a auditar y procesar las respuestas.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row gap-4 w-full xl:w-auto shrink-0">
              <LinkCard
                title="Formulario para Regantes (Público)"
                url={`${window.location.origin}/encuesta`}
                badgeText="Comuneros"
                badgeColor="bg-emerald-500/10 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border border-emerald-500/20 dark:border-emerald-500/30"
              />
              <LinkCard
                title="Módulo de Revisión (Técnicos)"
                url={`${window.location.origin}/encuestas`}
                badgeText="Técnicos"
                badgeColor="bg-blue-500/10 dark:bg-blue-500/20 text-blue-700 dark:text-blue-300 border border-blue-500/20 dark:border-blue-500/30"
              />
            </div>
          </div>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-7 gap-3">
        <KPICard
          icon={ClipboardList}
          label="Fichas Levantadas"
          value={totalPrincipales}
          color="#3b82f6"
          sub={fichasHijas.length > 0
            ? `+ ${fichasHijas.length.toLocaleString('es-EC')} fichas adicionales (Sección 7)`
            : `Total de fichas registradas en el catastro`}
        />
        {fichasHijas.length > 0 ? (
          <KPICard
            icon={MapPin}
            label="Fichas Adicionales (Otros Predios)"
            value={fichasHijas.length}
            color="#06b6d4"
            sub={`⚪ ${hijasPendientes.toLocaleString('es-EC')} pendientes S4 · ✅ ${hijasCompletadas.toLocaleString('es-EC')} completadas`}
          />
        ) : (
          <KPICard
            icon={MapPin}
            label="Otros Predios del Regante"
            value={totalDeclaradosPuros}
            color="#06b6d4"
            sub={`${totalDeclaradosPuros.toLocaleString('es-EC')} predios únicos sin encuesta`}
          />
        )}
        <KPICard icon={MapIcon} label="Polígonos Catastro" value={stats.totalPoligonos} color="#10b981" sub="Base catastral completa" />
        {/* La superficie del sistema se mide contando cada predio UNA vez (su
            polígono del catastro). Sumar el área de las fichas cuenta varias
            veces los predios de herederos —1.780 ha de más—; ese dato sigue
            visible debajo porque es lo que declara la gente, no un error. */}
        <KPICard
          icon={TrendingUp}
          label="Superficie del sistema"
          value={superficie
            ? `${superficie.total.superficie_catastral_ha.toLocaleString('es-EC',
                { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ha`
            : `${areaTotalHa.toLocaleString('es-EC', { maximumFractionDigits: 2 })} ha`}
          color="#f59e0b"
          sub={superficie
            ? `${superficie.total.predios_catastrales.toLocaleString('es-EC')} predios · los regantes declaran ${superficie.total.superficie_declarada_ha.toLocaleString('es-EC', { maximumFractionDigits: 0 })} ha`
            : `${Math.round(stats.areaTotal).toLocaleString('es-EC')} m² declarados`}
        />
        <KPICard icon={Users} label="Técnicos Activos" value={stats.tecnicosActivos} color="#8b5cf6" />
        <KPICard icon={Sprout} label="Cultivos Registrados" value={stats.totalCultivos} color="#22c55e" />
        <KPICard icon={PawPrint} label="Animales Registrados" value={totalAnimales} color="#ec4899" sub={`${filteredAnimales.length} registros`} />
      </div>

      {/* Sección Análisis Sectorial */}
      <div className="space-y-3">
        <h3 className="text-sm font-bold tracking-wide uppercase text-blue-500 flex items-center gap-2">
          <TrendingUp className="w-4 h-4" />
          Análisis del Sector Seleccionado
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {/* Tarjeta % Cultivos */}
          <div className="rounded-2xl border p-5 flex flex-col justify-between relative overflow-hidden transition-all duration-300 hover:border-emerald-500/30"
               style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)', boxShadow: 'var(--shadow-card)' }}>
            <div className="flex justify-between items-start">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Cultivos en el Sector</p>
                <h4 className="text-3xl font-black mt-2" style={{ color: 'var(--text-heading)' }}>{((stats.totalCultivos / (cultivosData.length || 1)) * 100).toFixed(1)}%</h4>
                <p className="text-[11px] mt-1 leading-normal" style={{ color: 'var(--text-secondary)' }}>
                  {stats.totalCultivos.toLocaleString('es-EC')} de {(cultivosData.length).toLocaleString('es-EC')} parcelas agrícolas del sistema
                </p>
              </div>
              <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 shrink-0">
                <Sprout className="w-5 h-5" />
              </div>
            </div>
            {/* Barra de progreso */}
            <div className="w-full bg-black/5 dark:bg-white/10 h-2 rounded-full mt-4 overflow-hidden">
              <div className="bg-emerald-500 h-full rounded-full transition-all duration-500" style={{ width: `${Math.min((stats.totalCultivos / (cultivosData.length || 1)) * 100, 100)}%` }} />
            </div>
          </div>

          {/* Tarjeta % Animales */}
          <div className="rounded-2xl border p-5 flex flex-col justify-between relative overflow-hidden transition-all duration-300 hover:border-pink-500/30"
               style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)', boxShadow: 'var(--shadow-card)' }}>
            <div className="flex justify-between items-start">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Animales en el Sector</p>
                <h4 className="text-3xl font-black mt-2" style={{ color: 'var(--text-heading)' }}>{((totalAnimales / (animalesData.reduce((acc: number, a: any) => acc + (Number(a.cantidad) || 0), 0) || 1)) * 100).toFixed(1)}%</h4>
                <p className="text-[11px] mt-1 leading-normal" style={{ color: 'var(--text-secondary)' }}>
                  {totalAnimales.toLocaleString('es-EC')} de {(animalesData.reduce((acc: number, a: any) => acc + (Number(a.cantidad) || 0), 0)).toLocaleString('es-EC')} cabezas registradas
                </p>
              </div>
              <div className="p-3 rounded-xl bg-pink-500/10 border border-pink-500/20 text-pink-500 shrink-0">
                <PawPrint className="w-5 h-5" />
              </div>
            </div>
            {/* Barra de progreso */}
            <div className="w-full bg-black/5 dark:bg-white/10 h-2 rounded-full mt-4 overflow-hidden">
              <div className="bg-pink-500 h-full rounded-full transition-all duration-500" style={{ width: `${Math.min((totalAnimales / (animalesData.reduce((acc: number, a: any) => acc + (Number(a.cantidad) || 0), 0) || 1)) * 100, 100)}%` }} />
            </div>
          </div>

          {/* Tarjeta ha CON Riego — pedida por el contratante el 9-ago: la
              pantalla mostraba solo la superficie sin riego, y el dato que le
              interesa es cuánta tierra riega hoy el sistema. */}
          <div className="rounded-2xl border p-5 flex flex-col justify-between relative overflow-hidden transition-all duration-300 hover:border-blue-500/30"
               style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)', boxShadow: 'var(--shadow-card)' }}>
            <div className="flex justify-between items-start">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Superficie con Riego</p>
                {/* Sin filtros manda la cifra del sistema, la misma que los
                    informes: el riego declarado arrastra la duplicación de los
                    predios de herederos y por eso sale más alto. Con un filtro
                    puesto no se puede usar —el JSON es del total— y se muestra
                    lo declarado, diciéndolo. */}
                <h4 className="text-3xl font-black mt-2" style={{ color: 'var(--text-heading)' }}>
                  {(superficie && !hayFiltro
                    ? superficie.total.riego_ajustado_ha
                    : areaRiegoHa
                  ).toLocaleString('es-EC', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ha
                </h4>
                <p className="text-[11px] mt-1 leading-normal" style={{ color: 'var(--text-secondary)' }}>
                  {superficie && !hayFiltro
                    ? `Cada predio contado una vez · los regantes declaran ${superficie.total.riego_declarado_ha.toLocaleString('es-EC', { maximumFractionDigits: 0 })} ha`
                    : `Equivalente a ${Math.round(areaRiegoTotalM2).toLocaleString('es-EC')} m² bajo riego en este sector`}
                </p>
              </div>
              <div className="p-3 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-500 shrink-0">
                <Droplets className="w-5 h-5" />
              </div>
            </div>
            <div className="text-[10px] mt-4 font-semibold text-blue-600 dark:text-blue-400 flex items-center gap-1">
              <span>{superficie && !hayFiltro
                ? 'Hectáreas regadas del sistema'
                : 'Hectáreas regadas registradas en fichas'}</span>
            </div>
          </div>

          {/* Tarjeta ha Sin Riego */}
          <div className="rounded-2xl border p-5 flex flex-col justify-between relative overflow-hidden transition-all duration-300 hover:border-amber-500/30"
               style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)', boxShadow: 'var(--shadow-card)' }}>
            <div className="flex justify-between items-start">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Superficie Sin Riego</p>
                <h4 className="text-3xl font-black mt-2" style={{ color: 'var(--text-heading)' }}>
                  {areaSinRiegoHa.toLocaleString('es-EC', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ha
                </h4>
                <p className="text-[11px] mt-1 leading-normal" style={{ color: 'var(--text-secondary)' }}>
                  Equivalente a {Math.round(areaSinRiegoTotalM2).toLocaleString('es-EC')} m² sin riego en este sector
                </p>
              </div>
              <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-500 shrink-0">
                <Droplets className="w-5 h-5" />
              </div>
            </div>
            {/* Mensaje informativo */}
            <div className="text-[10px] mt-4 font-semibold text-amber-600 dark:text-amber-400 flex items-center gap-1">
              <span>Hectáreas sin riego registradas en fichas</span>
            </div>
          </div>
        </div>
      </div>

      {/* Sección Gráficos Sectoriales Dinámicos */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        {/* Cobertura de Riego */}
        <div className="rounded-xl border p-4 flex flex-col justify-between"
             style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)', boxShadow: 'var(--shadow-card)' }}>
          <h4 className="text-xs font-bold uppercase tracking-wider text-blue-500 mb-4 flex items-center gap-2">
            <Droplets className="w-4 h-4 text-blue-500" />
            Uso del Suelo: Con Riego vs Sin Riego (ha)
          </h4>
          <div className="h-[180px] flex items-center justify-center">
            {coberturaRiegoData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={coberturaRiegoData}
                    cx="50%"
                    cy="50%"
                    innerRadius={45}
                    outerRadius={70}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {coberturaRiegoData.map((entry, index) => (
                      <Cell key={index} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(v: any) => `${Number(v).toLocaleString('es-EC', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ha`}
                    contentStyle={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)', borderRadius: 8 }}
                    itemStyle={{ color: 'var(--text-primary)' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Sin datos de área</span>
            )}
          </div>
          {/* La cifra va debajo y no como etiqueta del anillo: en una columna
              de un tercio de ancho, «Con riego: 8.978,86 ha» se salía del
              recuadro y aparecía cortada. */}
          <div className="flex flex-wrap justify-center gap-x-4 gap-y-1 mt-2">
            {coberturaRiegoData.map((entry) => (
              <span key={entry.name} className="text-[11px] flex items-center gap-1.5" style={{ color: 'var(--text-secondary)' }}>
                <span className="w-2 h-2 rounded-sm shrink-0" style={{ background: entry.color }} />
                {entry.name}: <strong style={{ color: 'var(--text-primary)' }}>
                  {entry.value.toLocaleString('es-EC', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ha
                </strong>
              </span>
            ))}
          </div>
        </div>

        {/* Especies Pecuarias */}
        <div className="rounded-xl border p-4 flex flex-col justify-between"
             style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)', boxShadow: 'var(--shadow-card)' }}>
          <h4 className="text-xs font-bold uppercase tracking-wider text-pink-500 mb-4 flex items-center gap-2">
            <PawPrint className="w-4 h-4 text-pink-500" />
            Especies Pecuarias Principales (Cabezas)
          </h4>
          <div className="h-[180px]">
            {animalesPorEspecieData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={animalesPorEspecieData} layout="vertical" margin={{ left: 10, right: 10, top: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                  <XAxis type="number" tick={{ fill: 'var(--text-secondary)', fontSize: 10 }} />
                  <YAxis type="category" dataKey="name" tick={{ fill: 'var(--text-secondary)', fontSize: 10 }} width={70} />
                  <Tooltip
                    contentStyle={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)', borderRadius: 8 }}
                    itemStyle={{ color: 'var(--text-primary)' }}
                  />
                  <Bar dataKey="value" fill="#ec4899" radius={[0, 4, 4, 0]} name="Animales">
                    {animalesPorEspecieData.map((_, index) => (
                      <Cell key={index} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                    <LabelList dataKey="value" position="insideRight" fill="#ffffff" fontSize={10} fontWeight="bold" />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center">
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Sin registros pecuarios</span>
              </div>
            )}
          </div>
        </div>

        {/* Propósito de Cultivos */}
        <div className="rounded-xl border p-4 flex flex-col justify-between"
             style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)', boxShadow: 'var(--shadow-card)' }}>
          <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-500 mb-4 flex items-center gap-2">
            <Sprout className="w-4 h-4 text-emerald-500" />
            Destino de la Producción Agrícola
          </h4>
          <div className="h-[180px]">
            {destinoCultivosData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={destinoCultivosData} margin={{ left: 10, right: 10, top: 5, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                  <XAxis dataKey="name" tick={{ fill: 'var(--text-secondary)', fontSize: 9 }} />
                  <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 10 }} />
                  <Tooltip
                    contentStyle={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)', borderRadius: 8 }}
                    itemStyle={{ color: 'var(--text-primary)' }}
                  />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]} name="Cultivos">
                    {destinoCultivosData.map((entry, index) => (
                      <Cell key={index} fill={entry.color} />
                    ))}
                    <LabelList dataKey="value" position="insideTop" fill="#ffffff" fontSize={10} fontWeight="bold" />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center">
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Sin registros agrícolas</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Perfil de las Familias del Padrón (v4.8) ──
          Ocupa el lugar que antes tenía «Fichas por Técnico» en la vista del
          contratante: en vez de cómo se repartió el trabajo, qué población
          quedó registrada. Todas las cifras salen de las fichas principales. */}
      <div className="space-y-3">
        <h3 className="text-sm font-bold tracking-wide uppercase text-indigo-500 flex items-center gap-2">
          <Users className="w-4 h-4" />
          Perfil de las Familias del Padrón
        </h3>
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
          {/* Nivel de instrucción */}
          <div className="rounded-xl border p-4 flex flex-col"
               style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)', boxShadow: 'var(--shadow-card)' }}>
            <h4 className="text-xs font-bold uppercase tracking-wider text-indigo-500 mb-4 flex items-center gap-2">
              <GraduationCap className="w-4 h-4 text-indigo-500" />
              Nivel de Instrucción
            </h4>
            <div className="h-[200px]">
              {instruccionData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={instruccionData} layout="vertical" margin={{ left: 10, right: 45, top: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                    <XAxis type="number" tick={{ fill: 'var(--text-secondary)', fontSize: 10 }} />
                    <YAxis type="category" dataKey="name" tick={{ fill: 'var(--text-secondary)', fontSize: 10 }} width={82} />
                    <Tooltip
                      contentStyle={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)', borderRadius: 8 }}
                      itemStyle={{ color: 'var(--text-primary)' }}
                      labelStyle={{ color: 'var(--text-primary)' }}
                    />
                    <Bar dataKey="value" name="Regantes" radius={[0, 4, 4, 0]}>
                      {instruccionData.map((entry, index) => (
                        <Cell key={index} fill={COLORES_INSTRUCCION[entry.name] || PIE_COLORS[index % PIE_COLORS.length]} />
                      ))}
                      {/* La etiqueta va FUERA de la barra: «Superior» y
                          «Alfabetizado» son barras cortas y el número quedaba
                          cortado por dentro. */}
                      <LabelList dataKey="value" position="right" fill="var(--text-secondary)" fontSize={10} fontWeight="bold" />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center">
                  <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Sin datos de instrucción</span>
                </div>
              )}
            </div>
            <p className="text-[10px] mt-3 leading-normal" style={{ color: 'var(--text-muted)' }}>
              {conDatoInstruccion.toLocaleString('es-EC')} de {fichasPersonas.length.toLocaleString('es-EC')} regantes con el dato registrado
            </p>
          </div>

          {/* Hijos declarados */}
          <div className="rounded-xl border p-4 flex flex-col"
               style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)', boxShadow: 'var(--shadow-card)' }}>
            <h4 className="text-xs font-bold uppercase tracking-wider text-pink-500 mb-4 flex items-center gap-2">
              <Baby className="w-4 h-4 text-pink-500" />
              Hijos por Familia
            </h4>
            <div className="h-[200px]">
              {totalHijos > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={hijosData} margin={{ left: 10, right: 10, top: 5, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                    <XAxis dataKey="name" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                    <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 10 }} />
                    <Tooltip
                      contentStyle={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)', borderRadius: 8 }}
                      itemStyle={{ color: 'var(--text-primary)' }}
                      labelStyle={{ color: 'var(--text-primary)' }}
                    />
                    <Bar dataKey="value" name="Hijos" radius={[4, 4, 0, 0]}>
                      {hijosData.map((entry, index) => (
                        <Cell key={index} fill={entry.color} />
                      ))}
                      <LabelList dataKey="value" position="insideTop" fill="#ffffff" fontSize={11} fontWeight="bold" />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center">
                  <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Sin datos de hijos</span>
                </div>
              )}
            </div>
            <p className="text-[10px] mt-3 leading-normal" style={{ color: 'var(--text-muted)' }}>
              {totalHijos.toLocaleString('es-EC')} hijos declarados por {familiasConDatoHijos.toLocaleString('es-EC')} familias
              {familiasConDatoHijos > 0 && ` · promedio ${promedioHijos.toLocaleString('es-EC', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} por familia`}
            </p>
          </div>

          {/* Encuesta comunitaria */}
          <div className="rounded-xl border p-4 flex flex-col"
               style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)', boxShadow: 'var(--shadow-card)' }}>
            <h4 className="text-xs font-bold uppercase tracking-wider text-amber-500 mb-4 flex items-center gap-2">
              <Lightbulb className="w-4 h-4 text-amber-500" />
              Represa y Capacitación
            </h4>
            <div className="h-[200px]">
              {comunitariaData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  {/* En horizontal: los tres rótulos ("Conoce la represa"…) se
                      encimaban en el eje X y quedaban ilegibles. */}
                  <BarChart data={comunitariaData} layout="vertical" margin={{ left: 10, right: 40, top: 5, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                    <XAxis type="number" tick={{ fill: 'var(--text-secondary)', fontSize: 10 }} />
                    <YAxis type="category" dataKey="name" tick={{ fill: 'var(--text-secondary)', fontSize: 9 }} width={98} interval={0} />
                    <Tooltip
                      contentStyle={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)', borderRadius: 8 }}
                      itemStyle={{ color: 'var(--text-primary)' }}
                      labelStyle={{ color: 'var(--text-primary)' }}
                    />
                    <Bar dataKey="si" name="Sí" fill="#10b981" radius={[0, 4, 4, 0]}>
                      <LabelList dataKey="si" position="right" fill="var(--text-secondary)" fontSize={9} fontWeight="bold" />
                    </Bar>
                    <Bar dataKey="no" name="No" fill="#ef4444" radius={[0, 4, 4, 0]}>
                      <LabelList dataKey="no" position="right" fill="var(--text-secondary)" fontSize={9} fontWeight="bold" />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center">
                  <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Sin respuestas registradas</span>
                </div>
              )}
            </div>
            <p className="text-[10px] mt-3 leading-normal" style={{ color: 'var(--text-muted)' }}>
              Respuestas de los regantes encuestados · verde Sí, rojo No
            </p>
          </div>
        </div>
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Método de Riego */}
        <div
          className="rounded-xl border p-4"
          style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)', boxShadow: 'var(--shadow-card)' }}
        >
          <h3 className="text-sm font-semibold mb-4 flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
            <Droplets className="w-4 h-4 text-cyan-400" />
            Método de Riego (promedio %)
          </h3>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={metodoRiego}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={4}
                dataKey="value"
                label={({ name, value }) => `${name}: ${value}%`}
              >
                {metodoRiego.map((entry, index) => (
                  <Cell key={index} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)', borderRadius: 8 }}
                itemStyle={{ color: 'var(--text-primary)' }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
        {/* Cultivos más frecuentes */}
        <div
          className="rounded-xl border p-4"
          style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)', boxShadow: 'var(--shadow-card)' }}
        >
          <h3 className="text-sm font-semibold mb-4 flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
            <Sprout className="w-4 h-4 text-emerald-400" />
            Cultivos Más Frecuentes
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={cultivosTop} margin={{ left: 10, right: 10, top: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
              <XAxis dataKey="name" tick={{ fill: 'var(--text-secondary)', fontSize: 9 }} angle={-45} textAnchor="end" height={60} />
              <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)', borderRadius: 8 }}
                itemStyle={{ color: 'var(--text-primary)' }}
              />
              <Bar dataKey="value" name="Registros" fill="#22c55e" radius={[4, 4, 0, 0]}>
                {cultivosTop.map((_, index) => (
                  <Cell key={index} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                ))}
                <LabelList dataKey="value" position="insideTop" fill="#ffffff" fontSize={10} fontWeight="bold" />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ── Seguimiento interno del equipo (v4.8) ──
          Los dos gráficos que miden al equipo — quién levantó cada ficha y el
          avance día a día — quedan fuera de la vista del contratante por
          pedido suyo del 9-ago. Es ocultamiento de pantalla, no de datos: el
          GeoJSON completo lo sigue descargando cualquier usuario con sesión,
          igual que antes. Si algún día hiciera falta que el cliente no pueda
          ni reconstruirlo, hay que filtrar en el export, no aquí. */}
      {esInterno && (
        <div className="space-y-3">
          <h3 className="text-sm font-bold tracking-wide uppercase text-slate-400 flex items-center gap-2">
            <Users className="w-4 h-4" />
            Seguimiento del Equipo
            <span className="text-[9px] font-bold px-2 py-0.5 rounded-full bg-slate-500/10 text-slate-400 border border-slate-500/20 normal-case tracking-normal">
              Solo equipo consultor
            </span>
          </h3>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Fichas por Técnico */}
            <div
              className="rounded-xl border p-4"
              style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)', boxShadow: 'var(--shadow-card)' }}
            >
              <h3 className="text-sm font-semibold mb-4 flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                <Users className="w-4 h-4 text-blue-400" />
                Fichas por Técnico
              </h3>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={fichasPorTecnico} layout="vertical" margin={{ left: 80, right: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                  <XAxis type="number" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                  <YAxis type="category" dataKey="nombre" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} width={80} />
                  <Tooltip
                    contentStyle={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)', borderRadius: 8 }}
                    itemStyle={{ color: 'var(--text-primary)' }}
                    labelStyle={{ color: 'var(--text-primary)' }}
                  />
                  <Bar dataKey="principales" name="Fichas Investigadas" radius={[0, 4, 4, 0]}>
                    {fichasPorTecnico.map((entry, index) => {
                      const tecKey = Object.entries(TECNICOS).find(([, v]) => v.nombre === entry.nombre)?.[0];
                      return <Cell key={index} fill={tecKey ? getColorTecnico(tecKey) : PIE_COLORS[index % PIE_COLORS.length]} />;
                    })}
                    <LabelList dataKey="principales" position="insideRight" fill="#ffffff" fontSize={11} fontWeight="bold" />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Progreso temporal */}
            <div
              className="rounded-xl border p-4"
              style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)', boxShadow: 'var(--shadow-card)' }}
            >
              <h3 className="text-sm font-semibold mb-4 flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                <TrendingUp className="w-4 h-4 text-green-400" />
                Fichas Investigadas por Día
              </h3>
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={avancePorDia} margin={{ left: 10, right: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                  <XAxis dataKey="fecha" tick={{ fill: 'var(--text-secondary)', fontSize: 10 }} />
                  <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)', borderRadius: 8 }}
                    itemStyle={{ color: 'var(--text-primary)' }}
                    labelStyle={{ color: 'var(--text-primary)' }}
                  />
                  <Line type="monotone" dataKey="campo" stroke="#10b981" strokeWidth={2} dot={{ r: 3, fill: '#10b981' }} name="Fichas levantadas en campo" />
                  <Line type="monotone" dataKey="completadas" stroke="#06b6d4" strokeWidth={2} dot={{ r: 3, fill: '#06b6d4' }} name="Predios adicionales investigados" />
                </LineChart>
              </ResponsiveContainer>
              <p className="text-[10px] mt-2 leading-normal" style={{ color: 'var(--text-muted)' }}>
                <span style={{ color: '#10b981' }}>■</span> {totalCampoDiario.toLocaleString('es-EC')} fichas levantadas en campo
                {' · '}
                <span style={{ color: '#06b6d4' }}>■</span> {totalCompletadasDiario.toLocaleString('es-EC')} predios adicionales investigados, por su fecha de investigación
                {generadasEnBloque > 0 && (
                  <><br />Las {generadasEnBloque.toLocaleString('es-EC')} fichas adicionales de la Sección 7 no se cuentan en su fecha de creación — se generaron por script en un solo día —, sino en el día en que se investigó el predio.
                  {generadasEnBloque - totalCompletadasDiario > 0 && ` Quedan fuera del gráfico ${(generadasEnBloque - totalCompletadasDiario).toLocaleString('es-EC')} sin esa fecha registrada.`}</>
                )}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Charts Row 3 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Tenencia del predio */}
        <div
          className="rounded-xl border p-4"
          style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)', boxShadow: 'var(--shadow-card)' }}
        >
          <h3 className="text-sm font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>
            Tenencia del Predio
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={tenencia} cx="50%" cy="50%" innerRadius={40} outerRadius={75} dataKey="value"
                label={({ name, value }) => `${name}: ${value}`} paddingAngle={3}>
                {tenencia.map((_, i) => (
                  <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)', borderRadius: 8 }}
                itemStyle={{ color: 'var(--text-primary)' }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Por parroquia */}
        <div
          className="rounded-xl border p-4"
          style={{ background: 'var(--bg-card)', borderColor: 'var(--border-color)', boxShadow: 'var(--shadow-card)' }}
        >
          <h3 className="text-sm font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>
            Fichas por Parroquia
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={fichasPorParroquia} margin={{ left: 10, right: 10, top: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
              <XAxis dataKey="name" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
              <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)', borderRadius: 8 }}
                itemStyle={{ color: 'var(--text-primary)' }}
              />
              <Bar dataKey="value" name="Fichas" fill="#8b5cf6" radius={[4, 4, 0, 0]}>
                <LabelList dataKey="value" position="insideTop" fill="#ffffff" fontSize={10} fontWeight="bold" />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
