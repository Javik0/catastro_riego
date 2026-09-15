# -*- coding: utf-8 -*-
"""
Dibuja las llamadas numeradas sobre las capturas del manual.

No se escriben coordenadas a mano: `capturar_manual.mjs` guardo el rectangulo
real de cada boton en capturas.json, asi que el globo cae siempre sobre el
elemento aunque la pantalla se rediseñe. Los numeros son los mismos con los que
el texto del manual enumera los pasos.

Entrega ademas la version reducida que se incrusta en el PDF: a resolucion
completa cada captura pesa unos 5 MB y el manual no cerraria.

Uso:  python -X utf8 scripts/anotar_capturas.py
"""
import io
import json
import os

from PIL import Image, ImageDraw, ImageFont

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CAPTURAS = os.path.join(BASE, 'docs', 'manual', 'capturas')
SALIDA = os.path.join(BASE, 'docs', 'manual', 'anotadas')

ESCALA = 2          # deviceScaleFactor con el que se capturo
ANCHO_PDF = 1800    # ancho final de la imagen que va al PDF

NARANJA = (249, 115, 22)
BLANCO = (255, 255, 255)

# Segoe UI viene con Windows; si faltara, Pillow pone su tipografia interna y
# el numero sale mas pequeño pero legible.
def _fuente(px):
    for ruta in (r'C:\Windows\Fonts\segoeuib.ttf', r'C:\Windows\Fonts\arialbd.ttf'):
        if os.path.exists(ruta):
            return ImageFont.truetype(ruta, px)
    return ImageFont.load_default()


def _globo(dib, cx, cy, numero, radio, fuente):
    dib.ellipse([cx - radio, cy - radio, cx + radio, cy + radio],
                fill=NARANJA, outline=BLANCO, width=4)
    t = str(numero)
    izq, arr, der, aba = dib.textbbox((0, 0), t, font=fuente)
    dib.text((cx - (der - izq) / 2 - izq, cy - (aba - arr) / 2 - arr),
             t, font=fuente, fill=BLANCO)


def anotar(toma):
    origen = os.path.join(CAPTURAS, toma['archivo'])
    im = Image.open(origen).convert('RGB')
    dib = ImageDraw.Draw(im)
    radio = 30
    fuente = _fuente(38)

    margen = 8
    cajas = [(m['x'] * ESCALA - margen, m['y'] * ESCALA - margen,
              (m['x'] + m['width']) * ESCALA + margen,
              (m['y'] + m['height']) * ESCALA + margen) for m in toma['marcas']]

    for (x0, y0, x1, y1), (i, m) in zip(cajas, enumerate(toma['marcas'], start=1)):
        dib.rounded_rectangle([x0, y0, x1, y1], radius=12, outline=NARANJA, width=6)

        # El globo va en la esquina superior izquierda del recuadro, mitad
        # dentro y mitad fuera. Es la convencion de las guias de uso y, a
        # diferencia de ponerlo al costado, nunca tapa el control vecino
        # cuando dos botones van pegados.
        cx = min(max(x0, radio + 4), im.width - radio - 4)
        cy = min(max(y0, radio + 4), im.height - radio - 4)
        elegido = (cx, cy)
        _globo(dib, elegido[0], elegido[1], i, radio, fuente)

    os.makedirs(SALIDA, exist_ok=True)
    destino = os.path.join(SALIDA, toma['archivo'].replace('.png', '.jpg'))
    if im.width > ANCHO_PDF:
        alto = round(im.height * ANCHO_PDF / im.width)
        im = im.resize((ANCHO_PDF, alto), Image.LANCZOS)
    im.save(destino, 'JPEG', quality=88, optimize=True)
    return destino, len(toma['marcas'])


def main():
    with io.open(os.path.join(CAPTURAS, 'capturas.json'), encoding='utf-8') as f:
        tomas = json.load(f)
    total = 0
    for t in tomas:
        destino, n = anotar(t)
        kb = os.path.getsize(destino) / 1024
        print(f"  {t['id']:<24} {n} llamada(s)  {kb:6.0f} KB")
        total += 1
    print(f"\n{total} capturas anotadas en {SALIDA}")


if __name__ == '__main__':
    main()
