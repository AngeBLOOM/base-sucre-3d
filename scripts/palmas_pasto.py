"""Palmas creíbles y pasto en 3D. Se corre después de calidad.py y antes de acabado.py:

    blender --background BaseSucre.blend --python palmas_pasto.py

- Palma real (Roystonea, la de las avenidas de la base): tronco gris anillado y un poco abombado abajo, capitel
  verde brillante, unas 16 hojas arqueadas con ~70 hojuelas por lado en planos alternos (aspecto plumoso), puntas
  secas, color variado por hojuela y luz que traspasa la hoja; dos hojas viejas colgando, secas.
- Palma de Bismarck (frente a la DIDA): abanicos plateados plisados, con las puntas partidas y caídas.
  Las dos mallas nuevas reemplazan a las viejas en todas sus copias (las posiciones y tamaños no cambian).
- Pasto: matas de hojas finas sembradas en cada césped modelado, solo donde nada lo tapa (calles, aceras,
  plataforma, edificios), con más densidad en el centro y menos hacia el borde donde se funde con la foto
  satelital. Cada mata tiene su propio tono y tamaño.
"""
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

rnd = random.Random(41)
DENSIDAD = 5.0          # matas de pasto por m² en el centro de cada césped (bajar si la laptop no aguanta)


# ----------------------------------------------------------------------------------- materiales
def mat_hoja(nombre, verde_osc, verde_cla, seco, translucido=0.3):
    """Hoja con tono por hojuela («var»), punta seca según «t» (0 base → 1 punta) y algo de luz a través."""
    m = bpy.data.materials.get(nombre)
    if m:
        return m
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    nt = m.node_tree
    out = nt.nodes.get("Material Output")
    b = nt.nodes.get("Principled BSDF")
    var = nt.nodes.new("ShaderNodeAttribute")
    var.attribute_name = "var"
    t = nt.nodes.new("ShaderNodeAttribute")
    t.attribute_name = "t"
    obj = nt.nodes.new("ShaderNodeObjectInfo")
    mezcla_var = nt.nodes.new("ShaderNodeMath")
    mezcla_var.operation = "ADD"
    nt.links.new(var.outputs["Fac"], mezcla_var.inputs[0])
    k = nt.nodes.new("ShaderNodeMath")
    k.operation = "MULTIPLY"
    k.inputs[1].default_value = 0.5
    nt.links.new(obj.outputs["Random"], k.inputs[0])
    nt.links.new(k.outputs[0], mezcla_var.inputs[1])
    rampa = nt.nodes.new("ShaderNodeValToRGB")
    rampa.color_ramp.elements[0].color = (*verde_osc, 1)
    rampa.color_ramp.elements[1].color = (*verde_cla, 1)
    fr = nt.nodes.new("ShaderNodeMath")
    fr.operation = "FRACT"
    nt.links.new(mezcla_var.outputs[0], fr.inputs[0])
    nt.links.new(fr.outputs[0], rampa.inputs["Fac"])
    punta = nt.nodes.new("ShaderNodeMath")
    punta.operation = "POWER"
    punta.inputs[1].default_value = 5.0
    nt.links.new(t.outputs["Fac"], punta.inputs[0])
    kp = nt.nodes.new("ShaderNodeMath")
    kp.operation = "MULTIPLY"
    kp.inputs[1].default_value = 0.75
    nt.links.new(punta.outputs[0], kp.inputs[0])
    seca = nt.nodes.new("ShaderNodeAttribute")
    seca.attribute_name = "seca"
    tot = nt.nodes.new("ShaderNodeMath")
    tot.operation = "MAXIMUM"
    nt.links.new(kp.outputs[0], tot.inputs[0])
    nt.links.new(seca.outputs["Fac"], tot.inputs[1])
    mx = nt.nodes.new("ShaderNodeMix")
    mx.data_type = "RGBA"
    nt.links.new(tot.outputs[0], mx.inputs["Factor"])
    nt.links.new(rampa.outputs["Color"], mx.inputs["A"])
    mx.inputs["B"].default_value = (*seco, 1)
    nt.links.new(mx.outputs["Result"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.5
    tr = nt.nodes.new("ShaderNodeBsdfTranslucent")
    nt.links.new(mx.outputs["Result"], tr.inputs["Color"])
    sh = nt.nodes.new("ShaderNodeMixShader")
    sh.inputs["Fac"].default_value = translucido
    nt.links.new(b.outputs["BSDF"], sh.inputs[1])
    nt.links.new(tr.outputs["BSDF"], sh.inputs[2])
    nt.links.new(sh.outputs["Shader"], out.inputs["Surface"])
    m.use_backface_culling = False
    return m


def mat_tronco_palma():
    m = bpy.data.materials.get("Tronco_palma_real")
    if m:
        return m
    m = bpy.data.materials.new("Tronco_palma_real")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    ola = nt.nodes.new("ShaderNodeTexWave")                 # anillos de las hojas caídas
    ola.wave_type = "BANDS"
    ola.bands_direction = "Z"
    ola.inputs["Scale"].default_value = 0.9
    ola.inputs["Distortion"].default_value = 1.5
    ola.inputs["Detail"].default_value = 3
    nt.links.new(coord.outputs["Object"], ola.inputs["Vector"])
    ru = nt.nodes.new("ShaderNodeTexNoise")
    ru.inputs["Scale"].default_value = 3.0
    ru.inputs["Detail"].default_value = 10
    nt.links.new(coord.outputs["Object"], ru.inputs["Vector"])
    rampa = nt.nodes.new("ShaderNodeValToRGB")
    rampa.color_ramp.elements[0].color = (0.22, 0.21, 0.19, 1)
    rampa.color_ramp.elements[1].color = (0.58, 0.56, 0.52, 1)
    nt.links.new(ru.outputs["Fac"], rampa.inputs["Fac"])
    anillo = nt.nodes.new("ShaderNodeMix")
    anillo.data_type = "RGBA"
    anillo.blend_type = "MULTIPLY"
    anillo.inputs["Factor"].default_value = 0.35
    nt.links.new(rampa.outputs["Color"], anillo.inputs["A"])
    nt.links.new(ola.outputs["Color"], anillo.inputs["B"])
    nt.links.new(anillo.outputs["Result"], b.inputs["Base Color"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.5
    suma = nt.nodes.new("ShaderNodeMath")
    suma.operation = "ADD"
    nt.links.new(ola.outputs["Fac"], suma.inputs[0])
    nt.links.new(ru.outputs["Fac"], suma.inputs[1])
    nt.links.new(suma.outputs[0], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = 0.85
    return m


# ----------------------------------------------------------------------------------- geometría
class Malla:
    """Acumula vértices, caras y atributos por vértice (t, var, seca) para armar la malla de una vez."""

    def __init__(self):
        self.v, self.f, self.mi = [], [], []
        self.attr = {"t": [], "var": [], "seca": []}

    def vert(self, p, t=0.0, var=0.0, seca=0.0):
        self.v.append(tuple(p))
        self.attr["t"].append(t)
        self.attr["var"].append(var)
        self.attr["seca"].append(seca)
        return len(self.v) - 1

    def cara(self, idx, mi):
        self.f.append(tuple(idx))
        self.mi.append(mi)

    def crear(self, nombre, materiales):
        me = bpy.data.meshes.new(nombre)
        me.from_pydata(self.v, [], self.f)
        me.polygons.foreach_set("material_index", self.mi)
        for k, vals in self.attr.items():
            a = me.attributes.new(k, "FLOAT", "POINT")
            a.data.foreach_set("value", vals)
        for m in materiales:
            me.materials.append(m)
        me.update()
        try:
            me.shade_smooth()
        except AttributeError:
            pass
        return me


def tubo(M, perfil, seg, mi):
    """Tronco: perfil = [(z, radio)]; leve curvatura y sección poco circular para que no parezca un cilindro."""
    anillos = []
    for z, r in perfil:
        fila = []
        for k in range(seg):
            a = 2 * math.pi * k / seg
            rr = r * (1 + 0.03 * math.sin(3 * a + z))
            fila.append(M.vert((rr * math.cos(a) + 0.012 * z * z / 10, rr * math.sin(a), z), z))
        anillos.append(fila)
    for a, b in zip(anillos, anillos[1:]):
        for k in range(seg):
            M.cara((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]), mi)


def hojuela(M, base, eje, lado, largo, ancho, caida, var, seca, mi):
    """Hojuela con nervio central levantado (sección en V) y curva hacia abajo, de 4 tramos."""
    filas = []
    n = 4
    arriba = eje.cross(lado).normalized()
    for k in range(n + 1):
        s = k / n
        p = base + eje * (largo * s) - Vector((0, 0, caida * s * s))
        w = ancho * math.sin(math.pi * min(0.15 + s, 1.0)) * (1 - 0.85 * s)
        fila = (M.vert(p + lado * w, s, var, seca), M.vert(p + arriba * w * 0.35, s, var, seca),
                M.vert(p - lado * w, s, var, seca))
        filas.append(fila)
    for a, b in zip(filas, filas[1:]):
        M.cara((a[0], a[1], b[1], b[0]), mi)
        M.cara((a[1], a[2], b[2], b[1]), mi)


def palma_real():
    M = Malla()
    alto = 12.0
    perfil = [(z, 0.30 + 0.09 * math.exp(-((z - 2.2) / 2.4) ** 2) - 0.05 * z / alto + (0.12 if z < 0.4 else 0))
              for z in np.linspace(0, alto, 26)]
    tubo(M, perfil, 16, 0)
    capitel = [(alto + z, 0.27 - 0.03 * z) for z in np.linspace(0, 2.4, 8)]
    tubo(M, capitel, 16, 1)
    tope = Vector((0.012 * alto * alto / 10, 0, alto + 2.3))
    hojas = 22                                         # copa llena (antes 16 y se veía rala)
    for i in range(hojas + 2):
        vieja = i >= hojas
        yaw = 2 * math.pi * ((i * 0.381966) % 1.0) + rnd.uniform(-0.15, 0.15)
        if vieja:
            elev0 = math.radians(-55 + rnd.uniform(-10, 10))
            largo = 3.6
        else:
            elev0 = math.radians(70 - 95 * (i / hojas) + rnd.uniform(-8, 8))
            largo = 4.2 + rnd.uniform(-0.4, 0.4)
        dirh = Vector((math.cos(yaw), math.sin(yaw), 0))
        lado_h = Vector((-math.sin(yaw), math.cos(yaw), 0))
        # raquis: arco que sube y se dobla por el peso
        pasos = 34
        pts = [tope.copy()]
        p = tope.copy()
        for k in range(pasos):
            s = k / pasos
            ang = elev0 - (1.5 if not vieja else 0.5) * s * s - 0.35 * s
            d = dirh * math.cos(ang) + Vector((0, 0, math.sin(ang)))
            p = p + d * (largo / pasos)
            pts.append(p.copy())
        for a, b in zip(pts, pts[1:]):                      # raquis fino
            w = 0.025
            i0, i1 = M.vert(a - lado_h * w, 0, 0.3), M.vert(a + lado_h * w, 0, 0.3)
            i2, i3 = M.vert(b + lado_h * w, 0, 0.3), M.vert(b - lado_h * w, 0, 0.3)
            M.cara((i0, i1, i2, i3), 2)
        seca = 1.0 if vieja else 0.0
        for k in range(5, pasos, 1):
            s = k / pasos
            a, b = pts[k], pts[k + 1]
            eje_r = (b - a).normalized()
            lado = eje_r.cross(Vector((0, 0, 1))).normalized()
            for sg in (-1, 1):
                for capa, (incl, rot) in enumerate(((0.45, 0.0), (-0.35, 0.5))):
                    if rnd.random() < 0.06:                 # hojuelas rotas o faltantes
                        continue
                    L = 0.95 * math.sin(math.pi * (0.08 + 0.85 * s)) ** 0.6 * rnd.uniform(0.85, 1.1)
                    abre = (lado * sg * (1.0 - 0.15 * capa) + eje_r * (0.35 + 0.25 * s)
                            + Vector((0, 0, incl + (0.15 if vieja else 0)))).normalized()
                    base = a.lerp(b, rot) + lado * sg * 0.02
                    hojuela(M, base, abre, abre.cross(Vector((0, 0, 1))).normalized() if abs(abre.z) < 0.95
                            else lado, L, 0.04 * rnd.uniform(0.85, 1.15), L * (0.25 + 0.3 * s),
                            rnd.random(), seca, 2)
    # verde normal, poca luz a través (antes las hojuelas eran hilos y salían azuladas y transparentes)
    hoja = mat_hoja("Hoja_palma_real", (0.03, 0.08, 0.015), (0.10, 0.20, 0.035), (0.42, 0.33, 0.17), 0.12)
    capitel_m = E.material("Capitel_palma_real", (0.16, 0.26, 0.06), 0.3)
    return M.crear("Palma_real_v2", [mat_tronco_palma(), capitel_m, hoja])


def palma_bismarck():
    M = Malla()
    alto = 6.6
    perfil = [(z, 0.48 - 0.08 * z / alto + (0.1 if z < 0.4 else 0)) for z in np.linspace(0, alto, 16)]
    tubo(M, perfil, 16, 0)
    tope = Vector((0.012 * alto * alto / 10, 0, alto))
    arriba = Vector((0, 0, 1))
    for i in range(22):
        yaw = 2 * math.pi * ((i * 0.381966) % 1.0)
        elev = math.radians(75 - 85 * (i / 21) + rnd.uniform(-6, 6))
        d = Vector((math.cos(yaw) * math.cos(elev), math.sin(yaw) * math.cos(elev), math.sin(elev)))
        lat = d.cross(arriba).normalized() if abs(d.z) < 0.99 else Vector((1, 0, 0))
        c = tope + d * (2.0 + rnd.random() * 0.6)
        i0, i1 = M.vert(tope + lat * 0.05, 0, 0.5), M.vert(tope - lat * 0.05, 0, 0.5)
        i2, i3 = M.vert(c - lat * 0.03, 0, 0.5), M.vert(c + lat * 0.03, 0, 0.5)
        M.cara((i0, i1, i2, i3), 1)
        v = (d + arriba * 0.3).normalized()
        u = lat
        n = u.cross(v).normalized()
        R = 2.0 + rnd.random() * 0.4
        cols, filas = 72, 8
        var = rnd.random()
        seca = 1.0 if i > 19 else 0.0
        grilla = []
        for j in range(cols + 1):
            a = math.radians(-140 + 280 * j / cols)
            col = []
            for k in range(filas + 1):
                r = R * k / filas
                pliegue = (0.06 if j % 2 else -0.06) * (r / R)
                # abanico en cuenco: la costilla central hace que las dos mitades se levanten un poco
                p = c + (u * math.sin(a) + v * math.cos(a)) * r + n * (pliegue + 0.35 * abs(math.sin(a)) * r / R)
                p -= Vector((0, 0, 0.2 * (1 - math.cos(a)) * r / R))
                if r > 0.75 * R:                            # puntas partidas que cuelgan
                    p -= Vector((0, 0, 1.2 * (r - 0.75 * R) ** 2))
                col.append(M.vert(p, r / R, var + 0.02 * j / cols, seca))
            grilla.append(col)
        for j in range(cols):
            for k in range(filas):
                if k / filas >= 0.75 and j % 2 == 1:        # separa los segmentos en la parte exterior
                    continue
                M.cara((grilla[j][k], grilla[j + 1][k], grilla[j + 1][k + 1], grilla[j][k + 1]), 1)
    hoja = mat_hoja("Hoja_bismarck_real", (0.08, 0.13, 0.11), (0.17, 0.24, 0.20), (0.40, 0.34, 0.22), 0.2)
    return M.crear("Palma_bismarck_v2", [mat_tronco_palma(), hoja])


def cambiar_malla(vieja, nueva):
    n = 0
    for ob in bpy.data.objects:
        if ob.type == "MESH" and ob.data.name == vieja:
            ob.data = nueva
            ob.modifiers.clear()
            n += 1
    return n


# ----------------------------------------------------------------------------------- pasto
def mata_pasto():
    """Mata de 14 hojas arqueadas (grama tropical algo descuidada, como en las fotos)."""
    nombre = "Mata_pasto"
    if nombre in bpy.data.objects:
        return bpy.data.objects[nombre]
    M = Malla()
    for _ in range(14):
        yaw = rnd.uniform(0, 2 * math.pi)
        incl = rnd.uniform(0.2, 0.75)
        alto = rnd.uniform(0.08, 0.24)
        base = Vector((rnd.uniform(-0.09, 0.09), rnd.uniform(-0.09, 0.09), 0))
        d = Vector((math.cos(yaw), math.sin(yaw), 0))
        lado = Vector((-d.y, d.x, 0))
        filas = []
        for k in range(4):
            s = k / 3
            p = base + d * (math.sin(incl) * alto * s + 0.06 * s * s) + Vector((0, 0, alto * s - 0.04 * s * s))
            w = 0.006 * (1 - s) + 0.0008
            filas.append((M.vert(p - lado * w, s, rnd.random()), M.vert(p + lado * w, s, rnd.random())))
        for a, b in zip(filas, filas[1:]):
            M.cara((a[0], a[1], b[1], b[0]), 0)
    mat = mat_hoja("Pasto_3d", (0.05, 0.10, 0.02), (0.20, 0.26, 0.06), (0.45, 0.40, 0.22), 0.35)
    me = M.crear(nombre, [mat])
    ob = bpy.data.objects.new(nombre, me)
    col = bpy.data.collections.get("Biblioteca_vegetacion")
    col.objects.link(ob)
    return ob


def grupo_instancias(mata):
    ng = bpy.data.node_groups.get("Sembrar_pasto")
    if ng:
        return ng
    ng = bpy.data.node_groups.new("Sembrar_pasto", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    nodos = ng.nodes
    ent = nodos.new("NodeGroupInput")
    sal = nodos.new("NodeGroupOutput")
    info = nodos.new("GeometryNodeObjectInfo")
    info.inputs["Object"].default_value = mata
    info.inputs["As Instance"].default_value = True
    inst = nodos.new("GeometryNodeInstanceOnPoints")
    rot = nodos.new("GeometryNodeInputNamedAttribute")
    rot.data_type = "FLOAT"
    rot.inputs["Name"].default_value = "giro"
    esc = nodos.new("GeometryNodeInputNamedAttribute")
    esc.data_type = "FLOAT"
    esc.inputs["Name"].default_value = "escala"
    comb = nodos.new("ShaderNodeCombineXYZ")
    ng.links.new(rot.outputs["Attribute"], comb.inputs["Z"])
    ng.links.new(ent.outputs[0], inst.inputs["Points"])
    ng.links.new(info.outputs["Geometry"], inst.inputs["Instance"])
    ng.links.new(comb.outputs["Vector"], inst.inputs["Rotation"])
    ng.links.new(esc.outputs["Attribute"], inst.inputs["Scale"])
    ng.links.new(inst.outputs["Instances"], sal.inputs[0])
    return ng


def sembrar():
    col = bpy.data.collections.get("Pasto_3d")
    if col:
        for ob in list(col.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
    else:
        col = bpy.data.collections.new("Pasto_3d")
        bpy.context.scene.collection.children.link(col)
    mata = mata_pasto()
    ng = grupo_instancias(mata)
    deps = bpy.context.evaluated_depsgraph_get()
    sc = bpy.context.scene
    total = 0
    for ob in list(bpy.data.objects):
        if ob.type != "MESH" or not ob.material_slots or not ob.material_slots[0].material \
                or not ob.material_slots[0].material.name.startswith("Pasto") or ob.name.startswith("Mata_pasto"):
            continue
        mw = ob.matrix_world
        centro = mw.translation
        R = max(ob.dimensions.x, ob.dimensions.y) / 2
        r_lleno, r_fin = 0.55 * R, 0.85 * R
        area = math.pi * r_fin * r_fin
        n = int(area * DENSIDAD)
        rs = np.sqrt(np.random.default_rng(len(ob.name)).random(n)) * r_fin
        aa = np.random.default_rng(len(ob.name) + 1).random(n) * 2 * math.pi
        acepta = np.random.default_rng(len(ob.name) + 2).random(n)
        pts, giros, escalas = [], [], []
        z0 = centro.z + 0.5
        for r, a, u in zip(rs, aa, acepta):
            if r > r_lleno and u > (r_fin - r) / (r_fin - r_lleno):
                continue
            x, y = centro.x + r * math.cos(a), centro.y + r * math.sin(a)
            ok, loc, _n, _i, hit, _m = sc.ray_cast(deps, Vector((x, y, z0 + 30.0)), Vector((0, 0, -1)), distance=40.0)
            if not ok or hit.name != ob.name:
                continue
            pts.append((x, y, loc.z))
            giros.append(rnd.uniform(0, 2 * math.pi))
            escalas.append(rnd.uniform(0.7, 1.4))
        if not pts:
            continue
        me = bpy.data.meshes.new("Puntos_pasto_" + ob.name)
        me.from_pydata(pts, [], [])
        for k, vals in (("giro", giros), ("escala", escalas)):
            at = me.attributes.new(k, "FLOAT", "POINT")
            at.data.foreach_set("value", vals)
        sem = bpy.data.objects.new("Pasto3d_" + ob.name, me)
        col.objects.link(sem)
        mod = sem.modifiers.new("Sembrar", "NODES")
        mod.node_group = ng
        total += len(pts)
        print(f"  {ob.name}: {len(pts)} matas")
    print("matas de pasto:", total)


def oscurecer_cesped():
    """Con el cielo fotográfico el césped de textura salía pálido: un verde más profundo y algo seco."""
    for m in bpy.data.materials:
        if m.name.startswith("Pasto") and m.name != "Pasto_3d" and m.use_nodes:
            for n in m.node_tree.nodes:
                if n.bl_idname == "ShaderNodeMix" and n.blend_type == "MULTIPLY" and n.inputs["Factor"].default_value == 1.0:
                    n.inputs["B"].default_value = (0.26, 0.50, 0.14, 1)
                    break


def main():
    oscurecer_cesped()
    n1 = cambiar_malla("Palma_real", palma_real())
    n2 = cambiar_malla("Palma_bismarck", palma_bismarck())
    print("palmas reales cambiadas:", n1, "| bismarck:", n2)
    sembrar()
    bpy.ops.wm.save_mainfile()
    print("palmas y pasto listos")


if __name__ == "__main__":
    main()
