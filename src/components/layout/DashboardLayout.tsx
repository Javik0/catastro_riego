import { Outlet, useLocation } from 'react-router-dom';
import { useState } from 'react';
import Sidebar from './Sidebar';
import Header from './Header';

export default function DashboardLayout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  // La represa es una vista única de mapa: menú recogido a íconos y sin el
  // acolchado del main, para que el lienzo ocupe todo. Al salir, todo vuelve.
  const esRepresa = useLocation().pathname.startsWith('/represa');

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
