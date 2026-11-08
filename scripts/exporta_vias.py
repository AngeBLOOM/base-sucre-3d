"""Extrae calles, caminos y estacionamientos de SVBS de los mosaicos vectoriales (OpenStreetMap vía Esri) que
AeroEscuela ya tiene guardados; no descarga nada. Resultado: datos/vias.json con coordenadas (este, norte) en m.

    python exporta_vias.py <carpeta del proyecto BaseSucre3D>
"""
import json, math, os, sys

SIM = r"C:\Users\angel\Proyectos\simulador-vuelo"
sys.path.insert(0, SIM)
from sim import geo, mvt  # noqa: E402

CAPAS_LINEA = {"road", "service road", "Daylight road", "road (access type)", "road link", "path", "track",
               "aeroway"}
CAPAS_AREA = {"amenity area", "transportation area", "private access area"}
R = 2600.0

db = geo.AirportDB(os.path.join(SIM, "datos"))
db.ensure(None)
a = db.get("SVBS")
proj = geo.LocalProjection(float(a["latitude_deg"]), float(a["longitude_deg"]))
z = 15
la = (proj.lat0 - R / proj.k_lat, proj.lat0 + R / proj.k_lat)
lo = (proj.lon0 - R / proj.k_lon, proj.lon0 + R / proj.k_lon)
x0, y0 = geo.merc_px(la[1], lo[0], z)
x1, y1 = geo.merc_px(la[0], lo[1], z)
scale = 2 ** z * 256.0
vias, areas = [], []
for tx in range(int(x0 // 256), int(x1 // 256) + 1):
    for ty in range(int(y0 // 256), int(y1 // 256) + 1):
        p = os.path.join(SIM, "datos", "geo", "vt", str(z), str(tx), f"{ty}.pbf")
        if not os.path.exists(p):
            continue
        data = open(p, "rb").read()
        if not data:
            continue
        for capa, feats in mvt.decode(data, CAPAS_LINEA | CAPAS_AREA).items():
            for gtype, rings, attrs, extent in feats:
                for ring in rings:
                    pts = []
                    for gx, gy in ring:
                        px = (tx + gx / extent) * 256.0
                        py = (ty + gy / extent) * 256.0
                        lon = px / scale * 360.0 - 180.0
                        lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * py / scale))))
                        n, e = proj.to_local(lat, lon)
                        pts.append((round(float(e), 2), round(float(n), 2)))
                    if len(pts) < 2:
                        continue
                    d = {"capa": capa, "simbolo": attrs.get("_symbol"), "nombre": attrs.get("_name"), "p": pts}
                    (vias if gtype == 2 else areas if gtype == 3 else []).append(d)
out = os.path.join(sys.argv[1], "datos", "vias.json")
json.dump({"vias": vias, "areas": areas}, open(out, "w", encoding="utf-8"))
from collections import Counter  # noqa: E402
print("vías:", Counter((v["capa"], v["simbolo"]) for v in vias).most_common())
print("áreas:", Counter((v["capa"], v["simbolo"]) for v in areas).most_common())
