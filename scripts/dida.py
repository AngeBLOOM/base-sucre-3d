"""Fachada del edificio DIDA (referencias/DIDA.jpg). Se corre después de entrada.py y guarda el .blend.

    blender --background BaseSucre.blend --python dida.py

El edificio cuelga del vacío «DIDA_origen», que se coloca con datos/ubicaciones.json (frente a la calle de
servicio de los hangares, enfrente del hangar gris). En su propio marco la fachada mira hacia -Y, X corre a lo largo
de la fachada y Z = 0 es el suelo.
"""
import json
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import entrada as E  # noqa: E402

UB = json.load(open(os.path.join(os.path.dirname(E.TEXTURAS), "datos", "ubicaciones.json"),
                    encoding="utf-8"))["edificios"]["DIDA"]
ANCHO, FONDO, ALTO, PISO = 30.0, 12.0, 8.2, 4.0
rnd = E.random.Random(5)


def limpiar():
    col = bpy.data.collections.get("DIDA")
    if col:
        for ob in list(col.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.collections.remove(col)
    for nombre in ("Cam_DIDA", "Cam_Zona_Hangares"):
        ob = bpy.data.objects.get(nombre)
        if ob:
            bpy.data.objects.remove(ob, do_unlink=True)
    col = bpy.data.collections.new("DIDA")
    bpy.context.scene.collection.children.link(col)
    return col


def distancia_calle():
    """Posición (Y local, negativa = delante) de la calle de servicio real frente a la fachada (datos/vias.json)."""
    ruta = os.path.join(os.path.dirname(E.TEXTURAS), "datos", "vias.json")
    if not os.path.exists(ruta):
        return -19.0
    V = json.load(open(ruta, encoding="utf-8"))
    r = math.radians(UB["rumbo_fachada"])
    f = Vector((math.sin(r), math.cos(r)))
    o = Vector((UB["este"], UB["norte"]))
    mejor = None
    for v in V["vias"]:
        if v["capa"] != "service road":
            continue
        for a, b in zip(v["p"], v["p"][1:]):
            a, b = Vector(a), Vector(b)
            t = max(0.0, min(1.0, (o - a).dot(b - a) / max((b - a).length_squared, 1e-9)))
            q = a + (b - a) * t
            d = (q - o).length
            if mejor is None or d < mejor[0]:
                mejor = (d, (q - o).dot(f))
    return -mejor[1] if mejor else -19.0


def poligono_xz(bm, pts, y, grueso, mi):
    """Placa con contorno pts (x, z) sobre el plano de la fachada, extruida hacia -Y."""
    vs = [bm.verts.new((x, y, z)) for x, z in pts]
    f = bm.faces.new(vs)
    f.material_index = mi
    r = bmesh.ops.extrude_face_region(bm, geom=[f])
    arriba = [g for g in r["geom"] if isinstance(g, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=Vector((0, -grueso, 0)), verts=arriba)
    for g in r["geom"]:
        if isinstance(g, bmesh.types.BMFace):
            g.material_index = mi


def contorno_escudo(cx, cz, w, h, n=14):
    """Escudo de tipo «heater»: lados rectos arriba y punta curva abajo."""
    pts = [(cx - w / 2, cz + h / 2), (cx + w / 2, cz + h / 2), (cx + w / 2, cz + h * 0.05)]
    for k in range(1, n):
        a = math.pi * k / n
        pts.append((cx + w / 2 * math.cos(a), cz + h * 0.05 - h * 0.55 * math.sin(a)))
    pts.append((cx - w / 2, cz + h * 0.05))
    return pts


def cinta(bm, cx, cz, w, curva, alto, y, mi, n=12):
    """Cinta curva (banderola) de un escudo: arco de ancho w, flecha «curva»."""
    sup, inf = [], []
    for k in range(n + 1):
        u = -1 + 2 * k / n
        z = cz + curva * (1 - u * u)
        sup.append((cx + u * w / 2, z + alto / 2))
        inf.append((cx + u * w / 2, z - alto / 2))
    poligono_xz(bm, sup + list(reversed(inf)), y, 0.05, mi)


def escudos(M, padre, col, cx, y, cz, s, texto_arriba, texto_abajo, tipo):
    """Escudo del letrero: borde blanco, campo azul, emblema central, cinta arriba y cinta abajo con su lema."""
    azul = M["azul_emblema"]
    blanco = M["blanco"]
    oro = M["dorado"]
    bm = bmesh.new()
    poligono_xz(bm, contorno_escudo(cx, cz, 1.45 * s, 1.5 * s), y, 0.05, 0)
    poligono_xz(bm, contorno_escudo(cx, cz, 1.25 * s, 1.3 * s), y - 0.05, 0.03, 1)
    if tipo == "amb":
        for k in range(7):                                   # siete estrellas en el borde superior
            E.cilindro(bm, (cx - 0.45 * s + k * 0.15 * s, y - 0.09, cz + 0.48 * s), 0.035 * s, 0.035 * s, 0.01,
                       2, 5, (math.pi / 2, 0, 0))
        for lado in (-1, 1):                                 # alas doradas
            for j in range(5):
                a = math.radians(20 + j * 16)
                E.caja(bm, (cx + lado * (0.22 + 0.06 * j) * s, y - 0.1, cz - 0.02 * s + 0.05 * j * s),
                       (0.28 * s, 0.02, 0.06 * s), 2, (0, lado * a, 0))
        E.cilindro(bm, (cx, y - 0.11, cz + 0.12 * s), 0.17 * s, 0.17 * s, 0.02, 2, 24, (math.pi / 2, 0, 0))
        E.cilindro(bm, (cx, y - 0.13, cz + 0.12 * s), 0.1 * s, 0.1 * s, 0.02, 3, 24, (math.pi / 2, 0, 0))
        E.caja(bm, (cx, y - 0.11, cz - 0.3 * s), (0.28 * s, 0.02, 0.24 * s), 4)                # cuartel tricolor
    else:
        E.cilindro(bm, (cx, y - 0.1, cz - 0.02 * s), 0.3 * s, 0.3 * s, 0.02, 5, 28, (math.pi / 2, 0, 0))   # globo
        for k in range(3):
            E.caja(bm, (cx, y - 0.12, cz - 0.02 * s + (k - 1) * 0.12 * s), (0.56 * s, 0.01, 0.015), 1)
        E.caja(bm, (cx, y - 0.12, cz - 0.02 * s), (0.015, 0.01, 0.58 * s), 1)
        E.cilindro(bm, (cx, y - 0.13, cz - 0.02 * s), 0.07 * s, 0.07 * s, 0.01, 3, 18, (math.pi / 2, 0, 0))
        poligono_xz(bm, [(cx - 0.18 * s, cz + 0.36 * s), (cx + 0.18 * s, cz + 0.36 * s), (cx, cz + 0.3 * s)],
                    y - 0.1, 0.02, 0)                        # avión estilizado sobre el globo
        for lado in (-1, 1):                                 # estelas blancas a los lados
            poligono_xz(bm, [(cx + lado * 0.38 * s, cz - 0.2 * s), (cx + lado * 0.46 * s, cz - 0.2 * s),
                             (cx + lado * 0.42 * s, cz + 0.3 * s)], y - 0.1, 0.02, 0)
    cinta(bm, cx, cz + 0.72 * s, 1.55 * s, 0.1 * s, 0.24 * s, y - 0.06, 1)
    cinta(bm, cx, cz - 0.9 * s, 1.75 * s, -0.14 * s, 0.24 * s, y - 0.06, 1)
    E.objeto("DIDA_escudo_" + tipo, bm, [blanco, azul, oro, E.material("Rojo_escudo", (0.65, 0.05, 0.05), 0.4),
                                          E.material("Amarillo_escudo", (0.95, 0.72, 0.05), 0.4),
                                          E.material("Azul_globo", (0.10, 0.35, 0.75), 0.4)], padre, col)
    for txt, z, tam in ((texto_arriba, cz + 0.8 * s, 0.085 * s), (texto_abajo, cz - 0.84 * s, 0.075 * s)):
        E.texto(txt, tam if len(txt) > 6 else 0.13 * s, blanco, padre, col, (cx, y - 0.13, z), (math.pi / 2, 0, 0))


def mata_platano(bm, base, alto, r):
    """Mata de plátano: pseudotallo y ocho hojas largas, anchas y arqueadas."""
    E.cilindro(bm, tuple(base), 0.16, 0.12, alto, 0, 10)
    top = base + Vector((0, 0, alto))
    for k in range(8):
        a = 2 * math.pi * k / 8 + r.uniform(-0.2, 0.2)
        d = Vector((math.cos(a), math.sin(a), 0))
        lado = Vector((-d.y, d.x, 0))
        largo, ancho = r.uniform(1.6, 2.3), r.uniform(0.35, 0.5)
        filas = []
        for j in range(7):
            s = j / 6
            p = top + d * (largo * s) + Vector((0, 0, 0.9 * s - 1.5 * s * s))
            w = ancho * math.sin(math.pi * (0.1 + 0.85 * s))
            filas.append((bm.verts.new(p - lado * w), bm.verts.new(p + Vector((0, 0, 0.04))), bm.verts.new(p + lado * w)))
        for f0, f1 in zip(filas, filas[1:]):
            for i0, i1 in ((0, 1), (1, 2)):
                f = bm.faces.new((f0[i0], f0[i1], f1[i1], f1[i0]))
                f.material_index = 1


def dormitorio_lateral(M, padre, col):
    """Dormitorio pequeño al lado izquierdo de la DIDA (foto del edificito blanco; huella OSM de 11,8 x 6,2 m):
    un piso, techo de lámina verde a un agua con vigas a la vista, ventanitas oscuras, puerta en el extremo,
    acera de concreto alrededor y la pintura gastada abajo."""
    cx, cy, L, W, h0, h1 = -21.9, 3.4, 11.8, 6.2, 3.2, 2.7           # L a lo largo de Y local
    pared = E.pbr("Friso_blanco_gastado", "friso", 3.0, pintura=(0.82, 0.83, 0.84))
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in ((cx - W / 2, cy - L / 2, 0), (cx + W / 2, cy - L / 2, 0),
                                    (cx + W / 2, cy + L / 2, 0), (cx - W / 2, cy + L / 2, 0),
                                    (cx - W / 2, cy - L / 2, h1), (cx + W / 2, cy - L / 2, h0),
                                    (cx + W / 2, cy + L / 2, h0), (cx - W / 2, cy + L / 2, h1))]
    for q in ((0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 6, 7), (3, 2, 1, 0)):
        bm.faces.new([vs[i] for i in q])
    E.objeto("DIDA_dormitorio_lateral", bm, [pared], padre, col)
    # techo de lámina verde con alero de 0,7 m, fascia y vigas (canes) que asoman
    verde = E.pbr("Lamina_verde_techo", "lamina", 1.6, metal=0.25, pintura=(0.12, 0.26, 0.17))
    bm = bmesh.new()
    bm.faces.new([bm.verts.new(v) for v in ((cx - W / 2 - 0.7, cy - L / 2 - 0.5, h1 - 0.08),
                                            (cx + W / 2 + 0.7, cy - L / 2 - 0.5, h0 + 0.08),
                                            (cx + W / 2 + 0.7, cy + L / 2 + 0.5, h0 + 0.08),
                                            (cx - W / 2 - 0.7, cy + L / 2 + 0.5, h1 - 0.08))])
    E.objeto("DIDA_dormitorio_techo", bm, [verde], padre, col)
    bm = bmesh.new()
    for x, z in ((cx - W / 2 - 0.7, h1 - 0.2), (cx + W / 2 + 0.7, h0 - 0.04)):
        E.caja(bm, (x, cy, z), (0.06, L + 1.0, 0.18), 0)
    for k in range(7):
        y = cy - L / 2 + 0.6 + k * (L - 1.2) / 6
        for x0, z in ((cx - W / 2, h1 - 0.25), (cx + W / 2, h0 - 0.22)):
            s = -1 if x0 < cx else 1
            E.caja(bm, (x0 + s * 0.35, y, z), (0.7, 0.12, 0.16), 0)
    E.objeto("DIDA_dormitorio_vigas", bm, [E.material("Verde_oscuro_vigas", (0.06, 0.12, 0.08), 0.6)], padre, col)
    # ventanitas oscuras en el costado largo (x+), ventana y puerta en el extremo (y-), lámparas de pared
    bm = bmesh.new()
    for y in (cy - 3.8, cy - 1.6, cy + 0.6, cy + 3.6):
        E.caja(bm, (cx + W / 2 + 0.03, y, 1.55), (0.06, 0.8 if y < cy else 1.1, 0.85), 0)
    E.caja(bm, (cx + 0.8, cy - L / 2 - 0.03, 1.0), (0.9, 0.06, 1.3), 0)
    E.caja(bm, (cx - 1.4, cy - L / 2 - 0.04, 0.12), (0.9, 0.08, 2.1), 1)
    E.objeto("DIDA_dormitorio_vanos", bm, [M["vidrio"], E.material("Puerta_negra", (0.04, 0.04, 0.045), 0.5)],
             padre, col)
    bm = bmesh.new()
    for p in ((cx + W / 2 + 0.06, cy - 2.7, 2.3), (cx - 0.3, cy - L / 2 - 0.06, 2.35)):
        E.cilindro(bm, p, 0.11, 0.11, 0.05, 0, 12, (0, math.pi / 2, 0) if p[1] > cy - L / 2 else (math.pi / 2, 0, 0))
    E.objeto("DIDA_dormitorio_lamparas", bm, [M["poste"]], padre, col)
    # zócalo despintado (manchas de humedad) y acera perimetral con lajas sueltas
    mancha = E.con_ruido(bpy.data.materials.get("Mancha_humedad") or bpy.data.materials.new("Mancha_humedad"),
                         (0.42, 0.40, 0.35), (0.62, 0.60, 0.55), 2.5, 0.2)
    bm = bmesh.new()
    E.caja(bm, (cx + W / 2 + 0.02, cy, 0), (0.04, L, 0.55), 0)
    E.caja(bm, (cx, cy - L / 2 - 0.02, 0), (W, 0.04, 0.45), 0)
    E.objeto("DIDA_dormitorio_zocalo", bm, [mancha], padre, col)
    bm = bmesh.new()
    E.caja(bm, (cx, cy, 0), (W + 1.6, L + 1.6, 0.12), 0)
    for k in range(4):
        E.caja(bm, (cx - 1.4, cy - L / 2 - 1.6 - k * 0.9, 0), (0.75, 0.55, 0.06), 0)
    E.objeto("DIDA_dormitorio_acera", bm, [M["acera"]], padre, col)
    # fotos del dormitorio por detrás: aires de ventana en el costado que da a la DIDA, aire split y cables en el
    # extremo trasero, y una tapa de tanque recostada en la pared
    aire = E.material("Aire_acondicionado", (0.80, 0.80, 0.78), 0.5)
    bm = bmesh.new()
    for y in (cy + 0.6, cy + 3.6):
        E.caja(bm, (cx + W / 2 + 0.22, y, 1.3), (0.45, 0.7, 0.42), 0)
    E.caja(bm, (cx + 1.2, cy + L / 2 + 0.2, 0.15), (0.85, 0.32, 0.6), 0)        # condensadora del split
    E.objeto("DIDA_dormitorio_aires", bm, [aire], padre, col)
    bm = bmesh.new()
    E.cilindro(bm, (cx + 1.0, cy + L / 2 + 0.03, 0.48), 0.2, 0.2, 0.02, 0, 20, (math.pi / 2, 0, 0))   # rejilla
    E.objeto("DIDA_dormitorio_aire_rejilla", bm, [M["oscuro"] if "oscuro" in M else marco_negro()], padre, col)
    bc = bmesh.new()                                    # cables que bajan por la pared (con algo de comba)
    for dx in (0.0, 0.06, 0.12):
        a = Vector((cx + 0.2 + dx, cy + L / 2 + 0.03, 2.2))
        b = Vector((cx + 0.9 + dx, cy + L / 2 + 0.05, 0.75))
        prev = a
        for k in range(1, 7):
            f = k / 6
            q = a.lerp(b, f) + Vector((0.12 * math.sin(math.pi * f), 0.02, 0))
            d = q - prev
            vs = bmesh.ops.create_cube(bc, size=1.0)["verts"]
            bmesh.ops.transform(bc, matrix=Matrix.Translation((prev + q) / 2) @ d.to_track_quat("Z", "Y").to_matrix()
                                .to_4x4() @ Matrix.Diagonal((0.012, 0.012, d.length, 1)), verts=vs)
            prev = q
    E.objeto("DIDA_dormitorio_cables", bc, [marco_negro()], padre, col)
    bm = bmesh.new()                                    # tapa recostada
    E.caja(bm, (cx - 1.4, cy + L / 2 + 0.35, 0), (1.3, 0.08, 1.1), 0, (math.radians(-14), 0, 0))
    E.objeto("DIDA_dormitorio_tapa", bm, [E.material("Plastico_gris", (0.16, 0.18, 0.20), 0.6)], padre, col)
    bm = bmesh.new()                                    # antena de varilla en la esquina del techo
    E.cilindro(bm, (cx + W / 2 - 0.3, cy + L / 2 - 0.3, h0), 0.02, 0.015, 4.0, 0, 6)
    E.objeto("DIDA_dormitorio_antena", bm, [M["poste"]], padre, col)


def marco_negro():
    return E.material("Marco_negro", (0.02, 0.02, 0.022), 0.4, 0.5)


def malla_bismarck(mat_tronco, mat_hoja):
    """Palma de Bismarck (hojas en abanico gris azuladas), como las de la foto."""
    bm = bmesh.new()
    E.cilindro(bm, (0, 0, 0), 0.48, 0.38, 6.6, 0, 14)
    arriba = Vector((0, 0, 1))
    top = Vector((0, 0, 6.6))
    for i in range(30):
        yaw = 2 * math.pi * i / 30 * 2.618 % (2 * math.pi)       # filotaxia (ángulo áureo)
        elev = math.radians(65 - 85 * (i / 29) + rnd.uniform(-8, 8))
        d = Vector((math.cos(yaw) * math.cos(elev), math.sin(yaw) * math.cos(elev), math.sin(elev)))
        largo_pec = 1.3 + rnd.random() * 0.6
        c = top + d * largo_pec
        # pecíolo
        lat = d.cross(arriba).normalized() if abs(d.z) < 0.99 else Vector((1, 0, 0))
        q = [top + lat * 0.05, top - lat * 0.05, c - lat * 0.03, c + lat * 0.03]
        f = bm.faces.new([bm.verts.new(p) for p in q])
        f.material_index = 1
        # abanico plisado
        v = (d + arriba * 0.25).normalized()
        u = lat
        n = u.cross(v)
        R = 1.5 + rnd.random() * 0.4
        rayos = 24
        pts = []
        for k in range(rayos + 1):
            a = math.radians(-125 + 250 * k / rayos)
            p = c + (u * math.sin(a) + v * math.cos(a)) * R + n * (0.07 if k % 2 else -0.07)
            p += Vector((0, 0, -0.35 * (1 - math.cos(a))))         # las puntas caen
            pts.append(bm.verts.new(p))
        cv = bm.verts.new(c)
        for a, b in zip(pts, pts[1:]):
            f = bm.faces.new((cv, a, b))
            f.material_index = 1
    me = bpy.data.meshes.new("Palma_bismarck")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat_tronco)
    me.materials.append(mat_hoja)
    E.suavizar(me)
    return me


