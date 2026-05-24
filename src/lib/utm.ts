/**
 * Conversión de coordenadas WGS84 (EPSG:4326) ↔ UTM Zona 17S (EPSG:32717)
 * Para el proyecto de riego en Cayambe, Pichincha, Ecuador.
 *
 * UTM Zona 17S:
 *   Meridiano central: -81°
 *   Falso Este: 500,000 m
 *   Falso Norte: 10,000,000 m (hemisferio sur)
 *   Elipsoide: WGS84
 */

// ── Parámetros del elipsoide WGS84 ──
const a = 6378137.0;            // semieje mayor (metros)
const f = 1 / 298.257223563;    // aplanamiento
const e2 = 2 * f - f * f;       // excentricidad² primera
const e_prime2 = e2 / (1 - e2); // excentricidad² segunda
const k0 = 0.9996;              // factor de escala UTM
const CM = -81;                  // meridiano central zona 17
const FE = 500000;               // falso este
const FN = 10000000;             // falso norte (hemisferio sur)

/**
 * Convierte lat/lon (WGS84) → Este/Norte UTM zona 17S
 */
export function wgs84ToUtm17S(lat: number, lon: number): { este: number; norte: number } {
  const latRad = (lat * Math.PI) / 180;
  const lonRad = (lon * Math.PI) / 180;
  const cmRad = (CM * Math.PI) / 180;

  const N = a / Math.sqrt(1 - e2 * Math.sin(latRad) ** 2);
  const T = Math.tan(latRad) ** 2;
  const C = e_prime2 * Math.cos(latRad) ** 2;
  const A = (lonRad - cmRad) * Math.cos(latRad);
  const M =
    a *
    ((1 - e2 / 4 - (3 * e2 ** 2) / 64 - (5 * e2 ** 3) / 256) * latRad -
      ((3 * e2) / 8 + (3 * e2 ** 2) / 32 + (45 * e2 ** 3) / 1024) * Math.sin(2 * latRad) +
      ((15 * e2 ** 2) / 256 + (45 * e2 ** 3) / 1024) * Math.sin(4 * latRad) -
      ((35 * e2 ** 3) / 3072) * Math.sin(6 * latRad));

  const este =
    FE +
    k0 *
      N *
      (A +
        ((1 - T + C) * A ** 3) / 6 +
        ((5 - 18 * T + T ** 2 + 72 * C - 58 * e_prime2) * A ** 5) / 120);

  const norte =
    FN +
    k0 *
      (M +
        N *
          Math.tan(latRad) *
          (A ** 2 / 2 +
            ((5 - T + 9 * C + 4 * C ** 2) * A ** 4) / 24 +
            ((61 - 58 * T + T ** 2 + 600 * C - 330 * e_prime2) * A ** 6) / 720));

  return { este: Math.round(este * 100) / 100, norte: Math.round(norte * 100) / 100 };
}

/**
 * Formatea coordenadas WGS84 (grados decimales)
 */
export function formatWGS84(lat: number, lon: number): string {
  return `${Math.abs(lat).toFixed(6)}° ${lat >= 0 ? 'N' : 'S'},  ${Math.abs(lon).toFixed(6)}° ${lon >= 0 ? 'E' : 'W'}`;
}

/**
 * Formatea coordenadas UTM zona 17S
 */
export function formatUTM17S(lat: number, lon: number): string {
  const { este, norte } = wgs84ToUtm17S(lat, lon);
  return `E ${este.toFixed(2)}  N ${norte.toFixed(2)}`;
}

export type CRS = 'wgs84' | 'utm17s';

/**
 * Formatea coordenadas según el CRS seleccionado
 */
export function formatCoords(lat: number, lon: number, crs: CRS): string {
  return crs === 'utm17s' ? formatUTM17S(lat, lon) : formatWGS84(lat, lon);
}

/**
 * Etiqueta del CRS
 */
export function crsLabel(crs: CRS): string {
  return crs === 'utm17s' ? 'UTM 17S (EPSG:32717)' : 'WGS84 (EPSG:4326)';
}
