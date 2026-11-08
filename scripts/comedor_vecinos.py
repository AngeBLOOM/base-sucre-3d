"""Vecinos del comedor que ella mandó en fotos (2026-11-05), siguiendo la vía al oeste del comedor:

- el tanque de agua elevado: torre de acero celeste de seis patas con arriostramiento en X, tanque galvanizado de
  fondo semiesférico con pasarela, baranda y escalera; abajo, cercado de malla ciclón con portón doble, el tanque
  hidroneumático celeste, las casetas de bombas y la tubería blanca;
- el CAA (Centro de Adiestramiento Aeronáutico): dos pisos, planta baja gris y alta blanca con franjas corridas de
  ventanas de marco blanco, el bloque azul al centro con el letrero y la entrada, celosías en las puntas, tres astas
  y reflectores en la azotea, palmitas al frente, acera con brocal amarillo, estacionamiento con rayas blancas y las
  letras «CAA» de bulto en el césped junto a la vía.
Sin adornos de Navidad (en las fotos hay cortinas rojas y verdes y coronas: no se modelan).
Se corre después de comedor.py:

    blender --background BaseSucre.blend --python comedor_vecinos.py
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

rnd = E.random.Random(91)


def limpiar():
    col = bpy.data.collections.get("Comedor_vecinos")
    if col:
        for ob in list(col.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.collections.remove(col)
    col = bpy.data.collections.new("Comedor_vecinos")
    bpy.context.scene.collection.children.link(col)
    return col


def mat_malla():
    """Malla ciclón: gris galvanizado casi transparente (de lejos se ve como una veladura)."""
    m = bpy.data.materials.get("Malla_ciclon")
    if m:
        return m
    m = E.material("Malla_ciclon", (0.55, 0.57, 0.58), 0.45, 0.8)
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Alpha"].default_value = 0.28
    if hasattr(m, "surface_render_method"):
        m.surface_render_method = "DITHERED"
    return m


def barra(bm, a, b, r, mi, seg=6):
    """Cilindro de a a b."""
    a, b = Vector(a), Vector(b)
    d = b - a
    vs = bmesh.ops.create_cone(bm, cap_ends=False, segments=seg, radius1=r, radius2=r, depth=d.length)["verts"]
    T = Matrix.Translation((a + b) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=T, verts=vs)
    for f in {f for v in vs for f in v.link_faces}:
        f.material_index = mi


def cerca(bm, bmm, pts, alto=2.2, paso=3.0, mi=0):
    """Cerca de malla ciclón con postes, tubo superior y la malla."""
    for a, b in zip(pts, pts[1:]):
        a, b = Vector(a), Vector(b)
        L = (b - a).length
        n = max(1, int(L / paso))
        for k in range(n + 1):
            q = a.lerp(b, k / n)
            E.cilindro(bm, (q.x, q.y, 0), 0.04, 0.04, alto + 0.25, mi, 8)
        barra(bm, (a.x, a.y, alto), (b.x, b.y, alto), 0.025, mi)
        bmm.faces.new([bmm.verts.new(v) for v in ((a.x, a.y, 0.05), (b.x, b.y, 0.05), (b.x, b.y, alto),
                                                  (a.x, a.y, alto))])


def tanque(M, col, z):
    ub = Hg.UBS["Tanque de agua"]
    p = Hg.origen("Tanque_origen", ub, col, z)
    celeste = E.material("Celeste_tanque", (0.30, 0.55, 0.72), 0.45, 0.3)
    galv = E.pbr("Tanque_galvanizado", "lamina_gastada", 2.5, metal=0.7, pintura=(0.42, 0.45, 0.46))
    blanco = M["blanco"]
    cy = 7.0                                         # centro de la torre (local), detrás de la cerca
    Ht, Rt, Rb = 19.0, 3.0, 4.2                      # altura al fondo del tanque, radio de patas arriba y abajo
    bm = bmesh.new()
    patas = []
    for k in range(6):
        a = 2 * math.pi * k / 6 + 0.3
        pb = Vector((Rb * math.cos(a), cy + Rb * math.sin(a), 0.3))
        pt = Vector((Rt * math.cos(a), cy + Rt * math.sin(a), Ht + 0.8))
        patas.append((pb, pt))
        barra(bm, pb, pt, 0.16, 0, 10)
        E.caja(bm, (pb.x, pb.y, 0.0), (0.8, 0.8, 0.35), 1)                     # dado de concreto
    niveles = [0.3 + i * (Ht + 0.5) / 5 for i in range(6)]
    for i in range(6):
        (a0, a1), (b0, b1) = patas[i], patas[(i + 1) % 6]

        def en(p0, p1, zz):
            return p0.lerp(p1, (zz - p0.z) / (p1.z - p0.z))
        for j in range(5):
            za, zb = niveles[j], niveles[j + 1]
            pa0, pa1, pb0, pb1 = en(a0, a1, za), en(a0, a1, zb), en(b0, b1, za), en(b0, b1, zb)
            barra(bm, pa0, pb1, 0.05, 0)                                         # X
            barra(bm, pb0, pa1, 0.05, 0)
            barra(bm, pa1, pb1, 0.07, 0)                                         # horizontal
    E.objeto("Tanque_torre", bm, [celeste, M["concreto"]], p, col)
    # tanque: fondo semiesférico, cilindro y techo cónico bajo, pasarela con baranda
    bm = bmesh.new()
    r, h = 4.3, 4.2
    sph = bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=r)["verts"]
    for v in sph:
        if v.co.z > 0:
            v.co.z = 0.0
    bmesh.ops.translate(bm, vec=Vector((0, cy, Ht + 0.2 + r * 0.55)), verts=sph)
    for v in sph:
        v.co.z = Ht + 0.2 + r * 0.55 + (v.co.z - (Ht + 0.2 + r * 0.55)) * 0.55
    E.cilindro(bm, (0, cy, Ht + 0.2 + r * 0.55), r, r, h, 0, 32)
    E.cilindro(bm, (0, cy, Ht + 0.2 + r * 0.55 + h), r, 0.4, 0.5, 0, 32)
    E.objeto("Tanque_deposito", bm, [galv], p, col)
    zc = Ht + 0.2 + r * 0.55
    bm = bmesh.new()
    E.cilindro(bm, (0, cy, zc - 0.05), r + 0.9, r + 0.9, 0.08, 0, 40)              # pasarela
    for k in range(28):
        a = 2 * math.pi * k / 28
        E.cilindro(bm, ((r + 0.85) * math.cos(a), cy + (r + 0.85) * math.sin(a), zc), 0.025, 0.025, 1.05, 0, 6)
    for zz in (zc + 0.55, zc + 1.05):
        tor = bmesh.ops.create_circle(bm, cap_ends=False, segments=40, radius=r + 0.85)["verts"]
        bmesh.ops.translate(bm, vec=Vector((0, cy, zz)), verts=tor)
        ext = bmesh.ops.extrude_edge_only(bm, edges=list({e for v in tor for e in v.link_edges}))
        bmesh.ops.translate(bm, vec=Vector((0, 0, 0.04)),
                            verts=[g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)])
    a = 2 * math.pi * 1 / 6 + 0.3                                                   # escalera por una pata
    base = Vector((Rb * math.cos(a), cy + Rb * math.sin(a), 0.3))
    tope = Vector((r * math.cos(a), cy + r * math.sin(a), zc + h + 0.4))
    lado = Vector((-math.sin(a), math.cos(a), 0)) * 0.22
    for s in (-1, 1):
        barra(bm, base + lado * s, tope + lado * s, 0.025, 0)
    n = int((tope.z - base.z) / 0.3)
    for k in range(n):
        q = base.lerp(tope, k / n)
        barra(bm, q - lado, q + lado, 0.015, 0)
    E.objeto("Tanque_baranda", bm, [celeste], p, col)
    # abajo: tanque hidroneumático, casetas de bombas, tubería blanca y la cerca con su portón doble
    bm = bmesh.new()
    E.cilindro(bm, (2.2, cy - 1.5, 0.35), 0.6, 0.6, 1.5, 0, 20)
    E.cilindro(bm, (2.2, cy - 1.5, 1.85), 0.6, 0.15, 0.35, 0, 20)
    for dx in (-0.4, 0.4):
        E.cilindro(bm, (2.2 + dx, cy - 1.5, 0), 0.05, 0.05, 0.4, 0, 6)
    E.objeto("Tanque_hidroneumatico", bm, [celeste], p, col)
    bm = bmesh.new()
    for x, y, w, d, hh in ((-1.5, cy - 0.5, 1.6, 1.4, 1.6), (-0.1, cy + 1.0, 1.2, 1.2, 1.3)):
        E.caja(bm, (x, y, 0), (w, d, hh), 0)
    E.objeto("Tanque_casetas", bm, [E.pbr("Concreto_casetas", "concreto_gastado", 2.0, pintura=(0.62, 0.66, 0.66))],
             p, col)
    bm = bmesh.new()
    barra(bm, (2.2, cy - 1.5, 0.9), (2.2, cy + 2.0, 0.9), 0.07, 0)
    barra(bm, (2.2, cy + 2.0, 0.9), (2.2, cy + 2.0, Ht), 0.09, 0)
    barra(bm, (-1.5, cy - 0.5, 0.5), (2.2, cy - 1.5, 0.5), 0.06, 0)
    E.objeto("Tanque_tuberia", bm, [blanco], p, col)
    bm, bmm = bmesh.new(), bmesh.new()
    cerca(bm, bmm, [(-2.5, 0.0), (-7.0, 0.0), (-7.0, 14.0), (7.0, 14.0), (7.0, 0.0), (2.5, 0.0)])
    for x0 in (-2.5, 0.0):                                                        # portón doble
        E.caja(bm, (x0 + 1.25, 0.0, 0.05), (2.5, 0.05, 0.05), 0)
        E.caja(bm, (x0 + 1.25, 0.0, 2.0), (2.5, 0.05, 0.05), 0)
        for xx in (x0 + 0.05, x0 + 2.45):
            E.caja(bm, (xx, 0.0, 0.05), (0.06, 0.06, 2.0), 0)
        bmm.faces.new([bmm.verts.new(v) for v in ((x0, 0.0, 0.1), (x0 + 2.5, 0.0, 0.1), (x0 + 2.5, 0.0, 2.0),
                                                  (x0, 0.0, 2.0))])
    E.objeto("Tanque_cerca", bm, [E.material("Galvanizado", (0.55, 0.56, 0.57), 0.35, 0.8)], p, col)
    E.objeto("Tanque_malla", bmm, [mat_malla()], p, col)
    bm = bmesh.new()
    E.caja(bm, (0, 7.0, -0.05), (13.8, 13.8, 0.1), 0)
    E.objeto("Tanque_tierra", bm, [E.con_ruido(bpy.data.materials.new("Tierra_tanque"), (0.30, 0.24, 0.17),
                                                (0.45, 0.40, 0.30), 0.6)], p, col)
    E.camara("Cam_Tanque", p, col, (-14.0, -16.0, 1.6), (0.0, 7.0, 9.0), 20)


def caa(M, col, z):
    ub = Hg.UBS["CAA"]
    p = Hg.origen("CAA_origen", ub, col, z)
    W, D = ub["ancho"], ub["fondo"]
    H1, H = 3.9, 7.8
    blanco = E.pbr("Friso_blanco_CAA", "friso", 3.0, pintura=(0.84, 0.85, 0.85))
    gris = E.pbr("Friso_gris_CAA", "friso", 3.0, pintura=(0.30, 0.31, 0.33))
    azul = E.pbr("Friso_azul_CAA", "friso", 3.0, pintura=(0.02, 0.12, 0.55))
    vidrio = E.material("Vidrio_CAA", (0.02, 0.04, 0.07), 0.05, 0.1)
    bm = bmesh.new()
    E.caja(bm, (0, D / 2, 0), (W, D, H1), 0)
    E.caja(bm, (0, D / 2, H1), (W, D, H - H1), 1)
    E.caja(bm, (0, D / 2, H), (W + 0.2, D + 0.2, 0.7), 1)                     # pretil
    E.objeto("CAA_volumen", bm, [gris, blanco], p, col)
    bm = bmesh.new()                                                          # franjas grises
    E.caja(bm, (0, -0.04, H1 - 0.15), (W + 0.1, 0.12, 0.3), 0)
    E.caja(bm, (0, -0.06, H + 0.55), (W + 0.3, 0.14, 0.15), 0)
    E.objeto("CAA_franjas", bm, [E.material("Gris_franja_CAA", (0.25, 0.26, 0.28), 0.6)], p, col)
    # franjas corridas de ventanas de marco blanco a los dos lados del bloque azul, en los dos pisos
    bv, bm = bmesh.new(), bmesh.new()
    xb = 4.2                                                                  # medio ancho del bloque azul
    for s in (-1, 1):
        x0, x1 = sorted((s * (xb + 0.8), s * (W / 2 - 2.6)))
        for z0, z1 in ((1.0, 2.7), (4.6, 6.6)):
            E.caja(bv, (0.5 * (x0 + x1), -0.03, z0), (x1 - x0, 0.04, z1 - z0), 0)
            E.caja(bm, (0.5 * (x0 + x1), -0.06, z0 - 0.08), (x1 - x0 + 0.1, 0.06, 0.08), 0)
            E.caja(bm, (0.5 * (x0 + x1), -0.06, z1), (x1 - x0 + 0.1, 0.06, 0.08), 0)
            E.caja(bm, (0.5 * (x0 + x1), -0.06, z0 + 0.62 * (z1 - z0)), (x1 - x0, 0.05, 0.05), 0)
            n = int((x1 - x0) / 1.05)
            for k in range(n + 1):
                E.caja(bm, (x0 + k * (x1 - x0) / n, -0.06, z0), (0.06, 0.06, z1 - z0), 0)
        # celosía de bloques en la punta
        xc = s * (W / 2 - 1.3)
        for i in range(5):
            for j in range(4):
                E.caja(bm, (xc - 0.8 + i * 0.4, -0.05, 1.0 + j * 0.42), (0.34, 0.06, 0.06), 0)
                E.caja(bm, (xc - 0.97 + i * 0.4, -0.05, 1.0 + j * 0.42), (0.06, 0.06, 0.36), 0)
    E.objeto("CAA_vidrios", bv, [vidrio], p, col)
    E.objeto("CAA_marcos", bm, [M["blanco"]], p, col)
    # bloque azul de la entrada: sobresale y sube por encima del pretil, letrero blanco, puerta de vidrio
    bm = bmesh.new()
    E.caja(bm, (0, -0.4, 0), (2 * xb, 1.0, H + 1.4), 0)
    E.objeto("CAA_bloque_azul", bm, [azul], p, col)
    bm = bmesh.new()
    E.caja(bm, (0, -0.93, 0.0), (3.2, 0.06, 2.6), 0)
    for x in (-1.6, -0.55, 0.55, 1.6):
        E.caja(bm, (x, -0.96, 0.0), (0.07, 0.06, 2.65), 1)
    E.caja(bm, (0, -0.96, 2.6), (3.3, 0.06, 0.08), 1)
    for z0 in (4.6, 6.0):
        E.caja(bm, (0, -0.93, z0), (5.6, 0.06, 1.0), 0)
    E.objeto("CAA_entrada", bm, [vidrio, M["blanco"]], p, col)
    E.texto("CENTRO DE ADIESTRAMIENTO", 0.34, M["blanco"], p, col, (0, -0.95, 3.55), (math.pi / 2, 0, 0), extr=0.03)
    E.texto("AERONÁUTICO", 0.34, M["blanco"], p, col, (0, -0.95, 3.05), (math.pi / 2, 0, 0), extr=0.03)
    bm = bmesh.new()                                       # alerito sobre la puerta
    E.caja(bm, (0, -1.5, 2.75), (4.0, 1.2, 0.12), 0)
    E.objeto("CAA_alero_puerta", bm, [M["blanco"]], p, col)
    # azotea: tres astas sobre el bloque azul, reflectores en el pretil y aires
    bm, bl = bmesh.new(), bmesh.new()
    for x in (-2.5, 0.0, 2.5):
        E.cilindro(bm, (x, 0.2, H + 1.4), 0.04, 0.025, 4.0, 0, 8)
    for x in (-W / 2 + 0.6, -6.0, 6.0, W / 2 - 0.6):
        E.caja(bm, (x, 0.0, H + 0.7), (0.08, 0.08, 0.6), 0)
        E.caja(bl, (x, -0.15, H + 1.25), (0.45, 0.25, 0.32), 0)
    for x, y in ((-10.0, D * 0.5), (9.0, D * 0.6), (13.0, D * 0.4)):
        E.caja(bm, (x, y, H), (1.1, 0.8, 0.8), 0)
    E.objeto("CAA_azotea", bm, [E.material("Galvanizado", (0.55, 0.56, 0.57), 0.35, 0.8)], p, col)
    E.objeto("CAA_reflectores", bl, [M["luz"]], p, col)
    # frente: jardinera con setos, acera con brocal amarillo, estacionamiento con rayas blancas
    bm, bh = bmesh.new(), bmesh.new()
    for s in (-1, 1):
        x0, x1 = sorted((s * (xb + 1.0), s * (W / 2 - 0.5)))
        E.caja(bm, (0.5 * (x0 + x1), -1.4, 0), (x1 - x0, 1.6, 0.3), 0)
        x = x0 + 1.2
        while x < x1 - 0.8:
            E.hojas(bh, Vector((x, -1.4, 0.75)), 0.5, 80, rnd, 0, 0.12)
            x += 3.2 + rnd.random()
    E.objeto("CAA_jardinera", bm, [E.material("Tierra_jardin_CAA", (0.18, 0.12, 0.08), 0.9)], p, col)
    E.objeto("CAA_matas", bh, [M["arbusto"]], p, col)
    palma = bpy.data.meshes.get("Palma_real")
    if palma:
        for x in (-12.0, -7.0, 6.5, 11.5, -16.0, 15.5):
            ob = bpy.data.objects.new("Palma_CAA", palma)
            ob.location = (x + rnd.uniform(-0.6, 0.6), -1.5, 0)
            ob.rotation_euler = (0, 0, rnd.uniform(0, 6.3))
            ob.scale = (0.45, 0.45, 0.38)
            col.objects.link(ob)
            ob.parent = p
    bm = bmesh.new()
    E.caja(bm, (0, -3.4, 0), (W + 6.0, 2.4, 0.15), 0)
    E.objeto("CAA_acera", bm, [M["acera"]], p, col)
    bm = bmesh.new()
    E.caja(bm, (0, -4.65, 0), (W + 6.0, 0.25, 0.2), 0)
    E.caja(bm, (0, -34.7, 0), (W + 30.0, 0.25, 0.2), 0)
    E.objeto("CAA_brocal", bm, [M["amarillo"]], p, col)
    bm = bmesh.new()
    E.caja(bm, (0, -19.6, 0), (W + 30.0, 29.8, 0.1), 0)
    E.objeto("CAA_estacionamiento", bm, [M["asfalto"]], p, col)
    bm = bmesh.new()
    x = -W / 2 - 12.0
    while x <= W / 2 + 12.0:
        E.caja(bm, (x, -31.0, 0.1), (0.12, 5.0, 0.01), 0)
        x += 2.7
    E.caja(bm, (0, -33.4, 0.1), (W + 26.0, 0.12, 0.01), 0)
    E.objeto("CAA_rayas", bm, [M["pintura"]], p, col)
    # letras «CAA» de bulto en el césped junto a la vía, sobre su base gris
    bm = bmesh.new()
    E.caja(bm, (-8.0, -38.5, 0), (4.6, 0.7, 0.3), 0)
    E.objeto("CAA_letras_base", bm, [E.material("Gris_base_letras", (0.22, 0.23, 0.25), 0.5)], p, col)
    t = E.texto("CAA", 1.6, M["blanco"], p, col, (-8.0, -38.5, 0.3), (math.pi / 2, 0, 0), extr=0.22)
    t.rotation_euler = (math.pi / 2, 0, math.radians(-12))
    E.camara("Cam_CAA", p, col, (6.0, -46.0, 1.6), (0.0, 0.0, 4.0), 22)


def main():
    col = limpiar()
    M = Hg.materiales(E.mats())
    ub = Hg.UBS["CAA"]
    z = E.aplanar(ub["este"], ub["norte"], "cota_caa", 62.0, 95.0)
    caa(M, col, z)
    ub = Hg.UBS["Tanque de agua"]
    # mismo nivel que el comedor (su césped de 85 m llega hasta aquí; con cota propia quedaba flotando)
    z = E.aplanar(ub["este"], ub["norte"], "cota_tanque", 14.0, 24.0, z0=bpy.context.scene.get("cota_comedor"))
    tanque(M, col, z)
    pasto = E.pbr("Pasto_vecinos", "pasto", 2.5, (0.45, 0.95, 0.30), fade=(40.0, 60.0),
                  variacion=(0.05, (0.85, 0.75, 0.45)))
    for nombre, r in (("CAA", 75.0), ("Tanque de agua", 22.0)):
        u = Hg.UBS[nombre]
        bm = bmesh.new()
        bmesh.ops.create_circle(bm, cap_ends=True, radius=r, segments=64)
        ob = E.objeto("Pasto_" + nombre.split()[0].lower(), bm, [pasto], None, col)
        ob.location = (u["este"], u["norte"], bpy.context.scene["cota_" + ("caa" if nombre == "CAA" else "tanque")]
                       + 0.01)
    bpy.ops.wm.save_mainfile()
    print("vecinos del comedor listos")


if __name__ == "__main__":
    main()
