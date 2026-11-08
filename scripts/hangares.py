"""CEA (hangar de techo curvo verde) y el hangar gris que queda frente a la DIDA.

Fotos: referencias/CEA ENTRADA .jpg, CREA ENTRADAA.jpg, HANGAR CEA.jpg, CEA LETRAS.jpg, CEA CASI HANGAR DIDA.jpg y
los cuadros del video (referencias/video_cuadros). Medidas y ubicación: datos/ubicaciones.json.
Se corre después de dida.py (usa la misma cota del terreno) y guarda el .blend:

    blender --background BaseSucre.blend --python hangares.py

Cada edificio cuelga de su vacío; en su marco la fachada que da a la calle mira hacia -Y, X corre a lo ancho y Y
hacia el fondo, con Z = 0 en el suelo (igual que la DIDA).
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

UBS = json.load(open(os.path.join(os.path.dirname(E.TEXTURAS), "datos", "ubicaciones.json"),
                     encoding="utf-8"))["edificios"]
rnd = E.random.Random(19)


def limpiar():
    col = bpy.data.collections.get("Hangares")
    if col:
        for ob in list(col.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.collections.remove(col)
    col = bpy.data.collections.new("Hangares")
    bpy.context.scene.collection.children.link(col)
    return col


def origen(nombre, ub, col, z):
    """Vacío en el centro de la fachada: centro del techo medido + medio fondo hacia la calle."""
    r = math.radians(ub["rumbo_fachada"])
    d = Vector((math.sin(r), math.cos(r)))
    p = Vector((ub["este"], ub["norte"])) + d * (ub["fondo"] / 2)
    ob = bpy.data.objects.new(nombre, None)
    ob.empty_display_type = "ARROWS"
    ob.empty_display_size = 6
    ob.location = (p.x, p.y, z)
    ob.rotation_euler = (0, 0, math.radians(180.0 - ub["rumbo_fachada"]))
    col.objects.link(ob)
    return ob


def materiales(M):
    M["lamina_gris"] = E.pbr("Lamina_gris", "lamina", 2.0, metal=0.3, pintura=(0.60, 0.62, 0.64))
    M["lamina_techo"] = E.pbr("Lamina_techo_gris", "lamina", 2.0, metal=0.3, pintura=(0.70, 0.72, 0.74))
    M["lamina_verde"] = E.pbr("Lamina_verde", "lamina", 2.0, metal=0.15, pintura=(0.52, 0.70, 0.46))
    M["lamina_azul"] = E.pbr("Lamina_azul_gris", "lamina", 2.0, metal=0.2, pintura=(0.36, 0.43, 0.50))
    M["amarillo_pared"] = E.pbr("Pared_amarilla", "pared", 3.0, pintura=(0.86, 0.64, 0.25))
    M["gris_zocalo"] = E.pbr("Pared_zocalo_gris", "pared", 3.0, pintura=(0.42, 0.43, 0.46))
    M["lama"] = E.material("Lamas_rejilla", (0.78, 0.72, 0.55), 0.6)
    M["rojo_cea"] = E.material("Rojo_CEA", (0.45, 0.03, 0.05), 0.4)
    M["rojo_portal"] = E.material("Rojo_portal", (0.70, 0.06, 0.06), 0.5)
    M["oscuro"] = E.material("Interior_oscuro", (0.015, 0.015, 0.015), 0.9)
    M["reja"] = E.material("Reja_blanca", (0.85, 0.85, 0.85), 0.5, 0.3)
    M["baldosa"] = E.material("Baldosa_terracota", (0.42, 0.17, 0.10), 0.7)
    M["negro"] = E.material("Helice_negra", (0.02, 0.02, 0.02), 0.35, 0.5)
    M["escudo_rojo"] = E.material("Escudo_rojo", (0.55, 0.05, 0.05), 0.4)
    M["escudo_verde"] = E.material("Escudo_verde", (0.05, 0.30, 0.12), 0.4)
    M["aire"] = E.material("Aire_acondicionado", (0.80, 0.80, 0.78), 0.5)
    M["concreto_patio"] = E.pbr("Concreto_patio", "acera", 4.0, (0.9, 0.9, 0.88))
    return M


# ----------------------------------------------------------------------------------- detalles reutilizables
def banda_rejillas(bm, x0, x1, y, z0, z1, mi_lama, mi_pilar, paneles, sale=-1):
    """Franja de rejillas de ventilación (lamas inclinadas) en paneles separados por pilastras."""
    ancho = (x1 - x0) / paneles
    n = int((z1 - z0) / 0.17)
    for i in range(paneles):
        xc = x0 + (i + 0.5) * ancho
        for k in range(n):
            E.caja(bm, (xc, y + sale * 0.06, z0 + 0.05 + k * 0.17), (ancho - 0.45, 0.10, 0.06), mi_lama,
                   (math.radians(-28 * sale), 0, 0))
        E.caja(bm, (x0 + i * ancho, y + sale * 0.05, z0 - 0.15), (0.35, 0.12, z1 - z0 + 0.3), mi_pilar)
    E.caja(bm, (x1, y + sale * 0.05, z0 - 0.15), (0.35, 0.12, z1 - z0 + 0.3), mi_pilar)


def ventana_reja(bm, x, y, z, w, h, mi_vidrio, mi_reja, sale=-1):
    E.caja(bm, (x, y + sale * 0.03, z), (w, 0.06, h), mi_vidrio)
    for k in range(7):
        E.caja(bm, (x - w / 2 + (k + 0.5) * w / 7, y + sale * 0.08, z), (0.04, 0.04, h), mi_reja)
    for zz in (z, z + h / 2, z + h - 0.05):
        E.caja(bm, (x, y + sale * 0.08, zz), (w, 0.04, 0.05), mi_reja)


def pared_x(bm, x0, x1, y, mats, sale=-1):
    """Capas de pintura de las paredes del CEA sobre una cara de normal ±Y: zócalo gris y dos filetes."""
    zoc, fil = mats
    E.caja(bm, (0.5 * (x0 + x1), y + sale * 0.03, 0), (x1 - x0 + 0.06, 0.06, 1.25), zoc)
    for zz in (1.45, 1.75):
        E.caja(bm, (0.5 * (x0 + x1), y + sale * 0.025, zz), (x1 - x0 + 0.04, 0.05, 0.12), fil)


def arco(semiluz, base, flecha, n=28):
    """Perfil de bóveda: puntos (x, z) de un arco circular que arranca en (±semiluz, base)."""
    R = (semiluz ** 2 + flecha ** 2) / (2 * flecha)
    zc = base + flecha - R
    tm = math.asin(semiluz / R)
    return [(R * math.sin(t), zc + R * math.cos(t)) for t in (-tm + 2 * tm * k / n for k in range(n + 1))]


# ----------------------------------------------------------------------------------- CEA
def cea(M, col, z):
    ub = UBS["CEA"]
    p = origen("CEA_origen", ub, col, z)
    S, L = ub["ancho"], ub["fondo"]
    hw, flecha = 4.6, 8.8
    perfil = arco(S / 2, hw, flecha)

    # bóveda de lámina verde, con un poco de alero en los dos frentes
    bm = bmesh.new()
    anillos = []
    for y in (-0.6, L + 0.6):
        anillos.append([bm.verts.new((x * 1.015, y, zz + 0.05)) for x, zz in perfil])
    for k in range(len(perfil) - 1):
        bm.faces.new((anillos[0][k], anillos[0][k + 1], anillos[1][k + 1], anillos[1][k]))
    E.objeto("CEA_boveda", bm, [M["lamina_verde"]], p, col)

    # muros: amarillo hasta el arranque del arco; tímpanos de lámina gris en los dos frentes
    bm = bmesh.new()
    E.caja(bm, (0, L / 2, 0), (S, L, hw), 0)
    for y in (0.0, L):
        vs = [bm.verts.new((x, y, zz)) for x, zz in perfil]
        f = bm.faces.new(vs)
        f.material_index = 1
    E.objeto("CEA_muros", bm, [M["amarillo_pared"], M["lamina_gris"]], p, col)

    # frente a la calle: zócalo y filetes, rejillas, ventanas con reja y portal rojo
    bm = bmesh.new()
    pared_x(bm, -S / 2, S / 2, 0.0, (0, 0))
    banda_rejillas(bm, -S / 2, S / 2, 0.0, 3.15, 4.45, 1, 2, 5)
    for x in (2.2, 8.6):
        ventana_reja(bm, x, 0.0, 1.95, 1.9, 1.05, 3, 4)
    ventana_reja(bm, -7.5, 0.0, 1.95, 1.4, 1.0, 3, 4)
    E.caja(bm, (-4.0, -0.03, 0.12), (2.3, 0.06, 2.7), 3)                    # puerta (interior oscuro)
    for dx in (-1.45, 1.45):
        E.caja(bm, (-4.0 + dx, -0.35, 0.12), (0.45, 0.7, 3.25), 5)          # portal rojo
    E.caja(bm, (-4.0, -0.35, 2.85), (3.35, 0.7, 0.55), 5)
    E.objeto("CEA_frente", bm, [M["gris_zocalo"], M["lama"], M["amarillo_pared"], M["oscuro"], M["reja"],
                                M["rojo_portal"]], p, col)

    # cara noreste: misma pintura y rejillas a lo largo
    bm = bmesh.new()
    E.caja(bm, (S / 2 + 0.03, L / 2, 0), (0.06, L + 0.06, 1.25), 0)
    for zz in (1.45, 1.75):
        E.caja(bm, (S / 2 + 0.025, L / 2, zz), (0.05, L + 0.04, 0.12), 0)
    paneles = 9
    for i in range(paneles):
        yc = (i + 0.5) * L / paneles
        for k in range(7):
            E.caja(bm, (S / 2 + 0.06, yc, 3.2 + k * 0.17), (0.10, L / paneles - 0.45, 0.06), 1,
                   (0, math.radians(28), 0))
        E.caja(bm, (S / 2 + 0.05, i * L / paneles, 3.0), (0.12, 0.35, 1.6), 2)
    for yc in (6.0, 18.0, 30.0, 42.0, 52.0):
        E.caja(bm, (S / 2 + 0.03, yc, 1.95), (0.06, 1.8, 1.05), 3)
    E.objeto("CEA_lado_noreste", bm, [M["gris_zocalo"], M["lama"], M["amarillo_pared"], M["oscuro"]], p, col)

    # letras CEA y escudos sobre el tímpano
    E.texto("CEA", 2.3, M["rojo_cea"], p, col, (-1.2, -0.3, 7.6), (math.pi / 2, 0, 0), extr=0.12).data.space_character = 1.15
    bm = bmesh.new()
    for x, zz, mi in ((-6.3, 7.6, 1), (-4.4, 7.6, 2), (2.2, 7.6, 3), (4.1, 7.6, 2), (-1.2, 10.0, 1)):
        E.cilindro(bm, (x, -0.06, zz), 0.62, 0.62, 0.08, 0, 32, (math.pi / 2, 0, 0))
        E.cilindro(bm, (x, -0.14, zz), 0.48, 0.48, 0.05, mi, 32, (math.pi / 2, 0, 0))
    E.caja(bm, (-8.1, -0.08, 7.0), (1.0, 0.08, 1.2), 0)                      # cuadro del escudo de la izquierda
    E.objeto("CEA_escudos", bm, [M["dorado"], M["azul_emblema"], M["escudo_rojo"], M["escudo_verde"]], p, col)

    # fondo hacia la plataforma: portones corredizos
    bm = bmesh.new()
    for i in range(6):
        E.caja(bm, (-S / 2 + (i + 0.5) * S / 6, L + 0.12, 0), (S / 6 - 0.15, 0.15, hw + 0.5), 0)
    E.objeto("CEA_portones", bm, [M["lamina_gris"]], p, col)

    # cobertizo largo al suroeste: paredes blancas, ventanas, aires y techo de lámina azul grisácea
    bm = bmesh.new()
    x_ext, x_int = -S / 2 - 6.0, -S / 2
    E.caja(bm, (x_ext + 0.15, L / 2, 0), (0.3, L - 6, 3.3), 0)
    for y in (3.0, L - 3.0):
        E.caja(bm, (0.5 * (x_ext + x_int), y, 0), (6.0, 0.3, 3.3), 0)
    E.caja(bm, (x_ext + 0.15, L / 2, 0), (0.36, L - 6, 0.9), 1)              # zócalo gris
    for k, yc in enumerate(range(6, int(L) - 4, 5)):
        if k % 3 == 2:
            E.caja(bm, (x_ext - 0.02, yc, 0.1), (0.08, 1.2, 2.3), 2)          # puerta
        else:
            E.caja(bm, (x_ext - 0.03, yc, 1.3), (0.08, 1.5, 1.0), 2)          # ventana
            if k % 2 == 0:
                E.caja(bm, (x_ext - 0.35, yc + 1.4, 1.9), (0.6, 0.8, 0.5), 3)  # aire acondicionado
    E.objeto("CEA_cobertizo", bm, [M["blanco"], M["gris_zocalo"], M["vidrio"], M["aire"]], p, col)
    bm = bmesh.new()
    a = [bm.verts.new(v) for v in ((x_int, 2.4, hw - 0.1), (x_int, L - 2.4, hw - 0.1),
                                   (x_ext - 0.7, L - 2.4, 3.35), (x_ext - 0.7, 2.4, 3.35))]
    bm.faces.new(a)
    E.objeto("CEA_cobertizo_techo", bm, [M["lamina_azul"]], p, col)

    # patio de baldosas, jardín con matas en materos y la hélice monumento
    bm = bmesh.new()
    E.caja(bm, (-4.0, -3.5, 0), (14.0, 7.0, 0.12), 0)
    E.objeto("CEA_patio", bm, [M["baldosa"]], p, col)
    bm, bh = bmesh.new(), bmesh.new()
    for x in (-11.0, -9.0, -7.0, -1.0, 1.0, 3.0, 5.0):
        E.cilindro(bm, (x, -1.4, 0.12), 0.24, 0.18, 0.4, 0, 12)
        E.hojas(bh, Vector((x, -1.4, 1.3)), 0.55, 90, rnd, 0, 0.22)
    E.objeto("CEA_materos", bm, [M["llanta"]], p, col)
    E.objeto("CEA_matas", bh, [M["arbusto"]], p, col)
    bh = bmesh.new()
    for x in (-10.0, -3.0, 4.5, 10.5):
        E.hojas(bh, Vector((x, -9.5, 0.5)), 1.1, 320, rnd, 0, 0.13)
    E.hojas(bh, Vector((7.0, -3.0, 0.6)), 1.0, 260, rnd, 0, 0.12)
    E.objeto("CEA_arbustos", bh, [M["arbusto"]], p, col)
    bm = bmesh.new()
    E.caja(bm, (3.2, -4.5, 0), (0.9, 0.9, 1.7), 0)                           # pedestal blanco
    E.objeto("CEA_pedestal", bm, [M["blanco"]], p, col)
    bm = bmesh.new()
    E.cilindro(bm, (3.2, -4.6, 2.35), 0.16, 0.10, 0.35, 0, 14, (math.pi / 2, 0, 0))
    for k in range(3):
        a = 2 * math.pi * k / 3
        E.caja(bm, (3.2 + 0.55 * math.sin(a), -4.75, 2.35 + 0.55 * math.cos(a) - 0.55), (0.22, 0.05, 1.1), 0,
               (0, a, 0))
    E.objeto("CEA_helice", bm, [M["negro"]], p, col)
    E.camara("Cam_CEA_Frente", p, col, (-2.0, -26.0, 1.7), (-1.5, 0.0, 5.0), 26)
    # vista del video: desde la calle, al suroeste, ve el costado con el cobertizo y el frente curvo
    E.camara("Cam_CEA_Costado", p, col, (-40.0, -34.0, 1.6), (-8.0, 14.0, 5.0), 30)
    return p


# ----------------------------------------------------------------------------------- hangar gris
def hangar_gris(M, col, z):
    ub = UBS["Hangar frente al DIDA"]
    p = origen("Hangar_gris_origen", ub, col, z)
    W, D = ub["ancho"], ub["fondo"]
    he, hc = 8.0, 14.5
    bm = bmesh.new()
    E.caja(bm, (0, D / 2, 0), (W, D, he), 0)
    for y in (0.0, D):
        bm.faces.new([bm.verts.new(v) for v in ((-W / 2, y, he), (W / 2, y, he), (0, y, hc))])
    E.objeto("Hangar_gris_muros", bm, [M["lamina_gris"]], p, col)
    # techo a dos aguas con alero
    bm = bmesh.new()
    for s in (-1, 1):
        bm.faces.new([bm.verts.new(v) for v in ((s * (W / 2 + 0.7), -0.5, he - 0.35), (0, -0.5, hc + 0.05),
                                                (0, D + 0.5, hc + 0.05), (s * (W / 2 + 0.7), D + 0.5, he - 0.35))])
    E.objeto("Hangar_gris_techo", bm, [M["lamina_techo"]], p, col)
    # portones corredizos hacia la calle, riel arriba y puerta de personal
    bm = bmesh.new()
    for i in range(6):
        E.caja(bm, (-W / 2 + 2.0 + (i + 0.5) * 7.0, -0.12, 0), (6.92, 0.14, 7.2), 0)
    E.caja(bm, (-W / 2 + 2.0 + 21.0, -0.22, 7.15), (43.0, 0.25, 0.35), 1)
    E.caja(bm, (W / 2 - 4.2, -0.03, 0), (1.3, 0.06, 2.3), 2)
    E.objeto("Hangar_gris_portones", bm, [M["lamina_gris"], M["poste"], M["oscuro"]], p, col)
    # anexo bajo a la derecha (noreste)
    bm = bmesh.new()
    E.caja(bm, (W / 2 + 4.5, 9.0, 0), (9.0, 18.0, 5.4), 0)
    E.caja(bm, (W / 2 + 4.5, 9.0, 5.4), (9.4, 18.4, 0.25), 1)
    E.caja(bm, (W / 2 + 6.0, -0.03, 0), (1.2, 0.06, 2.3), 2)
    E.objeto("Hangar_gris_anexo", bm, [M["lamina_gris"], M["poste"], M["oscuro"]], p, col)
    # patio de concreto con brocales amarillos y franja de césped con palmas
    bm = bmesh.new()
    E.caja(bm, (-6.0, -12.0, 0), (40.0, 24.0, 0.1), 0)
    E.objeto("Hangar_gris_patio", bm, [M["concreto_patio"]], p, col)
    bm = bmesh.new()
    for x0, x1 in ((-26.0, -18.0), (-4.0, 6.0), (14.5, 26.0)):
        E.caja(bm, (0.5 * (x0 + x1), -24.2, 0), (x1 - x0, 0.25, 0.16), 0)
    E.objeto("Hangar_gris_brocales", bm, [M["amarillo"]], p, col)
    palma = bpy.data.meshes.get("Palma_real")
    for x, y, s in ((20.0, -5.5, 0.42), (24.5, -4.0, 0.38)):
        if palma:
            E.instancia(palma, "Palma_navidad", p, col, x, y, s)
    # foto «dida detalles»: tres palmas reales altas juntas delante del hangar, a la izquierda vista desde la DIDA,
    # y dos más bajas a la izquierda del todo
    for x, y, s in ((-7.5, -10.5, 1.25), (-5.0, -11.5, 1.15), (-3.2, -10.0, 1.05), (-22.0, -11.0, 0.8),
                    (-25.0, -9.5, 0.75)):
        if palma:
            E.instancia(palma, "Palma_hangar_gris", p, col, x, y, s)
    bh = bmesh.new()
    E.hojas(bh, Vector((27.0, -6.5, 1.6)), 1.9, 700, rnd, 0, 0.3)            # palma de areca tupida
    E.hojas(bh, Vector((16.5, -5.0, 1.0)), 1.0, 300, rnd, 0, 0.16)
    E.objeto("Hangar_gris_matas", bh, [M["arbusto"]], p, col)
    E.camara("Cam_Hangar_Gris", p, col, (-6.0, -40.0, 1.5), (0.0, 0.0, 6.0), 24)
    return p


def hangar_curvo_blanco(M, col, z):
    """Hangar de bóveda blanca con el testero azul claro hacia la calle, al lado del hangar gris (foto «dida
    estacionamiento derecho y vista al cea»), con un muro bajo de bloques a lo largo del costado."""
    ub = UBS["Hangar curvo blanco"]
    p = origen("Hangar_blanco_origen", ub, col, z)
    S, L = ub["ancho"], ub["fondo"]
    hw, flecha = 3.0, S / 2 - 1.5
    perfil = arco(S / 2, hw, flecha, 36)
    blanca = E.pbr("Lamina_blanca", "lamina_gastada", 2.0, metal=0.25, pintura=(0.88, 0.89, 0.90))
    # (el color va en lineal: el 0,50/0,70/0,86 de antes salía casi blanco con el sol de mediodía)
    celeste = E.pbr("Lamina_celeste", "lamina_gastada", 1.6, metal=0.2, pintura=(0.16, 0.40, 0.66))
    bm = bmesh.new()
    an = [[bm.verts.new((x * 1.01, y, zz + 0.05)) for x, zz in perfil] for y in (-0.4, L + 0.4)]
    for k in range(len(perfil) - 1):
        bm.faces.new((an[0][k], an[0][k + 1], an[1][k + 1], an[1][k]))
    E.objeto("Hangar_blanco_boveda", bm, [blanca], p, col)
    bm = bmesh.new()
    E.caja(bm, (0, L / 2, 0), (S, L, hw), 0)
    for y in (0.0, L):
        f = bm.faces.new([bm.verts.new((x, y, zz)) for x, zz in perfil])
        f.material_index = 1
    E.objeto("Hangar_blanco_muros", bm, [blanca, celeste], p, col)
    bm = bmesh.new()                                     # testero: portón corredizo y puerta pequeña
    E.caja(bm, (2.0, -0.06, 0), (12.0, 0.1, 6.0), 0)
    E.caja(bm, (2.0, -0.13, 6.0), (12.6, 0.12, 0.2), 1)
    E.caja(bm, (-9.0, -0.05, 0), (1.1, 0.08, 2.2), 2)
    E.objeto("Hangar_blanco_porton", bm, [celeste, M["poste"], M["oscuro"]], p, col)
    bm = bmesh.new()                                     # muro bajo de bloques a lo largo del costado
    E.caja(bm, (-S / 2 - 2.5, L / 2, 0), (0.25, L - 4.0, 1.4), 0)
    E.objeto("Hangar_blanco_muro_bajo", bm, [M["gris_zocalo"]], p, col)
    bm = bmesh.new()                                     # dos bancos de concreto en el césped del frente
    for x in (8.0, 12.0):
        E.caja(bm, (x, -6.0, 0.42), (1.8, 0.45, 0.08), 0)
        for dx in (-0.7, 0.7):
            E.caja(bm, (x + dx, -6.0, 0), (0.12, 0.4, 0.42), 0)
    E.objeto("Hangar_blanco_bancos", bm, [M["concreto_patio"]], p, col)
    palma = bpy.data.meshes.get("Palma_real")
    if palma:                                            # cocoteros entre este hangar y el gris
        for x, y, s in ((S / 2 + 5.0, -6.0, 0.75), (S / 2 + 9.0, -4.0, 0.7)):
            ob = E.instancia(palma, "Palma_hangar_blanco", p, col, x, y, s)
            ob.rotation_euler = (math.radians(8), math.radians(-6), ob.rotation_euler.z)
    E.camara("Cam_Hangar_Blanco", p, col, (6.0, -24.0, 1.7), (0.0, 0.0, 6.5), 20)


def main():
    col = limpiar()
    M = materiales(E.mats())
    sc = bpy.context.scene
    z = sc.get("cota_DIDA")
    if z is None:
        raise SystemExit("Primero hay que correr dida.py (usa la misma cota del terreno)")
    # todo el frente de los dos hangares queda plano a la cota de la calle
    for ub, clave in ((UBS["CEA"], "cota_CEA"), (UBS["Hangar frente al DIDA"], "cota_hangar_gris")):
        E.aplanar(ub["este"], ub["norte"], clave, 55.0, 85.0, z0=z)
    cea(M, col, z)
    hangar_gris(M, col, z)
    ub = UBS["Hangar curvo blanco"]
    E.aplanar(ub["este"], ub["norte"], "cota_hangar_blanco", 50.0, 80.0, z0=z)
    hangar_curvo_blanco(M, col, z)
    # césped de la zona, que se funde con la foto satelital
    pasto = E.pbr("Pasto_hangares", "pasto", 2.5, (0.45, 0.95, 0.30), fade=(60.0, 95.0),
                  variacion=(0.05, (0.85, 0.75, 0.45)))
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, radius=95.0, segments=96)
    ob = E.objeto("Pasto_hangares", bm, [pasto], None, col)
    ob.location = (-440.0, -722.0, z + 0.015)
    bpy.ops.wm.save_mainfile()
    print("hangares listos")


if __name__ == "__main__":
    main()
