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

# Lista de técnicos a crear
tecnicos = [
    {
        "nombre": "Melany Jara",
        "email": "melany.jara@consorcio-cayambe.ec",
        "password": "MelanyJara2026!",
        "qfield_users": ["u0_a314", "u0_a319", "jvk-editor"]
    },
    {
        "nombre": "Adriana Cuascota",
        "email": "adriana.cuascota@consorcio-cayambe.ec",
        "password": "AdrianaCuascota2026!",
        "qfield_users": ["u0_a504", "jvk-editor6"]
    },
    {
        "nombre": "Huguito Ipial",
        "email": "hugo.ipial@consorcio-cayambe.ec",
        "password": "HuguitoIpial2026!",
        "qfield_users": ["u0_a279", "jvk-editor2"]
    },
    {
        "nombre": "Pablo Barrionuevo",
        "email": "pablo.barrionuevo@consorcio-cayambe.ec",
        "password": "PabloBarrionuevo2026!",
        "qfield_users": ["u0_a70", "jvk-editor5"]
    },
    {
        "nombre": "Mayra Benavides",
        "email": "mayra.benavides@consorcio-cayambe.ec",
        "password": "MayraBenavides2026!",
        "qfield_users": ["u0_a330", "mayralisseth201"]
    },
    {
        "nombre": "Martha Simbana",
        "email": "martha.simbana@consorcio-cayambe.ec",
        "password": "MarthaSimbana2026!",
        "qfield_users": ["u0_a362", "u0_a335", "jvk-editor4"]
    },
    {
        "nombre": "Dylan Chavez",
        "email": "dylan.chavez@consorcio-cayambe.ec",
        "password": "DylanChavez2026!",
        "qfield_users": ["u0_a302", "jvk-editor3"]
    },
    {
        "nombre": "Melanie2",
        "email": "melanie2@consorcio-cayambe.ec",
        "password": "Melanie2026!",
        "qfield_users": ["u0_a200"]
    }
]

print("=== PROCESANDO CREACION DE TECNICOS EN FIREBASE ===")
print("-" * 60)

reporte = []

for t in tecnicos:
    email = t["email"]
    password = t["password"]
    nombre = t["nombre"]
    uid = None
    status = ""
    
    # 1. Crear o recuperar el usuario en Auth
    try:
        user = auth.create_user(
            email=email,
            password=password,
            display_name=nombre
        )
        uid = user.uid
        status = "CREADO (Auth)"
    except auth.EmailAlreadyExistsError:
        user = auth.get_user_by_email(email)
        uid = user.uid
        status = "YA EXISTIA (Auth)"
    except Exception as e:
        print(f"Error al procesar en Auth a {nombre} ({email}): {e}")
        continue

    # 2. Registrar/Actualizar en la coleccion 'usuarios' de Firestore
    try:
        user_ref = db.collection('usuarios').document(uid)
        user_ref.set({
            "uid": uid,
            "email": email,
            "nombre": nombre,
            "rol": "tecnico"
        }, merge=True)
        print(f"OK: {nombre} | {email} | {status} | Registrado en Firestore con rol 'tecnico'")
        
        reporte.append({
            "nombre": nombre,
            "email": email,
            "password": password,
            "qfield_users": ", ".join(t["qfield_users"])
        })
    except Exception as e:
        print(f"Error al registrar en Firestore a {nombre} ({email}): {e}")

print("-" * 60)
print("=== DEPURACION DE CREDENCIALES COMPLETADA ===")

# Imprimir reporte formateado en texto plano
print("\n=== CREDENCIALES DE ACCESO PARA LOS TECNICOS ===")
print("Comparte estas credenciales con cada tecnico investigador:\n")
for idx, r in enumerate(reporte, 1):
    print(f"{idx}. Tecnico: {r['nombre']} (Mapeo QField: {r['qfield_users']})")
    print(f"   - Correo:     {r['email']}")
    print(f"   - Contrasena: {r['password']}")
    print("-" * 50)
