"""Los edificios de OpenStreetMap que todavía no tienen modelo propio, hechos como edificios de verdad en vez de
cajas con rayas: muros de friso pintado con zócalo, ventanas con vidrio, alféizar, dintel y reja, una puerta con
su alero, y techo de lámina con el color que tiene en la foto satelital (a dos aguas en las plantas
rectangulares pequeñas, plano con pretil en las demás). Los galpones grandes van en lámina con su portón.
Se corre después de academia.py y antes de vias.py (sustituye al objeto «Edificios» de construir_base.py):

    blender --background BaseSucre.blend --python edificios_genericos.py
"""
import json
import math
import os
import random
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import entrada as E  # noqa: E402

RAIZ = os.path.dirname(E.TEXTURAS)
DATOS = os.path.join(RAIZ, "datos")
ZONA = (-1500.0, 1300.0, -1130.0, 1690.0)
SAT_INT = 3000.0
PISO = 3.2
# colores de friso habituales en la base (crema, blanco, gris claro, amarillo pálido, salmón pálido)
PALETA = [((0.80, 0.74, 0.58), 35), ((0.84, 0.83, 0.79), 30), ((0.62, 0.65, 0.67), 15),
          ((0.83, 0.75, 0.48), 10), ((0.80, 0.63, 0.55), 10)]
P, PAR, ZOC, VID, HER, PUE, LAM, REM = range(8)


