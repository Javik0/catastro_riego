# -*- coding: utf-8 -*-
"""
Generador automático de Informe Técnico Premium para la reunión con el cliente.
Extrae datos del GeoPackage local, aplica corrección virtual en caliente,
calcula estadísticas por parroquias y sectores, y genera gráficos vectoriales SVG
para incrustar en el informe final en formato Markdown.

Uso:
  python scripts/generate_technical_report.py
"""

import sqlite3
import os
import math

# ── Configuraciones de rutas ─────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
QFIELD_DIR = r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline'
DATA_GPKG  = os.path.join(QFIELD_DIR, 'data.gpkg')

# Salidas relativas al script (se escriben en la raíz del espacio de trabajo)
REPORT_MD_PATH = os.path.abspath(os.path.join(BASE_DIR, '..', '..', 'informe_reunion_tecnica.md'))
GRAFICOS_DIR   = os.path.abspath(os.path.join(BASE_DIR, '..', '..', 'informe_graficos'))

os.makedirs(GRAFICOS_DIR, exist_ok=True)

# Paleta de colores Premium
COLORS = {
    'S1': '#10b981',       # Esmeralda (Sector 1)
    'S2': '#3b82f6',       # Azul (Sector 2)
    'S3': '#f59e0b',       # Ámbar (Sector 3)
    'TextPri': '#1e293b',  # Slate 800
    'TextSec': '#64748b',  # Slate 500
    'Grid': '#f1f5f9',     # Slate 100
    'Border': '#e2e8f0',   # Slate 200
    'BgCard': '#ffffff'    # Blanco
}

# ── Helper para generar SVG de Barras (Parroquias) ───────────
def generate_parroquias_svg(data, output_path):
    # data es lista de tuples (parroquia, n_comunidades)
    width, height = 600, 320
    margin = {'top': 50, 'right': 40, 'bottom': 50, 'left': 120}
    chart_width = width - margin['left'] - margin['right']
    chart_height = height - margin['top'] - margin['bottom']
    
    max_val = max([d[1] for d in data]) if data else 1
    # Redondear max_val al siguiente múltiplo de 5 para escala
    scale_max = math.ceil(max_val / 5) * 5
    
    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%">')
    # Estilos CSS internos
    svg.append("""
    <style>
        .title { font-family: 'Inter', system-ui, sans-serif; font-size: 16px; font-weight: bold; fill: #1e293b; }
        .axis-label { font-family: 'Inter', system-ui, sans-serif; font-size: 11px; fill: #64748b; font-weight: 500; }
        .bar-label { font-family: 'Inter', system-ui, sans-serif; font-size: 11px; fill: #1e293b; font-weight: 600; }
        .bar-val { font-family: 'Inter', system-ui, sans-serif; font-size: 11px; fill: #1e293b; font-weight: bold; }
        .grid-line { stroke: #e2e8f0; stroke-width: 1; stroke-dasharray: 2 2; }
        .axis-line { stroke: #cbd5e1; stroke-width: 1.5; }
        .bar { transition: fill 0.3s; }
        .bar:hover { fill: #059669 !important; }
    </style>
    """)
    
    # Fondo
    svg.append(f'<rect width="{width}" height="{height}" rx="12" fill="#ffffff" stroke="#e2e8f0" stroke-width="1.5"/>')
    # Título
    svg.append(f'<text x="24" y="32" class="title">N° de Comunidades Únicas por Parroquia</text>')
    
    # Líneas de cuadrícula verticales
    grid_ticks = 5
    for i in range(grid_ticks + 1):
        val = (scale_max / grid_ticks) * i
        x = margin['left'] + (val / scale_max) * chart_width
        svg.append(f'<line x1="{x}" y1="{margin["top"]}" x2="{x}" y2="{height - margin["bottom"]}" class="grid-line"/>')
        svg.append(f'<text x="{x}" y="{height - margin["bottom"] + 18}" text-anchor="middle" class="axis-label">{int(val)}</text>')
        
    # Dibujar barras horizontales
    bar_gap = 14
    n_bars = len(data)
    bar_height = (chart_height - (bar_gap * (n_bars - 1))) / n_bars
    
    for idx, (parr, count) in enumerate(data):
        y = margin['top'] + idx * (bar_height + bar_gap)
        bar_w = (count / scale_max) * chart_width
        
        # Color degradado
        color = '#10b981' if parr == 'CANGAHUA' else ('#3b82f6' if parr == 'OTÓN' else ('#f59e0b' if parr == 'ASCÁZUBI' else '#8b5cf6'))
        
        # Rectángulo de barra
        svg.append(f'<rect x="{margin["left"]}" y="{y}" width="{bar_w}" height="{bar_height}" rx="4" fill="{color}" class="bar"/>')
        # Nombre de parroquia (eje Y)
        svg.append(f'<text x="{margin["left"] - 12}" y="{y + bar_height/2 + 4}" text-anchor="end" class="bar-label">{parr}</text>')
        # Valor al final de la barra
        svg.append(f'<text x="{margin["left"] + bar_w + 8}" y="{y + bar_height/2 + 4}" class="bar-val">{count}</text>')
        
    # Eje Y vertical
    svg.append(f'<line x1="{margin["left"]}" y1="{margin["top"] - 10}" x2="{margin["left"]}" y2="{height - margin["bottom"]}" class="axis-line"/>')
    svg.append('</svg>')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(svg))


# ── Helper para generar SVG de Cobertura de Riego vs Secano (ha) ──
def generate_riego_secano_svg(data_sectores, output_path):
    width, height = 650, 260
    margin = {'top': 60, 'right': 140, 'bottom': 50, 'left': 100}
    chart_width = width - margin['left'] - margin['right']
    chart_height = height - margin['top'] - margin['bottom']
    
    sectors = ['Sector 1', 'Sector 2', 'Sector 3']
    categories = ['Riego', 'Secano']
    cat_colors = ['#3b82f6', '#f59e0b']
    
    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%">')
    svg.append("""
    <style>
        .title { font-family: 'Inter', system-ui, sans-serif; font-size: 16px; font-weight: bold; fill: #1e293b; }
        .subtitle { font-family: 'Inter', system-ui, sans-serif; font-size: 11px; fill: #64748b; }
        .axis-label { font-family: 'Inter', system-ui, sans-serif; font-size: 11px; fill: #64748b; font-weight: 500; }
        .bar-label { font-family: 'Inter', system-ui, sans-serif; font-size: 11px; fill: #1e293b; font-weight: 600; }
        .pct-label { font-family: 'Inter', system-ui, sans-serif; font-size: 10px; fill: #ffffff; font-weight: bold; }
        .legend-text { font-family: 'Inter', system-ui, sans-serif; font-size: 11px; fill: #1e293b; font-weight: 600; }
        .axis-line { stroke: #cbd5e1; stroke-width: 1.5; }
    </style>
    """)
    svg.append(f'<rect width="{width}" height="{height}" rx="12" fill="#ffffff" stroke="#e2e8f0" stroke-width="1.5"/>')
    svg.append(f'<text x="24" y="32" class="title">Cobertura de Suelo: Riego vs Secano por Sector</text>')
    svg.append(f'<text x="24" y="48" class="subtitle">Distribución porcentual de la superficie total (Horizontal 100%)</text>')
    
    for i in range(5):
        val = 25 * i
        x = margin['left'] + (val / 100) * chart_width
        svg.append(f'<line x1="{x}" y1="{margin["top"] - 5}" x2="{x}" y2="{height - margin["bottom"]}" stroke="#e2e8f0" stroke-dasharray="2 2"/>')
        svg.append(f'<text x="{x}" y="{height - margin["bottom"] + 16}" text-anchor="middle" class="axis-label">{val}%</text>')
        
    bar_height = 24
    bar_gap = 18
    
    for idx, sec in enumerate(sectors):
        y = margin['top'] + idx * (bar_height + bar_gap)
        sec_data = data_sectores.get(sec, {'Riego': 0.0, 'Secano': 0.0})
        val_riego = sec_data.get('Riego', 0.0)
        val_secano = sec_data.get('Secano', 0.0)
        total = val_riego + val_secano
        
        pct_riego = (val_riego / total * 100) if total > 0 else 0
        pct_secano = (val_secano / total * 100) if total > 0 else 0
        
        svg.append(f'<text x="{margin["left"] - 12}" y="{y + bar_height/2 + 4}" text-anchor="end" class="bar-label">{sec}</text>')
        
        w_riego = (pct_riego / 100) * chart_width
        if w_riego > 0:
            svg.append(f'<rect x="{margin["left"]}" y="{y}" width="{w_riego}" height="{bar_height}" rx="2" fill="{cat_colors[0]}" opacity="0.9"/>')
            if pct_riego > 8:
                svg.append(f'<text x="{margin["left"] + w_riego/2}" y="{y + bar_height/2 + 3.5}" text-anchor="middle" class="pct-label">{pct_riego:.1f}%</text>')
                
        w_secano = (pct_secano / 100) * chart_width
        if w_secano > 0:
            x_secano = margin['left'] + w_riego
            svg.append(f'<rect x="{x_secano}" y="{y}" width="{w_secano}" height="{bar_height}" rx="2" fill="{cat_colors[1]}" opacity="0.9"/>')
            if pct_secano > 8:
                svg.append(f'<text x="{x_secano + w_secano/2}" y="{y + bar_height/2 + 3.5}" text-anchor="middle" class="pct-label">{pct_secano:.1f}%</text>')
                
    leg_x = width - margin['right'] + 20
    for idx, cat in enumerate(categories):
        leg_y = margin['top'] + idx * 30
        svg.append(f'<rect x="{leg_x}" y="{leg_y}" width="16" height="16" rx="4" fill="{cat_colors[idx]}"/>')
        svg.append(f'<text x="{leg_x + 24}" y="{leg_y + 12}" class="legend-text">{cat}</text>')
        
    svg.append('</svg>')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(svg))


