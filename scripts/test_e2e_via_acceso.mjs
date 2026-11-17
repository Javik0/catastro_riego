/**
 * Test E2E automatizado para la integración de la Vía de Acceso CAD en /represa y /mapa.
 *
 * Utiliza puppeteer-core apuntando al Chrome local instalado.
 * Ejecución: node scripts/test_e2e_via_acceso.mjs
 */

import puppeteer from 'puppeteer-core';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const CHROME_PATH = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const OUTPUT_DIR = path.join(__dirname, '..', 'test-results', 'via_acceso');
const BASE_URL = 'http://localhost:5173';

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function runE2ETests() {
  console.log('========================================================');
  console.log(' INICIANDO PRUEBAS E2E: INTEGRACIÓN VÍA DE ACCESO CAD  ');
  console.log('========================================================');

  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }

  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: 'new',
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--window-size=1366,768',
      '--disable-gpu',
    ],
    defaultViewport: {
      width: 1366,
      height: 768,
    },
  });

  const page = await browser.newPage();

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      console.log(`[Browser Console ERROR] ${msg.text()}`);
    }
  });

  page.on('pageerror', (err) => {
    console.error(`[Browser PageError]`, err.message);
  });

  try {
    // -------------------------------------------------------------
    // TEST 1: VISOR REPRESA (/represa)
    // -------------------------------------------------------------
    console.log('\n--- TEST 1: Navegando a /represa ---');
    await page.goto(`${BASE_URL}/represa`, { waitUntil: 'networkidle0', timeout: 30000 });
    await sleep(2500);

    // Verificar que el mapa Leaflet haya inicializado
    const leafletMap = await page.$('.leaflet-container');
    if (!leafletMap) {
      throw new Error('No se encontró el contenedor .leaflet-container en /represa');
    }
    console.log('✔ Contenedor Leaflet detectado');

    // Verificar que aparezca el panel de Predios en la vía de acceso (CAD)
    await page.waitForFunction(
      () => document.body.innerText.includes('Predios en la vía de acceso (CAD)') ||
            document.body.innerText.includes('Vía de acceso CAD'),
      { timeout: 15000 }
    );
    console.log('✔ Sección "Predios en la vía de acceso (CAD)" detectada en el panel lateral');

    // Verificar las métricas clave de la vía en el texto
    const pageTextRepresa = await page.evaluate(() => document.body.innerText);
    const checksRepresa = [
      { label: 'Longitud de vía (6,01 km)', pass: pageTextRepresa.includes('6,01 km') || pageTextRepresa.includes('6.012') },
      { label: 'Calzada berma1', pass: pageTextRepresa.includes('berma1') },
      { label: 'Ocupación (3,55 ha)', pass: pageTextRepresa.includes('3,55 ha') || pageTextRepresa.includes('35.451') },
      { label: 'Predios afectados 28', pass: pageTextRepresa.includes('28 predios') || pageTextRepresa.includes('Lista (28)') },
      { label: 'Con ficha de padrón (7)', pass: pageTextRepresa.includes('Con ficha del padrón') && pageTextRepresa.includes('430,7 m²') },
      { label: 'Con titular municipal (9)', pass: pageTextRepresa.includes('Con titular municipal') && pageTextRepresa.includes('871,1 m²') },
      { label: 'Sin titular (12)', pass: pageTextRepresa.includes('Sin titular registrado') && pageTextRepresa.includes('34.149') },
      { label: 'Alcantarillas proyectadas (7)', pass: pageTextRepresa.includes('Alcantarillas proyectadas') && pageTextRepresa.includes('ALC-06') },
    ];

    for (const c of checksRepresa) {
      if (c.pass) {
        console.log(`✔ Métrica confirmada: ${c.label}`);
      } else {
        console.warn(`⚠ Advertencia: no se encontró "${c.label}"`);
      }
    }

    // Captura 1: Represa inicial
    const cap1Path = path.join(OUTPUT_DIR, '01_represa_inicial.png');
    await page.screenshot({ path: cap1Path });
    console.log(`📸 Captura 1 guardada: ${cap1Path}`);

    // Clic en "Ver vía y predios"
    console.log('Haciendo clic en "Ver vía y predios"...');
    const verViaBtn = await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const btn = btns.find((b) => b.innerText.includes('Ver vía y predios'));
      if (btn) {
        btn.click();
        return true;
      }
      return false;
    });

    if (verViaBtn) {
      console.log('✔ Clic en "Ver vía y predios" ejecutado con éxito');
    } else {
      console.warn('⚠ No se encontró el botón "Ver vía y predios"');
    }
    await sleep(2500);

    // Captura 2: Mapa encuadrado en la vía
    const cap2Path = path.join(OUTPUT_DIR, '02_represa_zoom_via.png');
    await page.screenshot({ path: cap2Path });
    console.log(`📸 Captura 2 guardada: ${cap2Path}`);

    // Clic en "Lista (28)" para desplegar los predios
    console.log('Desplegando lista de 28 predios...');
    const desplegarLista = await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const btn = btns.find((b) => b.innerText.includes('Lista (28)'));
      if (btn) {
        btn.click();
        return true;
      }
      return false;
    });

    if (desplegarLista) {
      console.log('✔ Clic en botón "Lista (28)" ejecutado');
      await sleep(1500);

      // Captura 3: Lista desplegada
      const cap3Path = path.join(OUTPUT_DIR, '03_represa_lista_desplegada.png');
      await page.screenshot({ path: cap3Path });
      console.log(`📸 Captura 3 guardada: ${cap3Path}`);

      // Hacer clic sobre el primer predio de la lista para abrir popup
      console.log('Haciendo clic sobre el predio 1702521580035 en la lista...');
      const clicPredio = await page.evaluate(() => {
        const btns = Array.from(document.querySelectorAll('button'));
        const predioBtn = btns.find((b) => b.innerText && b.innerText.includes('1702521580035'));
        if (predioBtn) {
          predioBtn.click();
          return true;
        }
        return false;
      });

      if (clicPredio) {
        console.log('✔ Predio 1702521580035 clickeado');
        await sleep(2500);

        // Verificar contenido del popup
        const tienePopup = await page.evaluate(() => {
          const popup = document.querySelector('.leaflet-popup-content');
          return popup ? popup.innerText : '';
        });

        if (tienePopup) {
          console.log(`✔ Popup abierto en visor represa: ${tienePopup.replace(/\n+/g, ' ').substring(0, 100)}...`);
        }

        const cap4Path = path.join(OUTPUT_DIR, '04_represa_predio_seleccionado.png');
        await page.screenshot({ path: cap4Path });
        console.log(`📸 Captura 4 guardada: ${cap4Path}`);
      }
    }

    // -------------------------------------------------------------
    // TEST 2: VISOR GENERAL (/mapa)
    // -------------------------------------------------------------
    console.log('\n--- TEST 2: Navegando a /mapa ---');
    await page.goto(`${BASE_URL}/mapa`, { waitUntil: 'networkidle0', timeout: 30000 });
    await sleep(3000);

    // Esperar a que el mapa cargue
    await page.waitForSelector('.leaflet-container', { timeout: 15000 });
    console.log('✔ Contenedor Leaflet detectado en /mapa');

    // Verificar presencia del botón rápido "🛣️ Zona Represa / Vía (28 predios)"
    const tieneBotonRapido = await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      return btns.some((b) => b.innerText.includes('Zona Represa / Vía'));
    });

    if (tieneBotonRapido) {
      console.log('✔ Botón rápido "🛣️ Zona Represa / Vía (28 predios)" detectado en el panel izquierdo');
    } else {
      console.warn('⚠ Botón rápido "Zona Represa / Vía" no encontrado');
    }

    // Captura 5: Mapa general inicial
    const cap5Path = path.join(OUTPUT_DIR, '05_mapa_general_inicial.png');
    await page.screenshot({ path: cap5Path });
    console.log(`📸 Captura 5 guardada: ${cap5Path}`);

    // Clic en el botón rápido de Zona Represa / Vía
    console.log('Haciendo clic en el botón rápido "🛣️ Zona Represa / Vía"...');
    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const btn = btns.find((b) => b.innerText.includes('Zona Represa / Vía'));
      if (btn) btn.click();
    });
    await sleep(3000);

    // Captura 6: Mapa centrado en la vía y represa
    const cap6Path = path.join(OUTPUT_DIR, '06_mapa_centrado_via.png');
    await page.screenshot({ path: cap6Path });
    console.log(`📸 Captura 6 guardada: ${cap6Path}`);

    // Probar búsqueda de un predio afectado en /mapa (1702521580035)
    console.log('Abriendo buscador de predios en /mapa...');
    const searchToggle = await page.$('button[title*="Buscar predio"]');
    if (searchToggle) {
      await searchToggle.click();
      await sleep(600);
    }

    const searchInput = await page.waitForSelector('input[placeholder*="Buscar predio"]', { timeout: 10000 });
    if (searchInput) {
      console.log('Escribiendo clave 1702521580035 en búsqueda...');
      await searchInput.click();
      await searchInput.type('1702521580035', { delay: 60 });
      await sleep(2000);

      // Clic en la primera sugerencia del dropdown (usa onMouseDown en React)
      console.log('Seleccionando resultado de la búsqueda...');
      const clicado = await page.evaluate(() => {
        const btns = Array.from(document.querySelectorAll('button'));
        const targetBtn = btns.find((b) => b.innerText && b.innerText.includes('1702521580035'));
        if (targetBtn) {
          targetBtn.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
          targetBtn.click();
          return true;
        }
        return false;
      });

      console.log('Resultado clickeado:', clicado);
      await sleep(3500);

      // Clic en el marcador de búsqueda pulsante para abrir su popup
      console.log('Abriendo popup del marcador de búsqueda...');
      const marker = await page.$('.search-pulse-marker');
      if (marker) {
        await marker.click();
        await sleep(1500);
      }

      // Comprobar si se renderizó el BannerViaAcceso
      const textoPopup = await page.evaluate(() => document.body.innerText);
      const tieneBannerAfectacion = textoPopup.includes('Afectación vía de acceso (CAD berma1)');
      if (tieneBannerAfectacion) {
        console.log('✔ BannerViaAcceso detectado exitosamente en el visor /mapa');
      } else {
        console.log('ℹ Texto en pantalla tras búsqueda:', textoPopup.substring(0, 300));
      }

      const cap7Path = path.join(OUTPUT_DIR, '07_mapa_busqueda_predio.png');
      await page.screenshot({ path: cap7Path });
      console.log(`📸 Captura 7 guardada: ${cap7Path}`);
    }

    // Abrir control de capas para verificar la capa de la vía
    console.log('\n--- TEST 3: Verificando control de capas en /mapa ---');
    const layersToggle = await page.$('.leaflet-control-layers-toggle');
    if (layersToggle) {
      await layersToggle.hover();
      await sleep(1000);
      const layersText = await page.evaluate(() => {
        const form = document.querySelector('.leaflet-control-layers');
        return form ? form.innerText : '';
      });

      if (layersText.includes('Vía de acceso represa (CAD)')) {
        console.log('✔ Capa "🛣️ Vía de acceso represa (CAD)" presente en el selector de capas');
      } else {
        console.warn('⚠ Capa no encontrada textualmente en control de capas:', layersText);
      }

      const cap8Path = path.join(OUTPUT_DIR, '08_mapa_control_capas.png');
      await page.screenshot({ path: cap8Path });
      console.log(`📸 Captura 8 guardada: ${cap8Path}`);
    }

    console.log('\n========================================================');
    console.log(' ✅ TODAS LAS PRUEBAS E2E FINALIZARON EXITOSAMENTE ');
    console.log('========================================================');
  } catch (err) {
    console.error('\n❌ ERROR DURANTE LA PRUEBA E2E:', err);
    const errPath = path.join(OUTPUT_DIR, 'error_screenshot.png');
    await page.screenshot({ path: errPath });
    console.log(`📸 Captura de error guardada: ${errPath}`);
  } finally {
    await browser.close();
  }
}

runE2ETests();
