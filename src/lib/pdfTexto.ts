/**
 * Texto seguro para los PDF que genera jsPDF.
 *
 * Por qué existe
 * --------------
 * jsPDF usa las fuentes estándar de PDF (Helvetica y compañía), que solo
 * cubren un juego de caracteres limitado. Las tildes y la ñ salen bien, pero
 * los signos tipográficos —guion largo, comillas curvas, puntos suspensivos—
 * **desaparecen sin avisar**: no dan error, simplemente no se dibujan.
 *
 * En el reporte por comunidad eso se leía así:
 *
 *     PADRÓN DE USUARIOS: ... GUANGUILQUÍPOROTOG
 *     Provincia Pichincha  Cantón Cayambe
 *
 * Los títulos venían de `constants.ts`, donde el guion largo es correcto
 * porque en pantalla se ve bien. Lo que hay que arreglar es el paso al PDF, no
 * el texto original.
 */

/** Cambia los signos que jsPDF no dibuja por equivalentes que sí. */
export function pdfSafe(texto: string): string {
  return (texto ?? '')
    .replace(/[–—‒―]/g, '-')      // guiones largos
    .replace(/[“”«»]/g, '"')      // comillas dobles curvas
    .replace(/['']/g, "'")        // comillas simples curvas
    .replace(/…/g, '...')
    .replace(/[·•]/g, '-')        // puntos medios y viñetas
    .replace(/ /g, ' ')      // espacio duro
    .replace(/[≥]/g, '>=')
    .replace(/[≤]/g, '<=');
}
