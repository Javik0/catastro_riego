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

// ── Comunidades que quedaron fuera de la investigación ──
// No correspondían al sistema y no se levantó ninguna ficha en ellas, así que
// JAVIKO decidió (2026-07-30) sacarlas TAMBIÉN del avance: quedaron fuera del
// alcance del contrato, de modo que sus 470 comuneros no deben pesar en el
// denominador. Salen de los selectores y de los cálculos de cobertura.
// Sus metas siguen declaradas en META_COMUNEROS como referencia histórica,
// pero nadie las suma porque los reportes iteran COMUNIDADES_POR_SECTOR_FILTRO.
export const COMUNIDADES_SIN_INVESTIGAR: ReadonlySet<string> = new Set([
  'AVELLANEDA',
  'MATÍAS IMBAGO',
  'SAN VICENTE DE GUAYLLABAMBA',
  'SR. COLOMA',
  'SR. HERNÁN TIMPE',
  'HDA. SAN FRANSISCO',
]);

// ── Comunidades Unificadas Oficiales (Depuradas de QField) ──
// Catálogo COMPLETO del padrón. Los selectores no lo usan directamente: usan
// COMUNIDADES, que se deriva quitando las sin investigar. Mantener dos listas a
// mano es cómo SAN VICENTE DE GUAYLLABAMBA se quedó en el selector cuando ya se
// había depurado del resto.
export const COMUNIDADES_TODAS = [
  'ALPAKA',
  'ASOC. PITANA BAJO',
  'ASOC. SAN VICENTE ALTO',
  'ASOC. SAN VICENTE BAJO',
  'ASOCIACIÓN 17 DE JUNIO',
  'ASOCIACIÓN POROTOG',
  'ASOCIACIÓN ROSALÍA',
  'ASOCIACIÓN SAN PEDRO',
  'AVELLANEDA',
  'CANGAHUA PUNGO',
  'CARRERA',
  'CHAMBITOLA',
  'CHAUPIESTANCIA',
  'CHINCHINLOMA',
  'COCHAPAMBA',
  'COMUNA IZACATA',
  'COMUNA POROTOG',
  'CORDILLERAS DE LOS ANDES',
  'CUARTO LOTE',
  'EL MANZANO',
  'HDA. GUANGUILQUI',
  'HDA. SAN FRANSISCO',
  'IZACATA GRANDE',
  'JESÚS GRAN PODER',
  'JUNTA SAN LUIS',
  'LA CANDELARIA',
  'LA LIBERTAD',
  'LARCACHACA',
  'LOMA GORDA',
  'LOS ANDES IZACATA',
  'MATÍAS IMBAGO',
  'MILAGRO',
  'MONTESERRÍN ALTO',
  'OTONCITO',
  'PAMBAMARCA',
  'PAMBAMARQUITO',
  'PITANA ALTO',
  'PROMEJ. PITANA BAJO',
  'PUCARÁ',
  'PUEBLO DE ASCÁZUBI',
  'PUEBLO DE OTÓN',
  'SAN ANTONIO',
  'SAN JACINTO',
  'SAN JOSÉ',
  'SAN VICENTE DE GUAYLLABAMBA',
  'SANTA BÁRBARA',
  'SANTA MARIANITA DE PINGULMI',
  'SANTA ROSA DE PACCHA',
  'SANTA ROSA DE PINGULMI',
  'SR. COLOMA',
  // Renombrada desde 'MONTESERÍN BAJO' (JAVIKO, 2026-07-30). Ver
  // RENOMBRES_PRESENTACION en scripts/comunidades_canon.py: el dato de campo
  // conserva el nombre original, solo cambia lo que se muestra.
  'SR. COLOMA MONTESERRIN BAJO',
  'SR. HERNÁN TIMPE',
] as const;

