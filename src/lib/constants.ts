// ═══════════════════════════════════════════════════════════
// Constantes — Dashboard Catastro de Riego Cayambe
// Todos los catálogos y mapeos basados en el script QGIS v4.2
// ═══════════════════════════════════════════════════════════

// ── Técnicos investigadores (colores idénticos a QGIS) ──
export const TECNICOS: Record<string, { nombre: string; color: string }> = {
  'u0_a314': { nombre: 'Melany Jara', color: '#FF0000' },
  'u0_a319': { nombre: 'Melany Jara', color: '#FF0000' },
  'jvk-editor': { nombre: 'Melany Jara', color: '#FF0000' },
  
  'u0_a504': { nombre: 'Adriana Cuascota', color: '#0000FF' },
  'jvk-editor6': { nombre: 'Adriana Cuascota', color: '#0000FF' },
  
  'u0_a279': { nombre: 'Huguito Ipial', color: '#00FF00' },
  'jvk-editor2': { nombre: 'Huguito Ipial', color: '#00FF00' },
  
  'u0_a70':  { nombre: 'Pablo Barrionuevo', color: '#800080' },
  'jvk-editor5': { nombre: 'Pablo Barrionuevo', color: '#800080' },
  
  'u0_a330': { nombre: 'Mayra Benavides', color: '#00FFFF' },
  'mayralisseth201': { nombre: 'Mayra Benavides', color: '#00FFFF' },
  
  'u0_a362': { nombre: 'Martha Simbaña', color: '#FFFF00' },
  'u0_a335': { nombre: 'Martha Simbaña', color: '#FFFF00' },
  'jvk-editor4': { nombre: 'Martha Simbaña', color: '#FFFF00' },
  
  'u0_a2':   { nombre: 'JVK-DIGITALIZACION', color: '#FFA500' },
  'jvk-digitalizacion': { nombre: 'JVK-DIGITALIZACION', color: '#FFA500' },
  
  'u0_a302': { nombre: 'Dylan Chavez', color: '#111111' },
  'jvk-editor3': { nombre: 'Dylan Chavez', color: '#111111' },
  
  // Melany Recalde — usa dos cuentas: jvk-corp en PAMBAMARCA y u0_a200 (que
  // figuraba como "Melanie2") en SAN ANTONIO. Confirmado por JAVIKO que es la
  // misma persona, así que sus 42 + 17 fichas se le acreditan juntas.
  'jvk-corp': { nombre: 'Melany Recalde', color: '#FF00FF' },
  'u0_a200': { nombre: 'Melany Recalde', color: '#FF00FF' },
};

export function getNombreTecnico(username: string): string {
  return TECNICOS[username]?.nombre ?? username;
}

export function getColorTecnico(username: string): string {
  return TECNICOS[username]?.color ?? '#999999';
}

// ── Parroquias del cantón Cayambe ──
export const PARROQUIAS = [
  'CANGAHUA',
  'OTÓN',
  'CUSUBAMBA',
  'ASCÁZUBI',
] as const;

// ── Sectores de riego ──
export const SECTORES = [
  'Porotog',
  'Guanguilqui',
  'Guang-Porotog',
] as const;

// ── Tipos de cultivo (ficha papel) ──
export const TIPOS_CULTIVO = [
  'Pasto mejorado', 'Pasto no mejorado', 'Cebolla',
  'Papas', 'Cebada', 'Trigo', 'Maíz', 'Habas',
  'Hortalizas', 'Frijol', 'Flores', 'Frutales',
  'Melloco', 'Chocho', 'Quinua', 'Baldío',
  'Monte', 'Bosque', 'Otros',
] as const;

// ── Especies pecuarias ──
export const ESPECIES_ANIMALES = [
  'Cuyes / Conejos', 'Pollos de engorde',
  'Gallinas ponedoras', 'Gallinas de campo',
  'Ovejas / Cabras', 'Porcino (Chanchos)',
  'Vacas en producción', 'Vacas secas',
  'Vaconas', 'Terneras', 'Terneros',
  'Toretes', 'Toros', 'Equinos', 'Otros',
] as const;

