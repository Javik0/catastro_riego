// ═══════════════════════════════════════════════════════════
// Tipos TypeScript — Dashboard Catastro de Riego Cayambe
// Basados en la estructura real de data.gpkg (QField)
// ═══════════════════════════════════════════════════════════

import { Timestamp } from 'firebase/firestore';

// ── Utilidad para manejar fechas de Firestore de forma segura ──
export function safeToDate(value: unknown): Date {
  if (!value) return new Date();
  if (value instanceof Date) return value;
  if (value instanceof Timestamp) return value.toDate();
  if (typeof value === 'string' || typeof value === 'number') {
    const d = new Date(value);
    return isNaN(d.getTime()) ? new Date() : d;
  }
  // Firestore Timestamp-like object {seconds, nanoseconds}
  if (typeof value === 'object' && value !== null && 'seconds' in value) {
    const ts = value as { seconds: number; nanoseconds?: number };
    return new Date(ts.seconds * 1000 + (ts.nanoseconds || 0) / 1_000_000);
  }
  return new Date();
}

// ── Ficha de Predio (tabla principal — 524+ registros) ──
export interface FichaPredio {
  // IDs
  id: string;
  fid?: number;
  cod_poligono: string;
  num_predio: number;
  codigo_final: string;

  // Propietario
  propietario: string;
  apellidos: string;
  nombres: string;
  cedula: string;
  clave_catastral: string;
  parroquia: string;
  comunidad?: string;
  comunidad_original?: string;
  sector_investigacion?: string;
  sector: string;
  telefono_celular?: string;
  telefono_casa?: string;
  hijos_hombres?: number;
  hijos_mujeres?: number;
  tenencia_predio: string;
  nivel_instruccion: string;

  // Predio y Riego
  area_total: number;
  org_riego?: string;
  sector_comunidad?: string;
  canal?: string;
  caudal_valor?: number;
  caudal_tipo?: string;
  area_riego: number;
  area_sin_riego: number;
  frecuencia_riego?: string;
  metodo_gravedad_pct?: number;
  metodo_aspersion_pct?: number;
  metodo_goteo_pct?: number;
  dias_riego?: number;
  horas_turno?: number;
  valor_tarifa?: number;
  tipo_tarifa?: string;
  tiene_reservorio?: string;

  // Servicios y Ubicación
  agua_consumo?: boolean;
  energia_electrica?: boolean;
  material_construccion?: string;
  material_constr_otro?: string;
  cota_msnm?: number;
  coord_x_utm?: number;
  coord_y_utm?: number;

  // Producción
  soberania_aliment_pct?: number;
  act_productivas_pct?: number;
  actividad_productiva?: string;

  // Encuesta Comunitaria
  conoce_presa?: string;
  como_elige_dir?: string;
  como_elige_dir_otro?: string;
  nom_presidente?: string;
  operador_sector?: string;
  anios_sistema?: number;
  km_canal?: number;
  recibio_capacitacion?: string;
  le_gustaria_cap?: string;
  temas_capacitacion?: string;

  // Multimedia y Auditoría
  foto_predio?: string;
  observaciones?: string;
  creado_por: string;
  fecha_creacion: Date | Timestamp | string;
  dispositivo?: string;
  precision_gps?: number;

  // Ficha Hija (v4.3 — generadas desde Sección 7 "Otros Predios")
  ficha_madre_id?: string;         // UUID de la ficha madre (null si es principal)
  es_ficha_hija?: boolean;         // true si fue generada automáticamente
  estado_investigacion?: 'pendiente_produccion' | 'completada' | 'en_revision' | string;
  completado_por?: string;         // Técnico que completó la Sección 4
  fecha_completado?: string;
  origen_datos?: 'campo' | 'auto_seccion7' | 'encuesta_web' | 'imputado' | string;

  // Geometría (para el mapa)
  geo?: { lat: number; lng: number };
  _geojson?: { type: string; coordinates: [number, number] };
}

// ── Helpers de Ficha Hija (v4.3) ──
// El GeoJSON exporta booleanos como 1/0, por eso se aceptan ambos formatos.
export function esFichaHija(f: FichaPredio): boolean {
  return f.es_ficha_hija === true || (f.es_ficha_hija as unknown) === 1;
}

export function esHijaPendiente(f: FichaPredio): boolean {
  return esFichaHija(f) && (f.estado_investigacion || 'pendiente_produccion') !== 'completada';
}

export function esHijaCompletada(f: FichaPredio): boolean {
  return esFichaHija(f) && f.estado_investigacion === 'completada';
}

// ── Cultivo Agrícola (tabla hija — 905+ registros) ──
export interface CultivoAgricola {
  id_cultivo: string;
  ficha_id: string;
  tipo_cultivo: string;
  tipo_cultivo_otro?: string;
  superficie_m2?: number;
  ref_area_predio?: number;
  es_principal?: boolean;
  es_autoconsumo?: boolean;
  es_mercado?: boolean;
  es_agroindustria?: boolean;
  es_exportacion?: boolean;
}

