import { useEffect, useState, useRef } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, LayersControl, useMap } from 'react-leaflet';
import type { CircleMarker as LeafletCircleMarker } from 'leaflet';
import { Loader2, MapPin, Eye, EyeOff } from 'lucide-react';
import { type FichaPredio, safeToDate } from '../../lib/types';
import { getNombreTecnico, getColorTecnico, TECNICOS } from '../../lib/constants';
import { useMapNav } from '../../hooks/useMapNav';
import 'leaflet/dist/leaflet.css';

interface Props {
  fichas: FichaPredio[];
  allFichas?: FichaPredio[];
  loading: boolean;
}

// ── Leyenda de técnicos ──
function MapLegend() {
  const [show, setShow] = useState(true);
  return (
    <div className="absolute bottom-4 right-4 z-[1000]">
      <button
        onClick={() => setShow(!show)}
        className="mb-1 p-1.5 rounded-md border cursor-pointer"
        style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)', color: 'var(--text-secondary)' }}
      >
        {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
      </button>
      {show && (
        <div
          className="rounded-lg border p-3 max-w-[180px]"
          style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
        >
          <p className="text-[10px] font-semibold mb-2 uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Técnicos</p>
          <div className="space-y-1.5">
            {Object.entries(TECNICOS).map(([key, { nombre, color }]) => (
              <div key={key} className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full shrink-0 border border-white/20" style={{ background: color }} />
                <span className="text-[10px] truncate" style={{ color: 'var(--text-secondary)' }}>{nombre}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Centrar mapa en ficha seleccionada ──
function FlyToFicha({ ficha }: { ficha: FichaPredio | null }) {
  const map = useMap();

  useEffect(() => {
    if (!ficha) return;
    let lat: number | undefined, lng: number | undefined;
    if (ficha.geo?.lat && ficha.geo?.lng) {
      lat = ficha.geo.lat;
      lng = ficha.geo.lng;
    } else if (ficha._geojson?.coordinates) {
      lng = ficha._geojson.coordinates[0] as number;
      lat = ficha._geojson.coordinates[1] as number;
    }
    if (lat && lng) {
      map.flyTo([lat, lng], 17, { duration: 1.2 });
    }
  }, [ficha, map]);

  return null;
}

function FitBounds({ fichas, skipIfFicha }: { fichas: FichaPredio[]; skipIfFicha: boolean }) {
  const mapInstance = useMap();
  const fitted = useRef(false);

  useEffect(() => {
    if (skipIfFicha || fitted.current || fichas.length === 0) return;
    const points = fichas
      .filter((f) => f.geo?.lat || f._geojson?.coordinates)
      .map((f) => {
        if (f.geo) return [f.geo.lat, f.geo.lng] as [number, number];
        if (f._geojson?.coordinates) return [f._geojson.coordinates[1], f._geojson.coordinates[0]] as [number, number];
        return null;
      })
      .filter(Boolean) as [number, number][];
    if (points.length > 0) {
      try { mapInstance.fitBounds(points as any, { padding: [40, 40] }); fitted.current = true; } catch {}
    }
  }, [fichas, mapInstance, skipIfFicha]);
  return null;
}

// ── Marcador que se abre automáticamente ──
function AutoOpenMarker({ ficha, coords }: { ficha: FichaPredio; coords: [number, number] }) {
  const markerRef = useRef<LeafletCircleMarker | null>(null);
  const { selectedFichaMap } = useMapNav();

  useEffect(() => {
    if (selectedFichaMap?.id === ficha.id && markerRef.current) {
      setTimeout(() => {
        markerRef.current?.openPopup();
      }, 1300); // esperar el flyTo
    }
  }, [selectedFichaMap, ficha.id]);

  const color = getColorTecnico(ficha.creado_por);

  return (
    <CircleMarker
      ref={markerRef}
      center={coords}
      radius={selectedFichaMap?.id === ficha.id ? 10 : 6}
      pathOptions={{
        fillColor: color,
        fillOpacity: 0.9,
        color: selectedFichaMap?.id === ficha.id ? '#ffffff' : '#ffffff',
        weight: selectedFichaMap?.id === ficha.id ? 3 : 1.5,
      }}
    >
      <Popup maxWidth={320}>
        <div className="text-xs space-y-1.5 min-w-[220px]">
          <div className="font-bold text-sm border-b pb-1 mb-1">
            {ficha.propietario || `${ficha.apellidos} ${ficha.nombres}`}
          </div>
          <div className="grid grid-cols-2 gap-1">
            <span className="opacity-60">Código:</span>
            <span className="font-medium">{ficha.codigo_final}</span>
            <span className="opacity-60">Cédula:</span>
            <span>{ficha.cedula || '—'}</span>
            <span className="opacity-60">Parroquia:</span>
            <span>{ficha.parroquia}</span>
            <span className="opacity-60">Sector:</span>
            <span>{ficha.sector}</span>
            <span className="opacity-60">Área Total:</span>
            <span>{ficha.area_total?.toLocaleString('es-EC')} m²</span>
            <span className="opacity-60">Caudal:</span>
            <span>{ficha.caudal_valor ? `${ficha.caudal_valor} l/s` : '—'}</span>
            <span className="opacity-60">Cota:</span>
            <span>{ficha.cota_msnm ? `${ficha.cota_msnm} msnm` : '—'}</span>
            <span className="opacity-60">Técnico:</span>
            <span style={{ color }}>{getNombreTecnico(ficha.creado_por)}</span>
            <span className="opacity-60">Fecha:</span>
            <span>{safeToDate(ficha.fecha_creacion).toLocaleDateString('es-EC')}</span>
          </div>
          {ficha.foto_predio && (
            <div className="mt-2 text-center opacity-60 text-[10px]">📷 {ficha.foto_predio}</div>
          )}
        </div>
      </Popup>
    </CircleMarker>
  );
}

// ── Componente principal ──
export default function MapPage({ fichas, loading }: Props) {
  const { selectedFichaMap, clearMapSelection } = useMapNav();

  useEffect(() => {
    // Limpiar selección al desmontar
    return () => clearMapSelection();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-200px)]">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    );
  }

  const fichasConGeo = fichas.filter((f) => f.geo?.lat || f._geojson?.coordinates);

  const getCoords = (f: FichaPredio): [number, number] => {
    if (f.geo?.lat && f.geo?.lng) return [f.geo.lat, f.geo.lng];
    if (f._geojson?.coordinates) return [
      f._geojson.coordinates[1] as number,
      f._geojson.coordinates[0] as number,
    ];
    return [0, 0];
  };

  const defaultCenter: [number, number] = [0.04, -78.15];

  return (
    <div className="relative h-[calc(100vh-200px)] rounded-xl overflow-hidden border"
      style={{ borderColor: 'var(--border-color)' }}>
      {/* Stats overlay */}
      <div
        className="absolute top-4 left-4 z-[1000] backdrop-blur-sm rounded-lg border px-3 py-2"
        style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
      >
        <div className="flex items-center gap-2">
          <MapPin className="w-4 h-4 text-blue-400" />
          <span className="text-xs font-medium" style={{ color: 'var(--text-primary)' }}>
            {fichasConGeo.length} puntos
          </span>
          <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
            de {fichas.length} fichas
          </span>
        </div>
        {selectedFichaMap && (
          <div className="mt-1 pt-1 border-t" style={{ borderColor: 'var(--border-color)' }}>
            <p className="text-[10px] text-blue-400 flex items-center gap-1">
              <MapPin className="w-3 h-3" />
              {selectedFichaMap.propietario || selectedFichaMap.codigo_final}
            </p>
          </div>
        )}
      </div>

      <MapContainer
        center={defaultCenter}
        zoom={13}
        className="h-full w-full"
        style={{ background: '#0f172a' }}
      >
        <LayersControl position="topright">
          <LayersControl.BaseLayer checked name="OpenStreetMap">
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
          </LayersControl.BaseLayer>
          <LayersControl.BaseLayer name="ESRI Satélite">
            <TileLayer
              attribution='&copy; ESRI'
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            />
          </LayersControl.BaseLayer>
          <LayersControl.BaseLayer name="ESRI Topográfico">
            <TileLayer
              attribution='&copy; ESRI'
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}"
            />
          </LayersControl.BaseLayer>
        </LayersControl>

        <FitBounds fichas={fichasConGeo} skipIfFicha={!!selectedFichaMap} />
        <FlyToFicha ficha={selectedFichaMap} />

        {fichasConGeo.map((ficha) => (
          <AutoOpenMarker
            key={ficha.id}
            ficha={ficha}
            coords={getCoords(ficha)}
          />
        ))}

        <MapLegend />
      </MapContainer>
    </div>
  );
}