// ── Frecuencia de riego ──
export const FRECUENCIAS_RIEGO = [
  'Permanente', 'Mensual', 'Quincenal', 'Semanal', 'No tiene riego',
] as const;

// ── Tipos de tarifa ──
export const TIPOS_TARIFA = [
  'por turno', 'fijo mensual', 'fijo anual', 'por hectárea',
] as const;

// ── Material de construcción ──
export const MATERIALES_CONSTRUCCION = [
  'HORMIGÓN ARMADO', 'ESTRUCTURA METÁLICA',
  'LADRILLO', 'BLOQUE', 'MADERA', 'MIXTA',
  'ADOBE', 'TAPIA', 'Otros',
] as const;

// ── Niveles de instrucción ──
export const NIVELES_INSTRUCCION = [
  'Ninguno', 'Alfabetizado', 'Primaria', 'Secundaria', 'Superior',
] as const;

// ── Tenencia del predio ──
export const TENENCIA_PREDIO = [
  'Escritura', 'Sin Escritura',
] as const;

// ── Tipo de caudal ──
export const TIPOS_CAUDAL = [
  'Recibe la Comunidad', 'Recibe individual',
] as const;

// ── Aliases de campos (etiquetas legibles del QGIS) ──
export const ALIASES: Record<string, string> = {
  id: 'ID (Auto)',
  cod_poligono: 'Código Polígono Base',
  num_predio: 'N° Predio',
  codigo_final: 'Código del Predio',
  propietario: 'Propietario (completo)',
  apellidos: 'Apellidos',
  nombres: 'Nombres',
  cedula: 'Cédula de Identidad',
  clave_catastral: 'Clave Catastral',
  parroquia: 'Parroquia',
  comunidad: 'Comunidad',
  telefono_celular: 'Teléfono Celular',
  telefono_casa: 'Teléfono Casa',
  hijos_hombres: 'Hijos (Hombres)',
  hijos_mujeres: 'Hijos (Mujeres)',
  sector: 'Sector',
  tenencia_predio: 'Tenencia del Predio',
  nivel_instruccion: 'Nivel de Instrucción',
  area_total: 'Área Total (m²)',
  org_riego: 'Organización de Riego',
  sector_comunidad: 'Sector en la Comunidad',
  canal: 'Canal (Nombre)',
  caudal_valor: 'Caudal (l/s)',
  caudal_tipo: 'Tipo de Caudal',
  area_riego: 'Área con Riego (m²)',
  area_sin_riego: 'Área sin Riego (m²)',
  frecuencia_riego: 'Frecuencia de Riego',
  metodo_gravedad_pct: 'Gravedad (%)',
  metodo_aspersion_pct: 'Aspersión (%)',
  metodo_goteo_pct: 'Goteo (%)',
  dias_riego: 'N° Días de Riego',
  horas_turno: 'Horas por Turno',
  valor_tarifa: 'Valor Tarifa ($)',
  tipo_tarifa: 'Tipo de Tarifa',
  tiene_reservorio: '¿Tiene Reservorio?',
  agua_consumo: 'Agua Consumo Humano',
  energia_electrica: 'Energía Eléctrica',
  material_construccion: 'Material de Construcción',
  cota_msnm: 'COTA (msnm)',
  coord_x_utm: 'Coordenada X (UTM)',
  coord_y_utm: 'Coordenada Y (UTM)',
  soberania_aliment_pct: 'Soberanía Alimentaria (%)',
  act_productivas_pct: 'Act. Productivas (%)',
  actividad_productiva: 'Actividad Productiva',
  conoce_presa: '¿Conoce el Proyecto Presa?',
  como_elige_dir: '¿Cómo se elige la directiva?',
  nom_presidente: 'Presidente Junta de Agua',
  operador_sector: 'Operador del Sistema',
  anios_sistema: 'Años del Sistema',
  km_canal: 'Km del Canal Principal',
  recibio_capacitacion: '¿Recibió Capacitación?',
  le_gustaria_cap: '¿Le gustaría Capacitación?',
  temas_capacitacion: 'Temas de Capacitación',
  foto_predio: 'Fotografía Anexo',
  observaciones: 'Observaciones',
  creado_por: 'Investigado por',
  fecha_creacion: 'Fecha de Registro',
  dispositivo: 'Dispositivo',
  precision_gps: 'Precisión GPS (m)',
};

