"""Entrada principal de la Base Aérea Escuela «Mariscal Sucre», modelada a partir de las fotos de referencias/.

Se ejecuta sobre BaseSucre.blend (después de construir_base.py) y la guarda de nuevo:
    blender --background BaseSucre.blend --python entrada.py

Todo cuelga del vacío «Entrada_origen», puesto sobre la portada que se ve en la foto satelital. En su marco local
+Y es el sentido de entrada (hacia el interior de la base, al suroeste), +X queda a la derecha de quien entra y Z = 0
es el nivel de la calle. Para corregir la ubicación basta con mover o girar ese vacío.
"""
import json
import math
import os
import random

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector, noise

ESTE, NORTE = 1440.0, 331.0     # centro de la portada (m desde el punto de referencia de SVBS)
RUMBO_ENTRADA = 222.0           # rumbo de la vía al entrar (grados desde el norte)
SOL_AZ, SOL_EL = 95.0, 38.0     # sol de media mañana, como en las fotos: la fachada exterior queda iluminada
rnd = random.Random(11)


# ----------------------------------------------------------------------------------- utilidades
def limpiar():
    col = bpy.data.collections.get("Entrada")
    if col:
        for ob in list(col.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.collections.remove(col)
    col = bpy.data.collections.new("Entrada")
    bpy.context.scene.collection.children.link(col)
    return col


def material(nombre, color, rug=0.6, metal=0.0):
    m = bpy.data.materials.get(nombre)
    if m:
        return m
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rug
    b.inputs["Metallic"].default_value = metal
    return m


def con_ruido(m, c1, c2, escala=1.0, bump=0.0, escala_bump=20.0, fade=None):
    """Color entre c1 y c2 según ruido en coordenadas del objeto; fade=(r0, r1) desvanece el borde."""
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    ru = nt.nodes.new("ShaderNodeTexNoise")
    ru.inputs["Scale"].default_value = escala
    ru.inputs["Detail"].default_value = 6
    nt.links.new(coord.outputs["Object"], ru.inputs["Vector"])
    ra = nt.nodes.new("ShaderNodeValToRGB")
    ra.color_ramp.elements[0].color = (*c1, 1)
    ra.color_ramp.elements[1].color = (*c2, 1)
    nt.links.new(ru.outputs["Fac"], ra.inputs["Fac"])
    nt.links.new(ra.outputs["Color"], b.inputs["Base Color"])
    if bump:
        g = nt.nodes.new("ShaderNodeTexNoise")
        g.inputs["Scale"].default_value = escala_bump
        nt.links.new(coord.outputs["Object"], g.inputs["Vector"])
        bp = nt.nodes.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = bump
        nt.links.new(g.outputs["Fac"], bp.inputs["Height"])
        nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    if fade:
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(coord.outputs["Object"], sep.inputs["Vector"])
        comb = nt.nodes.new("ShaderNodeCombineXYZ")
        nt.links.new(sep.outputs["X"], comb.inputs["X"])
        nt.links.new(sep.outputs["Y"], comb.inputs["Y"])
        lon = nt.nodes.new("ShaderNodeVectorMath")
        lon.operation = "LENGTH"
        nt.links.new(comb.outputs["Vector"], lon.inputs[0])
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value = fade[0]
        mr.inputs["From Max"].default_value = fade[1]
        mr.inputs["To Min"].default_value = 1.0
        mr.inputs["To Max"].default_value = 0.0
        nt.links.new(lon.outputs["Value"], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], b.inputs["Alpha"])
    return m


TEXTURAS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "texturas")