def mat_atributo(nombre, carpeta, metros, atributo, rango=(0.75, 1.15), metal=0.0):
    """Color por edificio (atributo de esquina) por el grano de una textura CC0, con su relieve y rugosidad."""
    m = bpy.data.materials.get(nombre)
    if m:
        return m
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapa = nt.nodes.new("ShaderNodeMapping")
    mapa.inputs["Scale"].default_value = (1 / metros,) * 3
    nt.links.new(coord.outputs["Object"], mapa.inputs["Vector"])

    def img(archivo, dato):
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(os.path.join(E.TEXTURAS, carpeta, archivo), check_existing=True)
        if dato:
            t.image.colorspace_settings.name = "Non-Color"
        t.projection = "BOX"
        t.projection_blend = 0.3
        nt.links.new(mapa.outputs["Vector"], t.inputs["Vector"])
        return t
    bw = nt.nodes.new("ShaderNodeRGBToBW")
    nt.links.new(img("color.jpg", False).outputs["Color"], bw.inputs["Color"])
    r = nt.nodes.new("ShaderNodeMapRange")
    r.inputs["From Min"].default_value = 0.05
    r.inputs["From Max"].default_value = 0.6
    r.inputs["To Min"].default_value, r.inputs["To Max"].default_value = rango
    nt.links.new(bw.outputs["Val"], r.inputs["Value"])
    at = nt.nodes.new("ShaderNodeAttribute")
    at.attribute_type = "GEOMETRY"
    at.attribute_name = atributo
    mx = nt.nodes.new("ShaderNodeMix")
    mx.data_type = "RGBA"
    mx.blend_type = "MULTIPLY"
    mx.inputs["Factor"].default_value = 1.0
    nt.links.new(at.outputs["Color"], mx.inputs["A"])
    nt.links.new(r.outputs["Result"], mx.inputs["B"])
    nt.links.new(mx.outputs["Result"], b.inputs["Base Color"])
    nt.links.new(img("rugosidad.jpg", True).outputs["Color"], b.inputs["Roughness"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.inputs["Strength"].default_value = 0.8
    nt.links.new(img("normal.jpg", True).outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Metallic"].default_value = metal
    return m


def materiales():
    return [E.material("Generico_base", (0.5, 0.5, 0.5)),          # 0 sin uso
            mat_atributo("Friso_generico", "friso", 3.0, "pared"),
            E.pbr("Zocalo_generico", "concreto_gastado", 2.0, pintura=(0.32, 0.32, 0.31)),
            E.material("Vidrio_oscuro", (0.015, 0.02, 0.03), 0.04),
            E.material("Herreria_generica", (0.07, 0.07, 0.075), 0.45, 0.6),
            E.material("Puerta_generica", (0.22, 0.12, 0.06), 0.55),
            E.pbr("Lamina_galpon", "lamina_gastada", 2.0, metal=0.3, pintura=(0.66, 0.68, 0.68)),
            mat_atributo("Techo_generico", "lamina_gastada", 2.0, "techo", (0.7, 1.2), 0.25)]


class Ctx:
    def __init__(self):
        self.V, self.F, self.MI, self.COL = [], [], [], []
        self.cp, self.ct = "pared", "techo"

    def cara(self, cos, mi, color=None, capa=None):
        i0 = len(self.V)
        self.V.extend(tuple(c) for c in cos)
        self.F.append(tuple(range(i0, i0 + len(cos))))
        self.MI.append(mi)
        self.COL.append((capa, color))

    def caja(self, centro, tam, mi, rot=(0, 0, 0)):
        """Caja con base en centro.z, girada solo en Z (bmesh.ops.create_cube recorre toda la malla en cada
        llamada y con miles de ventanas el tiempo crecía al cuadrado: aquí va directo a las listas)."""
        cx, cy, z0 = centro
        sx, sy, sz = tam[0] / 2, tam[1] / 2, tam[2]
        c, s = math.cos(rot[2]), math.sin(rot[2])
        i0 = len(self.V)
        for dz in (0.0, sz):
            for ax, ay in ((-sx, -sy), (sx, -sy), (sx, sy), (-sx, sy)):
                self.V.append((cx + ax * c - ay * s, cy + ax * s + ay * c, z0 + dz))
        for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
            self.F.append(tuple(i0 + k for k in f))
            self.MI.append(mi)
            self.COL.append((None, None))

    def crear(self, nombre, mats, col):
        me = bpy.data.meshes.new(nombre)
        me.from_pydata(self.V, [], self.F)
        me.polygons.foreach_set("material_index", self.MI)
        nl = sum(len(f) for f in self.F)
        for capa in ("pared", "techo"):
            arr = np.ones((nl, 4), np.float32)
            k = 0
            for f, (cp, colr) in zip(self.F, self.COL):
                if cp == capa and colr is not None:
                    arr[k:k + len(f)] = colr
                k += len(f)
            at = me.color_attributes.new(capa, "FLOAT_COLOR", "CORNER")
            at.data.foreach_set("color", arr.ravel())
        for m in mats:
            me.materials.append(m)
        me.update()
        ob = bpy.data.objects.new(nombre, me)
        col.objects.link(ob)
        return ob


def angulos_rectos(pts):
    if len(pts) != 4:
        return False
    for i in range(4):
        a = (pts[i - 1] - pts[i]).normalized()
        b = (pts[(i + 1) % 4] - pts[i]).normalized()
        if abs(a.dot(b)) > 0.2:
            return False
    return True


def fachada(C, a, b, suelo, alto, pisos, color, galpon, rnd, puerta):
    """Muro de a a b (planta antihoraria: afuera queda a la derecha de a→b) con su zócalo,
    ventanas y, si toca, la puerta."""
    d = b - a
    L = d.length
    if L < 0.3:
        return
    t = d / L
    n = Vector((t.y, -t.x))                         # normal hacia afuera
    giro = math.atan2(t.y, t.x)
    z0 = suelo - 0.4
    C.cara([(a.x, a.y, z0), (b.x, b.y, z0), (b.x, b.y, suelo + alto), (a.x, a.y, suelo + alto)],
           LAM if galpon else PAR, None if galpon else color, C.cp)
    # zócalo pintado de 60 cm
    o = n * 0.02
    C.cara([(a.x + o.x, a.y + o.y, z0), (b.x + o.x, b.y + o.y, z0), (b.x + o.x, b.y + o.y, suelo + 0.6),
            (a.x + o.x, a.y + o.y, suelo + 0.6)], ZOC)
    if galpon:
        if puerta and L > 16:
            c = (a + b) / 2 + n * 0.04
            w, h = min(14.0, L * 0.5), min(alto * 0.75, 9.0)
            C.caja((c.x, c.y, suelo), (w, 0.08, h), HER, (0, 0, giro))
            for k in range(1, int(w / 1.2)):                         # nervios del portón corredizo
                q = c + t * (-w / 2 + k * 1.2) + n * 0.05
                C.caja((q.x, q.y, suelo), (0.08, 0.06, h), LAM, (0, 0, giro))
        return
    # ventanas por piso cada ~3 m, dejando la puerta en el centro de la fachada más larga
    nv = int((L - 1.2) / 3.0)
    if nv < 1:
        return
    paso = L / nv
    hay_puerta = puerta
    for f in range(pisos):
        for k in range(nv):
            s = (k + 0.5) * paso
            if hay_puerta and f == 0 and abs(s - L / 2) < paso * 0.6:
                continue
            c = a + t * s
            zc = suelo + f * PISO + 1.6
            g = c + n * 0.03
            w, h = 1.2, 1.1
            C.cara([(g.x - t.x * w / 2, g.y - t.y * w / 2, zc - h / 2), (g.x + t.x * w / 2, g.y + t.y * w / 2, zc - h / 2),
                    (g.x + t.x * w / 2, g.y + t.y * w / 2, zc + h / 2), (g.x - t.x * w / 2, g.y - t.y * w / 2, zc + h / 2)],
                   VID)
            q = c + n * 0.06
            C.caja((q.x, q.y, zc - h / 2 - 0.05), (w + 0.25, 0.14, 0.07), ZOC, (0, 0, giro))   # alféizar
            C.caja((q.x, q.y, zc + h / 2 + 0.06), (w + 0.15, 0.10, 0.10), ZOC, (0, 0, giro))   # dintel
            r = c + n * 0.08
            for j in range(-2, 3):                                                                 # reja
                p = r + t * (j * w / 5)
                C.caja((p.x, p.y, zc - h / 2), (0.025, 0.025, h), HER, (0, 0, giro))
            C.caja((r.x, r.y, zc), (w, 0.025, 0.025), HER, (0, 0, giro))
    if hay_puerta:
        c = a + t * (L / 2) + n * 0.03
        C.cara([(c.x - t.x * 0.55, c.y - t.y * 0.55, suelo), (c.x + t.x * 0.55, c.y + t.y * 0.55, suelo),
                (c.x + t.x * 0.55, c.y + t.y * 0.55, suelo + 2.2), (c.x - t.x * 0.55, c.y - t.y * 0.55, suelo + 2.2)],
               PUE)
        q = c + n * 0.55
        C.caja((q.x, q.y, suelo + 2.55), (2.0, 1.1, 0.09), ZOC, (0, 0, giro))                 # alero de la puerta
        p = c + n * 0.6
        C.caja((p.x, p.y, suelo - 0.04), (1.8, 1.2, 0.16), ZOC, (0, 0, giro))                 # escalón


def techo_dos_aguas(C, pts, suelo, alto, color):
    lados = [(pts[(i + 1) % 4] - pts[i]).length for i in range(4)]
    i0 = 0 if lados[0] >= lados[1] else 1                         # lado largo = cumbrera
    a, b, c, d = (pts[(i0 + k) % 4] for k in range(4))
    u = (b - a).normalized()                                       # a lo largo de la cumbrera
    ancho = (d - a).length
    v = (d - a) / ancho
    vuelo = 0.5
    zc = suelo + alto
    flecha = (ancho / 2) * math.tan(math.radians(16))
    caida = vuelo * math.tan(math.radians(16))
    m0, m1 = (a + d) / 2 - u * vuelo, (b + c) / 2 + u * vuelo
    for lado, base0, base1 in ((-1, a, b), (1, d, c)):
        e0 = base0 - u * vuelo + v * (lado * vuelo)
        e1 = base1 + u * vuelo + v * (lado * vuelo)
        C.cara([(e0.x, e0.y, zc - caida), (e1.x, e1.y, zc - caida), (m1.x, m1.y, zc + flecha),
                (m0.x, m0.y, zc + flecha)], REM, color, C.ct)
    # testeros triangulares sobre los lados cortos
    for p0, p1 in ((a, d), (b, c)):
        m = (p0 + p1) / 2
        C.cara([(p0.x, p0.y, zc), (p1.x, p1.y, zc), (m.x, m.y, zc + flecha)], PAR, C._color, C.cp)


def techo_plano(C, pts, suelo, alto, color, galpon):
    zt = suelo + alto
    C.cara([(p.x, p.y, zt) for p in pts], REM, color, C.ct)
    # pretil de 60 cm con remate claro
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        C.cara([(a.x, a.y, zt), (b.x, b.y, zt), (b.x, b.y, zt + 0.6), (a.x, a.y, zt + 0.6)], LAM if galpon else PAR, None if galpon else C._color, C.cp)
        d = b - a
        if d.length > 0.3:
            m = (a + b) / 2
            C.caja((m.x, m.y, zt + 0.6), (d.length + 0.1, 0.25, 0.06), ZOC, (0, 0, math.atan2(d.y, d.x)))


def main():
    vieja = bpy.data.objects.get("Edificios")
    if vieja:
        bpy.data.objects.remove(vieja, do_unlink=True)
    col = bpy.data.collections.get("Edificios_genericos")
    if col:
        for ob in list(col.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
    else:
        col = bpy.data.collections.new("Edificios_genericos")
        bpy.context.scene.collection.children.link(col)
    D = json.load(open(os.path.join(DATOS, "svbs.json")))
    ub = json.load(open(os.path.join(DATOS, "ubicaciones.json"), encoding="utf-8"))["edificios"]
    excluir = [(u["este"], u["norte"], u["excluir"]) for u in ub.values() if "excluir" in u]
    img = bpy.data.images.load(os.path.join(DATOS, "sat_6km.png"), check_existing=True)
    w, h = img.size
    buf = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(buf)
    px = buf.reshape(h, w, 4)

    def color_techo(e, n):
        j = int((e + SAT_INT) / (2 * SAT_INT) * w)
        i = int((n + SAT_INT) / (2 * SAT_INT) * h)
        c = px[max(i - 1, 0):i + 2, max(j - 1, 0):j + 2, :3].reshape(-1, 3).mean(axis=0)
        c = np.clip(c, 0, 1) ** 2.2                                   # la foto viene en sRGB
        return (*c.tolist(), 1.0)
    terreno = bpy.data.objects["Terreno"]

    def cota(x, y):
        ok, p, _n, _i = terreno.ray_cast((x, y, 3000.0), (0, 0, -1))
        return p.z if ok else 0.0
    rnd = random.Random(7)
    colores, pesos = zip(*PALETA)
    C = Ctx()
    n_ed = n_dos = 0
    for b in D["buildings"]:
        pts = [Vector((p[1], p[0])) for p in b["p"]]
        if len(pts) > 2 and pts[0] == pts[-1]:
            pts = pts[:-1]
        if len(pts) < 3:
            continue
        cx = sum(p.x for p in pts) / len(pts)
        cy = sum(p.y for p in pts) / len(pts)
        if not (ZONA[0] < cx < ZONA[1] and ZONA[2] < cy < ZONA[3]):
            continue
        if any(math.hypot(cx - e, cy - n) < r or any(math.hypot(p.x - e, p.y - n) < r for p in pts)
               for e, n, r in excluir):
            continue
        area2 = sum(pts[i].x * pts[i - 1].y - pts[i - 1].x * pts[i].y for i in range(len(pts)))
        area = 0.5 * abs(area2)
        if area < 12:
            continue
        if area2 > 0:                       # area2 > 0 = horaria: se pasa a antihoraria, con afuera a la derecha
            pts = list(reversed(pts))
        if area > 2500:
            alto = 13.0 + rnd.random() * 3
        elif area > 800:
            alto = 7.5 + rnd.random() * 2.5
        else:
            alto = 3.6 + rnd.choice((0, 0, 0, 3.0)) + rnd.random() * 0.6
        galpon = area > 2500
        pisos = max(1, int(alto / PISO))
        suelo = min(cota(p.x, p.y) for p in pts)
        pared = (*rnd.choices(colores, pesos)[0], 1.0)
        C._color = pared
        techo = color_techo(cx, cy)
        lados = [(pts[(i + 1) % len(pts)] - pts[i]).length for i in range(len(pts))]
        largo = max(range(len(pts)), key=lambda i: lados[i])
        for i in range(len(pts)):
            fachada(C, pts[i], pts[(i + 1) % len(pts)], suelo, alto, pisos, pared, galpon, rnd, i == largo)
        if not galpon and area < 1200 and angulos_rectos(pts):
            techo_dos_aguas(C, pts, suelo, alto, techo)
            n_dos += 1
        else:
            techo_plano(C, pts, suelo, alto, techo, galpon)
        n_ed += 1
    ob = C.crear("Edificios", materiales(), col)
    print("edificios genéricos:", n_ed, "| a dos aguas:", n_dos, "| caras:", len(ob.data.polygons))
    bpy.ops.wm.save_mainfile()


if __name__ == "__main__":
    main()