// ── Proyecto ──
export const PROJECT_TITLE = 'ESTUDIO DEFINITIVO DE PRESA EN EL RIO POROTOG';
export const PROJECT_SUBTITLE = 'PADRÓN DE USUARIOS: SISTEMA DE RIEGO COMUNITARIO GUANGUILQUÍ–POROTOG';
export const PROJECT_SUBTITLE_ALCANCE = 'Ficha de empadronamiento predial y productivo – línea base censal';
export const PROJECT_LOCATION = 'Provincia Pichincha — Cantón Cayambe';

export const LOGO_PICHINCHA = '/logo-izq.png';
export const LOGO_CONSORCIO = '/logo-der.png';

// ── Catálogo oficial de comunidades del sistema ──
// Fuente: "GUANGUILQUI - POROTOG · SECTORES Y COMUNIDADES", listado que envió
// Armando el 2026-07-31. Ese documento fija el ORDEN y la NUMERACIÓN oficiales
// del sistema de riego, que no son alfabéticos sino de recorrido del canal.
//
// Cada entrada lleva dos nombres, y la distinción importa:
//   · `oficial` — como aparece en el documento de Armando. Es lo que se MUESTRA.
//   · `datos`   — como está escrito en el campo `comunidad` del data.gpkg. Es lo
//                 que se COMPARA. Nunca cambiarlo sin migrar las fichas.
//
// SAN VICENTE DE GUAYLLABAMBA (51) queda oculta: figura en el listado pero
// JAVIKO confirmó con Armando que no se investiga (2026-07-31), así que se
// muestran 50 de las 51. SR. COLOMA se eliminó del catálogo porque no aparece
// en el listado oficial y no tenía ninguna ficha levantada.
export interface Comunidad {
  /** Número oficial en el listado del sistema (1-51). */
  n: number;
  sector: string;
  /** Nombre del listado oficial — el que ve el usuario. */
  oficial: string;
  /** Nombre en el campo `comunidad` del data.gpkg — el que se compara. */
  datos: string;
  /** true = no se investiga; sale de selectores y del cálculo de avance. */
  oculta?: boolean;
}

