"""Annual NLCD Collection 1.2 fractional impervious (30 m) -> share of each HISDAC 250 m cell with >= 20 % impervious.
Downloads one national zip at a time from ScienceBase, reads the Florida window tile by tile, deletes the zip."""
import sys, os, zipfile, subprocess
import numpy as np, rasterio
from rasterio.windows import from_bounds
from rasterio.transform import Affine
from rasterio.warp import reproject, Resampling

W, DL = sys.argv[1], sys.argv[2]; years = [int(y) for y in sys.argv[3].split(',')]
x0, y0, R, nx, ny, c0, r0 = np.load(W + 'grid_meta.npy'); nx, ny = int(nx), int(ny)
land = np.load(W + 'landmask.npy')
ITEM = '697b907eb66b0197c3043c9f'
TS = 400
tiles = [(ty, tx) for ty in range(0, ny, TS) for tx in range(0, nx, TS) if land[ty:ty + TS, tx:tx + TS].any()]
for y in years:
    if os.path.exists(W + f'adev_{y}.npy'): continue
    name = f'Annual_NLCD_FctImp_{y}_CU_C1V2.zip'; zp = DL + name
    subprocess.run(['curl', '-sSL', '--retry', '4', '-m', '1800', '-o', zp,
                    f'https://www.sciencebase.gov/catalog/file/get/{ITEM}?name={name}'], check=True)
    tif = [n for n in zipfile.ZipFile(zp).namelist() if n.lower().endswith('.tif')][0]
    full = np.zeros((ny, nx), np.float32)
    with rasterio.open(f'/vsizip/{zp}/{tif}') as src:
        for ty, tx in tiles:
            h, w = min(TS, ny - ty), min(TS, nx - tx)
            xmin = x0 + tx * R; ymax = y0 - ty * R
            win = from_bounds(xmin - 90, ymax - h * R - 90, xmin + w * R + 90, ymax + 90, src.transform).round_offsets().round_lengths()
            a = src.read(1, window=win, boundless=True, fill_value=0)
            dev = ((a >= 20) & (a <= 100)).astype(np.float32)
            out = np.zeros((h, w), np.float32)
            reproject(dev, out, src_transform=src.window_transform(win), src_crs=src.crs,
                      dst_transform=Affine(R, 0, xmin, 0, -R, ymax), dst_crs='EPSG:5070', resampling=Resampling.average)
            full[ty:ty + h, tx:tx + w] = out
    full[~land] = 0
    np.save(W + f'adev_{y}.npy', full)
    os.remove(zp)
    print(y, 'developed acres %.0f' % (full.sum() * R * R / 4046.86), flush=True)
