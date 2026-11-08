"""G14 (edificio de dos pisos con celosía, techo azul y el avión en pedestal) y el Hangar 3 (cobertizo de cerchas
rojas delante de un hangar de lámina). Se corre después de hangares.py y guarda el .blend:

    blender --background BaseSucre.blend --python g14_hangar3.py

Fotos: G14 FRENTE AVION, G14 UNA PARTE, G14 CASI FINAL, OTRA VISTA G14, AVION DE G14, LETRERO G14, PLANTA ELECTRICA
DE G14, G14 PLATA ELECTRICA Y ESTACIONAMIENTO, HANGAR 3, HANGAR 3 FRENTE (FRENTE), HANGAR FRENTE CASI FINAL.
Ubicación y medidas (confianza baja): datos/ubicaciones.json. Mismo marco que la DIDA: el frente mira hacia -Y.
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import entrada as E  # noqa: E402
import hangares as Hg  # noqa: E402
import mentor  # noqa: E402

rnd = E.random.Random(14)


def limpiar():
    col = bpy.data.collections.get("G14_Hangar3")
    if col:
        for ob in list(col.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.collections.remove(col)
    col = bpy.data.collections.new("G14_Hangar3")
    bpy.context.scene.collection.children.link(col)
    return col


def viga(bm, a, b, grueso, mi=0):
    """Perfil recto de sección cuadrada entre dos puntos."""
    vs = bmesh.ops.create_cube(bm, size=1.0)["verts"]
    d = b - a
    rot = d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    M = Matrix.Translation((a + b) / 2) @ rot @ Matrix.Diagonal((grueso, grueso, d.length, 1))
    bmesh.ops.transform(bm, matrix=M, verts=vs)
    for f in {f for v in vs for f in v.link_faces}:
        f.material_index = mi


def mat_celosia():
    """Bloques calados: retícula de huecos oscuros con marcos de concreto claro."""
    m = bpy.data.materials.get("Celosia")
    if m:
        return m
    m = bpy.data.materials.new("Celosia")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapa = nt.nodes.new("ShaderNodeMapping")
    mapa.inputs["Rotation"].default_value = (math.pi / 2, 0, 0)       # la retícula sobre el plano XZ de la fachada
    nt.links.new(coord.outputs["Object"], mapa.inputs["Vector"])
    lad = nt.nodes.new("ShaderNodeTexBrick")
    lad.offset = 0.0
    lad.inputs["Color1"].default_value = (0.03, 0.03, 0.03, 1)
    lad.inputs["Color2"].default_value = (0.06, 0.06, 0.05, 1)
    lad.inputs["Mortar"].default_value = (0.80, 0.76, 0.64, 1)
    lad.inputs["Scale"].default_value = 1.0
    lad.inputs["Mortar Size"].default_value = 0.045
    lad.inputs["Brick Width"].default_value = 0.20
    lad.inputs["Row Height"].default_value = 0.20
    nt.links.new(mapa.outputs["Vector"], lad.inputs["Vector"])
    nt.links.new(lad.outputs["Color"], b.inputs["Base Color"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.6
    bp.invert = True
    nt.links.new(lad.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = 0.85
    return m


def mat_avion_blanco():
    """Blanco con las puntas de las alas rojo anaranjado (como el avión del G14)."""
    m = bpy.data.materials.get("Avion_blanco_rojo")
    if m:
        return m
    m = bpy.data.materials.new("Avion_blanco_rojo")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(coord.outputs["Object"], sep.inputs["Vector"])
    ab = nt.nodes.new("ShaderNodeMath")
    ab.operation = "ABSOLUTE"
    nt.links.new(sep.outputs["X"], ab.inputs[0])
    corte = nt.nodes.new("ShaderNodeMath")
    corte.operation = "GREATER_THAN"
    corte.inputs[1].default_value = 3.9
    nt.links.new(ab.outputs["Value"], corte.inputs[0])
    mx = nt.nodes.new("ShaderNodeMix")
    mx.data_type = "RGBA"
    mx.inputs["A"].default_value = (0.86, 0.87, 0.88, 1)
    mx.inputs["B"].default_value = (0.85, 0.14, 0.05, 1)
    nt.links.new(corte.outputs["Value"], mx.inputs["Factor"])
    nt.links.new(mx.outputs["Result"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.3
    return m


# ----------------------------------------------------------------------------------- G14
def g14(M, col, z):
    ub = Hg.UBS["G14"]
    p = Hg.origen("G14_origen", ub, col, z)
    L, D = ub["ancho"], ub["fondo"]
    h1, h2 = 3.4, 6.8
    cel = mat_celosia()
    piedra = E.pbr("Piedra_zocalo", "acera", 1.2, (0.55, 0.55, 0.55))
    crema = E.pbr("Pared_crema", "pared", 3.0, pintura=(0.86, 0.80, 0.64))
    azul = E.pbr("Lamina_azul", "lamina", 2.0, metal=0.2, pintura=(0.16, 0.27, 0.52))
    oscuro = E.material("Madera_oscura", (0.05, 0.035, 0.025), 0.6)

    bm = bmesh.new()
    E.caja(bm, (0, D / 2, 0), (L, D, h2), 0)
    E.objeto("G14_volumen", bm, [crema], p, col)

    bm = bmesh.new()
    E.caja(bm, (0, -0.03, 0), (L + 0.06, 0.08, 0.6), 0)                   # zócalo de piedra
    E.objeto("G14_zocalo", bm, [piedra], p, col)

    # planta baja: franjas de celosía alta, puertas y ventanas; alero oscuro corrido sobre postes
    bm = bmesh.new()
    for x in range(-18, 19, 6):
        E.caja(bm, (x, -0.04, 2.05), (4.4, 0.08, 0.55), 0)
    for x in (-15.0, -3.0, 9.0):
        E.caja(bm, (x, -0.03, 0.6), (1.6, 0.06, 1.25), 1)                  # ventanas bajas
    E.caja(bm, (-9.0, -0.03, 0.0), (1.8, 0.06, 2.3), 2)                     # puerta
    E.caja(bm, (3.0, -0.03, 0.0), (1.8, 0.06, 2.3), 2)
    E.caja(bm, (14.5, -0.05, 0.0), (4.2, 0.1, h2 - 0.2), 0)                 # paño de celosía de dos pisos
    E.objeto("G14_planta_baja", bm, [cel, M["vidrio"], M["oscuro"]], p, col)
    bm = bmesh.new()
    E.caja(bm, (0, -1.1, 2.75), (L, 2.2, 0.5), 0)                           # alero del corredor
    for x in range(-20, 21, 5):
        E.caja(bm, (x, -2.0, 0.0), (0.18, 0.18, 2.75), 0)
    # piso alto: pilares oscuros y ventanas corridas de aluminio
    for x in range(-21, 22, 6):
        E.caja(bm, (x, -0.06, h1), (0.3, 0.12, h2 - h1), 0)
    E.objeto("G14_estructura", bm, [oscuro], p, col)
    bm = bmesh.new()
    for x in range(-18, 19, 6):
        if abs(x - 14.5) < 3:
            continue
        E.caja(bm, (x, -0.03, 4.4), (4.6, 0.06, 1.25), 0)
        for k in range(1, 4):
            E.caja(bm, (x - 2.3 + k * 1.15, -0.07, 4.4), (0.05, 0.05, 1.25), 1)
        E.caja(bm, (x, -0.07, 5.0), (4.6, 0.05, 0.05), 1)
    E.objeto("G14_ventanas_altas", bm, [M["vidrio"], M["reja"]], p, col)
    bm = bmesh.new()
    for x in (-16.0, -4.0, 8.0):
        E.caja(bm, (x, -0.35, 3.7), (0.8, 0.6, 0.5), 0)
    E.objeto("G14_aires", bm, [M["aire"]], p, col)

    # techo azul a dos aguas, muy bajo, con alero y canes oscuros
    bm = bmesh.new()
    for s in (-1, 1):
        yb = -1.2 if s < 0 else D + 1.2
        bm.faces.new([bm.verts.new(v) for v in ((-L / 2 - 0.8, yb, h2 - 0.1), (L / 2 + 0.8, yb, h2 - 0.1),
                                                (L / 2 + 0.8, D / 2, h2 + 0.9), (-L / 2 - 0.8, D / 2, h2 + 0.9))])
    E.objeto("G14_techo", bm, [azul], p, col)
    bm = bmesh.new()
    E.caja(bm, (0, -1.25, h2 - 0.35), (L + 1.7, 0.08, 0.3), 0)              # fascia
    for x in range(-21, 22, 1):
        E.caja(bm, (x, -0.6, h2 - 0.25), (0.08, 1.2, 0.14), 0)
    E.objeto("G14_canes", bm, [oscuro], p, col)

    # lema sobre la franja oscura del extremo noroeste
    E.texto("SI NO TE VENCES, VENCERÁS", 0.32, M["blanco"], p, col, (-12.0, -2.22, 3.0), (math.pi / 2, 0, 0))

    # avión en pedestal tricolor
    bm = bmesh.new()
    for z0, h, mi in ((0.0, 0.9, 2), (0.9, 0.9, 1), (1.8, 0.9, 0)):
        E.caja(bm, (-10.0, -7.0, z0), (0.9, 0.9, h), mi)
    for k in range(8):
        a = math.pi * (0.15 + 0.7 * k / 7)
        E.cilindro(bm, (-10.0 + 0.32 * math.cos(a), -7.46, 1.15 + 0.32 * math.sin(a)), 0.05, 0.05, 0.02, 3, 6,
                   (math.pi / 2, 0, 0))
    E.objeto("G14_pedestal", bm, [E.material("Amarillo_bandera", (0.95, 0.72, 0.05), 0.5),
                                  E.material("Azul_bandera", (0.03, 0.10, 0.45), 0.5),
                                  E.material("Rojo_bandera", (0.75, 0.03, 0.04), 0.5), M["blanco"]], p, col)
    # T-34 Mentor sobre el pedestal (ella: «un Mentor en 3D»), nariz algo arriba y alabeado, como en la foto;
    # carenado blanco donde el pedestal se une al fuselaje
    bm = bmesh.new()
    E.cilindro(bm, (-10.0, -7.0, 2.7), 0.45, 0.22, 0.75, 0, 16)
    E.objeto("G14_carenado_pedestal", bm, [M["blanco"]], p, col)
    av = mentor.crear(p, col)
    av.location = (-10.0, -7.0, 3.75)
    av.rotation_euler = (math.radians(9), math.radians(-7), math.radians(52))

    # árboles podados en cono y palmas reales al frente
    bh = bmesh.new()
    for x, y in ((-2.0, -6.5), (10.0, -6.8)):
        for k in range(6):
            E.hojas(bh, Vector((x, y, 1.4 + k * 0.85)), 2.2 - k * 0.33, 520 - k * 60, rnd, 0, 0.16)
    E.objeto("G14_arboles_cono", bh, [M["follaje"]], p, col)
    bm = bmesh.new()
    for x, y in ((-2.0, -6.5), (10.0, -6.8)):
        E.cilindro(bm, (x, y, 0), 0.16, 0.1, 1.6, 0, 8)
    E.objeto("G14_troncos", bm, [M["tronco"]], p, col)
    palma = bpy.data.meshes.get("Palma_real")
    if palma:
        for x in (4.5, 18.0):
            E.instancia(palma, "Palma_G14", p, col, x, -5.0, 0.95)

    # acera, letrero ESCORPIONES, planta eléctrica y estacionamiento techado hacia la calle (sureste = +X)
    bm = bmesh.new()
    E.caja(bm, (0, -4.0, 0), (L + 4, 8.0, 0.12), 0)
    E.objeto("G14_acera", bm, [M["concreto_patio"]], p, col)
    bm = bmesh.new()
    for dx in (-1.9, 1.9):
        E.caja(bm, (L / 2 + 8.0 + dx, -14.0, 0), (0.2, 0.2, 1.2), 0)
    E.caja(bm, (L / 2 + 8.0, -14.0, 1.2), (4.6, 0.25, 2.2), 1)
    E.caja(bm, (L / 2 + 8.0, -14.0, 3.4), (4.8, 0.4, 0.2), 2)
    E.objeto("G14_letrero", bm, [M["blanco"], E.material("Letrero_oscuro", (0.18, 0.05, 0.04), 0.5),
                                 M["rojo_portal"]], p, col)
    E.texto("ESCORPIONES", 0.55, E.material("Letras_naranja", (0.95, 0.55, 0.10), 0.4), p, col,
            (L / 2 + 8.0, -14.15, 2.1), (math.pi / 2, 0, 0), extr=0.02)
    # entre el CEA y el G14 (ella: «al lado del CEA, después de un parquecito y una planta eléctrica"): el frente (-Y)
    # da a la calle de la DIDA; el CEA queda hacia -X. Yendo desde el CEA: parquecito, planta eléctrica y el G14.
    xp, yp = -L / 2 - 5.5, 4.0                                               # planta eléctrica, pegada al G14
    bm = bmesh.new()
    E.caja(bm, (xp + 4.5, yp, 0), (5.0, 4.5, 3.0), 0)                        # caseta
    E.caja(bm, (xp + 4.5, yp, 3.0), (5.4, 4.9, 0.2), 1)
    E.caja(bm, (xp + 2.0 - 0.03, yp, 0), (0.06, 1.0, 2.2), 2)
    E.objeto("G14_planta_caseta", bm, [M["blanco"], M["poste"], M["oscuro"]], p, col)
    bm = bmesh.new()
    E.caja(bm, (xp - 2.0, yp, 0), (3.2, 1.6, 1.8), 0)                        # generador verde
    E.objeto("G14_generador", bm, [E.material("Verde_generador", (0.04, 0.22, 0.14), 0.5)], p, col)
    bm = bmesh.new()
    for x in (xp - 4.5, xp + 0.5):
        for y in (yp - 2.0, yp + 2.0):
            E.caja(bm, (x, y, 0), (0.12, 0.12, 2.9), 0)
    E.caja(bm, (xp - 2.0, yp, 2.9), (5.6, 4.6, 0.12), 0)
    # cerca de malla alrededor de la planta
    for (cx, cy), (sx, sy) in (((xp - 2.0, yp - 3.0), (6.4, 0.05)), ((xp - 2.0, yp + 3.0), (6.4, 0.05)),
                               ((xp - 5.2, yp), (0.05, 6.0))):
        E.caja(bm, (cx, cy, 0), (sx, sy, 2.2), 0)
    E.objeto("G14_techo_generador", bm, [M["poste"]], p, col)
    # parquecito entre la planta y el CEA: caminería en L, bancos, columpios (video 2, t_036), matas y dos árboles
    xq = -L / 2 - 17.0
    bm = bmesh.new()
    E.caja(bm, (xq, -2.0, 0), (12.0, 1.8, 0.1), 0)
    E.caja(bm, (xq + 5.0, 3.5, 0), (1.8, 9.0, 0.1), 0)
    E.objeto("G14_parque_caminos", bm, [M["acera"]], p, col)
    bm = bmesh.new()
    for x in (xq - 4.0, xq + 1.0):
        E.caja(bm, (x, -0.8, 0), (1.8, 0.45, 0.45), 0)
    E.objeto("G14_parque_bancos", bm, [M["concreto_patio"]], p, col)
    bm, bc = bmesh.new(), bmesh.new()
    cx, cy, alto, largo = xq - 1.0, 6.5, 2.4, 4.2                             # columpios de dos puestos
    for sx in (-1, 1):
        for sy in (-1, 1):
            a = Vector((cx + sx * largo / 2, cy + sy * 0.9, 0.0))
            b = Vector((cx + sx * largo / 2, cy, alto))
            viga(bm, a, b, 0.07)
    viga(bm, Vector((cx - largo / 2, cy, alto)), Vector((cx + largo / 2, cy, alto)), 0.08)
    for x in (cx - 1.0, cx + 1.0):
        for dx in (-0.22, 0.22):
            viga(bc, Vector((x + dx, cy, alto)), Vector((x + dx, cy, 0.45)), 0.015, 0)
        E.caja(bc, (x, cy, 0.42), (0.5, 0.2, 0.04), 1)
    E.objeto("G14_columpios_marco", bm, [E.material("Tubo_amarillo", (0.85, 0.65, 0.08), 0.45, 0.4)], p, col)
    E.objeto("G14_columpios", bc, [M["poste"], M["negro"]], p, col)
    bh = bmesh.new()
    for x, y in ((xq - 5.0, -4.5), (xq + 1.5, -5.0), (xq + 4.0, 9.0), (xq - 5.5, 10.0)):
        E.hojas(bh, Vector((x, y, 0.6)), 0.9, 240, rnd, 0, 0.12)
    E.objeto("G14_parque_matas", bh, [M["arbusto"]], p, col)
    bh = bmesh.new()
    for x, y in ((xq - 4.0, 2.5), (xq + 3.0, 12.0)):
        E.hojas(bh, Vector((x, y, 5.0)), 2.6, 900, rnd, 0, 0.25)
    E.objeto("G14_parque_arbol", bh, [M["follaje"]], p, col)
    bm = bmesh.new()                                                        # estacionamiento techado
    for x in range(int(L / 2 + 10), int(L / 2 + 22), 6):
        for y in (-9.0, -2.0):
            E.caja(bm, (x, y, 0), (0.15, 0.15, 2.8), 0)
    E.caja(bm, (L / 2 + 15.0, -5.5, 2.8), (13.0, 8.2, 0.1), 0)
    for k in range(14):
        E.caja(bm, (L / 2 + 15.0, -9.4 + k * 0.6, 2.95), (13.0, 0.12, 0.12), 0)
    E.objeto("G14_estacionamiento", bm, [oscuro], p, col)
    E.camara("Cam_G14", p, col, (-24.0, -26.0, 1.7), (-4.0, 0.0, 3.6), 26)
    # desde la calle de la DIDA, a ~50 m: el G14 de frente, la planta y el parquecito a la izquierda (hacia el CEA)
    E.camara("Cam_G14_Calle", p, col, (-14.0, -50.0, 1.7), (-12.0, 0.0, 3.5), 30)
    return p


# ----------------------------------------------------------------------------------- Hangar 3
def hangar3(M, col, z):
    ub = Hg.UBS["Hangar 3"]
    p = Hg.origen("Hangar3_origen", ub, col, z)
    W, D = ub["ancho"], ub["fondo"]
    he, hc = 7.0, 11.5
    lamina_vieja = E.pbr("Lamina_vieja", "lamina", 2.0, metal=0.25, pintura=(0.55, 0.53, 0.49))
    rojo = E.pbr("Lamina_roja_cerchas", "lamina", 2.0, metal=0.2, pintura=(0.45, 0.12, 0.06))
    rojo_liso = E.material("Acero_rojo", (0.38, 0.09, 0.05), 0.55, 0.4)
    verde = E.pbr("Lamina_verde_oscuro", "lamina", 2.0, metal=0.2, pintura=(0.08, 0.28, 0.22))

    bm = bmesh.new()
    E.caja(bm, (0, D / 2, 0), (W, D, he), 0)
    for y in (0.0, D):
        bm.faces.new([bm.verts.new(v) for v in ((-W / 2, y, he), (W / 2, y, he), (0, y, hc))])
    E.objeto("Hangar3_muros", bm, [lamina_vieja], p, col)
    bm = bmesh.new()
    for s in (-1, 1):
        bm.faces.new([bm.verts.new(v) for v in ((s * (W / 2 + 0.6), -0.4, he - 0.3), (0, -0.4, hc + 0.05),
                                                (0, D + 0.4, hc + 0.05), (s * (W / 2 + 0.6), D + 0.4, he - 0.3))])
    E.objeto("Hangar3_techo", bm, [M["lamina_techo"]], p, col)
    # franja de rejillas color arena en lo alto del frente y ventanas de vidrio cuadriculado
    bm = bmesh.new()
    Hg.banda_rejillas(bm, -W / 2 + 0.5, W / 2 - 0.5, 0.0, 5.3, 6.8, 0, 1, 8)
    for x in (-13.0, -6.5, 1.0):
        E.caja(bm, (x, -0.03, 1.6), (2.4, 0.06, 1.8), 2)
        for k in range(1, 4):
            E.caja(bm, (x - 1.2 + k * 0.6, -0.07, 1.6), (0.05, 0.04, 1.8), 3)
        for k in range(1, 3):
            E.caja(bm, (x, -0.07, 1.6 + k * 0.6), (2.4, 0.04, 0.05), 3)
    E.objeto("Hangar3_frente", bm, [E.material("Lamas_arena", (0.72, 0.56, 0.38), 0.6), lamina_vieja,
                                    M["vidrio"], M["reja"]], p, col)

    # cobertizo de techo rojo con cerchas, delante del frente y corrido al suroeste
    xc, ancho, fondo = -6.9, 21.0, 9.0
    bm = bmesh.new()
    bm.faces.new([bm.verts.new(v) for v in ((xc - ancho / 2, 0.0, 5.0), (xc + ancho / 2, 0.0, 5.0),
                                            (xc + ancho / 2, -fondo, 4.2), (xc - ancho / 2, -fondo, 4.2))])
    E.objeto("Hangar3_cobertizo_techo", bm, [rojo], p, col)
    def techo_z(y):                                    # el techo baja de 5,0 m (pared) a 4,2 m (borde)
        return 5.0 + 0.8 * y / fondo

    bm = bmesh.new()
    for k in range(8):                                 # cerchas: cordón inferior y diagonales en zigzag
        x = xc - ancho / 2 + 0.4 + k * (ancho - 0.8) / 7
        E.caja(bm, (x, -fondo / 2, 3.85), (0.12, fondo, 0.12), 0)
        pasos = 8
        for j in range(pasos):
            ya, yb = -j * fondo / pasos, -(j + 1) * fondo / pasos
            za, zb = (3.91, techo_z(yb) - 0.04) if j % 2 == 0 else (techo_z(ya) - 0.04, 3.91)
            viga(bm, Vector((x, ya, za)), Vector((x, yb, zb)), 0.06)
    for x in (xc - ancho / 2 + 0.4, xc, xc + ancho / 2 - 0.4):
        E.caja(bm, (x, -fondo + 0.4, 1.4), (0.25, 0.25, 2.5), 0)                   # columnas
    E.objeto("Hangar3_cerchas", bm, [rojo_liso], p, col)
    bm = bmesh.new()
    for x in (xc - ancho / 2 + 0.4, xc, xc + ancho / 2 - 0.4):
        E.caja(bm, (x, -fondo + 0.4, 0), (0.26, 0.26, 1.4), 0)                     # base blanca de columnas
    E.objeto("Hangar3_columnas_base", bm, [M["blanco"]], p, col)
    bm = bmesh.new()
    E.caja(bm, (xc, -fondo / 2, 0), (ancho + 2, fondo + 1, 0.1), 0)
    E.objeto("Hangar3_piso", bm, [M["concreto_patio"]], p, col)

    # cobertizo verde oscuro al noreste
    bm = bmesh.new()
    E.caja(bm, (W / 2 + 4.0, D / 2, 0), (8.0, D - 2, 4.0), 0)
    E.objeto("Hangar3_anexo", bm, [lamina_vieja], p, col)
    bm = bmesh.new()
    bm.faces.new([bm.verts.new(v) for v in ((W / 2, 0.5, 4.9), (W / 2, D - 0.5, 4.9),
                                            (W / 2 + 8.6, D - 0.5, 3.9), (W / 2 + 8.6, 0.5, 3.9))])
    E.objeto("Hangar3_anexo_techo", bm, [verde], p, col)

    # camioneta blanca bajo el cobertizo
    bm = bmesh.new()
    E.caja(bm, (0, 0, 0.35), (1.9, 5.0, 1.5), 0)
    E.caja(bm, (0, 2.0, 1.85), (1.85, 1.0, 0.5), 1)
    for wx in (-0.9, 0.9):
        for wy in (-1.6, 1.6):
            E.cilindro(bm, (wx - 0.13, wy, 0.38), 0.38, 0.38, 0.26, 2, 16, (0, math.pi / 2, 0))
    ob = E.objeto("Hangar3_camioneta", bm, [M["auto_blanco"], M["vidrio"], M["llanta"]], p, col)
    ob.location = (xc + 7.0, -4.5, 0)
    ob.rotation_euler = (0, 0, math.radians(90))
    E.camara("Cam_Hangar3", p, col, (xc - 4.0, -24.0, 1.6), (xc + 1.0, 0.0, 3.6), 24)
    return p


def main():
    col = limpiar()
    M = Hg.materiales(E.mats())
    sc = bpy.context.scene
    z = sc.get("cota_DIDA")
    if z is None:
        raise SystemExit("Primero hay que correr dida.py y hangares.py")
    for clave, ub in (("cota_G14", Hg.UBS["G14"]), ("cota_Hangar3", Hg.UBS["Hangar 3"])):
        E.aplanar(ub["este"], ub["norte"], clave, 45.0, 75.0, z0=z)
    g14(M, col, z)
    hangar3(M, col, z)
    pasto = E.pbr("Pasto_G14", "pasto", 2.5, (0.45, 0.95, 0.30), fade=(45.0, 75.0),
                  variacion=(0.05, (0.85, 0.75, 0.45)))
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, radius=75.0, segments=96)
    ob = E.objeto("Pasto_G14", bm, [pasto], None, col)
    ob.location = (-362.0, -602.0, z + 0.01)
    # vista aérea de los cinco edificios de la calle de hangares
    E.camara("Cam_Hangares_Norte", None, col, (-230.0, -820.0, z + 120.0), (-400.0, -650.0, z), 28)
    bpy.ops.wm.save_mainfile()
    print("G14 y Hangar 3 listos")


main()
