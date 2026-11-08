"""Recorrido de cámara para el video de presentación (2K, 24 fps): vista aérea de toda la base, bajada a la entrada,
paso sobre la portada, traslado hasta Bomberos y vuelo bajo por la calle de los hangares hasta la DIDA, y subida
final mostrando la calle entera.

    blender --background BaseSucre.blend --python video_recorrido.py -- preparar
    blender --background BaseSucre.blend --python video_recorrido.py -- render <primer cuadro> <último cuadro>

Los cuadros quedan en renders/video/cuadro_####.png; luego se arma el mp4 con armar_video.py.
"""
import json
import math
import os
import sys

import bpy
from mathutils import Vector

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FPS = 24
ANCHO, ALTO = 2560, 1440
MUESTRAS = 16
ESCALA_TIEMPO = 0.8          # el recorrido diseñado en 45 s queda en 36 s


def calle_principal():
    """La calle de servicio de los hangares (OSM), recortada entre Bomberos y la DIDA, de Bomberos hacia la DIDA."""
    V = json.load(open(os.path.join(RAIZ, "datos", "vias.json"), encoding="utf-8"))
    U = json.load(open(os.path.join(RAIZ, "datos", "ubicaciones.json"), encoding="utf-8"))["edificios"]

    def proy(p, pl):
        mejor = None
        acum = 0.0
        for a, b in zip(pl, pl[1:]):
            a, b = Vector(a), Vector(b)
            L = (b - a).length
            t = max(0.0, min(1.0, (p - a).dot(b - a) / max(L * L, 1e-9)))
            d = (a + (b - a) * t - p).length
            if mejor is None or d < mejor[0]:
                mejor = (d, acum + t * L)
            acum += L
        return mejor

    dida = Vector((U["DIDA"]["este"], U["DIDA"]["norte"]))
    bomb = Vector((U["Bomberos"]["este"], U["Bomberos"]["norte"]))
    srv = [v["p"] for v in V["vias"] if v["capa"] == "service road"]
    pl = min(srv, key=lambda p: proy(dida, p)[0])
    s0, s1 = proy(bomb, pl)[1], proy(dida, pl)[1]

    def punto(s):
        acum = 0.0
        for a, b in zip(pl, pl[1:]):
            a, b = Vector(a), Vector(b)
            L = (b - a).length
            if acum + L >= s:
                return a.lerp(b, (s - acum) / L)
            acum += L
        return Vector(pl[-1])
    return punto, s0, s1


def catmull(p0, p1, p2, p3, t):
    t2, t3 = t * t, t * t * t
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)


def muestrear(claves, t):
    """claves: [(segundo, Vector)]; curva suave que pasa por todas las claves."""
    ts = [k[0] for k in claves]
    if t <= ts[0]:
        return claves[0][1].copy()
    if t >= ts[-1]:
        return claves[-1][1].copy()
    i = max(j for j in range(len(ts) - 1) if ts[j] <= t)
    u = (t - ts[i]) / (ts[i + 1] - ts[i])
    u = u * u * (3 - 2 * u) * 0.35 + u * 0.65            # leve suavizado en cada clave sin detenerse
    p = [claves[max(i - 1, 0)][1], claves[i][1], claves[i + 1][1], claves[min(i + 2, len(ts) - 1)][1]]
    return catmull(*p, u)


