"""Capturas de una lista de cámaras, en borrador (rápido, para revisar) o final (2K para el cliente).
Lo normal es lanzarlo con scripts/render.ps1, que además baja la prioridad para que la laptop siga usable:

    blender --background BaseSucre.blend --python capturas_hoy.py -- <carpeta> "Cam_A:nombre,Cam_B:nombre" [borrador|final]

Sin lista usa TOMAS. Salta las imágenes que ya existen (borrar el PNG para rehacerla).
"""
import os
import sys
import time

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_ligero as RL  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOMAS = [("Cam_Entrada_Dron", "entrada_y_plaza_desde_arriba"), ("Cam_Adentro_Portada", "portada_desde_adentro"),
         ("Cam_Entrada_Avion", "entrada_con_el_avion"), ("Cam_Comedor", "comedor_completo"),
         ("Cam_DIDA", "dida")]
_a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
carpeta = _a[0] if _a else "borrador"
if len(_a) >= 2 and _a[1]:
    TOMAS = [tuple(x.split(":")) for x in _a[1].split(",")]
borrador = (_a[2] if len(_a) >= 3 else "borrador") != "final"
sc = bpy.context.scene
RL.calidad(sc, borrador)
out = os.path.join(RAIZ, "renders", carpeta)
os.makedirs(out, exist_ok=True)
print("modo:", "borrador 1280x720" if borrador else "final 2560x1440", "→", out, flush=True)
for i, (cam, nombre) in enumerate(TOMAS, 1):
    ob = bpy.data.objects.get(cam)
    ruta = os.path.join(out, f"{i:02d}_{nombre}.png")
    if ob is None or os.path.exists(ruta):
        print("salto", cam, flush=True)
        continue
    sc.camera = ob
    sc.render.filepath = ruta
    t = time.time()
    with RL.recorte(sc, ob):
        bpy.ops.render.render(write_still=True)
    print("captura", ruta, "%.0f s" % (time.time() - t), flush=True)
