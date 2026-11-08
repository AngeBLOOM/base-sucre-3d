"""Estación de Bomberos de la base, más allá del Grupo 19 (fotos BOMBEROS DE LA BASE, BOMBEROS DE LA BASE Y PARTE
DE PISTA). Se corre después de comando_g19.py y antes de vias.py:

    blender --background BaseSucre.blend --python bomberos.py

Edificio de techo plano de 35,5 x 13 m: a la izquierda las oficinas de dos niveles con franja rosada y ventanas, a la
derecha tres naves para las máquinas con portones rojos y pilares blancos, saliente de la entrada al centro y un
techado de estructura metálica al lado, mirando a la calle de rodaje y la pista. Delante, la losa de concreto; al
lado, los árboles grandes de la foto, el poste de luz y la señal azul. Mismo marco que los demás: el frente mira
hacia -Y, X a lo ancho, Z = 0 en el suelo.
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

rnd = E.random.Random(115)


def limpiar():
    col = bpy.data.collections.get("Bomberos")
    if col:
        for ob in list(col.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.collections.remove(col)
    col = bpy.data.collections.new("Bomberos")
    bpy.context.scene.collection.children.link(col)
    return col


def bomberos(M, col, z):
    ub = Hg.UBS["Bomberos"]
    p = Hg.origen("Bomberos_origen", ub, col, z)
    W, D = ub["ancho"], ub["fondo"]
    xn = -W / 2 + 15.5                     # fin de las oficinas, empiezan las naves
    h_of, h_nv = 6.6, 6.2
    rosa = bpy.data.materials.get("Pared_rosada") or E.pbr("Pared_rosada", "friso", 3.0, pintura=(0.72, 0.36, 0.38))
    rojo = E.pbr("Porton_rojo", "lamina_gastada", 1.2, metal=0.3, pintura=(0.62, 0.05, 0.04))
    gris = M["gris_zocalo"]

    # volúmenes: oficinas de dos niveles, naves y saliente de la entrada
    bm = bmesh.new()
    E.caja(bm, (0.5 * (-W / 2 + xn), D / 2, 0), (xn + W / 2, D, h_of), 0)
    E.caja(bm, (0.5 * (xn + W / 2), D / 2, 0), (W / 2 - xn, D, h_nv), 0)
    E.caja(bm, (xn - 2.0, -1.9, 0), (8.4, 3.8, 3.6), 0)
    E.objeto("Bomberos_volumen", bm, [M["blanco"]], p, col)

    # franja rosada del piso alto de las oficinas, zócalo gris y cornisas
    bm = bmesh.new()
    E.caja(bm, (0.5 * (-W / 2 + xn), -0.03, 3.6), (xn + W / 2, 0.06, h_of - 3.6 - 0.35), 0)
    E.caja(bm, (-W / 2 - 0.03, D / 2, 3.6), (0.06, D, h_of - 3.6 - 0.35), 0)
    E.objeto("Bomberos_franja", bm, [rosa], p, col)
    bm = bmesh.new()
    E.caja(bm, (0, -0.04, 0), (W + 0.08, 0.08, 0.9), 0)
    E.caja(bm, (xn - 2.0, -3.84, 0), (8.5, 0.08, 0.9), 0)
    E.objeto("Bomberos_zocalo", bm, [gris], p, col)
    bm = bmesh.new()
    E.caja(bm, (0.5 * (-W / 2 + xn), D / 2 - 0.4, h_of), (xn + W / 2 + 1.2, D + 2.0, 0.35), 0)
    E.caja(bm, (0.5 * (xn + W / 2), D / 2 - 0.8, h_nv), (W / 2 - xn + 1.2, D + 2.8, 0.3), 0)
    E.caja(bm, (xn - 2.0, -2.0, 3.6), (9.0, 4.4, 0.28), 0)
    for x0, x1, h in ((-W / 2 - 0.6, xn, h_of), (xn, W / 2 + 0.6, h_nv)):      # pretiles de la azotea
        E.caja(bm, (0.5 * (x0 + x1), -1.4, h + 0.3), (x1 - x0, 0.2, 0.45), 0)
    E.objeto("Bomberos_cornisas", bm, [M["blanco"]], p, col)

    # naves: tres portones rojos de enrollar con pilares blancos y alero de concreto
    bm, bp = bmesh.new(), bmesh.new()
    ancho_nave = (W / 2 - xn) / 3
    for i in range(3):
        xc = xn + (i + 0.5) * ancho_nave
        E.caja(bm, (xc, -0.06, 0.0), (ancho_nave - 1.1, 0.1, 4.6), 0)
        for k in range(26):                                          # lamas del portón
            E.caja(bm, (xc, -0.12, 0.1 + k * 0.175), (ancho_nave - 1.15, 0.03, 0.05), 0)
        E.caja(bp, (xn + i * ancho_nave + 0.05, -0.25, 0), (0.6, 0.5, h_nv), 0)
        E.caja(bp, (xc, -0.25, 4.6), (ancho_nave - 1.0, 0.5, 0.35), 0)
    E.caja(bp, (W / 2 - 0.3, -0.25, 0), (0.6, 0.5, h_nv), 0)
    E.objeto("Bomberos_portones", bm, [rojo], p, col)
    E.objeto("Bomberos_pilares", bp, [M["blanco"]], p, col)

    # oficinas: ventanas con reja en los dos niveles y puerta de vidrio en el saliente
    bm = bmesh.new()
    for x in (-W / 2 + 2.0, -W / 2 + 4.6, -W / 2 + 7.2):
        Hg.ventana_reja(bm, x, -0.03, 1.2, 1.6, 1.2, 0, 1)
    for x in (-W / 2 + 2.0, -W / 2 + 4.6, -W / 2 + 7.2, -W / 2 + 9.8, -W / 2 + 12.4):
        E.caja(bm, (x, -0.05, 4.25), (1.8, 0.06, 1.3), 0)
        E.caja(bm, (x, -0.09, 4.85), (1.8, 0.04, 0.06), 1)
    E.caja(bm, (xn - 2.0, -3.85, 0.0), (2.2, 0.06, 2.6), 0)          # puerta
    for x in (xn - 4.5, xn + 0.5):
        Hg.ventana_reja(bm, x, -3.83, 1.1, 1.4, 1.1, 0, 1)
    E.objeto("Bomberos_ventanas", bm, [M["vidrio"], M["reja"]], p, col)
    E.texto("BOMBEROS AERONÁUTICOS", 0.4,E.material("Letras_rojas_bomberos", (0.65, 0.04, 0.04), 0.4), p, col,
            (xn - 2.0, -4.05, 3.15), (math.pi / 2, 0, 0), extr=0.03)

    # sirena y tanque de agua en la azotea
    bm = bmesh.new()
    E.cilindro(bm, (-W / 2 + 4.0, 6.0, h_of + 0.35), 1.1, 1.1, 1.8, 0, 20)
    E.cilindro(bm, (xn + 4.0, 4.0, h_nv + 0.3), 0.08, 0.08, 2.4, 1, 8)
    E.cilindro(bm, (xn + 4.0, 4.0, h_nv + 2.7), 0.25, 0.32, 0.35, 1, 12)
    E.objeto("Bomberos_azotea", bm, [E.material("Tanque_negro", (0.04, 0.04, 0.045), 0.6), M["poste"]], p, col)

    # techado metálico al lado este (estructura y lámina), como en la foto de la pista
    bm, bt = bmesh.new(), bmesh.new()
    x0, x1, y0, y1 = W / 2 + 1.5, W / 2 + 15.5, -4.0, D - 1.0
    for x in (x0, 0.5 * (x0 + x1), x1):
        for y in (y0, y1):
            E.caja(bm, (x, y, 0), (0.25, 0.25, 4.8), 0)
        E.caja(bm, (x, 0.5 * (y0 + y1), 4.75), (0.18, y1 - y0 + 0.6, 0.3), 0)
    bt.faces.new([bt.verts.new(v) for v in ((x0 - 0.5, y0 - 0.8, 5.05), (x1 + 0.5, y0 - 0.8, 5.05),
                                            (x1 + 0.5, y1 + 0.8, 5.45), (x0 - 0.5, y1 + 0.8, 5.45))])
    E.objeto("Bomberos_techado_estructura", bm, [E.material("Acero_oscuro", (0.12, 0.12, 0.13), 0.5, 0.6)], p, col)
    E.objeto("Bomberos_techado_lamina", bt, [M["lamina_techo"]], p, col)

    # losa de concreto delante de las naves (salida directa a la calle de rodaje) y caminería de las oficinas
    bm = bmesh.new()
    E.caja(bm, (0.5 * (xn + W / 2 + 15.5), -9.0, 0), (W / 2 + 15.5 - xn, 18.0, 0.1), 0)
    E.caja(bm, (xn - 2.0, -8.0, 0), (3.0, 8.0, 0.1), 0)
    E.objeto("Bomberos_losa", bm, [bpy.data.materials.get("Concreto_patio") or M["concreto_patio"]], p, col)
    bm = bmesh.new()                                                # franjas amarillas de salida de emergencia
    for i in range(3):
        xc = xn + (i + 0.5) * ancho_nave
        for k in range(5):
            E.caja(bm, (xc - 1.6 + k * 0.8, -6.0, 0.11), (0.35, 10.0, 0.01), 0)
    E.objeto("Bomberos_salida_pintura", bm, [M["amarillo"]], p, col)

    # árboles grandes alrededor (los de la foto), poste de luz con cables y la señal azul
    bh = bmesh.new()
    for x, y, r in ((W / 2 + 22.0, 6.0, 4.5), (W / 2 + 29.0, -2.0, 4.0), (-W / 2 - 6.0, 2.0, 4.2),
                    (-W / 2 - 9.0, -9.0, 3.8)):
        E.hojas(bh, Vector((x, y, 5.6)), r, 1800, rnd, 0, 0.3)
    E.objeto("Bomberos_arbol", bh, [M["follaje"]], p, col)
    bm = bmesh.new()
    for x, y in ((W / 2 + 22.0, 6.0), (W / 2 + 29.0, -2.0), (-W / 2 - 6.0, 2.0), (-W / 2 - 9.0, -9.0)):
        E.cilindro(bm, (x, y, 0), 0.45, 0.3, 4.2, 0, 10)
    E.objeto("Bomberos_arbol_tronco", bm, [M["tronco"]], p, col)
    bm = bmesh.new()
    E.cilindro(bm, (W / 2 + 4.0, -16.0, 0), 0.18, 0.13, 10.0, 0, 10)
    E.caja(bm, (W / 2 + 4.0, -16.0, 9.2), (2.2, 0.12, 0.12), 0)
    E.cilindro(bm, (-W / 2 - 14.0, -30.0, 0), 0.12, 0.06, 2.6, 0, 8)
    E.objeto("Bomberos_postes", bm, [M["concreto_patio"]], p, col)
    bm = bmesh.new()
    E.cilindro(bm, (-W / 2 - 14.0, -30.1, 2.9), 0.55, 0.55, 0.04, 0, 28, (math.pi / 2, 0, 0))
    E.caja(bm, (-W / 2 - 14.0, -30.1, 1.85), (1.2, 0.04, 0.55), 1)
    E.objeto("Bomberos_senal", bm, [E.material("Senal_azul", (0.05, 0.22, 0.65), 0.4),
                                    E.material("Senal_blanca", (0.85, 0.85, 0.85), 0.4)], p, col)

    # paneles a cuadros rojos y blancos (video DE LOS BOMBEROS HASTA EL DIDA y foto BOMBEROS DE LA BASE): a los lados
    # de la entrada y en las esquinas de la cara que da al campo
    bm = bmesh.new()
    for x in (xn - 5.7, xn + 1.7):
        E.caja(bm, (x, -3.86, 0.9), (0.9, 0.04, 2.7), 0)
    for x in (-W / 2 + 1.5, xn - 1.5, W / 2 - 1.5):
        E.caja(bm, (x, D + 0.03, 0.9), (2.4, 0.04, 3.0), 0)
    E.objeto("Bomberos_cuadros", bm, [mat_cuadros()], p, col)
    # cara trasera (hacia el campo): ventanas con reja, puertas de servicio, zócalo gris y aires
    bm = bmesh.new()
    for x in [-W / 2 + 4.0 + k * 2.6 for k in range(4)] + [xn + 2.0 + k * 3.0 for k in range(5)]:
        if abs(x - (xn - 1.5)) < 1.8 or abs(x - (W / 2 - 1.5)) < 1.8:
            continue
        Hg.ventana_reja(bm, x, D + 0.03, 1.4, 1.4, 1.0, 0, 1, sale=1)
    for x in (-W / 2 + 4.0 + 2.6 * 1.5, xn + 8.0):
        E.caja(bm, (x, D + 0.03, 0), (1.1, 0.06, 2.3), 2)
    for x in (-W / 2 + 4.0, -W / 2 + 9.2):
        Hg.ventana_reja(bm, x, D + 0.03, 4.4, 1.4, 1.0, 0, 1, sale=1)
    E.objeto("Bomberos_trasera", bm, [M["vidrio"], M["reja"], M["oscuro"]], p, col)
    bm = bmesh.new()
    E.caja(bm, (0, D + 0.04, 0), (W + 0.08, 0.08, 0.9), 0)
    E.objeto("Bomberos_zocalo_tras", bm, [gris], p, col)
    bm = bmesh.new()
    for x in (-W / 2 + 6.5, xn + 4.5):
        E.caja(bm, (x, D + 0.35, 2.2), (0.8, 0.6, 0.5), 0)
    E.objeto("Bomberos_aires", bm, [M["aire"]], p, col)

    E.camara("Cam_Bomberos", p, col, (-14.0, -40.0, 1.7), (2.0, 0.0, 3.5), 26)
    # como la foto: desde la calle del sur, a través del campo, con la sierra detrás
    E.camara("Cam_Bomberos_Campo", p, col, (16.0, 42.0, 1.6), (-2.0, 0.0, 4.0), 30)
    return p


def mat_cuadros():
    m = bpy.data.materials.get("Cuadros_rojo_blanco")
    if m:
        return m
    m = bpy.data.materials.new("Cuadros_rojo_blanco")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapa = nt.nodes.new("ShaderNodeMapping")
    mapa.inputs["Rotation"].default_value = (math.pi / 2, 0, 0)        # cuadros sobre el plano de la pared
    nt.links.new(coord.outputs["Object"], mapa.inputs["Vector"])
    ch = nt.nodes.new("ShaderNodeTexChecker")
    ch.inputs["Scale"].default_value = 1.6                                # cuadros de ~0,6 m
    ch.inputs["Color1"].default_value = (0.70, 0.06, 0.06, 1)
    ch.inputs["Color2"].default_value = (0.86, 0.86, 0.85, 1)
    nt.links.new(mapa.outputs["Vector"], ch.inputs["Vector"])
    nt.links.new(ch.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.6
    return m


def main():
    col = limpiar()
    M = Hg.materiales(E.mats())
    z = bpy.context.scene.get("cota_DIDA")
    if z is None:
        raise SystemExit("Primero hay que correr dida.py")
    ub = Hg.UBS["Bomberos"]
    # Bomberos da a la plataforma, más alta que la calle de los hangares: usa su propia cota (con la de la calle
    # quedaba 4 m hundido y la cámara del frente quedaba bajo tierra)
    z = E.aplanar(ub["este"], ub["norte"], "cota_bomberos", 50.0, 85.0)
    bomberos(M, col, z)
    pasto = E.pbr("Pasto_bomberos", "pasto", 2.5, (0.45, 0.95, 0.30), fade=(50.0, 80.0),
                  variacion=(0.05, (0.85, 0.75, 0.45)))
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, radius=80.0, segments=96)
    ob = E.objeto("Pasto_bomberos", bm, [pasto], None, col)
    ob.location = (ub["este"], ub["norte"] - 10.0, z + 0.01)
    bpy.ops.wm.save_mainfile()
    print("Bomberos listos")


if __name__ == "__main__":
    main()
