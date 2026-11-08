"""Calles internas, caminos, calles de rodaje y la plataforma de concreto de la base.

Trazado: datos/vias.json (OpenStreetMap, sacado con exporta_vias.py de los mosaicos que ya tenía AeroEscuela).
Plataforma: zona clara y continua de la foto satelital alrededor de la línea de hangares.
Se corre al final (después de todos los edificios, porque las calles siguen el terreno ya aplanado):

    blender --background BaseSucre.blend --python vias.py
"""
import json
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector, kdtree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import entrada as E  # noqa: E402

RAIZ = os.path.dirname(E.TEXTURAS)
D = json.load(open(os.path.join(RAIZ, "datos", "svbs.json")))
V = json.load(open(os.path.join(RAIZ, "datos", "vias.json"), encoding="utf-8"))
ZONA = (-1500.0, 1700.0, -1150.0, 1700.0)         # recuadro de la base (este, norte)
ENTRADA = Vector((1440.0, 331.0))                 # allí manda la calle modelada de la portada
# ancho (m) y material por tipo de vía
TIPOS = {("service road", 0): (6.5, "calle"), ("service road", 1): (6.5, "calle"),
         ("road link", 0): (6.5, "calle"), ("road link", 2): (6.5, "calle"),
         ("road (access type)", 4): (6.5, "calle"), ("road (access type)", 6): (7.0, "calle"),
         ("road", 0): (7.0, "calle"), ("road", 2): (7.0, "calle"), ("road", 6): (7.0, "calle"),
         ("road", 4): (7.0, "calle"), ("Daylight road", 10): (4.0, "camino"),
         ("Daylight road", 12): (4.0, "camino"), ("Daylight road", 13): (4.0, "camino"),
         ("track", 5): (3.5, "tierra"), ("aeroway", 0): (18.0, "rodaje"), ("aeroway", 1): (18.0, "rodaje")}


def limpiar():
    col = bpy.data.collections.get("Vias")
    if col:
        for ob in list(col.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.collections.remove(col)
    col = bpy.data.collections.new("Vias")
    bpy.context.scene.collection.children.link(col)
    return col


def en_pista(p, margen=6.0):
    for rw in D["runways"]:
        cn, ce = rw["center"]
        dn, de = rw["dir"]
        rx, ry = p.x - ce, p.y - cn
        if abs(rx * de + ry * dn) < rw["length"] / 2 + margen and abs(-rx * dn + ry * de) < rw["width"] / 2 + margen:
            return True
    return False


class Suelo:
    """Cota del suelo visible: el terreno ya aplanado o, donde lo hay, el césped de cada edificio (que queda 30 cm
    más arriba porque los edificios se asientan sobre el terreno bajado)."""

    def __init__(self):
        bpy.context.view_layer.update()
        self.obs = [bpy.data.objects["Terreno"]] + [o for o in bpy.data.objects
                                                   if o.type == "MESH" and o.name.startswith("Pasto")]
        self.inv = [o.matrix_world.inverted() for o in self.obs]
        self.lejos = bpy.data.objects.get("Paisaje_lejano")

    def z(self, x, y):
        mejor = None
        for ob, inv in zip(self.obs, self.inv):
            o = inv @ Vector((x, y, 3000.0))
            d = (inv.to_3x3() @ Vector((0, 0, -1))).normalized()
            ok, p, _n, _i = ob.ray_cast(o, d)
            if ok:
                zz = (ob.matrix_world @ p).z
                mejor = zz if mejor is None else max(mejor, zz)
        if mejor is None and self.lejos:
            ok, p, _n, _i = self.lejos.ray_cast((x, y, 3000.0), (0, 0, -1))
            mejor = p.z if ok else 0.0
        return mejor or 0.0


def remuestrear(pts, paso):
    out = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        L = (b - a).length
        n = max(1, int(L / paso))
        out += [a.lerp(b, k / n) for k in range(1, n + 1)]
    return out


def cinta(bm, pts, ancho, suelo, alto, desplaz=0.0, mi=0):
    """Franja de ancho fijo que sigue la polilínea y el relieve (alto = cuánto queda sobre el suelo)."""
    if len(pts) < 2:
        return
    izq, der = [], []
    for i, p in enumerate(pts):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, len(pts) - 1)]
        t = (b - a)
        if t.length < 1e-6:
            continue
        t.normalize()
        n = Vector((-t.y, t.x))
        c = p + n * desplaz
        for s, lista in ((1, izq), (-1, der)):
            q = c + n * (s * ancho / 2)
            lista.append(bm.verts.new((q.x, q.y, suelo.z(q.x, q.y) + alto)))
    for k in range(len(izq) - 1):
        f = bm.faces.new((der[k], der[k + 1], izq[k + 1], izq[k]))
        f.material_index = mi


