# -*- coding: utf-8 -*-
"""Vygeneruje barevné ikony a fanart (Pillow). Spuštění: python make_icons.py"""
import math
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src')
S = 512


def font(size, bold=True):
    for path, idx in [('/System/Library/Fonts/Avenir Next.ttc', 2 if bold else 0),
                      ('/System/Library/Fonts/HelveticaNeue.ttc', 1 if bold else 0),
                      ('/System/Library/Fonts/Helvetica.ttc', 1 if bold else 0)]:
        try:
            return ImageFont.truetype(path, size, index=idx)
        except OSError:
            continue
    return ImageFont.load_default()


def gradient(w, h, stops):
    """Diagonální gradient (levý horní -> pravý dolní roh) přes barevné zastávky."""
    img = Image.new('RGB', (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            t = (x / w * 0.55 + y / h * 0.45)
            for i in range(len(stops) - 1):
                p0, c0 = stops[i]
                p1, c1 = stops[i + 1]
                if t <= p1:
                    k = (t - p0) / (p1 - p0)
                    px[x, y] = tuple(int(c0[j] + (c1[j] - c0[j]) * k) for j in range(3))
                    break
            else:
                px[x, y] = stops[-1][1]
    return img


def rounded_mask(size, radius):
    m = Image.new('L', (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, size - 1, size - 1), radius, fill=255)
    return m


def glow(base, shape_fn, color, blur=14):
    layer = Image.new('RGBA', base.size, (0, 0, 0, 0))
    shape_fn(ImageDraw.Draw(layer), color)
    base.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur)))
    base.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur / 2)))


def sparkle(d, cx, cy, r, fill):
    pts = []
    for i in range(8):
        a = math.pi / 4 * i - math.pi / 2
        rr = r if i % 2 == 0 else r * 0.28
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=fill)


def addon_icon():
    bg = gradient(S, S, [(0, (40, 72, 230)), (0.4, (150, 50, 220)),
                         (0.75, (240, 60, 140)), (1, (255, 140, 60))]).convert('RGBA')
    d = ImageDraw.Draw(bg)
    # filmový pás vlevo
    film = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    fd = ImageDraw.Draw(film)
    fd.rounded_rectangle((52, 120, 222, 392), 26, fill=(255, 255, 255, 235))
    fd.rounded_rectangle((76, 150, 198, 362), 12, fill=(120, 190, 255, 255))
    for y in range(132, 384, 34):
        fd.rounded_rectangle((58, y, 70, y + 16), 3, fill=(150, 50, 220, 255))
        fd.rounded_rectangle((204, y, 216, y + 16), 3, fill=(150, 50, 220, 255))
    fd.polygon([(76, 362), (120, 280), (150, 320), (172, 290), (198, 340), (198, 362)], fill=(110, 80, 200, 255))
    fd.ellipse((96, 172, 128, 204), fill=(255, 255, 255, 255))
    film = film.rotate(-8, resample=Image.BICUBIC, center=(137, 256))
    bg.alpha_composite(film)
    # pixely
    for x, y, s in [(238, 150, 22), (268, 182, 16), (244, 214, 12), (262, 250, 20), (240, 290, 14), (270, 318, 10)]:
        d.rounded_rectangle((x, y, x + s, y + s), 3, fill=(255, 255, 255, 220))
    # zářící play
    tri = [(300, 130), (300, 382), (468, 256)]
    glow(bg, lambda dd, c: dd.polygon(tri, fill=c), (255, 255, 255, 200), 16)
    d = ImageDraw.Draw(bg)
    d.polygon(tri, fill=(255, 255, 255, 255))
    inner = [(322, 172), (322, 340), (432, 256)]
    d.polygon(inner, fill=(225, 60, 130, 255))
    d.polygon([(350, 222), (350, 290), (396, 256)], fill=(255, 255, 255, 255))
    sparkle(d, 440, 82, 30, (255, 255, 255, 255))
    # nápis
    f = font(64)
    text = 'freevideo'
    w = d.textlength(text, font=f)
    glow(bg, lambda dd, c: dd.text(((S - w) / 2, 412), text, font=f, fill=c), (60, 0, 80, 200), 8)
    d = ImageDraw.Draw(bg)
    d.text(((S - w) / 2, 412), text, font=f, fill=(255, 255, 255, 255))
    out = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    out.paste(bg, (0, 0), rounded_mask(S, 0))
    return out


def repo_icon():
    bg = gradient(S, S, [(0, (20, 170, 220)), (0.4, (70, 90, 235)),
                         (0.75, (170, 60, 220)), (1, (255, 90, 150))]).convert('RGBA')
    d = ImageDraw.Draw(bg)
    # krabice (balíček doplňků)
    top = [(256, 96), (420, 170), (256, 244), (92, 170)]
    left = [(92, 170), (256, 244), (256, 430), (92, 352)]
    right = [(420, 170), (256, 244), (256, 430), (420, 352)]
    glow(bg, lambda dd, c: dd.polygon([(256, 96), (420, 170), (420, 352), (256, 430), (92, 352), (92, 170)], fill=c),
         (255, 255, 255, 170), 18)
    d = ImageDraw.Draw(bg)
    d.polygon(left, fill=(255, 255, 255, 255))
    d.polygon(right, fill=(230, 225, 255, 255))
    d.polygon(top, fill=(255, 210, 90, 255))
    d.polygon([(174, 133), (338, 207), (338, 280), (306, 266), (306, 222), (142, 148)], fill=(255, 150, 70, 255))
    # play na boku krabice
    d.polygon([(130, 250), (130, 350), (210, 318)], fill=(240, 70, 140, 255))
    # velké R
    f = font(150)
    w = d.textlength('R', font=f)
    d.text((338 - w / 2, 236), 'R', font=f, fill=(90, 70, 220, 255))
    sparkle(d, 448, 78, 30, (255, 255, 255, 255))
    sparkle(d, 70, 450, 18, (255, 255, 255, 220))
    f2 = font(46)
    t = 'repository.radek'
    tw = d.textlength(t, font=f2)
    d.text(((S - tw) / 2, 446), t, font=f2, fill=(255, 255, 255, 255))
    return bg


def fanart():
    w, h = 1280, 720
    bg = gradient(w, h, [(0, (25, 30, 90)), (0.5, (90, 30, 120)), (1, (160, 40, 90))]).convert('RGBA')
    d = ImageDraw.Draw(bg)
    for i in range(40):
        x, y = (i * 389) % w, (i * 211) % h
        sparkle(d, x, y, 4 + i % 9, (255, 255, 255, 60 + (i * 7) % 120))
    ico = addon_icon().resize((300, 300), Image.LANCZOS)
    bg.alpha_composite(ico, (w - 380, h // 2 - 150))
    return bg.convert('RGB')


if __name__ == '__main__':
    a = addon_icon()
    a.save(os.path.join(ROOT, 'plugin.video.freevideo', 'icon.png'))
    fanart().save(os.path.join(ROOT, 'plugin.video.freevideo', 'fanart.jpg'), quality=88)
    repo_icon().save(os.path.join(ROOT, 'repository.radek', 'icon.png'))
    print('Ikony vytvořeny.')