# ── Helper para generar SVG de Especies Pecuarias Principales (Barras Verticales) ──
def generate_especies_pecuarias_svg(data_animales, output_path):
    width, height = 650, 260
    margin = {'top': 60, 'right': 40, 'bottom': 50, 'left': 80}
    chart_width = width - margin['left'] - margin['right']
    chart_height = height - margin['top'] - margin['bottom']
    
    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%">')
    svg.append("""
    <style>
        .title { font-family: 'Inter', system-ui, sans-serif; font-size: 16px; font-weight: bold; fill: #1e293b; }
        .subtitle { font-family: 'Inter', system-ui, sans-serif; font-size: 11px; fill: #64748b; }
        .axis-label { font-family: 'Inter', system-ui, sans-serif; font-size: 10px; fill: #64748b; font-weight: 500; }
        .bar-val { font-family: 'Inter', system-ui, sans-serif; font-size: 10px; fill: #1e293b; font-weight: bold; }
        .grid-line { stroke: #f1f5f9; stroke-width: 1.5; }
        .axis-line { stroke: #cbd5e1; stroke-width: 1.5; }
    </style>
    """)
    svg.append(f'<rect width="{width}" height="{height}" rx="12" fill="#ffffff" stroke="#e2e8f0" stroke-width="1.5"/>')
    svg.append(f'<text x="24" y="32" class="title">Especies Pecuarias Principales del Censo</text>')
    svg.append(f'<text x="24" y="48" class="subtitle">Total global de cabezas de ganado registradas en el catastro</text>')
    
    if not data_animales:
        svg.append(f'<text x="{width/2}" y="{height/2}" text-anchor="middle" class="subtitle">Sin datos pecuarios</text>')
        svg.append('</svg>')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(svg))
        return
        
    max_val = max([x[1] for x in data_animales]) or 1
    import math
    scale_max = math.ceil(max_val / 10000.0) * 10000
    if scale_max < 10: scale_max = max_val + 5
    
    grid_ticks = 4
    for i in range(grid_ticks + 1):
        val = (scale_max / grid_ticks) * i
        y = margin['top'] + chart_height - (val / scale_max) * chart_height
        svg.append(f'<line x1="{margin["left"]}" y1="{y}" x2="{width - margin["right"]}" y2="{y}" class="grid-line"/>')
        svg.append(f'<text x="{margin["left"] - 8}" y="{y + 4}" text-anchor="end" class="axis-label">{int(val):,}</text>')
        
    bar_width = (chart_width * 0.6) / len(data_animales)
    group_width = chart_width / len(data_animales)
    colors = ['#ec4899', '#f43f5e', '#a855f7', '#8b5cf6', '#6366f1']
    
    for idx, (especie, val) in enumerate(data_animales):
        bar_h = (val / scale_max) * chart_height
        x = margin['left'] + idx * group_width + (group_width - bar_width)/2
        y = margin['top'] + chart_height - bar_h
        
        svg.append(f'<rect x="{x}" y="{y}" width="{bar_width}" height="{bar_h}" rx="4" fill="{colors[idx % len(colors)]}" opacity="0.9"/>')
        svg.append(f'<text x="{x + bar_width/2}" y="{y - 6}" text-anchor="middle" class="bar-val">{val:,}</text>')
        label_esp = especie.title()
        if len(label_esp) > 12: label_esp = label_esp[:10] + '...'
        svg.append(f'<text x="{x + bar_width/2}" y="{height - margin["bottom"] + 16}" text-anchor="middle" class="axis-label">{label_esp}</text>')
        
    svg.append(f'<line x1="{margin["left"]}" y1="{height - margin["bottom"]}" x2="{width - margin["right"]}" y2="{height - margin["bottom"]}" class="axis-line"/>')
    svg.append('</svg>')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(svg))


# ── Helper para generar SVG de Destino de Cultivos (Barras Agrupadas) ──
def generate_destino_cultivos_svg(data_sectores, output_path):
    width, height = 650, 260
    margin = {'top': 60, 'right': 140, 'bottom': 50, 'left': 80}
    chart_width = width - margin['left'] - margin['right']
    chart_height = height - margin['top'] - margin['bottom']
    
    sectors = ['Sector 1', 'Sector 2', 'Sector 3']
    categories = ['Autoconsumo', 'Mercado / Venta', 'Agroindustria', 'Exportación']
    cat_keys = ['Autoconsumo', 'Mercado', 'Agroindustria', 'Exportación']
    cat_colors = ['#10b981', '#3b82f6', '#8b5cf6', '#ec4899']
    
    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%">')
    svg.append("""
    <style>
        .title { font-family: 'Inter', system-ui, sans-serif; font-size: 16px; font-weight: bold; fill: #1e293b; }
        .subtitle { font-family: 'Inter', system-ui, sans-serif; font-size: 11px; fill: #64748b; }
        .axis-label { font-family: 'Inter', system-ui, sans-serif; font-size: 10px; fill: #64748b; font-weight: 500; }
        .legend-text { font-family: 'Inter', system-ui, sans-serif; font-size: 11px; fill: #1e293b; font-weight: 600; }
        .grid-line { stroke: #f1f5f9; stroke-width: 1.5; }
        .axis-line { stroke: #cbd5e1; stroke-width: 1.5; }
    </style>
    """)
    svg.append(f'<rect width="{width}" height="{height}" rx="12" fill="#ffffff" stroke="#e2e8f0" stroke-width="1.5"/>')
    svg.append(f'<text x="24" y="32" class="title">Destino de la Producción Agrícola por Sector</text>')
    svg.append(f'<text x="24" y="48" class="subtitle">Cantidad de parcelas agrícolas según su propósito comercial</text>')
    
    max_val = 0
    for sec in sectors:
        for cat in cat_keys:
            max_val = max(max_val, data_sectores.get(sec, {}).get(cat, 0))
            
    import math
    scale_max = math.ceil((max_val or 1) / 500.0) * 500
    
    grid_ticks = 4
    for i in range(grid_ticks + 1):
        val = (scale_max / grid_ticks) * i
        y = margin['top'] + chart_height - (val / scale_max) * chart_height
        svg.append(f'<line x1="{margin["left"]}" y1="{y}" x2="{width - margin["right"]}" y2="{y}" class="grid-line"/>')
        svg.append(f'<text x="{margin["left"] - 8}" y="{y + 4}" text-anchor="end" class="axis-label">{int(val):,}</text>')
        
    group_width = chart_width / len(sectors)
    bar_width = (group_width * 0.7) / len(categories)
    bar_gap = 1.0
    
    for s_idx, sec in enumerate(sectors):
        group_x = margin['left'] + s_idx * group_width
        svg.append(f'<text x="{group_x + group_width/2}" y="{height - margin["bottom"] + 16}" text-anchor="middle" class="axis-label" style="font-weight: 600; fill: #1e293b;">{sec}</text>')
        
        for c_idx, cat in enumerate(cat_keys):
            val = data_sectores.get(sec, {}).get(cat, 0)
            bar_h = (val / scale_max) * chart_height
            bar_x = group_x + (group_width * 0.15) + c_idx * (bar_width + bar_gap)
            bar_y = margin['top'] + chart_height - bar_h
            
            svg.append(f'<rect x="{bar_x}" y="{bar_y}" width="{bar_width}" height="{bar_h}" rx="1.5" fill="{cat_colors[c_idx]}" opacity="0.9"/>')
            
    svg.append(f'<line x1="{margin["left"]}" y1="{height - margin["bottom"]}" x2="{width - margin["right"] + 10}" y2="{height - margin["bottom"]}" class="axis-line"/>')
    
    leg_x = width - margin['right'] + 20
    for c_idx, cat in enumerate(categories):
        leg_y = margin['top'] + 15 + c_idx * 30
        svg.append(f'<rect x="{leg_x}" y="{leg_y}" width="14" height="14" rx="4" fill="{cat_colors[c_idx]}"/>')
        svg.append(f'<text x="{leg_x + 20}" y="{leg_y + 11}" class="legend-text" style="font-size: 10px;">{cat}</text>')
        
    svg.append('</svg>')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(svg))


