"""Lo que está al lado del CAA (fotos que ella mandó el 2026-11-05, desde la vía que pasa por el norte):

- el edificio largo de dos pisos: paneles blancos entre pilastras gris verdoso, franja de piso del mismo color con la
  celosía de bloques debajo, losa plana con borde manchado, el hueco abierto de la escalera en la punta este (dos
  pisos, con balcón) y, en la punta oeste, ventanas de persiana viejas en vez de celosía y una franja amarilla en el
  testero; el poste de concreto con los transformadores delante y una palma real en la punta este;
- la «LAVANDERÍA SUCRE» detrás: nave blanca con techo rojo a dos aguas y chimeneas, el cuerpo bajo del frente con
  las letras pintadas, el porche de hierro, tanques azules y matas de plátano, y el ala gris al sur (huella OSM);
- el galpón de techo rojo a dos aguas más al oeste, con su faldón bajo, franja de ventanas y zócalo gris verdoso.
Sin adornos de Navidad. Se corre después de comedor_vecinos.py:

    blender --background BaseSucre.blend --python caa_vecinos.py
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import entrada as E  # noqa: E402
import hangares as Hg  # noqa: E402
import dida  # noqa: E402

rnd = E.random.Random(4321)


def limpiar():
    col = bpy.data.collections.get("CAA_vecinos")
    if col:
        for ob in list(col.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.collections.remove(col)
    col = bpy.data.collections.new("CAA_vecinos")
    bpy.context.scene.collection.children.link(col)
    return col


def celosia(bm, x0, x1, y, z0, z1, mi_fondo, mi_bloque, paso=0.2):
    """Celosía de bloques calados: fondo oscuro y retícula clara."""
    E.caja(bm, (0.5 * (x0 + x1), y + 0.04, z0), (x1 - x0, 0.04, z1 - z0), mi_fondo)
    n = max(1, int((x1 - x0) / paso))
    for k in range(n + 1):
        E.caja(bm, (x0 + k * (x1 - x0) / n, y, z0), (0.05, 0.1, z1 - z0), mi_bloque)
    for zz in (z0, 0.5 * (z0 + z1), z1 - 0.05):
        E.caja(bm, (0.5 * (x0 + x1), y, zz), (x1 - x0, 0.1, 0.05), mi_bloque)


def poste_transformador(bm, x, y, mi_poste, mi_metal):
    E.cilindro(bm, (x, y, 0), 0.17, 0.11, 11.0, mi_poste, 12)
    E.caja(bm, (x, y, 10.2), (2.4, 0.12, 0.12), mi_metal)
    E.caja(bm, (x, y, 9.2), (1.6, 0.1, 0.1), mi_metal)
    for s in (-1, 1):                                        # dos transformadores colgados
        E.cilindro(bm, (x + s * 0.32, y - 0.28, 6.6), 0.26, 0.26, 0.95, mi_metal, 16)
        E.cilindro(bm, (x + s * 0.32, y - 0.28, 7.55), 0.27, 0.2, 0.12, mi_metal, 16)
    for s in (-1.1, 0.0, 1.1):                               # aisladores
        E.cilindro(bm, (x + s, y, 10.32), 0.05, 0.04, 0.22, mi_metal, 8)


def edificio_largo(M, col, z):
    ub = Hg.UBS["Edificio largo CAA"]
    p = Hg.origen("Largo_origen", ub, col, z)
    W, D = ub["ancho"], ub["fondo"]
    H1, H = 3.5, 7.3
    blanco = E.pbr("Friso_crema_largo", "friso", 3.0, pintura=(0.80, 0.78, 0.70))
    gris_v = E.pbr("Gris_verdoso", "friso", 3.0, pintura=(0.26, 0.29, 0.24))
    losa = E.pbr("Losa_manchada", "concreto_gastado", 3.0, pintura=(0.30, 0.31, 0.30))
    oscuro = E.material("Interior_oscuro", (0.03, 0.03, 0.03), 0.9)
    bay = W / 16                                                  # 16 tramos entre pilastras
    xo0, xo1 = W / 2 - 2 * bay, W / 2                            # hueco de la escalera (punta este = +X)
    bm = bmesh.new()
    E.caja(bm, (0.5 * (-W / 2 + xo0), D / 2, 0), (xo0 + W / 2, D, H), 0)
    E.caja(bm, (0.5 * (xo0 + xo1), D / 2 + 2.0, 0), (xo1 - xo0, D - 4.0, H), 0)      # fondo del hueco
    E.objeto("Largo_volumen", bm, [blanco], p, col)
    bm = bmesh.new()                                            # interior oscuro y balcón del hueco
    E.caja(bm, (0.5 * (xo0 + xo1), 1.98, 0), (xo1 - xo0, 0.04, H), 0)
    E.objeto("Largo_hueco", bm, [oscuro], p, col)
    bm = bmesh.new()
    E.caja(bm, (0.5 * (xo0 + xo1), 1.0, H1 - 0.15), (xo1 - xo0, 2.1, 0.25), 0)
    E.caja(bm, (0.5 * (xo0 + xo1), 0.08, H1 + 0.1), (xo1 - xo0, 0.16, 1.0), 0)   # antepecho
    E.caja(bm, (xo1 - 0.15, D / 2, 0), (0.3, D, H), 0)                           # muro del testero
    E.objeto("Largo_balcon", bm, [blanco], p, col)
    # losa del techo con alero corto y borde manchado
    bm = bmesh.new()
    E.caja(bm, (0, D / 2, H), (W + 1.4, D + 1.4, 0.32), 0)
    E.objeto("Largo_losa", bm, [losa], p, col)
    # pilastras, franja de piso y celosía en las dos caras largas
    bm = bmesh.new()
    for y, sg in ((0.0, -1), (D, 1)):
        for k in range(17):
            x = -W / 2 + k * bay
            E.caja(bm, (x, y + sg * 0.08, 0), (0.34, 0.2, H), 0)
        E.caja(bm, (0, y + sg * 0.06, H1), (W, 0.14, 0.28), 0)
    for x in (-W / 2, W / 2):                                   # esquineros del testero
        for y in (0.1, D - 0.1):
            E.caja(bm, (x, y, 0), (0.36, 0.36, H), 0)
    E.objeto("Largo_pilastras", bm, [gris_v], p, col)
    bm = bmesh.new()
    for y, sg in ((0.0, -1), (D, 1)):
        for k in range(16):
            x0, x1 = -W / 2 + k * bay + 0.17, -W / 2 + (k + 1) * bay - 0.17
            if sg < 0 and x1 > xo0:
                continue
            if sg < 0 and k < 4:                               # punta oeste: persianas viejas
                continue
            celosia(bm, x0, x1, y + sg * 0.06, H1 - 0.62, H1 - 0.02, 0, 1)
    E.objeto("Largo_celosia", bm, [oscuro, E.material("Bloque_celosia", (0.62, 0.62, 0.58), 0.85)], p, col)
    bm = bmesh.new()                                            # ventanas de persiana de vidrio, viejas
    for k in range(4):
        x0, x1 = -W / 2 + k * bay + 0.2, -W / 2 + (k + 1) * bay - 0.2
        E.caja(bm, (0.5 * (x0 + x1), -0.03, H1 - 1.2), (x1 - x0, 0.04, 1.15), 0)
        for j in range(7):
            E.caja(bm, (0.5 * (x0 + x1), -0.08, H1 - 1.15 + j * 0.16), (x1 - x0, 0.1, 0.04), 1, (0.5, 0, 0))
    E.objeto("Largo_persianas", bm, [oscuro, E.material("Persiana_vieja", (0.36, 0.37, 0.36), 0.5, 0.3)], p, col)
    bm = bmesh.new()                                            # franja amarilla del testero oeste y caja eléctrica
    E.caja(bm, (-W / 2 - 0.05, D / 2, H1 - 0.1), (0.08, D, 0.55), 0)
    E.objeto("Largo_franja_amarilla", bm, [E.material("Amarillo_verdoso", (0.62, 0.58, 0.22), 0.6)], p, col)
    bm = bmesh.new()
    E.caja(bm, (-W / 2 + 3.6, -0.12, 1.2), (0.55, 0.2, 0.7), 0)
    E.objeto("Largo_caja_electrica", bm, [E.material("Caja_roja_oxido", (0.30, 0.08, 0.05), 0.6, 0.3)], p, col)
    # poste con transformadores delante de la punta oeste, palma real en la punta este
    bm = bmesh.new()
    poste_transformador(bm, -W / 2 + 6.5, -5.5, 0, 1)
    E.objeto("Largo_poste", bm, [E.material("Poste_concreto", (0.55, 0.54, 0.51), 0.85),
                                  E.material("Galvanizado", (0.55, 0.56, 0.57), 0.35, 0.8)], p, col)
    palma = bpy.data.meshes.get("Palma_real")
    if palma:
        ob = bpy.data.objects.new("Palma_largo", palma)
        ob.location = (W / 2 - 3.0, -6.0, 0)
        ob.scale = (1.0, 1.0, 0.95)
        col.objects.link(ob)
        ob.parent = p
    bm = bmesh.new()                                            # acera al pie
    E.caja(bm, (0, -0.8, 0), (W + 1.0, 1.6, 0.12), 0)
    E.objeto("Largo_acera", bm, [M["acera"]], p, col)
    E.camara("Cam_Largo_CAA", p, col, (W / 2 + 14.0, -34.0, 1.6), (-6.0, 0.0, 3.0), 22)


def lavanderia(M, col, z):
    ub = Hg.UBS["Lavanderia"]
    p = Hg.origen("Lavanderia_origen", ub, col, z)
    W, D = ub["ancho"], ub["fondo"]
    H, Hc = 3.6, 5.6
    blanco = E.pbr("Friso_blanco_lav", "friso", 3.0, pintura=(0.82, 0.83, 0.82))
    rojo = E.pbr("Lamina_roja_lav", "lamina_gastada", 2.0, metal=0.15, pintura=(0.45, 0.07, 0.04))
    oscuro = E.material("Interior_oscuro", (0.03, 0.03, 0.03), 0.9)
    bm = bmesh.new()
    E.caja(bm, (0, D / 2, 0), (W, D, H), 0)
    for x in (-W / 2, W / 2):
        bm.faces.new([bm.verts.new(v) for v in ((x, 0, H), (x, D, H), (x, D / 2, Hc))])
    E.objeto("Lavanderia_volumen", bm, [blanco], p, col)
    bm = bmesh.new()
    for y0, y1, z0, z1 in ((-0.8, D / 2, H - 0.25, Hc), (D / 2, D + 0.8, Hc, H - 0.25)):
        bm.faces.new([bm.verts.new(v) for v in ((-W / 2 - 0.6, y0, z0), (W / 2 + 0.6, y0, z0),
                                                (W / 2 + 0.6, y1, z1), (-W / 2 - 0.6, y1, z1))])
    E.objeto("Lavanderia_techo", bm, [rojo], p, col)
    bm = bmesh.new()                                            # franja alta de celosía y ventanas
    for y, sg in ((0.0, -1), (D, 1)):
        celosia(bm, -W / 2 + 1.0, W / 2 - 1.0, y + sg * 0.04, H - 1.1, H - 0.35, 0, 1, 0.22)
    E.objeto("Lavanderia_celosia", bm, [oscuro, E.material("Bloque_celosia", (0.62, 0.62, 0.58), 0.85)], p, col)
    bm = bmesh.new()                                            # chimeneas y extractores de las calderas
    for x, y, h in ((-8.0, D * 0.3, 2.4), (6.0, D * 0.35, 1.8), (16.0, D * 0.6, 2.0)):
        E.cilindro(bm, (x, y, Hc - 0.8), 0.18, 0.18, h + 0.8, 0, 12)
        E.cilindro(bm, (x, y, Hc + h), 0.32, 0.05, 0.25, 0, 12)
    E.objeto("Lavanderia_chimeneas", bm, [E.material("Galvanizado", (0.55, 0.56, 0.57), 0.35, 0.8)], p, col)
    # cuerpo bajo del frente con las letras y el porche de hierro a su derecha
    xa0, xa1, ya = -W / 2 + 14.0, -W / 2 + 32.0, -5.5
    bm = bmesh.new()
    E.caja(bm, (0.5 * (xa0 + xa1), 0.5 * ya, 0), (xa1 - xa0, -ya, 2.9), 0)
    E.objeto("Lavanderia_frente", bm, [blanco], p, col)
    bm = bmesh.new()
    bm.faces.new([bm.verts.new(v) for v in ((xa0 - 0.4, ya - 0.6, 3.0), (xa1 + 0.4, ya - 0.6, 3.0),
                                            (xa1 + 0.4, 0.2, 3.7), (xa0 - 0.4, 0.2, 3.7))])
    E.objeto("Lavanderia_frente_techo", bm, [rojo], p, col)
    negro = E.material("Letras_negras_pintadas", (0.02, 0.02, 0.02), 0.6)
    E.texto("LAVANDERÍA", 0.5, negro, p, col, (0.5 * (xa0 + xa1) - 1.2, ya - 0.02, 1.95), (math.pi / 2, 0, 0))
    E.texto("SUCRE", 0.42, negro, p, col, (0.5 * (xa0 + xa1) + 1.6, ya - 0.02, 1.35), (math.pi / 2, 0, 0))
    bm = bmesh.new()                                            # porche: postes, vigas y celosía de hierro
    xp0, xp1 = xa1 + 0.5, xa1 + 5.5
    for x in (xp0, xp1):
        for y in (ya, -0.2):
            E.caja(bm, (x, y, 0), (0.12, 0.12, 2.8), 0)
    for y in (ya, -0.2):
        E.caja(bm, (0.5 * (xp0 + xp1), y, 2.7), (xp1 - xp0 + 0.2, 0.1, 0.14), 0)
    for k in range(9):
        E.caja(bm, (xp0 + k * (xp1 - xp0) / 8, 0.5 * (ya - 0.2), 2.84), (0.05, -ya, 0.05), 0)
    for k in range(6):
        E.caja(bm, (xp0 + 0.2 + k * 0.8, ya, 1.0), (0.04, 0.04, 1.7), 0)
    E.objeto("Lavanderia_porche", bm, [E.material("Hierro_negro", (0.04, 0.04, 0.045), 0.5, 0.6)], p, col)
    bm = bmesh.new()
    bm.faces.new([bm.verts.new(v) for v in ((xp0 - 0.1, ya - 0.3, 2.95), (xp1 + 0.1, ya - 0.3, 2.95),
                                            (xp1 + 0.1, 0.0, 3.3), (xp0 - 0.1, 0.0, 3.3))])
    E.objeto("Lavanderia_porche_techo", bm, [rojo], p, col)
    bm = bmesh.new()                                            # puerta y ventanas del frente
    E.caja(bm, (xa1 - 2.0, ya - 0.03, 0), (1.0, 0.05, 2.1), 0)
    for x in (xa0 + 2.0, xa0 + 4.5):
        E.caja(bm, (x, ya - 0.03, 1.2), (1.2, 0.05, 1.0), 0)
    E.objeto("Lavanderia_vanos", bm, [oscuro], p, col)
    bm = bmesh.new()                                            # tanques azules junto al porche
    for x in (xp0 + 1.2, xp0 + 2.3):
        E.cilindro(bm, (x, ya - 1.2, 0), 0.38, 0.38, 1.1, 0, 18)
    E.objeto("Lavanderia_tanques", bm, [E.material("Tanque_azul", (0.03, 0.20, 0.60), 0.4)], p, col)
    bm = bmesh.new()                                            # matas de plátano delante del cuerpo bajo
    for k in range(6):
        dida.mata_platano(bm, Vector((xa0 - 6.0 + k * 1.6 + rnd.uniform(-0.4, 0.4), ya - 2.0 - rnd.uniform(0, 1.5),
                                      0)), rnd.uniform(1.8, 2.8), rnd)
    E.objeto("Lavanderia_platanos", bm, [E.material("Tallo_platano", (0.30, 0.33, 0.12), 0.6),
                                          E.material("Hoja_platano", (0.12, 0.32, 0.05), 0.5)], p, col)
    # ala gris de techo plano al sur (huella OSM)
    pts = [Vector(q) for q in ((971.5, 241.7), (975.3, 252.4), (1025.8, 234.0), (1021.9, 223.4))]
    bm = bmesh.new()
    base = bm.faces.new([bm.verts.new((q.x, q.y, z - 0.2)) for q in pts])
    base.normal_update()
    if base.normal.z < 0:
        base.normal_flip()
    r = bmesh.ops.extrude_face_region(bm, geom=[base])
    bmesh.ops.translate(bm, vec=Vector((0, 0, 3.6)), verts=[g for g in r["geom"] if isinstance(g, bmesh.types.BMVert)])
    E.objeto("Lavanderia_ala", bm, [blanco], None, col)
    bm = bmesh.new()
    c = sum(pts, Vector((0, 0))) / 4
    f = bm.faces.new([bm.verts.new((c.x + (q.x - c.x) * 1.02, c.y + (q.y - c.y) * 1.06, z + 3.4)) for q in pts])
    E.objeto("Lavanderia_ala_losa", bm, [bpy.data.materials["Losa_manchada"]], None, col)


def galpon_rojo(M, col, z):
    ub = Hg.UBS["Galpon rojo CAA"]
    p = Hg.origen("Galpon_rojo_origen", ub, col, z)
    W, D = ub["ancho"], ub["fondo"]
    H, Hf, Hc = 3.1, 4.0, 8.2
    crema = E.pbr("Friso_crema_galpon", "friso", 3.0, pintura=(0.80, 0.77, 0.62))
    gris_v = bpy.data.materials["Gris_verdoso"]
    rojo = E.pbr("Lamina_roja_galpon", "lamina_gastada", 2.0, metal=0.15, pintura=(0.42, 0.05, 0.03))
    bm = bmesh.new()
    E.caja(bm, (0, D / 2, 0), (W, D, H), 0)
    m = 2.6                                                     # el cuerpo alto queda retirado 2,6 m del muro
    E.caja(bm, (0, D / 2, H), (W - 2 * m, D - 2 * m, Hf - H), 0)
    for x in (-W / 2 + m, W / 2 - m):
        bm.faces.new([bm.verts.new(v) for v in ((x, m, Hf), (x, D - m, Hf), (x, D / 2, Hc))])
    E.objeto("Galpon_rojo_volumen", bm, [crema], p, col)
    bm = bmesh.new()                                            # faldón bajo alrededor y techo alto a dos aguas
    for y0, y1, za, zb in ((-0.9, m, H - 0.2, H + 0.75), (D - m, D + 0.9, H + 0.75, H - 0.2)):
        bm.faces.new([bm.verts.new(v) for v in ((-W / 2 - 0.9, y0, za), (W / 2 + 0.9, y0, za),
                                                (W / 2 + 0.9, y1, zb), (-W / 2 - 0.9, y1, zb))])
    for y0, y1, za, zb in ((m - 0.8, D / 2, Hf - 0.25, Hc), (D / 2, D - m + 0.8, Hc, Hf - 0.25)):
        bm.faces.new([bm.verts.new(v) for v in ((-W / 2 + m - 0.6, y0, za), (W / 2 - m + 0.6, y0, za),
                                                (W / 2 - m + 0.6, y1, zb), (-W / 2 + m - 0.6, y1, zb))])
    E.objeto("Galpon_rojo_techo", bm, [rojo], p, col)
    bm, bv = bmesh.new(), bmesh.new()                           # zócalo gris verdoso y franja de ventanas
    for y, sg in ((0.0, -1), (D, 1)):
        E.caja(bm, (0, y + sg * 0.03, 0), (W + 0.06, 0.06, 0.9), 0)
        E.caja(bv, (0, y + sg * 0.04, 1.3), (W - 1.0, 0.04, 1.3), 0)
        for k in range(13):
            E.caja(bm, (-W / 2 + 0.5 + k * (W - 1.0) / 12, y + sg * 0.07, 1.3), (0.08, 0.06, 1.3), 1)
    E.objeto("Galpon_rojo_zocalo", bm, [gris_v, M["blanco"]], p, col)
    E.objeto("Galpon_rojo_ventanas", bv, [M["vidrio"]], p, col)


def main():
    col = limpiar()
    M = Hg.materiales(E.mats())
    z = E.aplanar(Hg.UBS["Edificio largo CAA"]["este"], Hg.UBS["Edificio largo CAA"]["norte"], "cota_largo_caa",
                  40.0, 60.0, z0=bpy.context.scene.get("cota_caa"))
    edificio_largo(M, col, z)
    u = Hg.UBS["Lavanderia"]
    lavanderia(M, col, E.aplanar(u["este"], u["norte"], "cota_lavanderia", 34.0, 48.0, z0=z))
    u = Hg.UBS["Galpon rojo CAA"]
    galpon_rojo(M, col, E.aplanar(u["este"], u["norte"], "cota_galpon_rojo", 20.0, 32.0, z0=z))
    # césped alrededor de los tres (sin él se veía el satélite lavado, casi blanco); los «Pasto*» reciben pasto 3D
    pasto = E.pbr("Pasto_vecinos_caa", "pasto", 2.5, (0.45, 0.95, 0.30), fade=(55.0, 80.0),
                  variacion=(0.05, (0.85, 0.75, 0.45)))
    for nombre in ("Edificio largo CAA", "Lavanderia", "Galpon rojo CAA"):
        u = Hg.UBS[nombre]
        bm = bmesh.new()
        bmesh.ops.create_circle(bm, cap_ends=True, radius=80.0 if nombre != "Galpon rojo CAA" else 45.0, segments=80)
        ob = E.objeto("Pasto_" + nombre.split()[0].lower() + "_caa", bm, [pasto], None, col)
        ob.location = (u["este"], u["norte"], z + 0.01)
    bpy.ops.wm.save_mainfile()
    print("vecinos del CAA listos")


if __name__ == "__main__":
    main()
