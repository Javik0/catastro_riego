// ═══════════════════════════════════════════════════════════
// Hook de Autenticación — Firebase Auth
// ═══════════════════════════════════════════════════════════

import { useState, useEffect, useCallback } from 'react';
import {
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signOut,
  type User,
} from 'firebase/auth';
import { doc, getDoc } from 'firebase/firestore';
import { auth, db } from '../lib/firebaseConfig';
import type { UserProfile, UserRole } from '../lib/types';

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

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      if (firebaseUser) {
        try {
          const profileDoc = await getDoc(doc(db, 'usuarios', firebaseUser.uid));
          const profile: UserProfile = profileDoc.exists()
            ? (profileDoc.data() as UserProfile)
            : {
                uid: firebaseUser.uid,
                email: firebaseUser.email ?? '',
                nombre: firebaseUser.email?.split('@')[0] ?? 'Usuario',
                rol: 'cliente' as UserRole,
              };
          setState({ user: firebaseUser, userProfile: profile, loading: false, error: null });
        } catch {
          setState({
            user: firebaseUser,
            userProfile: {
              uid: firebaseUser.uid,
              email: firebaseUser.email ?? '',
              nombre: firebaseUser.email?.split('@')[0] ?? 'Usuario',
              rol: 'cliente',
            },
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

  const login = useCallback(async (email: string, password: string) => {
    setState((s) => ({ ...s, loading: true, error: null }));
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
    await signOut(auth);
  }, []);

  const isAdmin = state.userProfile?.rol === 'admin';

  return { ...state, login, logout, isAdmin };
}
