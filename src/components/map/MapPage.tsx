import { useEffect, useState, useRef } from 'react';
import {
  MapContainer, TileLayer, GeoJSON, CircleMarker, Popup,
  LayersControl, useMap, Tooltip,
} from 'react-leaflet';
import type { CircleMarker as LeafletCircleMarker, LeafletMouseEvent } from 'leaflet';
import type { FeatureCollection } from 'geojson';
import { Loader2, MapPin, Eye, EyeOff } from 'lucide-react';
import { type FichaPredio, safeToDate } from '../../lib/types';
import { getNombreTecnico, getColorTecnico, TECNICOS } from '../../lib/constants';
import { useMapNav } from '../../hooks/useMapNav';
import { wgs84ToUtm17S, type CRS } from '../../lib/utm';
import 'leaflet/dist/leaflet.css';

interface Props {
  fichas: FichaPredio[];
  loading: boolean;
}

// ── Leyenda ──────────────────────────────────────────────────
function MapLegend() {
  const [show, setShow] = useState(true);
  return (
    <div className="absolute bottom-4 right-4 z-[1000]">
      <button
        onClick={() => setShow(!show)}
        className="mb-1 p-1.5 rounded-md border cursor-pointer shadow"
        style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)', color: 'var(--text-secondary)' }}
      >
        {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
      </button>
      {show && (
        <div className="rounded-lg border p-3 max-w-[190px] shadow-lg"
          style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}>
          <p className="text-[10px] font-semibold mb-2 uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Técnicos</p>
          <div className="space-y-1.5">
            {Object.entries(TECNICOS).map(([key, { nombre, color }]) => (
              <div key={key} className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full shrink-0 border border-white/20" style={{ background: color }} />
                <span className="text-[10px] truncate" style={{ color: 'var(--text-secondary)' }}>{nombre}</span>
              </div>
            ))}
          </div>
          <div className="mt-3 pt-2 border-t space-y-1.5" style={{ borderColor: 'var(--border-color)' }}>
            <p className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Capas</p>
            <div className="flex items-center gap-2">
              <div className="w-3 h-2 rounded-sm border border-orange-400/60" style={{ background: 'rgba(249,115,22,0.15)' }} />
              <span className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>Catastro rural</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-5 h-0.5 rounded" style={{ background: '#38bdf8' }} />
              <span className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>Canales de riego</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── FlyTo zoom 18 ────────────────────────────────────────────
function FlyToFicha({ ficha }: { ficha: FichaPredio | null }) {
  const map = useMap();
  useEffect(() => {
    if (!ficha) return;
    let lat: number | undefined, lng: number | undefined;
    if (ficha.geo?.lat && ficha.geo?.lng) { lat = ficha.geo.lat; lng = ficha.geo.lng; }
    else if (ficha._geojson?.coordinates) {
      lng = ficha._geojson.coordinates[0] as number;
      lat = ficha._geojson.coordinates[1] as number;
    }
    if (lat && lng) {
      map.flyTo([lat, lng], 18, { duration: 1.5 });
    }
  }, [ficha, map]);
  return null;
}

// ── Auto-fit inicial ─────────────────────────────────────────
function FitBounds({ fichas, skip }: { fichas: FichaPredio[]; skip: boolean }) {
  const map = useMap();
  const fitted = useRef(false);
  useEffect(() => {
    if (skip || fitted.current || fichas.length === 0) return;
    const pts = fichas
      .filter((f) => f.geo?.lat || f._geojson?.coordinates)
      .map((f): [number, number] | null => {
        if (f.geo) return [f.geo.lat, f.geo.lng];
        if (f._geojson?.coordinates) return [f._geojson.coordinates[1] as number, f._geojson.coordinates[0] as number];
        return null;
      }).filter(Boolean) as [number, number][];
    if (pts.length > 0) {
      try { map.fitBounds(pts as any, { padding: [60, 60] }); fitted.current = true; } catch {}
    }
  }, [fichas, map, skip]);
  return null;
}

// ── Visor de coordenadas del mouse ───────────────────────────
function MouseCoordinates() {
  const map = useMap();
  const [pos, setPos] = useState<{ lat: number; lng: number } | null>(null);
  const [crs, setCrs] = useState<CRS>('wgs84');

  useEffect(() => {
    const handler = (e: LeafletMouseEvent) => setPos(e.latlng);
    map.on('mousemove', handler);
    map.on('mouseout', () => setPos(null));
    return () => { map.off('mousemove', handler); map.off('mouseout'); };
  }, [map]);

  if (!pos) return null;

  const utmCoords = wgs84ToUtm17S(pos.lat, pos.lng);

  return (
    <div
      className="absolute bottom-3 left-3 z-[1000] rounded-lg border px-3 py-1.5 shadow-lg backdrop-blur-sm flex items-center gap-3"
      style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
    >
      <div className="text-[11px] font-mono" style={{ color: 'var(--text-primary)' }}>
        {crs === 'utm17s' ? (
          <span>E <b>{utmCoords.este.toFixed(1)}</b>  N <b>{utmCoords.norte.toFixed(1)}</b></span>
        ) : (
          <span>
            <b>{Math.abs(pos.lat).toFixed(6)}°</b> {pos.lat >= 0 ? 'N' : 'S'}{' '}
            <b>{Math.abs(pos.lng).toFixed(6)}°</b> {pos.lng >= 0 ? 'E' : 'W'}
          </span>
        )}
      </div>
      <button
        onClick={() => setCrs(crs === 'wgs84' ? 'utm17s' : 'wgs84')}
        className="px-1.5 py-0.5 rounded text-[9px] font-bold border cursor-pointer transition-colors"
        style={{
          background: 'var(--bg-input)',
          borderColor: 'var(--border-input)',
          color: 'var(--text-secondary)',
        }}
        title={crs === 'wgs84' ? 'Cambiar a UTM 17S' : 'Cambiar a WGS84'}
      >
        {crs === 'wgs84' ? 'WGS84' : 'UTM 17S'}
      </button>
    </div>
  );
}

function FichaMarker({ ficha, coords }: { ficha: FichaPredio; coords: [number, number] }) {
  const markerRef = useRef<LeafletCircleMarker | null>(null);
  const { selectedFichaMap } = useMapNav();
  const isSelected = selectedFichaMap?.id === ficha.id;
  const [popupCrs, setPopupCrs] = useState<CRS>('utm17s');

  useEffect(() => {
    if (isSelected && markerRef.current) {
      setTimeout(() => { markerRef.current?.openPopup(); }, 1600);
    }
  }, [isSelected]);

  const color = getColorTecnico(ficha.creado_por);
  const lat = coords[0];
  const lng = coords[1];
  const utm = wgs84ToUtm17S(lat, lng);

  return (
    <CircleMarker
      ref={markerRef}
      center={coords}
      radius={isSelected ? 11 : 6}
      pathOptions={{
        fillColor: color, fillOpacity: 0.9,
        color: isSelected ? '#fff' : 'rgba(255,255,255,0.5)',
        weight: isSelected ? 3 : 1,
      }}
    >
      <Tooltip direction="top" offset={[0, -8]} opacity={0.9}>
        <span className="text-xs font-medium">{ficha.propietario || ficha.codigo_final}</span>
      </Tooltip>
      <Popup maxWidth={320}>
        <div className="text-xs space-y-1 min-w-[220px]">
          <div className="font-bold text-sm border-b pb-1 mb-2">
            {ficha.propietario || `${ficha.apellidos} ${ficha.nombres}`}
          </div>
          <div className="grid grid-cols-2 gap-x-3 gap-y-0.5">
            {([
              ['Código', ficha.codigo_final],
              ['Cédula', ficha.cedula],
              ['Parroquia', ficha.parroquia],
              ['Sector', ficha.sector],
              ['Área', ficha.area_total ? `${ficha.area_total.toLocaleString('es-EC')} m²` : null],
              ['Caudal', ficha.caudal_valor ? `${ficha.caudal_valor} l/s` : null],
              ['Cota', ficha.cota_msnm ? `${ficha.cota_msnm} msnm` : null],
              ['Técnico', getNombreTecnico(ficha.creado_por)],
              ['Fecha', safeToDate(ficha.fecha_creacion).toLocaleDateString('es-EC')],
            ] as [string, string | null][]).filter(([, v]) => v).map(([label, val]) => (
              <div key={label} className="contents">
                <span className="opacity-60">{label}:</span>
                <span className="font-medium">{val}</span>
              </div>
            ))}
          </div>

          {/* ── Coordenadas con toggle UTM/WGS84 ── */}
          <div className="mt-2 pt-2 border-t" style={{ borderColor: '#e5e7eb40' }}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] font-semibold uppercase tracking-wider opacity-60">Coordenadas</span>
              <button
                onClick={(e) => { e.stopPropagation(); setPopupCrs(popupCrs === 'wgs84' ? 'utm17s' : 'wgs84'); }}
                className="px-1.5 py-0.5 rounded text-[9px] font-bold border cursor-pointer hover:opacity-80"
                style={{ borderColor: '#9ca3af40' }}
              >
                {popupCrs === 'utm17s' ? 'UTM 17S' : 'WGS84'}
              </button>
            </div>
            {popupCrs === 'utm17s' ? (
              <div className="font-mono text-[11px] grid grid-cols-2 gap-x-2">
                <span className="opacity-50">Este:</span>
                <span className="font-semibold">{utm.este.toFixed(2)} m</span>
                <span className="opacity-50">Norte:</span>
                <span className="font-semibold">{utm.norte.toFixed(2)} m</span>
              </div>
            ) : (
              <div className="font-mono text-[11px] grid grid-cols-2 gap-x-2">
                <span className="opacity-50">Latitud:</span>
                <span className="font-semibold">{lat.toFixed(6)}°</span>
                <span className="opacity-50">Longitud:</span>
                <span className="font-semibold">{lng.toFixed(6)}°</span>
              </div>
            )}
          </div>
        </div>
      </Popup>
    </CircleMarker>
  );
}

// ══════════════════════════════════════════════════════════════
// Componente Principal del Mapa
// ══════════════════════════════════════════════════════════════

export default function MapPage({ fichas, loading }: Props) {
  const { selectedFichaMap, clearMapSelection } = useMapNav();
  const [catastroData, setCatastroData] = useState<FeatureCollection | null>(null);
  const [ramalesData, setRamalesData] = useState<FeatureCollection | null>(null);
  const [layerInfo, setLayerInfo] = useState({ catastro: 0, ramales: 0 });

  useEffect(() => {
    fetch('/geo/catastro_geo.geojson')
      .then((r) => r.json())
      .then((data: FeatureCollection) => {
        const valid = data.features?.filter((f) => f.geometry != null) || [];
        setCatastroData({ type: 'FeatureCollection', features: valid });
        setLayerInfo((p) => ({ ...p, catastro: valid.length }));
      }).catch(() => {});

    fetch('/geo/ramales_riego.geojson')
      .then((r) => r.json())
      .then((data: FeatureCollection) => {
        const valid = data.features?.filter((f) => f.geometry != null) || [];
        setRamalesData({ type: 'FeatureCollection', features: valid });
        setLayerInfo((p) => ({ ...p, ramales: valid.length }));
      }).catch(() => {});

    return () => clearMapSelection();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-180px)]">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    );
  }

  const fichasConGeo = fichas.filter((f) => f.geo?.lat || f._geojson?.coordinates);
  const getCoords = (f: FichaPredio): [number, number] => {
    if (f.geo?.lat && f.geo?.lng) return [f.geo.lat, f.geo.lng];
    if (f._geojson?.coordinates) return [f._geojson.coordinates[1] as number, f._geojson.coordinates[0] as number];
    return [0, 0];
  };

  return (
    <div className="relative rounded-xl overflow-hidden border"
      style={{ height: 'calc(100vh - 180px)', borderColor: 'var(--border-color)' }}>

      {/* Stats overlay */}
      <div className="absolute top-3 left-3 z-[1000] rounded-lg border px-3 py-2 shadow-lg backdrop-blur-sm"
        style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}>
        <div className="flex items-center gap-2 text-xs">
          <MapPin className="w-4 h-4 text-blue-400" />
          <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{fichasConGeo.length} fichas</span>
        </div>
        {layerInfo.catastro > 0 && (
          <div className="flex items-center gap-1.5 text-[10px] mt-1" style={{ color: 'var(--text-muted)' }}>
            <div className="w-2 h-2 rounded-sm border border-orange-400" style={{ background: 'rgba(249,115,22,0.2)' }} />
            {layerInfo.catastro} polígonos
          </div>
        )}
        {selectedFichaMap && (
          <div className="mt-1.5 pt-1.5 border-t flex items-center gap-1" style={{ borderColor: 'var(--border-color)' }}>
            <MapPin className="w-3 h-3 text-emerald-400" />
            <span className="text-[10px] text-emerald-400 max-w-[160px] truncate">
              {selectedFichaMap.propietario || selectedFichaMap.codigo_final}
            </span>
          </div>
        )}
      </div>

      <MapContainer center={[0.04, -78.15]} zoom={13} className="h-full w-full">
        {/* ── Basemaps ── */}
        <LayersControl position="topright">
          <LayersControl.BaseLayer checked name="ESRI Satélite">
            <TileLayer
              attribution='&copy; ESRI'
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
              maxZoom={20}
            />
          </LayersControl.BaseLayer>
          <LayersControl.BaseLayer name="ESRI Topográfico">
            <TileLayer
              attribution='&copy; ESRI'
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}"
              maxZoom={20}
            />
          </LayersControl.BaseLayer>

          {/* ── Overlay: Catastro ── */}
          {catastroData && catastroData.features.length > 0 && (
            <LayersControl.Overlay checked name="Catastro Rural">
              <GeoJSON
                data={catastroData}
                style={{ color: '#f97316', weight: 1.5, fillColor: '#f97316', fillOpacity: 0.08, opacity: 0.7 }}
                onEachFeature={(feature, layer) => {
                  const p = feature.properties;
                  if (p) {
                    layer.bindTooltip(
                      `<b>${p.apellidos || ''} ${p.nombres || ''}</b><br/>
                       Clave: ${p.clave_cata || '—'}<br/>
                       Área: ${p.area_predi ? Number(p.area_predi).toLocaleString('es-EC') + ' m²' : '—'}`,
                      { sticky: true, opacity: 0.9 }
                    );
                  }
                }}
              />
            </LayersControl.Overlay>
          )}

          {/* ── Overlay: Ramales ── */}
          {ramalesData && ramalesData.features.length > 0 && (
            <LayersControl.Overlay checked name="Canales de Riego">
              <GeoJSON
                data={ramalesData}
                style={{ color: '#38bdf8', weight: 2.5, opacity: 0.85, dashArray: '6 3' }}
                onEachFeature={(feature, layer) => {
                  const p = feature.properties;
                  if (p) {
                    const nombre = p.nombre || p.NOMBRE || p.name || p.ramal || Object.values(p)[0];
                    if (nombre) layer.bindTooltip(String(nombre), { sticky: true });
                  }
                }}
              />
            </LayersControl.Overlay>
          )}
        </LayersControl>

        {/* ── Fichas: NO dentro de LayersControl para evitar 524 checkboxes ── */}
        <FitBounds fichas={fichasConGeo} skip={!!selectedFichaMap} />
        <FlyToFicha ficha={selectedFichaMap} />
        {fichasConGeo.map((ficha) => (
          <FichaMarker key={ficha.id} ficha={ficha} coords={getCoords(ficha)} />
        ))}

        <MapLegend />
        <MouseCoordinates />
      </MapContainer>
    </div>
  );
}
