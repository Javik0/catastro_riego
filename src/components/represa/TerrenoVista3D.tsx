/**
 * Visor 3D del terreno de la represa de Porotog.
 *
 * El relieve sale de `public/geo/represa/terreno.json`, una malla de alturas
 * generada por `scripts/represa/05_modelo_terreno.py` a partir de las curvas de
 * nivel. El JSON trae las alturas en decímetros enteros (–32768 = sin dato) para
 * que el archivo no se llene de decimales inútiles.
 *
 * Sobre el relieve se dibujan el límite de proyecto y los rótulos de obra, que
 * es lo que convierte esto en algo útil y no en una maqueta bonita: se ve dónde
 * cae la presa respecto del valle y cómo quedan los bancos de materiales.
 *
 * Ojo con la resolución vertical: el modelo se apoya en cartografía regional de
 * 5 m. Sirve para entender el relieve, NO para medir volúmenes de obra.
 */
import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { Loader2, Mountain } from 'lucide-react';
import { wgs84ToUtm17S } from '../../lib/utm';

interface Terreno {
  nx: number;
  ny: number;
  bbox_utm: [number, number, number, number];
  ancho_m: number;
  alto_m: number;
  cota_min: number;
  cota_max: number;
  alturas: number[];
}

const SIN_DATO = -32768;

/** Paleta hipsométrica: de verde de valle a roca alta. */
function colorPorAltura(t: number): [number, number, number] {
  const paradas: Array<[number, [number, number, number]]> = [
    [0.0, [0.30, 0.45, 0.25]],
    [0.35, [0.55, 0.60, 0.30]],
    [0.6, [0.65, 0.55, 0.35]],
    [0.8, [0.55, 0.44, 0.36]],
    [1.0, [0.85, 0.85, 0.87]],
  ];
  for (let i = 0; i < paradas.length - 1; i++) {
    const [t0, c0] = paradas[i];
    const [t1, c1] = paradas[i + 1];
    if (t <= t1) {
      const f = (t - t0) / (t1 - t0 || 1);
      return [c0[0] + (c1[0] - c0[0]) * f,
              c0[1] + (c1[1] - c0[1]) * f,
              c0[2] + (c1[2] - c0[2]) * f];
    }
  }
  return paradas[paradas.length - 1][1];
}