VOLUMENES = ("DIDA_edificio", "CEA_muros", "CEA_cobertizo", "Hangar_gris_muros", "Hangar_gris_anexo",
             "G14_volumen", "G14_planta_caseta", "Hangar3_muros", "Hangar3_anexo", "Grupo7_volumen", "Grupo7_anexo",
             "_barras", "Comando_volumen", "Torre_fuste", "G19_muros", "Portada", "Garita", "Bomberos_volumen",
             "Combustible_volumen", "Hangarcito_boveda", "Hangarcito_caseta", "Hangarcito_torre_agua", "Comedor_volumen", "Hangar_blanco_muros", "Academia_muros",
             "Comedor_salon", "CAA_volumen", "Adentro_dgcim_muros", "Adentro_anexo_muros", "Tanque_casetas",
             "Largo_volumen", "Lavanderia_volumen", "Lavanderia_ala", "Galpon_rojo_volumen")


class Huellas:
    """Planta de los edificios modelados (caja de cada volumen principal) para que ninguna calle los atraviese."""

    def __init__(self, margen=1.5):
        bpy.context.view_layer.update()
        self.cajas = []
        for ob in bpy.data.objects:
            if ob.type == "MESH" and any(ob.name.endswith(s) or ob.name == s for s in VOLUMENES):
                bb = [Vector(c) for c in ob.bound_box]
                lo = Vector((min(c.x for c in bb) - margen, min(c.y for c in bb) - margen))
                hi = Vector((max(c.x for c in bb) + margen, max(c.y for c in bb) + margen))
                self.cajas.append((ob.matrix_world.inverted(), lo, hi))

    def dentro(self, p):
        for inv, lo, hi in self.cajas:
            q = inv @ Vector((p.x, p.y, 0.0))
            if lo.x < q.x < hi.x and lo.y < q.y < hi.y:
                return True
        return False


HUELLAS = None


def tramos_validos(pts):
    """Parte la polilínea donde sale de la base, entra en la portada, cruza una pista o pisa un edificio."""
    tramo, tramos = [], []
    for p in remuestrear(pts, 2.0):
        fuera = (not (ZONA[0] < p.x < ZONA[1] and ZONA[2] < p.y < ZONA[3]) or (p - ENTRADA).length < 110
                 or HUELLAS.dentro(p))
        if fuera:
            if len(tramo) > 1:
                tramos.append(tramo)
            tramo = []
        else:
            tramo.append(p)
    if len(tramo) > 1:
        tramos.append(tramo)
    return tramos


def _tangente(pts, i):
    t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
    return t.normalized() if t.length > 1e-6 else Vector((1.0, 0.0))