def pbr(nombre, carpeta, metros, tinte=None, metal=0.0, fade=None, variacion=None, pintura=None):
    """Material con las texturas de Poly Haven (color, normal, rugosidad) proyectadas en caja.

    metros: tamaño real de un mosaico. tinte: color que multiplica la foto. pintura: superficie pintada de ese
    color, con la foto apenas marcando manchas y relieve. variacion: (escala, color) de manchas grandes para que la
    repetición no se note. fade: (r0, r1) borde que se desvanece."""
    m = bpy.data.materials.get(nombre)
    if m:
        return m
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapa = nt.nodes.new("ShaderNodeMapping")
    mapa.inputs["Scale"].default_value = (1 / metros, 1 / metros, 1 / metros)
    nt.links.new(coord.outputs["Object"], mapa.inputs["Vector"])

    def img(archivo, dato):
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(os.path.join(TEXTURAS, carpeta, archivo), check_existing=True)
        if dato:
            t.image.colorspace_settings.name = "Non-Color"
        t.projection = "BOX"
        t.projection_blend = 0.3
        nt.links.new(mapa.outputs["Vector"], t.inputs["Vector"])
        return t

    color = img("color.jpg", False).outputs["Color"]
    nt.links.new(img("rugosidad.jpg", True).outputs["Color"], b.inputs["Roughness"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(img("normal.jpg", True).outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    if tinte:
        mx = nt.nodes.new("ShaderNodeMix")
        mx.data_type = "RGBA"
        mx.blend_type = "MULTIPLY"
        mx.inputs["Factor"].default_value = 1.0
        mx.inputs["B"].default_value = (*tinte, 1)
        nt.links.new(color, mx.inputs["A"])
        color = mx.outputs["Result"]
    if pintura:
        mx = nt.nodes.new("ShaderNodeMix")
        mx.data_type = "RGBA"
        mx.blend_type = "MULTIPLY"
        mx.inputs["Factor"].default_value = 0.35
        mx.inputs["A"].default_value = (*pintura, 1)
        nt.links.new(color, mx.inputs["B"])
        color = mx.outputs["Result"]
    if variacion:
        ru = nt.nodes.new("ShaderNodeTexNoise")
        ru.inputs["Scale"].default_value = variacion[0]
        ru.inputs["Detail"].default_value = 4
        nt.links.new(coord.outputs["Object"], ru.inputs["Vector"])
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value = 0.4
        mr.inputs["From Max"].default_value = 0.7
        mr.inputs["To Max"].default_value = 0.6
        nt.links.new(ru.outputs["Fac"], mr.inputs["Value"])
        mx = nt.nodes.new("ShaderNodeMix")
        mx.data_type = "RGBA"
        mx.blend_type = "MULTIPLY"
        mx.inputs["B"].default_value = (*variacion[1], 1)
        nt.links.new(mr.outputs["Result"], mx.inputs["Factor"])
        nt.links.new(color, mx.inputs["A"])
        color = mx.outputs["Result"]
    nt.links.new(color, b.inputs["Base Color"])
    b.inputs["Metallic"].default_value = metal
    if fade:
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(coord.outputs["Object"], sep.inputs["Vector"])
        comb = nt.nodes.new("ShaderNodeCombineXYZ")
        nt.links.new(sep.outputs["X"], comb.inputs["X"])
        nt.links.new(sep.outputs["Y"], comb.inputs["Y"])
        lon = nt.nodes.new("ShaderNodeVectorMath")
        lon.operation = "LENGTH"
        nt.links.new(comb.outputs["Vector"], lon.inputs[0])
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value = fade[0]
        mr.inputs["From Max"].default_value = fade[1]
        mr.inputs["To Min"].default_value = 1.0
        mr.inputs["To Max"].default_value = 0.0
        nt.links.new(lon.outputs["Value"], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], b.inputs["Alpha"])
    return m


def mats():
    M = {}
    M["blanco"] = pbr("Pared_blanca", "pared", 3.0, pintura=(0.86, 0.87, 0.87))
    M["gris"] = pbr("Pared_gris", "pared", 3.0, pintura=(0.075, 0.08, 0.09))     # gris oscuro de la foto aérea
    M["cielo_raso"] = material("Cielo_raso", (0.55, 0.56, 0.57), 0.8)
    M["vidrio"] = material("Vidrio_oscuro", (0.015, 0.02, 0.03), 0.04)
    M["letras"] = material("Letras_azul", (0.03, 0.06, 0.20), 0.4)
    M["dorado"] = material("Dorado", (0.85, 0.62, 0.22), 0.3, 1.0)
    M["azul_emblema"] = material("Azul_emblema", (0.04, 0.12, 0.45), 0.4)
    M["granito"] = material("Granito_negro", (0.018, 0.018, 0.022), 0.12)
    M["placa"] = material("Placa_gris", (0.35, 0.36, 0.38), 0.25, 0.6)
    M["jardinera"] = material("Jardinera_verde", (0.07, 0.30, 0.08), 0.55)
    M["naranja"] = material("Cono_naranja", (0.95, 0.25, 0.02), 0.45)
    M["llanta"] = material("Caucho", (0.02, 0.02, 0.02), 0.7)
    M["auto_blanco"] = material("Auto_blanco", (0.85, 0.86, 0.88), 0.25, 0.3)
    M["auto_negro"] = material("Auto_negro", (0.03, 0.035, 0.04), 0.2, 0.4)
    M["poste"] = material("Poste_gris", (0.45, 0.46, 0.47), 0.4, 0.8)
    M["luz"] = material("Luz_farol", (1.0, 0.95, 0.85), 0.3)
    M["pintura"] = bpy.data.materials.get("Pintura_blanca") or material("Pintura_blanca", (0.85, 0.85, 0.83), 0.7)
    M["amarillo"] = material("Pintura_amarilla", (0.95, 0.70, 0.05), 0.6)
    M["oro_erizo"] = material("Erizo_dorado", (0.80, 0.62, 0.18), 0.35, 0.8)
    M["tierra"] = con_ruido(bpy.data.materials.new("Tierra_jardin"), (0.12, 0.07, 0.04), (0.22, 0.14, 0.08), 3.0, 0.3)
    M["concreto"] = pbr("Concreto", "acera", 2.5, (0.85, 0.85, 0.82))
    M["acera"] = pbr("Acera", "acera", 2.0)
    M["asfalto"] = pbr("Asfalto_calle", "asfalto", 4.0, (0.75, 0.75, 0.75), fade=(95.0, 125.0),
                       variacion=(0.06, (0.55, 0.55, 0.55)))
    M["pasto"] = pbr("Pasto", "pasto", 2.5, (0.45, 0.95, 0.30), fade=(90.0, 125.0),
                     variacion=(0.05, (0.85, 0.75, 0.45)))
    # techo de lámina ondulada pintada de rojo
    M["techo"] = pbr("Techo_rojo_lamina", "lamina", 2.0, metal=0.15, pintura=(0.26, 0.022, 0.014))    # rojo ladrillo (antes salía rosado)

    # camuflaje del avión del monumento
    m = bpy.data.materials.new("Camuflaje")
    m.use_nodes = True
    nt = m.node_tree
    coord = nt.nodes.new("ShaderNodeTexCoord")
    ru = nt.nodes.new("ShaderNodeTexNoise")
    ru.inputs["Scale"].default_value = 0.5
    ru.inputs["Detail"].default_value = 2
    nt.links.new(coord.outputs["Object"], ru.inputs["Vector"])
    ra = nt.nodes.new("ShaderNodeValToRGB")
    ra.color_ramp.interpolation = "CONSTANT"
    ra.color_ramp.elements[0].color = (0.05, 0.09, 0.04, 1)
    ra.color_ramp.elements[1].position = 0.62
    ra.color_ramp.elements[1].color = (0.20, 0.18, 0.09, 1)
    e = ra.color_ramp.elements.new(0.45)
    e.color = (0.11, 0.17, 0.07, 1)
    nt.links.new(ru.outputs["Fac"], ra.inputs["Fac"])
    b = nt.nodes.get("Principled BSDF")
    nt.links.new(ra.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.45
    M["camuflaje"] = m

    # vegetación
    M["tronco_palma"] = con_ruido(bpy.data.materials.new("Tronco_palma"), (0.45, 0.43, 0.40), (0.68, 0.66, 0.62),
                                  4.0, 0.4, 6.0)
    M["capitel"] = material("Capitel_palma", (0.18, 0.32, 0.08), 0.5)
    M["hoja_palma"] = material("Hoja_palma", (0.09, 0.24, 0.04), 0.45)
    M["tronco"] = material("Tronco_arbol", (0.16, 0.12, 0.09), 0.85)
    M["follaje"] = con_ruido(bpy.data.materials.new("Follaje"), (0.02, 0.07, 0.012), (0.09, 0.20, 0.03), 1.2)
    M["follaje_int"] = material("Follaje_interior", (0.012, 0.04, 0.008), 0.8)
    M["flor_roja"] = material("Flor_roja", (0.75, 0.03, 0.05), 0.5)
    M["flor_rosa"] = material("Flor_rosa", (0.85, 0.25, 0.45), 0.5)
    M["flor_amarilla"] = material("Flor_amarilla", (0.95, 0.75, 0.05), 0.5)
    M["arbusto"] = con_ruido(bpy.data.materials.new("Arbusto"), (0.04, 0.14, 0.02), (0.20, 0.35, 0.05), 2.0, 0.4)
    return M


def objeto(nombre, bm, materiales, padre, col):
    me = bpy.data.meshes.new(nombre)
    bm.to_mesh(me)
    bm.free()
    for m in materiales:
        me.materials.append(m)
    suavizar(me)
    ob = bpy.data.objects.new(nombre, me)
    col.objects.link(ob)
    ob.parent = padre
    return ob


def suavizar(me, angulo=35.0):
    """Curvas suaves (fuselaje, troncos, copas) y aristas vivas en cajas."""
    try:
        me.shade_smooth()
        me.set_sharp_from_angle(angle=math.radians(angulo))
    except AttributeError:
        pass


def _caras(verts):
    return {f for v in verts for f in v.link_faces}


def caja(bm, centro, tam, mi=0, rot=(0, 0, 0)):
    """Caja con base en centro.z (o centrada si tam se pasa con z negativo no se usa)."""
    vs = bmesh.ops.create_cube(bm, size=1.0)["verts"]
    cx, cy, z0 = centro
    M = (Matrix.Translation((cx, cy, z0 + tam[2] / 2)) @ Euler(rot).to_matrix().to_4x4()
         @ Matrix.Diagonal((*tam, 1)))
    bmesh.ops.transform(bm, matrix=M, verts=vs)
    for f in _caras(vs):
        f.material_index = mi
    return vs


def cilindro(bm, centro, r1, r2, alto, mi=0, seg=16, rot=(0, 0, 0)):
    vs = bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r1, radius2=r2, depth=alto)["verts"]
    M = Matrix.Translation(centro) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Translation((0, 0, alto / 2))
    bmesh.ops.transform(bm, matrix=M, verts=vs)
    for f in _caras(vs):
        f.material_index = mi
    return vs


def casco(bm, puntos, mi=0):
    vs = [bm.verts.new(p) for p in puntos]
    r = bmesh.ops.convex_hull(bm, input=vs)
    for g in r["geom"]:
        if isinstance(g, bmesh.types.BMFace):
            g.material_index = mi
    for g in r.get("geom_interior", []) + r.get("geom_unused", []):
        if isinstance(g, bmesh.types.BMVert) and g.is_valid and not g.link_faces:
            bm.verts.remove(g)


def texto(cuerpo, tam, mat, padre, col, loc, rot, esc=(1, 1, 1), extr=0.0):
    cu = bpy.data.curves.new("Txt_" + cuerpo[:12], "FONT")
    cu.body = cuerpo
    cu.size = tam
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.extrude = extr
    ob = bpy.data.objects.new("Txt_" + cuerpo[:12], cu)
    ob.data.materials.append(mat)
    ob.location, ob.rotation_euler, ob.scale = loc, rot, esc
    col.objects.link(ob)
    ob.parent = padre
    return ob


def logo_plano(nombre, archivo, cx, cz, alto, y, padre, col, rug=0.4, metal=0.0):
    """Calcomanía de un escudo (texturas/logos/<archivo>, PNG con transparencia) en el plano y = cte, mirando a -Y,
    centrada en (cx, cz) y de «alto» metros."""
    ruta = os.path.join(TEXTURAS, "logos", archivo)
    if not os.path.exists(ruta):
        print("falta el logo", ruta)
        return None
    img = bpy.data.images.load(ruta, check_existing=True)
    w, h = img.size
    ancho = alto * w / h
    m = bpy.data.materials.get("Logo_" + archivo)
    if m is None:
        m = bpy.data.materials.new("Logo_" + archivo)
        m.use_nodes = True
        nt = m.node_tree
        b = nt.nodes.get("Principled BSDF")
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = img
        t.interpolation = "Cubic"
        nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
        nt.links.new(t.outputs["Alpha"], b.inputs["Alpha"])
        b.inputs["Roughness"].default_value = rug
        b.inputs["Metallic"].default_value = metal
        if hasattr(m, "surface_render_method"):
            m.surface_render_method = "DITHERED"
    me = bpy.data.meshes.new(nombre)
    me.from_pydata([(cx - ancho / 2, y, cz - alto / 2), (cx + ancho / 2, y, cz - alto / 2),
                    (cx + ancho / 2, y, cz + alto / 2), (cx - ancho / 2, y, cz + alto / 2)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name="UVMap")
    for li, c in zip(range(4), ((0, 0), (1, 0), (1, 1), (0, 1))):
        uv.data[li].uv = c
    me.materials.append(m)
    ob = bpy.data.objects.new(nombre, me)
    col.objects.link(ob)
    ob.parent = padre
    return ob


def letrero_bloque(cuerpo, tam, padre, col, loc, extr=0.07):
    """Letras como las de la portada en la foto: tipo condensado y grueso, blancas, con un contorno gris oscuro
    (copia engrosada detrás) que las hace leer sobre los paneles."""
    fuente = None
    for f in ("impact.ttf", "bahnschrift.ttf"):
        p = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", f)
        if os.path.exists(p):
            fuente = bpy.data.fonts.load(p, check_existing=True)
            break
    blanco = material("Letras_portada_blancas", (0.88, 0.89, 0.90), 0.35)
    gris = material("Letras_portada_contorno", (0.10, 0.11, 0.12), 0.5)
    x, y, z = loc
    t = texto(cuerpo, tam, blanco, padre, col, (x, y - 0.01, z), (math.pi / 2, 0, 0), extr=extr)
    c = texto(cuerpo, tam, gris, padre, col, (x, y + 0.03, z), (math.pi / 2, 0, 0), extr=extr)
    c.data.offset = tam * 0.035
    for o in (t, c):
        if fuente:
            o.data.font = fuente
        o.data.space_character = 1.04
    return t


# ----------------------------------------------------------------------------------- terreno
def preparar_terreno():
    """Cota de la calle en la portada y relieve aplanado alrededor (la foto satelital queda debajo)."""
    ter = bpy.data.objects["Terreno"]
    sc = bpy.context.scene
    if "cota_entrada" in sc:            # ya aplanado en una corrida anterior: no volver a bajarlo
        return sc["cota_entrada"]
    ok, p, _n, _i = ter.ray_cast((ESTE, NORTE, 3000.0), (0, 0, -1))
    z0 = p.z if ok else 0.0
    sc["cota_entrada"] = z0
    for v in ter.data.vertices:
        d = math.hypot(v.co.x - ESTE, v.co.y - NORTE)
        if d < 150:
            v.co.z = z0 - 0.3
        elif d < 240:
            t = (d - 150) / 90
            t = t * t * (3 - 2 * t)
            v.co.z = (z0 - 0.3) * (1 - t) + v.co.z * t
    ter.data.update()
    return z0


def aplanar(este, norte, clave, r_plano=50.0, r_fin=90.0, z0=None):
    """Relieve plano bajo un edificio y su calle; la cota queda guardada en la escena para no repetirlo.

    z0: cota impuesta (para que varios edificios vecinos queden al mismo nivel)."""
    sc = bpy.context.scene
    if clave in sc:
        return sc[clave]
    ter = bpy.data.objects["Terreno"]
    if z0 is None:
        ok, p, _n, _i = ter.ray_cast((este, norte, 3000.0), (0, 0, -1))
        z0 = p.z if ok else 0.0
    for v in ter.data.vertices:
        d = math.hypot(v.co.x - este, v.co.y - norte)
        if d < r_plano:
            v.co.z = z0 - 0.3
        elif d < r_fin:
            t = (d - r_plano) / (r_fin - r_plano)
            t = t * t * (3 - 2 * t)
            v.co.z = (z0 - 0.3) * (1 - t) + v.co.z * t
    ter.data.update()
    sc[clave] = z0
    return z0


# ----------------------------------------------------------------------------------- portada
L_BLOQUE = 13.0
X_PASO = 1.0          # medio ancho del pilar central
A_PASO = 7.0          # ancho de cada paso vehicular
FONDO = 12.0
H_PB = 4.0            # altura libre bajo el friso
H_FRISO = 2.2
X_EXT = X_PASO + A_PASO + L_BLOQUE     # 21 m: medio largo del edificio


def portada(M, padre, col):
    bm = bmesh.new()
    y0, y1 = -FONDO / 2, FONDO / 2
    # bloques de oficinas a cada lado y pilar central
    for s in (-1, 1):
        xc = s * (X_PASO + A_PASO + L_BLOQUE / 2)
        caja(bm, (xc, 0, 0), (L_BLOQUE, FONDO, H_PB), 0)
        # ventanas en las dos fachadas largas
        for k in range(4):
            xv = xc - L_BLOQUE / 2 + 1.9 + k * 3.1
            for yf in (y0,):        # la cara de adentro (mural, ventanas con reja) la hace entrada_adentro.py
                sg = -1 if yf < 0 else 1
                caja(bm, (xv, yf + sg * 0.03, 0.9), (2.2, 0.08, 1.9), 1)       # marco blanco
                caja(bm, (xv, yf + sg * 0.07, 1.0), (1.95, 0.06, 1.7), 2)      # vidrio
                for kk in (1, 2, 3):                                            # reja blanca
                    caja(bm, (xv - 0.975 + kk * 0.4875, yf + sg * 0.12, 1.0), (0.035, 0.035, 1.7), 1)
                for zz in (1.57, 2.13):
                    caja(bm, (xv, yf + sg * 0.12, zz), (1.95, 0.035, 0.035), 1)
                caja(bm, (xv, yf + sg * 0.14, 0.86), (2.35, 0.2, 0.06), 1)        # alféizar
        # puerta de vidrio hacia el paso
        caja(bm, (s * (X_PASO + A_PASO) + s * 0.02, 0, 0), (0.08, 2.0, 2.4), 2)
    # isla central: columnas redondas grises (fotos desde adentro), no un pilar macizo
    for yc in (-FONDO / 2 + 0.6, FONDO / 2 - 0.6):          # columna central cuadrada gris (fotos de adentro)
        caja(bm, (0, yc, 0), (0.55, 0.55, H_PB), 0)
    # friso blanco que corre sobre los pasos
    caja(bm, (0, 0, H_PB), (2 * X_EXT + 0.6, FONDO + 0.6, H_FRISO), 1)
    # cielo raso de los pasos (un poco por debajo del friso)
    for s in (-1, 1):
        caja(bm, (s * (X_PASO + A_PASO / 2), 0, H_PB - 0.05), (A_PASO, FONDO, 0.05), 3)
    oscuro = bpy.data.materials.get("Pared_portada_oscura") or con_ruido(
        material("Pared_portada_oscura", (0.05, 0.055, 0.06), 0.75), (0.035, 0.038, 0.042), (0.07, 0.074, 0.08), 1.5, 0.15)
    ob = objeto("Portada", bm, [oscuro, M["blanco"], M["vidrio"], M["cielo_raso"]], padre, col)

    # techo a cuatro aguas de lámina roja
    bm = bmesh.new()
    Lr, Wr = 2 * X_EXT + 2.0, FONDO + 2.0
    ze, zc = H_PB + H_FRISO, H_PB + H_FRISO + 1.9
    a = [bm.verts.new(p) for p in ((-Lr / 2, -Wr / 2, ze), (Lr / 2, -Wr / 2, ze), (Lr / 2, Wr / 2, ze),
                                   (-Lr / 2, Wr / 2, ze))]
    c = [bm.verts.new(p) for p in ((-(Lr - Wr) / 2, 0, zc), ((Lr - Wr) / 2, 0, zc))]
    bm.faces.new((a[0], a[1], c[1], c[0]))
    bm.faces.new((a[2], a[3], c[0], c[1]))
    bm.faces.new((a[1], a[2], c[1]))
    bm.faces.new((a[3], a[0], c[0]))
    bm.faces.new((a[3], a[2], a[1], a[0]))
    objeto("Techo_portada", bm, [M["techo"]], padre, col)

    # foto de frente (2026-11-07): el friso de afuera es un revestimiento de paneles de aluminio gris con juntas
    # verticales, más alto que el alero (desde la calle no se ve el techo); letras de aluminio en relieve y un escudo
    # a cada lado del texto
    H_PAN = H_FRISO + 1.3
    panel = bpy.data.materials.get("Panel_aluminio") or material("Panel_aluminio", (0.36, 0.38, 0.41), 0.4, 0.55)
    junta = material("Junta_panel", (0.12, 0.13, 0.14), 0.6, 0.3)
    bm = bmesh.new()
    yp = y0 - 1.12                                  # delante del alero del techo (que asomaba como una raya roja)
    caja(bm, (0, yp, H_PB - 0.05), (2 * X_EXT + 0.8, 0.12, H_PAN + 0.05), 0)
    for s in (-1, 1):                                   # vuelta del revestimiento en las puntas
        caja(bm, (s * (X_EXT + 0.4), yp + 2.0, H_PB - 0.05), (0.12, 4.0, H_PAN + 0.05), 0)
    x = -X_EXT
    while x <= X_EXT:
        caja(bm, (x, yp - 0.065, H_PB - 0.05), (0.04, 0.02, H_PAN + 0.05), 1)
        x += 1.6
    caja(bm, (0, yp - 0.07, H_PB - 0.06), (2 * X_EXT + 0.8, 0.04, 0.1), 1)       # junta inferior
    objeto("Portada_paneles", bm, [panel, junta], padre, col)
    yz = yp - 0.08
    zt = H_PB + H_PAN * 0.52
    # foto de frente: letras blancas condensadas con contorno oscuro y, pegado a cada punta del texto, un escudo:
    # Aviación Militar Bolivariana a la izquierda y Base Escuela «Mariscal Sucre» a la derecha
    t = letrero_bloque('BASE AÉREA ESCUELA “MARISCAL SUCRE”', 1.15, padre, col, (0, yz - 0.02, zt))
    bpy.context.view_layer.update()
    mitad = t.dimensions.x / 2
    for nombre, archivo, s in (("Logo_AMB_portada", "amb.png", -1), ("Logo_BaseSucre_portada", "base_sucre.png", 1)):
        logo_plano(nombre, archivo, s * (mitad + 1.15), zt + 0.05, 2.1, yz - 0.05, padre, col)
    return ob


def panel_27n(M, padre, col):
    """Muro de granito negro con el «27N» grande de colores (2 amarillo, 7 azul con estrellas, N rojo). Ella: primero
    (desde la portada) viene el monolito negro con el avión y DESPUÉS este paredón negro, más allá del monumento."""
    bm = bmesh.new()
    cx, cy = 45.0, -10.0
    caja(bm, (cx, cy, 0.0), (9.0, 0.6, 2.3), 0)
    caja(bm, (cx, cy, 2.3), (9.2, 0.7, 0.08), 0)
    objeto("Panel_27N", bm, [M["granito"]], padre, col)
    for k, (ch, color) in enumerate((("2", (0.95, 0.72, 0.03)), ("7", (0.03, 0.12, 0.50)), ("N", (0.70, 0.04, 0.05)))):
        mat = material("Letra_27N_" + ch, color, 0.4)
        texto(ch, 1.9, mat, padre, col, (cx - 1.7 + k * 1.7, cy - 0.32, 1.3), (math.pi / 2, 0, 0), extr=0.12)
    bm = bmesh.new()
    for k in range(8):                                    # estrellas blancas sobre el 7
        a = math.pi * (0.15 + 0.7 * k / 7)
        cilindro(bm, (cx + 0.55 * math.cos(a), cy - 0.46, 1.25 + 0.55 * math.sin(a)), 0.07, 0.07, 0.02, 0, 5,
                 (math.pi / 2, 0, 0))
    objeto("Panel_27N_estrellas", bm, [M["pintura"]], padre, col)


def columnas_y_garita(M, padre, col):
    bm = bmesh.new()
    # dos columnas blancas con farol a los lados de los pasos
    for s in (-1, 1):
        x = s * (X_PASO + A_PASO + 0.7)
        caja(bm, (x, -FONDO / 2 - 2.0, 0.15), (1.1, 1.1, 0.5), 0)
        caja(bm, (x, -FONDO / 2 - 2.0, 0.65), (0.7, 0.7, 3.3), 0)
        casco(bm, [(x - 0.5, -FONDO / 2 - 2.5, 3.95), (x + 0.5, -FONDO / 2 - 2.5, 3.95),
                   (x + 0.5, -FONDO / 2 - 1.5, 3.95), (x - 0.5, -FONDO / 2 - 1.5, 3.95),
                   (x, -FONDO / 2 - 2.0, 4.55)], 0)
    objeto("Columnas", bm, [M["blanco"]], padre, col)

    bm = bmesh.new()
    # ella: la garita está EN EL MEDIO, sobre la isla que divide la calle de entrada de la de salida
    xg, yg = 0.0, -FONDO / 2 - 13.0
    # caseta hueca (ella: «la ventana se ve como una pizarra negra»): antepecho y dintel corridos, esquineros, pared
    # trasera y la del lado de la puerta; ventanales de vidrio claro con perfiles blancos y adentro el mostrador, la
    # silla, un monitor y la lámpara del techo, que se ven a través del vidrio
    W, D, z0, zv0, zv1, zt = 3.0, 2.6, 0.15, 1.1, 2.4, 2.9
    caja(bm, (xg, yg, z0), (W, D, zv0 - z0), 0)                      # antepecho (y mesón por dentro)
    caja(bm, (xg, yg, zv1), (W, D, zt - zv1), 0)                     # dintel y techo
    for sx in (-1, 1):
        for sy in (-1, 1):
            caja(bm, (xg + sx * (W / 2 - 0.1), yg + sy * (D / 2 - 0.1), zv0), (0.2, 0.2, zv1 - zv0), 0)
    caja(bm, (xg, yg + D / 2 - 0.1, zv0), (W, 0.2, zv1 - zv0), 0)                 # pared trasera
    caja(bm, (xg + W / 2 - 0.1, yg + 0.65, zv0), (0.2, 1.3, zv1 - zv0), 0)       # pared de la puerta
    caja(bm, (xg, yg, 3.2), (5.2, 4.6, 0.35), 2)                     # marquesina
    caja(bm, (xg, yg, 3.55), (5.0, 4.4, 0.1), 0)                     # remate del techo
    caja(bm, (xg + 1.53, yg + 0.6, 0.15), (0.05, 0.9, 2.1), 2)       # puerta metálica al costado
    caja(bm, (xg - 1.6, yg + 0.7, 1.9), (0.3, 0.6, 0.42), 0)         # aire de ventana
    for dx, dy in ((-2.3, -2.0), (2.3, -2.0), (-2.3, 2.0), (2.3, 2.0)):
        caja(bm, (xg + dx, yg + dy, 0.15), (0.18, 0.18, 3.05), 2)
    # vidrios (frente y costados) y perfiles blancos
    caja(bm, (xg, yg - D / 2 + 0.05, zv0), (W - 0.4, 0.02, zv1 - zv0), 1)
    caja(bm, (xg - W / 2 + 0.05, yg, zv0), (0.02, D - 0.4, zv1 - zv0), 1)
    caja(bm, (xg + W / 2 - 0.05, yg - 0.6, zv0), (0.02, 1.0, zv1 - zv0), 1)
    for x in (-0.43, 0.43):
        caja(bm, (xg + x, yg - D / 2 + 0.03, zv0), (0.05, 0.06, zv1 - zv0), 0)
    caja(bm, (xg, yg - D / 2 + 0.03, 1.95), (W - 0.4, 0.06, 0.05), 0)
    for x, ys in ((-W / 2 + 0.03, (0.0,)), (W / 2 - 0.03, ())):
        for y in ys:
            caja(bm, (xg + x, yg + y, zv0), (0.06, 0.05, zv1 - zv0), 0)
    # adentro: mesón bajo el vidrio del frente, silla, monitor y lámpara
    caja(bm, (xg, yg - 0.8, zv0), (2.4, 0.5, 0.04), 4)
    caja(bm, (xg + 0.5, yg - 0.75, zv0 + 0.04), (0.5, 0.06, 0.32), 4)
    caja(bm, (xg - 0.3, yg - 0.1, z0), (0.45, 0.45, 0.48), 4)
    caja(bm, (xg - 0.3, yg + 0.12, z0 + 0.48), (0.45, 0.06, 0.55), 4)
    caja(bm, (xg, yg, zv1 - 0.03), (0.6, 0.6, 0.02), 5)
    vidrio_g = bpy.data.materials.get("Vidrio_garita")
    if vidrio_g is None:
        vidrio_g = material("Vidrio_garita", (0.10, 0.14, 0.16), 0.03)
        b = vidrio_g.node_tree.nodes.get("Principled BSDF")
        b.inputs["Alpha"].default_value = 0.3
        if hasattr(vidrio_g, "surface_render_method"):
            vidrio_g.surface_render_method = "DITHERED"
    objeto("Garita", bm, [M["blanco"], vidrio_g, M["cielo_raso"], M["jardinera"],
                          material("Mueble_oscuro", (0.05, 0.05, 0.055), 0.6), M["luz"]], padre, col)
    # delante de la garita: tres canteros de grama en fila, a la misma altura, con brocal blanco grueso y las
    # esquinas de afuera redondeadas (foto aérea; ella: «es pasto verde… las divisiones», NO escalones)
    bm, bg = bmesh.new(), bmesh.new()

    def contorno(cx, cy, w, h, r, n=6):
        """Rectángulo con las dos esquinas de -Y redondeadas (radio r)."""
        pts = [(cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)]
        for sx, a0 in ((-1, 180.0), (1, 270.0)):
            ccx, ccy = cx + sx * (w / 2 - r), cy - h / 2 + r
            for k in range(n + 1):
                a = math.radians(a0 + 90.0 * k / n)
                pts.append((ccx + r * math.cos(a), ccy + r * math.sin(a)))
        return pts
    for k in range(3):
        cy = yg - 2.45 - k * 2.05
        out = contorno(xg - 0.15 * k, cy, 3.4, 1.95, 0.55)
        base = [bm.verts.new((x, y, 0.15)) for x, y in out]
        cara = bm.faces.new(base)
        r = bmesh.ops.extrude_face_region(bm, geom=[cara])
        bmesh.ops.translate(bm, vec=Vector((0, 0, 0.32)),
                            verts=[g for g in r["geom"] if isinstance(g, bmesh.types.BMVert)])
        inn = contorno(xg - 0.15 * k, cy, 3.4 - 0.44, 1.95 - 0.44, 0.33)
        bg.faces.new([bg.verts.new((x, y, 0.475)) for x, y in inn])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    objeto("Garita_canteros", bm, [M["blanco"]], padre, col)
    objeto("Pasto_canteros_garita", bg, [M["pasto"]], padre, col)


# ----------------------------------------------------------------------------------- calle, aceras y pintura
def calles(M, padre, col):
    bm = bmesh.new()
    circ = bmesh.ops.create_circle(bm, cap_ends=True, radius=125.0, segments=128)["verts"]
    bmesh.ops.translate(bm, vec=Vector((0, 0, 0.0)), verts=circ)
    objeto("Pasto_entrada", bm, [M["pasto"]], padre, col)

    bm = bmesh.new()
    # afuera y bajo la portada; adentro siguen las vías de la plaza (entrada_adentro.py)
    caja(bm, (0, -25.5, -0.02), (19.0, 69.0, 0.06), 0)          # llega hasta la avenida (satélite), no la cruza
    objeto("Calle_acceso", bm, [M["asfalto"]], padre, col)
    # ella: todo el lado izquierdo (al entrar) es concreto, no grama: patio de concreto desde la calle hasta más allá
    # del bloque de oficinas (foto aérea de la entrada)
    bm = bmesh.new()
    caja(bm, (-22.0, -30.0, -0.01), (25.0, 48.0, 0.1), 0)
    # ella: «que se vea un poco más oscuro»: concreto propio, más gris que el resto
    objeto("Patio_concreto_entrada", bm, [pbr("Concreto_estacionamiento", "concreto_gastado", 2.5, (0.50, 0.50, 0.48),
                                              variacion=(0.05, (0.80, 0.80, 0.78)))], padre, col)
    bm = bmesh.new()                                   # juntas de las losas
    juntas = material("Junta_losa", (0.10, 0.10, 0.10), 0.9)
    for k in range(1, 5):
        caja(bm, (-34.5 + k * 5.0, -30.0, 0.09), (0.05, 48.0, 0.004), 0)
    for k in range(1, 10):
        caja(bm, (-22.0, -54.0 + k * 5.0, 0.09), (25.0, 0.05, 0.004), 0)
    objeto("Patio_concreto_juntas", bm, [juntas], padre, col)
    # foto de frente (2026-11-07): pegada al paredón por dentro va una franja de grama con los árboles grandes de
    # tronco encalado, con su brocal; el estacionamiento queda entre la franja y la calle, con puestos en diagonal
    # (entorno.py planta los árboles en los puntos que deja aquí)
    bm, bg, bb = bmesh.new(), bmesh.new(), bmesh.new()
    # ella: antes del paredón la franja es de TIERRA (no concreto ni grama), con los árboles grandes encima
    xf0, xf1 = -34.85, -27.0
    caja(bg, (0.5 * (xf0 + xf1), -30.0, 0.0), (xf1 - xf0, 48.0, 0.13), 0)
    caja(bb, (xf1, -30.0, 0.0), (0.2, 48.0, 0.2), 0)                       # brocal amarillo de la franja
    caja(bb, (0.5 * (xf0 + xf1), -54.0, 0.0), (xf1 - xf0, 0.2, 0.2), 0)
    tierra = bpy.data.materials.get("Tierra_franja") or con_ruido(material("Tierra_franja", (0.42, 0.31, 0.20), 0.95),
                                                                  (0.36, 0.26, 0.16), (0.58, 0.45, 0.30), 0.8, 0.3, 6.0)
    objeto("Tierra_franja_paredon", bg, [tierra], padre, col)
    objeto("Franja_brocal", bb, [M["amarillo"]], padre, col)
    puntos = [(-31.2 + (0.8 if i % 2 else -0.6), y) for i, y in enumerate((-50.0, -41.0, -32.0, -23.0, -14.0))]
    v = bpy.data.objects.new("Puntos_arboles_paredon", None)
    mw = padre.matrix_basis                         # (matrix_world aún no está al día en un objeto nuevo)
    v["puntos"] = json.dumps([list(mw @ Vector((x, yy, 0.16))) for x, yy in puntos])
    col.objects.link(v)
    ang = math.radians(60)                          # puestos en diagonal, inclinados hacia la portada
    largo = 5.2
    y = -52.0
    while y <= -10.0:
        a = Vector((xf1 + 0.15, y))
        b = a + Vector((math.sin(ang), math.cos(ang))) * largo
        m = (a + b) / 2
        caja(bm, (m.x, m.y, 0.09), (0.12, largo, 0.012), 0, (0, 0, -ang))
        y += 2.9
    caja(bm, (xf1 + 0.15 + largo * math.sin(ang), -31.0, 0.09), (0.12, 42.0, 0.012), 0)     # línea del fondo
    objeto("Estacionamiento_puestos", bm, [M["pintura"]], padre, col)

    bm = bmesh.new()
    # isla central bajo el pilar y hacia afuera
    caja(bm, (0, -6.5, 0.0), (2 * X_PASO, 13.0, 0.16), 0)
    # aceras delante y detrás de los bloques de oficinas
    for s in (-1, 1):
        caja(bm, (s * (X_PASO + A_PASO + 7.0), 0, 0.0), (14.0, FONDO + 4.0, 0.15), 0)
    caja(bm, (0.0, -FONDO / 2 - 15.75, 0.0), (5.6, 14.5, 0.16), 0)      # isla de la garita (en el eje)
    objeto("Aceras", bm, [M["acera"]], padre, col)

    bm = bmesh.new()
    z = 0.06              # la pintura queda 2 cm sobre el asfalto (evita parpadeo a distancia)
    yc =-FONDO / 2 - 5.0
    for k in range(-8, 9):
        x = k * 1.0
        if abs(x) < X_PASO + 0.3:
            continue
        caja(bm, (x, yc, z - 0.04), (0.5, 3.2, 0.04), 0)               # paso peatonal
    for s in (-1, 1):
        caja(bm, (s * (X_PASO + A_PASO / 2), yc - 2.6, z - 0.04), (A_PASO - 0.6, 0.45, 0.04), 0)   # línea de pare
        caja(bm, (s * 9.2, -32.0, z - 0.04), (0.15, 48.0, 0.04), 0)    # bordes (de la avenida a la portada)
    s = -56.0
    while s < 0:
        if not (-45.0 < s < 30.0):          # junto a la portada cada sentido es un solo canal (y ahí va el PARE)
            for xl in (-4.5, 4.5):
                caja(bm, (xl, s, z - 0.04), (0.15, 3.0, 0.04), 0)        # división de carril
        s += 9.0
    objeto("Demarcacion", bm, [M["pintura"]], padre, col)
    texto("PARE", 2.2, M["pintura"], padre, col, (-(X_PASO + A_PASO / 2) - 1.2, yc - 6.5, 0.065), (0, 0, 0), (1, 2.1, 1))

    # bordillos amarillos de la isla central
    bm = bmesh.new()
    for s in (-1, 1):
        caja(bm, (s * (X_PASO + 0.05), -6.5, 0.0), (0.12, 13.0, 0.18), 0)          # bajo la portada
        caja(bm, (s * 2.86, -FONDO / 2 - 15.75, 0.0), (0.12, 14.5, 0.2), 0)         # isla de la garita
    for yy in (-FONDO / 2 - 8.5, -FONDO / 2 - 23.0):
        caja(bm, (0.0, yy, 0.0), (5.84, 0.12, 0.2), 0)
    # bordillo amarillo del lado de la grama a lo largo de la calle de acceso (el izquierdo es el patio de concreto)
    caja(bm, (9.6, -33.0, 0.0), (0.18, 46.0, 0.18), 0)
    objeto("Bordillos", bm, [M["amarillo"]], padre, col)
    frente(M, padre, col)


def frente(M, padre, col):
    """Lo de afuera de la portada (ella: «acomoda la parte de al frente… el marcaje, las delimitaciones»).
    La avenida pública pasa en diagonal a ~46 m de la portada (satélite y OSM «road», marco local de la entrada):
    eje por (-8, -66) con rumbo local (0,777; 0,629). Se dibuja aquí el tramo que vias.py deja cortado alrededor de
    la portada, con su demarcación, y en la calle de acceso: flechas, línea discontinua entre carriles, rayado de
    aproximación a la isla de la garita y la boca de acceso con sus bordillos."""
    p0 = Vector((-8.0, -66.0))
    d = Vector((0.777, 0.629)).normalized()
    nrm = Vector((-d.y, d.x))                          # hacia la base
    giro = math.atan2(d.y, d.x)
    t0, t1 = -70.0, 165.0
    c = p0 + d * (0.5 * (t0 + t1))
    L = t1 - t0
    asf = M["asfalto"]
    bm = bmesh.new()
    caja(bm, (c.x, c.y, -0.02), (L, 9.5, 0.06), 0, (0, 0, giro))
    objeto("Avenida_frente", bm, [asf], padre, col)
    bm = bmesh.new()                                   # hombrillo de tierra del lado de afuera
    q = c - nrm * 7.2
    caja(bm, (q.x, q.y, -0.03), (L, 5.0, 0.06), 0, (0, 0, giro))
    objeto("Avenida_hombrillo", bm, [con_ruido(bpy.data.materials.get("Tierra_hombrillo")
                                               or material("Tierra_hombrillo", (0.4, 0.33, 0.24), 0.95),
                                               (0.30, 0.25, 0.18), (0.46, 0.39, 0.29), 0.4)], padre, col)
    # demarcación de la avenida: doble amarilla al centro y blancas en los bordes (cortadas en la boca de acceso)
    bm, by = bmesh.new(), bmesh.new()
    for s in (-0.12, 0.12):
        q = c + nrm * s
        caja(by, (q.x, q.y, 0.04), (L, 0.12, 0.012), 0, (0, 0, giro))
    tb = 0.5 * (t0 + t1)
    t_boca = (Vector((0.0, -60.0)) - p0).dot(d)          # donde la calle de acceso toca la avenida
    for s in (-4.5, 4.5):
        for a, b in ((t0, t_boca - 11.0), (t_boca + 11.0, t1)) if s > 0 else ((t0, t1),):
            q = p0 + d * (0.5 * (a + b)) + nrm * s
            caja(bm, (q.x, q.y, 0.04), (b - a, 0.14, 0.012), 0, (0, 0, giro))
    objeto("Avenida_lineas_blancas", bm, [M["pintura"]], padre, col)
    objeto("Avenida_lineas_amarillas", by, [M["amarillo"]], padre, col)
    # bordillos blancos del lado de la base, con la boca de acceso abierta y sus vueltas
    bm = bmesh.new()
    for a, b in ((t0, t_boca - 13.0), (t_boca + 13.0, t1)):
        q = p0 + d * (0.5 * (a + b)) + nrm * 4.95
        caja(bm, (q.x, q.y, 0.0), (b - a, 0.18, 0.18), 0, (0, 0, giro))
    for s in (-1, 1):                                  # vueltas curvas de la boca
        for k in range(7):
            ang = math.radians(90 * k / 6)
            r = 3.5
            cx, cy = s * (9.5 + r), -53.0
            x = cx - s * r * math.cos(ang)
            y = cy - r * math.sin(ang)
            caja(bm, (x, y, 0.0), (0.6, 0.18, 0.18), 0, (0, 0, -s * ang))
    objeto("Avenida_bordillos", bm, [M["blanco"]], padre, col)
    # calle de acceso: línea discontinua entre carriles, flechas y rayado de aproximación a la isla
    bm = bmesh.new()
    y = -56.0
    while y < -32.0:
        caja(bm, (0.0, y, 0.045), (0.14, 2.5, 0.012), 0)
        y += 5.0
    for s in (-1, 1):                                  # flechas: +X entra (hacia +Y), -X sale (hacia -Y)
        x, y = s * 5.0, -42.0
        caja(bm, (x, y, 0.045), (0.3, 3.2, 0.012), 0)
        sg = 1 if s > 0 else -1
        bm.faces.new([bm.verts.new(v) for v in ((x - 0.7, y + sg * 1.6, 0.058), (x + 0.7, y + sg * 1.6, 0.058),
                                                (x, y + sg * 3.0, 0.058))][::sg])
    # rayado en V delante de la isla de la garita (la isla termina en y = -29)
    for k in range(6):
        yy = -30.0 - k * 1.2
        w = 2.8 * (1 - k / 6)
        for s in (-1, 1):
            caja(bm, (s * w / 2, yy, 0.045), (0.3, 1.6, 0.012), 0, (0, 0, s * 0.6))
    for s in (-1, 1):
        a, b = Vector((s * 2.8, -29.2)), Vector((0.0, -37.5))
        m = (a + b) / 2
        caja(bm, (m.x, m.y, 0.045), ((b - a).length, 0.15, 0.012), 0, (0, 0, math.atan2(b.y - a.y, b.x - a.x)))
    objeto("Demarcacion_acceso", bm, [M["pintura"]], padre, col)
    # ojos de gato a lo largo de la doble amarilla y de los bordes de la calle de acceso
    bm = bmesh.new()
    for k in range(int(L / 12)):
        q = p0 + d * (t0 + 6 + k * 12)
        caja(bm, (q.x, q.y, 0.04), (0.12, 0.12, 0.03), 0, (0, 0, giro))
    for y in range(-56, -10, 6):
        for x in (-9.0, 9.0):
            caja(bm, (x, y, 0.04), (0.12, 0.12, 0.03), 0)
    objeto("Ojos_de_gato", bm, [material("Reflector_ambar", (0.9, 0.55, 0.05), 0.3, 0.2)], padre, col)
    # paredón perimetral sobre la avenida (ella: «el muro sobre la avenida»), del lado de la base, a los dos lados de
    # la entrada; abierto en la boca del acceso y en la plaza del monumento. SIN FOTO TODAVÍA: muro neutro blanco con
    # pilastras, remate y zócalo gris; cambiar color y remate cuando llegue la foto.
    # foto lateral de la entrada: el paredón es de concreto color arena, con el remate un poco más oscuro
    blanco = pbr("Paredon_arena", "friso", 3.0, pintura=(0.72, 0.64, 0.50))
    zocalo = pbr("Paredon_zocalo", "concreto_gastado", 2.0, pintura=(0.30, 0.30, 0.30))
    # ella: «falta el paredón a los lados»: arranca en cada punta del edificio de la portada (x = ±21) y corre
    # paralelo a la avenida hacia los dos lados (110 m cada uno). El monumento y el patio de concreto quedan afuera,
    # entre el paredón y la avenida.
    # ella (2026-11-07, con dibujo): el paredón sale de cada punta de la portada RECTO hacia la avenida, a los lados
    # del acceso. Del lado izquierdo va por fuera del estacionamiento de concreto (que es para quien espera afuera):
    # un tramo corto pegado a la portada hasta x = -35 y de ahí recto a la avenida.
    Hm = 2.6

    def hasta_avenida(x, retiro=9.0):
        return p0.y + (retiro - nrm.x * (x - p0.x)) / nrm.y

    xd, xi = X_EXT + 0.2, -35.0
    abajo = Vector((0.0, -1.0))
    # (foto de frente: del lado derecho, hacia el monumento y el 27N, no hay paredón: queda abierto)
    tramos = [(Vector((-X_EXT - 0.2, 0.3)), Vector((-1.0, 0.0)), -X_EXT - 0.2 - xi),
              (Vector((xi, 0.3)), abajo, 0.3 - hasta_avenida(xi))]
    bm, bz, bp = bmesh.new(), bmesh.new(), bmesh.new()
    for ini, u, Lw in tramos:
        gu = math.atan2(u.y, u.x)
        giro = gu
        q = ini + u * (Lw / 2)
        caja(bm, (q.x, q.y, 0.0), (Lw, 0.25, Hm), 0, (0, 0, gu))
        caja(bz, (q.x, q.y, 0.0), (Lw, 0.3, 0.45), 0, (0, 0, gu))
        caja(bp, (q.x, q.y, Hm), (Lw, 0.4, 0.1), 0, (0, 0, gu))
        n = int(Lw / 3.0)
        a, b = 0.0, Lw
        for k in range(n + 1):
            q = ini + u * (a + k * (b - a) / n)
            fin = k in (0, n)
            w = 0.7 if fin else 0.42
            caja(bm, (q.x, q.y, 0.0), (w, w, Hm + (0.35 if fin else 0.15)), 0, (0, 0, giro))
            caja(bp, (q.x, q.y, Hm + (0.35 if fin else 0.15)), (w + 0.1, w + 0.1, 0.08), 0, (0, 0, giro))
    objeto("Paredon", bm, [blanco], padre, col)
    objeto("Paredon_zocalo", bz, [zocalo], padre, col)
    objeto("Paredon_remate", bp, [material("Remate_paredon", (0.48, 0.42, 0.33), 0.8)], padre, col)


# ----------------------------------------------------------------------------------- monumento
def avion(M, padre, col, base, rot):
    """Entrenador turbohélice en camuflaje verde (proporciones de un Tucano: 9,9 m de largo, 11,1 m de envergadura)."""
    bm = bmesh.new()
    # fuselaje: secciones elípticas de cola (y=-5) a nariz (y=+4,9)
    perfil = [(-5.0, 0.12, 0.18, 0.25), (-4.2, 0.22, 0.30, 0.18), (-2.5, 0.40, 0.52, 0.08), (-1.0, 0.55, 0.68, 0.02),
              (1.0, 0.60, 0.70, 0.0), (2.6, 0.58, 0.60, -0.02), (3.8, 0.50, 0.50, -0.05), (4.5, 0.34, 0.34, -0.05),
              (4.9, 0.12, 0.12, -0.05)]
    n = 18
    anillos = []
    for y, rx, rz, zc in perfil:
        anillos.append([bm.verts.new((rx * math.cos(2 * math.pi * k / n), y, zc + rz * math.sin(2 * math.pi * k / n)))
                        for k in range(n)])
    for a, b in zip(anillos, anillos[1:]):
        for k in range(n):
            bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]))
    bm.faces.new(list(reversed(anillos[0])))
    bm.faces.new(anillos[-1])
    # alas bajas con diedro, estabilizadores y deriva
    for s in (-1, 1):
        casco(bm, [(0, 1.3, -0.45), (0, -1.0, -0.45), (0, 1.3, -0.20), (0, -1.0, -0.25),
                   (s * 5.55, 0.65, -0.05), (s * 5.55, -0.5, -0.05), (s * 5.55, 0.65, 0.03), (s * 5.55, -0.5, 0.0)])
        casco(bm, [(0, -3.7, 0.05), (0, -4.9, 0.05), (0, -3.7, 0.15), (0, -4.9, 0.12),
                   (s * 2.3, -4.3, 0.10), (s * 2.3, -4.95, 0.10), (s * 2.3, -4.3, 0.15), (s * 2.3, -4.95, 0.13)])
    casco(bm, [(-0.08, -3.4, 0.4), (0.08, -3.4, 0.4), (-0.08, -5.0, 0.3), (0.08, -5.0, 0.3),
               (-0.04, -4.6, 2.2), (0.04, -4.6, 2.2), (-0.04, -5.3, 2.2), (0.04, -5.3, 2.2)])
    # cabina tándem
    can = bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=10, radius=1.0)["verts"]
    bmesh.ops.transform(bm, matrix=Matrix.Translation((0, 0.3, 0.55)) @ Matrix.Diagonal((0.45, 1.9, 0.45, 1)), verts=can)
    for f in _caras(can):
        f.material_index = 1
    # hélice de tres palas y cono
    cilindro(bm, (0, 4.85, -0.05), 0.20, 0.02, 0.5, 2, 16, (-math.pi / 2, 0, 0))
    for k in range(3):
        caja(bm, (0, 5.0, -0.05), (0.18, 0.04, 1.2), 2, (0, 2 * math.pi * k / 3, 0))
    ob = objeto("Avion_monumento", bm, [M["camuflaje"], M["vidrio"], M["llanta"]], padre, col)
    ob.location = base
    ob.rotation_euler = rot
    return ob


