"""Academia Técnica Militar de la Aviación, detrás del comedor y lejos (foto ACADEMIA TECNICA).
Se corre después de comedor.py y antes de vias.py:

    blender --background BaseSucre.blend --python academia.py

El conjunto sale de la huella real de OpenStreetMap (alas en cruz de un piso con techo de teja roja a cuatro
aguas). La fachada principal (cara norte del ala noreste, ver datos/ubicaciones.json) lleva lo de la foto: pretil
alto con el revestimiento de piedras poligonales gris oscuro y gris claro, las letras doradas «ACADEMIA TÉCNICA
MILITAR DE LA AVIACIÓN» con un escudo en cada punta, el cuerpo central más alto color crema con su techo de teja, la
marquesina plana blanca sobre columnas redondas, el pasillo con columnas azules, muros gris azulado con franjas
claras, y la explanada de concreto agrietado con las rayas amarillas.
"""
import json
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import entrada as E  # noqa: E402
import hangares as Hg  # noqa: E402

RAIZ = os.path.dirname(E.TEXTURAS)
UB = Hg.UBS["Academia Técnica"]
rnd = E.random.Random(31)
H = 4.0                                  # altura de los muros de las alas


def limpiar():
    col = bpy.data.collections.get("Academia")
    if col:
        for ob in list(col.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.collections.remove(col)
    col = bpy.data.collections.new("Academia")
    bpy.context.scene.collection.children.link(col)
    return col


def mat_piedras():
    """Revestimiento de piedras poligonales grandes: celdas de Voronoi en dos grises con juntas claras."""
    m = bpy.data.materials.get("Piedras_poligonales")
    if m:
        return m
    m = bpy.data.materials.new("Piedras_poligonales")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapa = nt.nodes.new("ShaderNodeMapping")
    mapa.inputs["Rotation"].default_value = (math.pi / 2, 0, 0)       # sobre el plano de la fachada
    nt.links.new(coord.outputs["Object"], mapa.inputs["Vector"])
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.voronoi_dimensions = "2D"
    vor.inputs["Scale"].default_value = 0.55
    vor.inputs["Randomness"].default_value = 1.0
    nt.links.new(mapa.outputs["Vector"], vor.inputs["Vector"])
    borde = nt.nodes.new("ShaderNodeTexVoronoi")
    borde.voronoi_dimensions = "2D"
    borde.feature = "DISTANCE_TO_EDGE"
    borde.inputs["Scale"].default_value = 0.55
    borde.inputs["Randomness"].default_value = 1.0
    nt.links.new(mapa.outputs["Vector"], borde.inputs["Vector"])
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(vor.outputs["Color"], sep.inputs["Color"])
    ra = nt.nodes.new("ShaderNodeValToRGB")
    ra.color_ramp.interpolation = "CONSTANT"
    ra.color_ramp.elements[0].color = (0.11, 0.12, 0.14, 1)
    e = ra.color_ramp.elements.new(0.55)
    e.color = (0.24, 0.25, 0.28, 1)
    ra.color_ramp.elements[-1].position = 0.82
    ra.color_ramp.elements[-1].color = (0.40, 0.42, 0.45, 1)
    nt.links.new(sep.outputs["Red"], ra.inputs["Fac"])
    junta = nt.nodes.new("ShaderNodeMath")
    junta.operation = "LESS_THAN"
    junta.inputs[1].default_value = 0.03
    nt.links.new(borde.outputs["Distance"], junta.inputs[0])
    mx = nt.nodes.new("ShaderNodeMix")
    mx.data_type = "RGBA"
    mx.inputs["B"].default_value = (0.62, 0.63, 0.65, 1)
    nt.links.new(junta.outputs["Value"], mx.inputs["Factor"])
    nt.links.new(ra.outputs["Color"], mx.inputs["A"])
    nt.links.new(mx.outputs["Result"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.55
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.3
    nt.links.new(junta.outputs["Value"], bp.inputs["Height"])
    bp.invert = True
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def mat_teja():
    m = bpy.data.materials.get("Teja_roja")
    if m:
        return m
    m = bpy.data.materials.new("Teja_roja")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    lad = nt.nodes.new("ShaderNodeTexBrick")
    lad.inputs["Color1"].default_value = (0.50, 0.15, 0.07, 1)
    lad.inputs["Color2"].default_value = (0.62, 0.22, 0.10, 1)
    lad.inputs["Mortar"].default_value = (0.25, 0.08, 0.04, 1)
    lad.inputs["Scale"].default_value = 1.0
    lad.inputs["Mortar Size"].default_value = 0.02
    lad.inputs["Brick Width"].default_value = 0.3
    lad.inputs["Row Height"].default_value = 0.4
    nt.links.new(coord.outputs["Object"], lad.inputs["Vector"])
    nt.links.new(lad.outputs["Color"], b.inputs["Base Color"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.5
    nt.links.new(lad.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = 0.7
    return m


def huella():
    D = json.load(open(os.path.join(RAIZ, "datos", "svbs.json")))
    mejor = None
    for b in D["buildings"]:
        p = b["p"]
        n = sum(q[0] for q in p) / len(p)
        e = sum(q[1] for q in p) / len(p)
        if math.hypot(e - UB["este"], n - UB["norte"]) < 3:
            mejor = [Vector((q[1], q[0])) for q in p]
    if mejor and mejor[0] == mejor[-1]:
        mejor = mejor[:-1]
    return mejor


def techo_a_cuatro_aguas(bm, cara, alero, alto, inset):
    """Techo sobre una cara horizontal de cualquier forma: alero hacia afuera y caídas hasta una cumbrera interior
    (inset de la cara), como un techo de teja a cuatro aguas."""
    z0 = cara.verts[0].co.z
    # (inset_individual sí funciona con la huella cóncava en cruz; inset_region no hacía nada)
    antes = set(bm.verts)
    bmesh.ops.inset_individual(bm, faces=[cara], thickness=-alero, use_even_offset=True)
    # el anillo exterior es el original corrido hacia afuera: se baja un poco para el alero
    for v in antes:
        v.co.z = z0 - 0.15
    # sobre la huella en cruz, un segundo inset grande se cruza consigo mismo en los brazos angostos y arruga el
    # techo: se deja un techo de pendiente baja (alero abajo, centro 0,6 m arriba), sin cumbrera marcada
    for v in cara.verts:
        v.co.z = z0 + 0.6


def conjunto(col, z):
    pts = huella()
    if pts is None:
        print("no está la huella de la Academia")
        return None
    paredes = E.pbr("Pared_gris_azulado", "friso", 3.0, pintura=(0.24, 0.27, 0.33))
    # alas: muros y techo de teja
    bm = bmesh.new()
    base = bm.faces.new([bm.verts.new((p.x, p.y, z)) for p in pts])
    base.normal_update()
    if base.normal.z < 0:
        base.normal_flip()
    r = bmesh.ops.extrude_face_region(bm, geom=[base])
    bmesh.ops.translate(bm, vec=Vector((0, 0, H)), verts=[g for g in r["geom"] if isinstance(g, bmesh.types.BMVert)])
    E.objeto("Academia_muros", bm, [paredes], None, col)
    bm = bmesh.new()
    cara = bm.faces.new([bm.verts.new((p.x, p.y, z + H)) for p in pts])
    cara.normal_update()
    if cara.normal.z < 0:
        cara.normal_flip()
    techo_a_cuatro_aguas(bm, cara, 0.8, 2.2, 5.5)
    zs = sorted(v.co.z for v in bm.verts)
    print("techo de las alas: z", round(zs[0] - z, 2), "→", round(zs[-1] - z, 2), "| caras", len(bm.faces))
    E.objeto("Academia_techo", bm, [mat_teja()], None, col)
    # franjas claras horizontales en los muros (como en la foto), con un leve sobre-espesor
    bm = bmesh.new()
    for zz in (1.1, 2.0):
        f = bm.faces.new([bm.verts.new((p.x, p.y, z + zz)) for p in pts])
        r = bmesh.ops.extrude_face_region(bm, geom=[f])
        bmesh.ops.translate(bm, vec=Vector((0, 0, 0.08)),
                            verts=[g for g in r["geom"] if isinstance(g, bmesh.types.BMVert)])
    bmesh.ops.scale(bm, vec=(1.0, 1.0, 1.0), verts=bm.verts[:])
    E.objeto("Academia_franjas", bm, [E.material("Gris_claro_franja", (0.55, 0.58, 0.62), 0.6)], None, col)
    return pts


def fachada(col, z):
    a, b = (Vector(p) for p in UB["fachada"])
    c = (a + b) / 2
    eje = (b - a).normalized()
    normal = Vector((eje.y, -eje.x))
    if normal.dot(c - Vector((UB["este"], UB["norte"]))) < 0:
        normal = -normal
    p = bpy.data.objects.new("Academia_origen", None)
    p.empty_display_type = "ARROWS"
    p.location = (c.x, c.y, z)
    # marco local: -Y = afuera (normal), X a lo largo de la fachada
    p.rotation_euler = (0, 0, math.atan2(-normal.x, normal.y) + math.pi)
    col.objects.link(p)
    W = (b - a).length
    M = Hg.materiales(E.mats())
    piedra = mat_piedras()
    # pretil alto de piedras poligonales a todo lo ancho
    bm = bmesh.new()
    E.caja(bm, (0, 0.6, H - 0.2), (W + 0.2, 1.3, 2.4), 0)
    E.objeto("Academia_pretil", bm, [piedra], p, col)
    bm = bmesh.new()
    E.caja(bm, (0, 0.6, H + 2.2), (W + 0.4, 1.4, 0.12), 0)
    E.objeto("Academia_pretil_remate", bm, [M["concreto_patio"]], p, col)
    # cuerpo central más alto, crema, con techo de teja
    bm = bmesh.new()
    E.caja(bm, (0, 6.5, H), (17.0, 10.0, 3.9), 0)
    E.objeto("Academia_cuerpo_central", bm, [E.pbr("Friso_crema", "friso", 3.0, pintura=(0.86, 0.80, 0.58))], p, col)
    # techo a cuatro aguas explícito: alero de 0,9 m y cumbrera a lo largo, 1,7 m más arriba
    bm = bmesh.new()
    ze, zc = H + 3.75, H + 5.45
    a = [bm.verts.new(v) for v in ((-9.4, 0.6, ze), (9.4, 0.6, ze), (9.4, 12.4, ze), (-9.4, 12.4, ze))]
    c = [bm.verts.new(v) for v in ((-3.5, 6.5, zc), (3.5, 6.5, zc))]
    bm.faces.new((a[0], a[1], c[1], c[0]))
    bm.faces.new((a[2], a[3], c[0], c[1]))
    bm.faces.new((a[1], a[2], c[1]))
    bm.faces.new((a[3], a[0], c[0]))
    bm.faces.new((a[3], a[2], a[1], a[0]))
    E.objeto("Academia_techo_central", bm, [mat_teja()], p, col)
    # letras doradas y escudos sobre el pretil
    oro = E.material("Dorado_academia", (0.90, 0.68, 0.18), 0.3, 0.8)
    t = E.texto("ACADEMIA TÉCNICA MILITAR DE LA AVIACIÓN", 0.62, oro, p, col, (0, -0.1, H + 1.05),
                (math.pi / 2, 0, 0), extr=0.06)
    t.data.space_character = 1.05
    bm = bmesh.new()
    for x in (-10.4, 10.4):
        E.cilindro(bm, (x, -0.08, H + 1.05), 0.36, 0.36, 0.05, 0, 28, (math.pi / 2, 0, 0))
        E.cilindro(bm, (x, -0.12, H + 1.05), 0.27, 0.27, 0.03, 1, 28, (math.pi / 2, 0, 0))
    E.objeto("Academia_escudos", bm, [oro, M["azul_emblema"]], p, col)
    # marquesina plana sobre columnas redondas, con un remate más alto en el centro
    xm0, xm1, ym = -12.0, 12.0, -7.0
    bm = bmesh.new()
    E.caja(bm, (0.5 * (xm0 + xm1), ym / 2, 3.2), (xm1 - xm0, -ym, 0.38), 0)
    E.caja(bm, (0, ym / 2, 3.58), (4.0, -ym, 0.25), 0)
    for x in (-11.0, -5.0, -1.2, 1.2, 5.0, 11.0):
        E.cilindro(bm, (x, ym + 0.6, 0), 0.22, 0.22, 3.2, 0, 16)
    E.objeto("Academia_marquesina", bm, [M["blanco"]], p, col)
    # bajo la marquesina: muro blanco con tres cuadros, pasillo de columnas azules hacia la derecha y bancos
    bm = bmesh.new()
    E.caja(bm, (-4.0, -0.05, 0), (12.0, 0.1, 3.1), 0)
    E.objeto("Academia_vestibulo", bm, [M["blanco"]], p, col)
    bm = bmesh.new()
    for k, x in enumerate((-6.5, -4.5, -2.5)):
        E.caja(bm, (x, -0.13, 1.4), (1.5, 0.04, 1.0), k % 2)
    E.objeto("Academia_cuadros", bm, [E.material("Cuadro_azul", (0.15, 0.35, 0.60), 0.4),
                                      E.material("Cuadro_celeste", (0.50, 0.70, 0.85), 0.4)], p, col)
    bm = bmesh.new()
    for k in range(9):
        E.caja(bm, (2.0 + k * 1.1, -0.6 - k * 0.15, 0), (0.25, 0.25, 3.1), 0)
    E.objeto("Academia_columnas_azules", bm, [E.material("Azul_columnas", (0.05, 0.30, 0.62), 0.45)], p, col)
    bm = bmesh.new()
    for x in (-9.5, -8.0):
        E.caja(bm, (x, -1.2, 0.45), (1.2, 0.5, 0.06), 0)
        E.caja(bm, (x, -1.0, 0.45), (1.2, 0.06, 0.5), 0)
    E.objeto("Academia_bancos", bm, [E.material("Verde_banco", (0.05, 0.28, 0.16), 0.5)], p, col)
    # piso del pórtico y explanada de concreto agrietado con rayas amarillas
    bm = bmesh.new()
    E.caja(bm, (0, ym / 2, 0), (xm1 - xm0 + 2, -ym + 1, 0.15), 0)
    E.objeto("Academia_piso_portico", bm, [M["acera"]], p, col)
    bm = bmesh.new()
    E.caja(bm, (0, ym - 14.0, 0), (W + 16.0, 28.0, 0.1), 0)
    E.objeto("Academia_explanada", bm, [bpy.data.materials.get("Concreto_gastado") or M["concreto_patio"]], p, col)
    bm = bmesh.new()
    for x in (-8.0, 0.0, 8.0):
        E.caja(bm, (x, ym - 2.5, 0.1), (0.15, 5.0, 0.01), 0)
        E.caja(bm, (x, ym - 1.2, 0.1), (3.4, 0.15, 0.01), 0)
    E.caja(bm, (14.0, ym - 1.5, 0.1), (0.15, 3.5, 0.01), 0, (0, 0, 0.5))
    E.objeto("Academia_rayas", bm, [M["amarillo"]], p, col)
    E.camara("Cam_Academia", p, col, (0.0, -38.0, 1.7), (0.0, 0.0, 3.6), 22)


def main():
    col = limpiar()
    z = E.aplanar(UB["este"], UB["norte"], "cota_academia", 80.0, 120.0)
    conjunto(col, z)
    fachada(col, z)
    pasto = E.pbr("Pasto_academia", "pasto", 2.5, (0.45, 0.95, 0.30), fade=(80.0, 115.0),
                  variacion=(0.05, (0.85, 0.75, 0.45)))
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, radius=115.0, segments=96)
    ob = E.objeto("Pasto_academia", bm, [pasto], None, col)
    ob.location = (UB["este"], UB["norte"], z + 0.01)
    bpy.ops.wm.save_mainfile()
    print("Academia lista")


if __name__ == "__main__":
    main()
