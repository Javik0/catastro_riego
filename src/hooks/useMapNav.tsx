// ═══════════════════════════════════════════════════════════
// Contexto de Navegación al Mapa
// Permite a la tabla de fichas "centrar" el mapa en una ficha
// ═══════════════════════════════════════════════════════════

import { createContext, useContext, useState, type ReactNode } from 'react';
import type { FichaPredio } from '../lib/types';

interface MapNavContextType {
  selectedFichaMap: FichaPredio | null;
  navigateToFichaMap: (ficha: FichaPredio) => void;
  clearMapSelection: () => void;
}

const MapNavContext = createContext<MapNavContextType | null>(null);

export function MapNavProvider({ children }: { children: ReactNode }) {
  const [selectedFichaMap, setSelectedFichaMap] = useState<FichaPredio | null>(null);

  const navigateToFichaMap = (ficha: FichaPredio) => {
    setSelectedFichaMap(ficha);
  };

  const clearMapSelection = () => {
    setSelectedFichaMap(null);
  };

  return (
    <MapNavContext.Provider value={{ selectedFichaMap, navigateToFichaMap, clearMapSelection }}>
      {children}
    </MapNavContext.Provider>
  );
}

export function useMapNav() {
  const ctx = useContext(MapNavContext);
  if (!ctx) throw new Error('useMapNav debe usarse dentro de MapNavProvider');
  return ctx;
}
