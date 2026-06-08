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
import RoleProtectedRoute from './components/auth/RoleProtectedRoute';
import DashboardLayout from './components/layout/DashboardLayout';
import DashboardHome from './components/dashboard/DashboardHome';
import MapPage from './components/map/MapPage';
import FichasPage from './components/fichas/FichasPage';
import ReportesPage from './components/reportes/ReportesPage';
import EncuestaPublicaPage from './components/encuestas/EncuestaPublicaPage';
import AdminEncuestasPage from './components/encuestas/AdminEncuestasPage';

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
        const fichasData: FichaPredio[] = fichasGeo.features.map((f: any) => {
          let com = (f.properties.comunidad || '')
            .replace(/LARCACOCHA/ig, 'LARCACHACA')
            .replace(/INSACATA/ig, 'IZACATA')
            .replace(/^None$/i, '')
            .trim();
          
          if (f.properties.fecha_creacion) {
            const d = safeToDate(f.properties.fecha_creacion);
            // Usamos UTC para evitar discrepancias por la zona horaria del navegador del cliente
            if (d.getUTCFullYear() === 2026 && d.getUTCMonth() === 4) { // Mayo es mes 4
              const dia = d.getUTCDate();
              if (!com || com === '') {
                if (dia === 22) com = 'LA LIBERTAD';
                else if (dia === 26) com = 'CHAMBITOLA';
              }
              // Corrección para el 24 de mayo (registros del técnico u0_a279 mal etiquetados como Asoc. 17 de Junio pertenecen a San José)
              if (dia === 24 && (com === 'ASOCIACIÓN 17 DE JUNIO' || com === 'ASOCIACION 17 DE JUNIO')) {
                com = 'SAN JOSÉ';
              }
              // Corrección para el lunes 25 de mayo (se reasignan según la hora local de campo SOLO si estaba vacío en QField)
              if (dia === 25 && (!com || com === '')) {
                const hour = d.getUTCHours();
                if (hour >= 8 && hour < 15) {
                  com = 'MILAGRO';
                } else if (hour >= 15) {
                  com = 'ASOCIACIÓN 17 DE JUNIO';
                }
              }
            }
          }

          // Cambio de comunidad solicitado por técnicos (de Milagro a San José) para regantes específicos
          const ced = (f.properties.cedula || '').trim();
          const clav = (f.properties.clave_catastral || '').trim();
          const cidsToSanJose = [
            '1711308682', '1717858011', '1716464753', '1715022719', 
            '1722217930', '1707701726', '1714912233', '1712437407', '1707701700'
          ];
          const clavesToSanJose = [
            '1702520560029', '1702520560018', '1702520560013', '1702520560004',
            '1702520560048', '1702520550007', '1702520980102', '1702520560039', '1702520980069'
          ];

          if (cidsToSanJose.includes(ced) || clavesToSanJose.includes(clav)) {
            com = 'SAN JOSÉ';
          }

          const cidsToLaLibertad = ['1715033013'];
          const clavesToLaLibertad = ['1702520540066'];

          if (cidsToLaLibertad.includes(ced) || clavesToLaLibertad.includes(clav)) {
            com = 'LA LIBERTAD';
          }

          return {
            ...f.properties,
            id: f.properties.id?.toString() || f.properties.fid?.toString() || String(Math.random()),
            geo: f.geometry ? {
              lat: f.geometry.coordinates[1],
              lng: f.geometry.coordinates[0],
            } : undefined,
            _geojson: f.geometry,
            propietario: `${f.properties.apellidos || ''} ${f.properties.nombres || ''}`.trim() || f.properties.propietario || '',
            area_total: f.properties.area_total || 0,
            area_riego: f.properties.area_riego || 0,
            area_sin_riego: f.properties.area_sin_riego || 0,
            creado_por: f.properties.creado_por || '',
            parroquia: f.properties.parroquia || '',
            comunidad: com,
            sector_investigacion: f.properties.sector_investigacion || 'Sector 1',
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
          };
        });
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
    if (filtros.sectorInv && f.sector_investigacion !== filtros.sectorInv) return false;
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
                    <RoleProtectedRoute allowedRoles={['admin', 'cliente', 'tecnico']}>
                      <FilteredDataProvider>
                        {({ fichas, cultivosData, animalesData, prediosAdicionalesData, loading }) => (
                          <DashboardHome
                            fichas={fichas}
                            cultivosData={cultivosData}
                            animalesData={animalesData}
                            prediosAdicionalesData={prediosAdicionalesData}
                            loading={loading}
                          />
                        )}
                      </FilteredDataProvider>
                    </RoleProtectedRoute>
                  }
                />
                <Route
                  path="mapa"
                  element={
                    <RoleProtectedRoute allowedRoles={['admin', 'cliente', 'tecnico']}>
                      <FilteredDataProvider>
                        {({ fichas, prediosAdicionalesData, loading }) => (
                          <MapPage fichas={fichas} prediosAdicionalesData={prediosAdicionalesData} loading={loading} />
                        )}
                      </FilteredDataProvider>
                    </RoleProtectedRoute>
                  }
                />
                <Route
                  path="fichas"
                  element={
                    <RoleProtectedRoute allowedRoles={['admin', 'cliente']}>
                      <FilteredDataProvider>
                        {({ fichas, loading }) => <FichasPage fichas={fichas} loading={loading} />}
                      </FilteredDataProvider>
                    </RoleProtectedRoute>
                  }
                />
                <Route
                  path="reportes"
                  element={
                    <RoleProtectedRoute allowedRoles={['admin', 'cliente']}>
                      <FilteredDataProvider>
                        {({ fichas, allFichas, cultivosData, animalesData, prediosAdicionalesData, loading }) => (
                          <ReportesPage
                            fichas={fichas}
                            allFichas={allFichas}
                            cultivosData={cultivosData}
                            animalesData={animalesData}
                            prediosAdicionalesData={prediosAdicionalesData}
                            loading={loading}
                          />
                        )}
                      </FilteredDataProvider>
                    </RoleProtectedRoute>
                  }
                />
                <Route
                  path="encuestas"
                  element={
                    <RoleProtectedRoute allowedRoles={['admin', 'tecnico']}>
                      <AdminEncuestasPage />
                    </RoleProtectedRoute>
                  }
                />
              </Route>

              {/* Encuesta pública abierta para los comuneros/regantes */}
              <Route path="/encuesta" element={<EncuestaPublicaPage />} />

              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </FiltrosProvider>
        </BrowserRouter>
      </MapNavProvider>
    </ThemeProvider>
  );
}
