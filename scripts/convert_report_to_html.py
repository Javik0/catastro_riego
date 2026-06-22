# -*- coding: utf-8 -*-
"""
Convertidor de Informe Técnico Markdown a HTML Premium Autocontenido
Embebe los gráficos SVG directamente en el archivo HTML para que sea 100% portable,
e incluye estilos CSS corporativos listos para impresión y visualización.
"""

import os
import re

# Rutas
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MD_PATH = os.path.join(BASE_DIR, "informe_reunion_tecnica.md")
HTML_PATH = os.path.join(BASE_DIR, "informe_reunion_tecnica.html")
GRAFICOS_DIR = os.path.join(BASE_DIR, "informe_graficos")

def read_svg_content(img_path):
    """Lee el contenido de un archivo SVG y elimina el prólogo XML para inyectarlo en HTML."""
    full_path = os.path.join(BASE_DIR, img_path.replace("/", os.sep))
    if not os.path.exists(full_path):
        return f'<div class="error-box">Gráfico no encontrado: {img_path}</div>'
    
    with open(full_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Limpiar posibles cabeceras <?xml ...?> o doctypes
    content = re.sub(r'<\?xml.*?\?>', '', content, flags=re.DOTALL)
    content = re.sub(r'<!DOCTYPE.*?>', '', content, flags=re.DOTALL)
    return content.strip()

def parse_markdown(md_text):
    """Conversión simple y estilizada de Markdown a HTML."""
    lines = md_text.split("\n")
    html_lines = []
    
    in_list = False
    in_table = False
    table_headers = []
    table_rows = []
    
    for line in lines:
        stripped = line.strip()
        
        # Ignorar líneas de separación de tablas (ej. |---|---|)
        if in_table and re.match(r'^[\s|:-]+$', stripped):
            continue
            
        # Detectar Tablas
        if stripped.startswith("|") and stripped.endswith("|"):
            if not in_table:
                in_table = True
                # Limpiar celdas vacías por los pipes externos
                cells = [c.strip() for c in stripped.split("|")[1:-1]]
                table_headers = cells
            else:
                cells = [c.strip() for c in stripped.split("|")[1:-1]]
                table_rows.append(cells)
            continue
        elif in_table:
            # Fin de la tabla, renderizar
            html_lines.append('<div class="table-container">')
            html_lines.append('<table>')
            if table_headers:
                html_lines.append('<thead><tr>')
                for h in table_headers:
                    # Parsear negritas o texto dentro de la celda
                    h_html = parse_inline(h)
                    html_lines.append(f'<th>{h_html}</th>')
                html_lines.append('</tr></thead>')
            if table_rows:
                html_lines.append('<tbody>')
                for row in table_rows:
                    html_lines.append('<tr>')
                    for c in row:
                        c_html = parse_inline(c)
                        html_lines.append(f'<td>{c_html}</td>')
                    html_lines.append('</tr>')
                html_lines.append('</tbody>')
            html_lines.append('</table>')
            html_lines.append('</div>')
            in_table = False
            table_headers = []
            table_rows = []
            
        # Cerrar lista si corresponde
        if not stripped.startswith("* ") and in_list:
            html_lines.append("</ul>")
            in_list = False
            
        # Encabezados
        if stripped.startswith("# "):
            title = parse_inline(stripped[2:])
            html_lines.append(f"<h1>{title}</h1>")
        elif stripped.startswith("## "):
            title = parse_inline(stripped[3:])
            html_lines.append(f"<h2>{title}</h2>")
        elif stripped.startswith("### "):
            title = parse_inline(stripped[4:])
            html_lines.append(f"<h3>{title}</h3>")
        # Listas con viñetas
        elif stripped.startswith("* "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            item_text = parse_inline(stripped[2:])
            html_lines.append(f"<li>{item_text}</li>")
        # Separadores
        elif stripped == "---":
            html_lines.append("<hr />")
        # Imágenes (Gráficos SVG)
        elif stripped.startswith("![") and "]" in stripped and "(" in stripped:
            match = re.search(r'!\[(.*?)\]\((.*?)\)', stripped)
            if match:
                alt = match.group(1)
                img_path = match.group(2)
                if img_path.endswith(".svg"):
                    svg_content = read_svg_content(img_path)
                    html_lines.append(f'<div class="chart-box">')
                    html_lines.append(f'<div class="chart-title">{alt}</div>')
                    html_lines.append(svg_content)
                    html_lines.append('</div>')
                else:
                    html_lines.append(f'<div class="image-box"><img src="{img_path}" alt="{alt}"></div>')
        # Párrafos normales o líneas vacías
        else:
            if stripped:
                p_text = parse_inline(stripped)
                # Si empieza con alerta o emoji de hallazgo, darle una clase especial
                if p_text.startswith("📢") or p_text.startswith("🔊"):
                    html_lines.append(f'<p class="finding-alert">{p_text}</p>')
                elif p_text.startswith("✓") or p_text.startswith("[OK]"):
                    html_lines.append(f'<p class="success-alert">{p_text}</p>')
                elif p_text.startswith("❌") or p_text.startswith("⚠"):
                    html_lines.append(f'<p class="warning-alert">{p_text}</p>')
                else:
                    html_lines.append(f"<p>{p_text}</p>")
            else:
                html_lines.append("")
                
    # Cerrar elementos pendientes al final
    if in_table:
        html_lines.append("</table></div>")
    if in_list:
        html_lines.append("</ul>")
        
    return "\n".join(html_lines)

def parse_inline(text):
    """Parsear elementos en línea como negritas y enlaces."""
    # Reemplazar **texto** con <strong>texto</strong>
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    # Reemplazar *texto* con <em>texto</em>
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    # Reemplazar links [nombre](url)
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2" target="_blank">\1</a>', text)
    return text

def main():
    if not os.path.exists(MD_PATH):
        print(f"Error: No se encontró el informe técnico en {MD_PATH}")
        return

    with open(MD_PATH, "r", encoding="utf-8") as f:
        md_content = f.read()

    body_html = parse_markdown(md_content)

    html_template = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Informe Técnico - Padrón de Riego Porotog</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: #1e293b;
            --primary-light: #475569;
            --accent: #2563eb;
            --accent-light: #dbeafe;
            --bg-page: #f8fafc;
            --bg-card: #ffffff;
            --border: #e2e8f0;
            --text: #334155;
            --text-dark: #0f172a;
            --text-muted: #64748b;
            --success: #16a34a;
            --success-light: #dcfce7;
            --warning: #ca8a04;
            --warning-light: #fef9c3;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: 'Plus Jakarta Sans', sans-serif;
            background-color: var(--bg-page);
            color: var(--text);
            line-height: 1.6;
            padding: 40px 20px;
        }}

        .report-wrapper {{
            max-width: 900px;
            margin: 0 auto;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.05);
            padding: 50px 60px;
        }}

        /* Encabezados del Documento */
        h1, h2, h3, h4 {{
            font-family: 'Outfit', sans-serif;
            color: var(--text-dark);
            font-weight: 700;
        }}

        h1 {{
            font-size: 28px;
            line-height: 1.25;
            margin-bottom: 8px;
            border-bottom: 2px solid var(--accent);
            padding-bottom: 12px;
            text-align: center;
        }}

        p.subtitle {{
            text-align: center;
            font-size: 14px;
            color: var(--text-muted);
            font-style: italic;
            margin-bottom: 30px;
        }}

        h2 {{
            font-size: 20px;
            margin-top: 35px;
            margin-bottom: 15px;
            border-bottom: 1px solid var(--border);
            padding-bottom: 8px;
            color: var(--primary);
            display: flex;
            align-items: center;
        }}

        h3 {{
            font-size: 16px;
            margin-top: 20px;
            margin-bottom: 10px;
            color: var(--primary-light);
        }}

        p {{
            margin-bottom: 16px;
            font-size: 14.5px;
            text-align: justify;
        }}

        strong {{
            color: var(--text-dark);
            font-weight: 600;
        }}

        ul {{
            margin-left: 20px;
            margin-bottom: 20px;
        }}

        li {{
            margin-bottom: 6px;
            font-size: 14px;
        }}

        hr {{
            border: 0;
            height: 1px;
            background: var(--border);
            margin: 30px 0;
        }}

        a {{
            color: var(--accent);
            text-decoration: none;
            font-weight: 500;
        }}

        a:hover {{
            text-decoration: underline;
        }}

        /* Contenedores de tablas */
        .table-container {{
            width: 100%;
            overflow-x: auto;
            margin: 20px 0;
            border: 1px solid var(--border);
            border-radius: 8px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13.5px;
            text-align: left;
        }}

        th, td {{
            padding: 10px 14px;
            border-bottom: 1px solid var(--border);
        }}

        th {{
            background-color: var(--primary);
            color: white;
            font-weight: 600;
            font-family: 'Outfit', sans-serif;
        }}

        tr:nth-child(even) {{
            background-color: var(--bg-page);
        }}

        tr:hover {{
            background-color: #f1f5f9;
        }}

        /* Cajas de Gráficos SVG Embebidos */
        .chart-box {{
            background: var(--bg-page);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            margin: 25px 0;
            text-align: center;
            box-shadow: inset 0 2px 4px 0 rgba(0, 0, 0, 0.02);
        }}

        .chart-title {{
            font-family: 'Outfit', sans-serif;
            font-size: 13px;
            font-weight: 600;
            color: var(--text-dark);
            margin-bottom: 15px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        .chart-box svg {{
            max-width: 100%;
            height: auto;
            display: inline-block;
        }}

        /* Alertas estilizadas */
        .finding-alert {{
            background-color: var(--accent-light);
            border-left: 4px solid var(--accent);
            padding: 14px 18px;
            border-radius: 0 8px 8px 0;
            font-size: 14px;
            color: var(--text-dark);
            margin-top: 15px;
            margin-bottom: 15px;
            text-align: left;
        }}

        .success-alert {{
            background-color: var(--success-light);
            border-left: 4px solid var(--success);
            padding: 12px 16px;
            border-radius: 0 8px 8px 0;
            font-size: 13.5px;
            color: var(--text-dark);
            margin-top: 10px;
            margin-bottom: 10px;
        }}

        .warning-alert {{
            background-color: var(--warning-light);
            border-left: 4px solid var(--warning);
            padding: 12px 16px;
            border-radius: 0 8px 8px 0;
            font-size: 13.5px;
            color: var(--text-dark);
            margin-top: 10px;
            margin-bottom: 10px;
        }}

        /* Botón de Impresión en HTML */
        .print-btn-bar {{
            display: flex;
            justify-content: flex-end;
            margin-bottom: 20px;
            max-width: 900px;
            margin: 0 auto 15px auto;
        }}

        .print-btn {{
            background-color: var(--accent);
            color: white;
            font-family: 'Outfit', sans-serif;
            font-weight: 600;
            font-size: 13.5px;
            border: none;
            padding: 10px 18px;
            border-radius: 8px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2);
            transition: all 0.2s ease;
        }}

        .print-btn:hover {{
            background-color: #1d4ed8;
            box-shadow: 0 6px 8px -1px rgba(37, 99, 235, 0.3);
            transform: translateY(-1px);
        }}

        .print-btn svg {{
            width: 16px;
            height: 16px;
            fill: none;
            stroke: currentColor;
            stroke-width: 2;
        }}

        /* Estilos de Impresión */
        @media print {{
            body {{
                background-color: white;
                padding: 0;
                color: black;
            }}

            .report-wrapper {{
                border: none;
                box-shadow: none;
                padding: 0;
                max-width: 100%;
            }}

            .print-btn-bar {{
                display: none;
            }}

            .chart-box {{
                page-break-inside: avoid;
                background: white;
                border: 1px solid #ccc;
            }}

            h1, h2, h3, .table-container, .finding-alert {{
                page-break-inside: avoid;
            }}

            .finding-alert {{
                background-color: #f1f5f9 !important;
                border-left: 4px solid #475569 !important;
            }}
        }}
    </style>
</head>
<body>
    <div class="print-btn-bar">
        <button class="print-btn" onclick="window.print()">
            <svg viewBox="0 0 24 24"><path d="M6 9V2h12v7M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2m-12 0v5h12v-5M18 11.01L18 11"></path></svg>
            Imprimir Reporte / Guardar PDF
        </button>
    </div>
    
    <div class="report-wrapper">
        {body_html}
    </div>
</body>
</html>
"""

    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    print(f"[OK] Convertido exitosamente a HTML autocontenido en: {HTML_PATH}")

if __name__ == "__main__":
    main()
