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
echo [1/3] Exportando datos desde QFieldCloud...
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

:: Paso 2: Subir a GitHub
echo [2/3] Subiendo cambios a GitHub...
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

:: Paso 3: Build + Deploy a Firebase
echo [3/3] Compilando y desplegando a Firebase Hosting...
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