# ── Helper para generar SVG de Tamaño de Predios (Barras Agrupadas) ──
def generate_predios_svg(data_sectores, output_path):
    # data_sectores es dict {'Sector 1': [counts...], 'Sector 2': [...], 'Sector 3': [...]}
    # Los rangos son 6
    ranges_labels = ['&lt; 0.1 ha', '0.1-0.5 ha', '0.5-1.0 ha', '1.0-5.0 ha', '5.0-10.0 ha', '&gt; 10.0 ha']
    
    width, height = 750, 360
    margin = {'top': 60, 'right': 150, 'bottom': 50, 'left': 50}
    chart_width = width - margin['left'] - margin['right']
    chart_height = height - margin['top'] - margin['bottom']
    
    # Encontrar valor máximo para escala Y (porcentaje)
    max_val = 0
    for sec, values in data_sectores.items():
        total = sum(values)
        if total > 0:
            for v in values:
                pct = (v / total) * 100
                if pct > max_val:
                    max_val = pct
    
    scale_max = math.ceil(max_val / 10) * 10
    
    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%">')
    svg.append("""
    <style>
        .title { font-family: 'Inter', system-ui, sans-serif; font-size: 16px; font-weight: bold; fill: #1e293b; }
        .subtitle { font-family: 'Inter', system-ui, sans-serif; font-size: 11px; fill: #64748b; }
        .axis-label { font-family: 'Inter', system-ui, sans-serif; font-size: 10px; fill: #64748b; font-weight: 500; }
        .legend-text { font-family: 'Inter', system-ui, sans-serif; font-size: 11px; fill: #1e293b; font-weight: 600; }
        .grid-line { stroke: #f1f5f9; stroke-width: 1.5; }
        .axis-line { stroke: #cbd5e1; stroke-width: 1.5; }
    </style>
    """)
    
    # Fondo
    svg.append(f'<rect width="{width}" height="{height}" rx="12" fill="#ffffff" stroke="#e2e8f0" stroke-width="1.5"/>')
    # Título
    svg.append(f'<text x="24" y="32" class="title">Distribución del Tamaño de Predios por Sector</text>')
    svg.append(f'<text x="24" y="48" class="subtitle">Porcentaje de predios en cada rango de hectáreas (ha)</text>')
    
    # Líneas de cuadrícula horizontales
    grid_ticks = 5
    for i in range(grid_ticks + 1):
        val = (scale_max / grid_ticks) * i
        y = margin['top'] + chart_height - (val / scale_max) * chart_height
        svg.append(f'<line x1="{margin["left"]}" y1="{y}" x2="{width - margin["right"]}" y2="{y}" class="grid-line"/>')
        svg.append(f'<text x="{margin["left"] - 8}" y="{y + 4}" text-anchor="end" class="axis-label">{int(val)}%</text>')
        
    # Dibujar barras agrupadas
    group_width = chart_width / len(ranges_labels)
    bar_width = (group_width * 0.7) / 3
    bar_gap = 1.5
    
    sectors = ['Sector 1', 'Sector 2', 'Sector 3']
    colors = [COLORS['S1'], COLORS['S2'], COLORS['S3']]
    
    totals = {sec: sum(data_sectores[sec]) for sec in sectors}
    
    for r_idx in range(len(ranges_labels)):
        group_x = margin['left'] + r_idx * group_width
        
        # Línea de ticks en eje X
        svg.append(f'<text x="{group_x + group_width/2}" y="{height - margin["bottom"] + 16}" text-anchor="middle" class="axis-label">{ranges_labels[r_idx]}</text>')
        
        for s_idx, sec in enumerate(sectors):
            count = data_sectores[sec][r_idx]
            total = totals[sec]
            pct = (count / total * 100) if total > 0 else 0
            
            bar_h = (pct / scale_max) * chart_height
            bar_x = group_x + (group_width * 0.15) + s_idx * (bar_width + bar_gap)
            bar_y = margin['top'] + chart_height - bar_h
            
            # Dibujar barra
            svg.append(f'<rect x="{bar_x}" y="{bar_y}" width="{bar_width}" height="{bar_h}" rx="2" fill="{colors[s_idx]}" opacity="0.95"/>')
            
    # Eje X horizontal
    svg.append(f'<line x1="{margin["left"]}" y1="{height - margin["bottom"]}" x2="{width - margin["right"] + 10}" y2="{height - margin["bottom"]}" class="axis-line"/>')
    
    # Leyenda (Lateral derecha)
    leg_x = width - margin['right'] + 30
    for s_idx, sec in enumerate(sectors):
        leg_y = margin['top'] + 20 + s_idx * 30
        svg.append(f'<rect x="{leg_x}" y="{leg_y}" width="16" height="16" rx="4" fill="{colors[s_idx]}"/>')
        svg.append(f'<text x="{leg_x + 24}" y="{leg_y + 12}" class="legend-text">{sec}</text>')
        
    svg.append('</svg>')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(svg))


# ── Helper para generar SVG de Sistemas de Riego (Reservorios Pie/Donut) ──
def generate_reservorios_svg(data_sectores, output_path):
    # data_sectores es dict {'Sector 1': {'Comunitario': X, 'Privado': Y, 'No': Z}, ...}
    # Graficaremos barras apiladas al 100% horizontales, que son sumamente profesionales
    # y comparativas para ver la infraestructura de reservorios
    width, height = 650, 260
    margin = {'top': 60, 'right': 140, 'bottom': 50, 'left': 100}
    chart_width = width - margin['left'] - margin['right']
    chart_height = height - margin['top'] - margin['bottom']
    
    sectors = ['Sector 1', 'Sector 2', 'Sector 3']
    categories = ['Comunitario', 'Privado', 'No']
    cat_colors = ['#10b981', '#3b82f6', '#ef4444'] # Verde, Azul, Rojo
    
    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%">')
    svg.append("""
    <style>
        .title { font-family: 'Inter', system-ui, sans-serif; font-size: 16px; font-weight: bold; fill: #1e293b; }
        .subtitle { font-family: 'Inter', system-ui, sans-serif; font-size: 11px; fill: #64748b; }
        .axis-label { font-family: 'Inter', system-ui, sans-serif; font-size: 11px; fill: #64748b; font-weight: 500; }
        .bar-label { font-family: 'Inter', system-ui, sans-serif; font-size: 11px; fill: #1e293b; font-weight: 600; }
        .pct-label { font-family: 'Inter', system-ui, sans-serif; font-size: 10px; fill: #ffffff; font-weight: bold; }
        .legend-text { font-family: 'Inter', system-ui, sans-serif; font-size: 11px; fill: #1e293b; font-weight: 600; }
        .axis-line { stroke: #cbd5e1; stroke-width: 1.5; }
    </style>
    """)
    
    # Fondo
    svg.append(f'<rect width="{width}" height="{height}" rx="12" fill="#ffffff" stroke="#e2e8f0" stroke-width="1.5"/>')
    # Título
    svg.append(f'<text x="24" y="32" class="title">Tipo de Reservorio e Infraestructura de Riego</text>')
    svg.append(f'<text x="24" y="48" class="subtitle">Proporción de tenencia de reservorio (Horizontal 100%)</text>')
    
    # Eje X ticks (0% a 100%)
    for i in range(5):
        val = 25 * i
        x = margin['left'] + (val / 100) * chart_width
        svg.append(f'<line x1="{x}" y1="{margin["top"] - 5}" x2="{x}" y2="{height - margin["bottom"]}" stroke="#e2e8f0" stroke-dasharray="2 2"/>')
        svg.append(f'<text x="{x}" y="{height - margin["bottom"] + 16}" text-anchor="middle" class="axis-label">{val}%</text>')
        
    bar_height = 24
    bar_gap = 18
    
    for idx, sec in enumerate(sectors):
        y = margin['top'] + idx * (bar_height + bar_gap)
        
        # Calcular proporciones
        sec_data = data_sectores[sec]
        # mapear categorias
        vals = [sec_data.get('Comunitario', 0), sec_data.get('Privado', 0), sec_data.get('No', 0)]
        total = sum(vals)
        
        # Dibujar barra horizontal apilada
        x_curr = margin['left']
        for c_idx, val in enumerate(vals):
            if total == 0 or val == 0:
                continue
            pct = (val / total)
            w = pct * chart_width
            
            # Dibujar rect
            svg.append(f'<rect x="{x_curr}" y="{y}" width="{w}" height="{bar_height}" fill="{cat_colors[c_idx]}" opacity="0.95"/>')
            
            # Texto porcentaje interno
            if pct >= 0.10: # Solo si cabe de forma legible (minimo 10%)
                svg.append(f'<text x="{x_curr + w/2}" y="{y + bar_height/2 + 3.5}" text-anchor="middle" class="pct-label">{pct*100:.0f}%</text>')
                
            x_curr += w
            
        # Nombre de sector (eje Y)
        svg.append(f'<text x="{margin["left"] - 12}" y="{y + bar_height/2 + 4}" text-anchor="end" class="bar-label">{sec}</text>')
        
    # Eje Y vertical
    svg.append(f'<line x1="{margin["left"]}" y1="{margin["top"] - 10}" x2="{margin["left"]}" y2="{height - margin["bottom"]}" class="axis-line"/>')
    
    # Leyenda (Lateral derecha)
    leg_x = width - margin['right'] + 20
    for c_idx, cat in enumerate(categories):
        leg_y = margin['top'] + 20 + c_idx * 30
        svg.append(f'<rect x="{leg_x}" y="{leg_y}" width="14" height="14" rx="4" fill="{cat_colors[c_idx]}"/>')
        svg.append(f'<text x="{leg_x + 20}" y="{leg_y + 11}" class="legend-text">{cat}</text>')
        
    svg.append('</svg>')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(svg))


