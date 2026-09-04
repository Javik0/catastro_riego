import { Outlet, useLocation } from 'react-router-dom';
import { useEffect, useState } from 'react';
import Sidebar from './Sidebar';
import Header from './Header';

export default function DashboardLayout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  // La represa es una vista única de mapa: menú recogido a íconos y sin el
  // acolchado del main, para que el lienzo ocupe todo. Al salir, todo vuelve.
  const pathname = useLocation().pathname;
  const esRepresa = pathname.startsWith('/represa');

  // Al ENTRAR al mapa el menú se repliega solo, para dar espacio al lienzo
  // (pedido de JAVIKO, 3-sep-2026). A diferencia de Represa no queda forzado:
  // el usuario puede volver a abrirlo con el botón de siempre.
  const esMapa = pathname.startsWith('/mapa');
  useEffect(() => {
    if (esMapa) setSidebarCollapsed(true);
  }, [esMapa]);

  return (
    <div className="min-h-screen flex" style={{ background: 'var(--bg-primary)' }}>
      <Sidebar
        collapsed={sidebarCollapsed || esRepresa}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        mobileOpen={mobileOpen}
        onMobileClose={() => setMobileOpen(false)}
      />

      <div className="flex-1 flex flex-col min-w-0">
        <Header onMobileMenuOpen={() => setMobileOpen(true)} />
        <main className={`flex-1 overflow-y-auto ${esRepresa ? '' : 'p-4 lg:p-6'}`}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
