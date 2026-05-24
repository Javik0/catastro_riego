# 🌊 Dashboard — Catastro de Riego Comunitario Guanguilqui Porotog

**Estudio Definitivo de Presa en el Río Porotog**  
Prefectura de Pichincha — Cantón Cayambe | Consorcio Cayambe SPT

---

## 📋 Descripción

Dashboard web para visualización y análisis del **Padrón de Usuarios del Sistema de Riego Comunitario Guanguilqui Porotog**. Muestra los datos recolectados en campo mediante QField, incluyendo fichas de predios, ubicaciones GPS, cultivos, animales y estadísticas por parroquia y técnico.

## 🏗️ Tecnologías

| Capa | Tecnología |
|------|-----------|
| Frontend | React 19 + TypeScript + Vite |
| Estilos | TailwindCSS v4 |
| Mapa | Leaflet + React-Leaflet |
| Gráficos | Recharts |
| Base de datos | Firebase Firestore |
| Autenticación | Firebase Auth |
| Almacenamiento | Firebase Storage (fotos) |
| Hosting | Firebase Hosting |
| Reportes | jsPDF + xlsx |

## 📁 Estructura del Proyecto

```
padron-app/
├── public/
│   ├── geo/                    # GeoJSON generados (snapshot del último sync)
│   │   ├── fichas_predios.geojson     # 524+ fichas investigadas (puntos GPS)
│   │   ├── cultivos.json              # 905+ registros de cultivos
│   │   ├── animales.json              # 713+ registros de animales
│   │   ├── catastro_relevantes.geojson # Polígonos con fichas asociadas
│   │   └── predios_adicionales.json
│   ├── logo-izq.png            # Logo Prefectura de Pichincha
│   └── logo-der.png            # Logo Consorcio Cayambe SPT
├── src/
│   ├── components/
│   │   ├── auth/               # Login, ProtectedRoute
│   │   ├── dashboard/          # KPIs, gráficos estadísticos
│   │   ├── fichas/             # Tabla + modal de detalle
│   │   ├── layout/             # Sidebar, Header, DashboardLayout
│   │   ├── map/                # Mapa Leaflet interactivo
│   │   └── reportes/           # Exportación PDF y Excel
│   ├── hooks/                  # useAuth, useFiltros, useTheme, useMapNav
│   └── lib/                    # firebaseConfig, types, constants, firestoreService
├── scripts/
│   ├── export_geojson.py       # Exporta .gpkg → GeoJSON/JSON
│   ├── sync_to_firestore.py    # Sube datos a Firestore (pendiente)
│   └── inspect_gpkg.py         # Inspección del esquema del GeoPackage
├── firebase.json               # Configuración Firebase Hosting + Firestore
├── firestore.rules             # Reglas de seguridad Firestore
└── storage.rules               # Reglas de seguridad Storage
```

## 🔄 Flujo de Datos — QField → Firebase

```
QField (tablet)
    ↓ sync
QFieldCloud
    ↓ descarga manual del .gpkg
C:\Users\HP\QField\cloud\porotog_levantamiento_offline\data.gpkg
    ↓ scripts/export_geojson.py
public/geo/*.geojson  (para el mapa en local)
    ↓ scripts/sync_to_firestore.py  [próximamente automático]
Firebase Firestore  (para filtros avanzados y online)
Firebase Storage    (para fotos del campo)
```

## 🚀 Desarrollo Local

```bash
# Instalar dependencias
npm install

# Iniciar servidor de desarrollo
npm run dev

# Exportar datos desde el GeoPackage local
python scripts/export_geojson.py

# Build de producción
npm run build
```

## 🌐 Deploy a Firebase Hosting

```bash
# Login (primera vez)
firebase login

# Deploy completo
firebase deploy

# Solo Hosting
firebase deploy --only hosting

# URL de producción
# https://invs-riego-comunitario.web.app
```

## 🔐 Roles de Acceso

| Rol | Acceso | Descripción |
|-----|--------|-------------|
| `admin` | Lectura + escritura | Consorcio Cayambe SPT |
| `cliente` | Solo lectura | Prefectura de Pichincha |

Los usuarios se crean en **Firebase Console → Authentication** y su rol se asigna en **Firestore → colección `usuarios`**.

## 📊 Datos del Campo

- **Fichas investigadas:** 524+
- **Cultivos registrados:** 905+
- **Animales registrados:** 713+
- **Predios adicionales:** 114+
- **Polígonos catastro:** 24,452 (base catastral completa)
- **Parroquias:** Cangahua, Otón, Cusubamba, Ascázubi
- **Técnicos activos:** 8

## 📝 Notas Importantes

- Los archivos `.gpkg` **NO** se versionan en git (son grandes y contienen datos crudos que se regeneran del sync de QFieldCloud).
- Los GeoJSON en `public/geo/` **SÍ** se versionan como snapshot del último sync exitoso.
- Las fotos de los predios van en **Firebase Storage**, no en el repositorio.
- Las credenciales de Firebase están en el código fuente (son credenciales públicas de web app, no claves de servicio).

---

**© 2026 Consorcio Cayambe SPT — Prefectura de Pichincha**
