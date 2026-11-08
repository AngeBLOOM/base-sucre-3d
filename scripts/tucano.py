"""Embraer EMB-312 Tucano (AT-27 en la Aviación Militar Bolivariana), el avión del monumento 27N de la entrada.

Medidas reales: 9,86 m de largo, 11,14 m de envergadura, 3,4 m de alto. Nariz larga del turbohélice PT6 con la toma
de aire bajo la hélice y los escapes a los lados, cabina de burbuja larga de dos puestos en tándem (el de atrás más
alto), ala baja recta con diedro, deriva alta con aleta dorsal y aleta ventral, hélice tripala.
Reusa las piezas de mentor.py (fuselaje por secciones, perfiles NACA, rótulos). Ejes: +Y nariz, +X ala derecha,
+Z arriba; origen bajo el ala.

    import tucano; ob = tucano.crear(padre, coleccion, material_pintura)
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

import mentor as Mn

# (y, medio ancho, medio alto, centro z) — v2 (ella: «se parece al Mentor del G14»): fuselaje más delgado (0,92 m
# de ancho), nariz larga y afinada del PT6 que baja hacia la hélice, cola larga y fina que sube hacia la deriva
FUSELAJE = [(-4.95, 0.06, 0.13, 0.56), (-4.40, 0.12, 0.21, 0.48), (-3.60, 0.19, 0.29, 0.37), (-2.70, 0.27, 0.38, 0.26),
            (-1.70, 0.36, 0.48, 0.15), (-0.60, 0.43, 0.55, 0.07), (0.50, 0.46, 0.57, 0.02), (1.50, 0.45, 0.54, -0.02),
            (2.50, 0.41, 0.46, -0.07), (3.40, 0.34, 0.36, -0.12), (4.15, 0.27, 0.27, -0.15), (4.80, 0.20, 0.20, -0.16)]


def _disco(bm, c, n, r, mi, grueso=0.004, seg=28):
    """Disco plano (escarapela, luz, tapa de registro) centrado en c con normal n."""
    vs = bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=grueso)["verts"]
    bmesh.ops.transform(bm, matrix=Matrix.Translation(c) @ Vector(n).to_track_quat("Z", "Y").to_matrix().to_4x4(),
                        verts=vs)
    for f in {f for v in vs for f in v.link_faces}:
        f.material_index = mi


def _caja(bm, c, tam, mi, rot=None):
    vs = bmesh.ops.create_cube(bm, size=1.0)["verts"]
    M = Matrix.Translation(c) @ (rot.to_4x4() if rot is not None else Matrix.Identity(4)) @ Matrix.Diagonal((*tam, 1))
    bmesh.ops.transform(bm, matrix=M, verts=vs)
    for f in {f for v in vs for f in v.link_faces}:
        f.material_index = mi


def _ala(x, t, dih, arriba=True):
    """Punto sobre la piel del ala a |x| m de eje y a la fracción t de la cuerda, con su normal."""
    s = (abs(x) - 0.48) / 5.09
    le = 1.75 - 0.5 * s
    cu = 2.25 - 0.95 * s
    es = 0.15 - 0.03 * s
    zc = -0.48 + (abs(x) - 0.48) * math.tan(dih)
    h = es * cu * Mn._perfil(t) / 2
    p = Vector((x, le - t * cu, zc + (h if arriba else -h)))
    sg = 1 if x > 0 else -1
    n = Vector((-sg * math.sin(dih), 0, math.cos(dih))) * (1 if arriba else -1)
    return p, n


def escarapela(bm, c, n, r):
    """Escarapela de la aviación venezolana: anillos amarillo, azul y rojo, con las ocho estrellas blancas en el
    anillo azul."""
    n = Vector(n).normalized()
    for k, (rr, mi) in enumerate(((r, 5), (r * 0.68, 6), (r * 0.36, 7))):
        _disco(bm, c + n * (0.002 * k), n, rr, mi)
    q = n.to_track_quat("Z", "Y").to_matrix()
    for k in range(8):
        a = math.pi / 2 + math.pi * (k - 3.5) / 9 * 1.6
        p = c + n * 0.007 + q @ Vector((math.cos(a) * r * 0.52, math.sin(a) * r * 0.52, 0))
        _disco(bm, p, n, r * 0.055, 8, 0.002, 5)


def detalles_militares(bm, dih):
    """Lo que tiene el AT-27 del monumento en la foto (y el modelo que ella mandó): escarapelas sobre el ala izquierda
    y bajo la derecha, escarapela en la deriva bajo la bandera, flecha roja de rescate junto a la cabina, luces de
    navegación (roja a la izquierda, verde a la derecha, blanca en la cola), tubo pitot, antenas de cuchilla arriba y
    abajo, asientos eyectables y tablero bajo la burbuja, puntas amarillas en las palas, pasarelas antideslizantes en
    la raíz del ala y tapas de registro."""
    for x, arriba in ((-3.9, True), (-3.9, False)):         # foto desde abajo: escarapela bajo el ala izquierda
        p, n = _ala(x, 0.42, dih, arriba)
        escarapela(bm, p + n * 0.004, n, 0.36)
    for sx in (1, -1):                                      # escarapela en la deriva
        escarapela(bm, Vector((sx * 0.065, -4.15, 0.78)), Vector((sx, 0, 0)), 0.16)
    for sx in (1, -1):                                      # flecha roja de rescate bajo el marco de la cabina
        c = Vector((sx * 0.465, 1.65, 0.36))
        q = Vector((sx, 0, 0)).to_track_quat("Z", "Y").to_matrix()
        vs = [bm.verts.new(c + q @ Vector(v)) for v in ((0.0, 0.11, 0.0), (-0.09, -0.06, 0.0), (0.09, -0.06, 0.0))]
        f = bm.faces.new(vs if sx > 0 else list(reversed(vs)))
        f.material_index = 7
    # luces de navegación en las puntas y en la cola
    for x, mi in ((-5.58, 7), (5.58, 9)):
        p, _n = _ala(x, 0.12, dih)
        _disco(bm, Vector((x + (0.03 if x > 0 else -0.03), p.y, p.z - 0.03)), Vector((1 if x > 0 else -1, 0, 0)),
               0.05, mi, 0.04, 12)
    _disco(bm, Vector((0, -4.98, 0.08)), Vector((0, -1, 0)), 0.04, 8, 0.04, 12)
    # tubo pitot bajo el ala izquierda
    p, _n = _ala(-4.6, 0.05, dih, False)
    vs = bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.018, radius2=0.012, depth=0.7)["verts"]
    bmesh.ops.transform(bm, matrix=Matrix.Translation((p.x, p.y + 0.2, p.z - 0.08))
                        @ Matrix.Rotation(-math.pi / 2, 4, "X"), verts=vs)
    for f in {f for v in vs for f in v.link_faces}:
        f.material_index = 3
    # antenas de cuchilla
    for y, z, h, sg in ((-1.9, 0.58, 0.28, 1), (-0.6, -0.58, 0.22, -1), (2.4, -0.5, 0.16, -1)):
        _caja(bm, Vector((0, y, z + sg * h / 2)), (0.02, 0.22, h), 4, Matrix.Rotation(sg * 0.25, 3, "X"))
    # asientos eyectables en tándem (el de atrás más alto) y tablero con su visera
    for y, z in ((0.85, 0.12), (-0.35, 0.17)):              # cojín bajo el borde: la cabecera queda bajo la burbuja
        _caja(bm, Vector((0, y - 0.15, z + 0.25)), (0.46, 0.14, 0.75), 10)          # respaldo
        _caja(bm, Vector((0, y - 0.15, z + 0.72)), (0.30, 0.18, 0.2), 10)           # cabecera
        _caja(bm, Vector((0, y + 0.15, z)), (0.46, 0.45, 0.12), 10)                 # cojín
        _caja(bm, Vector((0, y + 0.72, z + 0.3)), (0.62, 0.12, 0.28), 4)            # tablero
        _caja(bm, Vector((0, y - 0.24, z + 0.83)), (0.22, 0.05, 0.05), 5)           # manija amarilla
    # puntas amarillas de las palas (la hélice queda en y = 5,0, centro z = -0.11)
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.3
        d = Vector((math.cos(a), 0, math.sin(a)))
        _caja(bm, Vector((0, 4.98, -0.16)) + d * 1.30, (0.2, 0.03, 0.2), 5,
              d.to_track_quat("Z", "Y").to_matrix())
    # pasarelas antideslizantes negras en la raíz del ala y tapas de registro
    for sg in (1, -1):
        for t0 in (0.25, 0.5):
            p, n = _ala(sg * 0.95, t0, dih)
            _caja(bm, p + n * 0.004, (0.55, 0.4, 0.004), 4,
                  Matrix.Rotation(sg * -dih, 3, "Y"))
        for x, t in ((1.6, 0.6), (2.6, 0.3), (3.0, 0.7), (4.6, 0.5), (1.3, 0.15)):
            for arriba in (True, False):
                p, n = _ala(sg * x, t, dih, arriba)
                _disco(bm, p + n * 0.003, n, 0.06, 4, 0.003, 14)


def crear(padre, col, pintura, nombre="Tucano_AT27"):
    mats = Mn._materiales() + [Mn._mat("Blanco_marcas", (0.85, 0.85, 0.85), 0.4),           # 8
                               Mn._mat("Luz_verde_nav", (0.02, 0.6, 0.1), 0.2),               # 9
                               Mn._mat("Asiento_eyectable", (0.06, 0.065, 0.06), 0.7)]        # 10
    mats[0] = pintura
    bm = bmesh.new()
    Mn._loft(bm, [Mn._seccion(hw, hh, zc, y) for y, hw, hh, zc in FUSELAJE], 0)
    # toma de aire bajo la nariz (la «barba» del PT6) y dos escapes a cada lado
    Mn._loft(bm, [Mn._seccion(w, h, -0.42, y, 16, 2.4) for y, w, h in
                  ((3.0, 0.05, 0.03), (3.6, 0.22, 0.14), (4.35, 0.24, 0.16), (4.55, 0.2, 0.12))], 0)
    for sx in (-1, 1):
        # escape corto y ovalado que sale del costado hacia atrás (no un caño de frente)
        vs = bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.075, radius2=0.06, depth=0.3)["verts"]
        bmesh.ops.transform(bm, matrix=Matrix.Translation((sx * 0.37, 3.7, -0.04))
                            @ Matrix.Rotation(sx * math.radians(-145), 4, "Z") @ Matrix.Rotation(math.pi / 2, 4, "X")
                            @ Matrix.Diagonal((1.0, 0.65, 1.0, 1.0)), verts=vs)
        for f in {f for v in vs for f in v.link_faces}:
            f.material_index = 4
    # cono y hélice tripala
    Mn._loft(bm, [Mn._seccion(r, r, -0.16, y, 16, 2.0) for y, r in ((4.78, 0.19), (5.02, 0.16), (5.22, 0.085), (5.33, 0.015))], 3)
    # palas planas de verdad (antes las caras se cruzaban y parecían cuerdas): ancho que se afina hacia la punta y
    # paso que gira de 35° en la raíz a 12° en la punta
    eje = Vector((0, 1, 0))
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.3
        d = Vector((math.cos(a), 0, math.sin(a)))
        lado = Vector((-d.z, 0, d.x))
        filas = []
        for j in range(9):
            s = j / 8
            r = 0.17 + 1.19 * s
            w = 0.13 * (1 - 0.35 * s) * (0.75 + 0.25 * math.sin(math.pi * min(s * 1.6, 1.0)))
            paso = math.radians(35 - 23 * s)
            cdir = lado * math.cos(paso) + eje * math.sin(paso)
            c = Vector((0, 4.98, -0.16)) + d * r
            filas.append((bm.verts.new(c - cdir * w), bm.verts.new(c + cdir * w)))
        for (a0, a1), (b0, b1) in zip(filas, filas[1:]):
            f = bm.faces.new((a0, a1, b1, b0))
            f.material_index = 4
    # alas rectas con diedro de 5,5° y puntas del mismo color del avión
    dih = math.radians(5.5)
    for sg in (1, -1):
        Mn._superficie(bm, (Vector((sg * 0.48, 1.75, -0.48)), 2.25, 0.15),
                       (Vector((sg * 5.57, 1.25, -0.48 + 5.1 * math.tan(dih))), 1.3, 0.12), 12, 14, lambda s: 0)
    # AT-27 (versión armada): cuatro pilones bajo las alas, perfilados, con su riel de enganche
    for sg in (1, -1):
        for x in (1.85, 3.25):
            zi = -0.48 + (x - 0.48) * math.tan(dih) - 0.06
            filas = Mn._loft(bm, [Mn._seccion(w, h, zi - h, y, 10, 2.2) for y, w, h in
                                  ((0.55, 0.02, 0.05), (0.85, 0.06, 0.16), (1.55, 0.06, 0.18), (2.05, 0.03, 0.07))], 0)
            bmesh.ops.translate(bm, vec=Vector((sg * x, 0, 0)), verts=[v for fila in filas for v in fila])
            vs = bmesh.ops.create_cube(bm, size=1.0)["verts"]
            bmesh.ops.transform(bm, matrix=Matrix.Translation((sg * x, 1.25, zi - 0.37))
                                @ Matrix.Diagonal((0.05, 0.8, 0.04, 1)), verts=vs)
            for f in {f for v in vs for f in v.link_faces}:
                f.material_index = 3
    # estabilizadores, deriva alta con aleta dorsal y aleta ventral
    # estabilizadores (4,7 m de punta a punta, puntas cuadradas)
    for sg in (1, -1):
        Mn._superficie(bm, (Vector((sg * 0.14, -3.75, 0.40)), 1.25, 0.10),
                       (Vector((sg * 2.33, -4.12, 0.45)), 0.62, 0.08), 6, 10, lambda s: 0)
    # deriva grande y muy inclinada hacia atrás (rasgo del Tucano), aleta dorsal larga y aleta ventral pequeña
    FIN = ((-2.85, 0.55, 1.95), (-4.40, 2.42, 0.78))       # (y borde de ataque, z, cuerda) en la raíz y en la punta
    Mn._superficie(bm, (Vector((0, FIN[0][0], FIN[0][1])), FIN[0][2], 0.10),
                   (Vector((0, FIN[1][0], FIN[1][1])), FIN[1][2], 0.09), 10, 12, lambda s: 0, vertical=True)
    Mn._superficie(bm, (Vector((0, -1.75, 0.60)), 1.25, 0.06), (Vector((0, -2.95, 0.78)), 0.25, 0.05), 4, 8,
                   lambda s: 0, vertical=True)
    Mn._superficie(bm, (Vector((0, -3.55, 0.08)), 0.75, 0.06), (Vector((0, -3.95, -0.22)), 0.4, 0.05), 3, 8,
                   lambda s: 0, vertical=True)
    # bandera en la deriva: tres franjas que siguen la inclinación (amarillo arriba, azul, rojo abajo)

    def borde_deriva(z):
        s = (z - FIN[0][1]) / (FIN[1][1] - FIN[0][1])
        le = FIN[0][0] + (FIN[1][0] - FIN[0][0]) * s
        return le - 0.08, le - (FIN[0][2] + (FIN[1][2] - FIN[0][2]) * s) + 0.06
    for k, mi in enumerate((7, 6, 5)):
        z0, z1 = 1.1 + k * 0.36, 1.1 + (k + 1) * 0.36
        a0, b0 = borde_deriva(z0)
        a1, b1 = borde_deriva(z1)
        for sx in (1, -1):
            x = sx * 0.05
            vs = [bm.verts.new(v) for v in ((x, a0, z0), (x, b0, z0), (x, b1, z1), (x, a1, z1))]
            f = bm.faces.new(vs if sx > 0 else list(reversed(vs)))
            f.material_index = mi
    # cabina de burbuja larga en dos tramos (el de atrás más alto) con sus arcos
    # v2: burbuja alta y larga de una pieza, el puesto de atrás bien más alto (escalón), parabrisas inclinado
    zt = 0.5
    filas = []
    for y, w, h in ((-1.85, 0.08, 0.05), (-1.45, 0.30, 0.46), (-0.85, 0.37, 0.72), (-0.25, 0.38, 0.73),
                    (0.35, 0.38, 0.60), (0.95, 0.37, 0.56), (1.5, 0.34, 0.47), (2.0, 0.26, 0.28), (2.3, 0.10, 0.06)):
        filas.append([Vector((w * math.cos(a), y, zt + h * math.sin(a))) for a in (math.pi * k / 12 for k in range(13))])
    vs = [[bm.verts.new(p) for p in fila] for fila in filas]
    for a, b in zip(vs, vs[1:]):
        for k in range(12):
            f = bm.faces.new((a[k], a[k + 1], b[k + 1], b[k]))
            f.material_index = 2
    for i in (1, 3, 5, 7):
        for p, q in zip(filas[i], filas[i][1:]):
            m = (p + q) / 2
            d = q - p
            vc = bmesh.ops.create_cube(bm, size=1.0)["verts"]
            bmesh.ops.transform(bm, matrix=Matrix.Translation(m + (m - Vector((0, m.y, zt))).normalized() * 0.012)
                                @ d.to_track_quat("X", "Y").to_matrix().to_4x4()
                                @ Matrix.Diagonal((d.length + 0.01, 0.045, 0.03, 1)), verts=vc)
            for f in {f for v in vc for f in v.link_faces}:
                f.material_index = 3
    detalles_militares(bm, dih)
    me = bpy.data.meshes.new(nombre)
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    try:
        me.shade_smooth()
        me.set_sharp_from_angle(angle=math.radians(40))
    except AttributeError:
        pass
    ob = bpy.data.objects.new(nombre, me)
    col.objects.link(ob)
    ob.parent = padre
    claro = Mn._mat("Gris_claro_rotulo", (0.55, 0.56, 0.57), 0.5)       # «FAV» gris claro sobre el gris oscuro
    negro = claro
    z_abajo = _ala(3.6, 0.45, dih, False)[0].z
    for cuerpo, tam, loc, rot in (("FAV", 0.6, (3.2, 1.0, _ala(3.2, 0.4, dih)[0].z + 0.012), (0, dih, math.pi)),
                                  ("FAV", 0.6, (3.6, 0.75, z_abajo - 0.006), (math.pi, dih, math.pi))):
        cu = bpy.data.curves.new("Rotulo_" + cuerpo, "FONT")
        cu.body, cu.size, cu.align_x, cu.align_y, cu.extrude = cuerpo, tam, "CENTER", "CENTER", 0.004
        t = bpy.data.objects.new("Rotulo_Tucano_" + cuerpo + str(len(col.objects)), cu)
        t.data.materials.append(negro)
        t.location, t.rotation_euler = loc, rot
        col.objects.link(t)
        t.parent = ob
    return ob