def ejes_de_vias():
    """Todos los tramos con su ancho y material, y muestras de su eje cada metro (para saber si un punto cae
    dentro de otra calle)."""
    lista = []
    for v in V["vias"]:
        tipo = TIPOS.get((v["capa"], v["simbolo"]))
        if tipo:
            for tramo in tramos_validos([Vector(p) for p in v["p"]]):
                lista.append((tramo, tipo[0], tipo[1]))
    muestras = []
    for vid, (tramo, ancho, _m) in enumerate(lista):
        pts = remuestrear(tramo, 1.0)
        for i, p in enumerate(pts):
            muestras.append((p, vid, ancho / 2, _tangente(pts, i)))
    kd = kdtree.KDTree(len(muestras))
    for k, (p, *_r) in enumerate(muestras):
        kd.insert((p.x, p.y, 0.0), k)
    kd.balance()
    return lista, muestras, kd


def borde_libre(q, vid, t, muestras, kd):
    """La línea blanca de borde no se pinta dentro de otra calle: así se abren los empalmes y, cuando OSM trae la
    misma calle dos veces (mosaicos que se solapan), solo la primera lleva líneas (antes salían dobles)."""
    for _co, idx, dist in kd.find_range((q.x, q.y, 0.0), 10.0):
        _p, v2, hw2, t2 = muestras[idx]
        if v2 == vid or dist > hw2 - 0.2:
            continue
        if abs(t.dot(t2)) > 0.9 and v2 > vid:
            continue
        return False
    return True


def calles(col, suelo, M):
    bms = {k: bmesh.new() for k in ("calle", "camino", "tierra", "rodaje", "linea_blanca", "linea_amarilla")}
    n = 0
    lista, muestras, kd = ejes_de_vias()
    for vid, (tramo, ancho, mat) in enumerate(lista):
        pts = remuestrear(tramo, 4.0)
        if mat == "rodaje":
            pts = [p for p in pts if not en_pista(p)]
            if len(pts) < 2:
                continue
            cinta(bms["rodaje"], pts, ancho, suelo, 0.05)
            cinta(bms["linea_amarilla"], pts, 0.3, suelo, 0.08)
        else:
            alto = {"calle": 0.09, "camino": 0.07, "tierra": 0.04}[mat]
            cinta(bms[mat], pts, ancho, suelo, alto)
            if mat == "calle":
                finos = remuestrear(tramo, 2.0)
                for s in (-1, 1):
                    off = s * (ancho / 2 - 0.35)
                    corrido = []
                    for i, p in enumerate(finos):
                        t = _tangente(finos, i)
                        if borde_libre(p + Vector((-t.y, t.x)) * off, vid, t, muestras, kd):
                            corrido.append(p)
                            continue
                        cinta(bms["linea_blanca"], corrido, 0.14, suelo, alto + 0.012, off)
                        corrido = []
                    cinta(bms["linea_blanca"], corrido, 0.14, suelo, alto + 0.012, off)
        n += 1
    mats = {"calle": E.pbr("Concreto_via", "acera", 4.0, (0.90, 0.90, 0.88), variacion=(0.03, (0.78, 0.78, 0.76))),
            "camino": E.pbr("Asfalto_camino", "asfalto", 4.0, (0.85, 0.85, 0.85), variacion=(0.05, (0.7, 0.7, 0.7))),
            "tierra": E.con_ruido(bpy.data.materials.new("Tierra_camino"), (0.30, 0.24, 0.17), (0.45, 0.37, 0.27), 0.3),
            "rodaje": (bpy.data.materials.get("Asfalto_pista") or bpy.data.materials.get("Asfalto")
                       or E.material("Asfalto_rodaje", (0.08, 0.08, 0.085), 0.85)),
            "linea_blanca": M["pintura"], "linea_amarilla": M["amarillo"]}
    for k, bm in bms.items():
        if len(bm.faces):
            E.objeto("Via_" + k, bm, [mats[k]], None, col)
        else:
            bm.free()
    print("tramos de vía:", n)


