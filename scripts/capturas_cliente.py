"""Capturas 2K (2560 x 1440) de cada lugar para mostrar al cliente, en renders/cliente/NN_nombre.png.

    blender --background BaseSucre.blend --python capturas_cliente.py
"""
import os
import sys

import bpy

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOMAS = [("Cam_General", "vista_general"), ("Cam_Aerea", "vista_aerea"), ("Cam_Entrada_Dron", "entrada_dron"), ("Cam_Entrada_Calle", "entrada"),
         ("Cam_Monumento", "monumento_entrada"), ("Cam_Bomberos", "bomberos"), ("Cam_Combustible", "combustible"),
         ("Cam_G19", "grupo_19"), ("Cam_Comando", "comando_combasucre"), ("Cam_Torre", "torre_de_control"),
         ("Cam_Hangarcito", "hangarcito_azul"), ("Cam_Hangar3", "hangar_3"), ("Cam_G14_Calle", "g14_calle"),
         ("Cam_G14", "g14_mentor"), ("Cam_Grupo7", "grupo_7"), ("Cam_Dormitorios", "dormitorios"),
         ("Cam_CEA_Costado", "cea"), ("Cam_CEA_Frente", "cea_frente"), ("Cam_Hangar_Gris", "hangar_gris"),
         ("Cam_DIDA", "dida"), ("Cam_Hangares_Norte", "calle_de_hangares_aerea"),
         ("Cam_DIDA_Caminería", "dida_caminería_y_hangar_gris"), ("Cam_DIDA_Esquina", "dida_esquina"),
         ("Cam_DIDA_Letrero", "dida_letrero"), ("Cam_DIDA_Dormitorio", "dida_dormitorio_lateral"),
         ("Cam_Comedor", "comedor_los_tacariguas"), ("Cam_Comedor_Entrada", "comedor_entrada"),
         ("Cam_Monumento_Cerca", "monumento_27N"), ("Cam_Hangar_Blanco", "hangar_curvo_blanco"),
         ("Cam_Academia", "academia_tecnica"), ("Cam_Pista", "pista_11_umbral"), ("Cam_Final", "final_pista_11"),
         ("Cam_Pistas_Aerea", "pistas_aerea"), ("Cam_Sierra", "sierra_y_lago"),
         ("Cam_Adentro_Portada", "portada_desde_adentro"), ("Cam_Adentro_Lado", "portada_y_edificio_crema"),
         ("Cam_Plaza", "plaza_de_la_isla"), ("Cam_Plaza_Lado", "plaza_de_la_isla_lado"),
         ("Cam_Comedor_Salon", "comedor_salon_este"), ("Cam_Tanque", "tanque_de_agua"), ("Cam_CAA", "caa"),
         ("Cam_Largo_CAA", "edificio_largo_y_lavanderia")]

sc = bpy.context.scene
# ella: «muy oscuro, agrégale más iluminación»: cielo un 20 % más fuerte y exposición 1,1 (antes 0,9)
sc.view_settings.exposure = max(sc.view_settings.exposure, 1.1)
for _n in sc.world.node_tree.nodes:
    if _n.bl_idname == "ShaderNodeBackground":
        _n.inputs["Strength"].default_value = max(_n.inputs["Strength"].default_value, 1.2)
# vistas del camino de la entrada a la DIDA (camino_dida.py), en orden
TOMAS += [(o.name, "camino_" + o.name[-2:]) for o in sorted(bpy.data.objects, key=lambda o: o.name)
          if o.type == "CAMERA" and o.name.startswith("Cam_Camino_")]
# vista general: la toma alta del primer cuadro del recorrido (toda la base, el lago y la sierra)
rec = bpy.data.objects.get("Cam_Recorrido")
if rec and "Cam_General" not in bpy.data.objects:
    sc.frame_set(1)
    cam = bpy.data.cameras.new("Cam_General")
    cam.lens, cam.clip_end = 24, 30000
    gen = bpy.data.objects.new("Cam_General", cam)
    sc.collection.objects.link(gen)
    gen.matrix_world = rec.matrix_world.copy()
sc.render.resolution_x, sc.render.resolution_y = 2560, 1440
sc.render.resolution_percentage = 100
sc.eevee.taa_render_samples = 96
sc.render.image_settings.file_format = "PNG"
# carpeta de salida: «-- cliente_v2» la cambia (por defecto renders/cliente)
_args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out = os.path.join(RAIZ, "renders", _args[0] if _args else "cliente")
os.makedirs(out, exist_ok=True)
for i, (cam, nombre) in enumerate(TOMAS, 1):
    ob = bpy.data.objects.get(cam)
    if ob is None:
        print("falta la cámara", cam)
        continue
    ruta = os.path.join(out, f"{i:02d}_{nombre}.png")
    if os.path.exists(ruta):
        continue
    sc.camera = ob
    sc.render.filepath = ruta
    bpy.ops.render.render(write_still=True)
    print("captura", ruta)
