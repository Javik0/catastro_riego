/**
 * Capturas de pantalla para el manual de uso del geovisor.
 *
 * Levanta el Chrome ya instalado (no descarga navegador) contra el servidor de
 * desarrollo, que entra sin credenciales gracias a VITE_DEV_LOGIN. Para que el
 * manual muestre lo que ve el consorcio y no lo que ve un tecnico, el .env.local
 * debe estar en VITE_DEV_ROL=cliente: ese rol no alcanza Reportes ni Represa.
 *
 * Ademas de la imagen, anota en capturas.json el rectangulo de cada elemento que
 * el manual senala. Asi las llamadas numeradas las dibuja despues un script
 * sobre coordenadas reales, y no sobre posiciones escritas a mano que se
 * desfasan en cuanto la pantalla cambia.
 *
 * Uso:  node scripts/capturar_manual.mjs
 */
import puppeteer from 'puppeteer-core';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const SALIDA = path.join(AQUI, '..', 'docs', 'manual', 'capturas');
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const URL = 'http://localhost:5173';

// Los selectores se anclan en atributos title, que son los rotulos que la
// propia interfaz le muestra al usuario: si cambian, el manual deberia
// cambiar igual, asi que es correcto que la captura falle y avise.
const T_INVESTIGACION = '[title^="Colorear los predios por su estado"]';
const T_RIEGO = '[title^="Colorear los predios según su condición de riego"]';
const T_QGIS = '[title="Descargar la cartografía para revisarla en QGIS"]';
const T_BUSCAR_PREDIO = '[title="Buscar predio por nombre, cédula o clave catastral"]';
const T_VER_FICHA = '[title="Ver detalle de la ficha"]';
const T_TIPO_FICHA = '[title="Filtrar por tipo de ficha"]';

const espera = (ms) => new Promise((r) => setTimeout(r, ms));

/**
 * Deja la pantalla como debe salir en el manual: TEMA OSCURO, que es como la
 * aplicacion abre por defecto y ademas el unico en el que la ficha se ve bien
 * (FichaDetailModal lleva sus colores fijos y no sigue el tema claro), y el
 * menu lateral desplegado, porque plegado solo muestra iconos y el manual
 * nombra los modulos. Decision de JAVIKO, 15-sep-2026.
 */
async function prepararPantalla(page) {
  const aOscuro = await page.$('[title="Cambiar a tema oscuro"]');
  if (aOscuro) { await aOscuro.click(); await espera(600); }
  const desplegado = await page.evaluate(() => {
    const enlace = document.querySelector('a[href="/mapa"]');
    if (!enlace) return true;
    let caja = enlace.parentElement;
    while (caja && !caja.querySelector('button')) caja = caja.parentElement;
    if (!caja) return true;
    if (caja.innerText.includes('CATASTRO RIEGO')) return true;
    caja.querySelector('button').click();
    return false;
  });
  if (!desplegado) await espera(600);

  // El login de desarrollo se identifica como «Desarrollo (cliente) /
  // dev-cliente@local»: eso es andamiaje nuestro y no puede salir en un
  // documento que se entrega. Se sustituye por un rotulo neutro y se oculta el
  // correo. El distintivo del rol se deja, porque si describe lo que el
  // consorcio ve.
  await page.evaluate(() => {
    const salir = [...document.querySelectorAll('button, a')]
      .find((e) => e.innerText.trim().startsWith('Cerrar sesión'));
    if (!salir) return;
    let caja = salir.parentElement;
    while (caja && !caja.innerText.includes('@')) caja = caja.parentElement;
    if (!caja) return;
    for (const e of caja.querySelectorAll('*')) {
      if (e.children.length) continue;
      const t = e.textContent.trim();
      if (t.includes('@')) e.textContent = '';
      else if (/^Desarrollo/.test(t)) e.textContent = 'Consorcio Cayambe SPT';
    }
  });
}

/** Las capas satelitales tardan: se espera a que no quede ningun tile cargando. */
async function esperarMapa(page) {
  await page.waitForSelector('.leaflet-container', { timeout: 60000 });
  await prepararPantalla(page);
  try {
    await page.waitForFunction(
      () => !document.querySelector('.leaflet-tile-loading'),
      { timeout: 45000 });
  } catch { /* si algun tile no llega, la captura igual sirve */ }
  await espera(4000);
}

async function esperarTablero(page) {
  await page.waitForFunction(
    () => document.body.innerText.includes('4.307'),
    { timeout: 60000 });
  await prepararPantalla(page);
  await espera(800);
}

async function esperarListado(page) {
  await page.waitForFunction(
    () => /\d[\d.]* de [\d.]+ registros/.test(document.body.innerText),
    { timeout: 60000 });
  await prepararPantalla(page);
  await espera(800);
}

