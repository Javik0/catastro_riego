@echo off
chcp 65001 >nul
title Sincronización - Padrón de Riego Porotog
cd /d "%~dp0"
echo.
echo ══════════════════════════════════════════════════
echo   SINCRONIZACIÓN - Padrón de Riego Porotog
echo ══════════════════════════════════════════════════
echo.

:: Paso 1: Exportar datos desde GeoPackage
echo [1/5] Exportando datos desde QFieldCloud...
echo.
python -X utf8 scripts/export_geojson.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo ❌ ERROR en la exportación. Verifica que Python y pyproj estén instalados.
    pause
    exit /b 1
)

echo.
echo ──────────────────────────────────────────────────

:: Paso 2: Sincronizar Fotos a Firebase Storage
echo [2/5] Sincronizando fotos a Firebase Storage...
echo.
python scripts/sync_photos.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo ❌ ERROR en la sincronización de fotos.
    pause
    exit /b 1
)

echo.
echo ──────────────────────────────────────────────────

:: Paso 3: Entrega cartografica para el contratante (GeoPackage + proyecto QGIS)
:: Se regenera aqui para que el cliente nunca descargue datos mas viejos que la web.
echo [3/5] Generando entrega cartografica para el contratante...
echo.
python -X utf8 scripts/generar_gpkg_cliente.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo ⚠  No se pudo generar el GeoPackage. La web se publica igual,
    echo    pero el paquete de descarga quedara con la version anterior.
    pause
) else (
    python -X utf8 scripts/generar_proyecto_qgis_cliente.py
    if %ERRORLEVEL% neq 0 (
        echo.
        echo ⚠  No se pudo armar el paquete .zip. Revisa el mensaje de arriba.
        pause
    )
)

echo.
echo ──────────────────────────────────────────────────

:: Paso 4: Subir a GitHub
echo [4/5] Subiendo cambios a GitHub...
echo.
git add .
git commit -m "data: sync QFieldCloud %date% %time:~0,5%"
git push origin main
if %ERRORLEVEL% neq 0 (
    echo.
    echo ❌ ERROR al subir a GitHub. Verifica tu conexión.
    pause
    exit /b 1
)

echo.
echo ──────────────────────────────────────────────────

:: Paso 5: Build + Deploy a Firebase
echo [5/5] Compilando y desplegando a Firebase Hosting...
echo.
call npm run build
if %ERRORLEVEL% neq 0 (
    echo.
    echo ❌ ERROR en la compilación. Revisa los errores de TypeScript.
    pause
    exit /b 1
)

call npx firebase deploy --only hosting
if %ERRORLEVEL% neq 0 (
    echo.
    echo ❌ ERROR al desplegar. Verifica tu autenticación de Firebase.
    pause
    exit /b 1
)

echo.
echo ══════════════════════════════════════════════════
echo   ✅ SINCRONIZACIÓN COMPLETADA
echo   🌐 https://invs-riego-comunitario.web.app
echo ══════════════════════════════════════════════════
echo.
pause
