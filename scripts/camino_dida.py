"""El camino real de la portada a la DIDA: ruta más corta por las calles de OpenStreetMap (datos/vias.json).

    blender --background BaseSucre.blend --python camino_dida.py      → cámaras Cam_Camino_01…NN en la escena
    python camino_dida.py --mapa <carpeta del proyecto>               → renders/cliente/mapa_camino_entrada_dida.png

Las cámaras van a 2,5 m de altura, sobre la calle, mirando hacia adelante en el sentido de la marcha, una cada
~300 m; la última mira a la DIDA.
"""
import heapq
import json
import math
import os
import sys

ES_BLENDER = "bpy" in sys.modules or any(a.endswith("blender.exe") for a in sys.argv[:1])
RAIZ = (sys.argv[sys.argv.index("--mapa") + 1] if "--mapa" in sys.argv
        else os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TIPOS = {"service road", "road", "road link", "road (access type)", "Daylight road"}
PORTADA = (1440.0, 331.0)


def ruta():
    V = json.load(open(os.path.join(RAIZ, "datos", "vias.json"), encoding="utf-8"))
    U = json.load(open(os.path.join(RAIZ, "datos", "ubicaciones.json"), encoding="utf-8"))["edificios"]
    destino = (U["DIDA"]["este"], U["DIDA"]["norte"])
    nodos, vecinos = {}, {}

    def nodo(p):
        k = (round(p[0] / 3.0), round(p[1] / 3.0))            # une vértices a menos de 3 m (cruces)
        nodos.setdefault(k, p)
        vecinos.setdefault(k, [])
        return k
    for v in V["vias"]:
        if v["capa"] not in TIPOS:
            continue
        pts = v["p"]
        for a, b in zip(pts, pts[1:]):
            ka, kb = nodo(a), nodo(b)
            d = math.hypot(a[0] - b[0], a[1] - b[1])
            vecinos[ka].append((kb, d))
            vecinos[kb].append((ka, d))

    # las calles vienen cortadas en el borde de cada mosaico: se unen los extremos que quedan a menos de 10 m
    celdas = {}
    for k, p in nodos.items():
        celdas.setdefault((int(p[0] // 10), int(p[1] // 10)), []).append(k)
    for k, p in nodos.items():
        cx, cy = int(p[0] // 10), int(p[1] // 10)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for k2 in celdas.get((cx + dx, cy + dy), []):
                    if k2 != k:
                        d = math.hypot(nodos[k2][0] - p[0], nodos[k2][1] - p[1])
                        if d < 10.0:
                            vecinos[k].append((k2, d))

    def cercano(p):
        return min(nodos, key=lambda k: math.hypot(nodos[k][0] - p[0], nodos[k][1] - p[1]))
    s = cercano(PORTADA)
    dist, prev, cola = {s: 0.0}, {}, [(0.0, s)]
    while cola:
        d, k = heapq.heappop(cola)
        if d > dist.get(k, 1e18):
            continue
        for n, w in vecinos[k]:
            if d + w < dist.get(n, 1e18):
                dist[n] = d + w
                prev[n] = k
                heapq.heappush(cola, (d + w, n))
    # destino: el punto alcanzable de la red más cercano a la DIDA (hay tramos sueltos que no conectan)
    t = min(dist, key=lambda k: math.hypot(nodos[k][0] - destino[0], nodos[k][1] - destino[1]))
    camino, k = [], t
    while k != s:
        camino.append(nodos[k])
        k = prev[k]
    camino.append(nodos[s])
    return list(reversed(camino)), destino, dist.get(t, 0.0)


def a_lo_largo(pts, paso):
    """Puntos cada «paso» metros sobre la polilínea, con su dirección de marcha."""
    out, acum, sig = [], 0.0, 0.0
    for a, b in zip(pts, pts[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        while L > 0 and sig <= acum + L:
            f = (sig - acum) / L
            out.append(((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f), ((b[0] - a[0]) / L, (b[1] - a[1]) / L)))
            sig += paso
        acum += L
    return out


def camaras():
    import bpy
    from mathutils import Vector
    pts, destino, largo = ruta()
    sc = bpy.context.scene
    deps = bpy.context.evaluated_depsgraph_get()
    for ob in [o for o in bpy.data.objects if o.name.startswith("Cam_Camino_")]:
        bpy.data.objects.remove(ob, do_unlink=True)
    marcas = a_lo_largo(pts, 300.0)[1:]
    terreno = bpy.data.objects["Terreno"]

    def cota(px, py):
        # solo el terreno: con scene.ray_cast un árbol o un alero daban una cota falsa
        ok, p, _n, _i = terreno.ray_cast((px, py, 3000.0), (0, 0, -1))
        return p.z if ok else 0.0
    for i, ((x, y), (dx, dy)) in enumerate(marcas, 1):
        z = cota(x - dx * 4.0, y - dy * 4.0)
        # si el terreno sube delante (la 01 salió tapada), la cámara sube lo necesario para ver por encima
        delante = max(cota(x + dx * k, y + dy * k) for k in range(5, 45, 5))
        z = max(z, delante - 0.6)
        cam = bpy.data.cameras.new(f"Cam_Camino_{i:02d}")
        cam.lens, cam.clip_end = 22, 30000
        ob = bpy.data.objects.new(f"Cam_Camino_{i:02d}", cam)
        sc.collection.objects.link(ob)
        ob.location = (x - dx * 4.0, y - dy * 4.0, z + 2.5)
        mira = Vector((x + dx * 60.0, y + dy * 60.0, max(cota(x + dx * 60.0, y + dy * 60.0), z) + 2.6))
        ob.rotation_euler = (mira - Vector(ob.location)).to_track_quat("-Z", "Y").to_euler()
    # llegada: desde la calle frente a la DIDA
    x, y = pts[-1]
    ok, loc, *_ = sc.ray_cast(deps, Vector((x, y, 3000.0)), Vector((0, 0, -1)))
    cam = bpy.data.cameras.new("Cam_Camino_llegada")
    cam.lens, cam.clip_end = 22, 30000
    ob = bpy.data.objects.new(f"Cam_Camino_{len(marcas) + 1:02d}", cam)
    sc.collection.objects.link(ob)
    d = Vector((destino[0] - x, destino[1] - y, 0)).normalized()
    ob.location = (x - d.x * 20, y - d.y * 20, (loc.z if ok else 0.0) + 2.0)
    ob.rotation_euler = (Vector((destino[0], destino[1], ob.location.z + 2)) - Vector(ob.location)).to_track_quat(
        "-Z", "Y").to_euler()
    bpy.ops.wm.save_mainfile()
    print(f"camino de {largo:.0f} m, {len(marcas) + 1} cámaras")


def mapa():
    from PIL import Image, ImageDraw, ImageFont
    pts, destino, largo = ruta()
    im = Image.open(os.path.join(RAIZ, "datos", "sat_6km.png")).convert("RGB")

    def px(e, n):
        return ((e + 3000) / 1.464844, (3000 - n) / 1.464844)
    xs = [px(*p)[0] for p in pts] + [px(*PORTADA)[0]]
    ys = [px(*p)[1] for p in pts] + [px(*PORTADA)[1]]
    m = 80
    caja = (int(min(xs)) - m, int(min(ys)) - m, int(max(xs)) + m, int(max(ys)) + m)
    c = im.crop(caja)
    k = 2560 / c.width
    c = c.resize((2560, int(c.height * k)), Image.LANCZOS)
    d = ImageDraw.Draw(c)

    def P(e, n):
        x, y = px(e, n)
        return ((x - caja[0]) * k, (y - caja[1]) * k)
    linea = [P(*p) for p in pts]
    d.line(linea, fill=(0, 0, 0), width=16, joint="curve")
    d.line(linea, fill=(255, 200, 0), width=9, joint="curve")
    f = ImageFont.truetype("arialbd.ttf", 44)
    marcas = a_lo_largo(pts, 300.0)[1:]
    for i, ((x, y), _) in enumerate(marcas, 1):
        cx, cy = P(x, y)
        d.ellipse([cx - 26, cy - 26, cx + 26, cy + 26], fill=(200, 20, 20), outline=(255, 255, 255), width=4)
        d.text((cx, cy), str(i), fill=(255, 255, 255), font=ImageFont.truetype("arialbd.ttf", 30), anchor="mm")
    for (e, n), txt in ((PORTADA, "ENTRADA"), (destino, "DIDA"), ((1201.3, 278.0), "COMEDOR"),
                        ((942.6, 12.8), "ACADEMIA")):
        x, y = P(e, n)
        d.text((x, y - 50), txt, fill=(255, 255, 255), font=f, anchor="mm", stroke_width=5, stroke_fill=(0, 0, 0))
    d.text((40, 30), f"Camino de la entrada a la DIDA · {largo / 1000:.1f} km", fill=(255, 255, 255), font=f,
           stroke_width=5, stroke_fill=(0, 0, 0))
    out = os.path.join(RAIZ, "renders", "cliente", "mapa_camino_entrada_dida.png")
    c.save(out)
    print("mapa:", out, c.size)


if __name__ == "__main__":
    if "--mapa" in sys.argv:
        mapa()
    else:
        camaras()
