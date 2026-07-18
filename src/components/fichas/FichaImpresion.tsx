import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, GeoJSON, CircleMarker, Rectangle, useMap } from 'react-leaflet';
import type { FeatureCollection } from 'geojson';
import { type FichaPredio, safeToDate, type CultivoAgricola, type AnimalEspecie, type PredioAdicional } from '../../lib/types';
import { getNombreTecnico, PROJECT_TITLE, PROJECT_SUBTITLE, PROJECT_SUBTITLE_ALCANCE, PROJECT_LOCATION } from '../../lib/constants';
import { wgs84ToUtm17S } from '../../lib/utm';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

interface Props {
  ficha: FichaPredio;
  cultivos: CultivoAgricola[];
  animales: AnimalEspecie[];
  prediosAdicionales: PredioAdicional[];
}



// Componente para forzar a Leaflet a recalcular sus dimensiones en impresión y centrar
function MapController({ center, zoom }: { center: [number, number]; zoom: number }) {
  const map = useMap();
  useEffect(() => {
    const timer = setTimeout(() => {
      map.invalidateSize();
      map.setView(center, zoom);
    }, 300);
    return () => clearTimeout(timer);
  }, [map, center, zoom]);
  return null;
}

// Componente inteligente que centra el mapa en los límites de un polígono, o cae al zoom por defecto
function PolygonBoundsController({ feature, center, defaultZoom }: { feature: any, center: [number, number], defaultZoom: number }) {
  const map = useMap();
  useEffect(() => {
    const timer = setTimeout(() => {
      map.invalidateSize();
      if (feature && feature.features && feature.features.length > 0) {
        try {
          const geoJsonLayer = L.geoJSON(feature);
          map.fitBounds(geoJsonLayer.getBounds(), { padding: [25, 25], maxZoom: 18 });
        } catch (e) {
          map.setView(center, defaultZoom);
        }
      } else {
        map.setView(center, defaultZoom);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [map, feature, center, defaultZoom]);
  return null;
}

export default function FichaImpresion({ ficha, cultivos, animales, prediosAdicionales }: Props) {
  const [mapPolygon, setMapPolygon] = useState<FeatureCollection | null>(null);
  const [allPolygons, setAllPolygons] = useState<FeatureCollection | null>(null);
  const [loadingPolygon, setLoadingPolygon] = useState(true);
  const [coords, setCoords] = useState<[number, number] | null>(null);
  const [parroquiasGeoJson, setParroquiasGeoJson] = useState<FeatureCollection | null>(null);

  // Cargar las parroquias para el mapa de ubicación general
  useEffect(() => {
    const timestamp = Date.now();
    fetch(`/geo/parroquias.geojson?t=${timestamp}`)
      .then((r) => r.json())
      .then((data) => setParroquiasGeoJson(data))
      .catch((e) => console.error("Error al cargar parroquias.geojson:", e));
  }, []);

  // Inicializar coords con los datos de la ficha
  useEffect(() => {
    if (ficha.geo?.lat && ficha.geo?.lng) {
      setCoords([ficha.geo.lat, ficha.geo.lng]);
    } else if (ficha._geojson?.coordinates) {
      setCoords([ficha._geojson.coordinates[1], ficha._geojson.coordinates[0]]);
    }
  }, [ficha]);

  // Cargar geometría cruzando clave_catastral de la ficha con catastro_geo.geojson o index general
  useEffect(() => {
    const timestamp = Date.now();
    setLoadingPolygon(true);
    const targetClave = (ficha.clave_catastral || '').trim();

    if (!targetClave) {
      setLoadingPolygon(false);
      return;
    }

    // 1. Obtener datos básicos de búsqueda para tener el centroide si la ficha no tiene coordenadas
    fetch(`/geo/catastro_busqueda.json?t=${timestamp}`)
      .then((r) => r.json())
      .then((busquedaData: any[]) => {
        const match = busquedaData.find(
          (item) => item.clave_cata && item.clave_cata.trim() === targetClave
        );

        if (match) {
          // Si no tiene coordenadas geográficas de campo, usar el centroide catastral rural
          if (!ficha.geo?.lat && !ficha._geojson?.coordinates && match.lat && match.lng) {
            setCoords([match.lat, match.lng]);
          }
        }

        // 2. Cargar geometrías desde catastro_geo.geojson (en lugar del archivo pesado catastro_poligonos.json)
        fetch(`/geo/catastro_geo.geojson?t=${timestamp}`)
          .then((r) => r.json())
          .then((geoData: FeatureCollection) => {
            const targetFeature = geoData.features.find(
              (f: any) => f.properties?.clave_cata && f.properties.clave_cata.trim() === targetClave
            );

            if (targetFeature) {
              setMapPolygon({
                type: 'FeatureCollection',
                features: [targetFeature]
              });
            }

            // Extraer polígonos vecinos (±0.008 grados aprox 800m)
            const neighbors: any[] = [];
            const targetLat = (targetFeature?.geometry as any)?.coordinates?.[0]?.[0]?.[1] || coords?.[0] || match?.lat;
            const targetLng = (targetFeature?.geometry as any)?.coordinates?.[0]?.[0]?.[0] || coords?.[1] || match?.lng;

            if (targetLat && targetLng) {
              geoData.features.forEach((f: any) => {
                const g = f.geometry;
                if (!g || !g.coordinates) return;

                let point;
                if (g.type === 'MultiPolygon' && g.coordinates[0] && g.coordinates[0][0]) {
                  point = g.coordinates[0][0][0];
                } else if (g.type === 'Polygon' && g.coordinates[0]) {
                  point = g.coordinates[0][0];
                }

                if (!point) return;

                const polyLng = point[0];
                const polyLat = point[1];

                if (
                  f.properties?.clave_cata?.trim() !== targetClave &&
                  Math.abs(polyLat - targetLat) < 0.008 &&
                  Math.abs(polyLng - targetLng) < 0.008
                ) {
                  neighbors.push(f);
                }
              });
            }

            if (neighbors.length > 0) {
              setAllPolygons({ type: 'FeatureCollection', features: neighbors });
            }

            setLoadingPolygon(false);
          })
          .catch((e) => {
            console.error("Error al cargar geojson de catastro", e);
            setLoadingPolygon(false);
          });
      })
      .catch((e) => {
        console.error("Error al cargar datos catastrales:", e);
        setLoadingPolygon(false);
      });
  }, [ficha.clave_catastral, ficha.geo, ficha._geojson]);

  const obtenerDestino = (item: { es_autoconsumo?: boolean | number; es_mercado?: boolean | number; es_agroindustria?: boolean | number; es_exportacion?: boolean | number }) => {
    const destinos = [];
    if (item.es_autoconsumo) destinos.push('Autoconsumo');
    if (item.es_mercado) destinos.push('Mercado');
    if (item.es_agroindustria) destinos.push('Agroindustria');
    if (item.es_exportacion) destinos.push('Exportación');
    return destinos.length > 0 ? destinos.join(', ') : '—';
  };



  const utm = coords ? wgs84ToUtm17S(coords[0], coords[1]) : null;

  return (
    <div className="print-report-view">
      {/* Estilos específicos de impresión inyectados */}
      <style>{`
        /* Sobrescribir todo para visualización de impresión */
        @media print {
          body, html {
            background: #ffffff !important;
            color: #000000 !important;
            margin: 0 !important;
            padding: 0 !important;
            font-size: 8pt !important;
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif !important;
          }
          /* Ocultar barra lateral, cabecera y controles de la app web */
          aside, header, nav, main, .no-print, button, .app-navigation, .fixed, .z-50, #root {
            display: none !important;
          }
          /* Mostrar únicamente el contenedor de impresión */
          .print-report-view {
            display: block !important;
            position: absolute !important;
            left: 0 !important;
            top: 0 !important;
            width: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
            box-shadow: none !important;
            background: #fff !important;
          }
          .print-container-portal {
            position: static !important;
            left: auto !important;
            top: auto !important;
            width: 100% !important;
            height: auto !important;
            overflow: visible !important;
            opacity: 1 !important;
            pointer-events: auto !important;
            display: block !important;
          }
          /* Márgenes de página */
          @page {
            size: A4 portrait;
            margin: 6mm 8mm 6mm 8mm;
          }
          .page-break {
            page-break-before: always;
            padding-top: 3mm;
          }
          .section-block {
            break-inside: avoid;
          }
        }

        /* Estilos en pantalla del visor de reporte */
        .print-report-view {
          background: #ffffff;
          color: #1e293b;
          font-family: 'Inter', sans-serif;
          max-width: 820px;
          margin: 15px auto;
          padding: 20px 25px;
          box-shadow: 0 10px 25px rgba(0,0,0,0.15);
          border-radius: 8px;
          line-height: 1.3;
        }

        .report-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          border-bottom: 2px solid #0f172a;
          padding-bottom: 6px;
          margin-bottom: 10px;
        }

        .report-title-block {
          text-align: center;
          flex: 1;
          padding: 0 10px;
        }

        .report-logo {
          height: 40px;
          width: auto;
          object-fit: contain;
        }

        .grid-details {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 5px;
          margin-bottom: 10px;
        }

        .detail-item {
          border: 1px solid #cbd5e1;
          padding: 3px 6px;
          border-radius: 4px;
          background: #f8fafc;
        }

        .detail-item.col-2 {
          grid-column: span 2;
        }

        .detail-item.col-4 {
          grid-column: span 4;
        }

        .detail-label {
          font-size: 7pt;
          text-transform: uppercase;
          color: #475569;
          font-weight: 700;
          letter-spacing: 0.03em;
        }

        .detail-value {
          font-size: 8.5pt;
          font-weight: 500;
          color: #0f172a;
        }

        .report-section-title {
          font-size: 9pt;
          font-weight: 700;
          color: #ffffff;
          background: #1e3a8a;
          padding: 3px 8px;
          margin-top: 10px;
          margin-bottom: 6px;
          text-transform: uppercase;
          border-radius: 3px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          -webkit-print-color-adjust: exact;
          print-color-adjust: exact;
        }

        .report-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 8pt;
          margin-bottom: 8px;
        }

        .report-table th {
          background: #e2e8f0;
          color: #1e293b;
          font-weight: 700;
          text-transform: uppercase;
          font-size: 7.5pt;
          border: 1px solid #cbd5e1;
          padding: 3px 6px;
        }

        .report-table td {
          border: 1px solid #cbd5e1;
          padding: 3px 6px;
        }

        .report-table tr:nth-child(even) {
          background: #f8fafc;
        }

        .print-footer-actions {
          position: fixed;
          bottom: 20px;
          right: 20px;
          display: flex;
          gap: 10px;
          z-index: 9999;
        }

        .print-btn {
          background: #2563eb;
          color: white;
          padding: 8px 16px;
          border-radius: 6px;
          font-size: 12px;
          font-weight: 600;
          cursor: pointer;
          border: none;
          box-shadow: 0 4px 10px rgba(37,99,235,0.3);
        }

        .close-btn {
          background: #475569;
          color: white;
          padding: 8px 16px;
          border-radius: 6px;
          font-size: 12px;
          font-weight: 600;
          cursor: pointer;
          border: none;
          box-shadow: 0 4px 10px rgba(71,85,105,0.3);
        }

        .visuals-container {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 10px;
          margin-top: 10px;
          break-inside: avoid;
        }

        .visual-box {
          border: 1px solid #cbd5e1;
          border-radius: 6px;
          overflow: hidden;
          background: #f8fafc;
          display: flex;
          flex-direction: column;
        }

        .visual-title {
          font-size: 7.5pt;
          font-weight: 700;
          background: #e2e8f0;
          color: #1e293b;
          padding: 3px 8px;
          text-transform: uppercase;
          border-bottom: 1px solid #cbd5e1;
        }

        .visual-content {
          flex: 1;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 6px;
          min-height: 180px;
        }

        .visual-img {
          max-height: 180px;
          max-width: 100%;
          object-fit: contain;
          border-radius: 4px;
          border: 1px solid #cbd5e1;
        }

        .no-visual {
          font-size: 7.5pt;
          color: #64748b;
          text-align: center;
        }

        .audit-block {
          border: 1.5px solid #1e3a8a;
          border-radius: 6px;
          background: #f8fafc;
          padding: 0;
          margin-top: 14px;
          display: grid;
          grid-template-columns: 1fr 1fr 2fr;
          break-inside: avoid;
          overflow: hidden;
        }

        .audit-item {
          padding: 6px 10px;
          border-right: 1px solid #cbd5e1;
        }

        .audit-item:last-child {
          border-right: none;
        }

        .audit-item-label {
          font-size: 6.5pt;
          text-transform: uppercase;
          color: #1e3a8a;
          font-weight: 700;
          letter-spacing: 0.03em;
          margin-bottom: 2px;
          background: #e2e8f0;
          margin: -6px -10px 4px -10px;
          padding: 3px 10px;
          border-bottom: 1px solid #cbd5e1;
        }

        .audit-item-value {
          font-size: 8.5pt;
          font-weight: 600;
          color: #0f172a;
        }

        .audit-item-sub {
          font-size: 6pt;
          color: #94a3b8;
          margin-top: 2px;
        }
      `}</style>

      {/* Cabecera oficial del reporte */}
      <div className="report-header" style={{ borderBottom: '2.5px solid #1e3a8a', paddingBottom: '10px', marginBottom: '14px' }}>
        <img src="/logo-izq.png" alt="Pichincha" className="report-logo" />
        <div className="report-title-block" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
          <h2 className="text-[7pt] font-bold text-slate-500 uppercase tracking-[0.12em] mb-1">{PROJECT_TITLE}</h2>
          <h1 className="text-[10pt] font-black text-[#0f172a] uppercase tracking-tight leading-tight">{PROJECT_SUBTITLE}</h1>
          <p className="text-[7pt] text-slate-500 mt-1 font-medium tracking-wide">{PROJECT_SUBTITLE_ALCANCE}</p>
          <p className="text-[6.5pt] text-slate-400 mt-0.5 tracking-wide">{PROJECT_LOCATION}</p>
        </div>
        <img src="/logo-der.png" alt="Consorcio" className="report-logo" />
      </div>

      <div className="text-center mb-4 flex flex-col items-center">
        <h3 className="text-[10.5pt] font-extrabold text-[#1e3a8a] uppercase tracking-[0.08em] relative inline-block">
          Ficha Técnica de Información de Regante
          <div className="absolute -bottom-1.5 left-[15%] right-[15%] h-[2px] bg-blue-500/60 rounded-full"></div>
        </h3>
        <div className="flex gap-4 mt-3.5 text-[7.5pt] font-mono text-slate-700 bg-slate-50/80 px-4 py-1.5 rounded-md border border-slate-200 shadow-sm">
          <span><span className="text-slate-400 font-sans font-bold uppercase tracking-widest text-[6pt] mr-1">CÓDIGO:</span> <b className="text-slate-900">{ficha.codigo_final}</b></span>
          <span className="text-slate-300">|</span>
          <span><span className="text-slate-400 font-sans font-bold uppercase tracking-widest text-[6pt] mr-1">CLAVE:</span> <span className="text-slate-900">{ficha.clave_catastral || 'S/N'}</span></span>
          <span className="text-slate-300">|</span>
          <span><span className="text-slate-400 font-sans font-bold uppercase tracking-widest text-[6pt] mr-1">REGISTRO:</span> <span className="text-slate-900">{safeToDate(ficha.fecha_creacion).toLocaleDateString('es-EC')}</span></span>
        </div>
      </div>

      {/* ── SECCIÓN 1: DATOS PROPIETARIO ── */}
      <div className="report-section-title">
        <span>1. Datos del Propietario / Regante</span>
      </div>
      <div className="grid-details">
        <div className="detail-item col-2">
          <p className="detail-label">Apellidos y Nombres</p>
          <p className="detail-value">{ficha.propietario || `${ficha.apellidos} ${ficha.nombres}`}</p>
        </div>
        <div className="detail-item">
          <p className="detail-label">Cédula Identidad</p>
          <p className="detail-value font-mono">{ficha.cedula || '—'}</p>
        </div>
        <div className="detail-item">
          <p className="detail-label">Teléfono Celular</p>
          <p className="detail-value font-mono">{ficha.telefono_celular || '—'}</p>
        </div>
        <div className="detail-item">
          <p className="detail-label">Parroquia</p>
          <p className="detail-value">{ficha.parroquia}</p>
        </div>
        <div className="detail-item">
          <p className="detail-label">Sector</p>
          <p className="detail-value">{ficha.sector}</p>
        </div>
        <div className="detail-item">
          <p className="detail-label">Comunidad</p>
          <p className="detail-value">{ficha.comunidad || '—'}</p>
        </div>
        <div className="detail-item">
          <p className="detail-label">Sector Comunidad</p>
          <p className="detail-value">{ficha.sector_comunidad || '—'}</p>
        </div>
        <div className="detail-item">
          <p className="detail-label">Hijos Varones</p>
          <p className="detail-value">{ficha.hijos_hombres ?? 0}</p>
        </div>
        <div className="detail-item">
          <p className="detail-label">Hijas Mujeres</p>
          <p className="detail-value">{ficha.hijos_mujeres ?? 0}</p>
        </div>
        <div className="detail-item">
          <p className="detail-label">Tenencia del Predio</p>
          <p className="detail-value">{ficha.tenencia_predio || '—'}</p>
        </div>
        <div className="detail-item">
          <p className="detail-label">Instrucción</p>
          <p className="detail-value">{ficha.nivel_instruccion || '—'}</p>
        </div>
      </div>

      {/* ── SECCIÓN 2: DATOS DEL PREDIO Y RIEGO ── */}
      <div className="report-section-title">
        <span>2. Información del Predio y de Riego</span>
      </div>
      <div className="grid-details">
        <div className="detail-item">
          <p className="detail-label">Árefa Total</p>
          <p className="detail-value font-semibold">{ficha.area_total?.toLocaleString('es-EC')} m²</p>
        </div>
        <div className="detail-item">
          <p className="detail-label">Área con Riego</p>
          <p className="detail-value">{ficha.area_riego?.toLocaleString('es-EC')} m²</p>
        </div>
        <div className="detail-item">
          <p className="detail-label">Área sin Riego</p>
          <p className="detail-value">{ficha.area_sin_riego?.toLocaleString('es-EC')} m²</p>
        </div>
        <div className="detail-item">
          <p className="detail-label">Reservorio</p>
          <p className="detail-value">{ficha.tiene_reservorio || '—'}</p>
        </div>
        <div className="detail-item col-2">
          <p className="detail-label">Organización de Riego</p>
          <p className="detail-value">{ficha.org_riego || '—'}</p>
        </div>
        <div className="detail-item">
          <p className="detail-label font-bold text-sky-700">Canal</p>
          <p className="detail-value text-sky-800 font-semibold">{ficha.canal || '—'}</p>
        </div>
        <div className="detail-item">
          <p className="detail-label font-bold text-sky-700">Caudal</p>
          <p className="detail-value text-sky-800 font-semibold">{ficha.caudal_valor ? `${ficha.caudal_valor} l/s (${ficha.caudal_tipo || ''})` : '—'}</p>
        </div>
        <div className="detail-item col-2">
          <p className="detail-label">Método Riego</p>
          <p className="detail-value">
            {[
              ficha.metodo_aspersion_pct ? `Aspersión (${ficha.metodo_aspersion_pct}%)` : '',
              ficha.metodo_gravedad_pct ? `Gravedad (${ficha.metodo_gravedad_pct}%)` : '',
              ficha.metodo_goteo_pct ? `Goteo (${ficha.metodo_goteo_pct}%)` : ''
            ].filter(Boolean).join(' · ') || '—'}
          </p>
        </div>
        <div className="detail-item">
          <p className="detail-label">Frecuencia</p>
          <p className="detail-value">{ficha.frecuencia_riego || '—'}</p>
        </div>
        <div className="detail-item">
          <p className="detail-label">Turno Riego</p>
          <p className="detail-value">{ficha.dias_riego ? `${ficha.dias_riego} días / ${ficha.horas_turno || 0} horas` : '—'}</p>
        </div>
        <div className="detail-item col-2">
          <p className="detail-label">Tarifa de Riego</p>
          <p className="detail-value">{ficha.valor_tarifa ? `$${ficha.valor_tarifa} (${ficha.tipo_tarifa || ''})` : '—'}</p>
        </div>
      </div>

      {/* ── SECCIÓN 3: OTROS PREDIOS DEL REGANTE EN LA COMUNIDAD ── */}
      <div className="section-block">
        <div className="report-section-title">
          <span>3. Otros Predios del Regante en la Comunidad</span>
        </div>
        {prediosAdicionales.length === 0 ? (
          <p className="text-[8pt] text-slate-500 italic p-1">No se registraron predios o pedidos adicionales asociados a este regante.</p>
        ) : (
          <table className="report-table">
            <thead>
              <tr>
                <th>Clave Catastral Adicional</th>
                <th>Área Total</th>
                <th>Área Lote Asignado</th>
                <th>Área Riego</th>
                <th>Área Sin Riego</th>
                <th>Observaciones del Lote</th>
              </tr>
            </thead>
            <tbody>
              {prediosAdicionales.map((pa, idx) => (
                <tr key={idx}>
                  <td className="font-mono font-semibold">{pa.clave_catastral_otro || '—'}</td>
                  <td>{pa.area_total_otro?.toLocaleString('es-EC')} m²</td>
                  <td className="font-semibold">{pa.area_lote_asignado_otro?.toLocaleString('es-EC')} m²</td>
                  <td>{pa.area_riego_otro?.toLocaleString('es-EC')} m²</td>
                  <td>{pa.area_sin_riego_otro?.toLocaleString('es-EC')} m²</td>
                  <td className="italic text-slate-600">{pa.observaciones_otro || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* ── SECCIÓN 4: SERVICIOS Y UBICACIÓN ── */}
      <div className="report-section-title">
        <span>4. Servicios Básicos e Infraestructura</span>
      </div>
      <div className="grid-details">
        <div className="detail-item">
          <p className="detail-label">Agua Consumo</p>
          <p className="detail-value">{ficha.agua_consumo ? 'Sí' : 'No'}</p>
        </div>
        <div className="detail-item">
          <p className="detail-label">Energía Eléctrica</p>
          <p className="detail-value">{ficha.energia_electrica ? 'Sí' : 'No'}</p>
        </div>
        <div className="detail-item col-2">
          <p className="detail-label">Material de Construcción</p>
          <p className="detail-value">{ficha.material_construccion === 'Otros' ? ficha.material_constr_otro : ficha.material_construccion || '—'}</p>
        </div>
        <div className="detail-item">
          <p className="detail-label">Cota Altura</p>
          <p className="detail-value font-mono">{ficha.cota_msnm ? `${ficha.cota_msnm.toLocaleString('es-EC')} msnm` : '—'}</p>
        </div>
        <div className="detail-item">
          <p className="detail-label font-bold text-sky-700">Este (X)</p>
          <p className="detail-value font-mono text-sky-800 font-semibold">{utm ? `${utm.este.toFixed(1)} m` : '—'}</p>
        </div>
        <div className="detail-item">
          <p className="detail-label font-bold text-sky-700">Norte (Y)</p>
          <p className="detail-value font-mono text-sky-800 font-semibold">{utm ? `${utm.norte.toFixed(1)} m` : '—'}</p>
        </div>
        <div className="detail-item">
          <p className="detail-label">Zona UTM</p>
          <p className="detail-value font-mono">17S</p>
        </div>
        <div className="detail-item col-4" style={{ background: '#eff6ff', borderColor: '#bfdbfe' }}>
          <p className="detail-label" style={{ color: '#1d4ed8' }}>📍 Referencia Cartográfica</p>
          <p className="detail-value" style={{ color: '#1e3a8a', fontSize: '7.5pt' }}>
            Polígono del predio referenciado a la capa <strong>Catastro Rural – GADM Cayambe</strong> (insumo municipal). Datum WGS 84 · Zona 17S.
          </p>
        </div>
      </div>



      {/* ── SECCIÓN 5: ACTIVIDAD AGROPECUARIA ── */}
      <div className="report-section-title">
        <span>5. Producción y Actividad Agropecuaria</span>
      </div>
      <div className="grid-details mb-2">
        <div className="detail-item col-2">
          <p className="detail-label">Actividad Productiva Principal</p>
          <p className="detail-value">{ficha.actividad_productiva || '—'}</p>
        </div>
        <div className="detail-item">
          <p className="detail-label">Soberanía Alimentaria</p>
          <p className="detail-value">{ficha.soberania_aliment_pct ? `${ficha.soberania_aliment_pct}%` : '—'}</p>
        </div>
        <div className="detail-item">
          <p className="detail-label">Comercialización</p>
          <p className="detail-value">{ficha.act_productivas_pct ? `${ficha.act_productivas_pct}%` : '—'}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {/* Tabla Cultivos */}
        <div className="section-block">
          <p className="text-[7.5pt] font-bold text-slate-700 uppercase tracking-wide mb-1 border-b pb-0.5">Cultivos Agrícolas</p>
          {cultivos.length === 0 ? (
            <p className="text-[7.5pt] text-slate-400 italic">Sin cultivos registrados.</p>
          ) : (
            <table className="report-table">
              <thead>
                <tr>
                  <th>Cultivo</th>
                  <th>Área</th>
                  <th>Destino</th>
                </tr>
              </thead>
              <tbody>
                {cultivos.map((c, i) => (
                  <tr key={i}>
                    <td className="font-semibold">{c.tipo_cultivo === 'Otros' ? c.tipo_cultivo_otro : c.tipo_cultivo} {c.es_principal ? '(P)' : ''}</td>
                    <td>{c.superficie_m2 ? `${c.superficie_m2.toLocaleString('es-EC')} m²` : '—'}</td>
                    <td>{obtenerDestino(c)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Tabla Animales */}
        <div className="section-block">
          <p className="text-[7.5pt] font-bold text-slate-700 uppercase tracking-wide mb-1 border-b pb-0.5">Producción Pecuaria</p>
          {animales.length === 0 ? (
            <p className="text-[7.5pt] text-slate-400 italic">Sin animales registrados.</p>
          ) : (
            <table className="report-table">
              <thead>
                <tr>
                  <th>Especie</th>
                  <th>Cantidad</th>
                  <th>Destino</th>
                </tr>
              </thead>
              <tbody>
                {animales.map((a, i) => (
                  <tr key={i}>
                    <td className="font-semibold">{a.especie === 'Otros' ? a.especie_otro : a.especie}</td>
                    <td>{a.cantidad}</td>
                    <td>{obtenerDestino(a)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Salto de página para la evidencia y mapas */}
      <div className="page-break"></div>

      <div className="report-header">
        <img src="/logo-izq.png" alt="Pichincha" className="report-logo" />
        <div className="report-title-block">
          <h1 className="text-[10px] font-bold text-slate-900 uppercase tracking-tight">{PROJECT_TITLE}</h1>
          <p className="text-[7px] text-slate-400 font-mono">Código Predio: {ficha.codigo_final}</p>
        </div>
        <img src="/logo-der.png" alt="Consorcio" className="report-logo" />
      </div>

      {/* ── SECCIÓN 6: ENCUESTA COMUNITARIA Y AUDITORÍA ── */}
      <div className="report-section-title">
        <span>6. Organización Comunitaria y Auditoría</span>
      </div>
      <div className="grid-details">
        <div className="detail-item col-2">
          <p className="detail-label">¿Conoce el Proyecto Presa?</p>
          <p className="detail-value">{ficha.conoce_presa || '—'}</p>
        </div>
        <div className="detail-item col-2">
          <p className="detail-label">Elección de Directivas</p>
          <p className="detail-value">{ficha.como_elige_dir === 'Otros' ? ficha.como_elige_dir_otro : ficha.como_elige_dir || '—'}</p>
        </div>
        <div className="detail-item">
          <p className="detail-label">Presidente Junta</p>
          <p className="detail-value">{ficha.nom_presidente || '—'}</p>
        </div>
        <div className="detail-item">
          <p className="detail-label">Operador Sector</p>
          <p className="detail-value">{ficha.operador_sector || '—'}</p>
        </div>
        <div className="detail-item">
          <p className="detail-label">Años Canal</p>
          <p className="detail-value">{ficha.anios_sistema ?? '—'}</p>
        </div>
        <div className="detail-item">
          <p className="detail-label">Canal Longitud</p>
          <p className="detail-value">{ficha.km_canal ? `${ficha.km_canal} km` : '—'}</p>
        </div>
        <div className="detail-item col-2">
          <p className="detail-label">Capacitación (¿Recibió? / ¿Desea?)</p>
          <p className="detail-value">Recibió: {ficha.recibio_capacitacion || 'No'} | Desea: {ficha.le_gustaria_cap || 'No'}</p>
        </div>
        <div className="detail-item col-2">
          <p className="detail-label">Temas Solicitados</p>
          <p className="detail-value">{ficha.temas_capacitacion || '—'}</p>
        </div>

      </div>

      {/* ── SECCIÓN 7: UBICACIÓN REGIONAL, EMPLAZAMIENTO Y FOTO ── */}
      <div className="visuals-container">

        {/* 1. UBICACIÓN REGIONAL (zoom amplio con parroquias + bounding box localizador) */}
        <div className="visual-box">
          <div className="visual-title">Ubicación Regional</div>
          <div className="visual-content relative" style={{ height: '190px', padding: 0 }}>
            {coords ? (
              <MapContainer
                center={coords}
                zoom={11}
                dragging={false}
                zoomControl={false}
                scrollWheelZoom={false}
                doubleClickZoom={false}
                touchZoom={false}
                className="h-full w-full z-0"
              >
                {/* Mapa base satelital (misma fuente que Emplazamiento) */}
                <TileLayer
                  attribution="&copy; ESRI"
                  url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                />
                <MapController center={coords} zoom={11} />

                {/* Límites de parroquias en blanco/cian brillante para alto contraste sobre fondo satelital */}
                {parroquiasGeoJson && (
                  <GeoJSON
                    data={parroquiasGeoJson}
                    style={{
                      color: '#ffffff',
                      weight: 2.5,
                      fillColor: '#06b6d4',
                      fillOpacity: 0.08,
                      dashArray: '6 3'
                    }}
                  />
                )}

                {/* Recuadro localizador (Bounding Box) que representa el área del Emplazamiento Predial.
                    Se dibuja un recuadro amplio para que sea visible a zoom 11 */}
                <Rectangle
                  bounds={[
                    [coords[0] - 0.012, coords[1] - 0.015],
                    [coords[0] + 0.012, coords[1] + 0.015]
                  ]}
                  pathOptions={{
                    color: '#facc15',
                    weight: 3,
                    fillColor: '#facc15',
                    fillOpacity: 0.12,
                    dashArray: '8 4'
                  }}
                />

                {/* Punto central del predio */}
                <CircleMarker
                  center={coords}
                  radius={5}
                  pathOptions={{
                    fillColor: '#ef4444',
                    fillOpacity: 1,
                    color: '#ffffff',
                    weight: 2
                  }}
                />
              </MapContainer>
            ) : (
              <div className="no-visual">Coordenadas geográficas no disponibles</div>
            )}
            {/* Etiqueta flotante de ubicación geográfica (Provincia › Cantón › Parroquia › Comunidad) */}
            <div style={{
              position: 'absolute',
              top: '6px',
              left: '6px',
              zIndex: 999, // Para asegurar que esté por encima del mapa
              background: 'rgba(15, 23, 42, 0.75)', // Fondo oscuro semi-transparente para alto contraste
              backdropFilter: 'blur(2px)',
              color: '#f8fafc',
              padding: '4px 8px',
              borderRadius: '4px',
              fontSize: '6pt',
              fontWeight: 600,
              letterSpacing: '0.04em',
              textTransform: 'uppercase',
              boxShadow: '0 2px 4px rgba(0,0,0,0.3)',
              maxWidth: '95%',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              pointerEvents: 'none'
            }}>
              PICHINCHA › CAYAMBE › {ficha.parroquia || 'SIN PARROQUIA'} › {ficha.sector_comunidad || ficha.sector || 'SIN COMUNIDAD'}
            </div>
          </div>
        </div>

        {/* 2. EMPLAZAMIENTO PREDIAL (zoom cerrado con polígono) */}
        <div className="visual-box">
          <div className="visual-title">Emplazamiento Predial</div>
          <div className="visual-content relative" style={{ height: '190px', padding: 0 }}>
            {coords ? (
              <MapContainer
                center={coords}
                zoom={17}
                dragging={false}
                zoomControl={false}
                scrollWheelZoom={false}
                doubleClickZoom={false}
                touchZoom={false}
                className="h-full w-full z-0"
              >
                <TileLayer
                  attribution="&copy; ESRI"
                  url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                />
                <PolygonBoundsController feature={mapPolygon} center={coords} defaultZoom={17} />

                {/* Polígonos catastrales vecinos (fondo tenue) */}
                {!loadingPolygon && allPolygons && (
                  <GeoJSON
                    data={allPolygons}
                    style={{ color: '#94a3b8', weight: 1.5, fillColor: 'transparent' }}
                  />
                )}

                {/* Polígono catastral del predio seleccionado en rojo (más grueso y con relleno) */}
                {!loadingPolygon && mapPolygon && (
                  <GeoJSON
                    data={mapPolygon}
                    style={{ color: '#ef4444', weight: 3.5, fillColor: '#ef4444', fillOpacity: 0.25 }}
                  />
                )}

                {/* Punto GPS levantado en campo (azul) */}
                <CircleMarker
                  center={coords}
                  radius={6}
                  pathOptions={{
                    fillColor: '#3b82f6',
                    fillOpacity: 1,
                    color: '#ffffff',
                    weight: 2
                  }}
                />
              </MapContainer>
            ) : (
              <div className="no-visual">Coordenadas geográficas no disponibles</div>
            )}
          </div>
        </div>


      </div>

      {/* ── BLOQUE FINAL: AUDITORÍA (4 columnas) + CONSENTIMIENTO ── */}

      {/* Consentimiento informado */}
      {(() => {
        const tieneConsentimiento = 
          (ficha as any).consentimiento_informado !== false && 
          (ficha as any).consentimiento_inform !== 0 && 
          (ficha as any).consentimiento_informado !== 0;
        return (
          <div style={{
            margin: '10px 0 6px',
            padding: '6px 10px',
            background: '#f0fdf4',
            border: '1px solid #bbf7d0',
            borderRadius: '4px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            breakInside: 'avoid'
          }}>
            <span style={{ 
              fontSize: '6.5pt', 
              fontWeight: 'bold', 
              color: '#15803d', 
              backgroundColor: '#dcfce7', 
              padding: '2px 6px', 
              borderRadius: '3px',
              border: '1px solid #86efac',
              textTransform: 'uppercase',
              letterSpacing: '0.05em'
            }}>
              {tieneConsentimiento ? 'Otorgado' : 'No Otorgado'}
            </span>
            <p style={{ fontSize: '7.5pt', color: '#166534', margin: 0, lineHeight: '1.3' }}>
              <strong>Consentimiento Informado:</strong> El/la informante autoriza el uso institucional de los datos
              recopilados en esta ficha para el Catastro de Riego de Cayambe, conforme a la normativa de protección de datos personales.
            </p>
          </div>
        );
      })()}

      {/* Responsables — 4 columnas */}
      <div className="audit-block" style={{ gridTemplateColumns: '1fr 1fr 1fr 1fr' }}>
        {/* Columna 1: Informante */}
        <div className="audit-item">
          <div className="audit-item-label">Informante</div>
          <p className="audit-item-value">{(ficha as any).informante || ficha.propietario || `${ficha.apellidos} ${ficha.nombres}`}</p>
          <p className="audit-item-sub">Propietario / Regante</p>
        </div>
        {/* Columna 2: Investigador */}
        <div className="audit-item">
          <div className="audit-item-label">Investigador (Técnico)</div>
          <p className="audit-item-value">{getNombreTecnico(ficha.creado_por)}</p>
          <p className="audit-item-sub">Responsable del Levantamiento</p>
          <div className="mt-1">
            <span style={{
              fontSize: '5.5pt', fontWeight: 700, color: '#475569',
              backgroundColor: '#f1f5f9', padding: '2px 5px',
              borderRadius: '3px', border: '1px solid #cbd5e1', letterSpacing: '0.05em'
            }}>AP&CATASTROS</span>
          </div>
        </div>
        {/* Columna 3: Supervisor */}
        <div className="audit-item">
          <div className="audit-item-label">Supervisor</div>
          <p className="audit-item-value">{(ficha as any).supervisor || 'Téc. Steven Proaño'}</p>
          <p className="audit-item-sub">AP CATASTROS</p>
        </div>
        {/* Columna 4: Fecha */}
        <div className="audit-item">
          <div className="audit-item-label">Fecha de Registro</div>
          <p className="audit-item-value">
            {safeToDate(ficha.fecha_creacion).toLocaleDateString('es-EC', {
              weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
            })}
          </p>
          <p className="audit-item-sub">Registro en campo</p>
        </div>
      </div>

      {/* Observaciones — fila completa */}
      {ficha.observaciones && (
        <div style={{
          marginTop: '6px', padding: '5px 10px',
          background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '4px'
        }}>
          <p style={{ fontSize: '6.5pt', textTransform: 'uppercase', color: '#475569', fontWeight: 700, marginBottom: '2px' }}>Observaciones Generales</p>
          <p style={{ fontSize: '8pt', fontStyle: 'italic', color: '#334155', lineHeight: '1.4' }}>"{ficha.observaciones}"</p>
        </div>
      )}
    </div>
  );
}
