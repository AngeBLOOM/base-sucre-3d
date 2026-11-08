"""Departamento de Combustible y el hangarcito azul (quonset «21»). Se corre después de bomberos.py y antes de
vias.py:

    blender --background BaseSucre.blend --python combustible_azul.py

Fotos: COMBUSTIBLE BASE SUCRE, COMBUSTIBLE DE LA BASE, HANGARSITO AZUL, FIN DEL HANGAR AZULITO y los cuadros del
video 2 (referencias/video2_cuadros t_005, t_006, t_019 a t_021). Ubicación: datos/ubicaciones.json.
Mismo marco que los demás: el frente mira hacia -Y, X a lo ancho, Y hacia el fondo, Z = 0 en el suelo.
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
import bomberos as Bo  # noqa: E402  (solo para el material a cuadros)

rnd = E.random.Random(21)


def limpiar():
    col = bpy.data.collections.get("Combustible_Azul")
    if col:
        for ob in list(col.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.collections.remove(col)
    col = bpy.data.collections.new("Combustible_Azul")
    bpy.context.scene.collection.children.link(col)
    return col


def rejilla_bloques(bm, x, y, z, w, h, mi, sale=-1):
    """Paño de bloques de ventilación (cuadrícula de huecos), como los de la foto de Combustible."""
    E.caja(bm, (x, y + sale * 0.02, z), (w, 0.04, h), mi)
    n, m = int(w / 0.35), int(h / 0.3)
    for i in range(n + 1):
        E.caja(bm, (x - w / 2 + i * w / n, y + sale * 0.05, z), (0.06, 0.05, h), mi + 1)
    for j in range(m + 1):
        E.caja(bm, (x, y + sale * 0.05, z + j * h / m), (w, 0.05, 0.06), mi + 1)


# ----------------------------------------------------------------------------------- Combustible
def combustible(M, col, z):
    ub = Hg.UBS["Combustible"]
    p = Hg.origen("Combustible_origen", ub, col, z)
    W, D, H = ub["ancho"], ub["fondo"], 4.1
    sucio = E.pbr("Friso_blanco_gastado", "friso", 3.0, pintura=(0.82, 0.83, 0.84))
    bm = bmesh.new()
    E.caja(bm, (0, D / 2, 0), (W, D, H), 0)
    E.objeto("Combustible_volumen", bm, [sucio], p, col)
    # techo de lámina a un agua, bajando hacia atrás, con alero y bajantes
    bm = bmesh.new()
    bm.faces.new([bm.verts.new(v) for v in ((-W / 2 - 0.5, -0.6, H + 0.35), (W / 2 + 0.5, -0.6, H + 0.35),
                                            (W / 2 + 0.5, D + 0.6, H - 0.05), (-W / 2 - 0.5, D + 0.6, H - 0.05))])
    E.objeto("Combustible_techo", bm, [M["lamina_techo"]], p, col)
    bm = bmesh.new()
    E.caja(bm, (0, -0.62, H + 0.2), (W + 1.0, 0.06, 0.2), 0)                      # fascia
    for x in (-W / 2 + 0.6, W / 2 - 0.6):
        E.cilindro(bm, (x, -0.12, 0), 0.05, 0.05, H + 0.2, 0, 8)                # bajantes
    for x in (-W / 2 + 4.0, -W / 2 + 9.5):
        E.caja(bm, (x, -0.2, H - 0.4), (0.12, 0.4, 0.12), 0)                     # soportes del alero
    E.objeto("Combustible_fascia", bm, [M["poste"]], p, col)
    # fachada: dos paños de ventilación arriba, aires, ventana con reja, puerta, zócalo y letrero
    bm = bmesh.new()
    rejilla_bloques(bm, -W / 2 + 2.4, 0.0, 2.75, 2.6, 0.9, 0)
    rejilla_bloques(bm, -W / 2 + 8.0, 0.0, 2.75, 2.6, 0.9, 0)
    E.objeto("Combustible_rejillas", bm, [M["oscuro"], sucio], p, col)
    bm = bmesh.new()
    for x in (-W / 2 + 5.0, -W / 2 + 10.4):
        E.caja(bm, (x, -0.35, 2.35), (0.85, 0.32, 0.55), 0)
        E.cilindro(bm, (x - 0.15, -0.52, 2.62), 0.18, 0.18, 0.02, 1, 18, (math.pi / 2, 0, 0))
        E.caja(bm, (x + 0.3, -0.12, 1.6), (0.04, 0.04, 0.8), 2)                  # tubería de condensado
    E.objeto("Combustible_aires", bm, [M["aire"], M["oscuro"], M["poste"]], p, col)
    bm = bmesh.new()
    Hg.ventana_reja(bm, W / 2 - 4.8, -0.03, 1.5, 1.3, 1.0, 0, 1)
    E.caja(bm, (W / 2 - 2.2, -0.04, 0), (1.1, 0.08, 2.3), 2)
    E.objeto("Combustible_ventanas", bm, [M["vidrio"], M["reja"], E.material("Puerta_gris", (0.42, 0.44, 0.47), 0.5, 0.4)],
             p, col)
    bm = bmesh.new()
    E.caja(bm, (0, -0.05, 0), (W + 0.1, 0.08, 0.35), 0)
    E.objeto("Combustible_zocalo", bm, [M["gris_zocalo"]], p, col)
    negro = E.material("Letras_negras_comb", (0.03, 0.03, 0.035), 0.5)
    E.texto("DPTO. COMBUSTIBLE", 0.36, negro, p, col, (W / 2 - 3.6, -0.06, 3.55), (math.pi / 2, 0, 0), extr=0.015)
    E.texto("BASE SUCRE", 0.42, negro, p, col, (W / 2 - 3.6, -0.06, 3.05), (math.pi / 2, 0, 0), extr=0.015)
    # esquina a cuadros rojos y blancos (vista en el video desde la plataforma)
    bm = bmesh.new()
    E.caja(bm, (W / 2 + 0.03, D / 2, 0.4), (0.04, D, 3.2), 0)
    E.caja(bm, (W / 2 - 0.6, D + 0.03, 0.4), (1.2, 0.04, 3.2), 0)
    E.objeto("Combustible_cuadros", bm, [Bo.mat_cuadros()], p, col)
    # cerca de tubo de la pista detrás (postes pintados a franjas y dos tubos horizontales)
    bm, bf = bmesh.new(), bmesh.new()
    L = 90.0
    for k in range(int(L / 4.0) + 1):
        x = -L / 2 + k * 4.0
        E.cilindro(bm, (x, D + 9.0, 0), 0.07, 0.07, 1.25, 0, 8)
        E.cilindro(bf, (x, D + 9.0, 0.55), 0.072, 0.072, 0.25, 0, 8)
    for zz in (0.65, 1.15):
        E.cilindro(bm, (-L / 2, D + 9.0, zz), 0.045, 0.045, L, 0, 8, (0, math.pi / 2, 0))
    E.objeto("Cerca_pista", bm, [E.material("Tubo_blanco", (0.82, 0.82, 0.80), 0.5, 0.3)], p, col)
    E.objeto("Cerca_pista_franjas", bf, [E.material("Tubo_negro", (0.04, 0.04, 0.04), 0.5)], p, col)
    # losa de concreto delante (la calle de la foto) y tierra con grama rala junto a la pared
    bm = bmesh.new()
    E.caja(bm, (0, -8.0, 0), (W + 30, 14.0, 0.1), 0)
    E.objeto("Combustible_losa", bm, [bpy.data.materials.get("Concreto_gastado") or M["concreto_patio"]], p, col)
    E.camara("Cam_Combustible", p, col, (-2.0, -16.0, 1.6), (1.5, 0.0, 2.2), 26)
    return p


# ----------------------------------------------------------------------------------- hangarcito azul
def hangarcito(M, col, z):
    ub = Hg.UBS["Hangarcito azul"]
    p = Hg.origen("Hangarcito_origen", ub, col, z)
    S, L = ub["ancho"], ub["fondo"]
    perfil = Hg.arco(S / 2, 0.4, S / 2 - 0.2, 32)
    azul = E.pbr("Lamina_azul_claro", "lamina_gastada", 1.6, metal=0.25, pintura=(0.48, 0.66, 0.82))
    bm = bmesh.new()
    an = [[bm.verts.new((x, y, zz)) for x, zz in perfil] for y in (0.0, L)]
    for k in range(len(perfil) - 1):
        bm.faces.new((an[0][k], an[0][k + 1], an[1][k + 1], an[1][k]))
    E.caja(bm, (0, L / 2, 0), (S, L, 0.4), 0)                                    # muro bajo de arranque
    E.objeto("Hangarcito_boveda", bm, [azul], p, col)
    bm = bmesh.new()                                                              # testeros planos
    for y in (0.0, L):
        bm.faces.new([bm.verts.new((x, y, zz)) for x, zz in perfil])
    E.objeto("Hangarcito_muros", bm, [azul], p, col)
    # costillas de la bóveda (juntas de las láminas)
    bm = bmesh.new()
    for k in range(1, int(L / 2.4)):
        y = k * 2.4
        for a, b in zip(perfil, perfil[1:]):
            m = Vector(((a[0] + b[0]) / 2 * 1.006, y, (a[1] + b[1]) / 2 * 1.006))
            ang = math.atan2(b[1] - a[1], b[0] - a[0])
            E.caja(bm, (m.x, m.y, m.z - 0.02), (math.hypot(b[0] - a[0], b[1] - a[1]) + 0.02, 0.07, 0.04), 0,
                   (0, -ang, 0))
    E.objeto("Hangarcito_costillas", bm, [azul], p, col)
    # banda de ventanas en los dos costados, donde la bóveda casi es vertical, con aleros de lámina
    bm, ba = bmesh.new(), bmesh.new()
    for s in (-1, 1):
        for k in range(8):
            y = 2.5 + k * 3.0
            x = s * (S / 2 - 0.25)
            E.caja(bm, (x, y, 1.55), (0.08, 2.4, 0.75), 0, (0, s * math.radians(-12), 0))
            for j in range(1, 4):
                E.caja(bm, (x + s * 0.02, y - 1.2 + j * 0.6, 1.55), (0.06, 0.05, 0.75), 1, (0, s * math.radians(-12), 0))
    for y, zz in ((0.0, 3.2), (0.0, 1.9)):                                       # aleritos del frente
        E.caja(ba, (-1.8, -0.35, zz), (1.4, 0.7, 0.05), 0, (math.radians(25), 0, 0))
    E.objeto("Hangarcito_ventanas", bm, [M["vidrio"], M["poste"]], p, col)
    E.objeto("Hangarcito_aleros", ba, [E.material("Alero_beige", (0.80, 0.70, 0.52), 0.6)], p, col)
    # frente: portón corredizo, puerta pequeña, número «21» y un escudo redondo
    bm = bmesh.new()
    E.caja(bm, (0.9, -0.06, 0), (3.6, 0.1, 3.2), 0)
    E.caja(bm, (0.9, -0.12, 3.2), (4.0, 0.12, 0.12), 1)
    E.caja(bm, (-2.8, -0.05, 0), (0.95, 0.08, 2.2), 2)
    E.objeto("Hangarcito_porton", bm, [azul, M["poste"], M["oscuro"]], p, col)
    E.texto("21", 0.42, M["negro"] if "negro" in M else E.material("Negro_21", (0.02, 0.02, 0.02), 0.5), p, col,
            (0.9, -0.15, 3.65), (math.pi / 2, 0, 0), extr=0.01)
    bm = bmesh.new()
    E.caja(bm, (0.9, -0.12, 3.66), (0.8, 0.02, 0.45), 0)
    E.cilindro(bm, (2.6, -0.1, 2.6), 0.38, 0.38, 0.03, 1, 28, (math.pi / 2, 0, 0))
    E.objeto("Hangarcito_placas", bm, [M["blanco"], M["dorado"]], p, col)
    # caseta de bloques calados al lado, gabinete eléctrico rojo y torre del tanque de agua
    bm = bmesh.new()
    E.caja(bm, (S / 2 + 4.0, 6.0, 0), (5.0, 6.0, 3.2), 0)
    E.caja(bm, (S / 2 + 4.0, 6.0, 3.2), (5.3, 6.3, 0.2), 0)
    E.objeto("Hangarcito_caseta", bm, [M["blanco"]], p, col)
    bm = bmesh.new()                                                              # bloques calados de la caseta
    for y in (4.6, 7.4):
        E.caja(bm, (S / 2 + 1.47, y, 0.8), (0.04, 1.2, 2.0), 0)
        for i in range(5):
            E.caja(bm, (S / 2 + 1.44, y - 0.6 + i * 0.3, 0.8), (0.05, 0.05, 2.0), 1)
        for j in range(8):
            E.caja(bm, (S / 2 + 1.44, y, 0.8 + j * 0.28), (0.05, 1.2, 0.05), 1)
    E.objeto("Hangarcito_caseta_calados", bm, [M["oscuro"], M["blanco"]], p, col)
    bm = bmesh.new()
    E.caja(bm, (S / 2 + 2.0, 1.6, 0), (1.2, 0.7, 1.3), 0)
    E.objeto("Hangarcito_gabinete", bm, [E.material("Gabinete_rojo", (0.55, 0.12, 0.14), 0.5, 0.3)], p, col)
    bm = bmesh.new()
    E.caja(bm, (S / 2 + 6.0, 12.0, 0), (2.6, 2.6, 11.0), 0)
    E.caja(bm, (S / 2 + 6.0, 12.0, 11.0), (4.2, 4.2, 3.2), 0)
    E.caja(bm, (S / 2 + 6.0, 12.0, 14.2), (4.5, 4.5, 0.25), 0)
    E.objeto("Hangarcito_torre_agua", bm, [M["blanco"]], p, col)
    # explanada de tierra y concreto delante, donde se empoza el agua
    bm = bmesh.new()
    E.caja(bm, (0, -9.0, 0), (S + 12, 18.0, 0.06), 0)
    E.objeto("Hangarcito_explanada", bm, [E.con_ruido(bpy.data.materials.get("Tierra_explanada")
                                                      or bpy.data.materials.new("Tierra_explanada"),
                                                      (0.36, 0.30, 0.22), (0.55, 0.50, 0.42), 0.4, 0.2)], p, col)
    E.camara("Cam_Hangarcito", p, col, (-9.0, -22.0, 1.6), (0.5, 6.0, 2.5), 26)
    return p


def main():
    col = limpiar()
    M = Hg.materiales(E.mats())
    M["negro"] = bpy.data.materials.get("Helice_negra") or E.material("Helice_negra", (0.02, 0.02, 0.02), 0.35, 0.5)
    z = bpy.context.scene.get("cota_DIDA")
    if z is None:
        raise SystemExit("Primero hay que correr dida.py")
    # Combustible queda al borde de la plataforma, más alta que la calle de los hangares: usa su propia cota
    ub = Hg.UBS["Combustible"]
    zc = E.aplanar(ub["este"], ub["norte"], "cota_combustible", 25.0, 45.0)
    ub = Hg.UBS["Hangarcito azul"]
    E.aplanar(ub["este"], ub["norte"], "cota_hangarcito", 40.0, 70.0, z0=z)
    print("cotas: calle", round(z, 2), "| combustible", round(zc, 2))
    combustible(M, col, zc)
    hangarcito(M, col, z)
    pasto = E.pbr("Pasto_hangarcito", "pasto", 2.5, (0.45, 0.95, 0.30), fade=(40.0, 65.0),
                  variacion=(0.05, (0.85, 0.75, 0.45)))
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, radius=65.0, segments=96)
    ub = Hg.UBS["Hangarcito azul"]
    ob = E.objeto("Pasto_hangarcito", bm, [pasto], None, col)
    ob.location = (ub["este"], ub["norte"], z + 0.01)
    bpy.ops.wm.save_mainfile()
    print("Combustible y hangarcito azul listos")


if __name__ == "__main__":
    main()
