# Usage: python3 scenes/nerava/logo/trace.py scenes/nerava/logo/source.png scenes/nerava/logo/logo
# Trace the Nerava logo PNG into one SVG path per glyph (6 letters + bolt).
import sys, numpy as np, potrace
from PIL import Image
from collections import Counter
src, out = sys.argv[1], sys.argv[2]
S = 8  # upsample before thresholding so the traced curves are smooth
im = Image.open(src).convert('RGB')
a = np.asarray(im).astype(int)
print('ink mode', Counter(map(tuple, a[a.sum(2) < 120])).most_common(2))
print('blue mode', Counter(map(tuple, a[(a[:,:,2]-a[:,:,0]) > 150])).most_common(2))
big = np.asarray(im.resize((im.width*S, im.height*S), Image.BICUBIC)).astype(float)
# soften the source pixel staircase before thresholding, or straight edges trace as ripples
from scipy import ndimage
big = ndimage.gaussian_filter(big, sigma=(S * 0.45, S * 0.45, 0))
bg = np.array([247, 246, 241.])
# coverage: distance from the background toward the glyph colour
ink_c = np.array([11, 16, 32.]); blue_c = np.array([60, 131, 246.])
def cov(c):
    d = c - bg
    return ((big - bg) @ d) / (d @ d)
isblue = (big[:,:,2] - big[:,:,0]) > 60
ink_mask = (cov(ink_c) > 0.5) & ~isblue
blue_mask = isblue & (cov(blue_c) > 0.5)

def trace(mask):
    bm = potrace.Bitmap(mask)
    path = bm.trace(turdsize=200, alphamax=0.9, opticurve=True, opttolerance=2.0)
    return path

def to_d(curve):
    f = lambda p: f"{p.x/S:.3f} {p.y/S:.3f}"
    d = f"M{f(curve.start_point)}"
    for seg in curve.segments:
        if seg.is_corner:
            d += f"L{f(seg.c)}L{f(seg.end_point)}"
        else:
            d += f"C{f(seg.c1)} {f(seg.c2)} {f(seg.end_point)}"
    return d + "Z"

# split ink into letters by connected components, ordered left to right
from scipy import ndimage
lab, n = ndimage.label(ink_mask)
comps = sorted(range(1, n+1), key=lambda k: np.where(lab == k)[1].min())
comps = [k for k in comps if (lab == k).sum() > 2000]
print('letters', len(comps))
glyphs = []
for i, k in enumerate(comps):
    m = lab == k
    xs = np.where(m)[1]
    glyphs.append(('NERAVA'[i] + str(i), ''.join(to_d(c) for c in trace(m) if c.start_point.x > 0), [xs.min()/S, (xs.max()+1)/S]))
p = trace(blue_mask)
glyphs.append(('bolt', ''.join(to_d(c) for c in p if c.start_point.x > 0), None))

ys, xs = np.where(ink_mask | blue_mask)
bbox = [xs.min()/S, ys.min()/S, (xs.max()+1)/S, (ys.max()+1)/S]
import json
json.dump({'bbox': [float(v) for v in bbox], 'glyphs': [{'id': g[0], 'd': g[1], 'x': [float(v) for v in g[2]] if g[2] else None} for g in glyphs]}, open(out + '.json', 'w'))
vb = f"{bbox[0]-4} {bbox[1]-4} {bbox[2]-bbox[0]+8} {bbox[3]-bbox[1]+8}"
svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}">' + ''.join(
    f'<path id="{g[0]}" fill="{"#3B82F6" if g[0]=="bolt" else "#0B1020"}" d="{g[1]}"/>' for g in glyphs) + '</svg>'
open(out + '.svg', 'w').write(svg)
print('bbox', bbox)

# The scenes load the glyphs as a classic script (no fetch at render time).
data = json.load(open(out + '.json'))
open(out.rsplit('/', 1)[0] + '/glyphs.js', 'w').write(
    "// Nerava logo traced from logo/source.png (8x upsample + potrace, one path per glyph).\n"
    "// Coordinates are source-PNG pixels. Regenerate with logo/trace.py; don't hand-edit.\n"
    "window.NERAVA_GLYPHS = " + json.dumps(data) + ";\n")
import os; os.remove(out + '.json')
