"""La entrada vista desde adentro y la plaza de la isla (fotos que ella mandó el 2026-11-05).
Se corre justo después de entrada.py, en el mismo marco Entrada_origen (+Y = hacia adentro, +X = derecha al entrar):

    blender --background BaseSucre.blend --python entrada_adentro.py

- Cara de adentro de la portada: mural geométrico de triángulos negro, gris y gris claro con líneas blancas,
  ventanas con reja blanca, puerta blanca de persiana, aires de ventana y split; el techo rojo sigue en un alero hondo
  con fascia blanca y el cielo raso del alero y de los pasos lleva los mismos triángulos y lámparas cuadradas.
- Pegado al extremo -X de la portada y corriendo hacia adentro: el edificio crema de un piso (techo de lámina
  oxidada a dos aguas, ventanitas altas con reja, bajantes, zócalo oscuro, puerta metálica, tres placas redondas y la
  bandera pintada). La pancarta política de la foto NO se modela.
- En el extremo +X: el anexo blanco más bajo (huella OSM), con ventana de reja y su aire.
- La plaza: la isla en triángulo entre la vía recta (a la DIDA) y la diagonal (a mano derecha, al comedor), con
  brocal gris, el busto dorado sobre pedestal negro, once astas blancas (una mucho más alta) en abanico; los setos
  amarillos, crotos y palmitas los siembra entorno.py con los puntos que deja aquí (no hay modelos de esas plantas).
- Vías de adentro (las de OSM quedan cortadas en los 110 m alrededor de la portada) y el estacionamiento del patio
  con rayas blancas y reflectores rojos.
Las posiciones salen del satélite y de OSM (corridas 8 m para casar con la portada modelada).
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

rnd = E.random.Random(2611)
F2 = E.FONDO / 2                        # cara de adentro de la portada (y = +6)
XB0, XB1 = E.X_PASO + E.A_PASO, E.X_EXT  # bloques: |x| de 8 a 21
HM = 5.45                               # alto del mural (hasta el cielo raso del alero)
XA = 19.0                               # el anexo +X empieza aquí
# vías de adentro (marco local)
DIAG = (Vector((0.0, 36.0)), Vector((95.0, 93.0)))      # a mano derecha, hacia el comedor
RAMAL = [Vector((0.0, 101.0)), Vector((20.0, 80.0)), Vector((48.0, 66.0))]
ISLA = [Vector((5.0, 44.3)), Vector((41.2, 66.0)), Vector((5.0, 92.4))]


def limpiar():
    for ob in [o for o in bpy.data.objects if o.name.startswith("Adentro_") or o.name.startswith("Cam_Adentro")
               or o.name.startswith("Cam_Plaza")]:
        bpy.data.objects.remove(ob, do_unlink=True)


def M_():
    g = bpy.data.materials.get
    return {"blanco": g("Pared_blanca"), "gris": g("Pared_gris"), "vidrio": g("Vidrio_oscuro"),
            "granito": g("Granito_negro"), "pintura": g("Pintura_blanca"), "asfalto": g("Asfalto_calle"),
            "acera": g("Acera"), "luz": g("Luz_farol"), "poste": g("Poste_gris"), "pasto": g("Pasto"),
            "dorado": E.material("Bronce_dorado", (0.80, 0.55, 0.20), 0.28, 1.0)}


# ----------------------------------------------------------------------------------- mural
def mural(bm, u0, u1, v0, v1, punto, semilla, gap=0.05):
    """Triángulos grandes en zigzag de borde a borde, algunos partidos en dos, separados por líneas (el fondo
    blanco queda a la vista). punto(u, v) -> coordenada 3D. Material 0/1/2 = negro, gris, gris claro."""
    r = E.random.Random(semilla)
    arriba, abajo = [u0], [u0 + r.uniform(1.0, 2.2)]
    while arriba[-1] < u1:
        arriba.append(arriba[-1] + r.uniform(2.6, 4.6))
    while abajo[-1] < u1:
        abajo.append(abajo[-1] + r.uniform(2.6, 4.6))
    arriba[-1] = abajo[-1] = u1
    abajo = [u0] + abajo
    tris = []
    i = j = 0
    while i < len(arriba) - 1 or j < len(abajo) - 1:
        if j < len(abajo) - 1 and (i >= len(arriba) - 1 or abajo[j + 1] <= arriba[i + 1]):
            tris.append([(abajo[j], v0), (abajo[j + 1], v0), (arriba[i], v1)])
            j += 1
        else:
            tris.append([(arriba[i], v1), (abajo[j], v0), (arriba[i + 1], v1)])
            i += 1
    polis = []
    for t in tris:
        if r.random() < 0.4:                                  # partido por una línea de un vértice al lado opuesto
            k = r.randrange(3)
            a, b, c = t[k], t[(k + 1) % 3], t[(k + 2) % 3]
            f = r.uniform(0.35, 0.65)
            m = (b[0] + (c[0] - b[0]) * f, b[1] + (c[1] - b[1]) * f)
            polis += [[a, b, m], [a, m, c]]
        else:
            polis.append(t)
    previo = -1
    for pl in polis:
        cu = sum(p[0] for p in pl) / len(pl)
        cv = sum(p[1] for p in pl) / len(pl)
        q = []
        for u, v in pl:
            d = math.hypot(u - cu, v - cv)
            s = max(0.0, 1.0 - gap / d) if d > 1e-6 else 0.0
            q.append((cu + (u - cu) * s, cv + (v - cv) * s))
        mi = r.choice([k for k in (0, 1, 2) if k != previo])
        previo = mi
        f = bm.faces.new([bm.verts.new(punto(u, v)) for u, v in q])
        f.material_index = mi


def mats_mural():
    return [E.material("Mural_negro", (0.022, 0.022, 0.025), 0.6),
            E.material("Mural_gris", (0.13, 0.135, 0.14), 0.6),
            E.material("Mural_gris_claro", (0.40, 0.40, 0.39), 0.65)]


# ----------------------------------------------------------------------------------- cara de adentro
def ventana_reja(bm, x, y, z0, w=1.05, h=1.15):
    """Vidrio oscuro (mi 0) con marco y reja blancos (mi 1), en la pared que mira a +Y."""
    E.caja(bm, (x, y + 0.02, z0), (w, 0.03, h), 0)
    for xx in (x - w / 2, x + w / 2):
        E.caja(bm, (xx, y + 0.05, z0 - 0.04), (0.07, 0.06, h + 0.08), 1)
    for zz in (z0 - 0.04, z0 + h):
        E.caja(bm, (x, y + 0.05, zz), (w + 0.07, 0.06, 0.06), 1)
    for k in (1, 2, 3):
        E.caja(bm, (x - w / 2 + k * w / 4, y + 0.09, z0), (0.03, 0.03, h), 1)
    for k in (1, 2):
        E.caja(bm, (x, y + 0.09, z0 + k * h / 3), (w, 0.03, 0.03), 1)


def cara_adentro(M, padre, col):
    y = F2
    # forro blanco que pone al ras la pared de los bloques con el friso, y el mural encima
    bm = bmesh.new()
    for s in (-1, 1):
        x0, x1 = sorted((s * XB0, s * (XA if s > 0 else XB1)))
        E.caja(bm, (0.5 * (x0 + x1), y + 0.16, 0), (x1 - x0, 0.32, HM), 0)
    E.objeto("Adentro_forro", bm, [M["blanco"]], padre, col)
    bm = bmesh.new()
    for s, sem in ((-1, 11), (1, 12)):
        x0, x1 = sorted((s * XB0, s * (XA if s > 0 else XB1)))
        mural(bm, x0, x1, 0.0, HM, lambda u, v: (u, y + 0.335, v), sem)
    # foto de frente (2026-11-07): la cara de AFUERA también lleva el mural de triángulos bajo los paneles
    for s, sem in ((-1, 21), (1, 22)):
        x0, x1 = sorted((s * XB0, s * XB1))
        mural(bm, x0, x1, 0.0, E.H_PB - 0.05, lambda u, v: (u, -F2 - 0.012, v), sem)
    E.objeto("Adentro_mural", bm, mats_mural(), padre, col)
    # ventanas con reja, puerta de persiana, aires (foto desde adentro: dos ventanas, la puerta y un split a la
    # izquierda mirando hacia afuera = +X; cinco ventanas, aires de ventana y una puerta a la derecha = -X)
    bm = bmesh.new()
    yv = y + 0.34
    for x in (17.0, 14.6, -9.8, -13.6, -15.6, -20.0):
        ventana_reja(bm, x, yv, 1.45)
    E.objeto("Adentro_ventanas", bm, [M["vidrio"], M["blanco"]], padre, col)
    bm = bmesh.new()
    for x in (10.8, -18.0):                                   # puertas de persiana blanca
        E.caja(bm, (x, yv + 0.03, 0.0), (0.95, 0.05, 2.1), 0)
        for k in range(14):
            E.caja(bm, (x, yv + 0.07, 0.15 + k * 0.13), (0.85, 0.03, 0.05), 0)
    E.objeto("Adentro_puertas", bm, [E.material("Puerta_blanca", (0.80, 0.80, 0.78), 0.5, 0.2)], padre, col)
    bm = bmesh.new()
    for x, zz in ((-9.8, 0.85), (-13.6, 0.85), (-15.6, 0.85), (14.6, 0.85)):     # aires de ventana
        E.caja(bm, (x, yv, zz), (0.62, 0.42, 0.42), 0)
        for k in range(5):
            E.caja(bm, (x, yv + 0.43, zz + 0.06 + k * 0.07), (0.5, 0.02, 0.02), 1)
    E.caja(bm, (17.0, yv, 0.8), (0.82, 0.3, 0.56), 0)                            # split bajo la ventana
    E.cilindro(bm, (17.12, yv + 0.31, 1.08), 0.2, 0.2, 0.02, 1, 18, (-math.pi / 2, 0, 0))
    E.objeto("Adentro_aires", bm, [E.material("Aire_acondicionado", (0.80, 0.80, 0.78), 0.5),
                                    E.material("Rejilla_aire", (0.15, 0.15, 0.16), 0.6)], padre, col)


def techo_adentro(M, padre, col):
    """El techo rojo de la portada sigue hacia adentro en un alero hondo, con fascia blanca y cielo raso de
    triángulos con lámparas cuadradas."""
    Lr = 2 * E.X_EXT + 2.0
    ze = E.H_PB + E.H_FRISO
    pend = 1.9 / ((E.FONDO + 2.0) / 2)
    y0, y1 = F2 + 1.0, F2 + 3.6
    z1 = ze - (y1 - y0) * pend
    bm = bmesh.new()
    bm.faces.new([bm.verts.new(v) for v in ((-Lr / 2, y0, ze), (Lr / 2, y0, ze), (Lr / 2, y1, z1), (-Lr / 2, y1, z1))])
    E.objeto("Adentro_alero_techo", bm, [bpy.data.materials.get("Techo_rojo_lamina")], padre, col)
    bm = bmesh.new()
    E.caja(bm, (0, y1 + 0.03, z1 - 0.32), (Lr + 0.1, 0.06, 0.36), 0)
    E.objeto("Adentro_fascia", bm, [M["blanco"]], padre, col)
    zs = HM
    bm = bmesh.new()
    ys = F2 + 0.33
    bm.faces.new([bm.verts.new(v) for v in ((-Lr / 2, ys, zs), (Lr / 2, ys, zs), (Lr / 2, y1, zs), (-Lr / 2, y1, zs))])
    E.objeto("Adentro_cielo_raso", bm, [M["blanco"]], padre, col)
    bm = bmesh.new()
    mural(bm, -Lr / 2, Lr / 2, F2 + 0.35, y1 - 0.05, lambda u, v: (u, v, zs - 0.012), 31, 0.06)
    # cielo raso de los dos pasos (bajo el friso)
    for s, sem in ((-1, 32), (1, 33)):
        x0, x1 = sorted((s * E.X_PASO, s * XB0))
        mural(bm, x0, x1, -F2, F2, lambda u, v, z=E.H_PB - 0.07: (u, v, z), sem, 0.06)
    E.objeto("Adentro_cielo_mural", bm, mats_mural(), padre, col)
    bm = bmesh.new()
    for x in range(-18, 19, 6):
        E.caja(bm, (x + 0.0, F2 + 2.0, zs - 0.06), (0.5, 0.5, 0.04), 0)
    for s in (-1, 1):
        for yy in (-3.0, 3.0):
            E.caja(bm, (s * (E.X_PASO + E.A_PASO / 2), yy, E.H_PB - 0.12), (0.5, 0.5, 0.04), 0)
    E.objeto("Adentro_lamparas", bm, [M["luz"]], padre, col)


# ----------------------------------------------------------------------------------- edificios de los lados
def edificio_crema(M, padre, col):
    """Un piso, pegado al extremo -X y corriendo hacia adentro; fachada mirando a +X (al patio)."""
    x0, x1, y0, y1 = -31.0, -21.0, F2 + 1.5, F2 + 27.5
    H, Hc = 3.5, 5.0
    crema = E.pbr("Friso_crema_adentro", "friso", 3.0, pintura=(0.80, 0.76, 0.62))
    bm = bmesh.new()
    E.caja(bm, (0.5 * (x0 + x1), 0.5 * (y0 + y1), 0), (x1 - x0, y1 - y0, H), 0)
    xm = 0.5 * (x0 + x1)
    for yy in (y0, y1):                                       # testeros
        bm.faces.new([bm.verts.new(v) for v in ((x0, yy, H), (x1, yy, H), (xm, yy, Hc))])
    E.objeto("Adentro_dgcim_muros", bm, [crema], padre, col)
    bm = bmesh.new()
    E.caja(bm, (x1 + 0.02, 0.5 * (y0 + y1), 0), (0.06, y1 - y0, 0.55), 0)       # zócalo oscuro
    E.objeto("Adentro_dgcim_zocalo", bm, [E.material("Zocalo_negro", (0.04, 0.04, 0.045), 0.6)], padre, col)
    oxidada = E.pbr("Lamina_oxidada_adentro", "lamina_oxidada", 2.0, metal=0.2, tinte=(0.75, 0.55, 0.45))
    bm = bmesh.new()
    for xa, xb, za, zb in ((x1 + 0.9, xm, H - 0.25, Hc), (xm, x0 - 0.9, Hc, H - 0.25)):
        bm.faces.new([bm.verts.new(v) for v in ((xa, y0 - 0.6, za), (xa, y1 + 0.6, za), (xb, y1 + 0.6, zb),
                                                (xb, y0 - 0.6, zb))])
    E.objeto("Adentro_dgcim_techo", bm, [oxidada], padre, col)
    bm = bmesh.new()                                          # canal y fascia
    E.caja(bm, (x1 + 0.92, 0.5 * (y0 + y1), H - 0.45), (0.12, y1 - y0 + 1.2, 0.22), 0)
    E.objeto("Adentro_dgcim_canal", bm, [E.material("Canal_gris", (0.45, 0.46, 0.47), 0.4, 0.5)], padre, col)
    # ventanitas altas con reja negra, bajantes, puerta metálica, placas redondas y la bandera pintada
    bv, br = bmesh.new(), bmesh.new()
    y = y0 + 2.0
    while y < y1 - 2.5:
        E.caja(bv, (x1 + 0.02, y, 2.15), (0.04, 0.75, 0.62), 0)
        for k in (-1, 0, 1):
            E.caja(br, (x1 + 0.06, y + k * 0.22, 2.15), (0.03, 0.03, 0.62), 0)
        E.caja(br, (x1 + 0.06, y, 2.45), (0.03, 0.75, 0.03), 0)
        y += 1.95
    E.objeto("Adentro_dgcim_ventanas", bv, [M["vidrio"]], padre, col)
    E.objeto("Adentro_dgcim_rejas", br, [E.material("Reja_negra", (0.03, 0.03, 0.03), 0.5, 0.5)], padre, col)
    bm = bmesh.new()
    for yy in (y0 + 6.5, y0 + 14.0, y1 - 4.5):
        E.cilindro(bm, (x1 + 0.5, yy, 0.0), 0.06, 0.06, H - 0.35, 0, 8)
    E.objeto("Adentro_dgcim_bajantes", bm, [E.material("Canal_gris", (0.45, 0.46, 0.47), 0.4, 0.5)], padre, col)
    bm = bmesh.new()
    E.caja(bm, (x1 + 0.03, y1 - 2.2, 0.0), (0.06, 1.5, 2.5), 0)
    E.objeto("Adentro_dgcim_puerta", bm, [E.material("Puerta_metal_negra", (0.03, 0.035, 0.04), 0.45, 0.5)],
             padre, col)
    bm = bmesh.new()
    for k, yy in enumerate((y0 + 16.5, y0 + 18.6, y0 + 20.7)):
        E.cilindro(bm, (x1 + 0.04, yy, 1.75), 0.48, 0.48, 0.05, 0, 28, (0, math.pi / 2, 0))
        E.cilindro(bm, (x1 + 0.08, yy, 1.75), 0.36, 0.36, 0.03, 1 + k % 2, 28, (0, math.pi / 2, 0))
    E.objeto("Adentro_dgcim_placas", bm, [E.material("Placa_blanca", (0.85, 0.85, 0.83), 0.5),
                                           E.material("Placa_roja", (0.50, 0.05, 0.04), 0.5),
                                           E.material("Azul_emblema", (0.04, 0.12, 0.45), 0.4)], padre, col)
    bm = bmesh.new()                                          # bandera de Venezuela pintada (3 franjas)
    for k, zz in enumerate((0.85, 1.35, 1.85)):
        E.caja(bm, (x1 + 0.03, y0 + 10.5, zz), (0.03, 2.3, 0.5), k)
    E.objeto("Adentro_dgcim_bandera", bm, [E.material("Bandera_rojo", (0.55, 0.03, 0.04), 0.5),
                                            E.material("Bandera_azul", (0.02, 0.06, 0.40), 0.5),
                                            E.material("Bandera_amarillo", (0.90, 0.68, 0.03), 0.5)], padre, col)
    bm = bmesh.new()                                          # franja de césped con brocal
    E.caja(bm, (x1 + 1.1, 0.5 * (y0 + y1), 0.0), (2.1, y1 - y0, 0.12), 0)
    E.objeto("Adentro_dgcim_cesped", bm, [M["pasto"]], padre, col)
    bm = bmesh.new()
    E.caja(bm, (x1 + 2.2, 0.5 * (y0 + y1), 0.0), (0.18, y1 - y0, 0.2), 0)
    E.objeto("Adentro_dgcim_brocal", bm, [E.material("Brocal_gris", (0.30, 0.30, 0.31), 0.8)], padre, col)
    # cerca de malla con alambre de púas en la punta de adentro
    bm = bmesh.new()
    for x in (x1 + 0.5, x1 + 3.5, x1 + 6.5):
        E.cilindro(bm, (x, y1 + 1.0, 0.0), 0.04, 0.04, 2.4, 0, 8)
        E.caja(bm, (x, y1 + 1.0, 2.4), (0.04, 0.5, 0.04), 0, (0.6, 0, 0))
    E.objeto("Adentro_cerca", bm, [E.material("Galvanizado", (0.55, 0.56, 0.57), 0.35, 0.8)], padre, col)


def anexo_mas_x(M, padre, col):
    """Anexo blanco más bajo del extremo +X (huella OSM), con la ventana de reja que da al patio."""
    x0, x1, y0, y1 = XA, 27.0, F2 + 0.3, F2 + 17.0
    H = 3.4
    blanco = E.pbr("Friso_blanco_anexo", "friso", 3.0, pintura=(0.82, 0.83, 0.82))
    bm = bmesh.new()
    E.caja(bm, (0.5 * (x0 + x1), 0.5 * (y0 + y1), 0), (x1 - x0, y1 - y0, H), 0)
    E.objeto("Adentro_anexo_muros", bm, [blanco], padre, col)
    bm = bmesh.new()
    bm.faces.new([bm.verts.new(v) for v in ((x0 - 0.7, y0 - 0.2, H + 0.6), (x1 + 0.5, y0 - 0.2, H + 0.6),
                                            (x1 + 0.5, y1 + 0.6, H - 0.1), (x0 - 0.7, y1 + 0.6, H - 0.1))])
    E.objeto("Adentro_anexo_techo", bm, [bpy.data.materials.get("Techo_rojo_lamina")], padre, col)
    bm = bmesh.new()
    E.caja(bm, (x0 - 0.72, 0.5 * (y0 + y1), H - 0.1), (0.05, y1 - y0 + 0.8, 0.5), 0)
    E.objeto("Adentro_anexo_fascia", bm, [M["blanco"]], padre, col)
    bm = bmesh.new()
    for yy in (F2 + 4.0, F2 + 11.0):                          # ventanas con reja blanca en la cara -X
        E.caja(bm, (x0 - 0.02, yy, 1.45), (0.03, 1.05, 1.15), 0)
        for k in (1, 2, 3):
            E.caja(bm, (x0 - 0.07, yy - 0.525 + k * 0.2625, 1.45), (0.03, 0.03, 1.15), 1)
        for k in (0, 1, 2, 3):
            E.caja(bm, (x0 - 0.07, yy, 1.42 + k * 0.39), (0.03, 1.1, 0.04), 1)
    E.caja(bm, (x0 - 0.03, F2 + 7.5, 0.0), (0.05, 1.0, 2.2), 1)
    E.objeto("Adentro_anexo_vanos", bm, [M["vidrio"], M["blanco"]], padre, col)
    bm = bmesh.new()
    E.caja(bm, (x0 - 0.25, F2 + 4.0, 0.85), (0.42, 0.62, 0.42), 0)
    E.objeto("Adentro_anexo_aire", bm, [E.material("Aire_acondicionado", (0.80, 0.80, 0.78), 0.5)], padre, col)


# ----------------------------------------------------------------------------------- vías, patio y plaza
def cinta(bm, pts, ancho, z, mi=0):
    izq, der = [], []
    for i, p in enumerate(pts):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t.normalize()
        n = Vector((-t.y, t.x))
        izq.append(bm.verts.new((*(p + n * ancho / 2), z)))
        der.append(bm.verts.new((*(p - n * ancho / 2), z)))
    for k in range(len(pts) - 1):
        f = bm.faces.new((der[k], der[k + 1], izq[k + 1], izq[k]))
        f.material_index = mi


def tramo(a, b, paso=2.0):
    n = max(1, int((b - a).length / paso))
    return [a.lerp(b, k / n) for k in range(n + 1)]


def curva(pts, paso=2.0):
    out = []
    for a, b in zip(pts, pts[1:]):
        out += tramo(a, b, paso)[:-1]
    return out + [pts[-1]]


def suavizar_poligono(pts, r=5.0, n=8):
    """Esquinas redondeadas (la isla tiene el brocal en curva)."""
    out = []
    for i, p in enumerate(pts):
        a, c = pts[i - 1], pts[(i + 1) % len(pts)]
        da, dc = (a - p).normalized(), (c - p).normalized()
        pa, pc = p + da * r, p + dc * r
        for k in range(n + 1):
            t = k / n
            q = pa.lerp(p, t).lerp(p.lerp(pc, t), t)              # bezier cuadrática
            out.append(q)
    return out


def vias_y_patio(M, padre, col):
    asf = M["asfalto"]
    bm = bmesh.new()
    # patio entre la portada, el edificio crema, el anexo y la isla
    E.caja(bm, (-1.0, 0.5 * (F2 + 42.0), 0.0), (41.0, 42.0 - F2, 0.04), 0)
    cinta(bm, tramo(Vector((0.0, 40.0)), Vector((0.0, 118.0))), 8.0, 0.035)
    cinta(bm, tramo(*DIAG), 8.0, 0.037)
    cinta(bm, curva(RAMAL), 7.0, 0.036)
    E.objeto("Adentro_vias", bm, [asf], padre, col)
    # pintura: bordes de las vías, puestos del patio y reflectores rojos
    bm, br = bmesh.new(), bmesh.new()
    for s in (-1, 1):
        cinta(bm, [p + Vector((s * 3.7, 0)) for p in tramo(Vector((0.0, 44.0)), Vector((0.0, 116.0)))], 0.14, 0.05)
    d = (DIAG[1] - DIAG[0]).normalized()
    n = Vector((-d.y, d.x))
    for s in (-1, 1):
        cinta(bm, [p + n * (s * 3.7) for p in tramo(DIAG[0] + d * 6.0, DIAG[1])], 0.14, 0.052)
    for k in range(9):                                        # puestos frente al edificio crema
        yy = F2 + 4.0 + k * 2.7
        E.caja(bm, (-16.8, yy, 0.04), (5.0, 0.12, 0.012), 0)
        E.caja(br, (-14.2, yy, 0.04), (0.12, 0.12, 0.03), 0)
    for k in range(8):                                        # hilera central del patio
        xx = -6.0 + k * 2.7
        E.caja(bm, (xx, 24.0, 0.04), (0.12, 5.0, 0.012), 0)
        E.caja(br, (xx, 21.3, 0.04), (0.12, 0.12, 0.03), 0)
    E.caja(bm, (3.4, 24.0, 0.04), (19.6, 0.12, 0.012), 0)
    pts = tramo(Vector((4.6, 14.0)), Vector((4.6, 40.0)), 4.0)   # línea de carril con ojos de gato
    for p in pts:
        E.caja(bm, (p.x, p.y, 0.04), (0.14, 2.6, 0.012), 0)
        E.caja(br, (p.x, p.y + 1.7, 0.04), (0.12, 0.12, 0.03), 0)
    E.objeto("Adentro_pintura", bm, [M["pintura"]], padre, col)
    E.objeto("Adentro_reflectores", br, [E.material("Reflector_rojo", (0.6, 0.03, 0.02), 0.3, 0.2)], padre, col)
    # flecha de seguir recto y cruzar a la derecha en el carril de entrada (foto desde adentro)
    bm = bmesh.new()
    x, y = E.X_PASO + E.A_PASO / 2, F2 + 11.0
    E.caja(bm, (x, y, 0.04), (0.35, 4.0, 0.012), 0)
    bm.faces.new([bm.verts.new(v) for v in ((x - 0.75, y + 4.0, 0.054), (x + 0.75, y + 4.0, 0.054),
                                            (x, y + 5.4, 0.054))])
    E.caja(bm, (x + 0.9, y + 1.8, 0.04), (1.8, 0.3, 0.012), 0)
    bm.faces.new([bm.verts.new(v) for v in ((x + 1.8, y + 1.25, 0.054), (x + 1.8, y + 2.35, 0.054),
                                            (x + 2.8, y + 1.8, 0.054))])
    E.objeto("Adentro_flecha", bm, [M["pintura"]], padre, col)


def plaza(M, padre, col):
    borde = suavizar_poligono(ISLA, 6.0)
    c = sum(ISLA, Vector((0, 0))) / 3
    bm = bmesh.new()                                          # brocal gris oscuro
    for a, b in zip(borde, borde[1:] + borde[:1]):
        L = (b - a).length
        if L < 1e-3:
            continue
        m = (a + b) / 2
        E.caja(bm, (m.x, m.y, 0.0), (L + 0.05, 0.3, 0.26), 0, (0, 0, math.atan2(b.y - a.y, b.x - a.x)))
    E.objeto("Adentro_isla_brocal", bm, [E.material("Brocal_isla", (0.17, 0.17, 0.18), 0.8)], padre, col)
    bm = bmesh.new()
    f = bm.faces.new([bm.verts.new((p.x, p.y, 0.22)) for p in borde])
    ob = E.objeto("Pasto_isla_plaza", bm, [M["pasto"]], padre, col)
    # busto dorado sobre pedestal de granito negro, mirando al patio (hacia la portada)
    bx, by = c.x - 4.0, c.y - 6.0
    giro = math.atan2(-(by - 20.0), -(bx - 0.0)) - math.pi / 2
    bm = bmesh.new()
    E.caja(bm, (bx, by, 0.2), (1.6, 1.6, 0.35), 0, (0, 0, giro))
    E.caja(bm, (bx, by, 0.55), (1.05, 1.05, 2.1), 0, (0, 0, giro))
    E.caja(bm, (bx, by, 2.65), (1.2, 1.2, 0.12), 0, (0, 0, giro))
    E.objeto("Adentro_busto_pedestal", bm, [M["granito"]], padre, col)
    bm = bmesh.new()
    hombros = bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=1.0)["verts"]
    for v in hombros:
        v.co = Vector((v.co.x * 0.42, v.co.y * 0.24, max(v.co.z, -0.35) * 0.38))
    bmesh.ops.translate(bm, vec=Vector((0, 0, 3.05)), verts=hombros)
    cabeza = bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=12, radius=1.0)["verts"]
    for v in cabeza:
        v.co = Vector((v.co.x * 0.13, v.co.y * 0.15 + 0.02, v.co.z * 0.18))
    bmesh.ops.translate(bm, vec=Vector((0, 0.0, 3.58)), verts=cabeza)
    E.cilindro(bm, (0, 0.0, 3.25), 0.075, 0.075, 0.2, 0, 12)
    for s in (-1, 1):                                         # charreteras
        E.cilindro(bm, (s * 0.36, 0.0, 3.27), 0.09, 0.09, 0.05, 0, 12)
    me_b = bpy.data.meshes.new("Adentro_busto")
    bm.to_mesh(me_b)
    bm.free()
    me_b.materials.append(M["dorado"])
    E.suavizar(me_b, 60)
    b = bpy.data.objects.new("Adentro_busto", me_b)
    b.location = (bx, by, 0.0)
    b.rotation_euler = (0, 0, giro + math.pi)
    col.objects.link(b)
    b.parent = padre
    # once astas blancas en abanico detrás del busto (la del medio-derecha mucho más alta), bases cuadradas
    bm, bb = bmesh.new(), bmesh.new()
    for k in range(11):
        a = math.radians(-70 + k * 14)
        d = Vector((math.sin(a), math.cos(a)))
        fr = Vector((math.cos(giro + math.pi / 2), math.sin(giro + math.pi / 2)))      # hacia el patio
        lado = Vector((-fr.y, fr.x))
        q = Vector((bx, by)) - fr * 1.5 + lado * (d.x * 9.0) + fr * (-d.y * 3.0 + 3.0)
        alto = 19.0 if k == 7 else 9.5 + rnd.uniform(-0.6, 1.6)
        E.caja(bb, (q.x, q.y, 0.2), (0.55, 0.55, 0.55), 0)
        E.cilindro(bm, (q.x, q.y, 0.75), 0.075 if k != 7 else 0.1, 0.045, alto, 0, 10)
        E.cilindro(bm, (q.x, q.y, 0.75 + alto), 0.07, 0.07, 0.12, 0, 10)
    E.objeto("Adentro_astas", bm, [M["blanco"]], padre, col)
    E.objeto("Adentro_astas_bases", bb, [M["blanco"]], padre, col)
    # puntos para las plantas que siembra entorno.py: seto amarillo a lo largo del brocal y matas adentro
    plantas = []
    mw = padre.matrix_world
    for i, (a, b2) in enumerate(zip(borde, borde[1:] + borde[:1])):
        L = (b2 - a).length
        hacia = (c - a).normalized()
        for t in [k / max(1, int(L / 1.1)) for k in range(max(1, int(L / 1.1)))]:
            p = a.lerp(b2, t) + hacia * 1.0
            w = mw @ Vector((p.x, p.y, 0.22))
            plantas.append([w.x, w.y, w.z, "seto", 0.75])
    for k in range(26):
        p = c + Vector((rnd.uniform(-9, 9), rnd.uniform(-12, 12)))
        if (p - Vector((bx, by))).length < 2.5:
            continue
        w = mw @ Vector((p.x, p.y, 0.22))
        plantas.append([w.x, w.y, w.z, rnd.choice(("croto", "croto", "seto", "helecho")), rnd.uniform(0.7, 1.3)])
    for x, y in ((-11.0, 7.4), (-9.0, 7.6), (-12.6, 7.8), (8.6, 7.5), (13.0, 7.6)):     # crotos junto a la portada
        w = mw @ Vector((x, y, 0.0))
        plantas.append([w.x, w.y, w.z, "croto", 1.1])
    v = bpy.data.objects.new("Adentro_plantas_plaza", None)
    v["plantas"] = json.dumps(plantas)
    col.objects.link(v)
    # faroles a lo largo de la vía recta, del lado de afuera de la isla
    bm, bl = bmesh.new(), bmesh.new()
    for y in (50.0, 80.0, 110.0):
        E.cilindro(bm, (-5.4, y, 0), 0.11, 0.08, 8.0, 0, 10)
        E.caja(bm, (-4.4, y, 7.9), (2.0, 0.12, 0.12), 0)
        E.caja(bl, (-3.5, y, 7.75), (0.6, 0.3, 0.15), 0)
    E.objeto("Adentro_faroles", bm, [M["poste"]], padre, col)
    E.objeto("Adentro_faroles_luz", bl, [M["luz"]], padre, col)
    return bx, by


def reja_rombos(bm, x0, x1, y, z0, z1, mi_marco, mi_barra, paso=0.28):
    """Reja de seguridad en rombos (barras en las dos diagonales) con su marco, en el plano y = cte."""
    E.caja(bm, (0.5 * (x0 + x1), y, z0), (x1 - x0, 0.08, 0.08), mi_marco)
    E.caja(bm, (0.5 * (x0 + x1), y, z1 - 0.08), (x1 - x0, 0.08, 0.08), mi_marco)
    for x in (x0, x1):
        E.caja(bm, (x, y, z0), (0.08, 0.08, z1 - z0), mi_marco)
    W, Hh = x1 - x0, z1 - z0
    for s in (-1, 1):
        k = -Hh
        while k < W + Hh:
            # recta x - x0 = k + s * (z - z0) recortada al rectángulo
            pts = []
            for zz in (0.0, Hh):
                xx = k + s * zz
                if 0 <= xx <= W:
                    pts.append(Vector((x0 + xx, z0 + zz)))
            for xx in (0.0, W):
                zz = (xx - k) * s
                if 0 <= zz <= Hh:
                    pts.append(Vector((x0 + xx, z0 + zz)))
            if len(pts) >= 2:
                a, b = pts[0], max(pts, key=lambda q: (q - pts[0]).length)
                L = (b - a).length
                if L > 0.05:
                    m = (a + b) / 2
                    ang = math.atan2(b.y - a.y, b.x - a.x)
                    E.caja(bm, (m.x, y, m.y - 0.012), (L, 0.025, 0.025), mi_barra, (0, -ang, 0))
            k += paso


def pasos(M, padre, col):
    """Los dos pasos vistos desde adentro (fotos 2026-11-07): columnas cuadradas grises en el borde de cada carril,
    y entre ellas y el bloque una garita de vigilancia cerrada con reja de rombos de piso a techo; acera alta bajo la
    reja, doble línea blanca entre los carriles y conos naranja."""
    gris = E.pbr("Concreto_gris_columnas", "concreto_gastado", 2.0, pintura=(0.28, 0.29, 0.30))
    xc = E.X_PASO + 4.6                                   # borde exterior del carril
    bm = bmesh.new()
    for s in (-1, 1):
        for yy in (-F2 + 0.35, F2 - 0.35):
            E.caja(bm, (s * xc, yy, 0), (0.45, 0.45, E.H_PB), 0)
    E.objeto("Adentro_columnas_pasos", bm, [gris], padre, col)
    bm = bmesh.new()
    for s in (-1, 1):
        x0, x1 = sorted((s * (xc + 0.23), s * XB0))
        E.caja(bm, (0.5 * (x0 + x1), 0, 0), (x1 - x0, E.FONDO, 0.18), 0)
    E.objeto("Adentro_acera_garitas", bm, [M["acera"]], padre, col)
    bm = bmesh.new()
    negro = E.material("Reja_negra", (0.03, 0.03, 0.03), 0.5, 0.5)
    for s in (-1, 1):
        x0, x1 = sorted((s * (xc + 0.25), s * (XB0 - 0.05)))
        for yy in (-F2 + 0.35, F2 - 0.35):
            reja_rombos(bm, x0, x1, yy, 0.18, E.H_PB - 0.05, 0, 0)
        # puertita de la reja del lado del carril
        E.caja(bm, (s * (xc + 0.25), 0, 0.18), (0.06, 1.0, 2.1), 0)
    E.objeto("Adentro_rejas_garitas", bm, [negro], padre, col)
    bm = bmesh.new()                                     # mostrador y escalerita de las garitas de los pasos
    for s in (-1, 1):
        E.caja(bm, (s * (xc + 1.1), -1.5, 0.18), (1.2, 0.5, 0.9), 0)
    E.objeto("Adentro_mostradores", bm, [gris], padre, col)
    # doble línea blanca entre los carriles (sale de la columna central hacia adentro) y bordes de carril
    bm = bmesh.new()
    for x in (-0.3, 0.3):
        E.caja(bm, (x, F2 + 7.0, 0.045), (0.14, 14.0, 0.012), 0)
    for s in (-1, 1):
        E.caja(bm, (s * (xc - 0.2), F2 + 5.0, 0.045), (0.14, 10.0, 0.012), 0)
    E.objeto("Adentro_doble_linea", bm, [M["pintura"]], padre, col)
    bm = bmesh.new()
    for x, y in ((-0.9, F2 + 1.2), (0.9, -F2 - 0.8), (2.6, -F2 - 1.2)):
        E.cilindro(bm, (x, y, 0.04), 0.19, 0.03, 0.7, 0, 12)
        E.caja(bm, (x, y, 0.04), (0.42, 0.42, 0.04), 1)
    E.objeto("Adentro_conos", bm, [E.material("Cono_naranja", (0.95, 0.25, 0.02), 0.45),
                                    E.material("Base_cono", (0.03, 0.03, 0.03), 0.6)], padre, col)


def main():
    limpiar()
    padre = bpy.data.objects["Entrada_origen"]
    col = bpy.data.collections["Entrada"]
    M = M_()
    pasos(M, padre, col)
    cara_adentro(M, padre, col)
    techo_adentro(M, padre, col)
    edificio_crema(M, padre, col)
    anexo_mas_x(M, padre, col)
    vias_y_patio(M, padre, col)
    bx, by = plaza(M, padre, col)
    E.camara("Cam_Adentro_Portada", padre, col, (3.5, 36.0, 1.5), (-1.0, 0.0, 3.4), 22)
    E.camara("Cam_Adentro_Lado", padre, col, (7.0, 27.0, 1.5), (-24.0, 12.0, 3.2), 20)
    E.camara("Cam_Adentro_Pasos", padre, col, (3.0, 17.0, 1.6), (-5.5, 0.0, 2.0), 24)
    E.camara("Cam_Plaza", padre, col, (-12.0, 16.0, 1.5), (bx + 6.0, by + 8.0, 6.0), 22)
    E.camara("Cam_Plaza_Lado", padre, col, (46.0, 44.0, 1.5), (bx, by + 4.0, 6.0), 24)
    bpy.ops.wm.save_mainfile()
    print("entrada por dentro y plaza listas")


if __name__ == "__main__":
    main()