const TOMAS = [
  {
    id: '01-tablero',
    titulo: 'Tablero de entrada',
    ruta: '/',
    preparar: esperarTablero,
    marcas: [
      { sel: 'a[href="/"]', nota: 'Tablero: las cifras del padrón' },
      { sel: 'a[href="/mapa"]', nota: 'Mapa: el catastro sobre imagen satelital' },
      { sel: 'a[href="/fichas"]', nota: 'Fichas: el listado del padrón' },
      { sel: '[title*="tema claro"], [title*="tema oscuro"]', nota: 'Cambia entre tema claro y oscuro' },
    ],
  },
  {
    id: '02-filtros',
    titulo: 'Barra de filtros',
    ruta: '/',
    preparar: esperarTablero,
    recorte: 'header',
    marcas: [
      { sel: 'input[placeholder^="Buscar propietario"]', nota: 'Buscador por propietario o cédula' },
      { sel: 'select', nota: 'Filtros: parroquia, sector, comunidad, técnico y fechas', indice: 0 },
    ],
  },
  {
    id: '03-mapa-investigacion',
    titulo: 'Mapa — vista Investigación',
    ruta: '/mapa',
    preparar: esperarMapa,
    marcas: [
      { sel: T_INVESTIGACION, nota: 'Vista Investigación: color según el estado de la ficha' },
      { sel: T_RIEGO, nota: 'Vista Riego: color según la condición de riego' },
      { sel: T_QGIS, nota: 'Descarga la cartografía para QGIS' },
      { sel: T_BUSCAR_PREDIO, nota: 'Busca un predio por su clave catastral' },
    ],
  },
  {
    id: '04-mapa-riego',
    titulo: 'Mapa — vista Riego',
    ruta: '/mapa',
    preparar: async (page) => {
      await esperarMapa(page);
      await page.click(T_RIEGO);
      await espera(3500);
    },
    marcas: [{ sel: T_RIEGO, nota: 'La vista Riego, activada' }],
  },
  {
    id: '05-fichas-listado',
    titulo: 'Listado de fichas',
    ruta: '/fichas',
    preparar: esperarListado,
    marcas: [
      { sel: 'input[placeholder^="Buscar por propietario"]', nota: 'Busca por nombre, cédula, clave catastral o código' },
      { sel: T_TIPO_FICHA, nota: 'Ver todas las fichas o solo las principales' },
      { sel: T_VER_FICHA, nota: 'Abre la ficha', indice: 0 },
    ],
  },
  {
    id: '06-mapa-predio',
    titulo: 'Mapa — ficha de un predio',
    ruta: '/mapa',
    preparar: async (page) => {
      await esperarMapa(page);
      // Un predio cualquiera del padron: el primer poligono dibujado.
      await page.click('path.leaflet-interactive');
      await espera(1200);
      await page.mouse.move(40, 780);   // fuera del mapa: quita el globo del raton
      await espera(1500);
    },
    marcas: [
      { sel: 'button::-p-text(Ver ficha completa)', nota: 'Abre la ficha completa del titular' },
    ],
  },
  {
    id: '07-mapa-qgis',
    titulo: 'Mapa — descarga de la cartografía',
    ruta: '/mapa',
    preparar: async (page) => {
      await esperarMapa(page);
      await page.click(T_QGIS);
      await espera(2000);
    },
    marcas: [{ sel: T_QGIS, nota: 'El botón QGIS y lo que descarga' }],
  },
  {
    id: '08-fichas-busqueda',
    titulo: 'Buscar una ficha por su código',
    ruta: '/fichas',
    preparar: async (page) => {
      await esperarListado(page);
      await page.type('input[placeholder^="Buscar por propietario"]', 'S01-C01-R056');
      await espera(1800);
    },
    marcas: [{ sel: 'input[placeholder^="Buscar por propietario"]', nota: 'El código escrito en el buscador deja una sola ficha' }],
  },
  {
    id: '09-ficha-detalle',
    titulo: 'La ficha abierta',
    ruta: '/fichas',
    preparar: async (page) => {
      await esperarListado(page);
      // Una ficha principal concreta: el manual explica el codigo con F01.
      await page.type('input[placeholder^="Buscar por propietario"]', 'S01-C01-R056-F01');
      await espera(1800);
      await page.click(T_VER_FICHA);
      await espera(2500);
    },
    marcas: [
      { sel: '[title="Imprimir Ficha Técnica A4"]', nota: 'Genera la ficha en A4, igual que la del expediente' },
    ],
  },
];

async function main() {
  fs.mkdirSync(SALIDA, { recursive: true });
  const navegador = await puppeteer.launch({
    executablePath: CHROME,
    headless: 'new',
    defaultViewport: { width: 1440, height: 900, deviceScaleFactor: 2 },
    args: ['--hide-scrollbars', '--force-device-scale-factor=2'],
  });
  const page = await navegador.newPage();
  const registro = [];

  for (const t of TOMAS) {
    process.stdout.write(`  ${t.id} ... `);
    await page.goto(URL + t.ruta, { waitUntil: 'networkidle2', timeout: 90000 });
    if (t.preparar) await t.preparar(page);

    const archivo = path.join(SALIDA, `${t.id}.png`);
    const objetivo = t.recorte ? await page.$(t.recorte) : page;

    // Los rectangulos que devuelve el navegador son absolutos de la pagina.
    // Cuando la captura es el recorte de un elemento, hay que restarle su
    // origen: si no, los globos salen corridos y senalan el control equivocado.
    const origen = t.recorte ? await objetivo.boundingBox() : { x: 0, y: 0 };

    const marcas = [];
    for (const m of t.marcas || []) {
      const els = await page.$$(m.sel);
      const el = els[m.indice || 0];
      if (!el) { console.log('     ! sin elemento: ' + m.sel); continue; }
      const caja = await el.boundingBox();
      if (caja) marcas.push({
        nota: m.nota,
        x: caja.x - origen.x, y: caja.y - origen.y,
        width: caja.width, height: caja.height,
      });
    }

    await objetivo.screenshot({ path: archivo });
    registro.push({ id: t.id, titulo: t.titulo, archivo: `${t.id}.png`, marcas });
    console.log('ok');
  }

  fs.writeFileSync(path.join(SALIDA, 'capturas.json'),
    JSON.stringify(registro, null, 2), 'utf8');
  await navegador.close();
  console.log(`\n${registro.length} capturas en ${SALIDA}`);
}

main().catch((e) => { console.error(e); process.exit(1); });
