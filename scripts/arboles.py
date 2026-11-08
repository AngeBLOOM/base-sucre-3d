"""Árboles de sombra como los de la base (mangos y samanes de las fotos): tronco recto y grueso, ramas que abren hacia
la copa y una copa ancha en cúpula, cerrada. Las hojas son tarjetas sacadas del island_tree de Poly Haven (CC0,
con su textura y transparencia) agrandadas y teñidas de verde oscuro, repartidas en la cáscara de la copa, con un
núcleo oscuro adentro para que no se vea a través. ~15 mil triángulos por árbol (el island_tree tenía 322 mil).

    import arboles; variantes = arboles.mallas()      # [(malla, alto), ...], con y sin cal en el tronco
"""
import math
import random

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector


def plantillas(n=60):
    """Tarjetas de hoja del island_tree: posiciones (respecto a su centro) y UV por esquina."""
    me = bpy.data.objects["island_tree_02_LOD1"].data
    hojas = {i for i, m in enumerate(me.materials) if m and "leaves" in m.name.lower()}
    uv = me.uv_layers.active.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    capa = bm.loops.layers.uv.active
    visto, out = set(), []
    paso = max(1, len(bm.faces) // (n * 40))
    for i in range(0, len(bm.faces), paso):
        f = bm.faces[i]
        if f.index in visto or f.material_index not in hojas:
            continue
        isla, pila = [], [f]
        visto.add(f.index)
        while pila:
            g = pila.pop()
            isla.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in visto and h.material_index in hojas:
                        visto.add(h.index)
                        pila.append(h)
        vs = list({v for g in isla for v in g.verts})
        c = sum((v.co for v in vs), Vector()) / len(vs)
        tam = max((v.co - c).length for v in vs)
        if tam < 1e-4:
            continue
        idx = {v: k for k, v in enumerate(vs)}
        caras = [([idx[l.vert] for l in g.loops], [tuple(l[capa].uv) for l in g.loops]) for g in isla]
        out.append(([(v.co - c) / tam for v in vs], caras))
        if len(out) >= n:
            break
    bm.free()
    del uv
    return out


def mat_hoja_mango():
    m = bpy.data.materials.get("Hoja_mango")
    if m:
        return m
    base = bpy.data.objects["island_tree_02_LOD1"].data.materials
    src = next(x for x in base if x and "leaves" in x.name.lower())
    m = src.copy()
    m.name = "Hoja_mango"
    nt = m.node_tree
    b = next((n for n in nt.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled"), None)
    if b and b.inputs["Base Color"].links:
        s = b.inputs["Base Color"].links[0].from_socket
        hs = nt.nodes.new("ShaderNodeHueSaturation")
        hs.inputs["Hue"].default_value = 0.55         # del verde oliva al verde de mango
        hs.inputs["Saturation"].default_value = 1.15
        hs.inputs["Value"].default_value = 0.62
        nt.links.new(s, hs.inputs["Color"])
        nt.links.new(hs.outputs["Color"], b.inputs["Base Color"])
    return m


def mat_corteza():
    m = bpy.data.materials.get("Corteza_mango")
    if m:
        return m
    m = bpy.data.materials.new("Corteza_mango")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    co = nt.nodes.new("ShaderNodeTexCoord")
    ru = nt.nodes.new("ShaderNodeTexNoise")
    ru.inputs["Scale"].default_value = 6.0
    ru.inputs["Detail"].default_value = 8
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (3.0, 3.0, 0.6)          # vetas a lo largo del tronco
    nt.links.new(co.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], ru.inputs["Vector"])
    ra = nt.nodes.new("ShaderNodeValToRGB")
    ra.color_ramp.elements[0].color = (0.05, 0.04, 0.03, 1)
    ra.color_ramp.elements[1].color = (0.20, 0.17, 0.13, 1)
    nt.links.new(ru.outputs["Fac"], ra.inputs["Fac"])
    nt.links.new(ra.outputs["Color"], b.inputs["Base Color"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.6
    nt.links.new(ru.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = 0.9
    return m


class Malla:
    def __init__(self):
        self.V, self.F, self.MI, self.UV = [], [], [], []

    def cara(self, cos, mi, uvs=None):
        i0 = len(self.V)
        self.V += [tuple(c) for c in cos]
        self.F.append(tuple(range(i0, i0 + len(cos))))
        self.MI.append(mi)
        self.UV += uvs or [(0.5, 0.5)] * len(cos)

    def tubo(self, a, b, r0, r1, mi, seg=10, cal=None):
        """Rama o tronco de a a b; cal = altura (m sobre a) hasta donde va pintado de blanco (material 3)."""
        d = b - a
        q = d.to_track_quat("Z", "Y")
        n = 6 if cal else 3
        anillos = []
        for k in range(n + 1):
            t = k / n
            if cal and k <= n - 3:
                t = min(cal / d.length, 0.9) * k / (n - 3)
            c = a + d * t
            r = r0 + (r1 - r0) * t
            anillos.append([c + q @ Vector((r * math.cos(2 * math.pi * j / seg), r * math.sin(2 * math.pi * j / seg), 0))
                            for j in range(seg)])
        for k in range(n):
            mi_k = 3 if (cal and k < n - 3) else mi
            for j in range(seg):
                p = [anillos[k][j], anillos[k][(j + 1) % seg], anillos[k + 1][(j + 1) % seg], anillos[k + 1][j]]
                self.cara(p, mi_k)

    def crear(self, nombre, mats):
        me = bpy.data.meshes.new(nombre)
        me.from_pydata(self.V, [], self.F)
        me.polygons.foreach_set("material_index", self.MI)
        uv = me.uv_layers.new(name="UVMap")
        uv.data.foreach_set("uv", np.array(self.UV, np.float32).ravel())
        for m in mats:
            me.materials.append(m)
        me.update()
        try:
            me.shade_smooth()
        except AttributeError:
            pass
        return me


def arbol(nombre, semilla, tmpl, cal):
    """Árbol de ~10 m: tronco de 2,2–3,5 m, 4–6 ramas maestras, copa en cúpula de 4,5–6,5 m de radio."""
    r = random.Random(semilla)
    H = 10.0
    hb = r.uniform(2.2, 3.4)                             # alto del tronco limpio
    R = r.uniform(4.6, 6.4)                              # radio de la copa
    Hc = H - hb + 0.6
    cz = hb + Hc * 0.42                                  # centro de la cúpula (más ancha que alta, base aplanada)
    M = Malla()
    lean = Vector((r.uniform(-0.25, 0.25), r.uniform(-0.25, 0.25), 0))
    base, cima = Vector((0, 0, -0.3)), Vector((0, 0, hb)) + lean
    rt = r.uniform(0.22, 0.32)
    M.tubo(base, cima, rt * 1.12, rt, 0, 12, cal=1.3 if cal else None)
    for k in range(r.randint(4, 6)):                     # ramas maestras
        a = 2 * math.pi * k / 5 + r.uniform(-0.4, 0.4)
        fin = Vector((math.cos(a) * R * r.uniform(0.45, 0.7), math.sin(a) * R * r.uniform(0.45, 0.7),
                      cz + r.uniform(-0.5, 1.5)))
        mid = cima.lerp(fin, 0.5) + Vector((0, 0, 0.6))
        M.tubo(cima, mid, rt * 0.62, rt * 0.42, 0, 8)
        M.tubo(mid, fin, rt * 0.42, rt * 0.16, 0, 6)
    # núcleo oscuro de la copa (icosfera aplastada)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * R * 0.78, v.co.y * R * 0.78, max(v.co.z, -0.55) * Hc * 0.4)) + Vector((0, 0, cz))
    for f in bm.faces:
        M.cara([v.co for v in f.verts], 2)
    bm.free()
    # tarjetas de hoja en la cáscara de la cúpula
    n = int(125 * R * R)
    lobulos = [Vector((r.gauss(0, 1), r.gauss(0, 1), abs(r.gauss(0, 0.6)))).normalized() for _ in range(7)]
    for _ in range(n):
        while True:
            d = Vector((r.gauss(0, 1), r.gauss(0, 1), r.gauss(0, 1)))
            if d.length > 1e-6:
                d.normalize()
                if d.z > -0.55:
                    break
        lob = 0.84 + 0.26 * max(max(d.dot(l), 0.0) for l in lobulos) ** 2      # copa con lóbulos
        u = r.uniform(0.74, 1.0) ** 0.5 * lob
        p = Vector((d.x * R * u, d.y * R * u, d.z * Hc * 0.5 * u)) + Vector((0, 0, cz))
        p.x += r.uniform(-0.4, 0.4)
        p.y += r.uniform(-0.4, 0.4)
        p.z -= 0.35 * (p.xy.length / R) ** 2 * Hc * 0.3          # bordes que caen un poco
        vs, caras = tmpl[r.randrange(len(tmpl))]
        escala = r.uniform(0.3, 0.46)
        rot = (Quaternion(Vector((0, 0, 1)), r.uniform(0, 2 * math.pi))
               @ Quaternion(Vector((1, 0, 0)), r.uniform(-0.8, 0.8)))
        T = Matrix.Translation(p) @ rot.to_matrix().to_4x4() @ Matrix.Scale(escala, 4)
        pts = [T @ v for v in vs]
        for ids, uvs in caras:
            M.cara([pts[i] for i in ids], 1, uvs)
    me = M.crear(nombre, [mat_corteza(), mat_hoja_mango(), _interior(),
                          bpy.data.materials.get("Cal_blanca") or _cal()])
    return me, H


def _interior():
    m = bpy.data.materials.get("Copa_interior")
    if m:
        return m
    m = bpy.data.materials.new("Copa_interior")
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (0.010, 0.030, 0.008, 1)
    b.inputs["Roughness"].default_value = 0.9
    return m


def _cal():
    m = bpy.data.materials.new("Cal_blanca")
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (0.84, 0.84, 0.82, 1)
    b.inputs["Roughness"].default_value = 0.92
    return m


def mallas(n=4):
    """n formas, cada una con y sin cal: {'cal': [(malla, alto)...], 'sin': [...]}."""
    if "Mango_0_sin" in bpy.data.meshes:
        return {k: [(bpy.data.meshes[f"Mango_{i}_{k}"], 10.0) for i in range(n)] for k in ("cal", "sin")}
    tmpl = plantillas()
    out = {"cal": [], "sin": []}
    for i in range(n):
        for k in ("cal", "sin"):
            out[k].append(arbol(f"Mango_{i}_{k}", 100 + i, tmpl, k == "cal"))
    print("árboles de sombra: %d formas, %d caras cada uno" % (n, len(out["sin"][0][0].polygons)))
    return out
