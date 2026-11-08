"""Comando de la base (COMBASUCRE) con la torre de control detrás, y el Grupo de Entrenamiento Aéreo N°19.
Se corre después de dorm_g7.py y antes de vias.py:

    blender --background BaseSucre.blend --python comando_g19.py

Fotos: COMANDO DE LA BASE SUCRE, COMANDO DE LA BASE (CASI) FRENTE, TORRE DETRAS DEL COMANDO DE LA BASE, AL LADO DEL
COMANDO DE LA BASE, HANGAR G19 FRENTE, HANGAR 19 DETALLES, AL LADO HANGAR 19, GRUPO 19. Ubicación (confianza media):
datos/ubicaciones.json. Mismo marco que los demás: el frente mira hacia -Y, Z = 0 en el suelo.
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

rnd = E.random.Random(19)


def limpiar():
    col = bpy.data.collections.get("Comando_G19")
    if col:
        for ob in list(col.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.collections.remove(col)
    col = bpy.data.collections.new("Comando_G19")
    bpy.context.scene.collection.children.link(col)
    return col


def auto(nombre, M, p, col, x, y, rumbo, mat, largo=4.3):
    bm = bmesh.new()
    E.caja(bm, (0, 0, 0.3), (1.75, largo, 0.75), 0)
    E.caja(bm, (0, -0.15, 1.05), (1.6, largo * 0.52, 0.55), 1)
    for wx in (-0.84, 0.84):
        for wy in (-largo * 0.31, largo * 0.31):
            E.cilindro(bm, (wx - 0.11, wy, 0.33), 0.33, 0.33, 0.22, 2, 16, (0, math.pi / 2, 0))
    ob = E.objeto(nombre, bm, [mat, M["vidrio"], M["llanta"]], p, col)
    ob.location = (x, y, 0)
    ob.rotation_euler = (0, 0, rumbo)
    return ob


def estacionamiento(M, p, col, nombre, x0, y0, puestos, ancho_puesto=2.6, fondo=5.2, autos=()):
    """Losa con puestos pintados en batería (perpendiculares a la fachada) y algunos carros estacionados."""
    L = puestos * ancho_puesto
    bm = bmesh.new()
    E.caja(bm, (x0 + L / 2, y0 - fondo / 2, 0), (L + 1.0, fondo + 1.0, 0.1), 0)
    E.objeto(nombre, bm, [M["concreto_patio"]], p, col)
    bm = bmesh.new()
    for k in range(puestos + 1):
        E.caja(bm, (x0 + k * ancho_puesto, y0 - fondo / 2, 0.1), (0.12, fondo, 0.02), 0)
    E.objeto(nombre + "_rayas", bm, [M["pintura"]], p, col)
    for i, (k, mat) in enumerate(autos):
        auto(f"{nombre}_auto_{i}", M, p, col, x0 + (k + 0.5) * ancho_puesto, y0 - fondo / 2, rnd.uniform(-0.03, 0.03),
             mat)


# ----------------------------------------------------------------------------------- Comando y torre
def comando(M, col, z):
    ub = Hg.UBS["Comando y torre"]
    p = Hg.origen("Comando_origen", ub, col, z)
    W, D = ub["ancho"], ub["fondo"]
    gris = M["gris_zocalo"]
    rosa = E.pbr("Pared_rosada", "pared", 3.0, pintura=(0.72, 0.36, 0.38))
    xa, xb = -W / 2 + 9.0, W / 2 - 6.5                       # ala izquierda | cuerpo central | ala derecha

    bm = bmesh.new()
    E.caja(bm, (0.5 * (-W / 2 + xa), D / 2, 0), (xa + W / 2, D, 6.2), 0)        # ala izquierda alta
    E.caja(bm, (0.5 * (xa + xb), D / 2 + 1.5, 0), (xb - xa, D - 3.0, 6.6), 0)  # cuerpo central (2 pisos)
    E.caja(bm, (0.5 * (xa + xb) - 2.0, D / 2 + 3.0, 6.6), (xb - xa - 4.0, D - 6.0, 3.0), 0)   # tercer nivel
    E.caja(bm, (0.5 * (xb + W / 2), D / 2, 0), (W / 2 - xb, D, 4.4), 0)        # ala derecha baja
    E.objeto("Comando_volumen", bm, [M["blanco"]], p, col)

    bm = bmesh.new()
    # pórtico de planta baja: losa volada, columnas y zócalo gris al fondo
    E.caja(bm, (0.5 * (xa + xb), 0.1, 3.5), (xb - xa, 3.2, 0.45), 0)
    for x in (xa + 7.0, xa + 12.0):
        E.cilindro(bm, (x, -1.2, 0), 0.35, 0.35, 3.5, 0, 16)
    # remates de cornisa
    for (cx, w, h, y) in ((0.5 * (-W / 2 + xa), xa + W / 2, 6.2, 0.0), (0.5 * (xb + W / 2), W / 2 - xb, 4.4, 0.0)):
        E.caja(bm, (cx, D / 2 + y, h), (w + 0.3, D + 0.3, 0.25), 0)
    E.caja(bm, (0.5 * (xa + xb), D / 2 + 1.5, 6.6), (xb - xa + 0.3, D - 2.7, 0.25), 0)
    E.caja(bm, (0.5 * (xa + xb) - 2.0, D / 2 + 3.0, 9.6), (xb - xa - 3.7, D - 5.7, 0.25), 0)
    E.objeto("Comando_cornisas", bm, [M["blanco"]], p, col)

    bm = bmesh.new()
    E.caja(bm, (0.5 * (xa + xb), 1.47, 0), (xb - xa - 0.1, 0.06, 1.3), 0)      # zócalo gris del pórtico
    E.caja(bm, (0.5 * (xa + xb), 1.46, 1.55), (xb - xa - 0.1, 0.05, 0.1), 0)
    for x0, x1, h in ((-W / 2, xa, 1.0), (xb, W / 2, 1.0)):
        E.caja(bm, (0.5 * (x0 + x1), -0.03, 0), (x1 - x0, 0.06, h), 0)
    E.objeto("Comando_zocalos", bm, [gris], p, col)

    bm = bmesh.new()
    for x in (-W / 2 + 2.0, -W / 2 + 4.3, -W / 2 + 6.6):                    # ala izquierda
        E.caja(bm, (x, -0.03, 1.0), (1.4, 0.06, 1.3), 0)
    for x in (xb + 1.4, xb + 3.3, xb + 5.2):                                # ala derecha
        E.caja(bm, (x, -0.03, 1.5), (1.4, 0.06, 1.2), 0)
    for x in (xa + 2.2, xa + 4.2, xa + 9.0, xa + 14.0, xa + 16.0):         # bajo el pórtico
        E.caja(bm, (x, 1.47, 1.2), (1.2, 0.06, 1.2), 0)
    E.caja(bm, (xa + 11.5, 1.46, 0), (1.7, 0.08, 2.6), 1)                   # puerta de rejas
    E.caja(bm, (xa + 3.5, 1.46, 0), (0.9, 0.08, 2.3), 1)
    E.caja(bm, (xa + 7.5, 1.47, 4.6), (4.6, 0.06, 1.7), 0)                  # ventanales altos
    E.caja(bm, (xa + 14.0, 1.47, 4.6), (4.6, 0.06, 1.7), 0)
    E.caja(bm, (-W / 2 + 3.5, -0.03, 4.4), (2.4, 0.06, 0.9), 0)
    E.caja(bm, (xa + 9.5, 1.47, 3.95), (1.9, 0.06, 0.6), 0)
    E.caja(bm, (xa + 4.0, 1.47, 3.95), (0.5, 0.06, 0.45), 0)
    E.objeto("Comando_ventanas", bm, [M["vidrio"], E.material("Madera_puerta", (0.30, 0.20, 0.12), 0.6)], p, col)
    E.texto("COMBASUCRE", 0.85, E.material("Letras_doradas", (0.70, 0.58, 0.40), 0.35, 0.7), p, col,
            (xa + 11.5, 1.42, 5.3), (math.pi / 2, 0, 0), extr=0.06).data.space_character = 1.2
    bm = bmesh.new()                                                       # antena parabólica beige
    vs = bmesh.ops.create_cone(bm, cap_ends=False, segments=24, radius1=0.05, radius2=0.9, depth=0.3)["verts"]
    bmesh.ops.transform(bm, matrix=E.Matrix.Translation((xa + 1.5, 0.9, 5.3)) @ E.Matrix.Rotation(1.35, 4, "X"),
                        verts=vs)
    E.objeto("Comando_antena", bm, [E.material("Beige_antena", (0.85, 0.62, 0.48), 0.5)], p, col)
    bm = bmesh.new()                                                       # escalones del ala derecha
    for k in range(3):
        E.caja(bm, (0.5 * (xb + W / 2), -0.4 - k * 0.35, 0), (W / 2 - xb, 0.35, 0.45 - k * 0.15), 0)
    E.objeto("Comando_escalones", bm, [M["concreto_patio"]], p, col)

    # torre de control detrás del ala izquierda: fuste rosado y blanco, cabina de vidrio, balcón y escalera
    tx, ty = -W / 2 + 6.0, D + 3.5
    bm = bmesh.new()
    E.caja(bm, (tx, ty, 0), (5.0, 5.0, 13.0), 0)
    E.caja(bm, (tx + 1.4, ty - 2.52, 6.5), (2.2, 0.06, 6.3), 1)             # paño rosado de la cara frontal
    E.caja(bm, (tx - 2.52, ty, 6.5), (0.06, 5.0, 6.3), 1)
    E.objeto("Torre_fuste", bm, [M["blanco"], rosa], p, col)
    bm = bmesh.new()
    E.caja(bm, (tx, ty, 12.9), (7.4, 7.4, 0.3), 0)                          # losa del balcón
    E.caja(bm, (tx, ty, 15.9), (7.8, 7.8, 0.45), 0)                         # techo volado de la cabina
    E.caja(bm, (tx, ty, 16.35), (3.0, 3.0, 0.6), 1)
    E.objeto("Torre_losas", bm, [rosa, M["blanco"]], p, col)
    bm = bmesh.new()                                                       # cabina de vidrio con parteluces
    E.caja(bm, (tx, ty, 13.05), (5.8, 5.8, 2.85), 0)
    for sx in (-1, 1):
        for sy in (-1, 1):
            E.caja(bm, (tx + sx * 2.85, ty + sy * 2.85, 13.05), (0.18, 0.18, 2.85), 1)
    E.objeto("Torre_cabina", bm, [M["vidrio"], M["blanco"]], p, col)
    bm = bmesh.new()
    for k in range(4):
        a = k * math.pi / 2
        for j in range(9):
            s = -3.5 + j * 7.0 / 8
            x = tx + (s if k % 2 == 0 else (3.6 if k == 1 else -3.6))
            y = ty + (s if k % 2 == 1 else (-3.6 if k == 0 else 3.6))
            E.caja(bm, (x, y, 13.05), (0.05, 0.05, 1.0), 0)
        E.caja(bm, (tx + (0 if k % 2 == 0 else (3.6 if k == 1 else -3.6)), ty + (0 if k % 2 == 1 else (-3.6 if k == 0 else 3.6)),
                    14.05), (7.2 if k % 2 == 0 else 0.06, 7.2 if k % 2 == 1 else 0.06, 0.06), 0)
    # escalera exterior que baja del balcón a la azotea del cuerpo central
    a = Vector((tx + 3.6, ty - 1.0, 12.9))
    b = Vector((tx + 11.0, ty - 1.0, 9.85))
    pasos = 16
    for k in range(pasos):
        q = a.lerp(b, (k + 0.5) / pasos)
        E.caja(bm, (q.x, q.y, q.z - 0.04), (0.42, 1.1, 0.05), 0)
    for dy in (-0.6, 0.6):
        for k in range(pasos + 1):
            q = a.lerp(b, k / pasos)
            if k % 4 == 0:
                E.caja(bm, (q.x, q.y + dy, q.z), (0.05, 0.05, 1.0), 0)
        for t in (0.0, 0.5):
            q0, q1 = a.lerp(b, t), a.lerp(b, t + 0.5)
            m = (q0 + q1) / 2
            L = (q1 - q0).length
            E.caja(bm, (m.x, m.y + dy, m.z + 0.95), (L, 0.05, 0.05), 0, (0, math.atan2(q0.z - q1.z, q1.x - q0.x), 0))
    E.objeto("Torre_barandas_escalera", bm, [M["reja"]], p, col)
    bm = bmesh.new()                                                       # baliza y mástil de antenas
    E.cilindro(bm, (tx, ty, 16.95), 0.25, 0.25, 0.5, 0, 12)
    E.cilindro(bm, (tx + 2.8, ty + 2.8, 16.1), 0.04, 0.03, 5.0, 1, 6)
    E.objeto("Torre_baliza", bm, [E.material("Baliza_roja", (0.7, 0.05, 0.03), 0.3), M["poste"]], p, col)

    # plaza frente al Comando: concreto, brocal amarillo curvo, estacionamiento y palmas
    bm = bmesh.new()
    E.caja(bm, (0, -9.0, 0), (W + 16, 18.0, 0.1), 0)
    E.objeto("Comando_plaza", bm, [M["concreto_patio"]], p, col)
    bm = bmesh.new()
    for k in range(13):
        a0, a1 = math.radians(180 + k * 7.5), math.radians(180 + (k + 1) * 7.5)
        c = Vector((W / 2 + 6.0, -12.0))
        q0 = c + Vector((math.cos(a0), math.sin(a0))) * 6.0
        q1 = c + Vector((math.cos(a1), math.sin(a1))) * 6.0
        m = (q0 + q1) / 2
        E.caja(bm, (m.x, m.y, 0.1), ((q1 - q0).length + 0.05, 0.3, 0.18), 0,
               (0, 0, math.atan2(q1.y - q0.y, q1.x - q0.x)))
    E.objeto("Comando_brocal", bm, [M["amarillo"]], p, col)
    estacionamiento(M, p, col, "Comando_estacionamiento", -W / 2 - 6.0, -12.5, 8,
                    autos=((1, M["auto_blanco"]), (2, M["auto_negro"]), (5, E.material("Gris_auto", (0.35, 0.36, 0.38), 0.25, 0.4))))
    palma = bpy.data.meshes.get("Palma_real")
    if palma:
        for x in (-W / 2 - 1.5, -2.0, 6.5):
            E.instancia(palma, "Palma_Comando", p, col, x, -4.0, 0.9)
    bh = bmesh.new()
    E.hojas(bh, Vector((W / 2 + 4.0, -2.0, 3.8)), 4.0, 1600, rnd, 0, 0.28)   # el árbol grande de la derecha
    E.objeto("Comando_arbol", bh, [M["follaje"]], p, col)
    bm = bmesh.new()
    E.cilindro(bm, (W / 2 + 4.0, -2.0, 0), 0.35, 0.25, 3.5, 0, 10)
    E.objeto("Comando_arbol_tronco", bm, [M["tronco"]], p, col)
    E.camara("Cam_Comando", p, col, (-4.0, -30.0, 1.7), (-2.0, 0.0, 7.0), 24)
    E.camara("Cam_Torre", p, col, (tx - 16.0, ty + 18.0, 1.6), (tx, ty, 9.0), 26)
    return p


# ----------------------------------------------------------------------------------- Grupo 19
def grupo19(M, col, z):
    ub = Hg.UBS["Grupo 19"]
    p = Hg.origen("G19_origen", ub, col, z)
    S, L = ub["ancho"], ub["fondo"]
    hw, flecha = 5.0, 9.0
    perfil = Hg.arco(S / 2, hw, flecha)
    # fotos: frente de lámina marrón oscura y oxidada; costados y bóveda verde turquesa (AL LADO HANGAR 19); pared
    # baja color crema con jardinera de ladrillo y bancos de concreto
    oscuro = E.pbr("Lamina_oscura_g19", "lamina_oxidada", 2.0, metal=0.3, pintura=(0.20, 0.16, 0.13))
    turquesa = E.pbr("Lamina_turquesa", "lamina_gastada", 2.0, metal=0.2, pintura=(0.10, 0.55, 0.47))
    crema = E.pbr("Pared_crema_g19", "friso", 3.0, pintura=(0.86, 0.76, 0.62))
    bm = bmesh.new()
    an = [[bm.verts.new((x * 1.015, y, zz + 0.05)) for x, zz in perfil] for y in (-0.6, L + 0.6)]
    for k in range(len(perfil) - 1):
        bm.faces.new((an[0][k], an[0][k + 1], an[1][k + 1], an[1][k]))
    E.objeto("G19_boveda", bm, [turquesa], p, col)
    bm = bmesh.new()
    E.caja(bm, (0, L / 2, 0), (S, L, hw), 0)
    for y in (0.0, L):
        f = bm.faces.new([bm.verts.new((x, y, zz)) for x, zz in perfil])
        f.material_index = 1
    E.objeto("G19_muros", bm, [turquesa, oscuro], p, col)
    bm = bmesh.new()                                         # pared baja crema del frente
    E.caja(bm, (0, -0.03, 0), (S - 6.0, 0.06, hw), 0)
    E.objeto("G19_pared_crema", bm, [crema], p, col)
    bm = bmesh.new()                                         # jardinera de ladrillo y bancos
    E.caja(bm, (2.0, -1.6, 0), (18.0, 0.35, 0.55), 0)
    for x in (-3.0, 3.5, 9.0):
        E.caja(bm, (x, -3.2, 0.42), (1.9, 0.45, 0.08), 1)
        for dx in (-0.75, 0.75):
            E.caja(bm, (x + dx, -3.2, 0), (0.12, 0.4, 0.42), 1)
    lad = bpy.data.materials.get("Ladrillo_real") or E.pbr("Ladrillo_real", "ladrillo", 1.6, (0.95, 0.85, 0.80))
    E.objeto("G19_jardinera", bm, [lad, M["concreto_patio"]], p, col)
    # frente: lámina oscura hasta abajo en los costados, zócalo, ventanitas y puerta
    bm = bmesh.new()
    for x0, x1 in ((-S / 2, -S / 2 + 3.0), (S / 2 - 3.0, S / 2)):
        E.caja(bm, (0.5 * (x0 + x1), -0.04, 0), (x1 - x0, 0.08, hw), 0)
    E.objeto("G19_costados", bm, [oscuro], p, col)
    bm = bmesh.new()                                         # ventanas con reja blanca, como en las fotos
    for x in (-9.5, -6.5, -2.0, 4.5, 8.5):
        Hg.ventana_reja(bm, x, -0.06, 2.4, 1.3, 0.8, 0, 2)
    E.caja(bm, (-4.3, -0.09, 0), (1.3, 0.06, 2.4), 1)
    E.objeto("G19_ventanas", bm, [M["vidrio"], M["oscuro"], M["reja"]], p, col)
    # el letrero sube un poco hacia la derecha, como en la foto (giro dentro del plano de la fachada)
    E.texto("GRUPO DE ENTRENAMIENTO AÉREO N°19", 0.58, M["blanco"], p, col, (-0.5, -0.12, 10.4),
            (math.pi / 2, math.radians(-4), 0), extr=0.03)
    # pancarta de bienvenida (tonos oscuros con franjas claras, sin reproducir las fotos)
    bm = bmesh.new()
    E.caja(bm, (-5.0, -0.1, 5.4), (9.5, 0.06, 4.2), 0)
    for k, x in enumerate((-3.6, -1.2, 1.1)):
        E.caja(bm, (x, -0.15, 6.0), (2.0, 0.03, 3.0), 1 + k % 2)
    E.objeto("G19_pancarta", bm, [E.material("Pancarta_azul_noche", (0.03, 0.04, 0.08), 0.5),
                                   E.material("Pancarta_verde", (0.20, 0.35, 0.22), 0.5),
                                   E.material("Pancarta_cielo", (0.35, 0.50, 0.62), 0.5)], p, col)
    E.texto("BIENVENIDOS AL NIDO DEL CÓNDOR", 0.32, M["blanco"], p, col, (-7.7, -0.16, 7.0), (math.pi / 2, 0, 0))
    E.texto("¡CÓNDOR HASTA EL FINAL!", 0.3, E.material("Letras_naranja_g19", (0.95, 0.55, 0.10), 0.4), p, col,
            (-5.0, -0.16, 5.75), (math.pi / 2, 0, 0))
    # valla «NIDO DEL CÓNDOR» a la derecha, sobre dos postes
    bm = bmesh.new()
    for dx in (-1.6, 1.6):
        E.caja(bm, (S / 2 + 4.0 + dx, -5.0, 0), (0.15, 0.15, 2.2), 0)
    E.caja(bm, (S / 2 + 4.0, -5.0, 2.2), (4.4, 0.15, 3.0), 1)
    E.objeto("G19_valla", bm, [M["poste"], E.material("Valla_azul", (0.05, 0.10, 0.25), 0.5)], p, col)
    E.texto("NIDO DEL CÓNDOR", 0.42, E.material("Letras_doradas_valla", (0.95, 0.80, 0.35), 0.4), p, col,
            (S / 2 + 4.0, -5.1, 4.9), (math.pi / 2, 0, 0))
    # piso de ladrillo frente a la fachada, jardín y el carro beige
    bm = bmesh.new()
    E.caja(bm, (0, -3.5, 0), (S + 2, 7.0, 0.1), 0)
    E.objeto("G19_piso", bm, [M["baldosa"]], p, col)
    bh = bmesh.new()
    for x in (-12.0, 12.5, 15.0):
        E.hojas(bh, Vector((x, -6.5, 0.6)), 0.9, 260, rnd, 0, 0.12)
    E.objeto("G19_matas", bh, [M["arbusto_amarillo"] if "arbusto_amarillo" in M else M["arbusto"]], p, col)
    auto("G19_auto_beige", M, p, col, 2.0, -5.0, math.radians(90),
         E.material("Beige_auto", (0.55, 0.48, 0.36), 0.25, 0.4), 4.0)
    estacionamiento(M, p, col, "G19_estacionamiento", -S / 2 - 12.0, -2.0, 4,
                    autos=((0, M["auto_blanco"]), (2, M["auto_negro"])))
    E.camara("Cam_G19", p, col, (4.0, -30.0, 1.7), (0.0, 0.0, 6.5), 26)
    return p


def main():
    col = limpiar()
    M = Hg.materiales(E.mats())
    M["arbusto_amarillo"] = bpy.data.materials.get("Arbusto_amarillo") or M["arbusto"]
    z = bpy.context.scene.get("cota_DIDA")
    if z is None:
        raise SystemExit("Primero hay que correr dida.py")
    for clave, ub in (("cota_comando", Hg.UBS["Comando y torre"]), ("cota_g19", Hg.UBS["Grupo 19"])):
        E.aplanar(ub["este"], ub["norte"], clave, 50.0, 85.0, z0=z)
    comando(M, col, z)
    grupo19(M, col, z)
    pasto = E.pbr("Pasto_comando", "pasto", 2.5, (0.45, 0.95, 0.30), fade=(55.0, 90.0),
                  variacion=(0.05, (0.85, 0.75, 0.45)))
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, radius=90.0, segments=96)
    ob = E.objeto("Pasto_comando", bm, [pasto], None, col)
    ob.location = (-100.0, -400.0, z + 0.01)
    bpy.ops.wm.save_mainfile()
    print("Comando, torre y Grupo 19 listos")


main()
