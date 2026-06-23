import os
import pypdf
import re
import json

pdf_path = r"C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO\FACTURA AGUA RIEGO 1.pdf"
out_json = r"C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO\padron-app\scratch\regantes_factura.json"

reader = pypdf.PdfReader(pdf_path)
text = ""
for page in reader.pages:
    text += page.extract_text() or ""

# Guardar texto crudo para inspeccion si es necesario
with open(r"C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO\padron-app\scratch\pdf_raw_text.txt", "w", encoding="utf-8") as f:
    f.write(text)

lines = text.split("\n")
regantes = []

# Expresion regular para buscar lineas que comiencen con un numero (el indice de la lista)
# Ejemplos:
# 1 Almeida Esthela 171186517-8 $ 2.00 $ 2.00
# 2 Almeida Tomasa $ 2.00 $ 2.00
# 34 Cuascota Cabascango Pablo 175043732-7 $ 2
# 102 Bastidas Carlos ...
pattern = re.compile(r"^(\d+)\s+([A-Za-z\s\.\u00C0-\u017F]+?)(?:\s+(\d{9,10}-\d|\d{9,10}))?\s+(\$.*)$")
# Nota: Tambien puede haber lineas donde no hay signo de dolar al final, o tiene otro formato.
# Intentemos con un parser por linea mas flexible.

for line in lines:
    line = line.strip()
    if not line:
        continue
    
    # Comprobar si empieza con un numero seguido de espacio
    match_num = re.match(r"^(\d+)\s+(.*)$", line)
    if match_num:
        num = int(match_num.group(1))
        rest = match_num.group(2).strip()
        
        # Intentar extraer la cedula
        # La cedula suele tener el patron: 171186517-8 o 100207658-4 o similar
        cedula_match = re.search(r"(\d{9,10}-\d|\d{8,10})", rest)
        cedula = ""
        nombre_part = rest
        
        if cedula_match:
            cedula = cedula_match.group(1)
            # El nombre es todo lo anterior a la cedula
            nombre_part = rest.split(cedula)[0].strip()
        else:
            # Si no hay cedula, el nombre es todo lo anterior a la parte de dinero (que empieza con $)
            if "$" in rest:
                nombre_part = rest.split("$")[0].strip()
            else:
                # Si no hay $, buscar donde empieza el primer numero o simbolo
                num_search = re.search(r"\d", rest)
                if num_search:
                    nombre_part = rest[:num_search.start()].strip()
        
        # Limpiar nombre
        # Si termina en puntos o espacios raros
        nombre = nombre_part.strip()
        
        # Guardar regante
        regantes.append({
            "idx": num,
            "nombre_completo": nombre,
            "cedula": cedula,
            "raw_line": line
        })

print(f"Total lineas parsed: {len(regantes)}")
print("Primeros 5 regantes:")
for r in regantes[:5]:
    print(r)

print("\nUltimos 5 regantes:")
for r in regantes[-5:]:
    print(r)

# Guardar en archivo JSON
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(regantes, f, indent=2, ensure_ascii=False)

print(f"\nDatos guardados en JSON: {out_json}")
