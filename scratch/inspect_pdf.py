import os

pdf_path = r"C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO\FACTURA AGUA RIEGO 1.pdf"

print(f"Existe PDF: {os.path.exists(pdf_path)}")
if os.path.exists(pdf_path):
    print(f"Size: {os.path.getsize(pdf_path)} bytes")

# Probar pypdf, pdfplumber, fitz
libs = ["pypdf", "pdfplumber", "fitz", "PyPDF2"]
available = {}
for lib in libs:
    try:
        __import__(lib)
        available[lib] = True
        print(f"Lib {lib}: disponible")
    except ImportError:
        available[lib] = False
        print(f"Lib {lib}: no disponible")

# Intentar leer el PDF con la primera disponible
text = ""
if available.get("pdfplumber"):
    import pdfplumber
    print("Leyendo con pdfplumber...")
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
elif available.get("pypdf"):
    import pypdf
    print("Leyendo con pypdf...")
    reader = pypdf.PdfReader(pdf_path)
    for page in reader.pages:
        text += page.extract_text() or ""
elif available.get("fitz"):
    import fitz
    print("Leyendo con fitz...")
    doc = fitz.open(pdf_path)
    for page in doc:
        text += page.get_text() or ""
elif available.get("PyPDF2"):
    import PyPDF2
    print("Leyendo con PyPDF2...")
    reader = PyPDF2.PdfReader(pdf_path)
    for page in reader.pages:
        text += page.extract_text() or ""

if text:
    print("Texto extraido con exito. Longitud:", len(text))
    # Imprimir los primeros 1000 caracteres de forma segura
    ascii_text = text[:1500].encode('ascii', 'ignore').decode('ascii')
    print("--- MUESTRA ---")
    print(ascii_text)
    print("---------------")
else:
    print("No se pudo extraer texto o el PDF esta vacio/escaneado como imagen.")