def placa_xz(bm, pts, y, grueso, mi):
    """Placa plana de contorno pts (x, z) sobre un plano Y = y, extruida hacia -Y (calcomanías en relieve)."""
    f = bm.faces.new([bm.verts.new((x, y, z)) for x, z in pts])
    f.material_index = mi
    r = bmesh.ops.extrude_face_region(bm, geom=[f])
    bmesh.ops.translate(bm, vec=Vector((0, -grueso, 0)),
                        verts=[g for g in r["geom"] if isinstance(g, bmesh.types.BMVert)])
    for g in r["geom"]:
        if isinstance(g, bmesh.types.BMFace):
            g.material_index = mi


def silueta_jet(cx, cz, s, giro):
    """Contorno de un caza en planta (para los grabados grises del obelisco), girado «giro» en el plano."""
    base = [(0, 1.0), (0.08, 0.6), (0.1, 0.2), (0.62, -0.25), (0.62, -0.38), (0.12, -0.3), (0.1, -0.62),
            (0.32, -0.82), (0.32, -0.92), (0, -0.82)]
    pts = base + [(-x, z) for x, z in reversed(base[1:-1])]
    c, sn = math.cos(giro), math.sin(giro)
    return [(cx + s * (x * c - z * sn), cz + s * (x * sn + z * c)) for x, z in pts]


