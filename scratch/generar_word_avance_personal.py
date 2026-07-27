# -*- coding: utf-8 -*-
import os
import shutil
import win32com.client

BASE_DIR = r'C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO'
HTML_PATH = os.path.join(BASE_DIR, 'informe_avance_personal_fichas_adicionales.html')
DOCX_ESCRITORIO = os.path.join(BASE_DIR, 'informe_avance_personal_fichas_adicionales.docx')
DOCX_DESCARGAS = r'C:\Users\HP\Downloads\informe_avance_personal_fichas_adicionales.docx'
DOCX_PUBLIC = os.path.join(BASE_DIR, 'padron-app', 'public', 'informe_avance_personal_fichas_adicionales.docx')

html_content = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Informe de Avance y Rendimiento de Personal - Fichas Adicionales</title>
<style>
    body {
        font-family: 'Calibri', 'Segoe UI', Arial, sans-serif;
        color: #1e293b;
        line-height: 1.5;
        margin: 40px;
    }
    h1 {
        color: #0f172a;
        font-size: 22pt;
        border-bottom: 3px solid #0284c7;
        padding-bottom: 8px;
        margin-bottom: 20px;
    }
    h2 {
        color: #0369a1;
        font-size: 14pt;
        margin-top: 24px;
        margin-bottom: 12px;
        border-left: 4px solid #0284c7;
        padding-left: 10px;
    }
    h3 {
        color: #334155;
        font-size: 12pt;
        margin-top: 18px;
        margin-bottom: 8px;
    }
    p, li {
        font-size: 11pt;
    }
    .header-box {
        background-color: #f0f9ff;
        border: 1px solid #bae6fd;
        border-radius: 6px;
        padding: 14px;
        margin-bottom: 24px;
    }
    .header-title {
        font-weight: bold;
        color: #0369a1;
        font-size: 12pt;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 12px;
        margin-bottom: 20px;
        font-size: 10pt;
    }
    th {
        background-color: #0f172a;
        color: #ffffff;
        font-weight: bold;
        text-align: left;
        padding: 8px 12px;
        border: 1px solid #0f172a;
    }
    td {
        padding: 7px 12px;
        border: 1px solid #cbd5e1;
    }
    tr:nth-child(even) td {
        background-color: #f8fafc;
    }
    .highlight-row td {
        background-color: #e0f2fe;
        font-weight: bold;
    }
    .badge-success {
        color: #15803d;
        font-weight: bold;
    }
    .badge-warning {
        color: #b45309;
        font-weight: bold;
    }
    .badge-info {
        color: #0369a1;
        font-weight: bold;
    }
    .note-box {
        background-color: #fefce8;
        border-left: 4px solid #eab308;
        padding: 12px;
        margin: 16px 0;
        font-size: 10.5pt;
    }
    .info-box {
        background-color: #f0fdf4;
        border-left: 4px solid #16a34a;
        padding: 12px;
        margin: 16px 0;
        font-size: 10.5pt;
    }
    .footer {
        margin-top: 40px;
        padding-top: 12px;
        border-top: 1px solid #cbd5e1;
        font-size: 9pt;
        color: #64748b;
        text-align: center;
    }
</style>
</head>
<body>

<div class="header-box">
    <div class="header-title">PROYECTO CATASTRO DE RIEGO GUANGUILQUÍ POROTOG</div>
    <div><strong>Informe Técnico:</strong> Avance Diario de Campo y Rendimiento por Personal (Fichas Adicionales - Sección 7)</div>
    <div><strong>Fecha de Evaluación:</strong> 27 de Julio de 2026 (Corte al 27 de Julio de 2026)</div>
    <div><strong>Elaborado por:</strong> Equipo Técnico de ap&catastro / Consorcio Cayambe SPT</div>
</div>

<h1>Reporte de Avance Diario y Rendimiento de Personal</h1>

<h2>1. Resumen General de Fichas Adicionales (Sección 7)</h2>
<p>El universo de predios adicionales declarados en la Sección 7 asciende a <strong>2,409 fichas hijas</strong> (Regla B: una ficha por cada regante declarante). El avance acumulado al corte de hoy se resume a continuación:</p>