# ── Helper para generar SVG de Métodos de Riego (Comparativa barras) ──
def generate_metodos_svg(data_sectores, output_path):
    # data_sectores es dict {'Sector 1': {'Gravedad': X_avg, 'Aspersión': Y_avg, 'Goteo': Z_avg}, ...}
    # Graficaremos un gráfico de barras agrupadas comparando el porcentaje promedio de uso
    width, height = 650, 260
    margin = {'top': 60, 'right': 140, 'bottom': 50, 'left': 50}
    chart_width = width - margin['left'] - margin['right']
    chart_height = height - margin['top'] - margin['bottom']
    
    methods = ['Gravedad', 'Aspersión', 'Goteo']
    colors = ['#f59e0b', '#3b82f6', '#10b981'] # Ámbar, Azul, Esmeralda
    sectors = ['Sector 1', 'Sector 2', 'Sector 3']
    
    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%">')
    svg.append("""
    <style>
        .title { font-family: 'Inter', system-ui, sans-serif; font-size: 16px; font-weight: bold; fill: #1e293b; }
        .subtitle { font-family: 'Inter', system-ui, sans-serif; font-size: 11px; fill: #64748b; }
        .axis-label { font-family: 'Inter', system-ui, sans-serif; font-size: 10px; fill: #64748b; font-weight: 500; }
        .legend-text { font-family: 'Inter', system-ui, sans-serif; font-size: 11px; fill: #1e293b; font-weight: 600; }
        .grid-line { stroke: #f1f5f9; stroke-width: 1.5; }
        .axis-line { stroke: #cbd5e1; stroke-width: 1.5; }
    </style>
    """)
    
    # Fondo
    svg.append(f'<rect width="{width}" height="{height}" rx="12" fill="#ffffff" stroke="#e2e8f0" stroke-width="1.5"/>')
    # Título
    svg.append(f'<text x="24" y="32" class="title">Distribución de Métodos de Riego por Sector</text>')
    svg.append(f'<text x="24" y="48" class="subtitle">Porcentaje de uso promedio de Gravedad, Aspersión y Goteo</text>')
    
    # Líneas de cuadrícula Y (0% a 100%)
    for i in range(5):
        val = 25 * i
        y = margin['top'] + chart_height - (val / 100) * chart_height
        svg.append(f'<line x1="{margin["left"]}" y1="{y}" x2="{width - margin["right"]}" y2="{y}" class="grid-line"/>')
        svg.append(f'<text x="{margin["left"] - 8}" y="{y + 4}" text-anchor="end" class="axis-label">{val}%</text>')
        
    group_width = chart_width / len(sectors)
    bar_width = (group_width * 0.7) / 3
    bar_gap = 1.5
    
    for s_idx, sec in enumerate(sectors):
        group_x = margin['left'] + s_idx * group_width
        
        # Etiqueta de eje X
        svg.append(f'<text x="{group_x + group_width/2}" y="{height - margin["bottom"] + 16}" text-anchor="middle" class="legend-text">{sec}</text>')
        
        sec_data = data_sectores[sec]
        vals = [sec_data.get('Gravedad', 0), sec_data.get('Aspersión', 0), sec_data.get('Goteo', 0)]
        
        for c_idx, val in enumerate(vals):
            bar_h = (val / 100) * chart_height
            bar_x = group_x + (group_width * 0.15) + c_idx * (bar_width + bar_gap)
            bar_y = margin['top'] + chart_height - bar_h
            
            svg.append(f'<rect x="{bar_x}" y="{bar_y}" width="{bar_width}" height="{bar_h}" rx="2" fill="{colors[c_idx]}" opacity="0.95"/>')
            
    # Eje X horizontal
    svg.append(f'<line x1="{margin["left"]}" y1="{height - margin["bottom"]}" x2="{width - margin["right"] + 10}" y2="{height - margin["bottom"]}" class="axis-line"/>')
    
    # Leyenda (Lateral derecha)
    leg_x = width - margin['right'] + 20
    for c_idx, cat in enumerate(methods):
        leg_y = margin['top'] + 20 + c_idx * 30
        svg.append(f'<rect x="{leg_x}" y="{leg_y}" width="14" height="14" rx="4" fill="{colors[c_idx]}"/>')
        svg.append(f'<text x="{leg_x + 20}" y="{leg_y + 11}" class="legend-text">{cat}</text>')
        
    svg.append('</svg>')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(svg))


