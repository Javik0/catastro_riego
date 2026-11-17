"""
Generador del Listado Profesional en Excel de los 28 Predios Afectados
por la Vía de Acceso (CAD berma 1 de 6 m) - Proyecto Presa Porotog.

Genera un libro .xlsx con formato institucional de alta gama:
- Fórmulas dinámicas (SUM, AVERAGE, ratios)
- Filtros automáticos en todas las hojas
- Progresivas viales calculadas (PK K0+000 a K6+012)
- Coordenadas georreferenciadas UTM 17S (X, Y) y WGS84 (Lat, Lon)
- Inventario de obras de drenaje proyectadas (7 alcantarillas, cruce canal, campamento)
- Balances territoriales y jurídicos listos para impresión y auditoría
"""

import os
import sys
import json
import math
import pyproj
from shapely.geometry import shape, Point
from shapely.ops import transform
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PUBLIC_DIR = os.path.join(BASE_DIR, "public")
GEO_REPRESA_DIR = os.path.join(PUBLIC_DIR, "geo", "represa")
DESCARGAS_DIR = os.path.join(PUBLIC_DIR, "descargas")
DOCS_DIR = os.path.join(BASE_DIR, "..", "CARTOGRAFIA REPRESA")

# Archivos de entrada
VIA_PATH = os.path.join(GEO_REPRESA_DIR, "via_acceso.geojson")
PREDIOS_PATH = os.path.join(GEO_REPRESA_DIR, "predios_via_acceso.geojson")
OBRAS_PATH = os.path.join(GEO_REPRESA_DIR, "obras_via_acceso.geojson")
MAGNITUD_PATH = os.path.join(GEO_REPRESA_DIR, "magnitud.json")

# Archivos de salida
os.makedirs(DESCARGAS_DIR, exist_ok=True)
os.makedirs(DOCS_DIR, exist_ok=True)
OUTPUT_WEB = os.path.join(DESCARGAS_DIR, "predios_afectados_via_acceso_represa.xlsx")
OUTPUT_CARTO = os.path.join(DOCS_DIR, "PREDIOS_AFECTADOS_VIA_ACCESO_REPRESA.xlsx")

# Transformadores de coordenadas
to_utm = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:32717", always_xy=True).transform
to_wgs = pyproj.Transformer.from_crs("EPSG:32717", "EPSG:4326", always_xy=True).transform

def format_pk(meters):
    if meters is None or math.isnan(meters):
        return "—"
    tot_m = int(round(meters))
    km = tot_m // 1000
    m = tot_m % 1000
    return f"K{km}+{m:03d}"

