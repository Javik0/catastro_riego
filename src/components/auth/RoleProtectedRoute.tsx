import { Navigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { Loader2 } from 'lucide-react';

interface Props {
  children: React.ReactNode;
  allowedRoles: ('admin' | 'cliente' | 'tecnico')[];
}

export default function RoleProtectedRoute({ children, allowedRoles }: Props) {
  const { user, userProfile, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
          <p className="text-slate-400 text-sm">Verificando permisos...</p>
        </div>
      </div>
    );
  }

  if (!user || !userProfile) {
    return <Navigate to="/login" replace />;
  }

  const userRole = userProfile.rol;

  if (!allowedRoles.includes(userRole)) {
    // Redirigir según el rol del usuario para evitar bloqueos
    if (userRole === 'tecnico') {
      return <Navigate to="/encuestas" replace />;
    }
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
