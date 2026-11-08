"""Render que gasta menos la laptop (i5 + Iris Xe, 8 GB):

- calidad «borrador» (para revisar): 1280 x 720, 24 muestras, sombras y GI rápidas más simples → ~5 veces menos
  trabajo por imagen que la final (2560 x 1440, 96 muestras);
- recorte por cámara: en cada toma a nivel de suelo se apaga lo que queda lejos y no se distingue (pasto 3D a más de
  180 m, plantas a más de 450 m, edificios a más de 1,6 km). Las tomas altas (dron, aérea, sierra) no se recortan.

    import render_ligero as RL
    RL.calidad(scene, borrador=True)
    with RL.recorte(scene, cam): bpy.ops.render.render(...)
"""
import contextlib

import bpy
from mathutils import Vector

SIEMPRE = ("Terreno", "Paisaje_lejano", "Paisaje_regional")
LIMITES = (("Pasto3d", 180.0), ("Arbol", 450.0), ("Planta", 300.0), ("Mata", 300.0), ("Palma", 600.0),
           ("Bismarck", 450.0), ("Troncos_cal", 450.0))
LEJOS = 1600.0
ALTURA_SIN_RECORTE = 60.0                   # cámaras más altas que esto sobre el terreno: tomas aéreas


def calidad(sc, borrador):
    sc.view_settings.exposure = max(sc.view_settings.exposure, 1.1)
    for n in sc.world.node_tree.nodes:
        if n.bl_idname == "ShaderNodeBackground":
            n.inputs["Strength"].default_value = max(n.inputs["Strength"].default_value, 1.2)
    e = sc.eevee
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    if borrador:
        sc.render.resolution_x, sc.render.resolution_y = 1280, 720
        e.taa_render_samples = 24
        for k, v in (("shadow_ray_count", 1), ("shadow_step_count", 4), ("fast_gi_quality", 0.25),
                     ("shadow_resolution_scale", 0.5)):
            if hasattr(e, k):
                setattr(e, k, v)
    else:
        sc.render.resolution_x, sc.render.resolution_y = 2560, 1440
        e.taa_render_samples = 96


def _distancia_caja(ob, p):
    mw = ob.matrix_world
    cs = [mw @ Vector(c) for c in ob.bound_box]
    lo = Vector((min(c.x for c in cs), min(c.y for c in cs), min(c.z for c in cs)))
    hi = Vector((max(c.x for c in cs), max(c.y for c in cs), max(c.z for c in cs)))
    d = Vector((max(lo.x - p.x, 0, p.x - hi.x), max(lo.y - p.y, 0, p.y - hi.y), max(lo.z - p.z, 0, p.z - hi.z)))
    return d.length


def _altura_sobre_suelo(sc, p):
    ter = bpy.data.objects.get("Terreno")
    if ter is None:
        return 0.0
    ok, q, _n, _i = ter.ray_cast((p.x, p.y, 5000.0), (0, 0, -1))
    return p.z - q.z if ok else 0.0


@contextlib.contextmanager
def recorte(sc, cam):
    p = cam.matrix_world.translation
    apagados = []
    if _altura_sobre_suelo(sc, p) < ALTURA_SIN_RECORTE:
        for ob in sc.objects:
            if ob.hide_render or ob.type not in ("MESH", "CURVE", "FONT") or ob.name in SIEMPRE:
                continue
            lim = next((l for pre, l in LIMITES if ob.name.startswith(pre)), LEJOS)
            if _distancia_caja(ob, p) > lim:
                ob.hide_render = True
                apagados.append(ob)
    print("  recorte %s: %d objetos apagados" % (cam.name, len(apagados)), flush=True)
    try:
        yield
    finally:
        for ob in apagados:
            ob.hide_render = False