def monumento(M, padre, col, cx, cy):
    """Monumento del 27N (fotos del obelisco): obelisco de granito negro en cuña sobre un zócalo, con el emblema
    «27N 1992», «POR AHORA Y PARA SIEMPRE», el escudo de la Aviación Militar Bolivariana, la cita del decreto y
    siluetas grises de aviones grabadas; en el zócalo «NADA NI NADIE NOS SACARÁ DEL CAMINO DE LA PATRIA» y la
    firma. Encima, un Tucano en camuflaje subiendo casi vertical. Jardinera circular elevada con bordillo de
    concreto y caminería de concreto estampado alrededor. Cara principal hacia -Y (la calle)."""
    oro = material("Dorado_letras", (0.86, 0.66, 0.26), 0.3, 0.9)
    gris_grab = material("Granito_grabado", (0.45, 0.46, 0.48), 0.4)          # siluetas gris claro, como en la foto
    concreto = M["concreto"]
    # caminería anular, bordillo y jardinera elevada con césped
    bm = bmesh.new()
    cilindro(bm, (cx, cy, 0), 9.5, 9.5, 0.12, 0, 64)
    objeto("Monumento_caminería", bm, [pbr("Concreto_estampado", "acera", 1.2, (0.80, 0.78, 0.74))], padre, col)
    bm = bmesh.new()
    cilindro(bm, (cx, cy, 0), 6.6, 6.6, 0.7, 0, 64)
    cilindro(bm, (cx, cy, 0), 9.6, 9.6, 0.22, 0, 64)
    objeto("Monumento_bordillos", bm, [concreto], padre, col)
    bm = bmesh.new()
    cilindro(bm, (cx, cy, 0), 6.3, 6.3, 0.74, 0, 64)
    objeto("Monumento_cesped", bm, [M["pasto"]], padre, col)
    z0 = 0.74
    # zócalo y obelisco en cuña (más ancho abajo, más delgado arriba)
    bm = bmesh.new()
    caja(bm, (cx, cy, z0), (4.0, 2.2, 1.9), 0)
    zb, zt = z0 + 1.9, z0 + 11.0
    casco(bm, [(cx - 1.55, cy - 0.75, zb), (cx + 1.55, cy - 0.75, zb), (cx + 1.55, cy + 0.75, zb),
               (cx - 1.55, cy + 0.75, zb), (cx - 0.85, cy - 0.4, zt), (cx + 0.85, cy - 0.4, zt),
               (cx + 0.85, cy + 0.4, zt), (cx - 0.85, cy + 0.4, zt)], 0)
    objeto("Obelisco", bm, [M["granito"]], padre, col)

    def yf(z):                                          # cara frontal del obelisco a la altura z
        t = (z - zb) / (zt - zb)
        return cy - (0.75 - 0.35 * t) - 0.012

    def ancho(z):
        t = (z - zb) / (zt - zb)
        return 3.1 - 1.4 * t
    # siluetas grises de aviones grabadas en la cara frontal (detrás del texto)
    bm = bmesh.new()
    for zz, s, g in ((5.4, 1.35, math.radians(35)), (5.2, 1.3, math.radians(-40)), (8.0, 0.9, math.radians(-25))):
        placa_xz(bm, silueta_jet(cx, zz + z0, s, g), yf(zz + z0) + 0.006, 0.006, 0)
    objeto("Obelisco_grabados", bm, [gris_grab], padre, col)
    # emblema 27N con corona de laurel, lema y escudo
    ze = zt - 1.2
    bm = bmesh.new()
    for k in range(9):
        for sg in (-1, 1):
            a = math.radians(200 + k * 17) if sg < 0 else math.radians(-20 - k * 17)
            x, z = cx + sg * 0.0 + 0.48 * math.cos(a), ze + 0.48 * math.sin(a)
            caja(bm, (x, yf(z) - 0.01, z - 0.04), (0.1, 0.02, 0.08), 0, (0, a, 0))
    placa_xz(bm, [(cx - 0.08, ze + 0.55), (cx + 0.08, ze + 0.55), (cx + 0.3, ze + 0.62), (cx, ze + 0.85),
                  (cx - 0.3, ze + 0.62)], yf(ze + 0.6) - 0.002, 0.01, 0)       # avión estilizado del emblema
    objeto("Obelisco_emblema", bm, [oro], padre, col)
    for txt, z, tam in (("27N", ze + 0.18, 0.42), ("1992", ze - 0.22, 0.24), ("POR AHORA", ze - 0.78, 0.15),
                        ("Y PARA SIEMPRE", ze - 0.98, 0.15)):
        texto(txt, tam, oro, padre, col, (cx, yf(z) - 0.02, z), (math.pi / 2, 0, 0), extr=0.01)
    zs = ze - 1.85              # escudo de la Aviación Militar Bolivariana: el escudo real (el que ella mandó) en bronce
    logo_plano("Obelisco_escudo_AMB", "amb_bronce.png", cx, zs - 0.05, 1.25, yf(zs) - 0.02, padre, col, 0.35, 0.8)
    # la cita del decreto, en letras doradas
    cita = ["EL 27 DE NOVIEMBRE DE 1992", "LA AVIACIÓN MILITAR", "BOLIVARIANA", "«COMO UN COMPONENTE",
            "DE LA FUERZA ARMADA,", "ASUMIÓ ESE HISTÓRICO DÍA", "UNA CONDUCTA DE FIEL APEGO",
            "COMO SOPORTE DE LA NACIÓN", "QUE LE DIO VIDA Y", "QUE SOLO DEBÍA RESPONDER",
            "A SUS ALTOS INTERESES DE SOBERANÍA,", "LIBERTAD, IGUALDAD Y BIENESTAR.»"]
    z = zs - 0.85
    for i, linea in enumerate(cita):
        tam = 0.15 if i in (1, 2) else (0.08 if i == 0 else 0.105)
        t = texto(linea, tam, oro, padre, col, (cx, yf(z) - 0.02, z), (math.pi / 2, 0, 0), extr=0.005)
        w = len(linea) * tam * 0.62                     # que ninguna línea se salga de la cara
        if w > ancho(z) * 0.88:
            t.scale = (ancho(z) * 0.88 / w, 1, 1)
        z -= tam * 1.55 + 0.04
    # zócalo: lema y firma
    ylz = cy - 1.1 - 0.012
    for txt, zz in (("NADA NI NADIE NOS SACARÁ", z0 + 1.38), ("DEL CAMINO DE LA PATRIA", z0 + 1.1)):
        texto(txt, 0.2, oro, padre, col, (cx, ylz, zz), (math.pi / 2, 0, 0), extr=0.01)
    bm = bmesh.new()
    for k in range(6):                                  # trazo de la firma
        a, b = Vector((cx - 0.4 + k * 0.14, ylz, z0 + 0.45 + 0.25 * (k % 2))), Vector((cx - 0.33 + k * 0.14, ylz,
                                                                                       z0 + 0.8 - 0.3 * (k % 2)))
        d = b - a
        caja(bm, ((a.x + b.x) / 2, ylz - 0.005, (a.z + b.z) / 2 - 0.01), (0.025, 0.01, d.length), 0,
             (0, -math.atan2(d.x, d.z), 0))
    objeto("Obelisco_firma", bm, [oro], padre, col)
    # estrella blanca en el costado del zócalo
    bm = bmesh.new()
    est = []
    for k in range(10):
        r = 0.42 if k % 2 == 0 else 0.17
        a = math.pi / 2 + k * math.pi / 5
        est.append((r * math.cos(a), r * math.sin(a)))
    f = bm.faces.new([bm.verts.new((cx + 2.012, cy + y, z0 + 0.95 + z)) for y, z in est])
    f.normal_update()
    objeto("Obelisco_estrella", bm, [M["blanco"]], padre, col)
    # el Tucano subiendo casi vertical, atravesando la punta del obelisco
    # el AT-27 Tucano subiendo casi vertical; nariz arriba y hacia la calle, la cola por detrás del obelisco para que
    # la cara con las letras quede a la vista
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import tucano
    av = tucano.crear(padre, col, mat_camuflaje_gris())
    # montado SOBRE el monolito: la punta del obelisco entra en el vientre, bajo el ala (antes flotaba 0,7 m arriba)
    av.location = (cx + 0.3, cy + 1.2, zt - 0.35)
    av.rotation_euler = (math.radians(62), math.radians(-12), math.radians(180))
    return av


