"""Fetch NLCD impervious (30 m) by tile over Florida and reduce to the HISDAC 250 m grid:
value = share of 30 m pixels with >= 20 % impervious (NLCD's developed threshold)."""
import sys, io, time, urllib.request, concurrent.futures as cf
import numpy as np, rasterio, geopandas as gpd
from rasterio.transform import Affine
from rasterio.warp import reproject, Resampling
from rasterio.features import rasterize

W = sys.argv[1]; years = [int(y) for y in sys.argv[2].split(',')]
# HISDAC grid (EPSG:5070, 250 m)
X0, Y0, R = -2356398.7593, 3172999.2874, 250.0
c0 = int((788000 - X0) // R); c1 = int((1650000 - X0) // R) + 1
r0 = int((Y0 - 1022000) // R); r1 = int((Y0 - 188000) // R) + 1
nx, ny = c1 - c0, r1 - r0
T = Affine(R, 0, X0 + c0 * R, 0, -R, Y0 - r0 * R)
np.save(W + 'grid_meta.npy', np.array([X0 + c0 * R, Y0 - r0 * R, R, nx, ny, c0, r0]))
shore = gpd.read_file(W + 'shore.geojson').to_crs(5070)
land = rasterize([(g, 1) for g in shore[shore.WATER == 0].geometry], out_shape=(ny, nx), transform=T, all_touched=True).astype(bool)
np.save(W + 'landmask.npy', land)
print('grid', nx, ny, 'land cells', land.sum(), flush=True)

TS = 400  # cells per tile side (100 km)
tiles = [(ty, tx) for ty in range(0, ny, TS) for tx in range(0, nx, TS) if land[ty:ty + TS, tx:tx + TS].any()]
print('tiles', len(tiles), flush=True)

def fetch(year, ty, tx):
    h, w = min(TS, ny - ty), min(TS, nx - tx)
    xmin = T.c + tx * R; ymax = T.f - ty * R
    xmax, ymin = xmin + w * R, ymax - h * R
    # snap request to NLCD 30 m grid (origin -2493045, 3310005) with a margin
    gx = lambda v, f: -2493045 + f((v + 2493045) / 30) * 30
    gy = lambda v, f: 3310005 - f((3310005 - v) / 30) * 30
    qx0, qx1 = gx(xmin - 60, np.floor), gx(xmax + 60, np.ceil)
    qy1, qy0 = gy(ymax + 60, np.floor), gy(ymin - 60, np.ceil)
    url = ('https://www.mrlc.gov/geoserver/mrlc_download/wcs?service=WCS&version=2.0.1&request=GetCoverage'
           f'&coverageId=mrlc_download__NLCD_{year}_Impervious_L48&subset=X({qx0:.0f},{qx1:.0f})&subset=Y({qy0:.0f},{qy1:.0f})&format=image/geotiff')
    for k in range(6):
        try:
            data = urllib.request.urlopen(url, timeout=300).read()
            with rasterio.MemoryFile(data) as mf, mf.open() as src:
                a = src.read(1); st = src.transform
            break
        except Exception as e:
            print('retry', year, ty, tx, e, flush=True); time.sleep(5 * (k + 1))
    else:
        raise SystemExit('failed tile')
    dev = ((a >= 20) & (a <= 100)).astype(np.float32)
    out = np.zeros((h, w), np.float32)
    reproject(dev, out, src_transform=st, src_crs='EPSG:5070', dst_transform=Affine(R, 0, xmin, 0, -R, ymax),
              dst_crs='EPSG:5070', resampling=Resampling.average)
    return ty, tx, out

for y in years:
    full = np.zeros((ny, nx), np.float32)
    with cf.ThreadPoolExecutor(4) as ex:
        for i, (ty, tx, out) in enumerate(ex.map(lambda t: fetch(y, *t), tiles)):
            full[ty:ty + out.shape[0], tx:tx + out.shape[1]] = out
    full[~land] = 0
    np.save(W + f'dev_{y}.npy', full)
    print(y, 'developed acres %.0f' % (full.sum() * R * R / 4046.86), flush=True)
