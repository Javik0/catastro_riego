import { useEffect, useState, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  MapContainer,
  TileLayer,
  GeoJSON,
  CircleMarker,
  Tooltip,
  useMapEvents,
  useMap
} from 'react-leaflet';
import L from 'leaflet';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';
import {
  ArrowLeft,
  Printer,
  FileText,
  Layers,
  Map as MapIcon,
  Compass,
  Calendar,
  Settings,
  Grid
} from 'lucide-react';

import { type FichaPredio } from '../../lib/types';
import {
  PROJECT_SUBTITLE,
  PROJECT_LOCATION,
  LOGO_PICHINCHA,
  LOGO_CONSORCIO
} from '../../lib/constants';
import {
  getComunidadColor,
  SECTOR_COLORS_MAP,
  loadImageBase64,
  calcularEscalaGrafica,
  type EscalaBarraInfo
} from '../../lib/map-print-utils';

import 'leaflet/dist/leaflet.css';

interface Props {
  fichas: FichaPredio[];
  loading: boolean;
}

// Subcomponente para reportar zoom y latitud a la composición
function MapStateTracker({
  onChange
}: {
  onChange: (zoom: number, lat: number, center: L.LatLng) => void;
}) {
  const map = useMapEvents({
    zoomend() {
      onChange(map.getZoom(), map.getCenter().lat, map.getCenter());
    },
    moveend() {
      onChange(map.getZoom(), map.getCenter().lat, map.getCenter());
    }
  });

  // Reportar estado inicial al montar
  useEffect(() => {
    onChange(map.getZoom(), map.getCenter().lat, map.getCenter());
  }, [map]); // eslint-disable-line react-hooks/exhaustive-deps

  return null;
}