<table>
    <thead>
        <tr>
            <th>Estado de Investigación</th>
            <th>Cantidad de Fichas</th>
            <th>Porcentaje</th>
            <th>Definición Operativa para la Gestión</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><span class="badge-success">Completadas en Campo (🟢)</span></td>
            <td><strong>660</strong></td>
            <td>27.4%</td>
            <td>Investigadas, verificadas y cerradas 100% por los técnicos en terreno.</td>
        </tr>
        <tr>
            <td><span class="badge-warning">En Revisión (Pre-cargadas 🔄)</span></td>
            <td><strong>108</strong></td>
            <td>4.5%</td>
            <td>Fichas con datos de producción pre-cargados de inspecciones previas, en proceso de validación rápida.</td>
        </tr>
        <tr>
            <td><span class="badge-info">Pendientes por Investigar (⚪)</span></td>
            <td><strong>1,641</strong></td>
            <td>68.1%</td>
            <td>Sección 4 vacía en programación de visita de campo.</td>
        </tr>
        <tr class="highlight-row">
            <td>TOTAL GENERADO (REGLA B)</td>
            <td>2,409</td>
            <td>100.0%</td>
            <td>Universo total de predios adicionales declarados en Sección 7.</td>
        </tr>
    </tbody>
</table>

<h2>2. Criterios Técnicos de Clasificación de Estados (Nota Aclaratoria para Supervisión)</h2>

<div class="info-box">
    Para garantizar absoluta claridad y transparencia en las auditorías de avance, los estados de investigación de los predios adicionales se definen según los siguientes criterios:
</div>

<ul>
    <li><strong>🟢 Completada (100% Verificada en Campo):</strong><br>
    Corresponde a predios adicionales donde el técnico de campo abrió la ficha en su dispositivo QField, entrevistó o confirmó directamente con el regante la producción de la Sección 4 (cultivos, ganado y riego), y dio el cierre definitivo.</li>
    
    <li><strong>🔄 En Revisión (Fichas Pre-cargadas / En Validación):</strong><br>
    Corresponde a fichas adicionales que <strong>NO están vacías</strong>, sino que cuentan con información de producción pre-cargada proveniente de inspecciones y censos anteriores (mayo-junio).<br>
    <em>¿Por qué están en este estado?</em> Se registran como <code>En Revisión</code> para que el técnico de campo las abra, confirme rápidamente con el regante que mantiene los mismos cultivos o animales, y con un solo clic cambie el estado a <code>Completada</code>. No requieren un levantamiento desde cero.</li>
    
    <li><strong>⚪ Pendiente (Por Investigar en Campo):</strong><br>
    Corresponde a predios adicionales donde la Sección 4 está completamente vacía y los técnicos deben realizar la visita de campo para tomar los datos agroeconómicos de primera mano.</li>
</ul>

<h2>3. Historial Comparativo de Trabajo Diario por Técnico (22, 23 y 24 de Julio)</h2>

<table>
    <thead>
        <tr>
            <th>Técnico Investigador</th>
            <th>Usuario QField</th>
            <th>Fichas Adic. (22-Jul)</th>
            <th>Fichas Adic. (23-Jul)</th>
            <th>Fichas Adic. (24-Jul)</th>
            <th>Total Adicionales Completadas</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><strong>Mayra Benavides</strong></td>
            <td><code>mayralisseth201</code></td>
            <td>65</td>
            <td>34</td>
            <td><strong>107</strong></td>
            <td><strong>206</strong></td>
        </tr>
        <tr>
            <td><strong>Adriana Cuascota</strong></td>
            <td><code>jvk-editor6</code></td>
            <td>—</td>
            <td><strong>116</strong></td>
            <td>—</td>
            <td><strong>116</strong></td>
        </tr>
        <tr>
            <td><strong>Martha Simbaña</strong></td>
            <td><code>jvk-editor4</code></td>
            <td>48</td>
            <td>66</td>
            <td><strong>38</strong></td>
            <td><strong>152</strong></td>
        </tr>
        <tr>
            <td><strong>Pablo Barrionuevo</strong></td>
            <td><code>jvk-editor5</code></td>
            <td>19</td>
            <td>24</td>
            <td><strong>26</strong></td>
            <td><strong>69</strong></td>
        </tr>
        <tr>
            <td><strong>JVK Corp</strong></td>
            <td><code>jvk-corp</code></td>
            <td>39</td>
            <td>18</td>
            <td><strong>16</strong></td>
            <td><strong>73</strong></td>
        </tr>
        <tr>
            <td><strong>Huguito Ipial</strong></td>
            <td><code>jvk-editor2</code></td>
            <td>—</td>
            <td>2</td>
            <td><strong>13</strong></td>
            <td><strong>15</strong></td>
        </tr>
        <tr>
            <td><strong>Melany Jara</strong></td>
            <td><code>jvk-editor</code></td>
            <td>7</td>
            <td>8</td>
            <td><strong>1</strong></td>
            <td><strong>16</strong></td>
        </tr>
        <tr>
            <td><strong>Dylan Chavez</strong></td>
            <td><code>jvk-editor3</code></td>
            <td>2</td>
            <td>5</td>
            <td>—</td>
            <td><strong>7</strong></td>
        </tr>
        <tr>
            <td><em>JVK Digitalización (Script)</em></td>
            <td><code>jvk-digitalizacion</code></td>
            <td>—</td>
            <td><em>103</em></td>
            <td>—</td>
            <td><em>103</em></td>
        </tr>
        <tr class="highlight-row">
            <td>TOTALES POR DÍA</td>
            <td>—</td>
            <td>180</td>
            <td>376</td>
            <td>201</td>
            <td>757</td>
        </tr>
    </tbody>
