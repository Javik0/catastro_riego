// ═══════════════════════════════════════════════════════════
// Servicio Firestore — CRUD y queries para el Dashboard
// ═══════════════════════════════════════════════════════════

import {
  collection,
  doc,
  getDoc,
  getDocs,
  query,
  where,
  orderBy,
  addDoc,
  updateDoc,
  type DocumentData,
} from 'firebase/firestore';
import { db } from './firebaseConfig';
import { safeToDate, type FichaPredio, type CultivoAgricola, type AnimalEspecie, type PredioAdicional, type FiltrosState, type EstadisticasResumen, type EncuestaPublica } from './types';
import { getNombreTecnico, TECNICOS } from './constants';

// ── Colecciones ──
const fichasCol = () => collection(db, 'fichas_predios');
const prediosAdicCol = () => collection(db, 'predios_adicionales');

// ── Conversión de documento Firestore a tipo ──
function docToFicha(docData: DocumentData, docId: string): FichaPredio {
  const d = docData;
  return {
    ...d,
    id: d.id || docId,
    fecha_creacion: safeToDate(d.fecha_creacion),
    area_total: d.area_total ?? 0,
    area_riego: d.area_riego ?? 0,
    area_sin_riego: d.area_sin_riego ?? 0,
    propietario: d.propietario ?? `${d.apellidos ?? ''} ${d.nombres ?? ''}`.trim(),
    creado_por: d.creado_por ?? '',
    parroquia: d.parroquia ?? '',
    sector: d.sector ?? '',
    cedula: d.cedula ?? '',
    codigo_final: d.codigo_final ?? '',
    cod_poligono: d.cod_poligono ?? '',
    num_predio: d.num_predio ?? 0,
    apellidos: d.apellidos ?? '',
    nombres: d.nombres ?? '',
    clave_catastral: d.clave_catastral ?? '',
    tenencia_predio: d.tenencia_predio ?? '',
    nivel_instruccion: d.nivel_instruccion ?? '',
  } as FichaPredio;
}

// ── Obtener todas las fichas (con filtros opcionales) ──
export async function getFichas(filtros?: FiltrosState): Promise<FichaPredio[]> {
  let q = query(fichasCol(), orderBy('fecha_creacion', 'desc'));

  // Firestore tiene limitaciones con queries compuestas,
  // así que filtramos lo que podamos en servidor y el resto en cliente
  if (filtros?.parroquia) {
    q = query(fichasCol(), where('parroquia', '==', filtros.parroquia), orderBy('fecha_creacion', 'desc'));
  }

  const snapshot = await getDocs(q);
  let fichas = snapshot.docs.map((d) => docToFicha(d.data(), d.id));

  // Filtros en cliente
  if (filtros) {
    if (filtros.sector) {
      fichas = fichas.filter((f) => f.sector === filtros.sector);
    }
    if (filtros.tecnico) {
      fichas = fichas.filter((f) => f.creado_por === filtros.tecnico);
    }
    if (filtros.fechaDesde) {
      const desde = new Date(filtros.fechaDesde);
      fichas = fichas.filter((f) => safeToDate(f.fecha_creacion) >= desde);
    }
    if (filtros.fechaHasta) {
      const hasta = new Date(filtros.fechaHasta);
      hasta.setHours(23, 59, 59);
      fichas = fichas.filter((f) => safeToDate(f.fecha_creacion) <= hasta);
    }
    if (filtros.busqueda) {
      const q = filtros.busqueda.toLowerCase();
      fichas = fichas.filter(
        (f) =>
          f.propietario?.toLowerCase().includes(q) ||
          f.apellidos?.toLowerCase().includes(q) ||
          f.nombres?.toLowerCase().includes(q) ||
          f.cedula?.includes(q) ||
          f.codigo_final?.toLowerCase().includes(q) ||
          f.clave_catastral?.includes(q)
      );
    }
  }

  return fichas;
}

// ── Obtener ficha por ID ──
export async function getFichaById(id: string): Promise<FichaPredio | null> {
  const docRef = doc(db, 'fichas_predios', id);
  const docSnap = await getDoc(docRef);
  if (!docSnap.exists()) return null;
  return docToFicha(docSnap.data(), docSnap.id);
}

// ── Obtener cultivos de una ficha ──
export async function getCultivosByFicha(fichaId: string): Promise<CultivoAgricola[]> {
  const q = query(collection(db, 'fichas_predios', fichaId, 'cultivos'));
  const snapshot = await getDocs(q);
  return snapshot.docs.map((d) => ({ ...d.data(), id_cultivo: d.id } as CultivoAgricola));
}