def vehiculo(nombre, M, padre, col, x, y, rumbo, mat):
    """Rústico tipo Land Cruiser (como los beige de la foto)."""
    bm = bmesh.new()
    E.caja(bm, (0, 0, 0.45), (1.9, 4.9, 1.0), 0)
    E.caja(bm, (0, -0.45, 1.45), (1.84, 3.7, 0.85), 1)
    E.caja(bm, (0, -0.45, 2.28), (1.86, 3.75, 0.07), 0)
    E.caja(bm, (0, 2.5, 0.35), (1.95, 0.18, 0.35), 2)       # parachoques
    E.caja(bm, (0, -2.5, 0.35), (1.95, 0.18, 0.35), 2)
    for wx in (-0.92, 0.92):
        for wy in (-1.6, 1.55):
            E.cilindro(bm, (wx - 0.14, wy, 0.42), 0.42, 0.42, 0.28, 2, 18, (0, math.pi / 2, 0))
    ob = E.objeto(nombre, bm, [mat, M["vidrio"], M["llanta"]], padre, col)
    ob.location = (x, y, 0)
    ob.rotation_euler = (0, 0, rumbo)


def main():
    col = limpiar()
    M = E.mats()
    yc = distancia_calle()
    rojo = E.material("Rojo_DIDA", (0.62, 0.035, 0.035), 0.45)
    azul = E.material("Vidrio_azul", (0.02, 0.20, 0.36), 0.03, 0.25)
    marco = E.material("Marco_negro", (0.02, 0.02, 0.022), 0.4, 0.5)
    beige = E.material("Beige_vehiculo", (0.50, 0.43, 0.29), 0.35, 0.1)
    terracota = E.material("Terracota", (0.45, 0.16, 0.08), 0.8)
    plata = E.material("Hoja_bismarck", (0.16, 0.25, 0.21), 0.5)

    padre = bpy.data.objects.new("DIDA_origen", None)
    padre.empty_display_type = "ARROWS"
    padre.empty_display_size = 5
    padre.location = (UB["este"], UB["norte"], E.aplanar(UB["este"], UB["norte"], "cota_DIDA"))
    # la fachada (-Y local) mira hacia rumbo_fachada
    padre.rotation_euler = (0, 0, math.radians(180.0 - UB["rumbo_fachada"]))
    col.objects.link(padre)

    # césped propio alrededor (se desvanece hacia la foto satelital)
    pasto = E.pbr("Pasto_DIDA", "pasto", 2.5, (0.45, 0.95, 0.30), fade=(32.0, 55.0),
                  variacion=(0.05, (0.85, 0.75, 0.45)))
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, radius=55.0, segments=96)
    bmesh.ops.translate(bm, vec=Vector((0, 0, 0.02)), verts=bm.verts[:])
    E.objeto("DIDA_pasto", bm, [pasto], padre, col)

    # Fotos «dida detalles», «dida detalles 2» y «dida estacionamiento izquierdo/derecho»: cuerpo de dos pisos a la
    # derecha, ala de un piso a la izquierda, entrada con marquesina entre ambos, franjas finas color vino, franjas
    # largas de vidrio azul reflejante y alero con las vigas a la vista.
    vino = E.material("Vino_DIDA", (0.28, 0.045, 0.045), 0.5)
    # ella corrigió: la entrada con la marquesina está en el MEDIO del edificio, que es de dos pisos completo
    xa = -ANCHO / 2
    bm = bmesh.new()
    E.caja(bm, (0, FONDO / 2, 0), (ANCHO, FONDO, ALTO), 0)
    E.objeto("DIDA_edificio", bm, [M["blanco"]], padre, col)
    bm = bmesh.new()                            # franja vino entre pisos y fascia vino del techo
    E.caja(bm, (0, FONDO / 2, PISO - 0.12), (ANCHO + 0.1, FONDO + 0.1, 0.2), 0)
    E.caja(bm, (0.4, FONDO / 2, ALTO - 0.05), (ANCHO + 1.8, FONDO + 1.8, 0.32), 0)
    E.objeto("DIDA_franjas", bm, [vino], padre, col)
    bm = bmesh.new()                            # losa del alero (cara inferior blanca) y vigas a la vista
    E.caja(bm, (0.4, FONDO / 2, ALTO - 0.16), (ANCHO + 1.7, FONDO + 1.7, 0.1), 0)
    for k in range(int(FONDO / 0.9) + 1):
        E.caja(bm, (ANCHO / 2 + 0.45, k * 0.9, ALTO - 0.38), (0.9, 0.09, 0.22), 1)
    E.objeto("DIDA_alero", bm, [M["blanco"], E.material("Madera_vigas", (0.32, 0.22, 0.14), 0.7)], padre, col)

    # franjas de ventanas de vidrio azul reflejante con marco oscuro y parteluces
    bm = bmesh.new()

    def franja(x0, x1, z0, z1, paños):
        w = x1 - x0
        E.caja(bm, (0.5 * (x0 + x1), -0.03, z0 - 0.07), (w + 0.14, 0.06, z1 - z0 + 0.14), 1)
        E.caja(bm, (0.5 * (x0 + x1), -0.07, z0), (w, 0.05, z1 - z0), 0)
        for k in range(1, paños):
            E.caja(bm, (x0 + k * w / paños, -0.1, z0), (0.06, 0.04, z1 - z0), 1)

    # alturas medidas en «dida detalles 2» y DIDA.jpg con la franja entre pisos (4 m) de escala: en planta baja el
    # vidrio va de 1,15 a 3,2 m y en la alta de ~5,2 a 7,25 m (antes estaban casi 1 m más abajo; se lo hicieron notar)
    franja(5.5, 13.8, 1.15, 3.2, 4)             # planta baja, a los dos lados de la entrada
    franja(-13.8, -5.5, 1.15, 3.2, 4)
    franja(-14.0, -7.5, 5.25, 7.2, 3)           # planta alta
    franja(-5.5, -1.0, 5.3, 7.15, 2)
    franja(1.0, 5.5, 5.3, 7.15, 2)
    franja(7.5, 14.0, 5.15, 7.25, 3)
    E.objeto("DIDA_ventanas", bm, [azul, marco], padre, col)
    bm = bmesh.new()                            # aires de ventana en la planta alta, bajo el vidrio
    for x in (-3.4, 3.2):
        E.caja(bm, (x, -0.22, 4.75), (0.7, 0.45, 0.45), 0)
    E.objeto("DIDA_aires", bm, [E.material("Aire_acondicionado", (0.80, 0.80, 0.78), 0.5)], padre, col)

    # fachada trasera y costado izquierdo (foto de atrás): ventanas de vidrio turquesa con marco, respiradero en
    # la azotea, mástil de antena y reflector en la esquina
    turquesa = E.material("Vidrio_turquesa", (0.02, 0.32, 0.48), 0.05, 0.2)
    bm = bmesh.new()
    # (subidas igual que las del frente)
    for x0, x1, z0, z1 in ((2.0, 6.0, 5.2, 6.9), (-6.5, -4.8, 5.3, 6.7), (-3.5, -2.2, 1.2, 3.0), (6.0, 7.6, 1.2, 3.0),
                           (10.0, 13.0, 5.2, 6.9), (10.5, 12.0, 1.3, 2.9)):
        E.caja(bm, (0.5 * (x0 + x1), FONDO + 0.03, z0 - 0.06), (x1 - x0 + 0.12, 0.06, z1 - z0 + 0.12), 1)
        E.caja(bm, (0.5 * (x0 + x1), FONDO + 0.07, z0), (x1 - x0, 0.05, z1 - z0), 0)
        n = max(1, round((x1 - x0) / 1.4))
        for k in range(1, n):
            E.caja(bm, (x0 + k * (x1 - x0) / n, FONDO + 0.1, z0), (0.05, 0.04, z1 - z0), 1)
    for y in (3.0, 7.0, 10.0):                                             # costado izquierdo (-X), dos pisos
        E.caja(bm, (xa - 0.03, y, 5.5), (0.06, 1.0, 1.2), 0)
    for y in (4.0, 8.5):
        E.caja(bm, (xa - 0.03, y, 1.6), (0.06, 1.1, 1.2), 0)
    E.objeto("DIDA_ventanas_traseras", bm, [turquesa, marco], padre, col)
    bm = bmesh.new()                                    # dos puertas blancas de servicio en la trasera
    for x in (-7.2, -1.0):
        E.caja(bm, (x, FONDO + 0.04, 0.2), (1.1, 0.08, 2.2), 0)
    E.caja(bm, (-4.0, FONDO + 0.6, 0), (7.5, 1.2, 0.2), 1)                   # losa de servicio
    E.objeto("DIDA_puertas_traseras", bm, [E.material("Puerta_blanca", (0.80, 0.80, 0.78), 0.5, 0.2),
                                           M["acera"]], padre, col)
    bm = bmesh.new()
    E.caja(bm, (xa + 1.2, FONDO - 1.0, ALTO + 0.1), (0.6, 0.6, 0.7), 0)        # respiradero con sombrerete
    E.caja(bm, (xa + 1.2, FONDO - 1.0, ALTO + 0.8), (0.9, 0.9, 0.08), 0)
    E.cilindro(bm, (2.0, FONDO - 3.0, ALTO + 0.1), 0.035, 0.02, 7.5, 0, 8)        # mástil de antena
    for k, (dx, dy) in enumerate(((2.5, 0), (-2.5, 0.5), (0, -2.5))):          # vientos del mástil
        a, b = Vector((2.0, FONDO - 3.0, ALTO + 5.5)), Vector((2.0 + dx, FONDO - 3.0 + dy, ALTO + 0.1))
        d = b - a
        vs = bmesh.ops.create_cube(bm, size=1.0)["verts"]
        bmesh.ops.transform(bm, matrix=Matrix.Translation((a + b) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
                            @ Matrix.Diagonal((0.012, 0.012, d.length, 1)), verts=vs)
    E.caja(bm, (ANCHO / 2 - 0.3, -0.25, ALTO - 0.7), (0.35, 0.3, 0.3), 0)       # reflector de la esquina
    E.objeto("DIDA_azotea", bm, [M["poste"]], padre, col)
    # matas de plátano y un árbol frondoso en la esquina trasera izquierda, entre la DIDA y el dormitorio
    bm = bmesh.new()
    for x, y, h in ((-16.8, FONDO + 1.2, 2.4), (-17.6, FONDO - 1.0, 2.8), (-16.4, FONDO - 3.2, 2.1),
                    (-15.9, FONDO + 3.0, 1.8)):
        mata_platano(bm, Vector((x, y, 0)), h, rnd)
    E.objeto("DIDA_platanos", bm, [E.material("Tallo_platano", (0.30, 0.34, 0.16), 0.7),
                                   E.material("Hoja_platano", (0.16, 0.36, 0.08), 0.5)], padre, col)
    bh = bmesh.new()
    E.hojas(bh, Vector((-17.0, FONDO + 5.5, 3.6)), 2.4, 1100, rnd, 0, 0.22)
    E.objeto("DIDA_arbol_trasero", bh, [M["follaje"]], padre, col)
    dormitorio_lateral(M, padre, col)

    # entrada: plataforma con dos escalones, vestíbulo de vidrio y marquesina plana de borde vino
    xe0, xe1, ye = -4.25, 4.25, -4.2
    bm = bmesh.new()
    E.caja(bm, (0.5 * (xe0 + xe1), ye / 2, 0), (xe1 - xe0, -ye, 0.45), 0)
    for k, h in enumerate((0.3, 0.15)):
        E.caja(bm, (0.5 * (xe0 + xe1), ye - 0.35 - k * 0.35, 0), (xe1 - xe0, 0.35, h), 0)
    E.objeto("DIDA_plataforma", bm, [M["acera"]], padre, col)
    bm = bmesh.new()
    E.caja(bm, (0.0, -0.05, 0.45), (5.0, 0.08, 2.75), 0)                   # vidrio del vestíbulo
    for x in (-2.4, -0.8, 0.8, 2.4):
        E.caja(bm, (x, -0.1, 0.45), (0.07, 0.05, 2.75), 1)
    E.caja(bm, (0.0, -0.1, 2.5), (5.0, 0.05, 0.07), 1)
    E.objeto("DIDA_vestibulo", bm, [M["vidrio"], marco], padre, col)
    bm = bmesh.new()
    E.caja(bm, (0.5 * (xe0 + xe1), ye / 2, 3.35), (xe1 - xe0 + 0.4, -ye + 0.2, 0.25), 0)
    for x in (xe0 + 0.25, xe1 - 0.25):                                       # postes de las dos esquinas
        E.caja(bm, (x, ye + 0.25, 0.45), (0.3, 0.3, 2.9), 0)
    E.objeto("DIDA_marquesina", bm, [M["blanco"]], padre, col)
    bm = bmesh.new()
    for (cx, cy), (sx, sy) in (((0.5 * (xe0 + xe1), ye - 0.12), (xe1 - xe0 + 0.65, 0.12)),
                               ((xe1 + 0.32, ye / 2), (0.12, -ye + 0.3)), ((xe0 - 0.32, ye / 2), (0.12, -ye + 0.3))):
        E.caja(bm, (cx, cy, 3.25), (sx, sy, 0.42), 0)
    E.objeto("DIDA_marquesina_borde", bm, [vino], padre, col)
    # letrero (foto del letrero): panel vino a todo lo ancho del frente de la marquesina, letras DIDA blancas en
    # relieve, escudo de la Aviación Militar Bolivariana a la izquierda y escudo de la DIDA a la derecha
    lx = 0.5 * (xe0 + xe1)
    yl = ye - 0.25
    zl0, zl1 = 3.2, 5.6
    bm = bmesh.new()
    E.caja(bm, (lx, yl, zl0), (xe1 - xe0 + 0.7, 0.22, zl1 - zl0), 0)
    E.caja(bm, (lx, yl + 0.5, zl0 + 0.5), (xe1 - xe0 + 0.3, 1.0, zl1 - zl0 - 0.6), 0)   # cuerpo trasero
    E.objeto("DIDA_letrero", bm, [vino], padre, col)
    t = E.texto("DIDA", 1.05, M["blanco"], padre, col, (lx, yl - 0.12, 0.5 * (zl0 + zl1) - 0.05),
                (math.pi / 2, 0, 0), extr=0.1)
    t.data.space_character = 1.25
    escudos(M, padre, col, lx - 2.95, yl - 0.13, 0.5 * (zl0 + zl1), 1.0, "AVIACIÓN MILITAR BOLIVARIANA",
            "SPATIUM SUPERANUS PALATINUS", "amb")
    escudos(M, padre, col, lx + 2.95, yl - 0.13, 0.5 * (zl0 + zl1), 1.0, "DIDA", "EL INFINITO ES EL LÍMITE", "dida")
    # cielo raso de la marquesina: paneles blancos con juntas, dos lámparas y las vigas en diagonal
    bm = bmesh.new()
    for k in range(1, 9):
        E.caja(bm, (xe0 + k * (xe1 - xe0) / 9, ye / 2, 3.33), (0.04, -ye, 0.02), 0)
    for k in range(1, 4):
        E.caja(bm, (lx, k * ye / 4, 3.33), (xe1 - xe0, 0.04, 0.02), 0)
    for s in (-1, 1):
        q0, q1 = Vector((lx + s * 0.8, ye + 0.2, 3.3)), Vector((lx + s * (xe1 - xe0) / 2, -0.2, 3.3))
        d = q1 - q0
        E.caja(bm, ((q0.x + q1.x) / 2, (q0.y + q1.y) / 2, 3.26), (d.length, 0.12, 0.08), 0,
               (0, 0, math.atan2(d.y, d.x)))
    E.objeto("DIDA_cielo_raso", bm, [M["cielo_raso"]], padre, col)
    bm = bmesh.new()
    for x in (lx - 1.6, lx + 1.6):
        E.caja(bm, (x, ye / 2, 3.28), (1.3, 0.4, 0.05), 0)
    E.objeto("DIDA_lamparas", bm, [M["luz"]], padre, col)
    # antena parabólica y farol sobre la marquesina
    bm = bmesh.new()
    E.cilindro(bm, (xe1 - 2.0, ye / 2 - 0.6, 3.6), 0.05, 0.05, 1.0, 0, 8)
    vs = bmesh.ops.create_cone(bm, cap_ends=False, segments=28, radius1=0.06, radius2=0.75, depth=0.24)["verts"]
    bmesh.ops.transform(bm, matrix=Matrix.Translation((xe1 - 2.0, ye / 2 - 0.8, 4.75)) @ Matrix.Rotation(-1.0, 4, "X"),
                        verts=vs)
    E.cilindro(bm, (xe0 + 1.0, ye + 1.4, 3.6), 0.04, 0.04, 2.6, 0, 8)
    E.caja(bm, (xe0 + 1.0, ye + 1.25, 6.2), (0.35, 0.45, 0.12), 0)
    E.objeto("DIDA_antena", bm, [M["poste"]], padre, col)

    # caminería ancha de concreto (con juntas) desde la entrada hasta el paso peatonal, brocales blancos
    ancho_c = 4.6
    y0c, y1c = ye - 1.05, yc + 3.4
    bm = bmesh.new()
    E.caja(bm, (0.5 * (xe0 + xe1), 0.5 * (y0c + y1c), 0), (ancho_c, y0c - y1c, 0.1), 0)
    E.caja(bm, (2.0, -0.9, 0), (ANCHO - 2.0, 1.8, 0.08), 0)                 # acera al pie de la fachada
    E.objeto("DIDA_aceras", bm, [M["acera"]], padre, col)
    bm = bmesh.new()
    k = 0
    while y0c - k * 2.4 > y1c:
        E.caja(bm, (0.5 * (xe0 + xe1), y0c - k * 2.4, 0.1), (ancho_c, 0.03, 0.005), 0)
        k += 1
    E.objeto("DIDA_juntas", bm, [marco], padre, col)
    bm = bmesh.new()
    xc = 0.5 * (xe0 + xe1)
    for s in (-1, 1):                                                    # brocales que se abren hacia la calle
        E.caja(bm, (xc + s * (ancho_c / 2 + 0.15), y1c + 4.5, 0), (0.25, 9.0, 0.2), 0)
        E.caja(bm, (xc + s * (ancho_c / 2 + 1.3), y1c + 0.9, 0), (0.25, 2.6, 0.2), 0, (0, 0, s * math.radians(-40)))
    E.caja(bm, (14.0, yc + 3.6, 0), (24.0, 0.25, 0.2), 0)                 # brocal blanco del lado de la DIDA
    E.caja(bm, (-22.0, yc + 3.6, 0), (14.0, 0.25, 0.2), 0)
    E.objeto("DIDA_brocal", bm, [M["pintura"]], padre, col)
    # la calle de servicio la dibuja vias.py con el trazado real; aquí solo el paso peatonal alineado
    bm = bmesh.new()
    for k in range(7):
        E.caja(bm, (xc - 3.0 + k * 1.0, yc, 0.12), (0.5, 6.4, 0.03), 0)
    E.objeto("DIDA_paso_peatonal", bm, [M["pintura"]], padre, col)

    # techados de estacionamiento a los dos lados de la caminería (tubos y lámina plana), sin carros
    for nombre, x0, x1 in (("izq", xc - 27.0, xc - 5.0), ("der", xc + 7.0, xc + 23.0)):
        bm, bt = bmesh.new(), bmesh.new()
        ya, yb = yc + 4.5, yc + 10.0
        x = x0
        while x <= x1 + 0.01:
            for y in (ya + 0.3, yb - 0.3):
                E.cilindro(bm, (x, y, 0), 0.06, 0.06, 2.6 if y < yb - 1 else 2.9, 0, 8)
            x += 4.4
        E.cilindro(bm, (x0, ya + 0.3, 2.55), 0.05, 0.05, x1 - x0, 0, 8, (0, math.pi / 2, 0))
        E.cilindro(bm, (x0, yb - 0.3, 2.85), 0.05, 0.05, x1 - x0, 0, 8, (0, math.pi / 2, 0))
        bt.faces.new([bt.verts.new(v) for v in ((x0 - 0.4, ya - 0.2, 2.62), (x1 + 0.4, ya - 0.2, 2.62),
                                                (x1 + 0.4, yb + 0.2, 2.95), (x0 - 0.4, yb + 0.2, 2.95))])
        E.objeto("DIDA_techado_" + nombre, bm, [M["poste"]], padre, col)
        E.objeto("DIDA_techado_lamina_" + nombre, bt, [M["lamina_techo"] if "lamina_techo" in M
                                                       else E.pbr("Lamina_techo_gris", "lamina", 2.0, metal=0.3,
                                                                  pintura=(0.70, 0.72, 0.74))], padre, col)
        bm = bmesh.new()
        E.caja(bm, (0.5 * (x0 + x1), 0.5 * (ya + yb), 0), (x1 - x0 + 1.0, yb - ya + 0.6, 0.06), 0)
        E.objeto("DIDA_estacionamiento_" + nombre, bm, [E.con_ruido(
            bpy.data.materials.get("Tierra_compactada") or bpy.data.materials.new("Tierra_compactada"),
            (0.30, 0.27, 0.22), (0.45, 0.42, 0.36), 0.5, 0.2)], padre, col)

    # aspersores blancos en el césped, un tocón de piedra y las matas del costado izquierdo
    bm = bmesh.new()
    for _ in range(18):
        x = rnd.uniform(-24.0, 24.0)
        y = rnd.uniform(yc + 11.0, ye - 2.0)
        if abs(x - xc) < ancho_c / 2 + 1.0:
            continue
        E.cilindro(bm, (x, y, 0), 0.045, 0.045, 0.22, 0, 8)
    E.objeto("DIDA_aspersores", bm, [M["pintura"]], padre, col)
    bm = bmesh.new()
    for x, y, h in ((xc + 13.0, yc + 5.0, 0.75), (xc - 12.0, yc + 6.5, 0.9)):   # tocones de palma cortada
        E.cilindro(bm, (x, y, 0), 0.5, 0.42, h, 0, 16)
    E.objeto("DIDA_tocon", bm, [M["tronco_palma"]], padre, col)
    bh = bmesh.new()
    for x, y, r in ((-ANCHO / 2 - 3.0, 2.0, 1.4), (-ANCHO / 2 - 5.5, -2.5, 1.8), (-ANCHO / 2 - 2.0, 7.0, 1.2),
                    (ANCHO / 2 - 1.0, -1.2, 0.7), (6.0, -1.2, 0.6), (-6.0, -1.2, 0.6)):
        E.hojas(bh, Vector((x, y, r * 0.8)), r, int(260 * r), rnd, 0, 0.14)
    E.objeto("DIDA_arbustos", bh, [M["arbusto"]], padre, col)
    bm, bh = bmesh.new(), bmesh.new()
    E.cilindro(bm, (xe1 + 0.6, -0.6, 0.45), 0.28, 0.22, 0.5, 0, 14)          # matero junto a la puerta
    E.hojas(bh, Vector((xe1 + 0.6, -0.6, 1.3)), 0.45, 120, rnd, 0, 0.13)
    E.objeto("DIDA_materos", bm, [terracota], padre, col)
    E.objeto("DIDA_matas", bh, [M["arbusto"]], padre, col)
    # como las fotos nuevas: desde la entrada mirando a la calle y al hangar gris, y desde la esquina derecha
    E.camara("Cam_DIDA_Caminería", padre, col, (xc + 0.5, ye - 2.0, 1.6), (xc - 2.0, yc - 40.0, 4.0), 18)
    E.camara("Cam_DIDA_Esquina", padre, col, (ANCHO / 2 + 6.0, -9.0, 1.2), (-6.0, 4.0, 4.5), 16)
    E.camara("Cam_DIDA_Letrero", padre, col, (lx, ye - 8.5, 1.8), (lx, ye, 4.3), 30)
    E.camara("Cam_DIDA_Dormitorio", padre, col, (-11.5, -6.5, 1.6), (-22.5, 4.5, 1.8), 22)

    cam = E.camara("Cam_DIDA", padre, col, (7.0, yc - 12.0, 1.7), (0.5, 0.0, 4.2), 30)
    # vista aérea de la calle de los hangares para revisar la ubicación (desde el sureste)
    z = padre.location.z
    E.camara("Cam_Zona_Hangares", None, col, (-250.0, -930.0, z + 160.0), (-430.0, -700.0, z), 30)
    bpy.context.scene.camera = cam
    bpy.ops.wm.save_mainfile()
    print("DIDA lista")


if __name__ == "__main__":
    main()
