"""Descarga de Poly Haven (CC0) el cielo HDRI, la vegetación en 3D y más texturas PBR.

    python bajar_assets.py <carpeta del proyecto BaseSucre3D>

Queda en assets/hdri, assets/modelos/<nombre>/ (el .blend con sus texturas) y texturas/<nombre>/ (como
bajar_texturas.py). No vuelve a bajar lo que ya está.
"""
import json, os, sys, urllib.request

RAIZ = sys.argv[1]
UA = {"User-Agent": "BaseSucre3D/1.0"}
HDRI = ("kloofendal_48d_partly_cloudy_puresky", "4k")
MODELOS = ("island_tree_02", "searsia_lucida", "shrub_02", "shrub_03", "shrub_04", "grass_bermuda_01")
TEXTURAS = {"ladrillo": "red_brick_03", "friso": "painted_plaster_wall", "lamina_gastada": "worn_corrugated_iron",
            "lamina_oxidada": "rusty_corrugated_iron", "concreto_gastado": "concrete_floor_worn_001"}
MAPAS = {"Diffuse": "color", "nor_gl": "normal", "Rough": "rugosidad"}


def api(ruta):
    return json.load(urllib.request.urlopen(urllib.request.Request("https://api.polyhaven.com/" + ruta, headers=UA),
                                            timeout=60))


total = 0


def bajar(url, ruta):
    global total
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    if not os.path.exists(ruta):
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r, open(ruta, "wb") as f:
            f.write(r.read())
    total += os.path.getsize(ruta)


def fuente(carpeta, activo):
    with open(os.path.join(carpeta, "FUENTE.txt"), "w", encoding="utf-8") as f:
        f.write(f"Poly Haven · {activo} · licencia CC0 · https://polyhaven.com/a/{activo}\n")


nombre, res = HDRI
info = api("files/" + nombre)["hdri"][res]["hdr"]
carpeta = os.path.join(RAIZ, "assets", "hdri")
bajar(info["url"], os.path.join(carpeta, f"{nombre}_{res}.hdr"))
fuente(carpeta, nombre)
print("hdri", nombre)

for m in MODELOS:
    b = api("files/" + m)["blend"]["1k"]["blend"]
    carpeta = os.path.join(RAIZ, "assets", "modelos", m)
    bajar(b["url"], os.path.join(carpeta, os.path.basename(b["url"])))
    for rel, inc in b.get("include", {}).items():
        bajar(inc["url"], os.path.join(carpeta, rel))
    fuente(carpeta, m)
    print("modelo", m)

for nombre, activo in TEXTURAS.items():
    info = api("files/" + activo)
    carpeta = os.path.join(RAIZ, "texturas", nombre)
    for clave, mapa in MAPAS.items():
        bajar(info[clave]["2k"]["jpg"]["url"], os.path.join(carpeta, f"{mapa}.jpg"))
    fuente(carpeta, activo)
    print("textura", nombre, activo)
print(f"total en disco {total / 1e6:.0f} MB")
