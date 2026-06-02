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
  
  'u0_a200': { nombre: 'Melanie2', color: '#a855f7' },
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
  'Permanente', 'Mensual', 'Quincenal', 'Semanal',
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
export const PROJECT_SUBTITLE = 'PADRÓN DE USUARIOS: SISTEMA DE RIEGO COMUNITARIO GUANGUILQUI POROTOG';
export const PROJECT_LOCATION = 'Provincia Pichincha — Cantón Cayambe';

export const LOGO_PICHINCHA = '/logo-izq.png';
export const LOGO_CONSORCIO = '/logo-der.png';

// ── Comunidades Unificadas Oficiales (Depuradas de QField) ──
export const COMUNIDADES = [
  'ASOCIACIÓN 17 DE JUNIO',
  'ASOCIACIÓN POROTOG',
  'AVELLANEDA',
  'CARRERA',
  'CHAMBITOLA',
  'COCHAPAMBA',
  'COMUNA INSACATA',
  'COMUNA POROTOG',
  'CORDILLERAS DE LOS ANDES',
  'INSACATA GRANDE',
  'JESÚS GRAN PODER',
  'LA CANDELARIA',
  'LA LIBERTAD',
  'LARCACHACA',
  'LOMA GORDA',
  'LOS ANDES INSACATA',
  'MATÍAS IMBAGO',
  'MILAGRO',
  'SAN ANTONIO',
  'SAN JACINTO',
  'SAN JOSÉ',
  'SANTA BÁRBARA',
] as const;

