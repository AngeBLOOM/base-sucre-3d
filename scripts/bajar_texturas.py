"""Descarga de Poly Haven (CC0) las texturas PBR de la escena: color, normal (OpenGL) y rugosidad a 2K."""
import json, os, sys, urllib.request

ACTIVOS = {
    "asfalto": "asphalt_02",
    "pasto": "leafy_grass",
    "acera": "concrete_pavement",
    "pared": "white_plaster_02",
    "lamina": "corrugated_iron",
}
MAPAS = {"Diffuse": "color", "nor_gl": "normal", "Rough": "rugosidad"}
DESTINO = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "texturas")
UA = {"User-Agent": "BaseSucre3D/1.0"}


def bajar(url, ruta):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r, open(ruta, "wb") as f:
        f.write(r.read())


total = 0
for nombre, activo in ACTIVOS.items():
    info = json.load(urllib.request.urlopen(
        urllib.request.Request(f"https://api.polyhaven.com/files/{activo}", headers=UA), timeout=60))
    carpeta = os.path.join(DESTINO, nombre)
    os.makedirs(carpeta, exist_ok=True)
    for clave, mapa in MAPAS.items():
        url = info[clave]["2k"]["jpg"]["url"]
        ruta = os.path.join(carpeta, f"{mapa}.jpg")
        bajar(url, ruta)
        total += os.path.getsize(ruta)
        print(f"{nombre:8} {mapa:9} {os.path.getsize(ruta) // 1024:6} KB  {url}")
    with open(os.path.join(carpeta, "FUENTE.txt"), "w", encoding="utf-8") as f:
        f.write(f"Poly Haven · {activo} · licencia CC0 · https://polyhaven.com/a/{activo}\n")
print(f"total {total / 1e6:.1f} MB")
