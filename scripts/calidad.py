"""Recursos reales de Poly Haven (CC0) en la escena. Se corre después de vias.py y antes de acabado.py:

    blender --background BaseSucre.blend --python calidad.py

1. Cielo fotográfico HDRI (assets/hdri): ilumina, da reflejos a los vidrios y su sol proyecta las sombras. Se gira
   para que el sol quede del este, como en las fotos de la entrada.
2. Vegetación: cada árbol y cada mata hecha con hojas sueltas se cambia por un modelo escaneado del mismo tamaño
   (island_tree_02, searsia_lucida, shrub_02). Las palmas siguen siendo las propias: Poly Haven no tiene palmas.
3. Texturas: ladrillo real en los dormitorios, friso pintado en paredes, lámina gastada y oxidada en hangares y
   concreto gastado en calles y plataforma.
"""
import math
import os
import random
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import entrada as E  # noqa: E402

RAIZ = os.path.dirname(E.TEXTURAS)
ASSETS = os.path.join(RAIZ, "assets")
SOL_AZ = 95.0                                       # sol de media mañana del este (grados desde el norte)
rnd = random.Random(23)


# ----------------------------------------------------------------------------------- 1. cielo
def cielo():
    sc = bpy.context.scene
    w = sc.world
    nt = w.node_tree
    ruta = next(os.path.join(ASSETS, "hdri", f) for f in os.listdir(os.path.join(ASSETS, "hdri")) if f.endswith(".hdr"))
    img = bpy.data.images.load(ruta, check_existing=True)
    # posición del sol en la foto: el píxel más brillante
    wd, ht = img.size
    buf = np.empty(wd * ht * 4, dtype=np.float32)
    img.pixels.foreach_get(buf)
    lum = buf.reshape(ht, wd, 4)[..., :3].sum(axis=2)
    fila, col = np.unravel_index(int(np.argmax(lum)), lum.shape)
    u, v = (col + 0.5) / wd, (fila + 0.5) / ht
    phi = (0.5 - u) * 2 * math.pi                    # Blender: u = 0,5 - atan2(y, x) / 2π
    elev = (v - 0.5) * math.pi
    d_foto = Vector((math.cos(phi), math.sin(phi)))
    az = math.radians(SOL_AZ)
    d_quiero = Vector((math.sin(az), math.cos(az)))
    giro = math.atan2(d_foto.y, d_foto.x) - math.atan2(d_quiero.y, d_quiero.x)
    print(f"sol del HDRI: elevación {math.degrees(elev):.1f}°, giro {math.degrees(giro):.1f}°")

    for n in list(nt.nodes):
        if n.bl_idname != "ShaderNodeOutputWorld":
            nt.nodes.remove(n)
    out = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeOutputWorld")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapa = nt.nodes.new("ShaderNodeMapping")
    mapa.inputs["Rotation"].default_value = (0, 0, giro)
    tex = nt.nodes.new("ShaderNodeTexEnvironment")
    tex.image = img
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 1.2          # ella: «muy oscuro, agrégale más iluminación»
    nt.links.new(coord.outputs["Generated"], mapa.inputs["Vector"])
    nt.links.new(mapa.outputs["Vector"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])

    # el sol de la foto hace las sombras (EEVEE lo extrae del HDRI); la lámpara vieja ya no hace falta
    if hasattr(w, "sun_threshold"):
        w.sun_threshold = 10.0
        w.sun_angle = math.radians(1.0)
        w.use_sun_shadow = True
        sol = bpy.data.objects.get("Sol")
        if sol:
            sol.hide_render = True
            sol.hide_viewport = True
    else:                                            # versión sin extracción: la lámpara copia la dirección del sol
        sol = bpy.data.objects.get("Sol")
        if sol:
            sol.rotation_euler = (math.pi / 2 - elev, 0, math.pi - az)
    sc.view_settings.exposure = 1.1
    w["hdri"] = True                                 # acabado.py no debe tocar la luz del cielo