def mat_camuflaje_gris():
    """Camuflaje del Tucano del monumento: manchas gris azulado, gris oscuro y verde oliva."""
    m = bpy.data.materials.get("Camuflaje_gris")
    if m:
        return m
    m = bpy.data.materials.new("Camuflaje_gris")
    m.use_nodes = True
    nt = m.node_tree
    coord = nt.nodes.new("ShaderNodeTexCoord")
    ru = nt.nodes.new("ShaderNodeTexNoise")
    ru.inputs["Scale"].default_value = 0.45
    ru.inputs["Detail"].default_value = 1.5
    nt.links.new(coord.outputs["Object"], ru.inputs["Vector"])
    ra = nt.nodes.new("ShaderNodeValToRGB")
    ra.color_ramp.interpolation = "CONSTANT"
    ra.color_ramp.elements[0].color = (0.05, 0.06, 0.065, 1)
    e = ra.color_ramp.elements.new(0.45)
    e.color = (0.12, 0.135, 0.15, 1)
    ra.color_ramp.elements[-1].position = 0.6
    ra.color_ramp.elements[-1].color = (0.07, 0.085, 0.05, 1)
    nt.links.new(ru.outputs["Fac"], ra.inputs["Fac"])
    b = nt.nodes.get("Principled BSDF")
    nt.links.new(ra.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.5
    return m


# ----------------------------------------------------------------------------------- vegetación y detalles
def malla_palma(M):
    bm = bmesh.new()
    seg, anillos, alto = 12, 14, 13.0
    capas = []
    for i in range(anillos + 1):
        t = i / anillos
        r = 0.30 + 0.09 * math.sin(math.pi * min(t * 1.2, 1.0)) - 0.05 * t
        z = t * alto
        capas.append([bm.verts.new((r * math.cos(2 * math.pi * k / seg), r * math.sin(2 * math.pi * k / seg), z))
                      for k in range(seg)])
    for a, b in zip(capas, capas[1:]):
        for k in range(seg):
            bm.faces.new((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]))
    cilindro(bm, (0, 0, alto), 0.27, 0.22, 2.3, 1, 12)
    zc = alto + 2.2
    for i in range(14):
        yaw = 2 * math.pi * i / 14 + rnd.random() * 0.3
        a0 = math.radians(55 - (i % 3) * 25)
        largo = 4.6 + rnd.random() * 0.8
        dirh = Vector((math.cos(yaw), math.sin(yaw), 0))
        lado = Vector((-math.sin(yaw), math.cos(yaw), 0))
        p = Vector((0, 0, zc))
        pasos = 22
        for k in range(pasos):
            s = k / pasos
            ang = a0 - s * 1.9
            d = dirh * math.cos(ang) + Vector((0, 0, math.sin(ang)))
            q = p + d * (largo / pasos)
            hl = 1.0 * math.sin(math.pi * (0.08 + 0.9 * s)) + 0.1
            for sg in (-1, 1):
                punta = q + lado * sg * hl * 0.85 + Vector((0, 0, -hl * 0.55)) + d * hl * 0.25
                f = bm.faces.new((bm.verts.new(p), bm.verts.new(q), bm.verts.new(punta)))
                f.material_index = 2
            p = q
    me = bpy.data.meshes.new("Palma_real")
    bm.to_mesh(me)
    bm.free()
    for m in (M["tronco_palma"], M["capitel"], M["hoja_palma"]):
        me.materials.append(m)
    return me


