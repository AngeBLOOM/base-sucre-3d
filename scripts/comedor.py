"""Comedor «Los Tacariguas», a mano derecha después de la entrada (foto del comedor que ella mandó por el chat).
Se corre después de combustible_azul.py y antes de vias.py:

    blender --background BaseSucre.blend --python comedor.py

Edificio largo de un piso: paredes blancas, techo de lámina a dos aguas muy bajo con borde naranja, alero ancho
sobre canes oscuros en diagonal, tres porches con franja de vidrio oscuro bajo el alero, la entrada al centro en
ladrillo con el letrero verde «LOS TACARIGUAS», puertas de vidrio de marco turquesa, dos escudos a la izquierda y
un emblema redondo a la derecha; jardineras de ladrillo con matas al pie de la fachada, estacionamiento de concreto
con rayas amarillas (sin carros), franja de césped con faroles blancos de globo y un árbol grande a la izquierda.
Sin adornos de Navidad. Mismo marco que los demás: el frente mira hacia -Y, X a lo ancho, Z = 0 en el suelo.
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

rnd = E.random.Random(77)


def limpiar():
    col = bpy.data.collections.get("Comedor")
    if col:
        for ob in list(col.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.collections.remove(col)
    col = bpy.data.collections.new("Comedor")
    bpy.context.scene.collection.children.link(col)
    return col


def comedor(M, col, z):
    ub = Hg.UBS["Comedor"]
    p = Hg.origen("Comedor_origen", ub, col, z)
    W, D, H = ub["ancho"], ub["fondo"], 4.2
    blanco = E.pbr("Friso_blanco_gastado", "friso", 3.0, pintura=(0.84, 0.85, 0.85))
    ladrillo = bpy.data.materials.get("Ladrillo_real") or E.pbr("Ladrillo_real", "ladrillo", 1.6, (0.95, 0.85, 0.80))
    # fotos del comedor completo (2026-11-05): techo de lámina naranja rojiza con fascia y canal blancos, vidrios
    # azul oscuro con marco blanco más pequeños, parteluces blancos en la franja de los porches
    naranja = M["blanco"]                                   # la fascia es blanca
    gris = E.pbr("Lamina_techo_naranja", "lamina_gastada", 2.0, metal=0.15, pintura=(0.50, 0.14, 0.06))
    oscuro = E.material("Vidrio_oscuro_comedor", (0.015, 0.02, 0.025), 0.05)
    azul_vid = E.material("Vidrio_azul_comedor", (0.008, 0.03, 0.10), 0.05, 0.1)
    negro = E.material("Canes_negros", (0.04, 0.04, 0.045), 0.5, 0.3)
    turquesa = E.material("Marco_turquesa", (0.05, 0.42, 0.45), 0.4, 0.3)
    verde = E.material("Letrero_verde", (0.03, 0.22, 0.12), 0.45)

    # tramos de la fachada (de izquierda a derecha): bloque | porche | entrada | porche | bloque
    xb0, xp0, xe0, xe1, xp1, xb1 = -W / 2, -W / 2 + 9.5, -4.5, 4.5, W / 2 - 9.5, W / 2
    retiro = 2.2                                        # los porches quedan retirados bajo el alero
    bm = bmesh.new()
    E.caja(bm, (0, D / 2 + retiro / 2, 0), (W, D - retiro, H), 0)              # volumen principal
    for x0, x1 in ((xb0, xp0), (xp1, xb1)):
        E.caja(bm, (0.5 * (x0 + x1), retiro / 2, 0), (x1 - x0, retiro, H), 0)  # bloques de los extremos al frente
    E.objeto("Comedor_volumen", bm, [blanco], p, col)
    bm = bmesh.new()                                    # cuerpo de la entrada en ladrillo, al ras de los bloques
    E.caja(bm, (0, retiro / 2, 0), (xe1 - xe0, retiro, H - 0.6), 0)
    E.objeto("Comedor_entrada_ladrillo", bm, [ladrillo], p, col)

    # franja de vidrio oscuro bajo el alero en los porches y sobre la entrada, con su viga negra
    bm = bmesh.new()
    for x0, x1, y in ((xp0, xe0, retiro), (xe1, xp1, retiro), (xe0, xe1, -0.02)):
        E.caja(bm, (0.5 * (x0 + x1), y - 0.03, H - 1.15), (x1 - x0, 0.06, 1.0), 0)
    E.objeto("Comedor_franja_vidrio", bm, [oscuro], p, col)
    bm, bw = bmesh.new(), bmesh.new()
    for x0, x1, y in ((xp0, xe0, retiro), (xe1, xp1, retiro), (xe0, xe1, -0.02)):
        E.caja(bm, (0.5 * (x0 + x1), y - 0.08, H - 1.25), (x1 - x0, 0.1, 0.12), 0)
        for k in range(1, int((x1 - x0) / 2.2) + 1):
            E.caja(bw, (x0 + k * (x1 - x0) / (int((x1 - x0) / 2.2) + 1), y - 0.08, H - 1.15), (0.07, 0.07, 1.0), 0)
    E.objeto("Comedor_parteluces", bm, [negro], p, col)
    E.objeto("Comedor_parteluces_blancos", bw, [M["blanco"]], p, col)

    # ventanas de vidrio azul oscuro con marco blanco delgado (≈ 1,9 x 1,05 m, antepecho a 1,35 m)
    bm, bmm = bmesh.new(), bmesh.new()
    vent = [(xb0 + 2.4, 0.0), (xb0 + 6.4, 0.0), (xp0 + 2.6, retiro), (xp0 + 6.0, retiro), (xp0 + 9.4, retiro),
            (xe1 + 3.2, retiro), (xe1 + 7.6, retiro), (xb1 - 6.4, 0.0), (xb1 - 2.4, 0.0)]
    for x, y in vent:
        E.caja(bmm, (x, y - 0.02, 1.28), (2.1, 0.04, 1.2), 0)           # marco blanco detrás
        E.caja(bm, (x, y - 0.06, 1.35), (1.92, 0.04, 1.06), 0)          # vidrio azul delante
        E.caja(bmm, (x, y - 0.08, 1.35), (0.05, 0.03, 1.06), 0)         # parteluz central
        E.caja(bmm, (x, y - 0.1, 1.2), (2.2, 0.16, 0.06), 0)            # alféizar
    E.objeto("Comedor_ventanas", bm, [azul_vid], p, col)
    E.objeto("Comedor_marcos", bmm, [M["blanco"]], p, col)
    aire = E.material("Aire_acondicionado", (0.80, 0.80, 0.78), 0.5)
    bm = bmesh.new()
    for x in (xb1 - 4.4, xb0 + 4.4):                                   # aires split de pared en los bloques
        E.caja(bm, (x, -0.2, 2.45), (0.85, 0.3, 0.32), 0)
    E.objeto("Comedor_aire", bm, [aire], p, col)
    bm = bmesh.new()                                    # condensadores negros en el piso de los porches
    for x, y in ((xp0 + 1.4, retiro - 0.45), (xp0 + 2.6, retiro - 0.45), (xe1 + 5.4, retiro - 0.45)):
        E.caja(bm, (x, y, 0.15), (0.85, 0.38, 0.7), 0)
        E.cilindro(bm, (x, y - 0.2, 0.5), 0.26, 0.26, 0.02, 1, 20, (math.pi / 2, 0, 0))
    E.objeto("Comedor_condensadores", bm, [E.material("Condensador_negro", (0.03, 0.03, 0.035), 0.5),
                                            E.material("Rejilla_condensador", (0.12, 0.12, 0.13), 0.6, 0.5)], p, col)
    bm, bl = bmesh.new(), bmesh.new()                   # bajantes blancos y lámparas redondas de pared
    for x in (xp0 + 0.2, xe0 - 0.2, xe1 + 0.2, xp1 - 0.2):
        E.cilindro(bm, (x, -0.25, 0.0), 0.07, 0.07, H + 0.1, 0, 10)
    for x, y, zz in ((xb0 + 4.4, -0.03, 3.2), (xb1 - 4.4, -0.03, 3.2), (xe1 + 8.0, retiro - 0.03, 3.0)):
        E.cilindro(bl, (x, y, zz), 0.15, 0.15, 0.06, 0, 18, (math.pi / 2, 0, 0))
    E.objeto("Comedor_bajantes", bm, [M["blanco"]], p, col)
    E.objeto("Comedor_lamparas_pared", bl, [M["luz"]], p, col)
    bm, bh = bmesh.new(), bmesh.new()
    for x0, x1, y in ((xp0 + 0.3, xe0 - 0.3, retiro - 0.9), (xe1 + 0.3, xp1 - 0.3, retiro - 0.9),
                      (xe0 + 0.2, -1.6, -0.6), (1.6, xe1 - 0.2, -0.6)):
        E.caja(bm, (0.5 * (x0 + x1), y, 0), (x1 - x0, 0.7, 0.55), 0)
        x = x0 + 0.5
        while x < x1 - 0.3:
            E.hojas(bh, Vector((x, y, 0.95)), 0.42, 90, rnd, 0, 0.12)
            x += 1.1
    E.objeto("Comedor_jardineras", bm, [ladrillo], p, col)
    E.objeto("Comedor_matas", bh, [M["arbusto"]], p, col)

    # entrada: puertas de vidrio con marco turquesa, letrero verde, dos escudos y el emblema redondo
    bm = bmesh.new()
    E.caja(bm, (0, -0.04, 0), (3.2, 0.08, 2.7), 0)
    E.objeto("Comedor_puertas_vidrio", bm, [E.material("Vidrio_turquesa", (0.02, 0.32, 0.48), 0.05, 0.2)], p, col)
    bm = bmesh.new()
    for x in (-1.6, -0.55, 0.55, 1.6):
        E.caja(bm, (x, -0.09, 0), (0.09, 0.08, 2.75), 0)
    E.caja(bm, (0, -0.09, 2.7), (3.3, 0.08, 0.1), 0)
    E.caja(bm, (0, -0.09, 1.0), (3.2, 0.06, 0.06), 0)
    E.objeto("Comedor_puertas_marco", bm, [turquesa], p, col)
    bm = bmesh.new()
    E.caja(bm, (0, -0.1, 2.95), (4.6, 0.1, 0.75), 0)
    E.objeto("Comedor_letrero", bm, [verde], p, col)
    oro = E.material("Letras_doradas_comedor", (0.86, 0.72, 0.38), 0.35, 0.6)
    E.texto("LOS TACARIGUAS", 0.36, oro, p, col, (0, -0.17, 3.37), (math.pi / 2, 0, 0), extr=0.02)
    E.texto("COMEDOR", 0.16, oro, p, col, (0, -0.17, 3.05), (math.pi / 2, 0, 0), extr=0.01)
    bm = bmesh.new()
    for x in (-3.3, -2.5):                               # dos escudos a la izquierda de la puerta
        E.caja(bm, (x, -0.06, 2.65), (0.5, 0.05, 0.6), 0)
        E.caja(bm, (x, -0.09, 2.68), (0.4, 0.03, 0.48), 1)
    E.cilindro(bm, (2.9, -0.07, 2.95), 0.42, 0.42, 0.05, 0, 28, (math.pi / 2, 0, 0))   # emblema redondo
    E.cilindro(bm, (2.9, -0.11, 2.95), 0.33, 0.33, 0.03, 2, 28, (math.pi / 2, 0, 0))
    E.objeto("Comedor_escudos", bm, [M["blanco"], M["azul_emblema"], E.material("Rojo_emblema", (0.6, 0.06, 0.05), 0.4)],
             p, col)

    # techo: dos aguas muy bajas con alero de 2,6 m al frente, cumbrera a lo largo, borde naranja y canes
    alero = 2.6
    ya, yc, yz = -alero, D / 2, D + 1.0
    bm = bmesh.new()
    for y0, y1, z0, z1 in ((ya, yc, H + 0.05, H + 1.5), (yc, yz, H + 1.5, H + 0.05)):
        bm.faces.new([bm.verts.new(v) for v in ((-W / 2 - 1.0, y0, z0), (W / 2 + 1.0, y0, z0),
                                                (W / 2 + 1.0, y1, z1), (-W / 2 - 1.0, y1, z1))])
    E.objeto("Comedor_techo", bm, [gris], p, col)
    bm = bmesh.new()
    E.caja(bm, (0, ya - 0.05, H - 0.2), (W + 2.1, 0.12, 0.32), 0)                   # fascia naranja del frente
    for s in (-1, 1):
        E.caja(bm, (s * (W / 2 + 1.05), D / 2, H - 0.1), (0.12, D + 2 * alero, 0.3), 0)
    E.objeto("Comedor_borde", bm, [naranja], p, col)
    bm = bmesh.new()                                    # cielo raso del alero y canes diagonales
    E.caja(bm, (0, ya / 2, H - 0.02), (W + 2.0, alero, 0.06), 0)
    for k in range(10):
        x = -W / 2 + 1.0 + k * (W - 2.0) / 9
        y0 = 0.0 if not (xp0 < x < xp1) else retiro
        a, b = Vector((x, y0, H - 1.4)), Vector((x, ya + 0.3, H - 0.05))
        d = b - a
        E.caja(bm, ((a.x + b.x) / 2, (a.y + b.y) / 2, (a.z + b.z) / 2 - 0.08), (0.14, d.length, 0.14), 1,
               (math.atan2(d.z, d.y), 0, 0))
    E.objeto("Comedor_alero", bm, [M["cielo_raso"], negro], p, col)
    bm = bmesh.new()                                    # chimeneas y respiraderos de la cocina en el techo
    for x, y, h in ((-2.0, D * 0.45, 1.6), (6.0, D * 0.4, 1.2), (14.0, D * 0.5, 1.0), (-14.0, D * 0.55, 1.0)):
        E.caja(bm, (x, y, H + 1.0), (0.7, 0.7, h), 0)
        E.caja(bm, (x, y, H + 1.0 + h), (1.0, 1.0, 0.08), 0)
    E.objeto("Comedor_chimeneas", bm, [E.material("Galvanizado", (0.55, 0.56, 0.57), 0.35, 0.8)], p, col)

    # acera, estacionamiento con rayas amarillas, franja de césped con faroles de globo y el árbol grande
    bm = bmesh.new()
    E.caja(bm, (0, -1.4, 0), (W + 1.0, 2.8, 0.14), 0)
    E.objeto("Comedor_acera", bm, [M["acera"]], p, col)
    # salón alto en el extremo ESTE (foto «y ahí empieza el comedor»): testero a dos aguas hacia el estacionamiento
    # grande, fila de ventanas altas bajo el alero, puerta de marco marrón, tres ventanas y condensadores
    este = 1.0 if p.matrix_world.col[0].x > 0 else -1.0      # lado del marco local que cae al este
    Ls, Hs, Hc = 13.0, 5.4, 7.6
    xs0, xs1 = sorted((este * W / 2, este * (W / 2 + Ls)))
    xt = este * (W / 2 + Ls)                                  # x del testero
    bm = bmesh.new()
    E.caja(bm, (0.5 * (xs0 + xs1), D / 2 - 1.0, 0), (Ls, D - 2.0, Hs), 0)
    for xx in (xs0, xs1):                                     # testeros triangulares (cumbrera a lo largo de X)
        bm.faces.new([bm.verts.new(v) for v in ((xx, 0.0, Hs), (xx, D - 2.0, Hs), (xx, D / 2 - 1.0, Hc))])
    E.objeto("Comedor_salon", bm, [blanco], p, col)
    bm = bmesh.new()
    for y0, y1, z0, z1 in ((-0.8, D / 2 - 1.0, Hs - 0.2, Hc), (D / 2 - 1.0, D - 1.2, Hc, Hs - 0.2)):
        bm.faces.new([bm.verts.new(v) for v in ((xs0 - 0.6, y0, z0), (xs1 + 0.6, y0, z0),
                                                (xs1 + 0.6, y1, z1), (xs0 - 0.6, y1, z1))])
    E.objeto("Comedor_salon_techo", bm, [gris], p, col)
    bm, bv = bmesh.new(), bmesh.new()
    E.caja(bm, (0.5 * (xs0 + xs1), -0.85, Hs - 0.45), (Ls + 1.3, 0.1, 0.28), 0)          # fascia blanca
    n = 14
    for k in range(n):                                        # ventanas altas bajo el alero, en el frente
        x = xs0 + (k + 0.5) * Ls / n
        E.caja(bv, (x, -0.04, Hs - 1.25), (Ls / n - 0.22, 0.04, 0.75), 0)
        E.caja(bm, (x - Ls / n / 2, -0.06, Hs - 1.3), (0.08, 0.06, 0.85), 0)
    for k, y in enumerate((3.0, 6.0, 9.5)):                   # testero: tres ventanas y la puerta
        E.caja(bv, (xt + este * 0.04, y, 1.35), (0.04, 1.1, 1.05), 0)
    E.caja(bv, (xt + este * 0.04, 12.6, 0.0), (0.05, 1.0, 2.15), 1)
    E.caja(bm, (xt + este * 0.07, 12.6, 0.0), (0.05, 1.2, 2.3), 0)
    E.objeto("Comedor_salon_detalles", bm, [M["blanco"]], p, col)
    E.objeto("Comedor_salon_vanos", bv, [azul_vid, E.material("Puerta_marron", (0.20, 0.10, 0.05), 0.5)], p, col)
    bm = bmesh.new()
    for y in (4.5, 7.6):
        E.caja(bm, (xt + este * 0.5, y, 0.1), (0.4, 0.85, 0.7), 0)
    E.objeto("Comedor_salon_condensadores", bm, [bpy.data.materials["Condensador_negro"]], p, col)

    # estacionamiento de losas de concreto con juntas: al frente y el lote grande al este, rayas amarillas
    ye0, ye1 = -3.0, -24.0
    xl0, xl1 = sorted((-este * (W / 2 + 8.0), este * (W / 2 + Ls + 42.0)))
    concreto = bpy.data.materials.get("Concreto_gastado") or M["concreto"]
    bm = bmesh.new()
    E.caja(bm, (0.5 * (xl0 + xl1), 0.5 * (ye0 + ye1), 0), (xl1 - xl0, ye0 - ye1, 0.1), 0)
    xg0, xg1 = sorted((este * (W / 2 + Ls + 2.0), este * (W / 2 + Ls + 42.0)))
    E.caja(bm, (0.5 * (xg0 + xg1), 0.5 * (ye0 + D + 6.0), 0), (xg1 - xg0, D + 6.0 - ye0, 0.1), 0)
    E.objeto("Comedor_estacionamiento", bm, [concreto], p, col)
    bm = bmesh.new()                                     # juntas de las losas (5 m)
    juntas = E.material("Junta_losa", (0.10, 0.10, 0.10), 0.9)
    x = xl0 + 5.0
    while x < xl1:
        E.caja(bm, (x, 0.5 * (ye0 + ye1), 0.1), (0.04, ye0 - ye1, 0.004), 0)
        x += 5.0
    y = ye1 + 5.0
    while y < ye0:
        E.caja(bm, (0.5 * (xl0 + xl1), y, 0.1), (xl1 - xl0, 0.04, 0.004), 0)
        y += 5.0
    y = ye0 + 5.0
    while y < D + 6.0:
        E.caja(bm, (0.5 * (xg0 + xg1), y, 0.1), (xg1 - xg0, 0.04, 0.004), 0)
        y += 5.0
    E.objeto("Comedor_juntas", bm, [juntas], p, col)
    bm = bmesh.new()
    x = xl0 + 2.0
    while x <= xl1 - 2.0:
        E.caja(bm, (x, -6.5, 0.1), (0.12, 5.0, 0.01), 0)
        x += 2.7
    E.caja(bm, (0.5 * (xl0 + xl1), ye1 + 0.3, 0.1), (xl1 - xl0, 0.15, 0.01), 0)
    E.objeto("Comedor_rayas", bm, [M["amarillo"]], p, col)
    # reflectores altos del lote grande (poste blanco de 12 m con dos lámparas)
    bm, bf = bmesh.new(), bmesh.new()
    for x, y in ((este * (W / 2 + Ls + 20.0), D + 4.0), (este * (W / 2 + Ls + 40.0), ye1 + 2.0)):
        E.cilindro(bm, (x, y, 0.1), 0.16, 0.09, 12.0, 0, 12)
        for s in (-1, 1):
            E.caja(bf, (x + s * 0.35, y, 12.0), (0.5, 0.25, 0.35), 0)
    # faroles de jardín de la franja de césped: poste blanco cuadrado y farol de vidrio con sombrerete negro
    for k in range(int((xl1 - xl0 - 8.0) / 9.0) + 1):
        x = xl0 + 4.0 + k * 9.0
        E.caja(bm, (x, ye1 - 3.0, 0), (0.22, 0.22, 1.5), 0)
        E.cilindro(bf, (x, ye1 - 3.0, 1.5), 0.13, 0.16, 0.42, 0, 8)
    E.objeto("Comedor_faroles", bm, [M["blanco"]], p, col)
    E.objeto("Comedor_faroles_luz", bf, [M["luz"]], p, col)
    bm = bmesh.new()
    for k in range(int((xl1 - xl0 - 8.0) / 9.0) + 1):
        x = xl0 + 4.0 + k * 9.0
        E.cilindro(bm, (x, ye1 - 3.0, 1.92), 0.2, 0.04, 0.16, 0, 8)
    E.objeto("Comedor_faroles_techo", bm, [negro], p, col)
    bm = bmesh.new()
    E.caja(bm, (0.5 * (xl0 + xl1), ye1 - 0.12, 0), (xl1 - xl0, 0.25, 0.2), 0)
    E.objeto("Comedor_brocal", bm, [M["amarillo"]], p, col)
    # palmas Bismarck en la franja (con la base del tronco pintada de blanco, como todos los de las fotos)
    me = bpy.data.meshes.get("Palma_bismarck")
    if me is None:
        import dida
        me = dida.malla_bismarck(M["tronco_palma"], M["hoja_palma"])
    for x in (-este * 14.0, este * 9.0, este * (W / 2 + 6.0)):
        ob = bpy.data.objects.new("Bismarck_comedor", me)
        ob.location = (x, ye1 - 6.0, 0)
        ob.rotation_euler = (0, 0, rnd.uniform(0, 6.3))
        ob.scale = (1.0, 1.0, 0.8)
        col.objects.link(ob)
        ob.parent = p
    E.camara("Cam_Comedor", p, col, (0.0, ye1 - 16.0, 1.7), (0.0, 0.0, 3.0), 18)
    E.camara("Cam_Comedor_Entrada", p, col, (6.0, -12.0, 1.7), (0.0, 0.0, 3.0), 26)
    E.camara("Cam_Comedor_Salon", p, col, (-este * 2.0, ye1 - 12.0, 1.6),
             (este * (W / 2 + Ls + 4.0), 6.0, 3.0), 22)
    return p


def main():
    col = limpiar()
    M = Hg.materiales(E.mats())
    ub = Hg.UBS["Comedor"]
    z = E.aplanar(ub["este"], ub["norte"] + 5.0, "cota_comedor", 55.0, 90.0)
    comedor(M, col, z)
    pasto = E.pbr("Pasto_comedor", "pasto", 2.5, (0.45, 0.95, 0.30), fade=(55.0, 85.0),
                  variacion=(0.05, (0.85, 0.75, 0.45)))
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, radius=85.0, segments=96)
    ob = E.objeto("Pasto_comedor", bm, [pasto], None, col)
    ob.location = (ub["este"], ub["norte"], z + 0.01)
    bpy.ops.wm.save_mainfile()
    print("Comedor listo")


if __name__ == "__main__":
    main()
