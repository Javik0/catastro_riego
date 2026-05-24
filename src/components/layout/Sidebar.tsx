import { NavLink } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { useTheme } from '../../hooks/useTheme';
import {
  LayoutDashboard, Map, ClipboardList, FileText,
  LogOut, ChevronLeft, ChevronRight, Menu, X,
  Sun, Moon,
} from 'lucide-react';

const NAV_ITEMS = [
  { path: '/', icon: LayoutDashboard, label: 'Dashboard', end: true },
  { path: '/mapa', icon: Map, label: 'Mapa', end: false },
  { path: '/fichas', icon: ClipboardList, label: 'Fichas', end: false },
  { path: '/reportes', icon: FileText, label: 'Reportes', end: false },
];

interface Props {
  collapsed: boolean;
  onToggle: () => void;
  mobileOpen: boolean;
  onMobileClose: () => void;
}

export default function Sidebar({ collapsed, onToggle, mobileOpen, onMobileClose }: Props) {
  const { userProfile, logout, isAdmin } = useAuth();
  const { toggleTheme, isDark } = useTheme();

  const sidebarContent = (
    <div
      className="flex flex-col h-full border-r"
      style={{
        background: 'var(--bg-sidebar)',
        borderColor: 'var(--border-color)',
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 h-14 border-b"
        style={{ borderColor: 'var(--border-color)' }}
      >
        {!collapsed && (
          <span className="text-sm font-bold tracking-wide truncate text-amber-400">
            CATASTRO RIEGO
          </span>
        )}
        <button
          onClick={onToggle}
          className="hidden lg:flex items-center justify-center w-7 h-7 rounded-md transition-colors cursor-pointer hover:bg-white/10"
          style={{ color: 'var(--text-secondary)' }}
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
        <button
          onClick={onMobileClose}
          className="lg:hidden flex items-center justify-center w-7 h-7 rounded-md cursor-pointer hover:bg-white/10"
          style={{ color: 'var(--text-secondary)' }}
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-3 px-2 space-y-1">
        {NAV_ITEMS.map(({ path, icon: Icon, label, end }) => (
          <NavLink
            key={path}
            to={path}
            end={end}
            onClick={onMobileClose}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors group ${
                isActive
                  ? 'bg-blue-500/20 text-blue-300 border-l-2 border-blue-400'
                  : 'hover:bg-white/10'
              }`
            }
            style={({ isActive }) => ({
              color: isActive ? undefined : 'var(--text-muted)',
            })}
          >
            <Icon className="w-5 h-5 shrink-0" />
            {!collapsed && <span className="truncate">{label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* Bottom section */}
      <div className="border-t p-3 space-y-2" style={{ borderColor: 'var(--border-color)' }}>
        {/* Theme toggle — botón claramente visible */}
        <button
          onClick={toggleTheme}
          className={`flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm font-medium transition-all cursor-pointer border ${
            collapsed ? 'justify-center' : ''
          }`}
          style={{
            background: isDark ? 'rgba(251,191,36,0.12)' : 'rgba(99,102,241,0.12)',
            borderColor: isDark ? 'rgba(251,191,36,0.3)' : 'rgba(99,102,241,0.3)',
            color: isDark ? '#fbbf24' : '#818cf8',
          }}
          title={isDark ? 'Cambiar a tema claro' : 'Cambiar a tema oscuro'}
        >
          {isDark ? (
            <Sun className="w-4 h-4 shrink-0" />
          ) : (
            <Moon className="w-4 h-4 shrink-0" />
          )}
          {!collapsed && (
            <span className="text-xs font-semibold">
              {isDark ? '☀ Tema claro' : '🌙 Tema oscuro'}
            </span>
          )}
        </button>

        {/* User info */}
        {!collapsed && (
          <div className="mb-1 px-2">
            <p className="text-xs font-medium text-white truncate">
              {userProfile?.nombre || 'Usuario'}
            </p>
            <p className="text-[10px] truncate" style={{ color: 'var(--text-muted)' }}>
              {userProfile?.email}
            </p>
            <span className={`inline-block mt-1 px-2 py-0.5 rounded-full text-[9px] font-semibold uppercase tracking-wider ${
              isAdmin ? 'bg-amber-500/20 text-amber-400' : 'bg-blue-500/20 text-blue-400'
            }`}>
              {isAdmin ? 'Administrador' : 'Cliente'}
            </span>
          </div>
        )}

        {/* Logout */}
        <button
          onClick={logout}
          className={`flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm transition-colors cursor-pointer hover:bg-red-500/10 hover:text-red-400 ${
            collapsed ? 'justify-center' : ''
          }`}
          style={{ color: 'var(--text-secondary)' }}
        >
          <LogOut className="w-4 h-4 shrink-0" />
          {!collapsed && <span>Cerrar sesión</span>}
        </button>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop sidebar */}
      <aside
        className={`hidden lg:block shrink-0 transition-all duration-300 ${collapsed ? 'w-16' : 'w-60'}`}
      >
        {sidebarContent}
      </aside>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-50 flex">
          <div className="absolute inset-0 bg-black/60" onClick={onMobileClose} />
          <aside className="relative w-60 h-full z-10">
            {sidebarContent}
          </aside>
        </div>
      )}
    </>
  );
}

export function MobileMenuButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="lg:hidden flex items-center justify-center w-9 h-9 rounded-lg cursor-pointer hover:bg-white/10"
      style={{ color: 'var(--text-secondary)' }}
    >
      <Menu className="w-5 h-5" />
    </button>
  );
}