def generar_excel():
    print("Cargando insumos geoespaciales...")
    with open(VIA_PATH, encoding="utf-8") as f:
        via_data = json.load(f)
    with open(PREDIOS_PATH, encoding="utf-8") as f:
        predios_data = json.load(f)
    with open(OBRAS_PATH, encoding="utf-8") as f:
        obras_data = json.load(f)
    with open(MAGNITUD_PATH, encoding="utf-8") as f:
        mag_data = json.load(f)

    via_info = mag_data.get("via_acceso", {})
    predios_lista = via_info.get("predios", [])
    print(f"Total predios registrados: {len(predios_lista)}")

    # Obtener geometría del eje en UTM 17S
    eje_feat = [f for f in via_data["features"] if f["properties"].get("tipo") == "eje"][0]
    geom_eje_wgs = shape(eje_feat["geometry"])
    geom_eje_utm = transform(to_utm, geom_eje_wgs)

    # Mapear geometrías de predios y solapes por clave
    geoms_predio_utm = {}
    geoms_solape_utm = {}
    for f in predios_data["features"]:
        clave = f["properties"].get("clave")
        tipo = f["properties"].get("tipo")
        if not clave:
            continue
        geom_wgs = shape(f["geometry"])
        geom_utm = transform(to_utm, geom_wgs)
        if tipo == "predio_completo":
            geoms_predio_utm[clave] = geom_utm
        elif tipo == "solape":
            geoms_solape_utm[clave] = geom_utm

    # Obras singulares consolidadas (sin líneas parásitas de campamento)
    obras_consolidadas = []
    campamento_geoms = []

    for f in obras_data["features"]:
        p = f["properties"]
        geom_wgs = shape(f["geometry"])
        geom_utm = transform(to_utm, geom_wgs)
        tipo = p.get("tipo_obra")
        nombre = p.get("nombre", "")

        if tipo == "campamento":
            campamento_geoms.append(geom_utm)
            continue

        if tipo in ("alcantarilla", "estructura_vial") and not nombre.startswith("Obra CAD"):
            c = geom_utm.centroid
            dist = geom_eje_utm.project(c)
            obras_consolidadas.append({
                "nombre": nombre,
                "tipo_obra": tipo,
                "detalle": p.get("detalle", ""),
                "capa_cad": p.get("capa_cad", ""),
                "cota": p.get("cota"),
                "geom": geom_utm,
                "dist_eje": dist,
                "pk": format_pk(dist),
                "x": c.x,
                "y": c.y,
            })

    # Consolidar el campamento de obra en 1 solo registro representativo
    if campamento_geoms:
        from shapely.ops import unary_union
        union_camp = unary_union(campamento_geoms)
        c_camp = union_camp.centroid
        dist_camp = geom_eje_utm.project(c_camp)
        obras_consolidadas.append({
            "nombre": "Campamento de obra - Presa Porotog",
            "tipo_obra": "campamento",
            "detalle": "Instalaciones de obra, talleres y administración (margen izquierda)",
            "capa_cad": "P-P_CAMPAMENTO",
            "cota": 3410.0,
            "geom": union_camp,
            "dist_eje": dist_camp,
            "pk": format_pk(dist_camp),
            "x": c_camp.x,
            "y": c_camp.y,
        })

    # Ordenar obras consolidadas por PK a lo largo del trazado
    obras_consolidadas.sort(key=lambda o: o["dist_eje"])

    # Enriquecer los 28 predios
    predios_enriquecidos = []
    for p in predios_lista:
        clave = p["clave"]
        geom_solape = geoms_solape_utm.get(clave)
        geom_predio = geoms_predio_utm.get(clave)
        geom_ref = geom_solape if geom_solape is not None else geom_predio

        # Coordenadas centroide
        if geom_ref is not None and not geom_ref.is_empty:
            c = geom_ref.centroid
            utm_x = round(c.x, 1)
            utm_y = round(c.y, 1)
            wgs_lon, wgs_lat = to_wgs(c.x, c.y)
            wgs_lat = round(wgs_lat, 6)
            wgs_lon = round(wgs_lon, 6)
        else:
            utm_x, utm_y, wgs_lat, wgs_lon = None, None, None, None

        # PK inicial y final
        if geom_ref is not None and not geom_ref.is_empty:
            inter = geom_ref.intersection(geom_eje_utm)
            if not inter.is_empty:
                if inter.geom_type == "LineString":
                    pts = list(inter.coords)
                elif inter.geom_type == "MultiLineString":
                    pts = [pt for ls in inter.geoms for pt in ls.coords]
                elif inter.geom_type in ("Point", "MultiPoint"):
                    pts = list(inter.coords) if hasattr(inter, "coords") else [g.coords[0] for g in inter.geoms]
                else:
                    pts = list(geom_ref.boundary.coords) if hasattr(geom_ref, "boundary") else []
                dists = [geom_eje_utm.project(Point(pt)) for pt in pts]
            else:
                pts = list(geom_ref.exterior.coords) if hasattr(geom_ref, "exterior") else []
                dists = [geom_eje_utm.project(Point(pt)) for pt in pts] if pts else [geom_eje_utm.project(geom_ref.centroid)]

            min_dist = min(dists) if dists else 0
            max_dist = max(dists) if dists else 0
        else:
            min_dist, max_dist = 0, 0

        # Obras singulares cercanas dentro del predio o a menos de 50 m
        obras_cercanas = []
        if geom_ref is not None and not geom_ref.is_empty:
            for o in obras_consolidadas:
                if o["geom"].distance(geom_ref) <= 45.0:
                    obras_cercanas.append(f"{o['nombre']} ({o['pk']})")

        obras_txt = " · ".join(dict.fromkeys(obras_cercanas)) if obras_cercanas else "Ninguna en la franja inmediata"

        fuente = p.get("fuente_propietario")
        if fuente == "padron":
            condicion_cat = "Padrón de Regantes (Investigado en campo)"
            tramite = "Constitución de servidumbre de paso vial e indemnización por franja (6,00 m)"
        elif fuente == "catastro_municipal":
            condicion_cat = "Catastro Municipal GADM (Sin ficha de padrón)"
            tramite = "Notificación a titular municipal / Verificación registral / Servidumbre de paso"
        else:
            condicion_cat = "Área Comunal / Páramo (Sin titular registrado)"
            tramite = "Acuerdo comunal de uso de suelo y declaratoria de utilidad pública"

        predios_enriquecidos.append({
            **p,
            "condicion_cat": condicion_cat,
            "tramite": tramite,
            "pk_inicio_m": min_dist,
            "pk_fin_m": max_dist,
            "pk_inicio": format_pk(min_dist),
            "pk_fin": format_pk(max_dist),
            "tramo_pk": f"{format_pk(min_dist)} a {format_pk(max_dist)}",
            "utm_x": utm_x,
            "utm_y": utm_y,
            "wgs_lat": wgs_lat,
            "wgs_lon": wgs_lon,
            "obras_cercanas": obras_txt
        })

    # Ordenar predios progresivamente desde el inicio de la vía (Izacata K0+000) hacia la presa (K6+012)
    predios_enriquecidos.sort(key=lambda r: (r["pk_inicio_m"], -r.get("m2_en_via", 0)))

    # Crear libro de Excel
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    # -------------------------------------------------------------------------
    # ESTILOS INSTITUCIONALES PROFESIONALES
    # -------------------------------------------------------------------------
    font_title = Font(name="Calibri", size=14, bold=True, color="1E3A8A")
    font_sub = Font(name="Calibri", size=9.5, bold=False, color="475569")
    font_sec = Font(name="Calibri", size=11, bold=True, color="0F172A")
    font_th = Font(name="Calibri", size=9.5, bold=True, color="FFFFFF")
    font_data = Font(name="Calibri", size=9.5, color="0F172A")
    font_mono = Font(name="Consolas", size=9.5, color="0F172A")
    font_total = Font(name="Calibri", size=10, bold=True, color="1E3A8A")

    fill_th = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid") # Navy
    fill_th2 = PatternFill(start_color="0F766E", end_color="0F766E", fill_type="solid") # Teal
    fill_th3 = PatternFill(start_color="334155", end_color="334155", fill_type="solid") # Slate
    fill_total = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")

    fill_padron = PatternFill(start_color="FEF2F2", end_color="FEF2F2", fill_type="solid")
    fill_muni = PatternFill(start_color="EFF6FF", end_color="EFF6FF", fill_type="solid")
    fill_paramo = PatternFill(start_color="FFFBEB", end_color="FFFBEB", fill_type="solid")

    border_thin_gray = Side(style="thin", color="CBD5E1")
    border_double_bottom = Side(style="double", color="1E3A8A")
    border_cell = Border(left=border_thin_gray, right=border_thin_gray, top=border_thin_gray, bottom=border_thin_gray)
    border_total_row = Border(top=border_thin_gray, bottom=border_double_bottom, left=border_thin_gray, right=border_thin_gray)

    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")
    align_right = Alignment(horizontal="right", vertical="center")

    # =========================================================================
    # HOJA 1: PREDIOS AFECTADOS VÍA (28)
    # =========================================================================
    ws1 = wb.create_sheet(title="Predios Afectados Vía (28)")
    ws1.views.sheetView[0].showGridLines = True

    # Membrete institucional
    ws1.merge_cells("A1:W1")
    ws1["A1"] = "PROYECTO DE RIEGO COMUNITARIO GUANGUILQUÍ - POROTOG"
    ws1["A1"].font = font_title
    ws1["A1"].alignment = Alignment(horizontal="left", vertical="center")

    ws1.merge_cells("A2:W2")
    ws1["A2"] = "CONSORCIO CAYAMBE SPT · GOBIERNO AUTÓNOMO DESCENTRALIZADO MUNICIPAL DE CAYAMBE · PREFECTURA DE PICHINCHA"
    ws1["A2"].font = Font(name="Calibri", size=10, bold=True, color="2563EB")
    ws1["A2"].alignment = Alignment(horizontal="left", vertical="center")

    ws1.merge_cells("A3:W3")
    ws1["A3"] = "INVENTARIO MAESTRO DE PREDIOS INTERVENIDOS POR LA VÍA DE ACCESO A LA PRESA (CAD BERMA 1 - 6.00 M) · LONGITUD: 6.011,8 M · OCUPACIÓN: 35.451,1 M² (3,55 HA)"
    ws1["A3"].font = font_sub
    ws1["A3"].alignment = Alignment(horizontal="left", vertical="center")

    # Mini tarjetas de resumen (KPIs)
    kpis = [
        ("B5:C5", "B6:C6", "LONGITUD DE VÍA", "6.011,8 m (6,01 km)", "1E3A8A"),
        ("E5:F5", "E6:F6", "ANCHO CALZADA", "6,00 m (berma 1)", "0F766E"),
        ("H5:I5", "H6:I6", "ÁREA OCUPADA", "35.451,1 m² (3,55 ha)", "EA580C"),
        ("K5:L5", "K6:L6", "PREDIOS AFECTADOS", "28 predios", "2563EB"),
        ("N5:O5", "N6:O6", "PADRÓN DE RIEGO", "7 predios (430,7 m²)", "DC2626"),
        ("Q5:R5", "Q6:R6", "CATASTRO MUNICIPAL", "9 predios (871,1 m²)", "2563EB"),
        ("T5:U5", "T6:U6", "PÁRAMO / COMUNAL", "12 predios (34.149,4 m²)", "D97706"),
    ]
    for cell_title, cell_val, title, val, col_hex in kpis:
        ws1.merge_cells(cell_title)
        ws1.merge_cells(cell_val)
        top_c = ws1[cell_title.split(":")[0]]
        val_c = ws1[cell_val.split(":")[0]]
        top_c.value = title
        top_c.font = Font(name="Calibri", size=8.5, bold=True, color="64748B")
        top_c.alignment = Alignment(horizontal="center", vertical="center")
        val_c.value = val
        val_c.font = Font(name="Calibri", size=10, bold=True, color=col_hex)
        val_c.alignment = Alignment(horizontal="center", vertical="center")

    # Encabezados de tabla
    headers1 = [
        ("N°", 5, align_center),
        ("Clave Catastral GADM", 17, align_center),
        ("Condición Jurídica / Registro", 26, align_left),
        ("Propietario / Titular / Declarante", 34, align_left),
        ("Cédula / RUC", 13, align_center),
        ("Comunidad / Sector", 20, align_left),
        ("Código Ficha Padrón", 18, align_center),
        ("Régimen de Tenencia", 24, align_left),
        ("PK Inicial", 11, align_center),
        ("PK Final", 11, align_center),
        ("Tramo PK", 14, align_center),
        ("Longitud Eje (m)", 14, align_right),
        ("Área Predio (ha)", 14, align_right),
        ("Área Predio (m²)", 15, align_right),
        ("Área en Vía (m²)", 15, align_right),
        ("Área en Vía (ha)", 14, align_right),
        ("% Afectación", 13, align_right),
        ("Caudal Riego (l/s)", 15, align_right),
        ("Coord. UTM Este X", 16, align_right),
        ("Coord. UTM Norte Y", 17, align_right),
        ("Coord. WGS84 Lat", 15, align_right),
        ("Coord. WGS84 Lon", 15, align_right),
        ("Obras de Drenaje / Viales Cercanas", 34, align_left),
        ("Trámite / Recomendación Legal", 38, align_left),
    ]

    h1_row = 8
    ws1.row_dimensions[h1_row].height = 28
    for col_idx, (h_title, col_w, h_align) in enumerate(headers1, 1):
        c = ws1.cell(row=h1_row, column=col_idx, value=h_title)
        c.font = font_th
        c.fill = fill_th
        c.alignment = align_center
        c.border = border_cell
        ws1.column_dimensions[get_column_letter(col_idx)].width = col_w

    start_r = 9
    for i, p in enumerate(predios_enriquecidos, 1):
        r_idx = start_r + i - 1
        ws1.row_dimensions[r_idx].height = 20

        fuente = p.get("fuente_propietario")
        if fuente == "padron":
            row_fill = fill_padron
        elif fuente == "catastro_municipal":
            row_fill = fill_muni
        else:
            row_fill = fill_paramo

        area_pred_ha = p.get("area_predio_ha") or 0.0
        area_pred_m2 = area_pred_ha * 10000.0
        m2_via = p.get("m2_en_via") or 0.0
        ha_via = m2_via / 10000.0
        pct_afect = (m2_via / area_pred_m2) if area_pred_m2 > 0 else 0.0

        fila_val = [
            (i, align_center, None),
            (p["clave"], align_center, None),
            (p["condicion_cat"], align_left, None),
            (p.get("propietario") or p.get("nombre_predio") or "Sin titular registrado", align_left, None),
            (p.get("cedula") or "—", align_center, None),
            (p.get("comunidad") or "—", align_left, None),
            (p.get("codigo_ficha") or "—", align_center, None),
            (p.get("tenencia") or "—", align_left, None),
            (p["pk_inicio"], align_center, None),
            (p["pk_fin"], align_center, None),
            (p["tramo_pk"], align_center, None),
            (p.get("longitud_eje_m") or 0.0, align_right, "#,##0.0"),
            (area_pred_ha, align_right, "#,##0.00"),
            (area_pred_m2, align_right, "#,##0"),
            (m2_via, align_right, "#,##0.0"),
            (ha_via, align_right, "#,##0.0000"),
            (pct_afect, align_right, "0.00%"),
            (p.get("caudal_ls") if p.get("caudal_ls") else None, align_right, "#,##0.00"),
            (p["utm_x"], align_right, "#,##0.0"),
            (p["utm_y"], align_right, "#,##0.0"),
            (p["wgs_lat"], align_right, "0.000000"),
            (p["wgs_lon"], align_right, "0.000000"),
            (p["obras_cercanas"], align_left, None),
            (p["tramite"], align_left, None),
        ]

        for col_idx, (val, c_align, num_fmt) in enumerate(fila_val, 1):
            cell = ws1.cell(row=r_idx, column=col_idx, value=val)
            cell.font = font_data
            cell.fill = row_fill
            cell.alignment = c_align
            cell.border = border_cell
            if num_fmt:
                cell.number_format = num_fmt

    # Fila de Totales
    tot_row = start_r + len(predios_enriquecidos)
    ws1.row_dimensions[tot_row].height = 24

    for c_i in range(1, len(headers1) + 1):
        cell = ws1.cell(row=tot_row, column=c_i)
        cell.fill = fill_total
        cell.border = border_total_row

    ws1.cell(row=tot_row, column=4, value="TOTALES GENERALES:").font = font_total
    ws1.cell(row=tot_row, column=4).alignment = align_right

    # Fórmulas de sumatoria
    ws1.cell(row=tot_row, column=12, value=f"=SUM(L{start_r}:L{tot_row-1})").number_format = "#,##0.0"
    ws1.cell(row=tot_row, column=12).font = font_total
    ws1.cell(row=tot_row, column=12).alignment = align_right

    ws1.cell(row=tot_row, column=13, value=f"=SUM(M{start_r}:M{tot_row-1})").number_format = "#,##0.00"
    ws1.cell(row=tot_row, column=13).font = font_total
    ws1.cell(row=tot_row, column=13).alignment = align_right

    ws1.cell(row=tot_row, column=14, value=f"=SUM(N{start_r}:N{tot_row-1})").number_format = "#,##0"
    ws1.cell(row=tot_row, column=14).font = font_total
    ws1.cell(row=tot_row, column=14).alignment = align_right

    ws1.cell(row=tot_row, column=15, value=f"=SUM(O{start_r}:O{tot_row-1})").number_format = "#,##0.0"
    ws1.cell(row=tot_row, column=15).font = font_total
    ws1.cell(row=tot_row, column=15).alignment = align_right

    ws1.cell(row=tot_row, column=16, value=f"=SUM(P{start_r}:P{tot_row-1})").number_format = "#,##0.0000"
    ws1.cell(row=tot_row, column=16).font = font_total
    ws1.cell(row=tot_row, column=16).alignment = align_right

    ws1.cell(row=tot_row, column=17, value=f"=O{tot_row}/N{tot_row}").number_format = "0.00%"
    ws1.cell(row=tot_row, column=17).font = font_total
    ws1.cell(row=tot_row, column=17).alignment = align_right

    ws1.cell(row=tot_row, column=18, value=f"=SUM(R{start_r}:R{tot_row-1})").number_format = "#,##0.00"
    ws1.cell(row=tot_row, column=18).font = font_total
    ws1.cell(row=tot_row, column=18).alignment = align_right

    # Filtros automáticos y freeze
    ws1.auto_filter.ref = f"A{h1_row}:{get_column_letter(len(headers1))}{tot_row-1}"
    ws1.freeze_panes = "C9"

    # =========================================================================
    # HOJA 2: OBRAS VIALES Y DRENAJE
    # =========================================================================
    ws2 = wb.create_sheet(title="Obras Viales y Drenaje")
    ws2.views.sheetView[0].showGridLines = True

    ws2.merge_cells("A1:H1")
    ws2["A1"] = "INVENTARIO DE OBRAS DE DRENAJE Y ESTRUCTURAS VIALES PROYECTADAS (CAD)"
    ws2["A1"].font = font_title

    ws2.merge_cells("A2:H2")
    ws2["A2"] = "7 ALCANTARILLAS (ALC-06 A ALC-12) · CRUCE DE CANAL · MUROS H.A. · ÁREA DE MANIOBRA · CAMPAMENTO PRESA"
    ws2["A2"].font = font_sub

    headers2 = [
        ("N°", 5, align_center),
        ("Nombre de Estructura / Obra", 36, align_left),
        ("Tipo de Obra", 18, align_center),
        ("Progresiva (PK)", 16, align_center),
        ("Distancia Eje (m)", 15, align_right),
        ("Coord. UTM Este X", 16, align_right),
        ("Coord. UTM Norte Y", 17, align_right),
        ("Cota Z (msnm)", 14, align_right),
        ("Descripción / Detalle Técnico", 42, align_left),
    ]

    h2_row = 4
    ws2.row_dimensions[h2_row].height = 26
    for col_idx, (h_title, col_w, h_align) in enumerate(headers2, 1):
        c = ws2.cell(row=h2_row, column=col_idx, value=h_title)
        c.font = font_th
        c.fill = fill_th2
        c.alignment = align_center
        c.border = border_cell
        ws2.column_dimensions[get_column_letter(col_idx)].width = col_w

    for i, o in enumerate(obras_consolidadas, 1):
        r_idx = h2_row + i
        ws2.row_dimensions[r_idx].height = 20

        tipo_fmt = "Alcantarilla" if o["tipo_obra"] == "alcantarilla" else ("Campamento" if o["tipo_obra"] == "campamento" else "Estructura Vial")
        vals2 = [
            (i, align_center, None),
            (o["nombre"], align_left, None),
            (tipo_fmt, align_center, None),
            (o["pk"], align_center, None),
            (round(o["dist_eje"], 1), align_right, "#,##0.0"),
            (round(o["x"], 1), align_right, "#,##0.0"),
            (round(o["y"], 1), align_right, "#,##0.0"),
            (round(float(o["cota"]), 2) if o["cota"] else "—", align_right, "#,##0.00" if o["cota"] else None),
            (o["detalle"] or o["capa_cad"], align_left, None),
        ]
        for c_idx, (val, c_align, num_fmt) in enumerate(vals2, 1):
            cell = ws2.cell(row=r_idx, column=c_idx, value=val)
            cell.font = font_data
            cell.alignment = c_align
            cell.border = border_cell
            if num_fmt:
                cell.number_format = num_fmt

    ws2.auto_filter.ref = f"A{h2_row}:{get_column_letter(len(headers2))}{h2_row + len(obras_consolidadas)}"
    ws2.freeze_panes = "C5"

    # =========================================================================
    # HOJA 3: RESUMEN Y BALANCES
    # =========================================================================
    ws3 = wb.create_sheet(title="Resumen y Balances")
    ws3.views.sheetView[0].showGridLines = True

    ws3.merge_cells("A1:G1")
    ws3["A1"] = "BALANCE DE AFECTACIONES Y DISTRIBUCIÓN TERRITORIAL"
    ws3["A1"].font = font_title

    ws3.merge_cells("A2:G2")
    ws3["A2"] = "RESUMEN EJECUTIVO PARA LA PREFECTURA DE PICHINCHA, GADM CAYAMBE Y COMUNIDADES BENEFICIARIAS"
    ws3["A2"].font = font_sub

    # Tabla 1: Por Condición Jurídica
    ws3.cell(row=4, column=1, value="1. BALANCE POR CONDICIÓN JURÍDICA").font = font_sec
    h_res1 = ["Condición Jurídica", "N° Predios", "% Predios", "Área en Vía (m²)", "Área en Vía (ha)", "% Ocupación Vía", "Longitud Eje (m)"]
    ws3.row_dimensions[5].height = 24
    for c_i, h in enumerate(h_res1, 1):
        c = ws3.cell(row=5, column=c_i, value=h)
        c.font = font_th
        c.fill = fill_th
        c.alignment = align_center
        c.border = border_cell

    filas_cond = [
        ("Predios con Ficha del Padrón de Regantes", 7, 7/28, 430.7, 430.7/10000, 430.7/35451.1, sum(p.get("longitud_eje_m",0) for p in predios_enriquecidos if p["fuente_propietario"]=="padron")),
        ("Predios con Titular Catastral Municipal GADM", 9, 9/28, 871.1, 871.1/10000, 871.1/35451.1, sum(p.get("longitud_eje_m",0) for p in predios_enriquecidos if p["fuente_propietario"]=="catastro_municipal")),
        ("Áreas Comunales / Páramo (Sin titular registrado)", 12, 12/28, 34149.4, 34149.4/10000, 34149.4/35451.1, sum(p.get("longitud_eje_m",0) for p in predios_enriquecidos if not p.get("fuente_propietario"))),
    ]

    for idx, (nombre, cant, pct_p, m2, ha, pct_v, m_eje) in enumerate(filas_cond, 6):
        ws3.cell(row=idx, column=1, value=nombre).alignment = align_left
        ws3.cell(row=idx, column=2, value=cant).alignment = align_center
        ws3.cell(row=idx, column=3, value=pct_p).number_format = "0.00%"
        ws3.cell(row=idx, column=3).alignment = align_right
        ws3.cell(row=idx, column=4, value=m2).number_format = "#,##0.0"
        ws3.cell(row=idx, column=4).alignment = align_right
        ws3.cell(row=idx, column=5, value=ha).number_format = "#,##0.0000"
        ws3.cell(row=idx, column=5).alignment = align_right
        ws3.cell(row=idx, column=6, value=pct_v).number_format = "0.00%"
        ws3.cell(row=idx, column=6).alignment = align_right
        ws3.cell(row=idx, column=7, value=m_eje).number_format = "#,##0.0"
        ws3.cell(row=idx, column=7).alignment = align_right

        for ci in range(1, 8):
            ws3.cell(row=idx, column=ci).border = border_cell
            ws3.cell(row=idx, column=ci).font = font_data

    # Totales T1
    t1_row = 9
    ws3.cell(row=t1_row, column=1, value="TOTAL GENERAL:").font = font_total
    ws3.cell(row=t1_row, column=2, value="=SUM(B6:B8)").alignment = align_center
    ws3.cell(row=t1_row, column=3, value="=SUM(C6:C8)").number_format = "0.00%"
    ws3.cell(row=t1_row, column=3).alignment = align_right
    ws3.cell(row=t1_row, column=4, value="=SUM(D6:D8)").number_format = "#,##0.0"
    ws3.cell(row=t1_row, column=4).alignment = align_right
    ws3.cell(row=t1_row, column=5, value="=SUM(E6:E8)").number_format = "#,##0.0000"
    ws3.cell(row=t1_row, column=5).alignment = align_right
    ws3.cell(row=t1_row, column=6, value="=SUM(F6:F8)").number_format = "0.00%"
    ws3.cell(row=t1_row, column=6).alignment = align_right
    ws3.cell(row=t1_row, column=7, value="=SUM(G6:G8)").number_format = "#,##0.0"
    ws3.cell(row=t1_row, column=7).alignment = align_right

    for ci in range(1, 8):
        c = ws3.cell(row=t1_row, column=ci)
        c.font = font_total
        c.fill = fill_total
        c.border = border_total_row

    # Tabla 2: Por Comunidad / Sector
    ws3.cell(row=12, column=1, value="2. BALANCE POR COMUNIDAD O SECTOR TERRITORIAL").font = font_sec
    ws3.row_dimensions[13].height = 24
    h_res2 = ["Comunidad o Sector Territorial", "N° Predios", "% Predios", "Área en Vía (m²)", "Área en Vía (ha)", "% Ocupación Vía", "Longitud Eje (m)"]
    for c_i, h in enumerate(h_res2, 1):
        c = ws3.cell(row=13, column=c_i, value=h)
        c.font = font_th
        c.fill = fill_th3
        c.alignment = align_center
        c.border = border_cell

    comunidades_agg = {}
    for p in predios_enriquecidos:
        com = p.get("comunidad") or "Páramo Chico / Comunal"
        if "IZACATA GRANDE" in com.upper():
            com_canon = "Izacata Grande"
        elif "LOS ANDES" in com.upper():
            com_canon = "Los Andes de Izacata"
        elif "COMUNA IZACATA" in com.upper() or "COMUNIDAD IZACATA" in com.upper():
            com_canon = "Comuna Izacata"
        else:
            com_canon = "Páramo Chico / Terreno Comunal"

        if com_canon not in comunidades_agg:
            comunidades_agg[com_canon] = {"count": 0, "m2": 0.0, "eje": 0.0}
        comunidades_agg[com_canon]["count"] += 1
        comunidades_agg[com_canon]["m2"] += (p.get("m2_en_via") or 0.0)
        comunidades_agg[com_canon]["eje"] += (p.get("longitud_eje_m") or 0.0)

    for idx, (com_nom, data) in enumerate(sorted(comunidades_agg.items(), key=lambda x: -x[1]["m2"]), 14):
        ws3.cell(row=idx, column=1, value=com_nom).alignment = align_left
        ws3.cell(row=idx, column=2, value=data["count"]).alignment = align_center
        ws3.cell(row=idx, column=3, value=data["count"]/28).number_format = "0.00%"
        ws3.cell(row=idx, column=3).alignment = align_right
        ws3.cell(row=idx, column=4, value=data["m2"]).number_format = "#,##0.0"
        ws3.cell(row=idx, column=4).alignment = align_right
        ws3.cell(row=idx, column=5, value=data["m2"]/10000.0).number_format = "#,##0.0000"
        ws3.cell(row=idx, column=5).alignment = align_right
        ws3.cell(row=idx, column=6, value=data["m2"]/35451.1).number_format = "0.00%"
        ws3.cell(row=idx, column=6).alignment = align_right
        ws3.cell(row=idx, column=7, value=data["eje"]).number_format = "#,##0.0"
        ws3.cell(row=idx, column=7).alignment = align_right

        for ci in range(1, 8):
            ws3.cell(row=idx, column=ci).border = border_cell
            ws3.cell(row=idx, column=ci).font = font_data

    last_com_row = 13 + len(comunidades_agg)
    t2_row = last_com_row + 1
    ws3.cell(row=t2_row, column=1, value="TOTAL GENERAL:").font = font_total
    ws3.cell(row=t2_row, column=2, value=f"=SUM(B14:B{last_com_row})").alignment = align_center
    ws3.cell(row=t2_row, column=3, value=f"=SUM(C14:C{last_com_row})").number_format = "0.00%"
    ws3.cell(row=t2_row, column=3).alignment = align_right
    ws3.cell(row=t2_row, column=4, value=f"=SUM(D14:D{last_com_row})").number_format = "#,##0.0"
    ws3.cell(row=t2_row, column=4).alignment = align_right
    ws3.cell(row=t2_row, column=5, value=f"=SUM(E14:E{last_com_row})").number_format = "#,##0.0000"
    ws3.cell(row=t2_row, column=5).alignment = align_right
    ws3.cell(row=t2_row, column=6, value=f"=SUM(F14:F{last_com_row})").number_format = "0.00%"
    ws3.cell(row=t2_row, column=6).alignment = align_right
    ws3.cell(row=t2_row, column=7, value=f"=SUM(G14:G{last_com_row})").number_format = "#,##0.0"
    ws3.cell(row=t2_row, column=7).alignment = align_right

    for ci in range(1, 8):
        c = ws3.cell(row=t2_row, column=ci)
        c.font = font_total
        c.fill = fill_total
        c.border = border_total_row

    for c_i, w in enumerate([36, 12, 12, 18, 18, 18, 18], 1):
        ws3.column_dimensions[get_column_letter(c_i)].width = w

    # Guardar ambos libros
    wb.save(OUTPUT_WEB)
    wb.save(OUTPUT_CARTO)
    print(f"✔ Libro Excel generado con éxito en:")
    print(f"  - Web: {OUTPUT_WEB}")
    print(f"  - Cartografía: {OUTPUT_CARTO}")

if __name__ == "__main__":
    generar_excel()