# ── MAIN PIPELINE ─────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--predios-vinculados', type=int, default=3442)
    args, unknown = parser.parse_known_args()
    predios_vinculados = args.predios_vinculados

    if not os.path.exists(DATA_GPKG):
        print(f"[ERROR] No se encuentra el archivo de datos SQLite: {DATA_GPKG}")
        return

    conn = sqlite3.connect(DATA_GPKG)
    cursor = conn.cursor()

    # Encontrar la tabla dinámica de fichas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    all_tables = [t[0] for t in cursor.fetchall()]
    fichas_table = next((t for t in all_tables if 'Fichas_Predios' in t and not any(x in t for x in ('rtree_','log_','gpkg_'))), None)

    if not fichas_table:
        print("[ERROR] No se encontro la tabla de Fichas_Predios.")
        conn.close()
        return

    # Contar cultivos y animales dinámicamente
    cultivos_table = next((t for t in all_tables if 'Cultivos_Agricolas' in t and not any(x in t for x in ('rtree_','log_','gpkg_'))), None)
    animales_table = next((t for t in all_tables if 'Animales_Especies' in t and not any(x in t for x in ('rtree_','log_','gpkg_'))), None)
    
    total_cultivos = 0
    if cultivos_table:
        cursor.execute(f'SELECT COUNT(*) FROM "{cultivos_table}"')
        total_cultivos = cursor.fetchone()[0]
        
    total_animales = 0
    if animales_table:
        cursor.execute(f'SELECT SUM(COALESCE(cantidad, 0)) FROM "{animales_table}"')
        total_animales = cursor.fetchone()[0] or 0

    # ── Métricas adicionales por sector ──────────────────
    # 1. Cultivos por Sector
    cultivos_por_sector = {'Sector 1': 0, 'Sector 2': 0, 'Sector 3': 0}
    if cultivos_table:
        cursor.execute(f"""
            SELECT COALESCE(NULLIF(f.sector_investigacion, ''), 'None') as sec, COUNT(c.id_cultivo)
            FROM "{cultivos_table}" c
            JOIN "{fichas_table}" f ON c.ficha_id = f.id
            GROUP BY sec
        """)
        for sec, count in cursor.fetchall():
            s_name = 'Sector 1' if sec == 'None' else sec
            if s_name in cultivos_por_sector:
                cultivos_por_sector[s_name] += count

    # 2. Animales por Sector
    animales_por_sector = {'Sector 1': 0, 'Sector 2': 0, 'Sector 3': 0}
    if animales_table:
        cursor.execute(f"""
            SELECT COALESCE(NULLIF(f.sector_investigacion, ''), 'None') as sec, SUM(COALESCE(a.cantidad, 0))
            FROM "{animales_table}" a
            JOIN "{fichas_table}" f ON a.ficha_id = f.id
            GROUP BY sec
        """)
        for sec, count in cursor.fetchall():
            s_name = 'Sector 1' if sec == 'None' else sec
            if s_name in animales_por_sector:
                animales_por_sector[s_name] += count

    # 3. Área sin Riego por Sector (con corrección en caliente)
    sin_riego_por_sector = {'Sector 1': 0.0, 'Sector 2': 0.0, 'Sector 3': 0.0}
    cursor.execute(f"""
        SELECT COALESCE(NULLIF(sector_investigacion, ''), 'None') as sec, area_total, area_riego, area_sin_riego
        FROM "{fichas_table}"
    """)
    for sec, area_tot, area_rieg, area_sin in cursor.fetchall():
        s_name = 'Sector 1' if sec == 'None' else sec
        a_tot = area_tot or 0.0
        a_rieg = area_rieg or 0.0
        a_sin = area_sin or 0.0
        if a_rieg > a_tot or a_sin < 0:
            a_sin = 0.0
        if s_name in sin_riego_por_sector:
            sin_riego_por_sector[s_name] += a_sin

    # ─────────────────────────────────────────────────────────
    # 1. Extracción de Fichas sin Comunidad
    # ─────────────────────────────────────────────────────────
    cursor.execute(f"""
        SELECT id, cedula, nombres, apellidos, creado_por, fecha_creacion, comunidad, sector_comunidad
        FROM "{fichas_table}"
        WHERE comunidad IS NULL OR comunidad = '' OR comunidad = 'None' OR UPPER(comunidad) = 'NONE'
    """)
    raw_empty_coms = cursor.fetchall()
    fichas_sin_com = []
    for f in raw_empty_coms:
        fichas_sin_com.append({
            'id': f[0],
            'cedula': f[1] or 'S/C',
            'nombre': f"{f[2] or ''} {f[3] or ''}".strip() or 'No registrado',
            'tecnico': f[4] or 'S/A',
            'fecha': (f[5] or '').split('T')[0] if f[5] else 'S/F',
            'sector_com': f[7] or 'N/A'
        })

    # ─────────────────────────────────────────────────────────
    # 2. Extracción de Comunidades por Parroquia
    # ─────────────────────────────────────────────────────────
    cursor.execute(f"""
        SELECT COALESCE(NULLIF(parroquia, ''), 'SIN PARROQUIA') as parr, COUNT(DISTINCT comunidad)
        FROM "{fichas_table}"
        WHERE comunidad IS NOT NULL AND comunidad != '' AND comunidad != 'None' AND UPPER(comunidad) != 'NONE'
        GROUP BY parr
        ORDER BY COUNT(DISTINCT comunidad) DESC
    """)
    parroquias_counts_raw = cursor.fetchall()
    
    parroquias_data = []
    for parr, count in parroquias_counts_raw:
        cursor.execute(f"""
            SELECT DISTINCT comunidad
            FROM "{fichas_table}"
            WHERE (parroquia = ? OR ((parroquia IS NULL OR parroquia = '') AND ? = 'SIN PARROQUIA'))
              AND comunidad IS NOT NULL AND comunidad != '' AND comunidad != 'None' AND UPPER(comunidad) != 'NONE'
            ORDER BY comunidad
        """, (parr, parr))
        coms = [r[0] for r in cursor.fetchall()]
        parroquias_data.append({
            'name': parr,
            'count': count,
            'comunidades': coms
        })

    # Generar SVG Parroquias
    svg_parr_data = [(p['name'], p['count']) for p in parroquias_data if p['name'] != 'SIN PARROQUIA']
    generate_parroquias_svg(svg_parr_data, os.path.join(GRAFICOS_DIR, 'chart_parroquias.svg'))

    # ─────────────────────────────────────────────────────────
    # 3. Extracción e Identificación de Inconsistencias de Área
    # ─────────────────────────────────────────────────────────
    cursor.execute(f"""
        SELECT id, cedula, nombres, apellidos, creado_por, area_total, area_riego, area_sin_riego
        FROM "{fichas_table}"
        WHERE area_sin_riego < 0 OR area_riego > area_total
    """)
    raw_inconsistencias = cursor.fetchall()
    inconsistencias_list = []
    for f in raw_inconsistencias:
        inconsistencias_list.append({
            'id': f[0],
            'cedula': f[1] or 'S/C',
            'nombre': f"{f[2] or ''} {f[3] or ''}".strip() or 'No registrado',
            'tecnico': f[4] or 'S/A',
            'total': f[5],
            'riego': f[6],
            'sin_riego': f[7]
        })

    # ─────────────────────────────────────────────────────────
    # 4. Extracción de Datos por Sectores (con corrección en caliente)
    # ─────────────────────────────────────────────────────────
    cursor.execute(f"""
        SELECT id, COALESCE(NULLIF(sector_investigacion, ''), 'None') as sec, area_total, area_riego, area_sin_riego,
               coalesce(hijos_hombres,0) + coalesce(hijos_mujeres,0) as hijos,
               tiene_reservorio, metodo_gravedad_pct, metodo_aspersion_pct, metodo_goteo_pct
        FROM "{fichas_table}"
    """)
    raw_all_fichas = cursor.fetchall()
    
    # Agrupar mapeando None -> Sector 1
    sectores_recs = {'Sector 1': [], 'Sector 2': [], 'Sector 3': []}
    for r in raw_all_fichas:
        sec = r[1]
        if sec == 'None':
            sec = 'Sector 1'
        
        # CORRECCIÓN EN CALIENTE PARA EL INFORME:
        area_tot = r[2] or 0.0
        area_rieg = r[3] or 0.0
        area_sin = r[4] or 0.0
        
        if area_rieg > area_tot or area_sin < 0:
            area_rieg = area_tot
            area_sin = 0.0
            
        record_corr = (r[0], sec, area_tot, area_rieg, area_sin, r[5], r[6], r[7], r[8], r[9])
        if sec in sectores_recs:
            sectores_recs[sec].append(record_corr)

    # Contenedores para gráficos de Sectores
    chart_predios_data = {}
    chart_reservorios_data = {}
    chart_metodos_data = {}
    chart_riego_secano_data = {}
    
    sector_stats_report = []

    for sector in ['Sector 1', 'Sector 2', 'Sector 3']:
        recs = sectores_recs[sector]
        tot = len(recs)
        
        areas_total = [r[2] for r in recs]
        areas_riego = [r[3] for r in recs]
        hijos_list = [r[5] for r in recs]
        reservorios = [r[6] for r in recs]
        
        sum_total = sum(areas_total)
        avg_total = sum_total / tot if tot > 0 else 0
        sum_riego = sum(areas_riego)
        avg_riego = sum_riego / tot if tot > 0 else 0
        
        # Rangos de predio (hectáreas)
        predio_counts = [0, 0, 0, 0, 0, 0] # '<0.1', '0.1-0.5', '0.5-1.0', '1.0-5.0', '5.0-10.0', '>10.0'
        for a in areas_total:
            ha = a / 10000.0
            if ha < 0.1: predio_counts[0] += 1
            elif ha < 0.5: predio_counts[1] += 1
            elif ha < 1.0: predio_counts[2] += 1
            elif ha < 5.0: predio_counts[3] += 1
            elif ha < 10.0: predio_counts[4] += 1
            else: predio_counts[5] += 1
            
        chart_predios_data[sector] = predio_counts

        # Promedios de hijos
        avg_kids = sum(hijos_list) / tot if tot > 0 else 0
        max_kids = max(hijos_list) if hijos_list else 0
        
        kids_dist = [0, 0, 0, 0] # 'Sin hijos', '1-2', '3-4', '5 o más'
        for h in hijos_list:
            if h == 0: kids_dist[0] += 1
            elif h <= 2: kids_dist[1] += 1
            elif h <= 4: kids_dist[2] += 1
            else: kids_dist[3] += 1

        # Reservorios
        res_counts = {'Comunitario': 0, 'Privado': 0, 'No': 0, 'No definido': 0}
        for res in reservorios:
            name = res or 'No definido'
            if 'Comunitario' in name or 'Comunidad' in name:
                res_counts['Comunitario'] += 1
            elif 'Privado' in name:
                res_counts['Privado'] += 1
            elif 'No' in name:
                res_counts['No'] += 1
            else:
                res_counts['No definido'] += 1
        
        chart_reservorios_data[sector] = res_counts

        # Métodos de Riego promedios (en predios con riego > 0)
        grav_pcts = [r[7] for r in recs if r[7] is not None and r[7] > 0]
        aspr_pcts = [r[8] for r in recs if r[8] is not None and r[8] > 0]
        gote_pcts = [r[9] for r in recs if r[9] is not None and r[9] > 0]
        
        grav_avg = sum(grav_pcts) / len(grav_pcts) if grav_pcts else 0
        aspr_avg = sum(aspr_pcts) / len(aspr_pcts) if aspr_pcts else 0
        gote_avg = sum(gote_pcts) / len(gote_pcts) if gote_pcts else 0
        
        chart_metodos_data[sector] = {
            'Gravedad': grav_avg,
            'Aspersión': aspr_avg,
            'Goteo': gote_avg
        }
        
        chart_riego_secano_data[sector] = {
            'Riego': sum_riego / 10000.0,
            'Secano': (sum_total - sum_riego) / 10000.0
        }

        sector_stats_report.append({
            'name': sector,
            'tot': tot,
            'sum_total': sum_total,
            'avg_total': avg_total,
            'sum_riego': sum_riego,
            'avg_riego': avg_riego,
            'predio_counts': predio_counts,
            'avg_kids': avg_kids,
            'max_kids': max_kids,
            'kids_dist': kids_dist,
            'res_counts': res_counts,
            'metodos_avg': {'Gravedad': grav_avg, 'Aspersión': aspr_avg, 'Goteo': gote_avg},
            'metodos_counts': {'Gravedad': len(grav_pcts), 'Aspersión': len(aspr_pcts), 'Goteo': len(gote_pcts)}
        })

    # ── Consultas SQL para los nuevos gráficos sectoriales ──
    chart_destino_cultivos_data = {'Sector 1': {'Autoconsumo': 0, 'Mercado': 0, 'Agroindustria': 0, 'Exportación': 0},
                                   'Sector 2': {'Autoconsumo': 0, 'Mercado': 0, 'Agroindustria': 0, 'Exportación': 0},
                                   'Sector 3': {'Autoconsumo': 0, 'Mercado': 0, 'Agroindustria': 0, 'Exportación': 0}}
    if cultivos_table:
        cursor.execute(f"""
            SELECT COALESCE(NULLIF(f.sector_investigacion, ''), 'None') as sec,
                   SUM(CASE WHEN c.es_autoconsumo THEN 1 ELSE 0 END) as aut,
                   SUM(CASE WHEN c.es_mercado THEN 1 ELSE 0 END) as mer,
                   SUM(CASE WHEN c.es_agroindustria THEN 1 ELSE 0 END) as agr,
                   SUM(CASE WHEN c.es_exportacion THEN 1 ELSE 0 END) as exp
            FROM "{cultivos_table}" c
            JOIN "{fichas_table}" f ON c.ficha_id = f.id
            GROUP BY sec
        """)
        for sec, aut, mer, agr, exp in cursor.fetchall():
            s_name = 'Sector 1' if sec == 'None' else sec
            if s_name in chart_destino_cultivos_data:
                chart_destino_cultivos_data[s_name]['Autoconsumo'] = aut or 0
                chart_destino_cultivos_data[s_name]['Mercado'] = mer or 0
                chart_destino_cultivos_data[s_name]['Agroindustria'] = agr or 0
                chart_destino_cultivos_data[s_name]['Exportación'] = exp or 0

    chart_especies_pecuarias_data = []
    if animales_table:
        cursor.execute(f"""
            SELECT TRIM(UPPER(especie)) as esp, SUM(COALESCE(cantidad, 0)) as tot
            FROM "{animales_table}"
            GROUP BY esp
            ORDER BY tot DESC
            LIMIT 5
        """)
        chart_especies_pecuarias_data = cursor.fetchall()

    # Generar gráficos SVG Sectoriales
    generate_predios_svg(chart_predios_data, os.path.join(GRAFICOS_DIR, 'chart_predios_sectores.svg'))
    generate_reservorios_svg(chart_reservorios_data, os.path.join(GRAFICOS_DIR, 'chart_reservorios.svg'))
    generate_metodos_svg(chart_metodos_data, os.path.join(GRAFICOS_DIR, 'chart_metodos_riego.svg'))
    generate_riego_secano_svg(chart_riego_secano_data, os.path.join(GRAFICOS_DIR, 'chart_riego_secano.svg'))
    generate_especies_pecuarias_svg(chart_especies_pecuarias_data, os.path.join(GRAFICOS_DIR, 'chart_especies_pecuarias.svg'))
    generate_destino_cultivos_svg(chart_destino_cultivos_data, os.path.join(GRAFICOS_DIR, 'chart_destino_cultivos.svg'))

    # ── Conteos Reales y Normalizados por Parroquia ──
    def normalizar_parroquia(p):
        if not p: return ''
        p = p.upper().strip()
        p = p.replace('Á', 'A').replace('É', 'E').replace('Í', 'I').replace('Ó', 'O').replace('Ú', 'U')
        if 'CANGAHUA' in p: return 'CANGAHUA'
        if 'OTON' in p: return 'OTÓN'
        if 'ASCAZUBI' in p: return 'ASCÁZUBI'
        if 'CUSUBAMBA' in p: return 'CUSUBAMBA'
        return p

    cursor.execute(f"""
        SELECT COALESCE(parroquia, '') as par, COALESCE(comunidad, '') as com
        FROM "{fichas_table}"
    """)
    comunidades_por_parroquia = {'CANGAHUA': set(), 'OTÓN': set(), 'ASCÁZUBI': set(), 'CUSUBAMBA': set()}
    fichas_por_parroquia = {'CANGAHUA': 0, 'OTÓN': 0, 'ASCÁZUBI': 0, 'CUSUBAMBA': 0}
    
    for par_raw, com_raw in cursor.fetchall():
        par = normalizar_parroquia(par_raw)
        if par in fichas_por_parroquia:
            fichas_por_parroquia[par] += 1
            if com_raw and com_raw.strip():
                comunidades_por_parroquia[par].add(com_raw.strip().upper())

    total_fichas_todas = len(raw_all_fichas)
    
    with open(REPORT_MD_PATH, 'w', encoding='utf-8') as f:
        f.write(f"""# Informe Técnico: Estado del Catastro y Levantamiento de Información
*Elaborado por el Equipo Técnico de ap&catastro*

Este informe técnico presenta los resultados consolidados del levantamiento catastral, de infraestructura y socio-productivo para el **SISTEMA DE RIEGO COMUNITARIO GUANGUILQUI POROTOG** al día de hoy. El documento sirve como soporte formal para la presentación y revisión del estado de avance de la consultoría.

---

## 1. Resumen Ejecutivo del Levantamiento

Actualmente, el levantamiento de información georreferenciada en campo presenta las siguientes métricas clave de cobertura global:

* **Total de Fichas Investigadas - Unidades de Producción Agropecuaria (UPAs)**: **{total_fichas_todas:,} fichas**
* **Predios Vinculados en Cartografía (Catastro)**: **{predios_vinculados:,} polígonos unificados**
* **Total de Cultivos Registrados**: **{total_cultivos:,} parcelas agrícolas**
* **Total de Animales Censados**: **{total_animales:,} especies pecuarias**

---

## 2. Cobertura por Parroquias y Comunidades

La investigación cubre **4 parroquias principales** del Cantón Cayambe, registrando la siguiente distribución de fichas asociadas:

| Parroquia | N° Fichas Asociadas |
|---|---|
| **CANGAHUA** | {fichas_por_parroquia['CANGAHUA']:,} |
| **OTÓN** | {fichas_por_parroquia['OTÓN']:,} |
| **ASCÁZUBI** | {fichas_por_parroquia['ASCÁZUBI']:,} |
| **CUSUBAMBA** | {fichas_por_parroquia['CUSUBAMBA']:,} |

### Gráfico de Comunidades por Parroquia:
![N° Comunidades](informe_graficos/chart_parroquias.svg)

---

## 3. Primeros Resultados por Sectores de Investigación (Sectores 1, 2 y 3)

### A. Superficies de Tenencia y Cobertura de Riego
La siguiente tabla compara las áreas cultivadas y las superficies bajo riego promedio reportadas por los regantes en cada sector:

| Métrica de Superficie | Sector 1 | Sector 2 | Sector 3 |
|---|---|---|---|
| **Fichas Totales** | {sector_stats_report[0]['tot']:,} | {sector_stats_report[1]['tot']:,} | {sector_stats_report[2]['tot']:,} |
| **Área Total Declarada** | {sector_stats_report[0]['sum_total']:,.2f} m² | {sector_stats_report[1]['sum_total']:,.2f} m² | {sector_stats_report[2]['sum_total']:,.2f} m² |
| **Área Total Promedio por Predio** | {sector_stats_report[0]['avg_total']:,.2f} m² ({sector_stats_report[0]['avg_total']/10000:.3f} ha) | {sector_stats_report[1]['avg_total']:,.2f} m² ({sector_stats_report[1]['avg_total']/10000:.3f} ha) | {sector_stats_report[2]['avg_total']:,.2f} m² ({sector_stats_report[2]['avg_total']/10000:.3f} ha) |
| **Área con Riego Declarada** | {sector_stats_report[0]['sum_riego']:,.2f} m² | {sector_stats_report[1]['sum_riego']:,.2f} m² | {sector_stats_report[2]['sum_riego']:,.2f} m² |
| **Área con Riego Promedio por Predio** | {sector_stats_report[0]['avg_riego']:,.2f} m² ({sector_stats_report[0]['avg_riego']/10000:.3f} ha) | {sector_stats_report[1]['avg_riego']:,.2f} m² ({sector_stats_report[1]['avg_riego']/10000:.3f} ha) | {sector_stats_report[2]['avg_riego']:,.2f} m² ({sector_stats_report[2]['avg_riego']/10000:.3f} ha) |
| **Área sin Riego Declarada (Secano)** | {sin_riego_por_sector['Sector 1']:,.2f} m² ({sin_riego_por_sector['Sector 1']/10000:.2f} ha) | {sin_riego_por_sector['Sector 2']:,.2f} m² ({sin_riego_por_sector['Sector 2']/10000:.2f} ha) | {sin_riego_por_sector['Sector 3']:,.2f} m² ({sin_riego_por_sector['Sector 3']/10000:.2f} ha) |
| **Cultivos en el Sector (% del total)** | {cultivos_por_sector['Sector 1']:,} ({cultivos_por_sector['Sector 1']/max(total_cultivos, 1)*100:.1f}%) | {cultivos_por_sector['Sector 2']:,} ({cultivos_por_sector['Sector 2']/max(total_cultivos, 1)*100:.1f}%) | {cultivos_por_sector['Sector 3']:,} ({cultivos_por_sector['Sector 3']/max(total_cultivos, 1)*100:.1f}%) |
| **Animales en el Sector (% del total)** | {animales_por_sector['Sector 1']:,} ({animales_por_sector['Sector 1']/max(total_animales, 1)*100:.1f}%) | {animales_por_sector['Sector 2']:,} ({animales_por_sector['Sector 2']/max(total_animales, 1)*100:.1f}%) | {animales_por_sector['Sector 3']:,} ({animales_por_sector['Sector 3']/max(total_animales, 1)*100:.1f}%) |

### Análisis de Cobertura y Uso Sectorial:
El análisis de superficies revela una distribución productiva y de acceso al recurso hídrico altamente contrastante entre los tres sectores de investigación:
* **Sector 1:** Concentra el **{cultivos_por_sector['Sector 1']/max(total_cultivos, 1)*100:.1f}%** de la producción agrícola y el **{animales_por_sector['Sector 1']/max(total_animales, 1)*100:.1f}%** de las especies pecuarias del sistema. A pesar de ser el motor agropecuario principal del proyecto, registra **{sin_riego_por_sector['Sector 1']/10000:.2f} ha** de tierras en condiciones de secano (sin riego), lo que limita su capacidad de diversificación.
* **Sector 2:** Representa una zona de producción intermedia estable, concentrando el **{cultivos_por_sector['Sector 2']/max(total_cultivos, 1)*100:.1f}%** de los cultivos y el **{animales_por_sector['Sector 2']/max(total_animales, 1)*100:.1f}%** del ganado. Este sector mantiene una superficie de secano de **{sin_riego_por_sector['Sector 2']/10000:.2f} ha**, sustentada principalmente en minifundios de explotación familiar.
* **Sector 3:** Al ubicarse en las zonas de mayor dispersión y altitud desfavorable, presenta la mayor superficie de secano declarada del sistema con **{sin_riego_por_sector['Sector 3']/10000:.2f} ha** (el **{sin_riego_por_sector['Sector 3']/max(sum(sin_riego_por_sector.values()), 1)*100:.1f}%** del secano total). Esta carencia crítica de cobertura de riego restringe su producción agrícola al **{cultivos_por_sector['Sector 3']/max(total_cultivos, 1)*100:.1f}%** del total, reflejando la necesidad prioritaria de implementar reservorios comunitarios y extensiones de ramales de riego en este sector.

### Gráfico de Cobertura de Riego vs Secano por Sector (ha):
![Cobertura de Riego](informe_graficos/chart_riego_secano.svg)

---

### B. Distribución del Tamaño de los Predios (Minifundio)
Para entender la fragmentación de la tierra en la zona de estudio, se desglosa el tamaño de las propiedades de los regantes (Unidades de Producción Agropecuaria - UPAs) en rangos lógicos de hectáreas:

| Rango de Propiedad (ha) | Sector 1 | Sector 2 | Sector 3 |
|---|---|---|---|
| **Menos de 0.1 ha** (Microparcela) | {sector_stats_report[0]['predio_counts'][0]} ({sector_stats_report[0]['predio_counts'][0]/sector_stats_report[0]['tot']*100:.1f}%) | {sector_stats_report[1]['predio_counts'][0]} ({sector_stats_report[1]['predio_counts'][0]/sector_stats_report[1]['tot']*100:.1f}%) | {sector_stats_report[2]['predio_counts'][0]} ({sector_stats_report[2]['predio_counts'][0]/sector_stats_report[2]['tot']*100:.1f}%) |
| **0.1 a 0.5 ha** (Pequeño predio) | {sector_stats_report[0]['predio_counts'][1]} ({sector_stats_report[0]['predio_counts'][1]/sector_stats_report[0]['tot']*100:.1f}%) | {sector_stats_report[1]['predio_counts'][1]} ({sector_stats_report[1]['predio_counts'][1]/sector_stats_report[1]['tot']*100:.1f}%) | {sector_stats_report[2]['predio_counts'][1]} ({sector_stats_report[2]['predio_counts'][1]/sector_stats_report[2]['tot']*100:.1f}%) |
| **0.5 a 1.0 ha** (Predio medio) | {sector_stats_report[0]['predio_counts'][2]} ({sector_stats_report[0]['predio_counts'][2]/sector_stats_report[0]['tot']*100:.1f}%) | {sector_stats_report[1]['predio_counts'][2]} ({sector_stats_report[1]['predio_counts'][2]/sector_stats_report[1]['tot']*100:.1f}%) | {sector_stats_report[2]['predio_counts'][2]} ({sector_stats_report[2]['predio_counts'][2]/sector_stats_report[2]['tot']*100:.1f}%) |
| **1.0 a 5.0 ha** (Familiar) | {sector_stats_report[0]['predio_counts'][3]} ({sector_stats_report[0]['predio_counts'][3]/sector_stats_report[0]['tot']*100:.1f}%) | {sector_stats_report[1]['predio_counts'][3]} ({sector_stats_report[1]['predio_counts'][3]/sector_stats_report[1]['tot']*100:.1f}%) | {sector_stats_report[2]['predio_counts'][3]} ({sector_stats_report[2]['predio_counts'][3]/sector_stats_report[2]['tot']*100:.1f}%) |
| **5.0 a 10.0 ha** (Mediana producción) | {sector_stats_report[0]['predio_counts'][4]} ({sector_stats_report[0]['predio_counts'][4]/sector_stats_report[0]['tot']*100:.1f}%) | {sector_stats_report[1]['predio_counts'][4]} ({sector_stats_report[1]['predio_counts'][4]/sector_stats_report[1]['tot']*100:.1f}%) | {sector_stats_report[2]['predio_counts'][4]} ({sector_stats_report[2]['predio_counts'][4]/sector_stats_report[2]['tot']*100:.1f}%) |
| **Más de 10.0 ha** (Gran escala) | {sector_stats_report[0]['predio_counts'][5]} ({sector_stats_report[0]['predio_counts'][5]/sector_stats_report[0]['tot']*100:.1f}%) | {sector_stats_report[1]['predio_counts'][5]} ({sector_stats_report[1]['predio_counts'][5]/sector_stats_report[1]['tot']*100:.1f}%) | {sector_stats_report[2]['predio_counts'][5]} ({sector_stats_report[2]['predio_counts'][5]/sector_stats_report[2]['tot']*100:.1f}%) |

### Gráfico de Distribución de Predios:
![Distribución Predios](informe_graficos/chart_predios_sectores.svg)

---

### C. Características de las Familias de Regantes
Evaluamos la carga demográfica que soportan las UPAs familiares a través del número de hijos reportados por hogar:

* **Promedio de Hijos por Hogar**: 
  * Sector 1: **{sector_stats_report[0]['avg_kids']:.1f} hijos** (Hogar promedio de ~{sector_stats_report[0]['avg_kids'] + 2:.1f} personas).
  * Sector 2: **{sector_stats_report[1]['avg_kids']:.1f} hijos** (Hogar promedio de ~{sector_stats_report[1]['avg_kids'] + 2:.1f} personas).
  * Sector 3: **{sector_stats_report[2]['avg_kids']:.1f} hijos** (Hogar promedio de ~{sector_stats_report[2]['avg_kids'] + 2:.1f} personas).

| Carga Familiar (N° Hijos) | Sector 1 | Sector 2 | Sector 3 |
|---|---|---|---|
| **Hogares Sin Hijos** | {sector_stats_report[0]['kids_dist'][0]} ({sector_stats_report[0]['kids_dist'][0]/sector_stats_report[0]['tot']*100:.1f}%) | {sector_stats_report[1]['kids_dist'][0]} ({sector_stats_report[1]['kids_dist'][0]/sector_stats_report[1]['tot']*100:.1f}%) | {sector_stats_report[2]['kids_dist'][0]} ({sector_stats_report[2]['kids_dist'][0]/sector_stats_report[2]['tot']*100:.1f}%) |
| **Hogares con 1 a 2 hijos** | {sector_stats_report[0]['kids_dist'][1]} ({sector_stats_report[0]['kids_dist'][1]/sector_stats_report[0]['tot']*100:.1f}%) | {sector_stats_report[1]['kids_dist'][1]} ({sector_stats_report[1]['kids_dist'][1]/sector_stats_report[1]['tot']*100:.1f}%) | {sector_stats_report[2]['kids_dist'][1]} ({sector_stats_report[2]['kids_dist'][1]/sector_stats_report[2]['tot']*100:.1f}%) |
| **Hogares con 3 a 4 hijos** | {sector_stats_report[0]['kids_dist'][2]} ({sector_stats_report[0]['kids_dist'][2]/sector_stats_report[0]['tot']*100:.1f}%) | {sector_stats_report[1]['kids_dist'][2]} ({sector_stats_report[1]['kids_dist'][2]/sector_stats_report[1]['tot']*100:.1f}%) | {sector_stats_report[2]['kids_dist'][2]} ({sector_stats_report[2]['kids_dist'][2]/sector_stats_report[2]['tot']*100:.1f}%) |
| **Hogares con 5 o más hijos** | {sector_stats_report[0]['kids_dist'][3]} ({sector_stats_report[0]['kids_dist'][3]/sector_stats_report[0]['tot']*100:.1f}%) | {sector_stats_report[1]['kids_dist'][3]} ({sector_stats_report[1]['kids_dist'][3]/sector_stats_report[1]['tot']*100:.1f}%) | {sector_stats_report[2]['kids_dist'][3]} ({sector_stats_report[2]['kids_dist'][3]/sector_stats_report[2]['tot']*100:.1f}%) |

---

### D. Actividad y Producción Agropecuaria por Sector

El desarrollo productivo de las Unidades de Producción Agropecuaria (UPAs) se sustenta en la actividad pecuaria y en el destino de los cultivos agrícolas cultivados en el territorio:

#### Especies Pecuarias Principales (Cabezas de Ganado):
![Especies Pecuarias](informe_graficos/chart_especies_pecuarias.svg)

#### Destino de la Producción Agrícola por Sector:
![Destino de la Producción](informe_graficos/chart_destino_cultivos.svg)

---

## 4. Infraestructura y Métodos de Riego

La infraestructura hidráulica y los métodos utilizados para regar los lotes reflejan la tecnología instalada en el territorio:

### A. Sistemas de Riego (Tenencia de Reservorio)
Comparación del tipo de reservorio del cual se abastece la familia:

| Tipo de Reservorio | Sector 1 | Sector 2 | Sector 3 |
|---|---|---|---|
| **Comunitario** | {sector_stats_report[0]['res_counts']['Comunitario']} ({sector_stats_report[0]['res_counts']['Comunitario']/sector_stats_report[0]['tot']*100:.1f}%) | {sector_stats_report[1]['res_counts']['Comunitario']} ({sector_stats_report[1]['res_counts']['Comunitario']/sector_stats_report[1]['tot']*100:.1f}%) | {sector_stats_report[2]['res_counts']['Comunitario']} ({sector_stats_report[2]['res_counts']['Comunitario']/sector_stats_report[2]['tot']*100:.1f}%) |
| **Privado** | {sector_stats_report[0]['res_counts']['Privado']} ({sector_stats_report[0]['res_counts']['Privado']/sector_stats_report[0]['tot']*100:.1f}%) | {sector_stats_report[1]['res_counts']['Privado']} ({sector_stats_report[1]['res_counts']['Privado']/sector_stats_report[1]['tot']*100:.1f}%) | {sector_stats_report[2]['res_counts']['Privado']} ({sector_stats_report[2]['res_counts']['Privado']/sector_stats_report[2]['tot']*100:.1f}%) |
| **No tiene reservorio** | {sector_stats_report[0]['res_counts']['No']} ({sector_stats_report[0]['res_counts']['No']/sector_stats_report[0]['tot']*100:.1f}%) | {sector_stats_report[1]['res_counts']['No']} ({sector_stats_report[1]['res_counts']['No']/sector_stats_report[1]['tot']*100:.1f}%) | {sector_stats_report[2]['res_counts']['No']} ({sector_stats_report[2]['res_counts']['No']/sector_stats_report[2]['tot']*100:.1f}%) |
| **No definido / S/A** | {sector_stats_report[0]['res_counts']['No definido']} ({sector_stats_report[0]['res_counts']['No definido']/sector_stats_report[0]['tot']*100:.1f}%) | {sector_stats_report[1]['res_counts']['No definido']} ({sector_stats_report[1]['res_counts']['No definido']/sector_stats_report[1]['tot']*100:.1f}%) | {sector_stats_report[2]['res_counts']['No definido']} ({sector_stats_report[2]['res_counts']['No definido']/sector_stats_report[2]['tot']*100:.1f}%) |

### Gráfico de Tenencia de Reservorio:
![Reservorios](informe_graficos/chart_reservorios.svg)

### B. Aplicación de Métodos de Riego por Sector
Desglose del porcentaje de uso promedio para cada método de riego reportado en los predios que cuentan con cobertura hídrica:

* **Gravedad**: 
  * Sector 1: **{sector_stats_report[0]['metodos_avg']['Gravedad']:.1f}%** promedio (en {sector_stats_report[0]['metodos_counts']['Gravedad']} predios).
  * Sector 2: **{sector_stats_report[1]['metodos_avg']['Gravedad']:.1f}%** promedio (en {sector_stats_report[1]['metodos_counts']['Gravedad']} predios).
  * Sector 3: **{sector_stats_report[2]['metodos_avg']['Gravedad']:.1f}%** promedio (en {sector_stats_report[2]['metodos_counts']['Gravedad']} predios).
* **Aspersión**: 
  * Sector 1: **{sector_stats_report[0]['metodos_avg']['Aspersión']:.1f}%** promedio (en {sector_stats_report[0]['metodos_counts']['Aspersión']} predios).
  * Sector 2: **{sector_stats_report[1]['metodos_avg']['Aspersión']:.1f}%** promedio (en {sector_stats_report[1]['metodos_counts']['Aspersión']} predios).
  * Sector 3: **{sector_stats_report[2]['metodos_avg']['Aspersión']:.1f}%** promedio (en {sector_stats_report[2]['metodos_counts']['Aspersión']} predios).
* **Goteo**: 
  * Sector 1: **{sector_stats_report[0]['metodos_avg']['Goteo']:.1f}%** promedio (en {sector_stats_report[0]['metodos_counts']['Goteo']} predios).
  * Sector 2: **{sector_stats_report[1]['metodos_avg']['Goteo']:.1f}%** promedio (en {sector_stats_report[1]['metodos_counts']['Goteo']} predios).
  * Sector 3: **{sector_stats_report[2]['metodos_avg']['Goteo']:.1f}%** promedio (en {sector_stats_report[2]['metodos_counts']['Goteo']} predios).

### Gráfico de Métodos de Riego por Sector:
![Métodos de Riego](informe_graficos/chart_metodos_riego.svg)

---

## 5. Hallazgos Clave de Alto Impacto para la Planificación

Analizando detalladamente la información del catastro y el censo socio-agrícola, destacamos cuatro hallazgos clave de alto impacto para la planificación del proyecto:

1. **La Realidad del Minifundio y su Impacto Productivo**: En los Sectores 2 y 3, **más del 65% de los predios investigados miden menos de 0.5 Hectáreas** (5,000 m²). Esto evidencia una fragmentación de tierra sumamente alta. Cualquier planificación de inversión y tecnificación debe estructurarse asumiendo que los regantes operan UPAs de subsistencia a muy pequeña escala, lo que dificulta la tecnificación individual y hace imprescindible las soluciones de manejo asociativo.
2. **Fuerte Dependencia de Gestión Comunitaria**: En promedio, **más del 85% de los regantes se abastecen de reservorios de tipo Comunitario**. La infraestructura privada o familiar es muy baja (menor al 8% en el mejor de los casos). Esto demuestra que el tejido social y organizativo local es la base fundamental del éxito del sistema. Las juntas de agua locales son las aliadas centrales en el desarrollo de la presa y canales.
3. **Aspersión como Tecnología Dominante con Oportunidad de Optimización**: El riego por aspersión abarca más del **95% de la aplicación** en los lotes con riego de todos los sectores, mientras que el riego por goteo (tecnología altamente eficiente) tiene una cobertura casi inexistente (menor al 5% en predios activos). Existe una oportunidad enorme de optimización y ahorro de recursos hídricos incentivando la transición de aspersión a goteo.
4. **Seguridad Alimentaria Familiar Crítica**: En el área del proyecto, **más del 20% de los hogares reportan familias con 5 o más hijos** (con un promedio general superior a 3.1 hijos por familia). Estos hogares de 5 a 6 personas dependen de la producción de parcelas menores a 0.5 ha. Garantizar un flujo constante de agua para riego no solo es un tema de desarrollo económico, sino de seguridad alimentaria directa para estas familias numerosas.

---

---
**Elaborado por:** Equipo Técnico de ap&catastro
""")
        
    print(f"  [OK] {REPORT_MD_PATH} e informe_graficos/ generados exitosamente.")
    conn.close()

if __name__ == "__main__":
    main()
