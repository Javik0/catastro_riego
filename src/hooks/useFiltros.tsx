// ═══════════════════════════════════════════════════════════
// Contexto de Filtros Globales del Dashboard
// ═══════════════════════════════════════════════════════════

import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import type { FiltrosState } from '../lib/types';

const INITIAL_FILTROS: FiltrosState = {
  parroquia: '',
  sector: '',
  tecnico: '',
  fechaDesde: '',
  fechaHasta: '',
  busqueda: '',
};

interface FiltrosContextType {
  filtros: FiltrosState;
  setFiltro: <K extends keyof FiltrosState>(key: K, value: FiltrosState[K]) => void;
  resetFiltros: () => void;
  hasActiveFilters: boolean;
}

const FiltrosContext = createContext<FiltrosContextType | null>(null);

export function FiltrosProvider({ children }: { children: ReactNode }) {
  const [filtros, setFiltros] = useState<FiltrosState>(INITIAL_FILTROS);

  const setFiltro = useCallback(<K extends keyof FiltrosState>(key: K, value: FiltrosState[K]) => {
    setFiltros((prev) => ({ ...prev, [key]: value }));
  }, []);

  const resetFiltros = useCallback(() => {
    setFiltros(INITIAL_FILTROS);
  }, []);

  const hasActiveFilters = Object.values(filtros).some((v) => v !== '');

  return (
    <FiltrosContext.Provider value={{ filtros, setFiltro, resetFiltros, hasActiveFilters }}>
      {children}
    </FiltrosContext.Provider>
  );
}

export function useFiltros() {
  const ctx = useContext(FiltrosContext);
  if (!ctx) throw new Error('useFiltros debe usarse dentro de FiltrosProvider');
  return ctx;
}
