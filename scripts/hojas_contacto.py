"""Hojas de contacto de las fotos de referencia: 6 por hoja (3x2) con el nombre del archivo debajo."""
import os, sys
from PIL import Image, ImageDraw, ImageFont

ORIGEN, DESTINO = sys.argv[1], sys.argv[2]
os.makedirs(DESTINO, exist_ok=True)
fotos = sorted((f for f in os.listdir(ORIGEN) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".avif"))),
               key=lambda f: os.path.getmtime(os.path.join(ORIGEN, f)))
CW, CH, TXT = 620, 420, 34
try:
    fuente = ImageFont.truetype("arial.ttf", 22)
except OSError:
    fuente = ImageFont.load_default()
indice = []
for h in range(0, len(fotos), 6):
    hoja = Image.new("RGB", (3 * CW, 2 * (CH + TXT)), (30, 30, 30))
    d = ImageDraw.Draw(hoja)
    for k, f in enumerate(fotos[h:h + 6]):
        im = Image.open(os.path.join(ORIGEN, f)).convert("RGB")
        im.thumbnail((CW - 8, CH - 8))
        x, y = (k % 3) * CW, (k // 3) * (CH + TXT)
        hoja.paste(im, (x + (CW - im.width) // 2, y + (CH - im.height) // 2))
        n = h + k + 1
        d.text((x + 8, y + CH + 4), f"{n}. {os.path.splitext(f)[0][:44]}", fill=(255, 230, 120), font=fuente)
        indice.append(f"{n}\t{f}")
    hoja.save(os.path.join(DESTINO, f"hoja_{h // 6 + 1:02d}.jpg"), quality=85)
open(os.path.join(DESTINO, "indice.txt"), "w", encoding="utf-8").write("\n".join(indice))
print(len(fotos), "fotos,", (len(fotos) + 5) // 6, "hojas")
