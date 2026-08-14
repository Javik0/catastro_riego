// ═══════════════════════════════════════════════════════════
// Hook de Autenticación — Firebase Auth
// Con auto-logout por inactividad (30 minutos)
// ═══════════════════════════════════════════════════════════

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signOut,
  type User,
} from 'firebase/auth';
import { doc, getDoc } from 'firebase/firestore';
import { auth, db } from '../lib/firebaseConfig';
import type { UserProfile, UserRole } from '../lib/types';

const INACTIVITY_TIMEOUT_MS = 1_800_000; // 30 minutos

// ── Sesión simulada para desarrollo ──────────────────────────────────────────
//
// Trabajar en local obligaba a escribir las credenciales reales cada vez que se
// reiniciaba el servidor. Con `VITE_DEV_LOGIN=1` en `.env.local` la aplicación
// arranca ya dentro, sin tocar Firebase, y `VITE_DEV_ROL` permite ver la
// aplicación como la ve cada rol — la única forma cómoda de comprobar que el
// cliente no llega a Represa ni a Reportes.
//
// Por qué esto NO llega a producción: `import.meta.env.DEV` es una constante que
// Vite sustituye por `false` al compilar, así que la condición entera se elimina
// del bundle. Aun así se comprueba también la variable, que vive en `.env.local`
// y no está en el repositorio. En un `npm run build` no queda ni el rastro.
//
// No sustituye a probar el login de verdad: para eso, apagar la variable.
const DEV_LOGIN = import.meta.env.DEV && import.meta.env.VITE_DEV_LOGIN === '1';

const perfilDeDesarrollo = (): UserProfile => {
  const rol = (import.meta.env.VITE_DEV_ROL || 'admin') as UserRole;
  return {
    uid: 'dev-local',
    email: `dev-${rol}@local`,
    nombre: `Desarrollo (${rol})`,
    rol,
  };
};

interface AuthState {
  user: User | null;
  userProfile: UserProfile | null;
  loading: boolean;
  error: string | null;
}

export function useAuth() {
  const [state, setState] = useState<AuthState>({
    user: null,
    userProfile: null,
    loading: true,
    error: null,
  });
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);

  // ── Listener de autenticación ──
  useEffect(() => {
    if (DEV_LOGIN) {
      // sesión simulada: ni se abre el listener de Firebase
      const perfil = perfilDeDesarrollo();
      console.info(`[dev] sesión simulada como ${perfil.rol}. ` +
                   'Apaga VITE_DEV_LOGIN en .env.local para probar el login real.');
      setState({
        user: { uid: perfil.uid, email: perfil.email } as User,
        userProfile: perfil,
        loading: false,
        error: null,
      });
      return;
    }

    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      if (firebaseUser) {
        try {
          const profileDoc = await getDoc(doc(db, 'usuarios', firebaseUser.uid));
          let profile: UserProfile = profileDoc.exists()
            ? (profileDoc.data() as UserProfile)
            : {
                uid: firebaseUser.uid,
                email: firebaseUser.email ?? '',
                nombre: firebaseUser.email?.split('@')[0] ?? 'Usuario',
                rol: 'cliente' as UserRole,
              };
          
          // Asegurar rol de administrador para los correos principales del proyecto
          if (
            firebaseUser.email === 'javier@proyectos-apcatastros.ec' ||
            firebaseUser.email === 'javier@proyectos_apcatastros.ec' ||
            firebaseUser.email === 'javier@consorcio-cayambe.ec' ||
            firebaseUser.email === 'jvkdigitalizacion@gmail.com'
          ) {
            profile.rol = 'admin';
          }
          
          setState({ user: firebaseUser, userProfile: profile, loading: false, error: null });
          setSessionExpired(false);
        } catch {
          const fallbackProfile: UserProfile = {
            uid: firebaseUser.uid,
            email: firebaseUser.email ?? '',
            nombre: firebaseUser.email?.split('@')[0] ?? 'Usuario',
            rol: (
              firebaseUser.email === 'javier@proyectos-apcatastros.ec' ||
              firebaseUser.email === 'javier@proyectos_apcatastros.ec' ||
              firebaseUser.email === 'javier@consorcio-cayambe.ec' ||
              firebaseUser.email === 'jvkdigitalizacion@gmail.com'
            ) ? 'admin' : 'cliente',
          };
          setState({
            user: firebaseUser,
            userProfile: fallbackProfile,
            loading: false,
            error: null,
          });
        }
      } else {
        setState({ user: null, userProfile: null, loading: false, error: null });
      }
    });
    return unsubscribe;
  }, []);

  // ── Auto-logout por inactividad ──
  const resetInactivityTimer = useCallback(() => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    // en la sesión simulada no hay nada que expirar, y hacerlo dejaría la
    // pantalla pidiendo un login que en local no queremos
    if (!state.user || DEV_LOGIN) return;

    timeoutRef.current = setTimeout(async () => {
      try {
        await signOut(auth);
        setSessionExpired(true);
      } catch {}
    }, INACTIVITY_TIMEOUT_MS);
  }, [state.user]);

  useEffect(() => {
    if (!state.user) return;

    // Eventos de actividad del usuario
    const events = ['mousedown', 'mousemove', 'keydown', 'scroll', 'touchstart', 'click'];
    const handler = () => resetInactivityTimer();

    events.forEach((e) => window.addEventListener(e, handler, { passive: true }));
    resetInactivityTimer(); // Iniciar el timer

    return () => {
      events.forEach((e) => window.removeEventListener(e, handler));
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, [state.user, resetInactivityTimer]);

  const login = useCallback(async (email: string, password: string) => {
    setState((s) => ({ ...s, loading: true, error: null }));
    setSessionExpired(false);
    try {
      await signInWithEmailAndPassword(auth, email, password);
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message.includes('invalid-credential')
            ? 'Correo o contraseña incorrectos'
            : err.message.includes('too-many-requests')
              ? 'Demasiados intentos. Intenta más tarde'
              : err.message.includes('network')
                ? 'Error de conexión. Verifica tu internet'
                : 'Error al iniciar sesión'
          : 'Error desconocido';
      setState((s) => ({ ...s, loading: false, error: msg }));
      throw new Error(msg);
    }
  }, []);

  const logout = useCallback(async () => {
    setSessionExpired(false);
    if (DEV_LOGIN) {
      // Firebase no tiene ninguna sesión que cerrar: se vacía el estado para
      // poder ver la pantalla de login. Recargar vuelve a entrar.
      setState({ user: null, userProfile: null, loading: false, error: null });
      return;
    }
    await signOut(auth);
  }, []);

  const isAdmin = state.userProfile?.rol === 'admin';
  const isTecnico = state.userProfile?.rol === 'tecnico';
  const isCliente = state.userProfile?.rol === 'cliente';

  return { ...state, login, logout, isAdmin, isTecnico, isCliente, sessionExpired };
}