# ----------------------------------------------------------------------------------- 2. vegetación
def biblioteca():
    """Trae una vez las mallas de los modelos (las copias comparten la malla: no gastan memoria)."""
    col = bpy.data.collections.get("Biblioteca_vegetacion")
    if col is None:
        col = bpy.data.collections.new("Biblioteca_vegetacion")
        bpy.context.scene.collection.children.link(col)
    col.hide_render = True
    col.hide_viewport = True
    quiero = {"island_tree_02": ["island_tree_02_LOD1"],
              "searsia_lucida": [f"searsia_lucida_{k}_LOD1" for k in "abcdef"],
              "shrub_02": [f"shrub_02_{k}_LOD1" for k in "abcd"]}
    mallas = {}
    for carpeta, nombres in quiero.items():
        archivo = next(os.path.join(ASSETS, "modelos", carpeta, f)
                       for f in os.listdir(os.path.join(ASSETS, "modelos", carpeta)) if f.endswith(".blend"))
        faltan = [n for n in nombres if n not in bpy.data.objects]
        if faltan:
            with bpy.data.libraries.load(archivo, link=False) as (src, dst):
                dst.objects = [n for n in src.objects if n in faltan]
            for ob in dst.objects:
                if ob:
                    col.objects.link(ob)
        for n in nombres:
            ob = bpy.data.objects[n]
            alto = ob.dimensions.z
            mallas.setdefault(carpeta, []).append((ob.data, alto))
    # las texturas de los modelos quedan junto a sus .blend
    bpy.ops.file.find_missing_files(directory=os.path.join(ASSETS, "modelos"))
    return mallas


def racimos(ob, celda=1.0):
    """Agrupa los vértices de una malla de hojas sueltas en racimos (centro, ancho, alto) en coordenadas del mundo."""
    mw = ob.matrix_world
    pts = np.array([tuple(mw @ v.co) for v in ob.data.vertices])
    if len(pts) == 0:
        return []
    claves = np.floor(pts / celda).astype(int)
    grupos = {}
    for i, k in enumerate(map(tuple, claves)):
        grupos.setdefault(k, []).append(i)
    vistos, out = set(), []
    for k in grupos:
        if k in vistos:
            continue
        pila, idx = [k], []
        vistos.add(k)
        while pila:
            c = pila.pop()
            idx += grupos[c]
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for dz in (-1, 0, 1):
                        n = (c[0] + dx, c[1] + dy, c[2] + dz)
                        if n in grupos and n not in vistos:
                            vistos.add(n)
                            pila.append(n)
        p = pts[idx]
        if len(p) < 12:
            continue
        lo, hi = p.min(axis=0), p.max(axis=0)
        out.append((Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2])),
                    max(hi[0] - lo[0], hi[1] - lo[1]), hi[2] - lo[2], hi[2]))
    return out


def plantar(col, malla, nombre, pos, escala):
    ob = bpy.data.objects.new(nombre, malla)
    ob.location = pos
    ob.rotation_euler = (0, 0, rnd.random() * 2 * math.pi)
    ob.scale = (escala * rnd.uniform(0.9, 1.1), escala * rnd.uniform(0.9, 1.1), escala)
    col.objects.link(ob)
    return ob


def suelo_bajo(p, ignorar):
    """Cota del suelo bajo un punto (para que los arbustos de los racimos no floten ni se entierren)."""
    deps = bpy.context.evaluated_depsgraph_get()
    ok, loc, _n, _i, ob, _m = bpy.context.scene.ray_cast(deps, Vector((p.x, p.y, p.z + 0.5)), Vector((0, 0, -1)),
                                                        distance=4.0)
    return loc.z if ok and ob.name not in ignorar else p.z


