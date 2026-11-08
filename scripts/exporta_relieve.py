"""Relieve fino y foto regional para las montañas, sacados de lo que AeroEscuela ya tiene guardado (no descarga si
están los mosaicos: relieve «terrarium» z12 ≈ 38 m/px y la capa satelital de 51 km).

    python exporta_relieve.py <carpeta del proyecto BaseSucre3D>

Deja en datos/: heights_40m.npy (±12 km, 601 x 601, filas = norte ascendente, en metros sobre el mar) y
sat_51km.png (±25,6 km, norte arriba, 12,5 m/px).
"""
import os
import sys

import numpy as np
from PIL import Image

SIM = r"C:\Users\angel\Proyectos\simulador-vuelo"
sys.path.insert(0, SIM)
from sim import geo  # noqa: E402

RAIZ = sys.argv[1]
DATOS_SIM = os.path.join(SIM, "datos")
db = geo.AirportDB(DATOS_SIM)
db.ensure(None)
a = db.get("SVBS")
proj = geo.LocalProjection(float(a["latitude_deg"]), float(a["longitude_deg"]))
R, N = 12000.0, 601
lat_rng = (proj.lat0 - R / proj.k_lat * 1.03, proj.lat0 + R / proj.k_lat * 1.03)
lon_rng = (proj.lon0 - R / proj.k_lon * 1.03, proj.lon0 + R / proj.k_lon * 1.03)
tf = geo.TileFetcher(DATOS_SIM)
dem, x0, y0 = tf.mosaic("dem", 12, lat_rng, lon_rng)
h = geo.resample(dem, x0, y0, 12, proj, -R, R, -R, R, N, linear=True).astype(np.float32)
np.save(os.path.join(RAIZ, "datos", "heights_40m.npy"), h)
print("relieve 40 m:", h.shape, "min", round(float(h.min()), 1), "max", round(float(h.max()), 1))

l2 = np.load(os.path.join(DATOS_SIM, "geo", "loc2_SVBS.npz"))
Image.fromarray(np.flipud(l2["sat0"])).save(os.path.join(RAIZ, "datos", "sat_51km.png"))
print("satélite regional:", l2["sat0"].shape, tuple(l2["rect0"]))
w = np.load(os.path.join(DATOS_SIM, "geo", "agua_SVBS.npz"))
m = w["mask"]
Image.fromarray(np.flipud(m * 255 if m.max() == 1 else m)).resize((2048, 2048), Image.BILINEAR).save(
    os.path.join(RAIZ, "datos", "agua_51km.png"))
print("agua regional:", tuple(w["rect"]))
