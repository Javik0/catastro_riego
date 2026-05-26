# -*- coding: utf-8 -*-
"""
Sincronizar y optimizar fotografías del catastro a Firebase Storage.
Comprime las imágenes de alta resolución a ~120KB y las sube al bucket.

Requisitos:
  pip install Pillow google-cloud-storage
"""

import os
import sys
import json
import io

# Asegurar codificación UTF-8 para evitar errores de consola en Windows
sys.stdout.reconfigure(encoding='utf-8')

# Directorios y Configuración
QFIELD_DCIM_DIR = r'C:\Users\HP\QField\cloud\porotog_levantamiento_offline\DCIM'
KEY_FILE = 'firebase-key.json'
BUCKET_NAME = 'invs-riego-comunitario.firebasestorage.app'
LOG_FILE = os.path.join(os.path.dirname(__file__), 'photos_sync_log.json')

def main():
    print("═" * 60)
    print("  SINCRONIZACIÓN DE FOTOS → Firebase Storage")
    print("═" * 60)

    # 1. Verificar presencia de firebase-key.json
    if not os.path.exists(KEY_FILE):
        print("\n⚠  ADVERTENCIA: No se encontró 'firebase-key.json' en la raíz de 'padron-app'.")
        print("   Se omitirá la sincronización de fotos a la nube.")
        print("   Para activar las fotos en el reporte, consulta las instrucciones en 'implementation_plan.md'.\n")
        sys.exit(0)

    # 2. Verificar que exista la carpeta DCIM de QField
    if not os.path.exists(QFIELD_DCIM_DIR):
        print(f"\n❌ ERROR: No se encontró la carpeta de fotos en: {QFIELD_DCIM_DIR}")
        print("   Verifica que la carpeta exista o que QFieldCloud esté sincronizado localmente.")
        sys.exit(0)

    # 3. Intentar importar o instalar dependencias necesarias
    try:
        from PIL import Image
        from google.cloud import storage
    except ImportError:
        print("\n📦 Instalandos dependencias requeridas (Pillow, google-cloud-storage)...")
        import subprocess
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow", "google-cloud-storage"])
            from PIL import Image
            from google.cloud import storage
            print("✓ Dependencias instaladas con éxito.")
        except Exception as e:
            print(f"❌ ERROR: No se pudieron instalar las dependencias automáticamente. Detalle: {e}")
            print("   Por favor ejecuta manualmente: pip install Pillow google-cloud-storage")
            sys.exit(1)

    # 4. Leer el log local de fotos ya sincronizadas
    sync_log = {}
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                sync_log = json.load(f)
        except:
            pass

    # 5. Obtener lista de imágenes en la carpeta DCIM
    valid_extensions = ('.jpg', '.jpeg', '.png')
    all_files = [f for f in os.listdir(QFIELD_DCIM_DIR) if f.lower().endswith(valid_extensions)]
    
    if not all_files:
        print("\nℹ  No se encontraron fotos en la carpeta DCIM de QField.")
        sys.exit(0)

    # Filtrar las fotos que no han sido subidas
    pending_files = [f for f in all_files if f not in sync_log]
    
    print(f"\n📸 Total fotos en DCIM local: {len(all_files)}")
    print(f"🔄 Fotos ya sincronizadas anteriormente: {len(all_files) - len(pending_files)}")
    print(f"🚀 Fotos nuevas pendientes de subir: {len(pending_files)}")

    if not pending_files:
        print("\n✅ Todas las fotos están al día. No se requiere subir archivos.")
        sys.exit(0)

    # 6. Conectar a Firebase Storage
    print("\n🔐 Conectando a Firebase Storage...")
    try:
        storage_client = storage.Client.from_service_account_json(KEY_FILE)
        bucket = storage_client.bucket(BUCKET_NAME)
    except Exception as e:
        print(f"❌ ERROR de conexión: No se pudo leer el archivo de claves o conectar a Firebase. Detalle: {e}")
        sys.exit(1)

    # 7. Procesar y subir cada foto pendiente
    uploaded_count = 0
    errors_count = 0

    for idx, filename in enumerate(pending_files, 1):
        local_path = os.path.join(QFIELD_DCIM_DIR, filename)
        
        # Saltarse archivos vacíos o directorios
        if not os.path.isfile(local_path) or os.path.getsize(local_path) == 0:
            continue

        print(f"[{idx}/{len(pending_files)}] Procesando {filename}...", end="", flush=True)

        try:
            # A. Comprimir y redimensionar imagen en memoria
            img = Image.open(local_path)
            
            # Corregir orientación EXIF si existe
            try:
                from PIL import ImageOps
                img = ImageOps.exif_transpose(img)
            except:
                pass

            # Redimensionar a un máx de 1024px de ancho/alto manteniendo proporción
            img.thumbnail((1024, 1024))
            
            # Guardar en buffer en formato JPEG
            img_buffer = io.BytesIO()
            img.convert('RGB').save(img_buffer, format='JPEG', quality=80, optimize=True)
            img_buffer.seek(0)
            
            size_kb = len(img_buffer.getbuffer()) / 1024

            # B. Subir a Firebase Storage
            blob_path = f"fotos_predios/{filename}"
            blob = bucket.blob(blob_path)
            
            # Subir directamente desde el buffer de memoria
            blob.upload_from_file(img_buffer, content_type='image/jpeg')
            
            # Guardar en log local
            sync_log[filename] = {
                "size_kb": round(size_kb, 1),
                "timestamp": blob.updated.isoformat() if blob.updated else ""
            }
            
            # Guardar log tras cada subida para poder reanudar si se cancela
            with open(LOG_FILE, 'w', encoding='utf-8') as f:
                json.dump(sync_log, f, ensure_ascii=False, indent=2)

            print(f" OK (~{size_kb:.1f} KB)")
            uploaded_count += 1

        except Exception as e:
            print(f" ERROR: {e}")
            errors_count += 1

    print("\n" + "═" * 60)
    print(f"  ✅ SINCRONIZACIÓN FINALIZADA")
    print(f"  📈 Subidas con éxito: {uploaded_count}")
    print(f"  ❌ Fallidas/Con error: {errors_count}")
    print("═" * 60 + "\n")

if __name__ == '__main__':
    main()
