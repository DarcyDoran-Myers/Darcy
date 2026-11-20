"""Build per-cell development timing on the HISDAC 250 m grid.
F       = share of the cell developed in the last satellite year (Annual NLCD fractional impervious >= 20 %)
Timing  = share developed by the first satellite year (1985) follows the cell's cumulative building-record curve
          (HISDAC BUPR, 5-yr epochs); later growth follows the Annual NLCD satellite years.
Output  = sparse cells with F and the years when 25/50/75/100 % of F was reached; yearly statewide acres."""
import sys, json, struct
import numpy as np, rasterio
from rasterio.windows import Window
from scipy import ndimage

W, D, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
m = np.load(W + 'grid_meta.npy'); x0, y0, R = m[0], m[1], m[2]; nx, ny, c0, r0 = map(int, m[3:7])
win = Window(c0, r0, nx, ny); land = np.load(W + 'landmask.npy')
rd = lambda p: np.nan_to_num(rasterio.open(p).read(1, window=win, boundless=True, fill_value=0)).astype(np.float32)
CELL_AC = R * R / 4046.86

NE = [int(y) for y in sys.argv[4].split(',')]       # satellite years, first one must be a BUPR epoch
PFX = sys.argv[5] if len(sys.argv) > 5 else 'adev'
dev = np.stack([np.load(W + f'{PFX}_{y}.npy') for y in NE])
dev = np.maximum.accumulate(dev, axis=0)           # development does not revert
F = dev[-1]; f01 = dev[0]
LAST = NE[-1]
BE = list(range(1900, NE[0] + 1, 5))
B = np.stack([rd(D + f'bupr/BUPR/{y}_BUPR.tif') for y in BE])
B = np.maximum.accumulate(B, axis=0)
fbuy = rd(D + 'f7337822')
has_rec = B[-1] > 0

# pre-2001 curve for cells with records
pre = np.zeros((len(BE),) + F.shape, np.float32)
pre[:, has_rec] = f01[has_rec] * (B[:, has_rec] / B[-1, has_rec])
q = np.zeros(F.shape, np.uint8)  # 0 dated by records, 1 by first-built year, 2 neighbourhood estimate, 3 none
# cells with no records but a first-built year: step at that year
fb = ~has_rec & (fbuy > 0) & (f01 > 0)
for i, y in enumerate(BE):
    pre[i, fb] = np.where(fbuy[fb] <= y, f01[fb], 0)
q[fb] = 1
# neighbourhood estimate for the rest: weighted mean of the median-development year of dated cells nearby
dated = has_rec & (f01 > 0)
half = np.argmax(pre >= 0.5 * np.maximum(f01, 1e-9)[None], axis=0)
myear = np.array(BE, np.float32)[half]
w = np.where(dated, f01, 0).astype(np.float32)
rest = ~has_rec & ~fb & (f01 > 0)
est = np.full(F.shape, np.nan, np.float32)
for size in (9, 33, 129):
    num = ndimage.uniform_filter(w * myear, size); den = ndimage.uniform_filter(w, size)
    ok = rest & np.isnan(est) & (den > 1e-4)
    est[ok] = num[ok] / den[ok]
for i, y in enumerate(BE):
    sel = rest & ~np.isnan(est)
    pre[i, sel] = np.where(est[sel] <= y + 2.5, f01[sel], 0)
q[rest & ~np.isnan(est)] = 2
q[rest & np.isnan(est)] = 3
nodate = rest & np.isnan(est)

# full curve on epoch times
times = np.array(BE + NE[1:], np.float32)
curve = np.concatenate([pre, dev[1:]], axis=0)
curve[:, nodate] = 0
curve[len(BE) - 1:, nodate] = 0
# undated pre-2001 share kept separately; post-2001 growth in undated cells is still dated by NLCD
undated_ac = float(f01[nodate].sum() * CELL_AC)
curve[len(BE):, nodate] = (dev[1:, nodate] - f01[nodate])
Fd = curve[-1]