export const CATALOGO_COMUNIDADES: readonly Comunidad[] = [
  { n: 1, sector: 'Sector 1', oficial: 'LARCACHACA', datos: 'LARCACHACA' },
  { n: 2, sector: 'Sector 1', oficial: 'LA LIBERTAD', datos: 'LA LIBERTAD' },
  { n: 3, sector: 'Sector 1', oficial: 'SAN ANTONIO', datos: 'SAN ANTONIO' },
  { n: 4, sector: 'Sector 1', oficial: 'SAN JOSE', datos: 'SAN JOSÉ' },
  { n: 5, sector: 'Sector 1', oficial: 'MILAGRO', datos: 'MILAGRO' },
  { n: 6, sector: 'Sector 1', oficial: 'CHAMBITOLA', datos: 'CHAMBITOLA' },
  { n: 7, sector: 'Sector 1', oficial: 'LA CANDELARIA', datos: 'LA CANDELARIA' },
  { n: 8, sector: 'Sector 1', oficial: 'CARRERA', datos: 'CARRERA' },
  { n: 9, sector: 'Sector 1', oficial: 'COCHAPAMBA', datos: 'COCHAPAMBA' },
  { n: 10, sector: 'Sector 1', oficial: 'JESUS DE GRAN PODER', datos: 'JESÚS GRAN PODER' },
  { n: 11, sector: 'Sector 1', oficial: 'AS. SANTA BARBARA', datos: 'SANTA BÁRBARA' },
  { n: 12, sector: 'Sector 1', oficial: 'ASO. POROTOG', datos: 'ASOCIACIÓN POROTOG' },
  { n: 13, sector: 'Sector 1', oficial: 'COMUNA POROTOG', datos: 'COMUNA POROTOG' },
  { n: 14, sector: 'Sector 1', oficial: 'ASO. 17 DE JUNIO', datos: 'ASOCIACIÓN 17 DE JUNIO' },
  { n: 15, sector: 'Sector 1', oficial: 'ELIOT AVELLANEDA', datos: 'AVELLANEDA' },
  { n: 16, sector: 'Sector 1', oficial: 'CORDILLERA LOS ANDES', datos: 'CORDILLERAS DE LOS ANDES' },
  { n: 17, sector: 'Sector 1', oficial: 'COMUNA JURIDICA IZACATA', datos: 'COMUNA IZACATA' },
  { n: 18, sector: 'Sector 1', oficial: 'IZACATA GRANDE', datos: 'IZACATA GRANDE' },
  { n: 19, sector: 'Sector 1', oficial: 'LOS ANDES IZACTA', datos: 'LOS ANDES IZACATA' },
  { n: 20, sector: 'Sector 1', oficial: 'ASO. LOMA GORDA', datos: 'LOMA GORDA' },
  { n: 21, sector: 'Sector 1', oficial: 'ASO. SAN JACINTO', datos: 'SAN JACINTO' },
  { n: 22, sector: 'Sector 1', oficial: 'MATIAS IMBAGO', datos: 'MATÍAS IMBAGO' },

  { n: 23, sector: 'Sector 2', oficial: 'CUARTO LOTE', datos: 'CUARTO LOTE' },
  { n: 24, sector: 'Sector 2', oficial: 'ASO. SAN VICENTE BAJO', datos: 'ASOC. SAN VICENTE BAJO' },
  { n: 25, sector: 'Sector 2', oficial: 'STA. ROSA DE PACCHA', datos: 'SANTA ROSA DE PACCHA' },
  { n: 26, sector: 'Sector 2', oficial: 'ASO. SAN VICENTE ALTO', datos: 'ASOC. SAN VICENTE ALTO' },
  { n: 27, sector: 'Sector 2', oficial: 'PUCARA', datos: 'PUCARÁ' },
  { n: 28, sector: 'Sector 2', oficial: 'ASO. SAN PEDRO', datos: 'ASOCIACIÓN SAN PEDRO' },
  { n: 29, sector: 'Sector 2', oficial: 'PITANA ALTO', datos: 'PITANA ALTO' },
  { n: 30, sector: 'Sector 2', oficial: 'ALPAKA', datos: 'ALPAKA' },
  { n: 31, sector: 'Sector 2', oficial: 'ASO. PITANA BAJO', datos: 'ASOC. PITANA BAJO' },
  { n: 32, sector: 'Sector 2', oficial: 'PRO MEJORAS PITANA BAJO', datos: 'PROMEJ. PITANA BAJO' },
  { n: 33, sector: 'Sector 2', oficial: 'STA. ROSA DE PINGULMI', datos: 'SANTA ROSA DE PINGULMI' },
  { n: 34, sector: 'Sector 2', oficial: 'STA. MARIANITA DE PINGULMI', datos: 'SANTA MARIANITA DE PINGULMI' },
  { n: 35, sector: 'Sector 2', oficial: 'PAMBAMARCA', datos: 'PAMBAMARCA' },

  { n: 36, sector: 'Sector 3', oficial: 'OTONCITO', datos: 'OTONCITO' },
  { n: 37, sector: 'Sector 3', oficial: 'PAMBAMARQUITO', datos: 'PAMBAMARQUITO' },
  { n: 38, sector: 'Sector 3', oficial: 'HERNAN TIMPE', datos: 'SR. HERNÁN TIMPE' },
  { n: 39, sector: 'Sector 3', oficial: 'HDA. SAN FRANCISCO', datos: 'HDA. SAN FRANSISCO' },
  { n: 40, sector: 'Sector 3', oficial: 'MONTESERRIN ALTO', datos: 'MONTESERRÍN ALTO' },
  { n: 41, sector: 'Sector 3', oficial: 'CHAUPIESTANCIA', datos: 'CHAUPIESTANCIA' },
  { n: 42, sector: 'Sector 3', oficial: 'PUEBLO DE OTON', datos: 'PUEBLO DE OTÓN' },
  { n: 43, sector: 'Sector 3', oficial: 'CANGAHUAPUNGO', datos: 'CANGAHUA PUNGO' },
  { n: 44, sector: 'Sector 3', oficial: 'CHINCHIN LOMA', datos: 'CHINCHINLOMA' },
  { n: 45, sector: 'Sector 3', oficial: 'ASO. ROSALIA', datos: 'ASOCIACIÓN ROSALÍA' },
  { n: 46, sector: 'Sector 3', oficial: 'SR. COLOMA MONT. BAJO', datos: 'SR. COLOMA MONTESERRIN BAJO' },
  { n: 47, sector: 'Sector 3', oficial: 'HDA. GUANGULQUI', datos: 'HDA. GUANGUILQUI' },
  { n: 48, sector: 'Sector 3', oficial: 'PUEBLO DE ASCAZUBI', datos: 'PUEBLO DE ASCÁZUBI' },
  { n: 49, sector: 'Sector 3', oficial: 'ASO. EL MANZANO', datos: 'EL MANZANO' },
  { n: 50, sector: 'Sector 3', oficial: 'JUNTA ADMISIS. RIEGO SAN LUIS', datos: 'JUNTA SAN LUIS' },
  { n: 51, sector: 'Sector 3', oficial: 'SAN VICENTE DE GUAYLLABAMBA', datos: 'SAN VICENTE DE GUAYLLABAMBA', oculta: true },
];