def plataforma(col, suelo):
    """Concreto de la plataforma: zona clara conectada de la foto satelital, en celdas de 4 m."""
    img = bpy.data.images.load(os.path.join(RAIZ, "datos", "sat_6km.png"), check_existing=True)
    w, h = img.size
    buf = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(buf)
    px = buf.reshape(h, w, 4)[..., :3]
    m = 6000.0 / w

    def color(e, n):
        j = int((e + 3000) / m)
        i = int((n + 3000) / m)
        return px[i - 1:i + 2, j - 1:j + 2].reshape(-1, 3).mean(axis=0)

    paso = 4.0
    e0, e1, n0, n1 = -900.0, 120.0, -1000.0, -230.0
    nx, ny = int((e1 - e0) / paso), int((n1 - n0) / paso)
    clara = np.zeros((ny, nx), bool)
    for iy in range(ny):
        for ix in range(nx):
            e, n = e0 + (ix + 0.5) * paso, n0 + (iy + 0.5) * paso
            c = color(e, n)
            lum = c.mean()
            sat = c.max() - c.min()
            # concreto: claro y poco saturado, sin el verde del pasto (también el muy blanco, junto a la torre)
            clara[iy, ix] = ((lum > 0.55 and sat < 0.2 and c[1] < c[0] + 0.04) or (lum > 0.7 and sat < 0.25)) \
                and not en_pista(Vector((e, n)), 2.0)
    # región conectada que contiene el centro de la plataforma
    from collections import deque
    # semilla: la celda clara más cercana a un punto en medio de la plataforma
    ys, xs = np.nonzero(clara)
    cx, cy = (-300 - e0) / paso, (-430 - n0) / paso
    k = int(np.argmin((xs - cx) ** 2 + (ys - cy) ** 2))
    sem = (int(xs[k]), int(ys[k]))
    print("celdas claras:", int(clara.sum()), "semilla", sem, "color", color(e0 + sem[0] * paso, n0 + sem[1] * paso))
    sel = np.zeros_like(clara)
    if clara[sem[1], sem[0]]:
        q = deque([sem])
        sel[sem[1], sem[0]] = True
        while q:
            x, y = q.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                a, b = x + dx, y + dy
                if 0 <= a < nx and 0 <= b < ny and clara[b, a] and not sel[b, a]:
                    sel[b, a] = True
                    q.append((a, b))
    # cierra huecos de una celda (aviones, manchas) para que el concreto quede corrido
    hueco = (~sel[1:-1, 1:-1]) & sel[:-2, 1:-1] & sel[2:, 1:-1] & sel[1:-1, :-2] & sel[1:-1, 2:]
    sel[1:-1, 1:-1] |= hueco
    # borde suave: campo difuminado en las esquinas de las celdas y recorte de cada celda por la curva de nivel 0,5
    # (marching squares), en vez de la escalera de cuadritos
    f = sel.astype(np.float32)
    for _ in range(2):
        g = np.pad(f, 1, mode="edge")
        f = (g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:] + 2 * g[1:-1, 1:-1]) / 6.0
    g = np.pad(f, 1, mode="constant")
    esq = (g[:-1, :-1] + g[1:, :-1] + g[:-1, 1:] + g[1:, 1:]) / 4.0       # (ny+1, nx+1)
    bm = bmesh.new()
    verts = {}

    def vert(x, y):
        k = (round(x, 2), round(y, 2))
        if k not in verts:
            verts[k] = bm.verts.new((x, y, suelo.z(x, y) + 0.06))
        return verts[k]
    celdas = 0
    for iy in range(ny):
        for ix in range(nx):
            c = [(ix, iy), (ix + 1, iy), (ix + 1, iy + 1), (ix, iy + 1)]
            val = [esq[j, i] - 0.5 for i, j in c]
            if max(val) <= 0:
                continue
            poli = []
            for k in range(4):
                (i0, j0), (i1, j1) = c[k], c[(k + 1) % 4]
                v0, v1 = val[k], val[(k + 1) % 4]
                if v0 > 0:
                    poli.append((i0, j0))
                if (v0 > 0) != (v1 > 0):
                    t = v0 / (v0 - v1)
                    poli.append((i0 + (i1 - i0) * t, j0 + (j1 - j0) * t))
            if len(poli) >= 3:
                vs = [vert(e0 + i * paso, n0 + j * paso) for i, j in poli]
                if len({id(v) for v in vs}) >= 3:
                    try:
                        bm.faces.new(vs)
                        celdas += 1
                    except ValueError:
                        pass
    mat = E.pbr("Concreto_plataforma", "acera", 5.0, (0.88, 0.87, 0.84), variacion=(0.02, (0.8, 0.8, 0.78)))
    E.objeto("Plataforma", bm, [mat], None, col)
    print("plataforma:", celdas, "celdas de 4 m =", round(celdas * paso * paso), "m2")