export default function TerrenoVista3D() {
  const contenedor = useRef<HTMLDivElement>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exageracion, setExageracion] = useState(2);
  const [info, setInfo] = useState<{ min: number; max: number } | null>(null);

  // La escena se reconstruye al cambiar la exageración (por eso está en las
  // dependencias). Se podría recalcular solo las alturas y evitar el remontaje,
  // pero a esta escala tarda milisegundos y el JSON ya está en caché.
  useEffect(() => {
    const nodo = contenedor.current;
    if (!nodo) return;

    let animacion = 0;
    let cancelado = false;
    const desechables: Array<{ dispose: () => void }> = [];
    const escena = new THREE.Scene();
    escena.background = new THREE.Color(0x0b1220);

    const camara = new THREE.PerspectiveCamera(50, 1, 1, 40000);
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    nodo.appendChild(renderer.domElement);

    const controles = new OrbitControls(camara, renderer.domElement);
    controles.enableDamping = true;
    controles.maxPolarAngle = Math.PI / 2.05;   // no meterse debajo del terreno

    escena.add(new THREE.AmbientLight(0xffffff, 0.55));
    const sol = new THREE.DirectionalLight(0xffffff, 1.1);
    sol.position.set(-1, 1.4, -0.8);
    escena.add(sol);

    // grupo del relieve: rotarlo entero deja el norte «hacia arriba» en pantalla
    const mundo = new THREE.Group();
    escena.add(mundo);

    async function construir() {
      const r = await fetch('/geo/represa/terreno.json');
      if (!r.ok) throw new Error('no se pudo cargar el modelo de terreno');
      const t: Terreno = await r.json();
      if (cancelado) return;

      const { nx, ny, alturas, cota_min, cota_max } = t;
      const centro = (cota_min + cota_max) / 2;
      setInfo({ min: cota_min, max: cota_max });

      const geom = new THREE.PlaneGeometry(t.ancho_m, t.alto_m, nx - 1, ny - 1);
      const pos = geom.attributes.position;
      const colores = new Float32Array(pos.count * 3);
      const alturaReal = new Float32Array(pos.count);

      for (let k = 0; k < pos.count; k++) {
        const bruto = alturas[k];
        const h = bruto === SIN_DATO ? cota_min : bruto / 10;
        alturaReal[k] = h;
        pos.setZ(k, (h - centro) * exageracion);
        const [cr, cg, cb] = colorPorAltura((h - cota_min) / (cota_max - cota_min || 1));
        colores[k * 3] = cr;
        colores[k * 3 + 1] = cg;
        colores[k * 3 + 2] = cb;
      }
      geom.setAttribute('color', new THREE.BufferAttribute(colores, 3));
      geom.rotateX(-Math.PI / 2);        // de plano vertical a suelo horizontal
      geom.computeVertexNormals();

      const material = new THREE.MeshLambertMaterial({ vertexColors: true });
      const malla = new THREE.Mesh(geom, material);
      mundo.add(malla);
      desechables.push(geom, material);

      // ── faldas laterales ──
      // Sin esto el modelo se ve como una sábana flotando en el vacío y cuesta
      // leer el relieve; cerrando los cuatro costados se percibe como un bloque
      // de terreno y las alturas se entienden solas.
      const alturaEscena = (i: number, j: number) =>
        (alturaReal[j * nx + i] - centro) * exageracion;
      const px = (i: number) => (i / (nx - 1) - 0.5) * t.ancho_m;
      const pz = (j: number) => (j / (ny - 1) - 0.5) * t.alto_m;
      const fondo = (cota_min - centro) * exageracion - 120;
      const vertices: number[] = [];
      const quad = (
        ax: number, ay: number, az: number, bx: number, by: number, bz: number,
      ) => {
        vertices.push(ax, ay, az, bx, by, bz, bx, fondo, bz);
        vertices.push(ax, ay, az, bx, fondo, bz, ax, fondo, az);
      };
      for (let i = 0; i < nx - 1; i++) {
        quad(px(i), alturaEscena(i, 0), pz(0), px(i + 1), alturaEscena(i + 1, 0), pz(0));
        quad(px(i + 1), alturaEscena(i + 1, ny - 1), pz(ny - 1),
             px(i), alturaEscena(i, ny - 1), pz(ny - 1));
      }
      for (let j = 0; j < ny - 1; j++) {
        quad(px(0), alturaEscena(0, j + 1), pz(j + 1), px(0), alturaEscena(0, j), pz(j));
        quad(px(nx - 1), alturaEscena(nx - 1, j), pz(j),
             px(nx - 1), alturaEscena(nx - 1, j + 1), pz(j + 1));
      }
      const gFalda = new THREE.BufferGeometry();
      gFalda.setAttribute('position',
        new THREE.BufferAttribute(new Float32Array(vertices), 3));
      gFalda.computeVertexNormals();
      const mFalda = new THREE.MeshLambertMaterial({
        color: 0x5b4a3a, side: THREE.DoubleSide,
      });
      mundo.add(new THREE.Mesh(gFalda, mFalda));
      desechables.push(gFalda, mFalda);

      /** Altura del terreno (ya exagerada) en una coordenada UTM. */
      const [x0, y0, x1, y1] = t.bbox_utm;
      const aEscena = (este: number, norte: number) => {
        const u = (este - x0) / (x1 - x0);
        const v = (norte - y0) / (y1 - y0);
        const i = Math.round(u * (nx - 1));
        const j = Math.round((1 - v) * (ny - 1));
        const dentro = i >= 0 && i < nx && j >= 0 && j < ny;
        const h = dentro ? alturaReal[j * nx + i] : cota_min;
        return new THREE.Vector3(
          (u - 0.5) * t.ancho_m,
          (h - centro) * exageracion,
          (0.5 - v) * t.alto_m,
        );
      };

      // ── límite de proyecto sobre el relieve ──
      try {
        const rl = await fetch('/geo/represa/limite_proyecto.geojson');
        const gj = await rl.json();
        for (const f of gj.features ?? []) {
          const anillos = f.geometry?.type === 'Polygon' ? f.geometry.coordinates : [];
          for (const anillo of anillos) {
            const puntos = anillo.map(([lon, lat]: [number, number]) => {
              const { este, norte } = wgs84ToUtm17S(lat, lon);
              const p = aEscena(este, norte);
              p.y += 8;                       // despegarlo para que no se entierre
              return p;
            });
            const g = new THREE.BufferGeometry().setFromPoints(puntos);
            const m = new THREE.LineBasicMaterial({ color: 0xff3b30 });
            mundo.add(new THREE.Line(g, m));
            desechables.push(g, m);
          }
        }
      } catch { /* el relieve se ve igual sin el límite */ }

      // ── rótulos de obra ──
      try {
        const rr = await fetch('/geo/represa/rotulos_obra.geojson');
        const gj = await rr.json();
        const vistos = new Set<string>();
        for (const f of gj.features ?? []) {
          const nombre: string = f.properties?.nombre ?? '';
          const c = f.geometry?.coordinates;
          if (!c || vistos.has(nombre)) continue;
          vistos.add(nombre);
          const { este, norte } = wgs84ToUtm17S(c[1], c[0]);
          const p = aEscena(este, norte);

          const g = new THREE.SphereGeometry(12, 12, 8);
          const m = new THREE.MeshBasicMaterial({ color: 0xffd400 });
          const punto = new THREE.Mesh(g, m);
          punto.position.copy(p).setY(p.y + 20);
          mundo.add(punto);
          desechables.push(g, m);

          const lienzo = document.createElement('canvas');
          lienzo.width = 512;
          lienzo.height = 64;
          const ctx = lienzo.getContext('2d')!;
          ctx.font = 'bold 34px system-ui, sans-serif';
          ctx.fillStyle = 'rgba(8,14,26,0.82)';
          const ancho = ctx.measureText(nombre).width + 24;
          ctx.fillRect(0, 8, ancho, 48);
          ctx.fillStyle = '#ffe680';
          ctx.fillText(nombre, 12, 42);
          const textura = new THREE.CanvasTexture(lienzo);
          const sm = new THREE.SpriteMaterial({ map: textura, depthTest: false });
          const sprite = new THREE.Sprite(sm);
          sprite.scale.set(300, 38, 1);
          sprite.position.copy(p).setY(p.y + 95);
          sprite.center.set(0, 0.5);          // anclar por la izquierda del texto
          mundo.add(sprite);
          desechables.push(textura, sm);
        }
      } catch { /* idem */ }

      const radio = Math.max(t.ancho_m, t.alto_m);
      camara.position.set(radio * 0.45, radio * 0.42, radio * 0.62);
      controles.target.set(0, 0, 0);
      controles.update();
      setCargando(false);
    }

    construir().catch((e) => {
      if (!cancelado) {
        setError(e instanceof Error ? e.message : 'error al construir el terreno');
        setCargando(false);
      }
    });

    const ajustar = () => {
      const { clientWidth: w, clientHeight: h } = nodo;
      if (!w || !h) return;
      camara.aspect = w / h;
      camara.updateProjectionMatrix();
      renderer.setSize(w, h, false);
    };
    ajustar();
    const observador = new ResizeObserver(ajustar);
    observador.observe(nodo);

    const bucle = () => {
      animacion = requestAnimationFrame(bucle);
      controles.update();
      renderer.render(escena, camara);
    };
    bucle();

    return () => {
      cancelado = true;
      cancelAnimationFrame(animacion);
      observador.disconnect();
      controles.dispose();
      desechables.forEach((d) => d.dispose());
      renderer.dispose();
      if (renderer.domElement.parentNode === nodo) {
        nodo.removeChild(renderer.domElement);
      }
    };
  }, [exageracion]);

  return (
    <div className="relative w-full h-full" style={{ background: '#0b1220' }}>
      <div ref={contenedor} className="w-full h-full" />

      {cargando && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="w-7 h-7 text-blue-400 animate-spin" />
            <p className="text-sm text-slate-300">Construyendo el relieve…</p>
          </div>
        </div>
      )}

      {error && (
        <div className="absolute inset-0 flex items-center justify-center p-6">
          <p className="text-sm text-red-300 text-center">{error}</p>
        </div>
      )}

      <div className="absolute top-3 left-3 rounded-lg px-3 py-2 text-xs backdrop-blur"
           style={{ background: 'rgba(8,14,26,0.78)', color: '#cbd5e1' }}>
        <div className="flex items-center gap-2 mb-2 font-semibold text-slate-200">
          <Mountain className="w-4 h-4 text-amber-400" />
          Relieve de la zona de presa
        </div>
        {info && (
          <p className="mb-2">
            Cotas {info.min.toFixed(0)} – {info.max.toFixed(0)} m ·
            desnivel {(info.max - info.min).toFixed(0)} m
          </p>
        )}
        <label className="block">
          Exageración vertical: <b>{exageracion}×</b>
          <input
            type="range" min={1} max={4} step={1}
            value={exageracion}
            onChange={(e) => setExageracion(Number(e.target.value))}
            className="w-40 mt-1 block"
          />
        </label>
        <p className="mt-2 text-[11px] text-slate-400 max-w-[15rem]">
          Arrastra para girar, rueda para acercar. Modelo apoyado en cartografía
          de 5 m: sirve para leer el relieve, no para medir volúmenes.
        </p>
      </div>
    </div>
  );
}
