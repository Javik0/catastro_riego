@echo off
rem Lanzador para quien recibe el paquete: doble clic y listo, sin instalar nada.
rem Tambien acepta que se le arrastre encima la carpeta de fichas a actualizar.
title Actualizar las fichas del padron
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0actualizar-fichas.ps1" -Destino "%~1"