/** Lo que se ofrece en los selectores: el catálogo menos las sin investigar. */
export const COMUNIDADES: readonly string[] = COMUNIDADES_TODAS.filter(
  (c) => !COMUNIDADES_SIN_INVESTIGAR.has(c)
);

// ── Mapeo oficial de Comunidades por Sector de Investigación (QField) ──
// Es el PADRÓN OFICIAL COMPLETO: incluye a propósito las comunidades sin
// investigar, porque App.tsx lo usa para decidir a qué sector pertenece cada
// ficha y ahí sí hacen falta todas. Los selectores y los cálculos de cobertura
// usan COMUNIDADES_POR_SECTOR_FILTRO, que las excluye.
//
// Una comunidad NO debe repetirse en dos sectores: App.tsx los recorre en orden
// y se queda con el primero, así que la duplicada quedaba asignada al sector
// equivocado y su meta se contaba dos veces en el total global. Le pasaba a
// ASOCIACIÓN ROSALÍA, que estaba en Sector 2 y Sector 3 y mandaba sus 47 fichas
// al Sector 2 cuando en campo son del Sector 3.
export const COMUNIDADES_POR_SECTOR: Record<string, string[]> = {
  'Sector 1': [
    "ASOCIACIÓN 17 DE JUNIO", "ASOCIACIÓN POROTOG", "AVELLANEDA",
    "CARRERA", "CHAMBITOLA", "COCHAPAMBA", "COMUNA IZACATA",
    "COMUNA POROTOG", "CORDILLERAS DE LOS ANDES", "IZACATA GRANDE",
    "JESÚS GRAN PODER", "LA CANDELARIA", "LA LIBERTAD",
    "LARCACHACA", "LOMA GORDA", "LOS ANDES IZACATA",
    "MATÍAS IMBAGO", "MILAGRO", "SAN ANTONIO", "SAN JACINTO",
    "SAN JOSÉ", "SANTA BÁRBARA"
  ],
  'Sector 2': [
    // ASOCIACIÓN ROSALÍA salió de aquí: no correspondía al Sector 2 y no se
    // investigó (JAVIKO, 2026-07-30). Sus 47 fichas son del Sector 3.
    "ALPAKA", "ASOC. PITANA BAJO", "ASOC. SAN VICENTE ALTO",
    "ASOC. SAN VICENTE BAJO", "ASOCIACIÓN SAN PEDRO",
    "CUARTO LOTE", "PAMBAMARCA", "PITANA ALTO", "PROMEJ. PITANA BAJO",
    "PUCARÁ", "SANTA MARIANITA DE PINGULMI", "SANTA ROSA DE PACCHA",
    "SANTA ROSA DE PINGULMI"
  ],
  'Sector 3': [
    "ASOCIACIÓN ROSALÍA", "CANGAHUA PUNGO", "CHAUPIESTANCIA",
    "CHINCHINLOMA", "EL MANZANO", "HDA. GUANGUILQUI",
    "HDA. SAN FRANSISCO", "JUNTA SAN LUIS",
    "MONTESERRÍN ALTO", "OTONCITO", "PAMBAMARQUITO", "PUEBLO DE ASCÁZUBI",
    "PUEBLO DE OTÓN", "SAN VICENTE DE GUAYLLABAMBA", "SR. COLOMA",
    "SR. COLOMA MONTESERRIN BAJO", "SR. HERNÁN TIMPE"
  ]
};

// El padrón oficial menos las comunidades fuera de alcance. Lo usan TANTO los
// selectores COMO los cálculos de meta y cobertura, para que el porcentaje se
// mida solo contra lo que de verdad había que investigar.
export const COMUNIDADES_POR_SECTOR_FILTRO: Record<string, string[]> =
  Object.fromEntries(
    Object.entries(COMUNIDADES_POR_SECTOR).map(([sector, comunidades]) => [
      sector,
      comunidades.filter((c) => !COMUNIDADES_SIN_INVESTIGAR.has(c)),
    ])
  );

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