// Subcomponente para forzar encuadre de zoom e invalidar el tamaño gris del contenedor
function FitBoundsHandler({
  bounds,
  formato
}: {
  bounds: L.LatLngBoundsExpression | null;
  formato: string;
}) {
  const map = useMapEvents({});
  useEffect(() => {
    const timer = setTimeout(() => {
      map.invalidateSize();
      if (bounds) {
        map.fitBounds(bounds, { padding: [30, 30] });
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [bounds, formato, map]);
  return null;
}

// Subcomponente de Canvas para renderizar fluidamente los 24K polígonos
function AllCatastroLayer({ data }: { data: any }) {
  const map = useMap();
  const layerRef = useRef<L.GeoJSON | null>(null);

  useEffect(() => {
    layerRef.current = L.geoJSON(data as any, {
      renderer: L.canvas({ padding: 0.5 }),
      style: {
        color: '#94a3b8',
        weight: 0.6,
        fillColor: '#cbd5e1',
        fillOpacity: 0.04,
        opacity: 0.5
      },
      interactive: false
    } as any);
    layerRef.current.addTo(map);
    layerRef.current.bringToBack();

    return () => {
      if (layerRef.current) {
        map.removeLayer(layerRef.current);
        layerRef.current = null;
      }
    };
  }, [data, map]);

  return null;
}

export default function MapPrintComposerPage({ fichas, loading }: Props) {
  const navigate = useNavigate();

  // ── Estados de Configuración Cartográfica ──
  const [formato, setFormato] = useState<'A3' | 'A1'>('A3');
  const [modo, setModo] = useState<'general' | 'sector' | 'comunidad'>('general');
  const [selectedSector, setSelectedSector] = useState<string>('Sector 1');
  const [selectedComunidad, setSelectedComunidad] = useState<string>('');
  const [mapBase, setMapBase] = useState<'satelite' | 'topografico'>('satelite');
  const [incluirTabla, setIncluirTabla] = useState<boolean>(true);
  const [incluirFichas, setIncluirFichas] = useState<boolean>(true);
  const [incluirCanales, setIncluirCanales] = useState<boolean>(true);
  const [incluirCatastro, setIncluirCatastro] = useState<boolean>(true);
  const [incluirOtrosPredios, setIncluirOtrosPredios] = useState<boolean>(true);
  
  // Catastro completo 24K
  const [showAllCatastro, setShowAllCatastro] = useState<boolean>(false);
  const [allCatastroData, setAllCatastroData] = useState<any>(null);
  const [cargandoTodosPredios, setCargandoTodosPredios] = useState<boolean>(false);
  const [cultivosData, setCultivosData] = useState<any[]>([]);

  // Textos personalizables del membrete
  const [tituloMap, setTituloMap] = useState<string>('MAPA GENERAL DEL PADRÓN DE USUARIOS');
  const [subtituloMap, setSubtituloMap] = useState<string>(PROJECT_SUBTITLE);

  // ── Capas GeoJSON cargadas ──
  const [catastroData, setCatastroData] = useState<any>(null);
  const [ramalesData, setRamalesData] = useState<any>(null);
  const [comunidadesData, setComunidadesData] = useState<any>(null);
  const [sectoresData, setSectoresData] = useState<any>(null);
  const [prediosAdicionalesData, setPrediosAdicionalesData] = useState<any>(null);

  // ── Estado del Mapa en Pantalla (para escala y exportación) ──
  const [mapZoom, setMapZoom] = useState<number>(14);
  const [mapLat, setMapLat] = useState<number>(0.04);
  const [mapCenter, setMapCenter] = useState<L.LatLng>(new L.LatLng(0.04, -78.15));
  const [exportProgress, setExportProgress] = useState<string | null>(null);

  // Logos cargados en base64 para jsPDF
  const [logosBase64, setLogosBase64] = useState<{ izq: string; der: string } | null>(null);

  // Cargar datos espaciales al montar
  useEffect(() => {
    const timestamp = Date.now();
    fetch(`/geo/catastro_geo.geojson?t=${timestamp}`)
      .then((r) => r.json())
      .then((data) => setCatastroData(data))
      .catch((e) => console.error('Error cargando catastro:', e));

    fetch(`/geo/ramales_riego.geojson?t=${timestamp}`)
      .then((r) => r.json())
      .then((data) => setRamalesData(data))
      .catch((e) => console.error('Error cargando ramales:', e));

    fetch(`/geo/comunidades.geojson?t=${timestamp}`)
      .then((r) => r.json())
      .then((data) => setComunidadesData(data))
      .catch((e) => console.error('Error cargando comunidades:', e));

    fetch(`/geo/sectores.geojson?t=${timestamp}`)
      .then((r) => r.json())
      .then((data) => setSectoresData(data))
      .catch((e) => console.error('Error cargando sectores:', e));

    fetch(`/geo/predios_adicionales.json?t=${timestamp}`)
      .then((r) => r.json())
      .then((data) => setPrediosAdicionalesData(data))
      .catch((e) => console.error('Error cargando predios adicionales:', e));

    fetch(`/geo/cultivos.json?t=${timestamp}`)
      .then((r) => r.json())
      .then((data) => setCultivosData(data))
      .catch((e) => console.error('Error cargando cultivos:', e));

    // Cargar logos
    Promise.all([
      loadImageBase64(LOGO_PICHINCHA),
      loadImageBase64(LOGO_CONSORCIO)
    ]).then(([izqRes, derRes]) => {
      setLogosBase64({ izq: izqRes.data, der: derRes.data });
    }).catch((e) => console.error('Error cargando logos base64:', e));
  }, []);

  // Catastro e irrigación con filtros de visualización
  const fichasConGeo = useMemo(() => {
    return fichas.filter((f) => f.geo && f.geo.lat != null && f.geo.lng != null);
  }, [fichas]);

  // Lista única de comunidades por el sector seleccionado
  const comunidadesDelSector = useMemo(() => {
    if (!comunidadesData) return [];
    return comunidadesData.features
      .filter((f: any) => f.properties?.sector === selectedSector)
      .map((f: any) => f.properties?.comunidad)
      .sort();
  }, [comunidadesData, selectedSector]);

  // Estadísticas agregadas del Dashboard para mostrar en la leyenda del plano
  const statsDashboard = useMemo(() => {
    // Filtrar fichas del grupo actual
    const fichasGrupo = fichas.filter((f) => {
      if (modo === 'sector') return f.sector_investigacion === selectedSector;
      if (modo === 'comunidad') return f.comunidad === selectedComunidad;
      return true;
    });

    const totalFichas = fichasGrupo.length;

    // 1. Métodos de riego
    let gravedadSuma = 0;
    let aspersionSuma = 0;
    let goteoSuma = 0;
    let fichasConRiegoMetodo = 0;

    fichasGrupo.forEach((f) => {
      if (f.metodo_gravedad_pct || f.metodo_aspersion_pct || f.metodo_goteo_pct) {
        gravedadSuma += f.metodo_gravedad_pct || 0;
        aspersionSuma += f.metodo_aspersion_pct || 0;
        goteoSuma += f.metodo_goteo_pct || 0;
        fichasConRiegoMetodo++;
      }
    });

    const gravedadPct = fichasConRiegoMetodo > 0 ? Math.round(gravedadSuma / fichasConRiegoMetodo) : 0;
    const aspersionPct = fichasConRiegoMetodo > 0 ? Math.round(aspersionSuma / fichasConRiegoMetodo) : 0;
    const goteoPct = fichasConRiegoMetodo > 0 ? Math.round(goteoSuma / fichasConRiegoMetodo) : 0;

    // 2. Tenencia de la tierra
    const tenencias: Record<string, number> = {};
    fichasGrupo.forEach((f) => {
      const t = (f.tenencia_predio || 'OTROS').toUpperCase().trim();
      tenencias[t] = (tenencias[t] || 0) + 1;
    });
    const tenenciasSorted = Object.entries(tenencias)
      .map(([name, count]) => ({ name, pct: totalFichas > 0 ? Math.round((count / totalFichas) * 100) : 0 }))
      .sort((a, b) => b.pct - a.pct)
      .slice(0, 3);

    // 3. Reservorios
    const conReservorio = fichasGrupo.filter((f) => f.tiene_reservorio?.toUpperCase().trim() === 'SÍ').length;
    const reservorioPct = totalFichas > 0 ? Math.round((conReservorio / totalFichas) * 100) : 0;

    // 4. Cultivos principales
    const cultivosCounts: Record<string, number> = {};
    if (cultivosData && cultivosData.length > 0) {
      const fichaIdsGrupo = new Set(fichasGrupo.map((f) => f.id));
      const cultivosGrupo = cultivosData.filter((c) => fichaIdsGrupo.has(c.ficha_id));
      
      cultivosGrupo.forEach((c) => {
        const tc = (c.tipo_cultivo || 'OTROS').toUpperCase().trim();
        cultivosCounts[tc] = (cultivosCounts[tc] || 0) + 1;
      });

      const totalCultivos = cultivosGrupo.length;
      const cultivosSorted = Object.entries(cultivosCounts)
        .map(([name, count]) => ({ name, pct: totalCultivos > 0 ? Math.round((count / totalCultivos) * 100) : 0 }))
        .sort((a, b) => b.pct - a.pct)
        .slice(0, 3);

      return {
        gravedadPct,
        aspersionPct,
        goteoPct,
        tenenciasSorted,
        reservorioPct,
        cultivosSorted
      };
    }

    return {
      gravedadPct,
      aspersionPct,
      goteoPct,
      tenenciasSorted,
      reservorioPct,
      cultivosSorted: []
    };
  }, [fichas, modo, selectedSector, selectedComunidad, cultivosData]);

  // Comunidad por defecto al cambiar de sector o modo
  useEffect(() => {
    if (comunidadesDelSector.length > 0) {
      setSelectedComunidad(comunidadesDelSector[0]);
    }
  }, [comunidadesDelSector]);

  // Actualizar título por defecto según el modo seleccionado
  useEffect(() => {
    if (modo === 'general') {
      setTituloMap('MAPA GENERAL DE INVESTIGACIÓN Y CATASTRO');
    } else if (modo === 'sector') {
      setTituloMap(`SISTEMA DE RIEGO - COMPOSICIÓN ${selectedSector.toUpperCase()}`);
    } else if (modo === 'comunidad') {
      setTituloMap(`PLANO PREDIAL - COMUNIDAD: ${selectedComunidad.toUpperCase()}`);
    }
  }, [modo, selectedSector, selectedComunidad]);

  // Encontrar la comunidad actual para enfocar y calcular estadísticas
  const comunidadActualProperties = useMemo(() => {
    if (!comunidadesData || !selectedComunidad) return null;
    const feat = comunidadesData.features.find(
      (f: any) => f.properties?.comunidad === selectedComunidad
    );
    return feat ? feat.properties : null;
  }, [comunidadesData, selectedComunidad]);

  // Encontrar el sector actual para estadísticas
  const sectorActualProperties = useMemo(() => {
    if (!sectoresData || !selectedSector) return null;
    const feat = sectoresData.features.find(
      (f: any) => f.properties?.sector === selectedSector
    );
    return feat ? feat.properties : null;
  }, [sectoresData, selectedSector]);

  // Bounds para enfocar automáticamente en base al modo seleccionado
  const activeBounds = useMemo<L.LatLngBoundsExpression | null>(() => {
    if (modo === 'sector' && sectoresData && selectedSector) {
      const feat = sectoresData.features.find(
        (f: any) => f.properties?.sector === selectedSector
      );
      if (feat && feat.geometry) {
        return L.geoJSON(feat.geometry).getBounds();
      }
    }
    if (modo === 'comunidad' && comunidadesData && selectedComunidad) {
      const feat = comunidadesData.features.find(
        (f: any) => f.properties?.comunidad === selectedComunidad
      );
      if (feat && feat.geometry) {
        return L.geoJSON(feat.geometry).getBounds();
      }
    }
    return null;
  }, [modo, selectedSector, selectedComunidad, sectoresData, comunidadesData]);

  // Mapear comunidades activas a colores consistentes para pintarlas
  const comunidadesColorMap = useMemo(() => {
    if (!comunidadesData) return new Map<string, string>();
    const m = new Map<string, string>();
    const comsSector1 = comunidadesData.features.filter((f: any) => f.properties?.sector === 'Sector 1');
    const comsSector2 = comunidadesData.features.filter((f: any) => f.properties?.sector === 'Sector 2');
    const comsSector3 = comunidadesData.features.filter((f: any) => f.properties?.sector === 'Sector 3');

    comsSector1.forEach((f: any, i: number) => m.set(f.properties.comunidad, getComunidadColor(f.properties.comunidad, 'Sector 1', i)));
    comsSector2.forEach((f: any, i: number) => m.set(f.properties.comunidad, getComunidadColor(f.properties.comunidad, 'Sector 2', i)));
    comsSector3.forEach((f: any, i: number) => m.set(f.properties.comunidad, getComunidadColor(f.properties.comunidad, 'Sector 3', i)));
    return m;
  }, [comunidadesData]);

  // Calcular la escala de la pantalla
  const escalaInfo = useMemo<EscalaBarraInfo>(() => {
    // Dimensiones en píxeles del contenedor del mapa en pantalla en la previsualización
    const mapWidthPx = 700; // Valor aproximado
    const mapWidthMm = formato === 'A3' ? 290 : 590; // Ancho proporcional del mapa en mm
    return calcularEscalaGrafica(mapLat, mapZoom, mapWidthPx, mapWidthMm);
  }, [mapZoom, mapLat, formato]);

  // ─── Exportación a PDF de alta resolución ───
  const handleExportPDF = async () => {
    if (!logosBase64) {
      alert('Los logotipos institucionales aún no se han cargado. Por favor, intente de nuevo en un segundo.');
      return;
    }

    try {
      setExportProgress('Generando composición cartográfica...');
      
      // Ancho y alto en píxeles (150 DPI)
      const anchoPx = formato === 'A3' ? 2480 : 4967;
      const altoPx = formato === 'A3' ? 1754 : 3508;

      // Crear div temporal fuera de pantalla para renderizar el Leaflet a alta resolución
      const printContainer = document.createElement('div');
      printContainer.style.position = 'absolute';
      printContainer.style.left = '-10000px';
      printContainer.style.top = '-10000px';
      
      // Ajustar tamaño del mapa principal dentro del layout en px (aproximadamente 72% del ancho y 82% del alto del papel)
      const mapWidthPx = Math.round(anchoPx * 0.72);
      const mapHeightPx = Math.round(altoPx * 0.82);
      printContainer.style.width = `${mapWidthPx}px`;
      printContainer.style.height = `${mapHeightPx}px`;
      
      document.body.appendChild(printContainer);

      setExportProgress('Renderizando capas cartográficas a alta resolución...');

      const mapDiv = document.createElement('div');
      mapDiv.style.width = '100%';
      mapDiv.style.height = '100%';
      printContainer.appendChild(mapDiv);

      const map = L.map(mapDiv, {
        zoomControl: false,
        attributionControl: false
      });

      if (activeBounds) {
        map.fitBounds(activeBounds, { padding: [40, 40] });
      } else {
        map.setView(mapCenter, mapZoom);
      }

      // Añadir la misma capa base
      const tileUrl = mapBase === 'satelite'
        ? 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
        : 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}';
      
      const tileLayer = L.tileLayer(tileUrl, { maxZoom: 20 });
      tileLayer.addTo(map);

      // Esperar a que se monte el mapa e invalidar tamaño para el renderizado off-screen
      await new Promise<void>((resolve) => {
        map.whenReady(() => {
          setTimeout(() => {
            map.invalidateSize();
            resolve();
          }, 100);
        });
      });

      // Dibujar capas vectoriales filtradas con simbología inteligente en el mapa off-screen
      
      // 1. Canales de Riego
      if (incluirCanales && ramalesData) {
        L.geoJSON(ramalesData, {
          style: { color: '#38bdf8', weight: formato === 'A3' ? 3 : 5, opacity: 0.85, dashArray: '6 3' }
        }).addTo(map);
      }

      // 2. Sectores de Investigación
      if (sectoresData) {
        L.geoJSON(sectoresData, {
          style: (feature) => {
            const sec = feature?.properties?.sector;
            const color = SECTOR_COLORS_MAP[sec] || '#6b7280';
            const isTarget = modo === 'general' || (modo === 'sector' && sec === selectedSector);
            return {
              color,
              weight: isTarget ? (formato === 'A3' ? 3.5 : 6) : 0,
              fillColor: color,
              fillOpacity: isTarget ? (modo === 'general' ? 0.08 : 0.04) : 0,
              opacity: isTarget ? 0.85 : 0,
              dashArray: '8 4'
            };
          }
        }).addTo(map);
      }

      // 3. Comunidades
      if (comunidadesData) {
        L.geoJSON(comunidadesData, {
          style: (feature) => {
            const com = feature?.properties?.comunidad;
            const sec = feature?.properties?.sector;
            const color = comunidadesColorMap.get(com) || '#94a3b8';
            
            // Decidir visibilidad
            let visible = false;
            if (modo === 'general') visible = true;
            else if (modo === 'sector' && sec === selectedSector) visible = true;
            else if (modo === 'comunidad' && com === selectedComunidad) visible = true;

            return {
              color: visible ? color : 'transparent',
              weight: visible ? (formato === 'A3' ? 2.5 : 4) : 0,
              fillColor: visible ? color : 'transparent',
              fillOpacity: visible ? (modo === 'comunidad' ? 0.15 : 0.08) : 0,
              opacity: visible ? 0.8 : 0,
              dashArray: '4 3'
            };
          }
        }).addTo(map);
      }

      // 4. Catastro Rural
      if (incluirCatastro && catastroData) {
        L.geoJSON(catastroData, {
          style: (feature) => {
            const com = feature?.properties?.comunidad;
            const isHighlight = modo === 'comunidad' && com === selectedComunidad;
            return {
              color: isHighlight ? '#f97316' : '#f97316',
              weight: isHighlight ? (formato === 'A3' ? 2 : 3) : (formato === 'A3' ? 1 : 1.5),
              fillColor: isHighlight ? '#f97316' : '#f97316',
              fillOpacity: isHighlight ? 0.2 : 0.05,
              opacity: isHighlight ? 0.9 : 0.6
            };
          }
        }).addTo(map);
      }

      // 4.5 Otros Predios del Regante
      if (incluirOtrosPredios && prediosAdicionalesData) {
        L.geoJSON(prediosAdicionalesData, {
          style: {
            color: '#71717a',
            weight: formato === 'A3' ? 1 : 1.5,
            fillColor: '#a1a1aa',
            fillOpacity: 0.04,
            opacity: 0.6
          }
        }).addTo(map);
      }

      // 4.7 Todos los predios (24K Canvas)
      if (showAllCatastro && allCatastroData) {
        const canvasRenderer = L.canvas({ padding: 0.5 });
        L.geoJSON(allCatastroData, {
          renderer: canvasRenderer,
          style: {
            color: '#cbd5e1',
            weight: formato === 'A3' ? 0.4 : 0.6,
            fillColor: '#cbd5e1',
            fillOpacity: 0.02,
            opacity: 0.4
          }
        } as any).addTo(map);
      }

      // 5. Fichas (Círculos)
      if (incluirFichas && fichasConGeo.length > 0) {
        fichasConGeo.forEach((f) => {
          // Filtrar por modo
          if (modo === 'sector' && f.sector_investigacion !== selectedSector) return;
          if (modo === 'comunidad' && f.comunidad !== selectedComunidad) return;

          const comColor = comunidadesColorMap.get(f.comunidad || '') || '#94a3b8';
          const latlng = L.latLng(f.geo!.lat, f.geo!.lng);

          L.circleMarker(latlng, {
            radius: formato === 'A3' ? 5 : 8,
            fillColor: comColor,
            fillOpacity: 0.9,
            color: '#ffffff',
            weight: formato === 'A3' ? 1.5 : 2.5
          }).addTo(map);
        });
      }

      // Esperar un delay explícito de 3.5 segundos para que todas las tiles se descarguen y dibujen en el div gigante
      setExportProgress('Descargando y renderizando fotografía satelital de alta definición...');
      await new Promise<void>((resolve) => {
        setTimeout(resolve, 3500);
      });

      // Capturar usando html2canvas con proxy para imágenes externas y escalamiento
      const canvas = await html2canvas(mapDiv, {
        useCORS: true,
        allowTaint: true,
        scale: 1, // Ya tiene el tamaño pixel exacto offscreen
        logging: false
      });

      const mapImgBase64 = canvas.toDataURL('image/jpeg', 0.93);

      // Destruir mapa off-screen temporal
      map.remove();
      document.body.removeChild(printContainer);

      setExportProgress('Componiendo PDF con membretes vectoriales...');

      // Crear documento jsPDF en la orientación correcta (landscape)
      const doc = new jsPDF({
        orientation: 'landscape',
        unit: 'mm',
        format: formato.toLowerCase() // 'a3' o 'a1'
      });

      // ── Componer PDF ──
      // Márgenes y tamaños basados en A3 (420 x 297) o A1 (841 x 594)
      const width = doc.internal.pageSize.getWidth();
      const height = doc.internal.pageSize.getHeight();
      
      const margin = formato === 'A3' ? 10 : 20;

      // 1. Dibujar membrete superior
      doc.setFillColor(248, 250, 252); // Gris muy claro slate-50
      const headerHeight = formato === 'A3' ? 24 : 42;
      doc.rect(margin, margin, width - margin * 2, headerHeight, 'F');
      doc.setDrawColor(226, 232, 240); // Borde slate-200
      doc.rect(margin, margin, width - margin * 2, headerHeight, 'S');

      // Logos
      // Pichincha (Izq)
      doc.addImage(logosBase64!.izq, 'PNG', margin + (formato === 'A3' ? 4 : 8), margin + (formato === 'A3' ? 3 : 5), formato === 'A3' ? 30 : 55, formato === 'A3' ? 18 : 32);
      // Consorcio (Der)
      const logoDerWidth = formato === 'A3' ? 24 : 44;
      doc.addImage(logosBase64!.der, 'PNG', width - margin - (formato === 'A3' ? 4 : 8) - logoDerWidth, margin + (formato === 'A3' ? 5 : 9), logoDerWidth, formato === 'A3' ? 14 : 24);

      // Título
      doc.setFont('Helvetica', 'bold');
      doc.setFontSize(formato === 'A3' ? 13 : 24);
      doc.setTextColor(15, 23, 42); // slate-900
      doc.text(tituloMap, width / 2, margin + (formato === 'A3' ? 8 : 15), { align: 'center' });

      // Subtítulo
      doc.setFont('Helvetica', 'normal');
      doc.setFontSize(formato === 'A3' ? 9 : 15);
      doc.setTextColor(71, 85, 105); // slate-600
      doc.text(subtituloMap, width / 2, margin + (formato === 'A3' ? 14 : 24), { align: 'center' });
      doc.setFontSize(formato === 'A3' ? 7.5 : 12);
      doc.text(PROJECT_LOCATION, width / 2, margin + (formato === 'A3' ? 18 : 31), { align: 'center' });

      // 2. Insertar Imagen de Mapa
      // Posición del mapa (ocupa el 72% del ancho)
      const mapX = margin;
      const mapY = margin + headerHeight + (formato === 'A3' ? 4 : 8);
      const mapW = (width - margin * 2) * 0.72;
      const mapH = height - mapY - margin - (formato === 'A3' ? 18 : 32); // Deja espacio para membrete inferior

      doc.addImage(mapImgBase64, 'JPEG', mapX, mapY, mapW, mapH);
      doc.setDrawColor(203, 213, 225); // slate-300
      doc.rect(mapX, mapY, mapW, mapH, 'S');

      // 3. Insertar leyenda lateral capturada directamente del DOM para conservar gráficos premium de Dashboard
      const leyX = mapX + mapW + (formato === 'A3' ? 4 : 8);
      const leyY = mapY;
      const leyW = width - margin - leyX;
      const leyH = mapH;

      setExportProgress('Generando e integrando infografía cartográfica y gráficos estadísticos...');
      
      const leyendaElement = document.getElementById('composicion-leyenda');
      if (leyendaElement) {
        const origOverflow = leyendaElement.style.overflow;
        const origMaxHeight = leyendaElement.style.maxHeight;
        
        leyendaElement.style.overflow = 'visible';
        leyendaElement.style.maxHeight = 'none';

        try {
          const canvasLeyenda = await html2canvas(leyendaElement, {
            scale: formato === 'A3' ? 3.5 : 5,
            useCORS: true,
            allowTaint: true,
            logging: false,
            backgroundColor: '#ffffff'
          });

          const imgLeyenda = canvasLeyenda.toDataURL('image/jpeg', 0.95);
          doc.addImage(imgLeyenda, 'JPEG', leyX, leyY, leyW, leyH);
        } catch (err) {
          console.error('Error al capturar la leyenda:', err);
          doc.setFillColor(255, 255, 255);
          doc.rect(leyX, leyY, leyW, leyH, 'F');
          doc.setDrawColor(203, 213, 225);
          doc.rect(leyX, leyY, leyW, leyH, 'S');
          doc.setFont('Helvetica', 'bold');
          doc.setFontSize(12);
          doc.text('Error al generar Leyenda', leyX + 10, leyY + 15);
        } finally {
          leyendaElement.style.overflow = origOverflow;
          leyendaElement.style.maxHeight = origMaxHeight;
        }
      } else {
        doc.setFillColor(255, 255, 255);
        doc.rect(leyX, leyY, leyW, leyH, 'F');
        doc.setDrawColor(203, 213, 225);
        doc.rect(leyX, leyY, leyW, leyH, 'S');
      }

      // 5. Membrete inferior (Escala y créditos vectoriales)
      const footerY = height - margin - (formato === 'A3' ? 8 : 16);
      doc.setFillColor(248, 250, 252);
      const footerH = formato === 'A3' ? 10 : 18;
      doc.rect(margin, footerY, width - margin * 2, footerH, 'F');
      doc.setDrawColor(226, 232, 240);
      doc.rect(margin, footerY, width - margin * 2, footerH, 'S');

      // Barra de escala calculada
      const escWidthMm = escalaInfo.anchoMm;
      const scaleX = margin + (formato === 'A3' ? 4 : 8);
      const scaleY = footerY + (formato === 'A3' ? 5 : 9);

      // Dibujar barra de escala cartográfica (rectángulo negro y blanco)
      doc.setFillColor(0, 0, 0);
      doc.rect(scaleX, scaleY - (formato === 'A3' ? 1.5 : 3), escWidthMm / 2, formato === 'A3' ? 1.5 : 3, 'F');
      doc.setFillColor(255, 255, 255);
      doc.rect(scaleX + escWidthMm / 2, scaleY - (formato === 'A3' ? 1.5 : 3), escWidthMm / 2, formato === 'A3' ? 1.5 : 3, 'F');
      doc.setDrawColor(0, 0, 0);
      doc.rect(scaleX, scaleY - (formato === 'A3' ? 1.5 : 3), escWidthMm, formato === 'A3' ? 1.5 : 3, 'S');

      // Texto de escala
      doc.setFont('Helvetica', 'bold');
      doc.setFontSize(formato === 'A3' ? 7 : 11);
      doc.setTextColor(15, 23, 42);
      doc.text(escalaInfo.label, scaleX + escWidthMm + 2, scaleY);

      // Proyección SRC (Centrado dinámicamente en el papel)
      doc.setFont('Helvetica', 'normal');
      doc.setFontSize(formato === 'A3' ? 7.5 : 12);
      doc.text(`SRC: WGS 84 / UTM zone 17S (EPSG:32717)`, width / 2, footerY + (formato === 'A3' ? 6.5 : 11.5), { align: 'center' });

      // Flecha de Norte (Ubicado a la derecha de la escala gráfica para evitar solapamiento)
      const northX = scaleX + escWidthMm + (formato === 'A3' ? 15 : 25);
      const northY = footerY + (formato === 'A3' ? 5 : 9);
      doc.setDrawColor(0, 0, 0);
      doc.setLineWidth(formato === 'A3' ? 0.3 : 0.6);
      // Triángulo del Norte
      doc.line(northX, northY - (formato === 'A3' ? 3 : 5.5), northX, northY + (formato === 'A3' ? 3 : 5.5)); // Eje vertical
      doc.line(northX - (formato === 'A3' ? 2 : 3.5), northY - (formato === 'A3' ? 0.5 : 1), northX, northY - (formato === 'A3' ? 3 : 5.5)); // Izq
      doc.line(northX + (formato === 'A3' ? 2 : 3.5), northY - (formato === 'A3' ? 0.5 : 1), northX, northY - (formato === 'A3' ? 3 : 5.5)); // Der
      doc.setFont('Helvetica', 'bold');
      doc.setFontSize(formato === 'A3' ? 6.5 : 10);
      doc.text('N', northX - (formato === 'A3' ? 1 : 2), northY - (formato === 'A3' ? 3.5 : 6.5));
      doc.setLineWidth(0.2); // reset

      // Créditos y Fecha (Alineados dinámicamente a la derecha)
      doc.setFont('Helvetica', 'normal');
      doc.setFontSize(formato === 'A3' ? 7.5 : 12);
      doc.setTextColor(71, 85, 105);
      const dateStr = new Date().toLocaleDateString('es-EC', { year: 'numeric', month: '2-digit', day: '2-digit' });
      doc.text(`Fecha: ${dateStr}`, width - margin - (formato === 'A3' ? 42 : 80), footerY + (formato === 'A3' ? 6.5 : 11.5));
      doc.setFont('Helvetica', 'bold');
      doc.text('Consorcio Cayambe SPT', width - margin - (formato === 'A3' ? 4 : 8), footerY + (formato === 'A3' ? 6.5 : 11.5), { align: 'right' });

      // Guardar PDF
      const nameClean = tituloMap.toLowerCase().replace(/[^a-z0-9]/g, '_');
      doc.save(`mapa_${nameClean}_${formato.toLowerCase()}.pdf`);
      setExportProgress(null);
    } catch (err) {
      console.error(err);
      alert('Ocurrió un error al generar el PDF cartográfico. Por favor intente nuevamente.');
      setExportProgress(null);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col">
      {/* Header Superior del Compositor */}
      <header className="h-14 border-b border-slate-800 bg-slate-950 flex items-center justify-between px-6 z-10">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/mapa')}
            className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-slate-100 transition-colors"
            title="Volver al mapa interactivo"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-base font-bold flex items-center gap-2">
              <Grid className="w-4 h-4 text-blue-500" />
              Diseñador de Impresión Cartográfica
            </h1>
            <p className="text-[10px] text-slate-400">
              Composición de hojas de plano A1 y A3 estilo QGIS Layout
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleExportPDF}
            disabled={exportProgress != null}
            className="flex items-center gap-2 px-4 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 text-white font-medium text-xs rounded-lg transition-colors shadow-lg cursor-pointer"
          >
            <Printer className="w-4 h-4" />
            {exportProgress ? 'Exportando...' : 'Exportar PDF'}
          </button>
        </div>
      </header>

      {/* Cuerpo Principal */}
      <div className="flex-1 flex overflow-hidden">
        {/* Panel Izquierdo: Configuración */}
        <aside className="w-80 border-r border-slate-800 bg-slate-950 p-6 flex flex-col gap-6 overflow-y-auto">
          {/* Formato de papel */}
          <div className="space-y-2">
            <label className="text-[11px] font-bold tracking-wider text-slate-400 flex items-center gap-1.5">
              <Settings className="w-3.5 h-3.5 text-blue-500" />
              FORMATO DE HOJA
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => setFormato('A3')}
                className={`py-2 text-xs font-semibold rounded-lg border transition-colors cursor-pointer ${
                  formato === 'A3'
                    ? 'bg-blue-600/10 border-blue-500 text-blue-400'
                    : 'bg-slate-900 border-slate-800 hover:border-slate-700 text-slate-300'
                }`}
              >
                A3 (42 x 29.7 cm)
              </button>
              <button
                onClick={() => setFormato('A1')}
                className={`py-2 text-xs font-semibold rounded-lg border transition-colors cursor-pointer ${
                  formato === 'A1'
                    ? 'bg-blue-600/10 border-blue-500 text-blue-400'
                    : 'bg-slate-900 border-slate-800 hover:border-slate-700 text-slate-300'
                }`}
              >
                A1 (84 x 59.4 cm)
              </button>
            </div>
          </div>

          {/* Modo temático */}
          <div className="space-y-2">
            <label className="text-[11px] font-bold tracking-wider text-slate-400 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-blue-500" />
              MODO CARTOGRÁFICO
            </label>
            <select
              value={modo}
              onChange={(e) => setModo(e.target.value as any)}
              className="w-full bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-100 rounded-lg py-2 px-3 text-xs focus:outline-none focus:border-blue-500 cursor-pointer"
            >
              <option value="general">Mapa General del Proyecto</option>
              <option value="sector">Mapa de Sector</option>
              <option value="comunidad">Mapa de Comunidad</option>
            </select>
          </div>

          {/* Selectores dinámicos según modo */}
          {modo === 'sector' && (
            <div className="space-y-2">
              <label className="text-[11px] font-bold tracking-wider text-slate-400">
                SELECCIONAR SECTOR
              </label>
              <select
                value={selectedSector}
                onChange={(e) => setSelectedSector(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 text-slate-100 rounded-lg py-2 px-3 text-xs focus:outline-none focus:border-blue-500 cursor-pointer"
              >
                <option value="Sector 1">Sector 1</option>
                <option value="Sector 2">Sector 2</option>
                <option value="Sector 3">Sector 3</option>
              </select>
            </div>
          )}

          {modo === 'comunidad' && (
            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-[11px] font-bold tracking-wider text-slate-400">
                  FILTRAR POR SECTOR
                </label>
                <select
                  value={selectedSector}
                  onChange={(e) => setSelectedSector(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 text-slate-100 rounded-lg py-2 px-3 text-xs focus:outline-none focus:border-blue-500 cursor-pointer"
                >
                  <option value="Sector 1">Sector 1</option>
                  <option value="Sector 2">Sector 2</option>
                  <option value="Sector 3">Sector 3</option>
                </select>
              </div>

              <div className="space-y-2">
                <label className="text-[11px] font-bold tracking-wider text-slate-400">
                  SELECCIONAR COMUNIDAD
                </label>
                <select
                  value={selectedComunidad}
                  onChange={(e) => setSelectedComunidad(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 text-slate-100 rounded-lg py-2 px-3 text-xs focus:outline-none focus:border-blue-500 cursor-pointer"
                >
                  {comunidadesDelSector.map((c: string) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}

          {/* Título de Mapa */}
          <div className="space-y-2">
            <label className="text-[11px] font-bold tracking-wider text-slate-400 flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-blue-500" />
              TÍTULO DEL MAPA
            </label>
            <input
              type="text"
              value={tituloMap}
              onChange={(e) => setTituloMap(e.target.value)}
              className="w-full bg-slate-900 border border-slate-800 text-slate-100 rounded-lg py-2 px-3 text-xs focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* Subtítulo de Mapa */}
          <div className="space-y-2">
            <label className="text-[11px] font-bold tracking-wider text-slate-400">
              SUBTÍTULO DEL MAPA
            </label>
            <textarea
              value={subtituloMap}
              onChange={(e) => setSubtituloMap(e.target.value)}
              rows={2}
              className="w-full bg-slate-900 border border-slate-800 text-slate-100 rounded-lg py-2 px-3 text-xs focus:outline-none focus:border-blue-500 resize-none"
            />
          </div>

          {/* Capas y Capas base */}
          <div className="space-y-3">
            <label className="text-[11px] font-bold tracking-wider text-slate-400 flex items-center gap-1.5">
              <MapIcon className="w-3.5 h-3.5 text-blue-500" />
              CAPAS A MOSTRAR
            </label>

            <div className="space-y-2">
              <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={incluirCanales}
                  onChange={(e) => setIncluirCanales(e.target.checked)}
                  className="rounded border-slate-800 text-blue-600 bg-slate-900 focus:ring-0 focus:ring-offset-0"
                />
                Canales de Riego (Ramales)
              </label>

              <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={incluirCatastro}
                  onChange={(e) => setIncluirCatastro(e.target.checked)}
                  className="rounded border-slate-800 text-blue-600 bg-slate-900 focus:ring-0 focus:ring-offset-0"
                />
                Catastro Rural (Predios)
              </label>

              <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={incluirFichas}
                  onChange={(e) => setIncluirFichas(e.target.checked)}
                  className="rounded border-slate-800 text-blue-600 bg-slate-900 focus:ring-0 focus:ring-offset-0"
                />
                Puntos de Fichas (GPS)
              </label>

              <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer" title="Polígonos adicionales de catastro sin ficha de campo">
                <input
                  type="checkbox"
                  checked={incluirOtrosPredios}
                  onChange={(e) => setIncluirOtrosPredios(e.target.checked)}
                  className="rounded border-slate-800 text-blue-600 bg-slate-900 focus:ring-0 focus:ring-offset-0"
                />
                Otros Predios del Regante
              </label>

              <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer" title="Cargar los 24K polígonos catastrales del cantón (Dibujado en Canvas)">
                <input
                  type="checkbox"
                  checked={showAllCatastro}
                  onChange={async (e) => {
                    const checked = e.target.checked;
                    setShowAllCatastro(checked);
                    if (checked && !allCatastroData) {
                      setCargandoTodosPredios(true);
                      try {
                        const timestamp = Date.now();
                        const res = await fetch(`/geo/catastro_poligonos.json?t=${timestamp}`);
                        const data = await res.json();
                        const features = Object.entries(data).map(([fid, geom]) => ({
                          type: 'Feature' as const,
                          properties: { fid: Number(fid) },
                          geometry: geom as any,
                        }));
                        setAllCatastroData({ type: 'FeatureCollection', features });
                      } catch (err) {
                        console.error('Error cargando catastro completo:', err);
                      } finally {
                        setCargandoTodosPredios(false);
                      }
                    }
                  }}
                  className="rounded border-slate-800 text-blue-600 bg-slate-900 focus:ring-0 focus:ring-offset-0"
                />
                <span>Todos los predios (24K)</span>
                {cargandoTodosPredios && <span className="text-[10px] text-blue-400 animate-pulse ml-1">(Cargando...)</span>}
              </label>
            </div>
          </div>

          {/* Selección de Mapa Base */}
          <div className="space-y-2">
            <label className="text-[11px] font-bold tracking-wider text-slate-400">
              MAPA BASE (FONDO)
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => setMapBase('satelite')}
                className={`py-2 text-[10px] font-semibold rounded-lg border transition-colors cursor-pointer ${
                  mapBase === 'satelite'
                    ? 'bg-blue-600/10 border-blue-500 text-blue-400'
                    : 'bg-slate-900 border-slate-800 hover:border-slate-700 text-slate-300'
                }`}
              >
                ESRI Satélite
              </button>
              <button
                onClick={() => setMapBase('topografico')}
                className={`py-2 text-[10px] font-semibold rounded-lg border transition-colors cursor-pointer ${
                  mapBase === 'topografico'
                    ? 'bg-blue-600/10 border-blue-500 text-blue-400'
                    : 'bg-slate-900 border-slate-800 hover:border-slate-700 text-slate-300'
                }`}
              >
                ESRI Topográfico
              </button>
            </div>
          </div>

          {/* Tabla de resumen */}
          <div className="space-y-2">
            <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={incluirTabla}
                onChange={(e) => setIncluirTabla(e.target.checked)}
                className="rounded border-slate-800 text-blue-600 bg-slate-900 focus:ring-0 focus:ring-offset-0"
              />
              Incluir resumen de datos en leyenda
            </label>
          </div>
        </aside>

        {/* Panel Central: Lienzo de Composición */}
        <main className="flex-1 bg-slate-800 overflow-auto p-8 flex items-center justify-center relative">
          {/* Indicador de progreso al exportar */}
          {exportProgress && (
            <div className="absolute inset-0 bg-slate-950/85 z-[3000] flex flex-col items-center justify-center gap-4">
              <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <p className="text-sm font-semibold text-slate-200">{exportProgress}</p>
            </div>
          )}

          {/* Lienzo del Papel (Relación aspect A3/A1 apaisado) */}
          <div
            id="print-sheet-canvas"
            className="bg-white text-slate-900 shadow-2xl p-4 flex flex-col justify-between select-none relative transition-all"
            style={{
              width: formato === 'A3' ? '840px' : '1120px',
              height: formato === 'A3' ? '594px' : '792px',
              border: '1px solid #cbd5e1'
            }}
          >
            {/* ── 1. Membrete Superior ── */}
            <div className="h-14 border border-slate-200 bg-slate-50 flex items-center justify-between px-4 py-1.5 relative overflow-hidden">
              <img src="/logo-izq.png" alt="Pichincha" className="h-9 object-contain" />
              
              <div className="text-center flex-1 mx-4">
                <h2 className="text-[10px] font-bold text-slate-900 leading-tight uppercase">
                  {tituloMap}
                </h2>
                <p className="text-[7.5px] text-slate-600 leading-none mt-0.5">
                  {subtituloMap}
                </p>
                <p className="text-[7px] text-slate-500 leading-none mt-0.5">
                  {PROJECT_LOCATION}
                </p>
              </div>

              <img src="/logo-der.png" alt="Consorcio" className="h-9 object-contain" />
            </div>

            {/* ── 2. Cuerpo Central: Mapa + Leyenda ── */}
            <div className="flex-1 flex gap-2 my-2 min-h-0 relative">
              {/* Contenedor del Mapa interactivo de visualización */}
              <div className="flex-1 border border-slate-300 relative h-full bg-slate-100">
                {!loading && (
                  <MapContainer
                    center={[0.04, -78.15]}
                    zoom={14}
                    zoomControl={false}
                    className="w-full h-full"
                  >
                    {/* Basemap */}
                    <TileLayer
                      url={
                        mapBase === 'satelite'
                          ? 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
                          : 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}'
                      }
                    />

                    {/* Tracker de zoom y coordenadas */}
                    <MapStateTracker
                      onChange={(z, lt, center) => {
                        setMapZoom(z);
                        setMapLat(lt);
                        setMapCenter(center);
                      }}
                    />

                    {/* Handler para ajustar zoom automático */}
                    {activeBounds && <FitBoundsHandler bounds={activeBounds} formato={formato} />}

                    {/* Canales de riego */}
                    {incluirCanales && ramalesData && (
                      <GeoJSON
                        key={`print-ramales-${incluirCanales}`}
                        data={ramalesData}
                        style={{ color: '#38bdf8', weight: 2, opacity: 0.85, dashArray: '4 2' }}
                      />
                    )}

                    {/* Sectores */}
                    {sectoresData && (
                      <GeoJSON
                        key={`print-sectores-${modo}-${selectedSector}`}
                        data={sectoresData}
                        style={(feature) => {
                          const sec = feature?.properties?.sector;
                          const color = SECTOR_COLORS_MAP[sec] || '#6b7280';
                          const isTarget = modo === 'general' || (modo === 'sector' && sec === selectedSector);
                          return {
                            color,
                            weight: isTarget ? 2.5 : 0,
                            fillColor: color,
                            fillOpacity: isTarget ? (modo === 'general' ? 0.08 : 0.04) : 0,
                            opacity: isTarget ? 0.85 : 0,
                            dashArray: '6 3'
                          };
                        }}
                      />
                    )}

                    {/* Comunidades */}
                    {comunidadesData && (
                      <GeoJSON
                        key={`print-comunidades-${modo}-${selectedSector}-${selectedComunidad}`}
                        data={comunidadesData}
                        style={(feature) => {
                          const com = feature?.properties?.comunidad;
                          const sec = feature?.properties?.sector;
                          const color = comunidadesColorMap.get(com) || '#94a3b8';
                          
                          // Decidir visibilidad
                          let visible = false;
                          if (modo === 'general') visible = true;
                          else if (modo === 'sector' && sec === selectedSector) visible = true;
                          else if (modo === 'comunidad' && com === selectedComunidad) visible = true;

                          return {
                            color: visible ? color : 'transparent',
                            weight: visible ? 1.8 : 0,
                            fillColor: visible ? color : 'transparent',
                            fillOpacity: visible ? (modo === 'comunidad' ? 0.15 : 0.08) : 0,
                            opacity: visible ? 0.8 : 0,
                            dashArray: '3 2'
                          };
                        }}
                      />
                    )}

                    {/* Catastro Rural */}
                    {incluirCatastro && catastroData && (
                      <GeoJSON
                        key={`print-catastro-${modo}-${selectedComunidad}`}
                        data={catastroData}
                        style={(feature) => {
                          const com = feature?.properties?.comunidad;
                          const isHighlight = modo === 'comunidad' && com === selectedComunidad;
                          return {
                            color: isHighlight ? '#f97316' : '#f97316',
                            weight: isHighlight ? 1.5 : 0.8,
                            fillColor: isHighlight ? '#f97316' : '#f97316',
                            fillOpacity: isHighlight ? 0.15 : 0.04,
                            opacity: isHighlight ? 0.85 : 0.5
                          };
                        }}
                      />
                    )}

                    {/* Otros Predios del Regante */}
                    {incluirOtrosPredios && prediosAdicionalesData && (
                      <GeoJSON
                        key={`print-adicionales-${incluirOtrosPredios}`}
                        data={prediosAdicionalesData}
                        style={{
                          color: '#a1a1aa',
                          weight: 1,
                          fillColor: '#d4d4d8',
                          fillOpacity: 0.05,
                          opacity: 0.6
                        }}
                      />
                    )}

                    {/* Todos los predios (24K Canvas) */}
                    {showAllCatastro && allCatastroData && (
                      <AllCatastroLayer data={allCatastroData} />
                    )}

                    {/* Puntos de fichas */}
                    {incluirFichas &&
                      fichasConGeo.map((f) => {
                        // Filtrar por modo en previsualización
                        if (modo === 'sector' && f.sector_investigacion !== selectedSector) return null;
                        if (modo === 'comunidad' && f.comunidad !== selectedComunidad) return null;

                         const color = comunidadesColorMap.get(f.comunidad || '') || '#94a3b8';
                        return (
                          <CircleMarker
                            key={f.id}
                            center={[f.geo!.lat, f.geo!.lng]}
                            radius={4}
                            fillColor={color}
                            fillOpacity={0.9}
                            color="#ffffff"
                            weight={1}
                          >
                            <Tooltip sticky>
                              <b>{f.propietario}</b>
                              <br />
                              Comunidad: {f.comunidad}
                            </Tooltip>
                          </CircleMarker>
                        );
                      })}
                  </MapContainer>
                )}

                {/* Controles de zoom falsos (estilo cartográfico) */}
                <div className="absolute top-2 left-2 bg-white/95 border border-slate-300 rounded shadow-md z-[1000] p-1 flex flex-col gap-1">
                  <div className="text-[7.5px] font-bold text-slate-800 text-center px-1">
                    Z:{mapZoom}
                  </div>
                </div>
              </div>

              {/* Leyenda Lateral */}
              <div id="composicion-leyenda" className="w-[185px] border border-slate-300 bg-white flex flex-col justify-start overflow-hidden">
                <div className="bg-slate-100 border-b border-slate-300 py-1.5 text-center text-[7.5px] font-bold text-slate-800 tracking-wider">
                  LEYENDA CARTOGRÁFICA
                </div>

                <div className="p-2 space-y-3 overflow-y-auto text-[7px] text-slate-700">
                  {/* Canales */}
                  {incluirCanales && (
                    <div className="flex items-center gap-2">
                      <div className="w-5 h-0.5 border-t-2 border-dashed border-sky-400" />
                      <span>Canales de Riego (Ramales)</span>
                    </div>
                  )}

                  {/* Catastro */}
                  {incluirCatastro && (
                    <div className="flex items-center gap-2">
                      <div className="w-5 h-3 bg-orange-500/10 border border-orange-500" />
                      <span>Catastro Rural (Predios)</span>
                    </div>
                  )}

                  {/* Otros Predios */}
                  {incluirOtrosPredios && (
                    <div className="flex items-center gap-2">
                      <div className="w-5 h-3 bg-zinc-500/5 border border-zinc-400 border-dashed" />
                      <span>Otros Predios del Regante</span>
                    </div>
                  )}

                  {/* Elementos dinámicos por modo */}
                  {modo === 'general' && sectoresData && (
                    <div className="space-y-1.5">
                      <p className="font-bold text-slate-800">Sectores de Investigación:</p>
                      {sectoresData.features.map((s: any) => {
                        const name = s.properties?.sector;
                        const count = s.properties?.total_fichas || 0;
                        const color = SECTOR_COLORS_MAP[name] || '#6b7280';
                        return (
                          <div key={name} className="flex items-center gap-2 ml-1">
                            <div className="w-4 h-2.5" style={{ backgroundColor: color }} />
                            <span className="truncate">
                              {name} ({count})
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {modo === 'sector' && comunidadesData && (
                    <div className="space-y-1.5">
                      <p className="font-bold text-slate-800">Comunidades de {selectedSector}:</p>
                      <div className="max-h-32 overflow-y-auto space-y-1">
                        {comunidadesData.features
                          .filter((f: any) => f.properties?.sector === selectedSector)
                          .slice(0, 12)
                          .map((c: any) => {
                             const name = c.properties?.comunidad || '';
                             const count = c.properties?.total_fichas || 0;
                             const color = comunidadesColorMap.get(name) || '#94a3b8';
                            return (
                              <div key={name} className="flex items-center gap-2 ml-1">
                                <div className="w-3.5 h-2" style={{ backgroundColor: color }} />
                                <span className="truncate">
                                  {name} ({count})
                                </span>
                              </div>
                            );
                          })}
                        {comunidadesDelSector.length > 12 && (
                          <p className="text-[6.5px] italic text-slate-500 ml-1">
                            + {comunidadesDelSector.length - 12} comunidades más
                          </p>
                        )}
                      </div>
                    </div>
                  )}

                  {modo === 'comunidad' && (
                    <div className="space-y-1.5">
                      <p className="font-bold text-slate-800">Comunidad Seleccionada:</p>
                      <div className="flex items-center gap-2 ml-1">
                         <div
                           className="w-4 h-2.5"
                           style={{
                             backgroundColor: comunidadesColorMap.get(selectedComunidad || '') || '#94a3b8'
                           }}
                         />
                        <span className="font-semibold truncate">{selectedComunidad}</span>
                      </div>
                    </div>
                  )}

                  {/* Fichas */}
                  {incluirFichas && (
                    <div className="flex items-center gap-2">
                      <div className="w-2.5 h-2.5 rounded-full bg-red-600 border border-white" />
                      <span>Ficha investigada (Punto GPS)</span>
                    </div>
                  )}

                  {/* Resumen de datos y gráficos del Dashboard */}
                  {incluirTabla && (
                    <div className="border-t border-slate-200 pt-2 space-y-2">
                      <p className="font-bold text-slate-800">RESUMEN DE DATOS:</p>
                      <div className="grid grid-cols-2 gap-y-0.5 text-[6.5px]">
                        <span className="font-medium text-slate-500">Fichas:</span>
                        <span className="font-bold text-right">
                          {modo === 'general'
                            ? fichas.length
                            : modo === 'sector'
                            ? sectorActualProperties?.total_fichas || 0
                            : comunidadActualProperties?.total_fichas || 0}
                        </span>

                        <span className="font-medium text-slate-500">Área Riego:</span>
                        <span className="font-bold text-right">
                          {modo === 'general'
                            ? (fichas.reduce((acc, c) => acc + (c.area_riego || 0), 0) / 10000).toFixed(1)
                            : modo === 'sector'
                            ? Number(sectorActualProperties?.area_riego_ha || 0).toFixed(1)
                            : Number(comunidadActualProperties?.area_riego_ha || 0).toFixed(1)}{' '}
                          ha
                        </span>

                        <span className="font-medium text-slate-500">Caudal:</span>
                        <span className="font-bold text-right">
                          {modo === 'general'
                            ? fichas.reduce((acc, c) => acc + (c.caudal_valor || 0), 0).toFixed(1)
                            : modo === 'sector'
                            ? Number(sectorActualProperties?.caudal_total_ls || 0).toFixed(1)
                            : Number(comunidadActualProperties?.caudal_total_ls || 0).toFixed(1)}{' '}
                          l/s
                        </span>

                        <span className="font-medium text-slate-500">Área Geo:</span>
                        <span className="font-bold text-right">
                          {modo === 'general'
                            ? '2,450.3'
                            : modo === 'sector'
                            ? Number(sectorActualProperties?.area_dissolve_ha || 0).toFixed(1)
                            : Number(comunidadActualProperties?.area_dissolve_ha || 0).toFixed(1)}{' '}
                          ha
                        </span>
                      </div>

                      {/* Métodos de Riego */}
                      <div className="border-t border-slate-100 pt-1.5 space-y-1">
                        <p className="font-bold text-slate-800 uppercase tracking-wide text-[5.5px]">Métodos de Riego:</p>
                        <div className="space-y-1 text-[5px]">
                          <div>
                            <div className="flex justify-between text-slate-600 mb-0.5">
                              <span>Gravedad</span>
                              <span className="font-bold">{statsDashboard.gravedadPct}%</span>
                            </div>
                            <div className="w-full bg-slate-100 h-1 rounded-full overflow-hidden">
                              <div className="bg-amber-600 h-full rounded-full" style={{ width: `${statsDashboard.gravedadPct}%` }} />
                            </div>
                          </div>
                          <div>
                            <div className="flex justify-between text-slate-600 mb-0.5">
                              <span>Aspersión</span>
                              <span className="font-bold">{statsDashboard.aspersionPct}%</span>
                            </div>
                            <div className="w-full bg-slate-100 h-1 rounded-full overflow-hidden">
                              <div className="bg-sky-500 h-full rounded-full" style={{ width: `${statsDashboard.aspersionPct}%` }} />
                            </div>
                          </div>
                          <div>
                            <div className="flex justify-between text-slate-600 mb-0.5">
                              <span>Goteo</span>
                              <span className="font-bold">{statsDashboard.goteoPct}%</span>
                            </div>
                            <div className="w-full bg-slate-100 h-1 rounded-full overflow-hidden">
                              <div className="bg-emerald-500 h-full rounded-full" style={{ width: `${statsDashboard.goteoPct}%` }} />
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Reservorios */}
                      <div className="border-t border-slate-100 pt-1.5 space-y-1">
                        <div className="flex justify-between items-center text-[5.5px]">
                          <span className="font-bold text-slate-800 uppercase">Tiene Reservorio:</span>
                          <span className="font-bold text-indigo-600">{statsDashboard.reservorioPct}% SÍ</span>
                        </div>
                        <div className="w-full bg-slate-100 h-1 rounded-full overflow-hidden">
                          <div className="bg-indigo-500 h-full rounded-full" style={{ width: `${statsDashboard.reservorioPct}%` }} />
                        </div>
                      </div>

                      {/* Tenencias */}
                      {statsDashboard.tenenciasSorted.length > 0 && (
                        <div className="border-t border-slate-100 pt-1.5 space-y-1">
                          <p className="font-bold text-slate-800 uppercase tracking-wide text-[5.5px]">Tenencia de Tierra:</p>
                          <div className="space-y-1 text-[5px]">
                            {statsDashboard.tenenciasSorted.map((t) => (
                              <div key={t.name}>
                                <div className="flex justify-between text-slate-600 mb-0.5">
                                  <span className="truncate max-w-[125px]">{t.name}</span>
                                  <span className="font-bold">{t.pct}%</span>
                                </div>
                                <div className="w-full bg-slate-100 h-1 rounded-full overflow-hidden">
                                  <div className="bg-slate-500 h-full rounded-full" style={{ width: `${t.pct}%` }} />
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Cultivos */}
                      {statsDashboard.cultivosSorted.length > 0 && (
                        <div className="border-t border-slate-100 pt-1.5 space-y-1">
                          <p className="font-bold text-slate-800 uppercase tracking-wide text-[5.5px]">Cultivos Principales:</p>
                          <div className="space-y-1 text-[5px]">
                            {statsDashboard.cultivosSorted.map((c) => (
                              <div key={c.name}>
                                <div className="flex justify-between text-slate-600 mb-0.5">
                                  <span className="truncate max-w-[125px]">{c.name}</span>
                                  <span className="font-bold">{c.pct}%</span>
                                </div>
                                <div className="w-full bg-slate-100 h-1 rounded-full overflow-hidden">
                                  <div className="bg-green-600 h-full rounded-full" style={{ width: `${c.pct}%` }} />
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* ── 3. Membrete Inferior ── */}
            <div className="h-8 border border-slate-200 bg-slate-50 flex items-center justify-between px-3 text-[6.5px] text-slate-700">
              {/* Escala */}
              <div className="flex items-center gap-2">
                <div className="flex flex-col gap-0.5">
                  <div className="flex border border-slate-900" style={{ width: `${escalaInfo.anchoMm * 2}px`, height: '3px' }}>
                    <div className="bg-slate-900" style={{ width: '50%', height: '100%' }} />
                    <div className="bg-white" style={{ width: '50%', height: '100%' }} />
                  </div>
                  <span className="font-bold text-slate-900 text-[6px] tracking-wide">
                    ESCALA CARTOGRÁFICA: {escalaInfo.label}
                  </span>
                </div>
              </div>

              {/* Norte y SRC */}
              <div className="flex items-center gap-6">
                <div className="flex items-center gap-1.5 font-semibold">
                  <Compass className="w-3 h-3 text-slate-700 animate-pulse" />
                  <span>SRC: WGS 84 / UTM zone 17S (EPSG:32717)</span>
                </div>
              </div>

              {/* Fecha y Créditos */}
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-1">
                  <Calendar className="w-2.5 h-2.5 text-slate-500" />
                  <span>Fecha: {new Date().toLocaleDateString('es-EC')}</span>
                </div>
                <span className="font-bold text-slate-900 border-l border-slate-200 pl-4 uppercase">
                  Prefectura de Pichincha
                </span>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
