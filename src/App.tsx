import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { useAuth } from './hooks/useAuth';
import { FiltrosProvider, useFiltros } from './hooks/useFiltros';
import { ThemeProvider } from './hooks/useTheme';
import { MapNavProvider } from './hooks/useMapNav';
import { type FichaPredio, safeToDate } from './lib/types';
import { getNombreTecnico } from './lib/constants';
import LoginPage from './components/auth/LoginPage';
import ProtectedRoute from './components/auth/ProtectedRoute';
import DashboardLayout from './components/layout/DashboardLayout';
import DashboardHome from './components/dashboard/DashboardHome';
import MapPage from './components/map/MapPage';
import FichasPage from './components/fichas/FichasPage';
import ReportesPage from './components/reportes/ReportesPage';

// ── Data Loader: lee los GeoJSON exportados ──
function useLocalData() {
  const [fichas, setFichas] = useState<FichaPredio[]>([]);
  const [cultivosData, setCultivosData] = useState<any[]>([]);
  const [animalesData, setAnimalesData] = useState<any[]>([]);
  const [prediosAdicionalesData, setPrediosAdicionalesData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const fichasRes = await fetch('/geo/fichas_predios.geojson');
        const fichasGeo = await fichasRes.json();
        const fichasData: FichaPredio[] = fichasGeo.features.map((f: any) => ({
          ...f.properties,
          id: f.properties.id?.toString() || f.properties.fid?.toString() || String(Math.random()),
          geo: f.geometry ? {
            lat: f.geometry.coordinates[1],
            lng: f.geometry.coordinates[0],
          } : undefined,
          _geojson: f.geometry,
          propietario: f.properties.propietario || `${f.properties.apellidos || ''} ${f.properties.nombres || ''}`.trim(),
          area_total: f.properties.area_total || 0,
          area_riego: f.properties.area_riego || 0,
          area_sin_riego: f.properties.area_sin_riego || 0,
          creado_por: f.properties.creado_por || '',
          parroquia: f.properties.parroquia || '',
          comunidad: f.properties.comunidad || '',
          sector: f.properties.sector || '',
          cedula: f.properties.cedula || '',
          codigo_final: f.properties.codigo_final || '',
          cod_poligono: f.properties.cod_poligono || '',
          num_predio: f.properties.num_predio || 0,
          apellidos: f.properties.apellidos || '',
          nombres: f.properties.nombres || '',
          clave_catastral: f.properties.clave_catastral || '',
          tenencia_predio: f.properties.tenencia_predio || '',
          nivel_instruccion: f.properties.nivel_instruccion || '',
        }));
        setFichas(fichasData);

        const cultRes = await fetch('/geo/cultivos.json');
        setCultivosData(await cultRes.json());

        const animRes = await fetch('/geo/animales.json');
        setAnimalesData(await animRes.json());

        const predRes = await fetch('/geo/predios_adicionales.json');
        setPrediosAdicionalesData(await predRes.json());
      } catch (err) {
        console.error('Error loading data:', err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return { fichas, cultivosData, animalesData, prediosAdicionalesData, loading };
}

// ── Wrapper que aplica filtros globales ──
function FilteredDataProvider({ children }: { children: (props: {
  fichas: FichaPredio[];
  allFichas: FichaPredio[];
  cultivosData: any[];
  animalesData: any[];
  prediosAdicionalesData: any[];
  loading: boolean;
}) => React.ReactNode }) {
  const { fichas: allFichas, cultivosData, animalesData, prediosAdicionalesData, loading } = useLocalData();
  const { filtros } = useFiltros();

  const filtered = allFichas.filter((f) => {
    if (filtros.parroquia && f.parroquia !== filtros.parroquia) return false;
    if (filtros.sector && f.sector !== filtros.sector) return false;
    if (filtros.tecnico && getNombreTecnico(f.creado_por) !== filtros.tecnico) return false;
    if (filtros.comunidad && (f.comunidad || f.sector_comunidad || '').trim() !== filtros.comunidad) return false;
    if (filtros.fechaDesde && safeToDate(f.fecha_creacion) < new Date(filtros.fechaDesde)) return false;
    if (filtros.fechaHasta) {
      const hasta = new Date(filtros.fechaHasta);
      hasta.setHours(23, 59, 59);
      if (safeToDate(f.fecha_creacion) > hasta) return false;
    }
    if (filtros.busqueda) {
      const q = filtros.busqueda.toLowerCase();
      const match = [f.propietario, f.apellidos, f.nombres, f.cedula, f.codigo_final, f.clave_catastral]
        .some((v) => v?.toLowerCase().includes(q));
      if (!match) return false;
    }
    return true;
  });

  return <>{children({ fichas: filtered, allFichas, cultivosData, animalesData, prediosAdicionalesData, loading })}</>;
}

// ── App Principal ──
export default function App() {
  const { user, loading: authLoading } = useAuth();

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: 'var(--bg-primary)' }}>
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Cargando...</p>
        </div>
      </div>
    );
  }

  return (
    <ThemeProvider>
      <MapNavProvider>
        <BrowserRouter>
          <FiltrosProvider>
            <Routes>
              <Route path="/login" element={user ? <Navigate to="/" replace /> : <LoginPage />} />

              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <DashboardLayout />
                  </ProtectedRoute>
                }
              >
                <Route
                  index
                  element={
                    <FilteredDataProvider>
                      {({ fichas, cultivosData, loading }) => (
                        <DashboardHome fichas={fichas} cultivosData={cultivosData} loading={loading} />
                      )}
                    </FilteredDataProvider>
                  }
                />
                <Route
                  path="mapa"
                  element={
                    <FilteredDataProvider>
                      {({ fichas, loading }) => (
                        <MapPage fichas={fichas} loading={loading} />
                      )}
                    </FilteredDataProvider>
                  }
                />
                <Route
                  path="fichas"
                  element={
                    <FilteredDataProvider>
                      {({ fichas, loading }) => <FichasPage fichas={fichas} loading={loading} />}
                    </FilteredDataProvider>
                  }
                />
                <Route
                  path="reportes"
                  element={
                    <FilteredDataProvider>
                      {({ fichas, cultivosData, animalesData, prediosAdicionalesData, loading }) => (
                        <ReportesPage
                          fichas={fichas}
                          cultivosData={cultivosData}
                          animalesData={animalesData}
                          prediosAdicionalesData={prediosAdicionalesData}
                          loading={loading}
                        />
                      )}
                    </FilteredDataProvider>
                  }
                />
              </Route>

              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </FiltrosProvider>
        </BrowserRouter>
      </MapNavProvider>
    </ThemeProvider>
  );
}
