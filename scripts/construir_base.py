"""Base Aérea Mariscal Sucre (SVBS, Maracay) en Blender, armada con datos reales.

Relieve (DEM), foto satelital, pistas 11/29 y 06/24 y huellas de edificios de OpenStreetMap salen de los
datos que AeroEscuela ya descargó (ver datos/). Ejes: X = este, Y = norte, Z = altura sobre la pista (m).

Uso:  blender --background --python construir_base.py -- <carpeta del proyecto>
"""
import json, math, os, random, sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

RAIZ = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else os.path.dirname(os.path.dirname(__file__))
DATOS = os.path.join(RAIZ, "datos")
D = json.load(open(os.path.join(DATOS, "svbs.json")))
H = np.load(os.path.join(DATOS, "heights.npy"))
ELEV = D["elev"]
H0, HS = D["h_rect"][0], D["h_rect"][2]
# relieve fino (±12 km cada 40 m, de exporta_relieve.py): la sierra con sus filas y quebradas, no bultos lisos
_R40 = os.path.join(DATOS, "heights_40m.npy")
H40 = np.load(_R40) if os.path.exists(_R40) else None
R40 = 12000.0

# zona militar que se modela con edificios (este, norte en m); fuera queda la foto satelital
ZONA = (-1500.0, 1300.0, -1130.0, 1690.0)
SAT_INT = 3000.0       # semilado de la foto fina (1,5 m/px)
SAT_EXT = 10000.0      # semilado del paisaje lejano (4,9 m/px)
SAT_REG = 25600.0      # semilado del paisaje regional (12,5 m/px): lago, Maracay y la sierra entera


# ----------------------------------------------------------------------------------- relieve
def _bilineal(A, origen, lado, e, n):
    c = lado / (A.shape[0] - 1)
    fi, fj = (n - origen) / c, (e - origen) / c
    i, j = int(math.floor(fi)), int(math.floor(fj))
    i = min(max(i, 0), A.shape[0] - 2)
    j = min(max(j, 0), A.shape[1] - 2)
    ti, tj = fi - i, fj - j
    return float(A[i, j] * (1 - ti) * (1 - tj) + A[i + 1, j] * ti * (1 - tj)
                 + A[i, j + 1] * (1 - ti) * tj + A[i + 1, j + 1] * ti * tj)


def cota(e, n):
    """Altura del DEM relativa a la pista: el relieve de 40 m dentro de ±12 km, el de 100 m afuera, con una
    transición suave en el último kilómetro para que no quede un escalón."""
    h100 = _bilineal(H, H0, HS, e, n)
    if H40 is None:
        return h100 - ELEV
    borde = max(abs(e), abs(n))
    if borde >= R40:
        return h100 - ELEV
    h40 = _bilineal(H40, -R40, 2 * R40, e, n)
    t = min(max((borde - (R40 - 1000.0)) / 1000.0, 0.0), 1.0)
    return h40 * (1 - t) + h100 * t - ELEV


def dist_pista(e, n):
    """Distancia al rectángulo de la pista más cercana (0 dentro)."""
    best = 1e9
    for rw in D["runways"]:
        cn, ce = rw["center"]
        dn, de = rw["dir"]
        rx, ry = e - ce, n - cn
        a = abs(rx * de + ry * dn) - rw["length"] / 2
        b = abs(-rx * dn + ry * de) - rw["width"] / 2
        best = min(best, math.hypot(max(a, 0), max(b, 0)))
    return best


def cota_suave(e, n):
    """El campo de aviación queda plano a la cota de la pista y se funde con el DEM a 250 m."""
    d = dist_pista(e, n)
    t = min(max((d - 80.0) / 250.0, 0.0), 1.0)
    t = t * t * (3 - 2 * t)
    return cota(e, n) * t