// ── Obtener animales de una ficha ──
export async function getAnimalesByFicha(fichaId: string): Promise<AnimalEspecie[]> {
  const q = query(collection(db, 'fichas_predios', fichaId, 'animales'));
  const snapshot = await getDocs(q);
  return snapshot.docs.map((d) => ({ ...d.data(), id_animal: d.id } as AnimalEspecie));
}

// ── Obtener predios adicionales de una ficha ──
export async function getPrediosAdicionalesByFicha(fichaId: string): Promise<PredioAdicional[]> {
  const q = query(prediosAdicCol(), where('ficha_id', '==', fichaId));
  const snapshot = await getDocs(q);
  return snapshot.docs.map((d) => ({ ...d.data(), id_adicional: d.id } as PredioAdicional));
}

// ── Calcular estadísticas de todas las fichas ──
export function calcularEstadisticas(fichas: FichaPredio[]): EstadisticasResumen {
  const fichasPorParroquia: Record<string, number> = {};
  const fichasPorTecnico: Record<string, number> = {};
  const fichasPorFecha: Record<string, number> = {};
  const cultivosFrecuentes: Record<string, number> = {};
  const tenenciaPredioCounts: Record<string, number> = {};
  let areaTotal = 0, areaRiego = 0, areaSinRiego = 0;
  let gravedad = 0, aspersion = 0, goteo = 0;
  const tecnicosSet = new Set<string>();

  for (const f of fichas) {
    // Por parroquia
    const parr = f.parroquia || 'Sin parroquia';
    fichasPorParroquia[parr] = (fichasPorParroquia[parr] || 0) + 1;

    // Por técnico
    const tecNombre = getNombreTecnico(f.creado_por);
    fichasPorTecnico[tecNombre] = (fichasPorTecnico[tecNombre] || 0) + 1;
    if (f.creado_por) tecnicosSet.add(tecNombre);

    // Por fecha
    const fecha = safeToDate(f.fecha_creacion).toISOString().split('T')[0];
    fichasPorFecha[fecha] = (fichasPorFecha[fecha] || 0) + 1;

    // Áreas
    areaTotal += f.area_total || 0;
    areaRiego += f.area_riego || 0;
    areaSinRiego += f.area_sin_riego || 0;

    // Métodos de riego (promedio ponderado)
    gravedad += f.metodo_gravedad_pct || 0;
    aspersion += f.metodo_aspersion_pct || 0;
    goteo += f.metodo_goteo_pct || 0;

    // Tenencia
    const ten = f.tenencia_predio || 'Sin dato';
    tenenciaPredioCounts[ten] = (tenenciaPredioCounts[ten] || 0) + 1;
  }

  const n = fichas.length || 1;

  const totalTecnicosUnicos = new Set(Object.values(TECNICOS).map((t) => t.nombre)).size;

  return {
    totalFichas: fichas.length,
    totalPoligonos: 24452,
    totalCultivos: 0, // se llena aparte
    totalAnimales: 0,
    totalPrediosAdicionales: 0,
    areaTotal,
    areaRiego,
    areaSinRiego,
    tecnicosActivos: tecnicosSet.size || totalTecnicosUnicos,
    fichasPorParroquia,
    fichasPorTecnico,
    fichasPorFecha,
    metodoRiego: {
      gravedad: Math.round(gravedad / n),
      aspersion: Math.round(aspersion / n),
      goteo: Math.round(goteo / n),
    },
    cultivosFrecuentes,
    tenenciaPredioCounts,
  };
}

// ── Guardar una nueva encuesta pública ──
export async function submitEncuestaPublica(
  encuesta: Omit<EncuestaPublica, 'id' | 'fecha_envio' | 'estado'>
): Promise<string> {
  const colRef = collection(db, 'encuestas_publicas');
  const docRef = await addDoc(colRef, {
    ...encuesta,
    fecha_envio: new Date().toISOString(),
    estado: 'pendiente'
  });
  return docRef.id;
}

// ── Obtener todas las encuestas públicas ──
export async function getEncuestasPublicas(): Promise<EncuestaPublica[]> {
  const colRef = collection(db, 'encuestas_publicas');
  const q = query(colRef, orderBy('fecha_envio', 'desc'));
  const snapshot = await getDocs(q);
  return snapshot.docs.map(d => ({
    ...d.data(),
    id: d.id,
  } as EncuestaPublica));
}

// ── Actualizar estado de una encuesta ──
export async function updateEstadoEncuesta(
  id: string,
  estado: 'pendiente' | 'procesada' | 'rechazada',
  observaciones?: string,
  tecnicoEmail?: string
): Promise<void> {
  const docRef = doc(db, 'encuestas_publicas', id);
  const data: any = { estado };
  if (observaciones !== undefined) data.observaciones = observaciones;
  if (tecnicoEmail !== undefined) {
    data.procesado_por = tecnicoEmail;
    data.fecha_procesado = new Date().toISOString();
  }
  await updateDoc(docRef, data);
}

