"""Dormitorios de ladrillo frente al CEA y el Grupo 7 (GRUEVI 7). Se corre después de g14_hangar3.py:

    blender --background BaseSucre.blend --python dorm_g7.py

Dormitorios: las dos huellas en H de OpenStreetMap (datos/svbs.json); cada H son dos barras de tres pisos con
pasillos volados hacia el patio angosto y la escalera de acero en el medio (fotos DORMITORIOS FRENTE DEL CEA 1-3,
DORMITORIOS FRENTE DEL CEA LLEGANDO A GRUPO 7). Marco de cada H: origen en la esquina exterior sureste de la primera
barra, X atraviesa las barras y Y corre a lo largo de ellas hacia el noroeste.

Grupo 7: GRUPO 7 FRENTE, GRUPO 7 OTRA VISTA FRENTE, ESQUINA IZQUIERDA/DERECHA, AL LADO DE GRUPO 7. Mismo marco que
la DIDA (el frente mira hacia -Y).
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
rnd = E.random.Random(7)
PISO, PISOS = 3.1, 3


def limpiar():
    col = bpy.data.collections.get("Dormitorios_G7")
    if col:
        for ob in list(col.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.collections.remove(col)
    col = bpy.data.collections.new("Dormitorios_G7")
    bpy.context.scene.collection.children.link(col)
    return col


def mat_ladrillo():
    """Ladrillo rojo con junta clara, en las caras verticales del marco del objeto."""
    m = bpy.data.materials.get("Ladrillo_rojo")
    if m:
        return m
    m = bpy.data.materials.new("Ladrillo_rojo")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(coord.outputs["Object"], sep.inputs["Vector"])
    suma = nt.nodes.new("ShaderNodeMath")
    suma.operation = "ADD"
    nt.links.new(sep.outputs["X"], suma.inputs[0])
    nt.links.new(sep.outputs["Y"], suma.inputs[1])
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(suma.outputs["Value"], comb.inputs["X"])
    nt.links.new(sep.outputs["Z"], comb.inputs["Y"])
    lad = nt.nodes.new("ShaderNodeTexBrick")
    lad.inputs["Color1"].default_value = (0.40, 0.15, 0.08, 1)
    lad.inputs["Color2"].default_value = (0.55, 0.24, 0.13, 1)
    lad.inputs["Mortar"].default_value = (0.50, 0.44, 0.38, 1)
    lad.inputs["Scale"].default_value = 1.0
    lad.inputs["Mortar Size"].default_value = 0.012
    lad.inputs["Brick Width"].default_value = 0.30
    lad.inputs["Row Height"].default_value = 0.10
    nt.links.new(comb.outputs["Vector"], lad.inputs["Vector"])
    nt.links.new(lad.outputs["Color"], b.inputs["Base Color"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.35
    bp.invert = True
    nt.links.new(lad.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = 0.88
    return m


def mat_malla():
    m = bpy.data.materials.get("Malla_baranda")
    if m:
        return m
    m = E.material("Malla_baranda", (0.78, 0.40, 0.28), 0.6, 0.3)
    m.node_tree.nodes.get("Principled BSDF").inputs["Alpha"].default_value = 0.45
    return m


# ----------------------------------------------------------------------------------- dormitorios
def huellas_h():
    D = json.load(open(os.path.join(RAIZ, "datos", "svbs.json")))
    hs = []
    for b in D["buildings"]:
        p = b["p"]
        if len(p) != 12:
            continue
        n = sum(q[0] for q in p) / 12
        e = sum(q[1] for q in p) / 12
        if math.hypot(e + 364.3, n + 706.8) < 30:
            hs.append([Vector((q[1], q[0])) for q in p])
    return hs


def dormitorio(nombre, pts, M, col, z):
    """Un edificio en H a partir de sus 12 vértices de OpenStreetMap."""
    o = pts[11]
    Y = (pts[0] - o).normalized()                       # a lo largo de las barras, hacia el noroeste
    X = pts[5] - pts[0]
    X = (X - X.dot(Y) * Y).normalized()                 # atraviesa las barras
    if X.x * Y.y - X.y * Y.x < 0:                       # marco directo (Z hacia arriba)
        X = -X
    loc = [Vector(((q - o).dot(X), (q - o).dot(Y))) for q in pts]
    L = loc[0].y
    xa1, xb0, xb1 = loc[1].x, loc[4].x, loc[5].x
    y_esc0, y_esc1 = loc[8].y, loc[2].y
    xe0, xe1 = loc[2].x, loc[3].x

    p = bpy.data.objects.new(nombre + "_origen", None)
    p.empty_display_type = "ARROWS"
    p.location = (o.x, o.y, z)
    p.rotation_euler = (0, 0, math.atan2(X.y, X.x))
    col.objects.link(p)

    H = PISO * PISOS
    lad, acero, malla = mat_ladrillo(), M["acero_dorm"], mat_malla()
    bm = bmesh.new()
    for x0, x1 in ((0.0, xa1), (xb0, xb1)):
        E.caja(bm, (0.5 * (x0 + x1), L / 2, 0), (x1 - x0, L, H), 0)
    E.objeto(nombre + "_barras", bm, [lad], p, col)

    # estructura de acero vista: columnas en las esquinas y vigas de borde en cada piso
    bm = bmesh.new()
    for x0, x1 in ((0.0, xa1), (xb0, xb1)):
        for x in (x0, x1):
            for y in [0.0, L] + [L * k / 6 for k in range(1, 6)]:
                if 0 < y < L and x not in (xa1, xb0):
                    continue
                E.caja(bm, (x, y, 0), (0.24, 0.24, H + 0.1), 0)
        for k in range(1, PISOS + 1):
            for y in (-0.05, L + 0.05):
                E.caja(bm, (0.5 * (x0 + x1), y, k * PISO - 0.18), (x1 - x0 + 0.1, 0.12, 0.18), 0)
            for x in (x0 - 0.05, x1 + 0.05):
                E.caja(bm, (x, L / 2, k * PISO - 0.18), (0.12, L + 0.1, 0.18), 0)
    E.objeto(nombre + "_estructura", bm, [acero], p, col)

    # pasillos volados hacia el patio, con baranda de malla, y puertas de las habitaciones
    bm, bb, bp = bmesh.new(), bmesh.new(), bmesh.new()
    for xcara, s in ((xa1, 1), (xb0, -1)):
        for k in range(1, PISOS):
            zz = k * PISO
            E.caja(bm, (xcara + s * 0.7, L / 2, zz - 0.15), (1.4, L, 0.15), 0)
            for yy in [L * j / 6 for j in range(7)]:
                E.caja(bm, (xcara + s * 1.35, yy, zz - 0.3), (0.06, 0.06, 0.3), 0)
            E.caja(bm, (xcara + s * 1.38, L / 2, zz + 1.0), (0.06, L, 0.06), 0)
            E.caja(bb, (xcara + s * 1.38, L / 2, zz + 0.1), (0.03, L, 0.9), 0)
        for k in range(PISOS):
            for j in range(6):
                yy = L * (j + 0.5) / 6
                if y_esc0 - 0.5 < yy < y_esc1 + 0.5:
                    continue
                E.caja(bp, (xcara + s * 0.03, yy, k * PISO + 0.02), (0.06, 0.9, 2.1), 0)
    E.objeto(nombre + "_pasillos", bm, [acero], p, col)
    E.objeto(nombre + "_barandas", bb, [malla], p, col)
    E.objeto(nombre + "_puertas", bp, [M["puerta_marron"]], p, col)

    # ventanas y aires en las caras exteriores; respiradero oscuro y una antena en los testeros
    bm = bmesh.new()
    for xcara, s in ((0.0, -1), (xb1, 1)):
        for k in range(PISOS):
            for j in range(6):
                yy = L * (j + 0.5) / 6
                zz = k * PISO + 1.0
                E.caja(bm, (xcara + s * 0.03, yy, zz - 0.06), (0.06, 1.15, 1.25), 1)
                E.caja(bm, (xcara + s * 0.06, yy, zz), (0.05, 1.0, 1.1), 0)
                if (j + k) % 3 == 0:
                    E.caja(bm, (xcara + s * 0.3, yy + 0.9, zz + 0.1), (0.5, 0.7, 0.45), 2)
    for x0, x1 in ((0.0, xa1), (xb0, xb1)):
        for y, s in ((0.0, -1), (L, 1)):
            for k in (1, 2):
                E.caja(bm, (0.5 * (x0 + x1), y + s * 0.03, k * PISO + 0.6), (0.9, 0.06, 0.9), 3)
    E.objeto(nombre + "_ventanas", bm, [M["vidrio"], M["blanco"], M["aire"], M["oscuro"]], p, col)

    # escalera de acero entre las barras: losas de descanso, tramos en zigzag y barandas
    bm, bb = bmesh.new(), bmesh.new()
    ancho_e = xe1 - xe0
    for k in range(1, PISOS + 1):
        E.caja(bm, (0.5 * (xe0 + xe1), 0.5 * (y_esc0 + y_esc1), k * PISO - 0.15),
               (ancho_e, y_esc1 - y_esc0, 0.15), 0)
    for k in range(PISOS):
        z0 = k * PISO
        for t in range(2):                                   # dos tramos por piso, ida y vuelta
            xa = xe0 + 0.35 + t * (ancho_e / 2)
            for s in range(9):
                f = (s + 0.5) / 9
                yy = (y_esc0 + 0.6 + f * (y_esc1 - y_esc0 - 1.2)) if t == 0 else (y_esc1 - 0.6 - f * (y_esc1 - y_esc0 - 1.2))
                E.caja(bm, (xa + ancho_e / 4 - 0.35, yy, z0 + (t + f) * PISO / 2 - 0.05), (ancho_e / 2 - 0.5, 0.32, 0.05), 0)
    for x in (xe0 + 0.1, xe1 - 0.1):
        for y in (y_esc0 + 0.1, y_esc1 - 0.1):
            E.caja(bm, (x, y, 0), (0.2, 0.2, H + 0.5), 0)
    for k in range(1, PISOS + 1):
        for y in (y_esc0 + 0.05, y_esc1 - 0.05):
            E.caja(bb, (0.5 * (xe0 + xe1), y, k * PISO), (ancho_e, 0.03, 1.0), 0)
    E.objeto(nombre + "_escalera", bm, [acero], p, col)
    E.objeto(nombre + "_escalera_baranda", bb, [malla], p, col)

    # techos de lámina naranja a dos aguas en cada barra y techo plano sobre la escalera
    bm = bmesh.new()
    for x0, x1 in ((0.0, xa1), (xb0, xb1)):
        xm = 0.5 * (x0 + x1)
        for s in (-1, 1):
            xe = (x0 - 0.6) if s < 0 else (x1 + 0.6)
            bm.faces.new([bm.verts.new(v) for v in ((xe, -0.5, H - 0.1), (xm, -0.5, H + 0.75),
                                                    (xm, L + 0.5, H + 0.75), (xe, L + 0.5, H - 0.1))])
    E.caja(bm, (0.5 * (xe0 + xe1), 0.5 * (y_esc0 + y_esc1), H + 0.45), (ancho_e + 0.8, y_esc1 - y_esc0 + 0.8, 0.08), 0)
    E.objeto(nombre + "_techos", bm, [M["lamina_naranja"]], p, col)
    # testeros: el triángulo de ladrillo que cierra cada extremo bajo el techo (sin él el techo parecía flotar),
    # con un remate de lámina en el borde
    bm = bmesh.new()
    for x0, x1 in ((0.0, xa1), (xb0, xb1)):
        xm = 0.5 * (x0 + x1)
        for y in (0.0, L):
            f = bm.faces.new([bm.verts.new(v) for v in ((x0, y, H), (x1, y, H), (xm, y, H + 0.72))])
            f.material_index = 0
            for s in (-1, 1):
                a = Vector((x0 if s < 0 else x1, y, H - 0.02))
                b = Vector((xm, y, H + 0.74))
                m = (a + b) / 2
                E.caja(bm, (m.x, m.y + (-0.25 if y == 0 else 0.25), m.z - 0.06), ((b - a).length + 0.3, 0.5, 0.06), 1,
                       (0, math.atan2(b.z - a.z, b.x - a.x) * -1, 0))
    E.objeto(nombre + "_testeros", bm, [lad, M["lamina_naranja"]], p, col)

    # caminerías, césped ralo y matas como en las fotos
    bm = bmesh.new()
    E.caja(bm, (0.5 * (xe0 + xe1), L / 2, 0), (ancho_e + 0.2, L + 14, 0.08), 0)
    E.objeto(nombre + "_caminerias", bm, [M["concreto_patio"]], p, col)
    bh = bmesh.new()
    for x, y in ((-3.0, 4.0), (-2.5, L - 6.0), (xb1 + 2.5, 8.0), (xb1 + 3.0, L - 3.0)):
        E.hojas(bh, Vector((x, y, 0.8)), 1.2, 380, rnd, 0, 0.13)
    E.objeto(nombre + "_matas", bh, [M["arbusto_amarillo"]], p, col)
    palma = bpy.data.meshes.get("Palma_real")
    if palma:
        for x, y in ((-4.0, L * 0.5), (xb1 + 4.5, L * 0.35)):
            E.instancia(palma, nombre + "_palma", p, col, x, y, 0.42)
    return p, (xe0, xe1, y_esc0, y_esc1, L)


# ----------------------------------------------------------------------------------- Grupo 7
def grupo7(M, col, z):
    ub = Hg.UBS["Grupo 7 (GRUEVI 7)"]
    p = Hg.origen("Grupo7_origen", ub, col, z)
    W, D = ub["ancho"], ub["fondo"]
    xs = -W / 2 + 30.0                                    # fin de la nave oscura, empieza el ala blanca
    h_nave, h_ala = 8.4, 7.6
    panel = E.pbr("Panel_gris_oscuro", "pared", 3.0, pintura=(0.13, 0.15, 0.19))
    bm = bmesh.new()
    E.caja(bm, (0.5 * (-W / 2 + xs), D / 2, 0), (xs + W / 2, D, h_nave), 0)
    E.caja(bm, (0.5 * (xs + W / 2), D / 2, 0), (W / 2 - xs, D, h_ala), 1)
    E.objeto("Grupo7_volumen", bm, [panel, M["blanco"]], p, col)

    # retícula blanca de columnas y vigas sobre la fachada oscura
    bm = bmesh.new()
    for k in range(6):
        x = -W / 2 + k * (xs + W / 2) / 5
        E.caja(bm, (x, -0.13, 0), (0.45, 0.26, h_nave), 0)
    for zz, h in ((3.9, 0.35), (h_nave - 0.5, 0.5)):
        E.caja(bm, (0.5 * (-W / 2 + xs), -0.13, zz), (xs + W / 2 + 0.45, 0.26, h), 0)
    # jardineras sobre la viga intermedia
    for x in (-15.0, -8.5, -2.0):
        E.caja(bm, (x, -0.45, 3.4), (2.4, 0.6, 0.5), 1)
    E.objeto("Grupo7_reticula", bm, [M["blanco"], M["gris_zocalo"]], p, col)
    bh = bmesh.new()
    for x in (-15.0, -8.5, -2.0):
        E.hojas(bh, Vector((x, -0.5, 4.2)), 0.7, 160, rnd, 0, 0.16)
    E.objeto("Grupo7_jardineras_matas", bh, [M["arbusto"]], p, col)

    # entrada: vano oscuro con paneles grises a los lados y el letrero GRUEVI 7
    xe = xs - 5.5
    bm = bmesh.new()
    E.caja(bm, (xe, -0.05, 0), (3.6, 0.1, 3.6), 0)
    for dx in (-2.8, 2.8):
        E.caja(bm, (xe + dx, -0.06, 0), (1.9, 0.12, 3.7), 1)
        E.caja(bm, (xe + dx, -0.14, 1.9), (1.4, 0.05, 0.6), 2)
    E.caja(bm, (xe, -0.2, 4.45), (4.4, 0.18, 1.0), 3)
    E.objeto("Grupo7_entrada", bm, [M["oscuro"], M["gris_zocalo"], M["blanco"],
                                    E.material("Letrero_azul_noche", (0.03, 0.05, 0.14), 0.4)], p, col)
    E.texto("GRUEVI", 0.6, M["blanco"], p, col, (xe - 0.5, -0.31, 4.95), (math.pi / 2, 0, 0), extr=0.02)
    E.texto("7", 0.85, E.material("Azul_GRUEVI", (0.10, 0.45, 0.85), 0.4), p, col, (xe + 1.6, -0.31, 4.95),
            (math.pi / 2, 0, 0), extr=0.03)

    # ala blanca a la derecha: ventanas corridas y entrada de vidrio azul con marquesina
    bm = bmesh.new()
    for zz in (1.1, 4.6):
        E.caja(bm, (0.5 * (xs + W / 2) + 1.5, -0.04, zz), (W / 2 - xs - 6.0, 0.08, 1.3), 0)
    E.caja(bm, (W / 2 - 3.2, -0.05, 0), (3.4, 0.1, 3.2), 1)
    E.objeto("Grupo7_ala_vidrios", bm, [M["vidrio"], bpy.data.materials.get("Vidrio_azul") or M["vidrio"]], p, col)
    bm = bmesh.new()
    E.caja(bm, (W / 2 - 3.2, -1.3, 3.3), (4.6, 2.6, 0.2), 0)
    E.objeto("Grupo7_marquesina", bm, [M["blanco"]], p, col)

    # techo plano con vigas que asoman bajo el alero
    bm = bmesh.new()
    E.caja(bm, (0, D / 2 - 0.6, h_nave), (W + 1.2, D + 2.4, 0.3), 0)
    for k in range(int(W / 1.6) + 1):
        x = -W / 2 + k * 1.6
        if x > xs:
            break
        E.caja(bm, (x, -1.0, h_nave - 0.22), (0.16, 2.2, 0.22), 0)
    E.objeto("Grupo7_techo", bm, [M["blanco"]], p, col)

    # anexo blanco viejo a la izquierda, con su ventana de rejas
    bm = bmesh.new()
    E.caja(bm, (-W / 2 - 4.5, 7.0, 0), (9.0, 12.0, 4.3), 0)
    E.caja(bm, (-W / 2 - 4.5, 7.0, 4.3), (9.6, 12.6, 0.2), 0)
    E.objeto("Grupo7_anexo", bm, [M["blanco"]], p, col)
    bm = bmesh.new()
    Hg.ventana_reja(bm, -W / 2 - 4.5, 1.0, 2.2, 2.0, 0.9, 0, 1)
    E.objeto("Grupo7_anexo_reja", bm, [M["oscuro"], M["reja"]], p, col)

    # estacionamiento, caminería de adoquines, brocal amarillo, frangipanes y palmas
    bm = bmesh.new()
    E.caja(bm, (0, -7.5, 0), (W + 14, 15.0, 0.1), 0)
    E.objeto("Grupo7_estacionamiento", bm, [M["concreto_patio"]], p, col)
    bm = bmesh.new()
    E.caja(bm, (0, -0.9, 0), (W, 1.8, 0.16), 0)
    E.objeto("Grupo7_acera", bm, [M["acera"]], p, col)
    bm = bmesh.new()
    E.caja(bm, (0, -1.85, 0), (W, 0.2, 0.18), 0)
    E.objeto("Grupo7_brocal", bm, [M["amarillo"]], p, col)
    bm, bh = bmesh.new(), bmesh.new()
    for x in (-18.5, -12.0, -5.5):
        for r in range(3):                                   # frangipán: tronco que se abre en ramas
            a = r * 2.1 + rnd.random()
            E.cilindro(bm, (x, -0.9, 0.15), 0.09, 0.05, 3.4, 0, 7, (0.25, 0, a))
            tip = Vector((x + 0.8 * math.sin(a) * 0.9, -0.9 - 0.8 * math.cos(a) * 0.9, 3.4))
            E.hojas(bh, tip, 0.75, 90, rnd, 0, 0.28)
    E.objeto("Grupo7_frangipanes", bm, [E.material("Tronco_claro", (0.62, 0.60, 0.55), 0.7)], p, col)
    E.objeto("Grupo7_frangipanes_hojas", bh, [M["follaje"]], p, col)
    palma = bpy.data.meshes.get("Palma_real")
    if palma:
        for x, y in ((-W / 2 - 8.0, -2.0), (-W / 2 - 3.0, -3.5)):
            E.instancia(palma, "Palma_G7", p, col, x, y, 0.5)
    # sedán blanco estacionado
    bm = bmesh.new()
    E.caja(bm, (0, 0, 0.3), (1.8, 4.5, 0.75), 0)
    E.caja(bm, (0, -0.2, 1.05), (1.65, 2.3, 0.55), 1)
    for wx in (-0.85, 0.85):
        for wy in (-1.4, 1.4):
            E.cilindro(bm, (wx - 0.11, wy, 0.33), 0.33, 0.33, 0.22, 2, 16, (0, math.pi / 2, 0))
    ob = E.objeto("Grupo7_sedan", bm, [M["auto_blanco"], M["vidrio"], M["llanta"]], p, col)
    ob.location = (W / 2 - 9.0, -4.0, 0)
    ob.rotation_euler = (0, 0, math.radians(90))
    E.camara("Cam_Grupo7", p, col, (-3.0, -42.0, 1.7), (-3.0, 0.0, 4.6), 26)
    return p


def main():
    col = limpiar()
    M = Hg.materiales(E.mats())
    M["acero_dorm"] = E.material("Acero_marron", (0.10, 0.06, 0.045), 0.5, 0.5)
    M["puerta_marron"] = E.material("Puerta_marron", (0.30, 0.10, 0.06), 0.6)
    M["lamina_naranja"] = E.pbr("Lamina_naranja", "lamina", 2.0, metal=0.15, pintura=(0.62, 0.28, 0.15))
    M["arbusto_amarillo"] = E.con_ruido(bpy.data.materials.new("Arbusto_amarillo"), (0.25, 0.32, 0.03),
                                        (0.55, 0.60, 0.08), 2.0, 0.4)
    z = bpy.context.scene.get("cota_DIDA")
    if z is None:
        raise SystemExit("Primero hay que correr dida.py")
    E.aplanar(-364.3, -706.8, "cota_dormitorios", 40.0, 70.0, z0=z)
    E.aplanar(-271.9, -677.8, "cota_grupo7", 50.0, 80.0, z0=z)
    hs = huellas_h()
    datos = []
    for i, pts in enumerate(hs):
        datos.append(dormitorio(f"Dormitorio_{i + 1}", pts, M, col, z))
    grupo7(M, col, z)
    pasto = E.pbr("Pasto_dormitorios", "pasto", 2.5, (0.50, 0.88, 0.32), fade=(55.0, 90.0),
                  variacion=(0.04, (0.95, 0.80, 0.45)))
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, radius=90.0, segments=96)
    ob = E.objeto("Pasto_dormitorios_G7", bm, [pasto], None, col)
    ob.location = (-320.0, -700.0, z + 0.012)
    # cámara como la foto del patio entre barras: desde el noroeste, mirando hacia la escalera
    if datos:
        p, (xe0, xe1, y0, y1, L) = datos[0]
        xc = 0.5 * (xe0 + xe1)
        E.camara("Cam_Dormitorios", p, col, (xc - 7.0, L + 14.0, 1.6), (xc + 0.5, L - 9.0, 5.0), 22)
    bpy.ops.wm.save_mainfile()
    print("dormitorios y Grupo 7 listos:", len(hs), "edificios en H")


main()