/** Las que se investigan: 50 de las 51 del listado oficial. */
export const COMUNIDADES_VISIBLES: readonly Comunidad[] =
  CATALOGO_COMUNIDADES.filter((c) => !c.oculta);

const POR_DATOS = new Map(CATALOGO_COMUNIDADES.map((c) => [c.datos, c]));

/** "15. ELIOT AVELLANEDA" — número y nombre oficial para mostrar al usuario. */
export function etiquetaComunidad(nombreEnDatos: string): string {
  const c = POR_DATOS.get((nombreEnDatos || '').trim());
  return c ? `${c.n}. ${c.oficial}` : (nombreEnDatos || '');
}

/** Número oficial de una comunidad, para ordenar. 999 si no está catalogada. */
export function ordenComunidad(nombreEnDatos: string): number {
  return POR_DATOS.get((nombreEnDatos || '').trim())?.n ?? 999;
}

// ── Derivados: los nombres tal como están en los datos ──
// Se conservan estos nombres de constante porque son los que ya consumen el
// mapa, los reportes y la encuesta pública.

/** Comunidades que se ofrecen en los SELECTORES, en el orden oficial. */
export const COMUNIDADES: readonly string[] = COMUNIDADES_VISIBLES.map((c) => c.datos);

/** Catálogo COMPLETO, incluidas las que no se investigan. */
export const COMUNIDADES_TODAS: readonly string[] = CATALOGO_COMUNIDADES.map((c) => c.datos);

export const COMUNIDADES_SIN_INVESTIGAR: ReadonlySet<string> = new Set(
  CATALOGO_COMUNIDADES.filter((c) => c.oculta).map((c) => c.datos)
);

/**
 * Padrón oficial COMPLETO por sector. App.tsx lo usa para decidir a qué sector
 * pertenece cada ficha, y ahí hacen falta todas.
 *
 * Una comunidad NO debe repetirse en dos sectores: App.tsx los recorre en orden
 * y se queda con el primero, así que la duplicada quedaba asignada al sector
 * equivocado y su meta se contaba dos veces. Le pasaba a ASOCIACIÓN ROSALÍA,
 * que estaba en Sector 2 y Sector 3 y mandaba sus 47 fichas al Sector 2 cuando
 * en campo son del Sector 3.
 */