def malla_terreno(nombre, semilado, paso, imagen, bajar=0.0, aplanar=True, hueco=0.0, agua=("agua_20km.png", SAT_EXT)):
    """hueco: semilado del cuadro central que se deja sin caras (lo cubre una malla más fina)."""
    n = int(2 * semilado / paso) + 1
    verts, uvs = [], []
    for i in range(n):
        y = -semilado + i * paso
        for j in range(n):
            x = -semilado + j * paso
            z = (cota_suave(x, y) if aplanar else cota(x, y)) - bajar
            verts.append((x, y, z))
    caras = []
    for i in range(n - 1):
        for j in range(n - 1):
            if hueco and max(abs(-semilado + (j + 0.5) * paso), abs(-semilado + (i + 0.5) * paso)) < hueco - paso:
                continue
            caras.append((i * n + j, i * n + j + 1, (i + 1) * n + j + 1, (i + 1) * n + j))
    me = bpy.data.meshes.new(nombre)
    me.from_pydata(verts, [], caras)
    uv = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            x, y, _ = verts[me.loops[li].vertex_index]
            uv.data[li].uv = ((x + semilado) / (2 * semilado), (y + semilado) / (2 * semilado))
    ob = bpy.data.objects.new(nombre, me)
    bpy.context.collection.objects.link(ob)
    ob.data.materials.append(mat_suelo(nombre, imagen, semilado, *agua))
    return ob


# ----------------------------------------------------------------------------------- materiales
def nodos(nombre):
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    return m, nt, bsdf


def mat_suelo(nombre, imagen, semilado, imagen_agua="agua_20km.png", semilado_agua=SAT_EXT):
    m, nt, bsdf = nodos("Suelo_" + nombre)
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(os.path.join(DATOS, imagen))
    tex.interpolation = "Cubic"
    tex.extension = "EXTEND"
    agua = nt.nodes.new("ShaderNodeTexImage")
    agua.image = bpy.data.images.load(os.path.join(DATOS, imagen_agua))
    agua.image.colorspace_settings.name = "Non-Color"
    # la máscara de agua cubre su propio cuadro; se reescala a las UV de esta malla
    uvn = nt.nodes.new("ShaderNodeUVMap")
    mapa = nt.nodes.new("ShaderNodeMapping")
    k = semilado / semilado_agua
    mapa.inputs["Scale"].default_value = (k, k, 1)
    mapa.inputs["Location"].default_value = ((1 - k) / 2, (1 - k) / 2, 0)
    nt.links.new(uvn.outputs["UV"], mapa.inputs["Vector"])
    nt.links.new(mapa.outputs["Vector"], agua.inputs["Vector"])
    # el lago: color de la foto oscurecido y brillo de agua
    oscuro = nt.nodes.new("ShaderNodeMix")
    oscuro.data_type = "RGBA"
    oscuro.blend_type = "MULTIPLY"
    oscuro.inputs["Factor"].default_value = 1.0
    oscuro.inputs["B"].default_value = (0.22, 0.30, 0.28, 1)
    nt.links.new(tex.outputs["Color"], oscuro.inputs["A"])
    col = nt.nodes.new("ShaderNodeMix")
    col.data_type = "RGBA"
    nt.links.new(agua.outputs["Color"], col.inputs["Factor"])
    nt.links.new(tex.outputs["Color"], col.inputs["A"])
    nt.links.new(oscuro.outputs["Result"], col.inputs["B"])
    nt.links.new(col.outputs["Result"], bsdf.inputs["Base Color"])
    rug = nt.nodes.new("ShaderNodeMapRange")
    rug.inputs["To Min"].default_value = 0.92
    rug.inputs["To Max"].default_value = 0.2
    nt.links.new(agua.outputs["Color"], rug.inputs["Value"])
    nt.links.new(rug.outputs["Result"], bsdf.inputs["Roughness"])
    return m


