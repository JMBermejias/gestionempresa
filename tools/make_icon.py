#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Genera los iconos exclusivos de la app: portapapeles de medicion con regla.
# Copyright (C) 2026 JMBernabeu - GPL-3.0
import math
import os
import sys
from PIL import Image, ImageDraw

TOP = (79, 195, 247)      # #4FC3F7
BOTTOM = (2, 136, 209)    # #0288D1
DARK = (2, 112, 174)      # #0270AE
WHITE = (255, 255, 255, 255)
GRAY = (224, 231, 236, 255)
RED = (229, 57, 53, 255)
YELLOW = (255, 193, 7, 255)
PINK = (233, 90, 120, 255)
STEEL = (120, 144, 156, 255)
SCALE = 4


def rounded_gradient(size, radius):
    S = size * SCALE
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, S - 1, S - 1), radius=radius * SCALE, fill=255)
    grad = Image.new("RGBA", (S, S))
    gd = ImageDraw.Draw(grad)
    for y in range(S):
        t = y / (S - 1)
        color = tuple(int(TOP[i] + (BOTTOM[i] - TOP[i]) * t) for i in range(3))
        gd.line((0, y, S - 1, y), fill=color + (255,))
    img.paste(grad, (0, 0), mask)
    return img


def make_clipboard(S):
    layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    # Tabla blanca
    bx0, bx1 = int(S * 0.16), int(S * 0.84)
    by0, by1 = int(S * 0.14), int(S * 0.90)
    rad = int(S * 0.05)
    d.rounded_rectangle((bx0, by0, bx1, by1), radius=rad, fill=WHITE)
    d.rounded_rectangle((bx0, by0, bx1, by1), radius=rad,
                        outline=(200, 210, 218, 255), width=max(2, S // 170))

    # Clip metalico
    cx0, cx1 = int(S * 0.42), int(S * 0.58)
    cy0, cy1 = int(S * 0.08), int(S * 0.20)
    d.rounded_rectangle((cx0, cy0, cx1, cy1), radius=int(S * 0.025),
                        fill=STEEL)
    d.rounded_rectangle((cx0, cy0, cx1, cy1), radius=int(S * 0.025),
                        outline=(90, 112, 124, 255), width=max(2, S // 180))

    # Filas de medicion (lineas grises)
    lw = max(2, S // 160)
    for i, ry in enumerate((0.31, 0.38, 0.45)):
        y = int(S * ry)
        d.line((int(S * 0.24), y, int(S * 0.76), y), fill=GRAY, width=lw)

    # Regla graduada (franja azul con marcas blancas)
    ry0, ry1 = int(S * 0.55), int(S * 0.66)
    d.rounded_rectangle((int(S * 0.20), ry0, int(S * 0.80), ry1),
                        radius=int(S * 0.018), fill=DARK)
    n = 15
    step = (int(S * 0.80) - int(S * 0.20)) / (n - 1)
    for i in range(n):
        big = i % 3 == 0
        th = int(S * (0.055 if big else 0.035))
        lw2 = max(2, int(S * (0.006 if big else 0.004)))
        tx = int(S * 0.20) + int(round(i * step))
        d.line((tx, ry1 - th, tx, ry1), fill=WHITE, width=lw2)
    # Marca roja central
    txc = int(S * 0.50)
    d.line((txc, ry1 - int(S * 0.06), txc, ry1), fill=RED,
           width=max(3, S // 140))

    return layer.rotate(-5, resample=Image.BICUBIC, expand=False)


def make_pencil(S):
    layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    lx0, lx1 = int(S * 0.52), int(S * 0.98)
    ly0, ly1 = int(S * 0.72), int(S * 0.90)
    # Cuerpo amarillo
    d.rectangle((lx0, ly0, lx1, ly1), fill=YELLOW)
    # Punta
    d.polygon([(lx0, ly0), (lx0, ly1), (int(S * 0.44), int(S * 0.81))],
              fill=(224, 157, 0, 255))
    d.polygon([(lx0, int(S * 0.81)), (int(S * 0.44), int(S * 0.81)),
               (lx0, ly1)], fill=(66, 66, 66, 255))
    # Goma
    d.rectangle((lx1, ly0, lx1 + int(S * 0.05), ly1), fill=PINK)
    # Mango metalico
    d.rectangle((lx1 + int(S * 0.05), ly0, lx1 + int(S * 0.09), ly1),
                fill=STEEL)
    return layer.rotate(35, resample=Image.BICUBIC, expand=False)


def draw_icon(size, out_path):
    S = size * SCALE
    img = rounded_gradient(size, int(size * 0.22))
    img.alpha_composite(make_clipboard(S))
    img.alpha_composite(make_pencil(S))
    img = img.resize((size, size), Image.LANCZOS)
    img.save(out_path, "PNG")
    print("Generado:", out_path, size, "x", size)


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    draw_icon(512, os.path.join(root, "icon-512.png"))
    draw_icon(192, os.path.join(root, "icon-192.png"))
    hicolor = os.path.join(root, "packaging", "usr", "share", "icons", "hicolor")
    draw_icon(512, os.path.join(hicolor, "512x512", "apps", "gestion-empresa.png"))
    draw_icon(256, os.path.join(hicolor, "256x256", "apps", "gestion-empresa.png"))
    draw_icon(192, os.path.join(hicolor, "192x192", "apps", "gestion-empresa.png"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
