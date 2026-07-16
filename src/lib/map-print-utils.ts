// Paletas de colores oficiales por sector para las comunidades (estilo QGIS)
export const SECTOR_COLORS_MAP: Record<string, string> = {
  'Sector 1': '#8b5cf6', // Violeta
  'Sector 2': '#06b6d4', // Cian
  'Sector 3': '#10b981', // Verde esmeralda
};

// Colores específicos de comunidades del Sector 1
export const SECTOR_1_COLORS = [
  '#e63946', '#f4845f', '#f7b267', '#f7d794', '#a8d8ea',
  '#3dc1d3', '#0abde3', '#7f8fa6', '#c44569', '#cf6a87',
  '#f8a5c2', '#63cdda', '#3ae374', '#786fa6', '#f19066',
  '#ea8685', '#574b90', '#f78fb3', '#3B3B98', '#cc8e35',
  '#e77f67', '#778beb'
];

// Colores específicos de comunidades del Sector 2
export const SECTOR_2_COLORS = [
  '#2ed573', '#ffa502', '#ff6348', '#1e90ff', '#5f27cd',
  '#ff9ff3', '#54a0ff', '#00d2d3', '#c8d6e5', '#feca57',
  '#ee5a24', '#0be881', '#3c40c6', '#f8b739'
];

// Colores específicos de comunidades del Sector 3
export const SECTOR_3_COLORS = [
  '#e17055', '#00b894', '#6c5ce7', '#fdcb6e', '#e84393',
  '#55efc4', '#74b9ff', '#a29bfe', '#dfe6e9', '#fab1a0',
  '#81ecec', '#ffeaa7', '#636e72', '#b2bec3', '#d63031',
  '#00cec9', '#fd79a8'
];

// Asignar un color único y consistente a una comunidad según su sector
export function getComunidadColor(_comunidad: string, sector: string, index: number): string {
  const sectorNorm = sector || '';
  
  if (sectorNorm === 'Sector 1') {
    return SECTOR_1_COLORS[index % SECTOR_1_COLORS.length];
  } else if (sectorNorm === 'Sector 2') {
    return SECTOR_2_COLORS[index % SECTOR_2_COLORS.length];
  } else if (sectorNorm === 'Sector 3') {
    return SECTOR_3_COLORS[index % SECTOR_3_COLORS.length];
  }
  
  // Fallback a un color neutro
  return '#94a3b8';
}

// ── Carga asíncrona de imágenes Base64 para jsPDF ──
export function loadImageBase64(src: string): Promise<{ data: string; width: number; height: number }> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.drawImage(img, 0, 0);
        resolve({
          data: canvas.toDataURL('image/png'),
          width: img.naturalWidth,
          height: img.naturalHeight
        });
      } else {
        reject(new Error('No se pudo obtener el contexto 2d del canvas'));
      }
    };
    img.onerror = () => reject(new Error(`Error al cargar la imagen: ${src}`));
    img.src = src;
  });
}

// ── Cálculo de escala gráfica ──
export interface EscalaBarraInfo {
  anchoPx: number;
  anchoMm: number;
  distanciaMetros: number;
  label: string;
}

export function calcularEscalaGrafica(
  lat: number,
  zoom: number,
  mapWidthPx: number,
  mapWidthMm: number,
  maxBarWidthMm: number = 50
): EscalaBarraInfo {
  // Metros por píxel en el ecuador usando Web Mercator
  const ecuadorLength = 40075016.686;
  const metersPerPixel = (ecuadorLength * Math.cos((lat * Math.PI) / 180)) / Math.pow(2, zoom + 8);

  // Ancho máximo que queremos para la barra en píxeles de pantalla/renderizado
  const maxBarWidthPx = (maxBarWidthMm * mapWidthPx) / mapWidthMm;
  const maxMeters = maxBarWidthPx * metersPerPixel;

  // Encontrar una distancia "redonda" en metros menor que la distancia máxima de la barra
  const distanciasRedondas = [
    50000, 20000, 10000, 5000, 2000, 1000, 500, 250, 100, 50, 20, 10, 5, 2, 1
  ];
  
  let distanciaSeleccionada = 100;
  for (const d of distanciasRedondas) {
    if (d < maxMeters) {
      distanciaSeleccionada = d;
      break;
    }
  }

  // Calcular el ancho de la barra en píxeles y en milímetros del papel
  const anchoPx = distanciaSeleccionada / metersPerPixel;
  const anchoMm = (anchoPx * mapWidthMm) / mapWidthPx;

  // Generar label descriptivo
  const label = distanciaSeleccionada >= 1000
    ? `${(distanciaSeleccionada / 1000).toFixed(0)} km`
    : `${distanciaSeleccionada.toFixed(0)} m`;

  return {
    anchoPx,
    anchoMm,
    distanciaMetros: distanciaSeleccionada,
    label
  };
}