def claves():
    sc = bpy.context.scene
    z = sc.get("cota_DIDA", 0.0)
    ze = sc.get("cota_entrada", z)
    punto, s0, s1 = calle_principal()
    centro = Vector((-150.0, -520.0, z))
    gate = Vector((1440.0, 331.0, ze))
    afuera = Vector((math.sin(math.radians(42)), math.cos(math.radians(42)), 0))
    pos, mira = [], []
    # 1. vista aérea de toda la base
    pos += [(0.0, Vector((1100.0, -1900.0, z + 950.0))), (5.0, Vector((1250.0, -700.0, z + 520.0)))]
    mira += [(0.0, centro), (5.0, Vector((600.0, -150.0, z)))]
    # 2. bajada a la entrada, de frente a la portada
    pos += [(10.0, gate + afuera * 70 + Vector((0, 0, 14.0))), (13.0, gate + afuera * 22 + Vector((0, 0, 9.0)))]
    mira += [(10.0, gate + Vector((0, 0, 5.0))), (13.0, gate + Vector((0, 0, 5.0)))]
    # 3. sobre la portada y hacia adentro, subiendo para el traslado
    adentro = -afuera
    pos += [(15.5, gate + adentro * 40 + Vector((0, 0, 30.0)))]
    mira += [(15.5, gate + adentro * 200 + Vector((0, 0, 0.0)))]
    # 4. traslado alto hasta Bomberos
    ini = punto(s0 - 60.0)
    pos += [(19.0, Vector((700.0, -120.0, z + 120.0))), (23.0, Vector((ini.x + 60, ini.y + 40, z + 45.0)))]
    mira += [(19.0, Vector((60.0, -380.0, z))), (23.0, Vector((ini.x, ini.y, z + 4.0)))]
    # 5. vuelo bajo por la calle, de Bomberos a la DIDA, mirando hacia adelante y algo hacia abajo
    n = 9
    t0, t1 = 25.0, 41.0
    for k in range(n + 1):
        f = k / n
        s = s0 + (s1 - s0) * f
        a = punto(s)
        b = punto(s + (s1 - s0) * 0.06)
        lado = Vector((-(b - a).y, (b - a).x, 0)).normalized() * (6.0 if k % 2 else -6.0)
        pos.append((t0 + (t1 - t0) * f, Vector((a.x + lado.x, a.y + lado.y, z + 16.0 - 4.0 * math.sin(math.pi * f)))))
        c = punto(s + (s1 - s0) * 0.12)
        mira.append((t0 + (t1 - t0) * f, Vector((c.x, c.y, z + 4.0))))
    # 6. subida final mostrando la calle completa
    fin = punto(s1)
    medio = punto((s0 + s1) / 2)
    pos += [(45.0, Vector((fin.x - 140.0, fin.y - 140.0, z + 170.0)))]
    mira += [(45.0, Vector((medio.x, medio.y, z)))]
    k = ESCALA_TIEMPO
    return [(t * k, v) for t, v in pos], [(t * k, v) for t, v in mira], 45.0 * k


def preparar():
    sc = bpy.context.scene
    ob = bpy.data.objects.get("Cam_Recorrido")
    if ob:
        bpy.data.objects.remove(ob, do_unlink=True)
    cam = bpy.data.cameras.new("Cam_Recorrido")
    cam.lens = 22
    cam.clip_start = 0.3
    cam.clip_end = 30000
    ob = bpy.data.objects.new("Cam_Recorrido", cam)
    sc.collection.objects.link(ob)
    pos, mira, dur = claves()
    nf = int(dur * FPS)
    previo = None
    for f in range(nf + 1):
        t = f / FPS
        p = muestrear(pos, t)
        m = muestrear(mira, t)
        q = (m - p).to_track_quat("-Z", "Y")
        e = q.to_euler("XYZ", previo) if previo else q.to_euler("XYZ")   # sin saltos de ±180° entre cuadros
        previo = e
        ob.location = p
        ob.rotation_euler = e
        ob.keyframe_insert("location", frame=f + 1)
        ob.keyframe_insert("rotation_euler", frame=f + 1)
    bpy.context.view_layer.update()
    sc.camera = ob
    sc.frame_start, sc.frame_end = 1, nf + 1
    sc.render.fps = FPS
    sc.render.resolution_x, sc.render.resolution_y = ANCHO, ALTO
    sc.render.resolution_percentage = 100
    sc.eevee.taa_render_samples = MUESTRAS
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = os.path.join(RAIZ, "renders", "video", "cuadro_")
    bpy.ops.wm.save_mainfile()
    print("recorrido listo:", nf + 1, "cuadros")


def render(a, b):
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = a, b
    sc.render.use_overwrite = False
    sc.render.use_placeholder = True
    bpy.ops.render.render(animation=True)


args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["preparar"]
if args[0] == "preparar":
    preparar()
else:
    render(int(args[1]), int(args[2]))