</table>

<h2>4. Estimación de Tiempos y Planificación de Cierre</h2>

<div class="note-box">
    <strong>Capacidad de Procesamiento por Modalidad:</strong><br>
    • <strong>Fichas Principales (investigación desde cero):</strong> 15 a 25 fichas/día por técnico.<br>
    • <strong>Fichas Adicionales (completar Sección 4):</strong> 35 a 116 fichas/día por técnico (al contar con las Secciones 1, 2, 3, 5 y 6 heredadas).
</div>

<h3>Proyección Real de Cierre de Trabajo de Campo:</h3>
<p>Descontando la inyección automatizada por script y considerando únicamente el ritmo real de campo de la fuerza de terreno (<strong>~218 predios adicionales completados por día de campo</strong>):</p>

<p style="text-align: center; font-size: 13pt; font-weight: bold; color: #0284c7;">
    Tiempo Real de Cierre Restante = 1,641 fichas pendientes / 218 fichas reales/día = 7.5 Días Laborables
</p>

<p><strong>Conclusión Operativa:</strong> Manteniendo el esquema y la asignación actual por polígonos/comunidades, el universo completo de 2,409 predios adicionales estará <strong>100% investigado y cerrado en aproximadamente 7 a 8 días de trabajo de campo</strong>.</p>

<div class="footer">
    Consorcio Cayambe SPT — Sistema de Riego Comunitario Guanguilquí Porotog<br>
    Documento autogenerado para control operativo de personal
</div>

</body>
</html>
"""

with open(HTML_PATH, 'w', encoding='utf-8') as f:
    f.write(html_content)
print(f"✓ Guardado HTML en: {HTML_PATH}")

# Convertir a DOCX usando MS Word COM
try:
    print("📄 Automatizando MS Word para generar el archivo DOCX...")
    word = win32com.client.Dispatch('Word.Application')
    word.Visible = False
    doc = word.Documents.Open(HTML_PATH)
    
    # Guardar en Escritorio
    doc.SaveAs2(DOCX_ESCRITORIO, FileFormat=16) # 16 = .docx
    print(f"✓ Archivo Word nativo generado en Escritorio: {DOCX_ESCRITORIO}")
    
    doc.Close()
    word.Quit()
    
    # Copiar a Descargas y Public
    shutil.copy2(DOCX_ESCRITORIO, DOCX_DESCARGAS)
    print(f"✓ Copiado a Descargas: {DOCX_DESCARGAS}")
    
    os.makedirs(os.path.dirname(DOCX_PUBLIC), exist_ok=True)
    shutil.copy2(DOCX_ESCRITORIO, DOCX_PUBLIC)
    print(f"✓ Copiado a padron-app/public: {DOCX_PUBLIC}")
    
    print("\n[OK] Generación de documento Word (.docx) completada con éxito.")
except Exception as e:
    print(f"⚠️ Error generando DOCX: {e}")