def vegetacion(mallas):
    col = bpy.data.collections.get("Vegetacion_real")
    if col and len(col.objects):
        # ya se cambió en una corrida anterior (las mallas de hojas originales se borraron): no repetir
        print("vegetación ya cambiada:", len(col.objects), "plantas")
        return
    if col is None:
        col = bpy.data.collections.new("Vegetacion_real")
        bpy.context.scene.collection.children.link(col)
    arbol, alto_arbol = mallas["island_tree_02"][0]
    searsias = mallas["searsia_lucida"]
    matas = mallas["shrub_02"]
    n_arb = n_mat = 0
    quitar = []
    for ob in list(bpy.data.objects):
        if ob.type != "MESH" or ob.users_collection and ob.users_collection[0].name in ("Vegetacion_real",
                                                                                       "Biblioteca_vegetacion"):
            continue
        nombre = ob.name
        # árboles de copa redonda de la entrada (instancias de Arbol_n)
        if nombre.startswith("Arbol") and ob.data.name.startswith("Arbol_"):
            alto = 8.0 * ob.scale.z
            plantar(col, arbol, "Arbol_real", ob.matrix_world.translation, alto / alto_arbol)
            quitar.append(ob)
            n_arb += 1
            continue
        es_hojas = any(k in nombre for k in ("matas", "arbustos", "Arbustos", "arbol", "frangipanes_hojas",
                                              "arboles_cono", "_jardineras_matas"))
        if not es_hojas or nombre.endswith(("_tronco", "_troncos")):
            continue
        for centro, ancho, alto, tope in racimos(ob, 0.9):
            if tope - centro.z > 3.0 or "arbol" in nombre.lower() or "frangipanes" in nombre:
                # árbol: copa del mismo tamaño, el tronco del modelo llega al suelo
                base = Vector((centro.x, centro.y, suelo_bajo(centro, {ob.name})))
                h = max(tope - base.z, 3.0)
                if "cono" in nombre:                 # árboles podados en cono del G14: arbusto alto y denso
                    m, ha = searsias[0]
                    plantar(col, m, "Arbusto_alto_real", base, h / ha)
                else:
                    plantar(col, arbol, "Arbol_real", base, h / alto_arbol)
                n_arb += 1
            else:
                # searsia: follaje denso; shrub_02 queda ralo, como maleza, y no sirve de mata de jardín
                m, ha = rnd.choice(searsias[2:] if ancho > 0.9 else searsias[3:])
                base = Vector((centro.x, centro.y, centro.z - 0.05))
                plantar(col, m, "Mata_real", base, max(alto, 0.5) / ha)
                n_mat += 1
        quitar.append(ob)
    # troncos y ramas de los árboles viejos (los modelos traen los suyos)
    for ob in bpy.data.objects:
        if ob.type == "MESH" and ob.name in ("G14_troncos", "Comando_arbol_tronco", "Grupo7_frangipanes",
                                                    "Bomberos_arbol_tronco"):
            quitar.append(ob)
    for ob in set(quitar):
        bpy.data.objects.remove(ob, do_unlink=True)
    print("árboles:", n_arb, "matas:", n_mat)


# ----------------------------------------------------------------------------------- 3. texturas
CAMBIOS = {"pared": "friso", "lamina": "lamina_gastada", "acera": None}
POR_MATERIAL = {"Lamina_vieja": "lamina_oxidada", "Concreto_via": "concreto_gastado",
                "Concreto_plataforma": "concreto_gastado", "Concreto_calle": "concreto_gastado"}


def cambiar_imagenes(m, nueva):
    """Cambia las imágenes de texturas/<vieja>/ por las de texturas/<nueva>/ manteniendo nodos y escala."""
    for n in m.node_tree.nodes:
        if n.bl_idname == "ShaderNodeTexImage" and n.image:
            ruta = bpy.path.abspath(n.image.filepath)
            archivo = os.path.basename(ruta)
            vieja = os.path.basename(os.path.dirname(ruta))
            destino = nueva or CAMBIOS.get(vieja)
            if not destino or vieja == destino:
                continue
            nueva_ruta = os.path.join(E.TEXTURAS, destino, archivo)
            if os.path.exists(nueva_ruta):
                cs = n.image.colorspace_settings.name
                n.image = bpy.data.images.load(nueva_ruta, check_existing=True)
                n.image.colorspace_settings.name = cs


def texturas():
    for m in bpy.data.materials:
        if not m.use_nodes:
            continue
        cambiar_imagenes(m, POR_MATERIAL.get(m.name))
    # ladrillo real de los dormitorios en lugar del patrón generado
    viejo = bpy.data.materials.get("Ladrillo_rojo")
    if viejo:
        nuevo = E.pbr("Ladrillo_real", "ladrillo", 1.6, (0.95, 0.85, 0.80))
        for ob in bpy.data.objects:
            for s in ob.material_slots:
                if s.material == viejo:
                    s.material = nuevo
    print("texturas cambiadas")


def main():
    cielo()
    vegetacion(biblioteca())
    texturas()
    bpy.ops.wm.save_mainfile()
    print("calidad lista")


main()
