"""Beechcraft T-34 Mentor en 3D (el avión del pedestal frente al G14: fotos AVION DE G14, G14 FRENTE AVION).

Medidas reales: 7,9 m de largo, 10 m de envergadura. Ala baja con diedro, cabina de burbuja de dos puestos en
tándem con sus marcos, hélice bipala con cono, puntas de ala y de estabilizador naranja fluorescente, «FAV» sobre el
ala derecha, «E» roja en el fuselaje, 8113 y la bandera de Venezuela en la deriva.
Ejes del avión: +Y hacia la nariz, +X hacia el ala derecha, +Z arriba; origen bajo el ala, donde apoya el pedestal.

    import mentor; ob = mentor.crear(padre, coleccion)
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

# estaciones del fuselaje: (y, medio ancho, medio alto, centro z)
FUSELAJE = [(-4.00, 0.05, 0.08, 0.40), (-3.55, 0.12, 0.16, 0.32), (-3.00, 0.19, 0.25, 0.25), (-2.20, 0.30, 0.36, 0.16),
            (-1.30, 0.41, 0.46, 0.09), (-0.40, 0.48, 0.53, 0.05), (0.50, 0.52, 0.57, 0.03), (1.40, 0.54, 0.58, 0.02),
            (2.30, 0.53, 0.55, 0.00), (3.00, 0.48, 0.48, -0.03), (3.45, 0.40, 0.40, -0.05), (3.75, 0.30, 0.31, -0.06)]


def _mat(nombre, color, rug=0.35, metal=0.0, coat=0.0, alpha=1.0):
    m = bpy.data.materials.get(nombre)
    if m:
        return m
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rug
    b.inputs["Metallic"].default_value = metal
    if "Coat Weight" in b.inputs:
        b.inputs["Coat Weight"].default_value = coat
    b.inputs["Alpha"].default_value = alpha
    return m


def _materiales():
    return [_mat("Mentor_blanco", (0.80, 0.81, 0.82), 0.28, 0.0, 0.5),          # 0 pintura
            _mat("Mentor_naranja", (0.95, 0.22, 0.04), 0.3, 0.0, 0.5),          # 1 puntas fluorescentes
            _mat("Vidrio_cabina_mentor", (0.05, 0.07, 0.09), 0.02, 0.0, 1.0),   # 2 burbuja
            _mat("Mentor_marco", (0.70, 0.71, 0.72), 0.35, 0.3),                # 3 marcos y aluminio
            _mat("Mentor_negro", (0.02, 0.02, 0.022), 0.4, 0.2),                # 4 hélice, rejillas
            _mat("Bandera_amarillo_m", (0.95, 0.72, 0.03), 0.4),                # 5
            _mat("Bandera_azul_m", (0.02, 0.10, 0.42), 0.4),                    # 6
            _mat("Bandera_rojo_m", (0.75, 0.03, 0.04), 0.4)]                    # 7


def _seccion(hw, hh, zc, y, n=20, e=2.6):
    """Sección de superelipse (caja redondeada) del fuselaje."""
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        c, s = math.cos(a), math.sin(a)
        x = hw * math.copysign(abs(c) ** (2 / e), c)
        z = hh * math.copysign(abs(s) ** (2 / e), s)
        pts.append(Vector((x, y, zc + z)))
    return pts


def _loft(bm, anillos, mi, tapar=True):
    vs = [[bm.verts.new(p) for p in a] for a in anillos]
    n = len(anillos[0])
    for a, b in zip(vs, vs[1:]):
        for k in range(n):
            f = bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]))
            f.material_index = mi
    if tapar:
        for fila, rev in ((vs[0], True), (vs[-1], False)):
            f = bm.faces.new(list(reversed(fila)) if rev else fila)
            f.material_index = mi
    return vs


def _perfil(t):
    """Espesor de perfil NACA de 4 cifras (t = fracción de cuerda)."""
    return 5 * (0.2969 * math.sqrt(t) - 0.1260 * t - 0.3516 * t ** 2 + 0.2843 * t ** 3 - 0.1015 * t ** 4)


def _superficie(bm, raiz, punta, n_env=10, n_cuerda=14, mi_fn=lambda s: 0, vertical=False):
    """Ala o estabilizador: raiz/punta = (borde de ataque Vector, cuerda, espesor relativo)."""
    filas = []
    for i in range(n_env + 1):
        s = i / n_env
        le = raiz[0].lerp(punta[0], s)
        cu = raiz[1] + (punta[1] - raiz[1]) * s
        es = raiz[2] + (punta[2] - raiz[2]) * s
        fila = []
        for k in range(n_cuerda + 1):                    # de borde de ataque a borde de fuga por arriba y abajo
            t = (1 - math.cos(math.pi * k / n_cuerda)) / 2
            fila.append((t, es * cu * _perfil(t) / 2))
        arriba = [le + Vector((0, -t * cu, 0)) + (Vector((h, 0, 0)) if vertical else Vector((0, 0, h)))
                  for t, h in fila]
        abajo = [le + Vector((0, -t * cu, 0)) - (Vector((h, 0, 0)) if vertical else Vector((0, 0, h)))
                 for t, h in reversed(fila[1:-1])]
        filas.append(([bm.verts.new(p) for p in arriba + abajo], s))
    n = len(filas[0][0])
    for (a, s), (b, _s) in zip(filas, filas[1:]):
        for k in range(n):
            f = bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]))
            f.material_index = mi_fn(s)
    for vs, s in (filas[0], filas[-1]):
        try:
            f = bm.faces.new(vs if s else list(reversed(vs)))
            f.material_index = mi_fn(s)
        except ValueError:
            pass


def crear(padre, col, nombre="Mentor_T34"):
    bm = bmesh.new()
    # fuselaje
    _loft(bm, [_seccion(hw, hh, zc, y) for y, hw, hh, zc in FUSELAJE], 0)
    # capó: rejilla de admisión bajo la nariz y escapes a los lados
    for x in (-0.36, 0.36):
        vs = bmesh.ops.create_cube(bm, size=1.0)["verts"]
        bmesh.ops.transform(bm, matrix=Matrix.Translation((x * 1.25, 3.1, -0.18)) @ Matrix.Diagonal((0.06, 0.35, 0.12, 1)),
                            verts=vs)
        for f in {f for v in vs for f in v.link_faces}:
            f.material_index = 4
    vs = bmesh.ops.create_cube(bm, size=1.0)["verts"]
    bmesh.ops.transform(bm, matrix=Matrix.Translation((0, 3.55, -0.32)) @ Matrix.Diagonal((0.36, 0.2, 0.08, 1)), verts=vs)
    for f in {f for v in vs for f in v.link_faces}:
        f.material_index = 4
    # cono de la hélice y dos palas con torsión
    cono = [_seccion(r, r, -0.06, y, 16, 2.0) for y, r in ((3.72, 0.17), (3.95, 0.15), (4.12, 0.09), (4.22, 0.015))]
    _loft(bm, cono, 3)
    for sg in (1, -1):
        for k in range(8):
            r0, r1 = 0.15 + k * 0.125, 0.15 + (k + 1) * 0.125
            ang0, ang1 = math.radians(55 - k * 4), math.radians(55 - (k + 1) * 4)
            w0, w1 = 0.11 - 0.006 * k, 0.11 - 0.006 * (k + 1)
            q = []
            for r, ang, w in ((r0, ang0, w0), (r1, ang1, w1)):
                d = Vector((math.cos(ang), math.sin(ang), 0)) * w
                c = Vector((0, 3.85, -0.06 + sg * r))
                q.append((c + Vector((d.x, d.y * 0.4, 0)), c - Vector((d.x, d.y * 0.4, 0))))
            f = bm.faces.new([bm.verts.new(q[0][0]), bm.verts.new(q[1][0]), bm.verts.new(q[1][1]),
                              bm.verts.new(q[0][1])])
            f.material_index = 4
    # alas: ala baja, diedro de 6°, puntas naranja
    dih = math.radians(6)
    for sg in (1, -1):
        raiz = (Vector((sg * 0.45, 1.85, -0.42)), 2.15, 0.16)
        punta = (Vector((sg * 5.0, 1.15, -0.42 + 4.55 * math.tan(dih))), 1.05, 0.11)
        _superficie(bm, raiz, punta, 12, 14, lambda s: 1 if s > 0.84 else 0)
    # estabilizador horizontal y deriva
    for sg in (1, -1):
        _superficie(bm, (Vector((sg * 0.12, -3.05, 0.30)), 0.95, 0.09),
                    (Vector((sg * 1.85, -3.35, 0.33)), 0.55, 0.08), 6, 10, lambda s: 1 if s > 0.8 else 0)
    _superficie(bm, (Vector((0, -2.75, 0.55)), 1.25, 0.10), (Vector((0, -3.45, 1.85)), 0.62, 0.09), 8, 10,
                lambda s: 1 if s > 0.88 else 0, vertical=True)
    # bandera en el timón (franjas amarilla, azul y roja de abajo arriba)
    for k, mi in enumerate((5, 6, 7)):
        for sx in (1, -1):
            z0 = 0.75 + k * 0.3
            vs = bmesh.ops.create_cube(bm, size=1.0)["verts"]
            bmesh.ops.transform(bm, matrix=Matrix.Translation((sx * 0.055, -3.75 - 0.1 * k, z0 + 0.15))
                                @ Matrix.Diagonal((0.012, 0.42, 0.29, 1)), verts=vs)
            for f in {f for v in vs for f in v.link_faces}:
                f.material_index = mi
    # cabina de burbuja de dos puestos, con marcos
    cab = []
    for y, w, h in ((-0.75, 0.10, 0.05), (-0.45, 0.30, 0.25), (0.0, 0.38, 0.40), (0.6, 0.40, 0.45), (1.2, 0.40, 0.45),
                    (1.75, 0.37, 0.38), (2.15, 0.28, 0.20), (2.35, 0.12, 0.04)):
        zt = 0.03 + 0.57 * 0.97
        cab.append([Vector((w * math.cos(a), y, zt + h * math.sin(a))) for a in
                    (math.pi * k / 12 for k in range(13))])
    vs = [[bm.verts.new(p) for p in fila] for fila in cab]
    for a, b in zip(vs, vs[1:]):
        for k in range(12):
            f = bm.faces.new((a[k], a[k + 1], b[k + 1], b[k]))
            f.material_index = 2
    for y_idx in (1, 3, 4, 6):                           # arcos del marco
        fila = cab[y_idx]
        for p, q in zip(fila, fila[1:]):
            m = (p + q) / 2
            d = q - p
            vs_c = bmesh.ops.create_cube(bm, size=1.0)["verts"]
            rot = d.to_track_quat("X", "Y").to_matrix().to_4x4()
            bmesh.ops.transform(bm, matrix=Matrix.Translation(m + (m - Vector((0, m.y, 0.58))).normalized() * 0.012)
                                @ rot @ Matrix.Diagonal((d.length + 0.01, 0.045, 0.03, 1)), verts=vs_c)
            for f in {f for v in vs_c for f in v.link_faces}:
                f.material_index = 3
    me = bpy.data.meshes.new(nombre)
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    for m in _materiales():
        me.materials.append(m)
    try:
        me.shade_smooth()
        me.set_sharp_from_angle(angle=math.radians(40))
    except AttributeError:
        pass
    ob = bpy.data.objects.new(nombre, me)
    col.objects.link(ob)
    ob.parent = padre
    # rotulación
    negro = bpy.data.materials["Mentor_negro"]
    rojo = bpy.data.materials["Bandera_rojo_m"]
    for cuerpo, tam, loc, rot, mat in (("FAV", 0.55, (3.0, 0.9, -0.42 + 2.55 * math.tan(dih) + 0.075), (0, 0, math.pi), negro),
                                       ("E", 0.55, (0.47, -1.6, 0.12), (math.pi / 2, 0, math.pi / 2), rojo),
                                       ("E", 0.55, (-0.47, -1.6, 0.12), (math.pi / 2, 0, -math.pi / 2), rojo),
                                       ("8113", 0.26, (0.07, -3.3, 1.3), (math.pi / 2, 0, math.pi / 2), negro),
                                       ("8113", 0.26, (-0.07, -3.3, 1.3), (math.pi / 2, 0, -math.pi / 2), negro)):
        cu = bpy.data.curves.new("Rotulo_" + cuerpo, "FONT")
        cu.body = cuerpo
        cu.size = tam
        cu.align_x = "CENTER"
        cu.align_y = "CENTER"
        cu.extrude = 0.004
        t = bpy.data.objects.new("Rotulo_" + cuerpo, cu)
        t.data.materials.append(mat)
        t.location, t.rotation_euler = loc, rot
        col.objects.link(t)
        t.parent = ob
    return ob