def postes_de_luz(col, suelo):
    """Postes de concreto con cruceta y tres cables a lo largo de la calle de los hangares, del lado noroeste
    (fotos «dida detalles» y «dida estacionamiento»): uno cada ~38 m, cables con catenaria."""
    U = json.load(open(os.path.join(RAIZ, "datos", "ubicaciones.json"), encoding="utf-8"))["edificios"]
    dida = Vector((U["DIDA"]["este"], U["DIDA"]["norte"]))

    def dist(pl):
        return min((Vector(p) - dida).length for p in remuestrear([Vector(q) for q in pl], 4.0))
    srv = [v["p"] for v in V["vias"] if v["capa"] == "service road"]
    pl = [Vector(p) for p in min(srv, key=dist)]
    pts = remuestrear(pl, 2.0)
    bm, bc = bmesh.new(), bmesh.new()
    cimas = []
    acum, sig = 0.0, 0.0
    for i in range(1, len(pts)):
        acum += (pts[i] - pts[i - 1]).length
        if acum < sig:
            continue
        sig = acum + 38.0
        t = (pts[i] - pts[i - 1]).normalized()
        n = Vector((-t.y, t.x))                       # izquierda de la marcha = noroeste
        p = pts[i] + n * 6.0
        if HUELLAS.dentro(p) or en_pista(p):
            cimas.append(None)
            continue
        z = suelo.z(p.x, p.y)
        E.cilindro(bm, (p.x, p.y, z), 0.17, 0.11, 10.5, 0, 10)
        rot = math.atan2(n.y, n.x)
        E.caja(bm, (p.x, p.y, z + 9.6), (2.2, 0.12, 0.12), 0, (0, 0, rot))
        cimas.append([Vector((p.x + n.x * s, p.y + n.y * s, z + 9.75)) for s in (-1.0, 0.0, 1.0)])
    for a, b in zip(cimas, cimas[1:]):
        if a is None or b is None:
            continue
        for pa, pb in zip(a, b):
            prev = pa
            for k in range(1, 9):
                f = k / 8
                q = pa.lerp(pb, f) - Vector((0, 0, 0.9 * 4 * f * (1 - f)))
                d = q - prev
                m = (prev + q) / 2
                vs = bmesh.ops.create_cube(bc, size=1.0)["verts"]
                bmesh.ops.transform(bc, matrix=Matrix.Translation(m) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
                                    @ Matrix.Diagonal((0.025, 0.025, d.length, 1)), verts=vs)
                prev = q
    concreto = E.material("Poste_concreto", (0.55, 0.54, 0.51), 0.85)
    E.objeto("Postes_luz", bm, [concreto], None, col)
    E.objeto("Cables_luz", bc, [E.material("Cable_negro", (0.02, 0.02, 0.02), 0.5)], None, col)
    print("postes de luz:", sum(1 for c in cimas if c))


def main():
    global HUELLAS
    col = limpiar()
    M = E.mats()
    suelo = Suelo()
    HUELLAS = Huellas()
    print("edificios que cortan calles:", len(HUELLAS.cajas))
    calles(col, suelo, M)
    plataforma(col, suelo)
    postes_de_luz(col, suelo)
    bpy.ops.wm.save_mainfile()
    print("vías listas")


main()
