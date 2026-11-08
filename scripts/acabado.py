"""Pasada final de calidad sobre toda la escena. Se corre la última, después de vias.py:

    blender --background BaseSucre.blend --python acabado.py

- Quita los vehículos (por ahora la escena va sin carros).
- Bisela las aristas de los edificios modelados: nada de cantos perfectos de juguete.
- Ensucia los materiales de paredes, láminas, concreto y pintura: oclusión en rincones, salpicado de lluvia y
  polvo en la base de los muros, chorreado bajo cornisas y manchas grandes de desgaste.
- Vidrios con reflejo real y luz con rebote (iluminación global en pantalla), sombras suaves y más muestras.
"""
import bpy
from mathutils import Vector

VEHICULOS = ("Rustico_", "Pickup_", "Camioneta_", "Auto_blanco", "Hangar3_camioneta", "Grupo7_sedan",
             "_auto_", "G19_auto", "Conos")
COLECCIONES = ("Entrada", "DIDA", "Hangares", "G14_Hangar3", "Dormitorios_G7", "Comando_G19", "Bomberos", "Combustible_Azul", "Comedor", "Academia", "Comedor_vecinos", "CAA_vecinos")
SIN_BISEL = ("hojas", "matas", "arbustos", "Arbol", "Palma", "Bismarck", "Flores", "Pasto", "Txt_", "frangipanes_hojas",
             "arbol", "_jardineras_matas", "_barandas", "Erizos")
# materiales que no se ensucian (vidrio, vegetación, letreros, metales pulidos, cielo)
LIMPIOS = ("Vidrio", "Logo_", "Panel_aluminio", "Letra_27N", "Jardinera", "Techo_rojo", "Pared_portada", "Bandera", "Mural", "Hoja", "Follaje", "Arbusto", "Flor", "Letras", "Letrero", "Dorado", "Azul_emblema", "Escudo",
           "Luz_farol", "Pancarta", "Valla", "Erizo", "Baliza", "Camuflaje", "Avion", "Rojo_E", "Pasto", "Tierra",
           "Capitel", "Tronco", "Suelo_", "Celosia", "Malla", "Helice", "Bandera", "Caucho", "Auto", "Cono",
           "Cuadros", "Mentor", "Piedras_poligonales", "Teja", "Goma", "Lente", "PAPI", "Manga")


def quitar_vehiculos():
    n = 0
    for ob in list(bpy.data.objects):
        if ob.type == "MESH" and any(k in ob.name for k in VEHICULOS):
            bpy.data.objects.remove(ob, do_unlink=True)
            n += 1
    print("vehículos quitados:", n)


def biselar():
    n = 0
    for nombre in COLECCIONES:
        col = bpy.data.collections.get(nombre)
        if not col:
            continue
        for ob in col.objects:
            if ob.type != "MESH" or any(k in ob.name for k in SIN_BISEL):
                continue
            if any(m.type == "BEVEL" for m in ob.modifiers):
                continue
            m = ob.modifiers.new("Bisel", "BEVEL")
            m.width = 0.025
            m.segments = 2
            m.limit_method = "ANGLE"
            m.angle_limit = 0.6
            m.harden_normals = True
            m.use_clamp_overlap = True
            n += 1
    print("objetos biselados:", n)


def _nodo(nt, tipo, **props):
    nd = nt.nodes.new(tipo)
    for k, v in props.items():
        setattr(nd, k, v)
    return nd