# yearly statewide acres (linear between epochs)
years = np.arange(1900, LAST + 1)
tot = curve.reshape(len(times), -1).sum(1) * CELL_AC
yearly = np.interp(years, times, tot)
est_tot = curve[:, (q == 2)].sum(1) * CELL_AC
print('developed acres 1900 %.0f 1950 %.0f 1980 %.0f 2000 %.0f last %.0f; undated pre-satellite %.0f; estimated share last %.2f'
      % (yearly[0], yearly[50], yearly[80], yearly[100], yearly[-1], undated_ac, est_tot[-1] / tot[-1]))

# quartile years per cell
keep = Fd >= 0.03
idx = np.flatnonzero(keep)
cv = curve.reshape(len(times), -1)[:, idx]; Fk = Fd.reshape(-1)[idx]
qy = []
for k in (0.25, 0.5, 0.75, 1.0):
    target = Fk * k - 1e-6
    j = np.argmax(cv >= target[None], axis=0)
    jp = np.maximum(j - 1, 0)
    v0, v1 = cv[jp, np.arange(len(idx))], cv[j, np.arange(len(idx))]
    t0, t1 = times[jp], times[j]
    frac = np.where((v1 > v0) & (j > 0), (target - v0) / np.maximum(v1 - v0, 1e-9), 1.0)
    yr = np.where(j == 0, 1900, t0 + frac * (t1 - t0))
    qy.append(np.clip(np.ceil(yr), 1900, LAST).astype(np.int32))
qy = np.stack(qy)
# reproject F and quartile years onto a 250 m grid aligned to Florida Albers (EPSG:3086), the web map's CRS
from rasterio.warp import reproject, Resampling, transform_bounds
from rasterio.transform import Affine
src_T = Affine(R, 0, x0, 0, -R, y0)
grids = np.zeros((5,) + F.shape, np.float32)
flat = grids.reshape(5, -1); flat[0, idx] = Fk; flat[1:, idx] = qy
bx0, by0, bx1, by1 = transform_bounds(5070, 3086, x0, y0 - ny * R, x0 + nx * R, y0)
bx0, by1 = np.floor(bx0 / R) * R, np.ceil(by1 / R) * R
gnx, gny = int(np.ceil((bx1 - bx0) / R)), int(np.ceil((by1 - by0) / R))
dst_T = Affine(R, 0, bx0, 0, -R, by1)
out = np.zeros((5, gny, gnx), np.float32)
for k in range(5):
    reproject(grids[k], out[k], src_transform=src_T, src_crs=5070, dst_transform=dst_T, dst_crs=3086, resampling=Resampling.nearest)
idx = np.flatnonzero(out[0] > 0); Fk = out[0].reshape(-1)[idx]; qy = out[1:].reshape(4, -1)[:, idx].astype(np.int32)
nx, ny, x0, y0 = gnx, gny, bx0, by1
print('cells kept', len(idx), 'of', int((Fd > 0).sum()), 'acres kept %.0f' % (Fk.sum() * CELL_AC))

# binary: header, then per cell: varint index delta, F (0-255), 4 years (year-1900)
buf = bytearray()
prev = 0
for i, f, a, b, c, d in zip(idx, np.round(Fk * 255).astype(int), *(qy - 1900)):
    dlt = int(i - prev); prev = int(i)
    while True:
        byte = dlt & 0x7F; dlt >>= 7
        buf.append(byte | (0x80 if dlt else 0))
        if not dlt: break
    buf += bytes((max(1, f), a, b, c, d))
open(OUT + 'developed.bin', 'wb').write(buf)
# grid placement in EPSG:3086 (top-left corner, cell size)
json.dump({'nx': nx, 'ny': ny, 'cell_acres': CELL_AC, 'x0': float(x0), 'y0': float(y0), 'res': R, 'n': int(len(idx)),
           'yearly': {int(y): round(float(v)) for y, v in zip(years, yearly)},
           'estimated_share_last': round(float(est_tot[-1] / tot[-1]), 3), 'undated_presat_acres': round(undated_ac), 'last': LAST, 'sat_years': NE},
          open(OUT + 'developed_meta.json', 'w'), separators=(',', ':'))
print('bytes', len(buf))
