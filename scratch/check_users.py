import firebase_admin
from firebase_admin import credentials
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

print("=== LISTA DE DOCUMENTOS EN LA COLECCION 'usuarios' ===")
users_ref = db.collection('usuarios')
docs = users_ref.stream()

count = 0
for doc in docs:
    count += 1
    data = doc.to_dict()
    print(f"{count}. Documento ID (UID): {doc.id}")
    print(f"   Nombre: {data.get('nombre')}")
    print(f"   Email:  {data.get('email')}")
    print(f"   Rol:    {data.get('rol')}")
    print("-" * 50)

if count == 0:
    print("No hay usuarios registrados en la coleccion 'usuarios'.")
