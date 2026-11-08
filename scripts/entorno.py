"""Entorno del recorrido de la portada a la DIDA: lo que en las capturas del camino se veía como campo borroso.
Se corre después de palmas_pasto.py y antes de acabado.py:

    blender --background BaseSucre.blend --python entorno.py

Todo sale de la foto satelital de 1,5 m/px (datos/sat_6km.png), nada inventado:
- cada píxel se clasifica en copa de árbol (oscuro y verde, más oscuro que su entorno), pasto verde o sabana seca;
- el suelo del terreno lleva encima el detalle de la textura de grama (relieve y grano) modulando el color satelital,
  para que de cerca no se vea la mancha estirada;
- pasto 3D a cada lado de la ruta: grama verde donde el satélite es verde y monte alto y seco donde es sabana;
- árboles donde el satélite muestra copas (la hilera que bordea la calle entre la portada y los hangares, los del
  conjunto administrativo), con el modelo completo cerca de la calle y uno aligerado más lejos.
"""
import json
import math
import os
import random
import sys

import bpy
import numpy as np
from mathutils import Vector, kdtree
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import entrada as E  # noqa: E402
import camino_dida as CD  # noqa: E402
import palmas_pasto as PP  # noqa: E402

RAIZ = os.path.dirname(E.TEXTURAS)
rnd = random.Random(57)
ANCHO_PASTO = 42.0          # pasto 3D hasta esta distancia del eje de la ruta
LLENO = 18.0                # densidad completa hasta aquí, luego se desvanece
ANCHO_ARBOLES = 120.0       # árboles hasta esta distancia
CERCA = 22.0                # modelo completo (322 mil triángulos) solo junto a la calle, y como mucho MAX_COMPLETOS
MEDIO = 60.0                # hasta aquí el aligerado al 5 %; más lejos, uno al 1,5 %
MAX_COMPLETOS = 140
CELDA_ARBOL = 9.0
DENS = {1: 1.8, 2: 1.3, 3: 0.45}      # matas/m²: verde, seco, bajo copa


# ----------------------------------------------------------------------------------- satélite
class Satelite:
    def __init__(self, e0, e1, n0, n1):
        img = bpy.data.images.load(os.path.join(RAIZ, "datos", "sat_6km.png"), check_existing=True)
        w, h = img.size
        buf = np.empty(w * h * 4, dtype=np.float32)
        img.pixels.foreach_get(buf)
        self.m = 6000.0 / w
        self.j0, self.i0 = int((e0 + 3000) / self.m), int((n0 + 3000) / self.m)
        j1, i1 = int((e1 + 3000) / self.m), int((n1 + 3000) / self.m)
        px = buf.reshape(h, w, 4)[self.i0:i1, self.j0:j1, :3].astype(np.float64)     # fila 0 = sur
        del buf
        r, g, b = px[..., 0], px[..., 1], px[..., 2]
        lum = px.mean(-1)
        sat = px.max(-1) - px.min(-1)
        loc = self._media(lum, 12)
        copa = (lum < 0.33) & (lum < loc - 0.045) & (g > r * 1.02) & (g > b * 1.05)
        verde = ~copa & (g > r * 1.03) & (g > b * 1.1) & (lum < 0.55)
        seco = ~copa & ~verde & (r >= g * 0.97) & (sat > 0.07) & (lum < 0.55) & (r > b * 1.15)
        self.clase = np.zeros(lum.shape, np.uint8)
        self.clase[verde] = 1
        self.clase[seco] = 2
        self.clase[copa] = 3
        print("satélite: copa %.1f%%  verde %.1f%%  seco %.1f%%" % (100 * copa.mean(), 100 * verde.mean(),
                                                                     100 * seco.mean()))

    @staticmethod
    def _media(a, k):
        h, w = a.shape
        I = np.zeros((h + 1, w + 1))
        I[1:, 1:] = a.cumsum(0).cumsum(1)
        y0, y1 = np.clip(np.arange(h) - k, 0, h), np.clip(np.arange(h) + k + 1, 0, h)
        x0, x1 = np.clip(np.arange(w) - k, 0, w), np.clip(np.arange(w) + k + 1, 0, w)
        s = I[y1][:, x1] - I[y0][:, x1] - I[y1][:, x0] + I[y0][:, x0]
        return s / ((y1 - y0)[:, None] * (x1 - x0)[None, :])

    def en(self, e, n):
        i = int((n + 3000) / self.m) - self.i0
        j = int((e + 3000) / self.m) - self.j0
        if 0 <= i < self.clase.shape[0] and 0 <= j < self.clase.shape[1]:
            return int(self.clase[i, j])
        return 0

    def bloque(self, e, n, lado):
        """Píxeles de un cuadro de «lado» metros con esquina en (e, n)."""
        i = int((n + 3000) / self.m) - self.i0
        j = int((e + 3000) / self.m) - self.j0
        k = max(1, int(round(lado / self.m)))
        return self.clase[max(i, 0):max(i + k, 0), max(j, 0):max(j + k, 0)], i, j, k


