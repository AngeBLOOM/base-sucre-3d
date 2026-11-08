"""Prepara los escudos que ella mandó para usarlos como calcomanías en Blender (fondo blanco → transparente).

    python preparar_logos.py

Entrada (texturas/logos): amb_original.webp (Aviación Militar Bolivariana) y base_sucre_completo.* si ella lo dejó;
si no, base_sucre_original.png (recortado). Salida: amb.png, amb_bronce.png (para el obelisco) y base_sucre.png.
"""
import glob
import os

from PIL import Image, ImageDraw, ImageFilter, ImageOps

D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "texturas", "logos")


def sin_fondo(im, gris_min=180, sat_max=22):
    """Quita el fondo claro y sin color (blanco o el cuadriculado blanco/gris de las imágenes «transparentes») que
    está conectado con el borde, sin tocar los blancos de adentro del escudo."""
    from collections import deque
    import numpy as np
    im = im.convert("RGB")
    a = np.asarray(im).astype(np.int16)
    w, h = im.size
    claro = (a.min(-1) >= gris_min) & ((a.max(-1) - a.min(-1)) <= sat_max)
    fondo = np.zeros((h, w), bool)
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if claro[y, x] and not fondo[y, x]:
                fondo[y, x] = True
                q.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if claro[y, x] and not fondo[y, x]:
                fondo[y, x] = True
                q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            yy, xx = y + dy, x + dx
            if 0 <= yy < h and 0 <= xx < w and claro[yy, xx] and not fondo[yy, xx]:
                fondo[yy, xx] = True
                q.append((yy, xx))
    m = Image.fromarray(np.where(fondo, 0, 255).astype(np.uint8))
    m = m.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
    out = im.convert("RGBA")
    out.putalpha(m)
    bb = m.getbbox()
    return out.crop(bb) if bb else out


def bronce(im):
    g = ImageOps.grayscale(im.convert("RGB"))
    g = ImageOps.autocontrast(g, cutoff=2)
    b = ImageOps.colorize(g, black=(40, 26, 10), mid=(150, 105, 45), white=(235, 200, 120))
    b = b.convert("RGBA")
    b.putalpha(im.getchannel("A"))
    return b


def main():
    amb = sin_fondo(Image.open(os.path.join(D, "amb_original.webp")))
    amb.save(os.path.join(D, "amb.png"))
    bronce(amb).save(os.path.join(D, "amb_bronce.png"))
    completo = sorted(glob.glob(os.path.join(D, "base_sucre_completo.*")))
    src = completo[0] if completo else os.path.join(D, "base_sucre_original.png")
    bs = sin_fondo(Image.open(src))
    bs.save(os.path.join(D, "base_sucre.png"))
    print("logos listos:", amb.size, bs.size, "(base sucre de", os.path.basename(src) + ")")


if __name__ == "__main__":
    main()