def ensuciar(m, fuerza=1.0):
    """Mete suciedad entre la textura y el BSDF (una sola vez por material)."""
    if not m.use_nodes or m.get("sucio"):
        return False
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    if b is None:
        return False
    entrada = b.inputs["Base Color"]
    if entrada.links:
        base = entrada.links[0].from_socket
    else:
        rgb = _nodo(nt, "ShaderNodeRGB")
        rgb.outputs[0].default_value = entrada.default_value
        base = rgb.outputs[0]
    coord = _nodo(nt, "ShaderNodeTexCoord")
    sep = _nodo(nt, "ShaderNodeSeparateXYZ")
    nt.links.new(coord.outputs["Object"], sep.inputs["Vector"])

    def mezclar(color_base, fac, color, modo="MULTIPLY"):
        mx = _nodo(nt, "ShaderNodeMix", data_type="RGBA", blend_type=modo)
        nt.links.new(fac, mx.inputs["Factor"])
        nt.links.new(color_base, mx.inputs["A"])
        mx.inputs["B"].default_value = color
        return mx.outputs["Result"]

    # 1) oclusión ambiental: rincones, encuentros con el piso y bajo aleros más oscuros
    ao = _nodo(nt, "ShaderNodeAmbientOcclusion", samples=8)
    ao.inputs["Distance"].default_value = 1.2
    inv = _nodo(nt, "ShaderNodeMath", operation="SUBTRACT")
    inv.inputs[0].default_value = 1.0
    nt.links.new(ao.outputs["AO"], inv.inputs[1])
    k_ao = _nodo(nt, "ShaderNodeMath", operation="MULTIPLY")
    k_ao.inputs[1].default_value = 0.55 * fuerza
    nt.links.new(inv.outputs[0], k_ao.inputs[0])
    col = mezclar(base, k_ao.outputs[0], (0.25, 0.22, 0.19, 1))

    # 2) polvo y salpicado de lluvia en el primer metro sobre el suelo (rojizo terroso, irregular)
    ru = _nodo(nt, "ShaderNodeTexNoise")
    ru.inputs["Scale"].default_value = 3.0
    ru.inputs["Detail"].default_value = 10
    nt.links.new(coord.outputs["Object"], ru.inputs["Vector"])
    alto = _nodo(nt, "ShaderNodeMath", operation="ADD")
    nt.links.new(sep.outputs["Z"], alto.inputs[0])
    nt.links.new(ru.outputs["Fac"], alto.inputs[1])
    zona = _nodo(nt, "ShaderNodeMapRange")
    zona.inputs["From Min"].default_value = 1.5
    zona.inputs["From Max"].default_value = 0.4
    zona.inputs["To Max"].default_value = 0.5 * fuerza
    nt.links.new(alto.outputs[0], zona.inputs["Value"])
    col = mezclar(col, zona.outputs["Result"], (0.52, 0.40, 0.30, 1))

    # 3) chorreado vertical: ruido muy estirado en Z, más fuerte arriba (bajo cornisas y bordes de techo)
    est = _nodo(nt, "ShaderNodeMapping")
    est.inputs["Scale"].default_value = (6.0, 6.0, 0.25)
    nt.links.new(coord.outputs["Object"], est.inputs["Vector"])
    ch = _nodo(nt, "ShaderNodeTexNoise")
    ch.inputs["Scale"].default_value = 2.5
    ch.inputs["Detail"].default_value = 4
    nt.links.new(est.outputs["Vector"], ch.inputs["Vector"])
    cr = _nodo(nt, "ShaderNodeMapRange")
    cr.inputs["From Min"].default_value = 0.52
    cr.inputs["From Max"].default_value = 0.7
    cr.inputs["To Max"].default_value = 0.35 * fuerza
    nt.links.new(ch.outputs["Fac"], cr.inputs["Value"])
    col = mezclar(col, cr.outputs["Result"], (0.40, 0.37, 0.33, 1))

    # 4) manchas grandes de desgaste y decoloración por sol
    mg = _nodo(nt, "ShaderNodeTexNoise")
    mg.inputs["Scale"].default_value = 0.15
    mg.inputs["Detail"].default_value = 3
    nt.links.new(coord.outputs["Object"], mg.inputs["Vector"])
    mr = _nodo(nt, "ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.45
    mr.inputs["From Max"].default_value = 0.65
    mr.inputs["To Max"].default_value = 0.22 * fuerza
    nt.links.new(mg.outputs["Fac"], mr.inputs["Value"])
    col = mezclar(col, mr.outputs["Result"], (0.80, 0.78, 0.72, 1), "MIX")

    nt.links.new(col, b.inputs["Base Color"])
    # la suciedad también quita brillo
    if not b.inputs["Roughness"].links:
        b.inputs["Roughness"].default_value = min(0.95, b.inputs["Roughness"].default_value + 0.12)
    m["sucio"] = True
    return True


def materiales():
    n = 0
    usados = set()
    for nombre in COLECCIONES + ("Vias",):
        col = bpy.data.collections.get(nombre)
        if col:
            for ob in col.objects:
                if ob.type in ("MESH", "FONT"):
                    usados.update(ms.material for ms in ob.material_slots if ms.material)
    for m in usados:
        if any(k in m.name for k in LIMPIOS):
            continue
        fuerza = 0.6 if m.name.startswith(("Pintura", "Concreto", "Asfalto", "Acera", "Baldosa")) else 1.0
        n += ensuciar(m, fuerza)
    # vidrios: reflejo del cielo y de los edificios de enfrente
    for m in bpy.data.materials:
        if m.name.startswith("Vidrio") and m.use_nodes:
            b = m.node_tree.nodes.get("Principled BSDF")
            b.inputs["Roughness"].default_value = 0.03
            b.inputs["Metallic"].default_value = 0.0
            if "IOR" in b.inputs:
                b.inputs["IOR"].default_value = 1.52
            if "Specular IOR Level" in b.inputs:
                b.inputs["Specular IOR Level"].default_value = 1.0
            if "Coat Weight" in b.inputs:
                b.inputs["Coat Weight"].default_value = 0.4
    print("materiales ensuciados:", n)


def luz():
    sc = bpy.context.scene
    e = sc.eevee
    e.taa_render_samples = 96
    e.use_shadows = True
    e.shadow_ray_count = 2
    e.shadow_step_count = 8
    e.shadow_resolution_scale = 1.0
    e.use_raytracing = True
    e.ray_tracing_method = "SCREEN"
    e.use_fast_gi = True
    e.fast_gi_method = "GLOBAL_ILLUMINATION"
    e.fast_gi_distance = 20.0
    e.fast_gi_quality = 0.5
    looks = {i.identifier for i in sc.view_settings.bl_rna.properties["look"].enum_items}
    if sc.world.get("hdri"):
        # con el cielo fotográfico (calidad.py) la luz ya viene de la foto: solo el tono de la imagen
        # contraste medio: con el alto, los aleros y porches quedaban negros
        for look in ("AgX - Medium Contrast", "AgX - Base Contrast", "AgX - Medium High Contrast"):
            if look in looks:
                sc.view_settings.look = look
                break
        return
    sol = bpy.data.objects.get("Sol")
    if sol:
        sol.data.angle = 0.012              # ~0,7°: penumbra natural sin perder sombras marcadas
        sol.data.energy = 6.5
    for n in sc.world.node_tree.nodes:
        if n.bl_idname == "ShaderNodeBackground":
            n.inputs["Strength"].default_value = 0.18   # el cielo solo rellena; con más, todo se lava
    for look in ("AgX - High Contrast", "AgX - Medium High Contrast"):
        if look in looks:
            sc.view_settings.look = look
            break
    sc.view_settings.exposure = 0.0
    quitar_bruma(sc)


def quitar_bruma(sc):
    # sin bruma volumétrica: en la Iris Xe deja los renders negros y cierra Blender
    w = sc.world
    for n in list(w.node_tree.nodes):
        if n.bl_idname == "ShaderNodeVolumePrincipled":
            w.node_tree.nodes.remove(n)
    w.pop("bruma", None)


def quitar_plantas_en_vias():
    """Árboles, matas y palmas que quedaron sobre una calle, la plataforma o una pista se quitan."""
    deps = bpy.context.evaluated_depsgraph_get()
    sc = bpy.context.scene
    n = 0
    for ob in list(bpy.data.objects):
        if ob.type != "MESH" or not ob.name.startswith(("Arbol_real", "Mata_real", "Arbusto_alto_real", "Palma")):
            continue
        p = ob.matrix_world.translation
        ok, _loc, _n, _i, hit, _m = sc.ray_cast(deps, p + Vector((0, 0, 0.6)), Vector((0, 0, -1)), distance=3.0)
        if ok and hit.name.startswith(("Via_calle", "Via_camino", "Via_rodaje", "Plataforma", "Pista")):
            bpy.data.objects.remove(ob, do_unlink=True)
            n += 1
    print("plantas sobre calles quitadas:", n)


def main():
    quitar_plantas_en_vias()
    quitar_vehiculos()
    biselar()
    materiales()
    luz()
    bpy.ops.wm.save_mainfile()
    print("acabado listo")


main()