def hojas(bm, centro, radio, cantidad, r, mi, tam=0.26):
    """Racimo de hojas sueltas (cuadriláteros) repartidas cerca de la superficie de una esfera."""
    for _ in range(cantidad):
        d = Vector((r.gauss(0, 1), r.gauss(0, 1), r.gauss(0, 1))).normalized()
        p = centro + d * radio * (0.55 + 0.45 * r.random() ** 0.4)
        n = (d + Vector((r.uniform(-.6, .6), r.uniform(-.6, .6), r.uniform(0, .6)))).normalized()
        u = n.cross(Vector((0.3, 0.2, 1.0))).normalized()
        w = n.cross(u)
        a, b = tam * (0.7 + 0.6 * r.random()), tam * 0.5
        f = bm.faces.new([bm.verts.new(p + u * x * a + w * y * b) for x, y in ((-1, 0), (0, -1), (1, 0), (0, 1))])
        f.material_index = mi


def malla_arbol(M, semilla):
    """Árbol frondoso: tronco, ramas, copa interior oscura y miles de hojas sueltas para el contorno."""
    r = random.Random(semilla)
    bm = bmesh.new()
    cilindro(bm, (0, 0, 0), 0.30, 0.16, 4.0, 0, 10)
    copas = []
    for k in range(6):
        ang = 2 * math.pi * k / 6 + r.random() * 0.5
        incl = math.radians(35 + r.random() * 20)
        lr = 2.6 + r.random() * 1.2
        base = Vector((0, 0, 3.0 + r.random() * 0.9))
        d = Vector((math.cos(ang) * math.sin(incl), math.sin(ang) * math.sin(incl), math.cos(incl)))
        cilindro(bm, base, 0.13, 0.05, lr, 0, 7, (0, incl, ang))
        copas.append(base + d * lr)
    copas.append(Vector((0, 0, 6.6)))
    for c in copas:
        rad = 1.5 + r.random() * 0.9
        vs = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=rad * 0.72)["verts"]
        for v in vs:
            v.co = c + v.co * (1.0 + 0.25 * noise.noise((v.co + c) * 1.3))
        for f in _caras(vs):
            f.material_index = 2
        hojas(bm, c, rad, 420, r, 1)
    me = bpy.data.meshes.new(f"Arbol_{semilla}")
    bm.to_mesh(me)
    bm.free()
    for m in (M["tronco"], M["follaje"], M["follaje_int"]):
        me.materials.append(m)
    suavizar(me)
    return me


