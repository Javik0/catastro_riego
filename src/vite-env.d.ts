/// <reference types="vite/client" />

/**
 * Variables de entorno del proyecto.
 *
 * Las de desarrollo viven en `.env.local`, que no está en el repositorio.
 * Ver `.env.example` para qué hace cada una.
 */
interface ImportMetaEnv {
  /** '1' entra al sistema sin login en `npm run dev`. Nunca llega a producción. */
  readonly VITE_DEV_LOGIN?: string;
  /** Rol de la sesión simulada: 'admin' | 'tecnico' | 'cliente'. Por defecto admin. */
  readonly VITE_DEV_ROL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