# ----------------------------------------------------------------------------------- suelo
def suelo_detalle():
    """Grano de la grama (CC0, texturas/pasto) multiplicando el color satelital del terreno, con relieve; manchas
    medianas de ruido para romper lo liso de la foto. El lago no se toca."""
    m = bpy.data.materials.get("Suelo_Terreno")
    if m is None or m.get("detalle"):
        return
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    fuente = bsdf.inputs["Base Color"].links[0].from_socket
    agua = next((n for n in nt.nodes if n.bl_idname == "ShaderNodeTexImage" and n.image
                 and n.image.name.startswith("agua")), None)
    carpeta = os.path.join(E.TEXTURAS, "pasto")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapa = nt.nodes.new("ShaderNodeMapping")
    mapa.inputs["Scale"].default_value = (1 / 2.2, 1 / 2.2, 1 / 2.2)
    nt.links.new(coord.outputs["Object"], mapa.inputs["Vector"])

    def imagen(nombre, dato):
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(os.path.join(carpeta, nombre), check_existing=True)
        if dato:
            t.image.colorspace_settings.name = "Non-Color"
        nt.links.new(mapa.outputs["Vector"], t.inputs["Vector"])
        return t
    col = imagen("color.jpg", False)
    bw = nt.nodes.new("ShaderNodeRGBToBW")
    nt.links.new(col.outputs["Color"], bw.inputs["Color"])
    rango = nt.nodes.new("ShaderNodeMapRange")          # luminancia media lineal de la textura ≈ 0,2
    rango.inputs["From Min"].default_value = 0.09
    rango.inputs["From Max"].default_value = 0.32
    rango.inputs["To Min"].default_value = 0.55
    rango.inputs["To Max"].default_value = 1.45
    nt.links.new(bw.outputs["Val"], rango.inputs["Value"])
    ruido = nt.nodes.new("ShaderNodeTexNoise")
    ruido.inputs["Scale"].default_value = 0.06
    ruido.inputs["Detail"].default_value = 4
    nt.links.new(coord.outputs["Object"], ruido.inputs["Vector"])
    r2 = nt.nodes.new("ShaderNodeMapRange")
    r2.inputs["To Min"].default_value = 0.86
    r2.inputs["To Max"].default_value = 1.12
    nt.links.new(ruido.outputs["Fac"], r2.inputs["Value"])
    prod = nt.nodes.new("ShaderNodeMath")
    prod.operation = "MULTIPLY"
    nt.links.new(rango.outputs["Result"], prod.inputs[0])
    nt.links.new(r2.outputs["Result"], prod.inputs[1])
    mezcla = nt.nodes.new("ShaderNodeMix")
    mezcla.data_type = "RGBA"
    mezcla.blend_type = "MULTIPLY"
    mezcla.clamp_result = True
    nt.links.new(fuente, mezcla.inputs["A"])
    nt.links.new(prod.outputs["Value"], mezcla.inputs["B"])
    if agua:
        inv = nt.nodes.new("ShaderNodeMath")
        inv.operation = "SUBTRACT"
        inv.inputs[0].default_value = 1.0
        nt.links.new(agua.outputs["Color"], inv.inputs[1])
        nt.links.new(inv.outputs["Value"], mezcla.inputs["Factor"])
    else:
        mezcla.inputs["Factor"].default_value = 1.0
    nt.links.new(mezcla.outputs["Result"], bsdf.inputs["Base Color"])
    if not bsdf.inputs["Normal"].links:
        nor = imagen("normal.jpg", True)
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = 0.6
        nt.links.new(nor.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    m["detalle"] = True
    print("suelo con detalle de grama")


# ----------------------------------------------------------------------------------- pasto 3D
def mata_seca():
    nombre = "Mata_pasto_seco"
    if nombre in bpy.data.objects:
        return bpy.data.objects[nombre]
    base = PP.mata_pasto()
    me = base.data.copy()
    me.name = nombre
    me.materials.clear()
    me.materials.append(PP.mat_hoja("Pasto_3d_seco", (0.10, 0.09, 0.03), (0.40, 0.35, 0.14), (0.62, 0.52, 0.30), 0.35))
    ob = bpy.data.objects.new(nombre, me)
    bpy.data.collections["Biblioteca_vegetacion"].objects.link(ob)
    return ob


def grupo(mata, nombre):
    ng = bpy.data.node_groups.get(nombre)
    if ng:
        return ng
    ng = PP.grupo_instancias(PP.mata_pasto()).copy()
    ng.name = nombre
    for n in ng.nodes:
        if n.bl_idname == "GeometryNodeObjectInfo":
            n.inputs["Object"].default_value = mata
    return ng


def muestras_ruta(pts, paso=2.0):
    out = CD.a_lo_largo(pts, paso)
    kd = kdtree.KDTree(len(out))
    for k, ((x, y), _) in enumerate(out):
        kd.insert((x, y, 0.0), k)
    kd.balance()
    return out, kd


class Suelo:
    """Cota del terreno y obstáculos (calles, plataforma, edificios, céspedes de cada edificio, palmas...) en un solo
    árbol de rayos. (scene.ray_cast era lentísimo: cada rayo revisaba las 188 mil matas de pasto instanciadas.)"""
    SIN = {"Vegetacion_real", "Biblioteca_vegetacion", "Pasto_3d", "Entorno_ruta"}

    def __init__(self, caja):
        e0, e1, n0, n1 = caja
        deps = bpy.context.evaluated_depsgraph_get()
        self.terreno = bpy.data.objects["Terreno"]
        grupos = {False: ([], []), True: ([], [])}      # obstáculos | céspedes (los árboles sí van sobre césped)
        n_obs = 0
        for ob in bpy.data.objects:
            if ob.type != "MESH" or ob.name in ("Terreno", "Paisaje_lejano", "Paisaje_regional") or ob.hide_render \
                    or ob.name.startswith(("Pasto3d", "Mata_", "Puntos_")) \
                    or any(c.name in self.SIN or c.hide_render for c in ob.users_collection):
                continue
            bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
            if max(c.x for c in bb) < e0 or min(c.x for c in bb) > e1 or max(c.y for c in bb) < n0 \
                    or min(c.y for c in bb) > n1:
                continue
            ev = ob.evaluated_get(deps)
            me = ev.to_mesh()
            me.calc_loop_triangles()
            nv = len(me.vertices)
            co = np.empty(nv * 3, np.float32)
            me.vertices.foreach_get("co", co)
            co = co.reshape(-1, 3)
            M = np.array(ob.matrix_world, np.float32)
            co = co @ M[:3, :3].T + M[:3, 3]
            tri = np.empty(len(me.loop_triangles) * 3, np.int32)
            me.loop_triangles.foreach_get("vertices", tri)
            vs, ts = grupos[ob.name.startswith("Pasto")]
            base = sum(len(v) for v in vs)
            vs.append(co)
            ts.append(tri.reshape(-1, 3) + base)
            ev.to_mesh_clear()
            n_obs += 1
        self.bvh = {}
        for k, (vs, ts) in grupos.items():
            V = np.concatenate(vs).tolist() if vs else [(0, 0, -9999.0)] * 3
            T = np.concatenate(ts).tolist() if ts else [(0, 1, 2)]
            self.bvh[k] = BVHTree.FromPolygons(V, T, all_triangles=True)
        print("obstáculos:", n_obs, "objetos")

    def z(self, x, y):
        ok, p, _n, _i = self.terreno.ray_cast((x, y, 3000.0), (0, 0, -1))
        return p.z if ok else None

    def libre(self, x, y, z, cesped=True):
        """Sin obstáculo encima; con cesped=True tampoco vale un césped de edificio (ese ya tiene su pasto)."""
        for k in ((False, True) if cesped else (False,)):
            p, *_r = self.bvh[k].ray_cast(Vector((x, y, z + 80.0)), Vector((0, 0, -1)), 80.6)
            if p is not None:
                return False
        return True


def sembrar_pasto(col, sat, muestras, kd, suelo):
    nubes = {1: ([], [], []), 2: ([], [], [])}
    dmax = max(DENS.values())
    gen = np.random.default_rng(5)
    for k, ((x, y), (dx, dy)) in enumerate(muestras):
        nx, ny = -dy, dx
        n = gen.poisson(2.0 * 2 * ANCHO_PASTO * dmax)
        a = gen.random(n) * 2.0
        u = (gen.random(n) * 2 - 1) * ANCHO_PASTO
        acepta = gen.random(n)
        for aa, uu, ac in zip(a, u, acepta):
            px, py = x + dx * aa + nx * uu, y + dy * aa + ny * uu
            _co, idx, d = kd.find((px, py, 0.0))
            if idx != k:                                   # en las curvas, cada punto lo siembra una sola muestra
                continue
            f = 1.0 if d < LLENO else max(0.0, (ANCHO_PASTO - d) / (ANCHO_PASTO - LLENO))
            c = sat.en(px, py)
            if c == 0 or ac > f * DENS[c] / dmax:
                continue
            z = suelo.z(px, py)
            if z is None or not suelo.libre(px, py, z):
                continue
            tipo = 2 if c == 2 else 1
            p, gi, es = nubes[tipo]
            p.append((px, py, z))
            gi.append(rnd.uniform(0, 2 * math.pi))
            es.append(rnd.uniform(1.5, 2.7) if tipo == 2 else rnd.uniform(0.8, 1.5))
    matas = {1: PP.mata_pasto(), 2: mata_seca()}
    grupos = {1: PP.grupo_instancias(matas[1]), 2: grupo(matas[2], "Sembrar_pasto_seco")}
    for tipo, (p, gi, es) in nubes.items():
        if not p:
            continue
        me = bpy.data.meshes.new(f"Puntos_ruta_{tipo}")
        me.from_pydata(p, [], [])
        for nombre, vals in (("giro", gi), ("escala", es)):
            at = me.attributes.new(nombre, "FLOAT", "POINT")
            at.data.foreach_set("value", vals)
        ob = bpy.data.objects.new("Pasto3d_ruta_" + ("verde" if tipo == 1 else "seco"), me)
        col.objects.link(ob)
        ob.modifiers.new("Sembrar", "NODES").node_group = grupos[tipo]
        print(f"pasto de la ruta ({'verde' if tipo == 1 else 'seco'}): {len(p)} matas")


# ----------------------------------------------------------------------------------- árboles
def arbol_ligero(ratio=0.05, nombre="Arbol_ligero", densidad=1.6):
    """Copia del island_tree aligerada para los árboles lejos de la calle. Antes se diezmaba la malla entera y las
    hojas (tarjetas sueltas) se deshacían: la copa salía rala, casi sin hojas. Ahora se conservan tarjetas de hoja
    ENTERAS (una de cada 1/ratio), agrandadas para que la copa quede igual de tupida, y solo el tronco y las ramas
    se diezman."""
    import bmesh
    if nombre in bpy.data.meshes:
        return bpy.data.meshes[nombre]
    src = bpy.data.objects["island_tree_02_LOD1"].data
    hojas = {i for i, m in enumerate(src.materials) if m and any(k in m.name.lower() for k in ("leaf", "leaves", "hoja"))}
    if not hojas:                                   # sin nombres claros: el material con más caras son las hojas
        cuenta = {}
        for pl in src.polygons:
            cuenta[pl.material_index] = cuenta.get(pl.material_index, 0) + 1
        hojas = {max(cuenta, key=cuenta.get)}
    bm = bmesh.new()
    bm.from_mesh(src)
    bm.faces.ensure_lookup_table()
    visto = set()
    quitar = []
    k = 0
    paso = max(1, round(1 / ratio) // 3)            # tarjetas que se quedan: 1 de cada «paso»
    # el island_tree es de copa abierta; los mangos y samanes de las fotos la tienen cerrada: hojas más grandes
    escala = math.sqrt(paso) * densidad
    for f in bm.faces:
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
        k += 1
        if k % paso:
            quitar += isla
        else:
            vs = {v for g in isla for v in g.verts}
            c = sum((v.co for v in vs), Vector()) / len(vs)
            for v in vs:
                v.co = c + (v.co - c) * escala
    bmesh.ops.delete(bm, geom=quitar, context="FACES")
    ramas = [f for f in bm.faces if f.material_index not in hojas]
    if ramas:
        bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(8), verts=list({v for f in ramas for v in f.verts}),
                                 edges=list({e for f in ramas for e in f.edges}))
    me = bpy.data.meshes.new(nombre)
    bm.to_mesh(me)
    bm.free()
    for m in src.materials:
        me.materials.append(m)
    print("árbol ligero %s: %d caras (%d tarjetas de hoja, 1 de cada %d)" % (nombre, len(me.polygons), k, paso))
    return me


def plantar_arboles(col, sat, muestras, kd, suelo):
    # ella: «esos árboles tan raros» (el island_tree es un arbolito retorcido tipo olivo): árboles de sombra propios
    # tipo mango o samán (arboles.py), con cal en el tronco junto a la calle como en las fotos
    import arboles
    variantes = arboles.mallas()
    cambiar_arboles_viejos(variantes)
    # plantas que ya existen (no duplicar junto a ellas)
    hay = [o.matrix_world.translation for o in bpy.data.objects
           if o.type == "MESH" and o.name.startswith(("Arbol", "Palma", "Mata_real", "Arbusto"))]
    kh = kdtree.KDTree(max(len(hay), 1))
    for k, p in enumerate(hay):
        kh.insert((p.x, p.y, 0.0), k)
    kh.balance()
    xs = [m[0][0] for m in muestras]
    ys = [m[0][1] for m in muestras]
    e0, e1 = min(xs) - ANCHO_ARBOLES, max(xs) + ANCHO_ARBOLES
    n0, n1 = min(ys) - ANCHO_ARBOLES, max(ys) + ANCHO_ARBOLES
    L = CELDA_ARBOL
    frac = {}
    for iy in range(int((n1 - n0) / L)):
        for ix in range(int((e1 - e0) / L)):
            b, *_ = sat.bloque(e0 + ix * L, n0 + iy * L, L)
            if b.size:
                frac[ix, iy] = float((b == 3).mean())
    n_cerca = n_lejos = 0
    for (ix, iy), fr in frac.items():
        if fr < 0.42:
            continue
        x0, y0 = e0 + ix * L, n0 + iy * L
        _co, _i, d = kd.find((x0 + L / 2, y0 + L / 2, 0.0))
        if d > ANCHO_ARBOLES:
            continue
        b, i, j, k = sat.bloque(x0, y0, L)
        yy, xx = np.nonzero(b == 3)
        cx = x0 + (xx.mean() + 0.5) * sat.m + rnd.uniform(-1, 1)
        cy = y0 + (yy.mean() + 0.5) * sat.m + rnd.uniform(-1, 1)
        if kh.find((cx, cy, 0.0))[2] is not None and kh.find((cx, cy, 0.0))[2] < 6.0:
            continue
        # el tronco no puede caer en una calle, la plataforma ni un edificio
        z = suelo.z(cx, cy)
        if z is None or not all(suelo.libre(cx + ox, cy + oy, z, cesped=False)
                                for ox, oy in ((0, 0), (2.0, 0), (-2.0, 0), (0, 2.0), (0, -2.0))):
            continue
        vec = [frac.get((ix + a, iy + c), 0.0) for a in (-1, 0, 1) for c in (-1, 0, 1)]
        masa = sum(vec) / 9.0                              # copa grande y corrida → árbol más grande
        h = 7.0 + 6.0 * masa + rnd.uniform(-0.8, 0.8)
        cerca = d < 16.0
        me, alto_modelo = rnd.choice(variantes["cal" if cerca else "sin"])
        ob = bpy.data.objects.new("Arbol_ruta", me)
        ob.location = (cx, cy, z - 0.05)
        ob.rotation_euler = (0, 0, rnd.uniform(0, 2 * math.pi))
        s = h / alto_modelo
        ob.scale = (s * rnd.uniform(0.9, 1.1), s * rnd.uniform(0.9, 1.1), s)
        col.objects.link(ob)
        n_cerca += cerca
        n_lejos += not cerca
    print("árboles del satélite: %d cerca de la calle, %d más lejos" % (n_cerca, n_lejos))


def cambiar_arboles_viejos(variantes):
    """Los árboles que calidad.py había puesto con el island_tree (entrada, DIDA, G14...) pasan al árbol de sombra,
    con la misma altura."""
    viejo = bpy.data.objects["island_tree_02_LOD1"]
    alto_viejo = viejo.dimensions.z / max(viejo.scale.z, 1e-6)
    n = 0
    for ob in bpy.data.objects:
        if ob.type == "MESH" and ob.data == viejo.data and ob != viejo:
            h = alto_viejo * ob.scale.z
            me, alto = rnd.choice(variantes["sin"])
            ob.data = me
            s = max(h, 6.0) / alto
            ob.scale = (s, s, s)
            n += 1
    print("árboles viejos cambiados:", n)


def malla_tenida(base, nombre, hue, sat=1.1, val=1.15):
    """Copia de la malla de un modelo de Poly Haven con sus hojas cambiadas de tono (no hay modelos CC0 de setos
    amarillos ni de crotos: se tiñe la searsia, que tiene la hoja parecida)."""
    if nombre in bpy.data.meshes:
        return bpy.data.meshes[nombre]
    me = base.copy()
    me.name = nombre
    for i, m in enumerate(me.materials):
        if m is None or not m.use_nodes:
            continue
        m2 = m.copy()
        m2.name = f"{m.name}_{nombre}"
        nt = m2.node_tree
        b = next((n for n in nt.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled"), None)
        if b and b.inputs["Base Color"].links:
            src = b.inputs["Base Color"].links[0].from_socket
            hs = nt.nodes.new("ShaderNodeHueSaturation")
            hs.inputs["Hue"].default_value = hue
            hs.inputs["Saturation"].default_value = sat
            hs.inputs["Value"].default_value = val
            nt.links.new(src, hs.inputs["Color"])
            nt.links.new(hs.outputs["Color"], b.inputs["Base Color"])
        me.materials[i] = m2
    return me


def plantas_jardin(col):
    """Setos amarillos (duranta), crotos rojos y amarillos y helechos en los puntos que dejó entrada_adentro.py."""
    v = bpy.data.objects.get("Adentro_plantas_plaza")
    if v is None or "plantas" not in v:
        return
    sear = [bpy.data.objects.get(f"searsia_lucida_{k}_LOD1") for k in "bcd"]
    sear = [o for o in sear if o]
    if not sear:
        print("no está la searsia en la biblioteca")
        return
    mallas = {"seto": [(malla_tenida(o.data, f"Seto_amarillo_{k}", 0.43, 1.25, 1.35), o.dimensions.z)
                       for k, o in enumerate(sear)],
              "croto": [(malla_tenida(o.data, f"Croto_rojo_{k}", 0.30, 1.4, 1.0), o.dimensions.z)
                        for k, o in enumerate(sear[:2])]
              + [(malla_tenida(o.data, f"Croto_amarillo_{k}", 0.38, 1.35, 1.25), o.dimensions.z)
                 for k, o in enumerate(sear[1:])],
              "helecho": [(o.data, o.dimensions.z) for o in sear]}
    n = 0
    for x, y, z, tipo, tam in json.loads(v["plantas"]):
        me, h = rnd.choice(mallas.get(tipo, mallas["seto"]))
        ob = bpy.data.objects.new("Planta_plaza", me)
        ob.location = (x, y, z - 0.05)
        ob.rotation_euler = (0, 0, rnd.uniform(0, 2 * math.pi))
        s = tam / max(h, 0.1)
        ob.scale = (s * rnd.uniform(1.0, 1.4), s * rnd.uniform(1.0, 1.4), s)
        col.objects.link(ob)
        n += 1
    print("plantas de jardín:", n)


def radio_base(me, cache={}):
    """Radio del tronco al pie (vértices de la malla a menos de 0,5 m del punto más bajo)."""
    if me.name in cache:
        return cache[me.name]
    nv = len(me.vertices)
    co = np.empty(nv * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    bajo = co[co[:, 2] < co[:, 2].min() + 0.5]
    r = float(np.percentile(np.hypot(bajo[:, 0], bajo[:, 1]), 90)) if len(bajo) else 0.3
    cache[me.name] = r
    return r


def arboles_paredon(col):
    """Ella: los árboles del estacionamiento de la entrada van pegados al paredón por DENTRO. Se plantan árboles de
    sombra en los alcorques que dejó entrada.py y se quitan los del satélite que quedaban justo por fuera del muro
    (eran esos mismos árboles, corridos unos metros)."""
    v = bpy.data.objects.get("Puntos_arboles_paredon")
    if v is None or "puntos" not in v:
        return
    import arboles
    variantes = arboles.mallas()
    padre = bpy.data.objects["Entrada_origen"]
    inv = padre.matrix_world.inverted()
    quitar = []
    for ob in col.objects:
        if ob.name.startswith("Arbol_ruta"):
            q = inv @ ob.matrix_world.translation
            if -52.0 < q.x < -34.0 and -80.0 < q.y < 5.0:
                quitar.append(ob)
    for ob in quitar:
        bpy.data.objects.remove(ob, do_unlink=True)
    pts = json.loads(v["puntos"])
    for x, y, z in pts:
        me, alto = rnd.choice(variantes["cal"])
        ob = bpy.data.objects.new("Arbol_paredon", me)
        ob.location = (x, y, z - 0.1)
        ob.rotation_euler = (0, 0, rnd.uniform(0, 2 * math.pi))
        s = rnd.uniform(11.5, 13.5) / alto              # los de la foto son grandes, de tronco grueso
        ob.scale = (s, s, s)
        col.objects.link(ob)
    print("árboles del paredón: %d plantados, %d quitados de afuera" % (len(pts), len(quitar)))


def troncos_blancos(col, kd):
    """Cal blanca al pie de los troncos, como todos los de las fotos: palmas de la entrada, del comedor y del CAA, y
    los árboles junto a la calle del recorrido."""
    import bmesh
    cal = bpy.data.materials.get("Cal_blanca") or E.material("Cal_blanca", (0.84, 0.84, 0.82), 0.92)
    bm = bmesh.new()
    n = 0
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        es_palma = ob.name.startswith(("Palma", "Bismarck")) and any(
            c.name in ("Entrada", "Comedor", "Comedor_vecinos") for c in ob.users_collection)
        es_arbol = False                         # los árboles de sombra ya traen la cal en el tronco
        if not (es_palma or es_arbol):
            continue
        mw = ob.matrix_world
        r = min(radio_base(ob.data) * max(mw.to_scale().x, 0.05), 0.42)
        p = mw.translation
        alto = 1.3 if es_palma else 1.5
        E.cilindro(bm, (p.x, p.y, p.z - 0.05), r * 1.12, r * 1.05, alto, 0, 16)
        n += 1
    E.objeto("Troncos_cal", bm, [cal], None, col)
    print("troncos pintados de blanco:", n)


def limpiar():
    col = bpy.data.collections.get("Entorno_ruta")
    if col:
        for ob in list(col.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
    else:
        col = bpy.data.collections.new("Entorno_ruta")
        bpy.context.scene.collection.children.link(col)
    return col


def main():
    col = limpiar()
    pts, _destino, largo = CD.ruta()
    muestras, kd = muestras_ruta(pts)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    sat = Satelite(min(xs) - 200, max(xs) + 200, min(ys) - 200, max(ys) + 200)
    suelo_detalle()
    suelo = Suelo((min(xs) - ANCHO_ARBOLES - 10, max(xs) + ANCHO_ARBOLES + 10,
                   min(ys) - ANCHO_ARBOLES - 10, max(ys) + ANCHO_ARBOLES + 10))
    sembrar_pasto(col, sat, muestras, kd, suelo)
    plantar_arboles(col, sat, muestras, kd, suelo)
    plantas_jardin(col)
    arboles_paredon(col)
    troncos_blancos(col, kd)
    bpy.ops.wm.save_mainfile()
    print("entorno listo, ruta de %.0f m" % largo)


if __name__ == "__main__":
    main()