def mat_asfalto():
    m, nt, bsdf = nodos("Asfalto")
    ruido = nt.nodes.new("ShaderNodeTexNoise")
    ruido.inputs["Scale"].default_value = 0.35
    ruido.inputs["Detail"].default_value = 8
    rampa = nt.nodes.new("ShaderNodeValToRGB")
    rampa.color_ramp.elements[0].color = (0.045, 0.045, 0.048, 1)
    rampa.color_ramp.elements[1].color = (0.11, 0.105, 0.10, 1)
    nt.links.new(ruido.outputs["Fac"], rampa.inputs["Fac"])
    nt.links.new(rampa.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.85
    grano = nt.nodes.new("ShaderNodeTexNoise")
    grano.inputs["Scale"].default_value = 60
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.15
    nt.links.new(grano.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def mat_plano(nombre, color, rug=0.6, metal=0.0):
    m, nt, bsdf = nodos(nombre)
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = rug
    bsdf.inputs["Metallic"].default_value = metal
    return m


def mat_techos():
    """Cada techo toma el color que tiene en la foto satelital (atributo «techo»)."""
    m, nt, bsdf = nodos("Techos")
    at = nt.nodes.new("ShaderNodeAttribute")
    at.attribute_type = "GEOMETRY"
    at.attribute_name = "techo"
    nt.links.new(at.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.55
    bsdf.inputs["Metallic"].default_value = 0.0
    return m


def mat_paredes():
    m, nt, bsdf = nodos("Paredes")
    ruido = nt.nodes.new("ShaderNodeTexNoise")
    ruido.inputs["Scale"].default_value = 2.0
    rampa = nt.nodes.new("ShaderNodeValToRGB")
    rampa.color_ramp.elements[0].color = (0.62, 0.58, 0.50, 1)
    rampa.color_ramp.elements[1].color = (0.80, 0.77, 0.70, 1)
    nt.links.new(ruido.outputs["Fac"], rampa.inputs["Fac"])
    nt.links.new(rampa.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.8
    # franjas de ventanas por piso (3 m)
    coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(coord.outputs["Object"], sep.inputs["Vector"])
    ola = nt.nodes.new("ShaderNodeMath")
    ola.operation = "PINGPONG"
    ola.inputs[1].default_value = 1.5
    nt.links.new(sep.outputs["Z"], ola.inputs[0])
    corte = nt.nodes.new("ShaderNodeMath")
    corte.operation = "GREATER_THAN"
    corte.inputs[1].default_value = 1.0
    nt.links.new(ola.outputs["Value"], corte.inputs[0])
    vid = nt.nodes.new("ShaderNodeMix")
    vid.data_type = "RGBA"
    vid.inputs["B"].default_value = (0.06, 0.08, 0.10, 1)
    nt.links.new(corte.outputs["Value"], vid.inputs["Factor"])
    nt.links.new(rampa.outputs["Color"], vid.inputs["A"])
    nt.links.new(vid.outputs["Result"], bsdf.inputs["Base Color"])
    return m


# ----------------------------------------------------------------------------------- pistas
def rectangulo(bm, ce, cn, dirv, largo, ancho, z):
    de, dn = dirv[1], dirv[0]
    ux, uy = de * largo / 2, dn * largo / 2
    vx, vy = -dn * ancho / 2, de * ancho / 2
    vs = [bm.verts.new((ce + sx * ux + sy * vx, cn + sx * uy + sy * vy, z))
          for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    bm.faces.new(vs)


def mat_asfalto_pista():
    """Asfalto de pista con la textura real (texturas/asfalto), más oscuro y con parches de reparación."""
    m, nt, bsdf = nodos("Asfalto_pista")
    tex_dir = os.path.join(RAIZ, "texturas", "asfalto")
    if not os.path.exists(os.path.join(tex_dir, "color.jpg")):
        return mat_asfalto()
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapa = nt.nodes.new("ShaderNodeMapping")
    mapa.inputs["Scale"].default_value = (0.25, 0.25, 0.25)
    nt.links.new(coord.outputs["Object"], mapa.inputs["Vector"])

    def img(nombre, dato):
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(os.path.join(tex_dir, nombre), check_existing=True)
        if dato:
            t.image.colorspace_settings.name = "Non-Color"
        nt.links.new(mapa.outputs["Vector"], t.inputs["Vector"])
        return t
    col = img("color.jpg", False)
    tinte = nt.nodes.new("ShaderNodeMix")
    tinte.data_type = "RGBA"
    tinte.blend_type = "MULTIPLY"
    tinte.inputs["Factor"].default_value = 1.0
    tinte.inputs["B"].default_value = (0.55, 0.55, 0.56, 1)
    nt.links.new(col.outputs["Color"], tinte.inputs["A"])
    parches = nt.nodes.new("ShaderNodeTexNoise")              # parches de recapeo más oscuros
    parches.inputs["Scale"].default_value = 0.02
    parches.inputs["Detail"].default_value = 2
    nt.links.new(coord.outputs["Object"], parches.inputs["Vector"])
    corte = nt.nodes.new("ShaderNodeMapRange")
    corte.inputs["From Min"].default_value = 0.55
    corte.inputs["From Max"].default_value = 0.6
    corte.inputs["To Max"].default_value = 0.45
    nt.links.new(parches.outputs["Fac"], corte.inputs["Value"])
    osc = nt.nodes.new("ShaderNodeMix")
    osc.data_type = "RGBA"
    osc.blend_type = "MULTIPLY"
    osc.inputs["B"].default_value = (0.55, 0.55, 0.55, 1)
    nt.links.new(corte.outputs["Result"], osc.inputs["Factor"])
    nt.links.new(tinte.outputs["Result"], osc.inputs["A"])
    nt.links.new(osc.outputs["Result"], bsdf.inputs["Base Color"])
    nt.links.new(img("rugosidad.jpg", True).outputs["Color"], bsdf.inputs["Roughness"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(img("normal.jpg", True).outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def mat_goma():
    """Depósitos de goma de los neumáticos en la zona de toma de contacto: oscuro, irregular y semitransparente."""
    m, nt, bsdf = nodos("Goma_pista")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    est = nt.nodes.new("ShaderNodeMapping")
    est.inputs["Scale"].default_value = (0.06, 0.06, 1.0)
    nt.links.new(coord.outputs["Object"], est.inputs["Vector"])
    ru = nt.nodes.new("ShaderNodeTexNoise")
    ru.inputs["Scale"].default_value = 3.0
    ru.inputs["Detail"].default_value = 6
    nt.links.new(est.outputs["Vector"], ru.inputs["Vector"])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.4
    mr.inputs["From Max"].default_value = 0.65
    mr.inputs["To Max"].default_value = 0.75
    nt.links.new(ru.outputs["Fac"], mr.inputs["Value"])
    bsdf.inputs["Base Color"].default_value = (0.012, 0.012, 0.013, 1)
    bsdf.inputs["Roughness"].default_value = 0.55
    nt.links.new(mr.outputs["Result"], bsdf.inputs["Alpha"])
    return m


def _en_otra_pista(rw, e, n):
    for otra in D["runways"]:
        if otra is rw:
            continue
        cn, ce = otra["center"]
        dn, de = otra["dir"]
        rx, ry = e - ce, n - cn
        if abs(rx * de + ry * dn) < otra["length"] / 2 and abs(-rx * dn + ry * de) < otra["width"] / 2 + 3:
            return True
    return False


def _objeto(nombre, bm, mats):
    me = bpy.data.meshes.new(nombre)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(nombre, me)
    bpy.context.collection.objects.link(ob)
    return ob


def ayudas_pista(rw, blanco):
    """Marcas OACI adicionales, goma, luces de borde y umbral, PAPI y manga de viento de una pista."""
    cn, ce = rw["center"]
    dn, de = rw["dir"]
    L, W = rw["length"], rw["width"]
    ident = "-".join(rw["idents"])

    def P(s, off):
        return ce + de * s - dn * off, cn + dn * s + de * off

    # punto de visada (a 400 m) y zona de toma de contacto (pares de barras a 150, 600, 750 y 900 m)
    bm = bmesh.new()
    for fin in (-1, 1):
        def s_de(d):
            return fin * (L / 2 - d)
        for lado in (-1, 1):
            x, y = P(s_de(400 + 22.5), lado * 12.0)
            rectangulo(bm, x, y, rw["dir"], 45, 6.0, 0.065)
            for d, barras in ((150, 3), (600, 2), (750, 2), (900, 1)):
                if d > L / 2 - 100:
                    continue
                for b in range(barras):
                    x, y = P(s_de(d + 11.25), lado * (9.5 + b * 3.3))
                    rectangulo(bm, x, y, rw["dir"], 22.5, 1.8, 0.065)
    _objeto("Pista_" + ident + "_marcas_tdz", bm, [blanco])
    # depósitos de goma entre 150 m y 750 m de cada umbral
    bm = bmesh.new()
    for fin in (-1, 1):
        x, y = P(fin * (L / 2 - 450), 0)
        rectangulo(bm, x, y, rw["dir"], 620, 16.0, 0.062)
    _objeto("Pista_" + ident + "_goma", bm, [mat_goma()])
    # luces de borde cada 60 m (base, cuerpo y lente) y de umbral (verdes) en las dos cabeceras
    bm, bl, bv = bmesh.new(), bmesh.new(), bmesh.new()
    s = -L / 2
    while s <= L / 2 + 0.1:
        for lado in (-1, 1):
            x, y = P(s, lado * (W / 2 + 1.5))
            if _en_otra_pista(rw, x, y):
                continue
            vs = bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.12, radius2=0.08, depth=0.35)["verts"]
            bmesh.ops.translate(bm, vec=Vector((x, y, 0.2)), verts=vs)
            vs = bmesh.ops.create_cone(bl, cap_ends=True, segments=8, radius1=0.1, radius2=0.06, depth=0.12)["verts"]
            bmesh.ops.translate(bl, vec=Vector((x, y, 0.43)), verts=vs)
        s += 60.0
    for fin in (-1, 1):
        for k in range(-8, 9):
            x, y = P(fin * (L / 2 + 2.0), k * (W / 16))
            vs = bmesh.ops.create_cone(bv, cap_ends=True, segments=8, radius1=0.12, radius2=0.07, depth=0.25)["verts"]
            bmesh.ops.translate(bv, vec=Vector((x, y, 0.15)), verts=vs)
    _objeto("Pista_" + ident + "_luces_base", bm, [mat_plano("Luz_base_amarilla", (0.85, 0.65, 0.05, 1), 0.5)])
    _objeto("Pista_" + ident + "_luces", bl, [mat_plano("Lente_luz", (0.95, 0.92, 0.80, 1), 0.1)])
    _objeto("Pista_" + ident + "_luces_umbral", bv, [mat_plano("Lente_verde", (0.10, 0.65, 0.20, 1), 0.1)])
    # PAPI: cuatro cajas a la izquierda de cada cabecera, a 300 m del umbral
    bm = bmesh.new()
    for fin in (-1, 1):
        for k in range(4):
            off = -fin * (W / 2 + 15.0 + k * 9.0)
            x, y = P(fin * (L / 2 - 300), off)
            vs = bmesh.ops.create_cube(bm, size=1.0)["verts"]
            ang = math.atan2(dn, de)
            bmesh.ops.transform(bm, matrix=Matrix.Translation((x, y, 0.55)) @ Matrix.Rotation(ang, 4, "Z")
                                @ Matrix.Diagonal((0.9, 1.4, 0.7, 1)), verts=vs)
            vs = bmesh.ops.create_cube(bm, size=1.0)["verts"]
            bmesh.ops.transform(bm, matrix=Matrix.Translation((x, y, 0.12)) @ Matrix.Diagonal((0.2, 0.2, 0.25, 1)),
                                verts=vs)
    _objeto("Pista_" + ident + "_PAPI", bm, [mat_plano("PAPI_gris", (0.55, 0.56, 0.58, 1), 0.4, 0.5)])
    return P


def manga_de_viento(x, y):
    """Manga de viento naranja y blanca sobre su mástil, junto a la pista principal."""
    bm, bn, bb = bmesh.new(), bmesh.new(), bmesh.new()
    vs = bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.09, radius2=0.06, depth=7.0)["verts"]
    bmesh.ops.translate(bm, vec=Vector((x, y, 3.5)), verts=vs)
    for k in range(5):                                       # cinco franjas, la manga cae un poco
        r0, r1 = 0.45 - k * 0.06, 0.45 - (k + 1) * 0.06
        destino = bn if k % 2 == 0 else bb
        vs = bmesh.ops.create_cone(destino, cap_ends=False, segments=16, radius1=r0, radius2=r1, depth=0.75)["verts"]
        bmesh.ops.transform(destino, matrix=Matrix.Translation((x + 0.4 + k * 0.74, y, 6.75 - k * 0.12))
                            @ Matrix.Rotation(math.radians(95), 4, "Y"), verts=vs)
    _objeto("Manga_viento_mastil", bm, [mat_plano("Mastil_blanco", (0.85, 0.85, 0.85, 1), 0.5)])
    _objeto("Manga_viento_naranja", bn, [mat_plano("Manga_naranja", (0.95, 0.30, 0.03, 1), 0.7)])
    _objeto("Manga_viento_blanca", bb, [mat_plano("Manga_blanca", (0.90, 0.90, 0.88, 1), 0.7)])


def pistas():
    asf, blanco = mat_asfalto_pista(), mat_plano("Pintura_blanca", (0.85, 0.85, 0.83, 1), 0.7)
    for rw in D["runways"]:
        cn, ce = rw["center"]
        dn, de = rw["dir"]
        L, W = rw["length"], rw["width"]
        nombre = "Pista_" + "-".join(rw["idents"])
        bm = bmesh.new()
        rectangulo(bm, ce, cn, rw["dir"], L + 4, W + 6, 0.03)
        me = bpy.data.meshes.new(nombre)
        bm.to_mesh(me)
        ob = bpy.data.objects.new(nombre, me)
        ob.data.materials.append(asf)
        bpy.context.collection.objects.link(ob)
        P = ayudas_pista(rw, blanco)
        if rw is D["runways"][0]:
            manga_de_viento(*P(-(L / 2 - 250), W / 2 + 60.0))

        bm = bmesh.new()
        z = 0.06
        # eje: trazos de 30 m con 20 m de separación (sin cruzar sobre la otra pista)
        s = -L / 2 + 120
        while s < L / 2 - 120:
            x, y = ce + de * (s + 15), cn + dn * (s + 15)
            if not _en_otra_pista(rw, x, y):
                rectangulo(bm, x, y, rw["dir"], 30, 0.9, z)
            s += 50
        # bordes laterales
        for lado in (-1, 1):
            off = lado * (W / 2 - 0.6)
            rectangulo(bm, ce - dn * off, cn + de * off, rw["dir"], L - 10, 0.9, z)
        # umbrales (piano) en ambas cabeceras
        for fin in (-1, 1):
            base = fin * (L / 2 - 6 - 15)
            for k in range(6):
                for lado in (-1, 1):
                    off = lado * (2.7 + k * 3.6)
                    rectangulo(bm, ce + de * base - dn * off, cn + dn * base + de * off, rw["dir"], 30, 1.8, z)
        me = bpy.data.meshes.new(nombre + "_marcas")
        bm.to_mesh(me)
        ob = bpy.data.objects.new(nombre + "_marcas", me)
        ob.data.materials.append(blanco)
        bpy.context.collection.objects.link(ob)

        # números de cabecera, legibles para quien aterriza
        for fin, txt in ((-1, rw["idents"][0]), (1, rw["idents"][1])):
            cu = bpy.data.curves.new("Num_" + txt, "FONT")
            cu.body = txt
            cu.size = 9.0
            cu.align_x = "CENTER"
            cu.align_y = "CENTER"
            ob = bpy.data.objects.new("Num_" + txt, cu)
            p = fin * (L / 2 - 75)
            ob.location = (ce + de * p, cn + dn * p, 0.07)
            arriba = math.atan2(dn, de) if fin < 0 else math.atan2(-dn, -de)
            ob.rotation_euler = (0, 0, arriba - math.pi / 2)
            ob.scale = (1.0, 1.6, 1.0)
            ob.data.materials.append(blanco)
            bpy.context.collection.objects.link(ob)


# ----------------------------------------------------------------------------------- edificios
def edificios():
    img =bpy.data.images.load(os.path.join(DATOS, "sat_6km.png"))
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)   # fila 0 = sur en Blender

    def color_techo(e, n):
        j = int((e + SAT_INT) / (2 * SAT_INT) * w)
        i = int((n + SAT_INT) / (2 * SAT_INT) * h)
        c = px[max(i - 1, 0):i + 2, max(j - 1, 0):j + 2, :3].reshape(-1, 3).mean(axis=0)
        return (*c.tolist(), 1.0)

    # los edificios que se modelan en detalle no llevan su bloque de OpenStreetMap
    ub = os.path.join(DATOS, "ubicaciones.json")
    excluir = [(u["este"], u["norte"], u["excluir"]) for u in json.load(open(ub, encoding="utf-8"))["edificios"].values()
               if "excluir" in u] if os.path.exists(ub) else []
    bm = bmesh.new()
    capa = bm.loops.layers.float_color.new("techo")
    rnd = random.Random(7)
    n_ed = 0
    for b in D["buildings"]:
        pts = [(p[1], p[0]) for p in b["p"]]           # (norte, este) → (x=este, y=norte)
        if len(pts) > 2 and pts[0] == pts[-1]:
            pts = pts[:-1]
        if len(pts) < 3:
            continue
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        if not (ZONA[0] < cx < ZONA[1] and ZONA[2] < cy < ZONA[3]):
            continue
        if any(math.hypot(cx - e, cy - n) < r or any(math.hypot(x - e, y - n) < r for x, y in pts)
               for e, n, r in excluir):
            continue
        area = 0.5 * abs(sum(pts[i][0] * pts[i - 1][1] - pts[i - 1][0] * pts[i][1] for i in range(len(pts))))
        if area < 12:
            continue
        if area > 2500:
            alto = 13.0 + rnd.random() * 3          # hangares
        elif area > 800:
            alto = 7.5 + rnd.random() * 2.5
        else:
            alto = 3.6 + rnd.choice((0, 0, 0, 3.0)) + rnd.random() * 0.6
        z0 = cota_suave(cx, cy) - 0.3
        try:
            base = [bm.verts.new((x, y, z0)) for x, y in pts]
            cara = bm.faces.new(base)
        except ValueError:
            continue
        cara.normal_update()
        if cara.normal.z < 0:
            cara.normal_flip()
        res = bmesh.ops.extrude_face_region(bm, geom=[cara])
        arriba = [v for v in res["geom"] if isinstance(v, bmesh.types.BMVert)]
        bmesh.ops.translate(bm, vec=Vector((0, 0, alto + 0.3)), verts=arriba)
        techo = [f for f in res["geom"] if isinstance(f, bmesh.types.BMFace)]
        col = color_techo(cx, cy)
        for f in techo:
            if abs(f.normal.z) > 0.9:
                f.material_index = 1
                for lo in f.loops:
                    lo[capa] = col
        n_ed += 1
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new("Edificios")
    bm.to_mesh(me)
    ob = bpy.data.objects.new("Edificios", me)
    ob.data.materials.append(mat_paredes())
    ob.data.materials.append(mat_techos())
    bpy.context.collection.objects.link(ob)
    print("edificios:", n_ed)


# ----------------------------------------------------------------------------------- luz, cielo y cámaras
def ambiente():
    sc = bpy.context.scene
    world = sc.world or bpy.data.worlds.new("Mundo")
    sc.world = world
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes.get("Background")
    sky = nt.nodes.new("ShaderNodeTexSky")
    for tipo in ("MULTIPLE_SCATTERING", "NISHITA", "SINGLE_SCATTERING", "HOSEK_WILKIE"):
        try:
            sky.sky_type = tipo
            break
        except TypeError:
            continue
    elev_sol, az_sol = math.radians(32), math.radians(250)      # tarde, sol del oeste-suroeste
    if hasattr(sky, "sun_elevation"):
        sky.sun_elevation = elev_sol
        sky.sun_rotation = az_sol
    if hasattr(sky, "altitude"):
        sky.altitude = 450
    if hasattr(sky, "air_density"):
        sky.air_density = 1.2
    if hasattr(sky, "dust_density"):
        sky.dust_density = 2.0
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.35

    sol = bpy.data.lights.new("Sol", "SUN")
    sol.energy = 4.0
    sol.angle = math.radians(0.6)
    sol.color = (1.0, 0.95, 0.87)
    ob = bpy.data.objects.new("Sol", sol)
    # la luz apunta desde el azimut del sol (medido desde el norte, horario)
    ob.rotation_euler = (math.pi / 2 - elev_sol, 0, math.pi - az_sol)
    sc.collection.objects.link(ob)

    sc.render.engine = "BLENDER_EEVEE"
    sc.eevee.taa_render_samples = 64
    try:
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    if hasattr(sc.eevee, "use_raytracing"):
        sc.eevee.use_raytracing = False
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080


def camara(nombre, pos, mira, lente=35):
    cam = bpy.data.cameras.new(nombre)
    cam.lens = lente
    cam.clip_start = 0.5
    cam.clip_end = 30000
    ob = bpy.data.objects.new(nombre, cam)
    ob.location = pos
    d = Vector(mira) - Vector(pos)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(ob)
    return ob


def main():
    bpy.ops.wm.read_homefile(use_empty=True)
    terreno = malla_terreno("Terreno", SAT_INT, 15.0, "sat_6km.png")
    # la sierra a 40 m de malla (relieve fino) y, alrededor, el paisaje regional de 51 km con hueco en el centro
    lejos = malla_terreno("Paisaje_lejano", SAT_EXT, 40.0, "sat_20km.png", bajar=4.0, aplanar=False)
    malla_terreno("Paisaje_regional", SAT_REG, 200.0, "sat_51km.png", bajar=10.0, aplanar=False, hueco=SAT_EXT,
                  agua=("agua_51km.png", SAT_REG))
    pistas()
    edificios()
    ambiente()
    rw = D["runways"][0]
    cn, ce = rw["center"]
    dn, de = rw["dir"]
    ext = (ce - de * (rw["length"] / 2 + 15), cn - dn * (rw["length"] / 2 + 15))
    aerea = camara("Cam_Aerea", (1900, -1500, 650), (-50, 250, 0), 32)
    camara("Cam_Cabecera11", (ext[0] - de * 40, ext[1] - dn * 40, 2.2), (ce, cn, 0), 40)
    # sobre la pista, a la altura de una cabina en el umbral 11, y en final corta (con la sierra al frente)
    um = (ce - de * (rw["length"] / 2 - 20), cn - dn * (rw["length"] / 2 - 20))
    camara("Cam_Pista", (um[0], um[1], 2.0), (ce + de * 400, cn + dn * 400, 6.0), 28)
    camara("Cam_Final", (um[0] - de * 1500, um[1] - dn * 1500, 85.0), (ce, cn, 0), 30)
    camara("Cam_Sierra", (2500.0, -5500.0, 1400.0), (0.0, 6000.0, 600.0), 24)
    camara("Cam_Pistas_Aerea", (-1200.0, -1700.0, 700.0), (200.0, -100.0, 0.0), 28)
    bpy.context.scene.camera = aerea
    del terreno, lejos
    salida = os.path.join(RAIZ, "BaseSucre.blend")
    bpy.ops.wm.save_as_mainfile(filepath=salida)
    print("guardado", salida)


main()