// ── Animal / Especie (tabla hija — 713+ registros) ──
export interface AnimalEspecie {
  id_animal: string;
  ficha_id: string;
  especie: string;
  especie_otro?: string;
  cantidad: number;
  es_autoconsumo?: boolean;
  es_mercado?: boolean;
  es_agroindustria?: boolean;
  es_exportacion?: boolean;
}

// ── Predio Adicional (tabla hija — 114+ registros) ──
export interface PredioAdicional {
  id_adicional: string;
  ficha_id: string;
  clave_catastral_otro: string;
  area_total_otro?: number;
  area_lote_asignado_otro?: number;
  area_riego_otro?: number;
  area_sin_riego_otro?: number;
  tiene_observaciones?: boolean;
  observaciones_otro?: string;
  ficha_hija_generada_id?: string; // UUID de la ficha hija generada (v4.3, trazabilidad)
}

// ── Polígono del Catastro Rural ──
export interface PoligonoCatastro {
  fid: number;
  clave_cata: string;
  area_predi: number;
  forma_de_a?: string;
  uso_habita?: string;
  cobertura_?: string;
  CATASTRO_U?: string; // Apellidos
  CATASTRO_1?: string; // Nombres
  CATASTRO_2?: string; // Cédula
  CATASTRO_3?: string;
  CATASTRO_4?: string; // Comunidad
}

// ── Parroquia ──
export interface Parroquia {
  fid: number;
  nombre: string;
  cod_catast: string;
  area_ha: number;
  area_km2: number;
}

// ── Autenticación ──
export type UserRole = 'admin' | 'cliente' | 'tecnico';

export interface UserProfile {
  uid: string;
  email: string;
  nombre: string;
  rol: UserRole;
}

export interface EncuestaPublica {
  id: string;
  fecha_envio: string; // ISO string
  estado: 'pendiente' | 'procesada' | 'rechazada';
  observaciones?: string;
  procesado_por?: string; // Técnico/Admin que la procesó
  fecha_procesado?: string; // ISO string
  
  // Respuestas Pestaña 1
  clave_catastral: string;
  cedula: string;
  apellidos: string;
  nombres: string;
  comunidad: string;
  parroquia: string;
  sector_investigacion: string;
  telefono_celular: string;
  hijos_hombres: number;
  hijos_mujeres: number;
  tenencia_predio: string;
  nivel_instruccion: string;
  tiene_construccion: boolean;
  
  // Riego y reservorio
  area_riego?: number;
  tiene_reservorio?: string;
  metodo_gravedad_pct?: number;
  metodo_aspersion_pct?: number;
  metodo_goteo_pct?: number;
  
  // Respuestas Pestaña 3
  agua_consumo: boolean;
  energia_electrica: boolean;
  material_construccion: string;
  material_constr_otro?: string;
  
  // Respuestas Pestaña 4
  cultivos: { tipo_cultivo: string; tipo_cultivo_otro?: string; superficie_m2: number; es_principal: boolean }[];
  animales: { especie: string; especie_otro?: string; cantidad: number }[];
  soberania_aliment_pct: number;
  act_productivas_pct: number;
  actividad_productiva: string;
  
  // Respuestas Pestaña 7 (Otros predios)
  predios_adicionales: { clave_catastral_otro: string; area_riego_otro: number }[];
}

// ── Filtros del Dashboard ──
export interface FiltrosState {
  parroquia: string;
  sector: string;
  sectorInv: string;
  tecnico: string;
  comunidad: string;
  fechaDesde: string;
  fechaHasta: string;
  busqueda: string;
}

// ── Estadísticas Resumen ──
export interface EstadisticasResumen {
  totalFichas: number;
  totalPoligonos: number;
  totalCultivos: number;
  totalAnimales: number;
  totalPrediosAdicionales: number;
  areaTotal: number;
  areaRiego: number;
  areaSinRiego: number;
  tecnicosActivos: number;
  fichasPorParroquia: Record<string, number>;
  fichasPorTecnico: Record<string, number>;
  fichasPorFecha: Record<string, number>;
  metodoRiego: { gravedad: number; aspersion: number; goteo: number };
  cultivosFrecuentes: Record<string, number>;
  tenenciaPredioCounts: Record<string, number>;
}

// ── GeoJSON helpers ──
export interface GeoJSONFeature {
  type: 'Feature';
  properties: Record<string, unknown>;
  geometry: {
    type: string;
    coordinates: unknown;
  };
}

export interface GeoJSONCollection {
  type: 'FeatureCollection';
  features: GeoJSONFeature[];
}
