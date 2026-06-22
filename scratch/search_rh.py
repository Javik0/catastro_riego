import os

base_dir = r"c:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO"

for root, dirs, files in os.walk(base_dir):
    if "node_modules" in root or ".git" in root or "dist" in root:
        continue
    for file in files:
        if file.endswith((".md", ".txt", ".py", ".json", ".tsx", ".ts")):
            path = os.path.join(root, file)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                if " rh " in content.lower() or "rh:" in content.lower() or " rh." in content.lower() or "recurso hídrico" in content.lower() or "recursos hidricos" in content.lower() or "red hidrografica" in content.lower():
                    print(f"Match in {path}")
            except Exception:
                pass