def instancia(me, nombre, padre, col, x, y, esc=1.0):
    ob = bpy.data.objects.new(nombre, me)
    ob.location = (x, y, 0)
    ob.rotation_euler = (0, 0, rnd.random() * 2 * math.pi)
    ob.scale = (esc, esc, esc)
    col.objects.link(ob)
    ob.parent = padre
    return ob


def vegetacion(M, padre, col, monu):
    palma = malla_palma(M)
    arboles = [malla_arbol(M, s) for s in (1, 2, 3)]
    # palmas reales: una frente a cada bloque por dentro (fotos desde adentro, con la base pintada de blanco), una
    # junto a la isla de la plaza y las del monumento. Los árboles grandes ya no van al azar: entorno.py los pone donde
    # el satélite muestra copas.
    del arboles
    # foto de frente: tres palmas reales delante del bloque izquierdo y una delante del derecho, pegadas a la fachada
    for x, y in ((-17.5, -8.5), (-13.0, -8.5), (-9.6, -8.5), (11.5, -8.5)):
        instancia(palma, "Palma", padre, col, x, y, 0.95 + rnd.random() * 0.15)
    for x, y in ((11.5, 9.5), (-11.5, 9.0), (8.0, 44.0)):
        instancia(palma, "Palma", padre, col, x, y, 0.9 + rnd.random() * 0.2)
    for x, y in ((monu[0] - 11.0, monu[1] + 4.0), (monu[0] + 9.0, monu[1] + 9.0), (-27.0, -9.0)):
        instancia(palma, "Palma", padre, col, x, y, 1.0)