export const COMUNIDADES_POR_SECTOR: Record<string, string[]> =
  CATALOGO_COMUNIDADES.reduce((acc, c) => {
    (acc[c.sector] ||= []).push(c.datos);
    return acc;
  }, {} as Record<string, string[]>);

/**
 * Lo que se ofrece en los SELECTORES y lo que se mide en el AVANCE: el padrón
 * oficial menos las comunidades que no se investigan, en el orden del sistema.
 */
export const COMUNIDADES_POR_SECTOR_FILTRO: Record<string, string[]> =
  COMUNIDADES_VISIBLES.reduce((acc, c) => {
    (acc[c.sector] ||= []).push(c.datos);
    return acc;
  }, {} as Record<string, string[]>);

// ── Meta de comuneros planificados por comunidad (Catastro Oficial) ──
export const META_COMUNEROS: Record<string, number> = {
  // Sector 1
  "LARCACHACA": 103,
  "LA LIBERTAD": 125,
  "SAN ANTONIO": 95,
  "SAN JOSÉ": 120,
  "MILAGRO": 38,
  "ASOCIACIÓN 17 DE JUNIO": 32,
  "CHAMBITOLA": 120,
  "LA CANDELARIA": 170,
  "CARRERA": 280,
  "MATÍAS IMBAGO": 1,
  "COCHAPAMBA": 244,
  "JESÚS GRAN PODER": 56,
  "SANTA BÁRBARA": 6,
  "ASOCIACIÓN POROTOG": 48,
  "COMUNA POROTOG": 80,
  "CORDILLERAS DE LOS ANDES": 43,
  "COMUNA IZACATA": 65,
  "IZACATA GRANDE": 43,
  "LOS ANDES IZACATA": 48,
  "LOMA GORDA": 45,
  "SAN JACINTO": 6,
  
  // Sector 2
  "CUARTO LOTE": 46,
  "ASOC. SAN VICENTE BAJO": 80,
  "SANTA ROSA DE PACCHA": 46,
  "ASOC. SAN VICENTE ALTO": 59,
  "PUCARÁ": 231,
  "ASOCIACIÓN SAN PEDRO": 24,
  "PITANA ALTO": 99,
  // 15 era el catastro ANTES del fraccionamiento. Hoy ALPAKA son 492 lotes
  // (374 propietarios distintos), todos levantados. Con la meta vieja la
  // comunidad marcaba 3.280% y descuadraba todo el reporte de avance.
  "ALPAKA": 492,
  "ASOC. PITANA BAJO": 42,
  "PROMEJ. PITANA BAJO": 180,
  "SANTA ROSA DE PINGULMI": 117,
  "SANTA MARIANITA DE PINGULMI": 189,
  "PAMBAMARCA": 61,
  
  // Sector 3
  "OTONCITO": 66,
  "PAMBAMARQUITO": 100,
  "MONTESERRÍN ALTO": 27,
  "CHAUPIESTANCIA": 150,
  "PUEBLO DE OTÓN": 152,
  "CANGAHUA PUNGO": 147,
  "CHINCHINLOMA": 80,
  "ASOCIACIÓN ROSALÍA": 41,
  "SR. COLOMA": 16,
  // 118 comuneros del acta + las 4 fichas principales que se levantaron sobre
  // el mismo polígono (hacienda, comunidad, bosque productivo y páramo).
  // JAVIKO fijó la meta en 122 para que la comunidad cierre al 100% y no en
  // 103,4% (2026-07-30).
  "SR. COLOMA MONTESERRIN BAJO": 122,
  "HDA. GUANGUILQUI": 15,
  "PUEBLO DE ASCÁZUBI": 16,
  "EL MANZANO": 19,
  "JUNTA SAN LUIS": 33,
  "SAN VICENTE DE GUAYLLABAMBA": 453,
  
  // Comunidades sin datos meta pero existentes
  "AVELLANEDA": 0,
  "HDA. SAN FRANSISCO": 0,
  "SR. HERNÁN TIMPE": 0
};



