import firebase_admin
from firebase_admin import credentials
from firebase_admin import auth
from firebase_admin import firestore
import os

key_path = r"c:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO\padron-app\firebase-key.json"

if not os.path.exists(key_path):
    print("Error: No se encontro firebase-key.json")
    exit()

# Inicializar Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate(key_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Nuevo dominio a crear (usamos guion medio para cumplir con la sintaxis de correo de Firebase)
nuevo_dominio = "proyectos-apcatastros.ec"

# Lista de técnicos a crear
tecnicos = [
    {
        "nombre": "Melany Jara",
        "username": "melany.jara",
        "password": "MelanyJara2026!",
        "qfield_users": ["u0_a314", "u0_a319", "jvk-editor"]
    },
    {
        "nombre": "Adriana Cuascota",
        "username": "adriana.cuascota",
        "password": "AdrianaCuascota2026!",
        "qfield_users": ["u0_a504", "jvk-editor6"]
    },
    {
        "nombre": "Huguito Ipial",
        "username": "hugo.ipial",
        "password": "HuguitoIpial2026!",
        "qfield_users": ["u0_a279", "jvk-editor2"]
    },
    {
        "nombre": "Pablo Barrionuevo",
        "username": "pablo.barrionuevo",
        "password": "PabloBarrionuevo2026!",
        "qfield_users": ["u0_a70", "jvk-editor5"]
    },
    {
        "nombre": "Mayra Benavides",
        "username": "mayra.benavides",
        "password": "MayraBenavides2026!",
        "qfield_users": ["u0_a330", "mayralisseth201"]
    },
    {
        "nombre": "Martha Simbana",
        "username": "martha.simbana",
        "password": "MarthaSimbana2026!",
        "qfield_users": ["u0_a362", "u0_a335", "jvk-editor4"]
    },
    {
        "nombre": "Dylan Chavez",
        "username": "dylan.chavez",
        "password": "DylanChavez2026!",
        "qfield_users": ["u0_a302", "jvk-editor3"]
    },
    {
        "nombre": "Melanie2",
        "username": "melanie2",
        "password": "Melanie2026!",
        "qfield_users": ["u0_a200"]
    }
]

print("=== CREANDO CUENTAS CON EL DOMINIO CORREGIDO (proyectos-apcatastros.ec) ===")
print("-" * 60)

reporte = []

for t in tecnicos:
    email_nuevo = f"{t['username']}@{nuevo_dominio}"
    password = t["password"]
    nombre = t["nombre"]
    uid = None
    status = ""
    
    # 1. Crear o recuperar el usuario en Auth
    try:
        user = auth.create_user(
            email=email_nuevo,
            password=password,
            display_name=nombre
        )
        uid = user.uid
        status = "CREADO (Auth)"
    except auth.EmailAlreadyExistsError:
        user = auth.get_user_by_email(email_nuevo)
        uid = user.uid
        status = "YA EXISTIA (Auth)"
    except Exception as e:
        print(f"Error al procesar en Auth a {nombre} ({email_nuevo}): {e}")
        continue

    # 2. Registrar/Actualizar en la coleccion 'usuarios' de Firestore
    try:
        user_ref = db.collection('usuarios').document(uid)
        user_ref.set({
            "uid": uid,
            "email": email_nuevo,
            "nombre": nombre,
            "rol": "tecnico"
        }, merge=True)
        print(f"OK: {nombre} | {email_nuevo} | {status} | Registrado en Firestore con rol 'tecnico'")
        
        reporte.append({
            "nombre": nombre,
            "email": email_nuevo,
            "password": password,
            "qfield_users": ", ".join(t["qfield_users"])
        })
    except Exception as e:
        print(f"Error al registrar en Firestore a {nombre} ({email_nuevo}): {e}")

print("-" * 60)
print("=== PROCESAMIENTO COMPLETADO ===")

# Imprimir reporte formateado en texto plano
print("\n=== CREDENCIALES ACTUALIZADAS CON DOMINIO: " + nuevo_dominio + " ===")
print("Comparte estas credenciales con cada tecnico investigador:\n")
for idx, r in enumerate(reporte, 1):
    print(f"{idx}. Tecnico: {r['nombre']} (Mapeo QField: {r['qfield_users']})")
    print(f"   - Correo:     {r['email']}")
    print(f"   - Contrasena: {r['password']}")
    print("-" * 50)