def autos_y_detalles(M, padre, col):
    def auto(nombre, x, y, rumbo, mat):
        bm = bmesh.new()
        caja(bm, (0, 0, 0.32), (1.85, 4.6, 0.75), 0)
        caja(bm, (0, -0.35, 1.07), (1.70, 2.5, 0.62), 1)
        caja(bm, (0, -0.35, 1.69), (1.62, 2.3, 0.06), 0)
        for wx in (-0.86, 0.86):
            for wy in (-1.45, 1.45):
                cilindro(bm, (wx - 0.12, wy, 0.36), 0.36, 0.36, 0.24, 2, 16, (0, math.pi / 2, 0))
        ob = objeto(nombre, bm, [mat, M["vidrio"], M["llanta"]], padre, col)
        ob.location = (x, y, 0)
        ob.rotation_euler = (0, 0, rumbo)

    auto("Camioneta_negra", 4.5, 1.0, 0.0, M["auto_negro"])
    auto("Auto_blanco", -4.6, -2.0, math.pi, M["auto_blanco"])
    bm = bmesh.new()
    for x, y in ((6.0, -17.0), (7.6, -18.2)):
        cilindro(bm, (x, y, 0.0), 0.2, 0.03, 0.72, 0, 12)
    objeto("Conos", bm, [M["naranja"]], padre, col)
    # faroles a lo largo de la vía interior
    bm = bmesh.new()
    bml = bmesh.new()
    for s in (-1, 1):
        for y in (-30.0, -55.0):            # (adentro los faroles van con las vías de la plaza)
            x = s * 10.4
            cilindro(bm, (x, y, 0), 0.11, 0.08, 8.0, 0, 10)
            caja(bm, (x - s * 1.0, y, 7.9), (2.0, 0.12, 0.12), 0)
            caja(bml, (x - s * 1.9, y, 7.75), (0.6, 0.3, 0.15), 0)
    objeto("Faroles", bm, [M["poste"]], padre, col)
    objeto("Faroles_luz", bml, [M["luz"]], padre, col)


# ----------------------------------------------------------------------------------- sol y cámaras
def sol_de_manana():
    sc = bpy.context.scene
    sol = bpy.data.objects.get("Sol")
    if sol:
        sol.rotation_euler = (math.radians(90 - SOL_EL), 0, math.radians(180 - SOL_AZ))
        sol.data.energy = 6.0
    w = sc.world
    for n in w.node_tree.nodes:
        if n.bl_idname == "ShaderNodeTexSky":
            if hasattr(n, "sun_elevation"):
                n.sun_elevation = math.radians(SOL_EL)
            if hasattr(n, "sun_disc"):
                n.sun_disc = False
        if n.bl_idname == "ShaderNodeBackground":
            n.inputs["Strength"].default_value = 0.12    # el cielo solo rellena: el sol marca sombras y color
    looks = {i.identifier for i in sc.view_settings.bl_rna.properties["look"].enum_items}
    for look in ("AgX - Punchy", "Punchy", "AgX - Medium High Contrast", "Medium High Contrast"):
        if look in looks:
            sc.view_settings.look = look
            break
    print("look:", sc.view_settings.look)
    # reflejos en vidrios y granito (trazado en pantalla: lo más liviano)
    if hasattr(sc.eevee, "use_raytracing"):
        sc.eevee.use_raytracing = True
        if hasattr(sc.eevee, "ray_tracing_method"):
            sc.eevee.ray_tracing_method = "SCREEN"


def camara(nombre, padre, col, pos, mira, lente):
    cam = bpy.data.cameras.new(nombre)
    cam.lens = lente
    cam.clip_start = 0.1
    cam.clip_end = 30000
    ob = bpy.data.objects.new(nombre, cam)
    ob.location = pos
    ob.rotation_euler = (Vector(mira) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
    col.objects.link(ob)
    ob.parent = padre
    return ob


def main():
    col = limpiar()
    for nombre in ("Cam_Entrada_Calle", "Cam_Entrada_Dron", "Cam_Monumento", "Cam_Monumento_Cerca", "Cam_Entrada_Avion"):
        ob = bpy.data.objects.get(nombre)
        if ob:
            bpy.data.objects.remove(ob, do_unlink=True)
    z0 = preparar_terreno()
    padre = bpy.data.objects.new("Entrada_origen", None)
    padre.empty_display_type = "ARROWS"
    padre.empty_display_size = 6
    padre.location = (ESTE, NORTE, z0)
    padre.rotation_euler = (0, 0, math.radians(-RUMBO_ENTRADA))
    col.objects.link(padre)

    M = mats()
    portada(M, padre, col)
    columnas_y_garita(M, padre, col)
    calles(M, padre, col)
    monu = (31.0, -14.0)
    monumento(M, padre, col, *monu)
    panel_27n(M, padre, col)
    vegetacion(M, padre, col, monu)
    autos_y_detalles(M, padre, col)
    sol_de_manana()

    camara("Cam_Entrada_Calle", padre, col, (-3.0, -48.0, 1.7), (0.0, 0.0, 4.0), 32)
    camara("Cam_Entrada_Dron", padre, col, (-7.0, -42.0, 21.0), (0.0, -3.0, 2.0), 24)
    camara("Cam_Monumento", padre, col, (22.0, -36.0, 1.6), (monu[0], monu[1], 7.5), 22)
    camara("Cam_Entrada_Avion", padre, col, (36.0, -50.0, 1.7), (6.0, -4.0, 5.0), 22)    # portada + monumento con el AT-27
    camara("Cam_Monumento_Cerca", padre, col, (monu[0] - 2.5, monu[1] - 13.5, 1.6), (monu[0], monu[1], 7.5), 16)
    bpy.context.scene.camera = bpy.data.objects["Cam_Entrada_Calle"]
    bpy.ops.wm.save_mainfile()
    print("entrada lista, cota", round(z0, 2))


if __name__ == "__main__":
    main()
