"""Step 2: make FNAI footprint disjoint, then date every piece of it from parcel records."""
import sys
import numpy as np, pandas as pd, geopandas as gpd
import shapely
from shapely import make_valid
import shapely as _s
G = 0.5
from shapely.geometry import MultiPolygon, Polygon
def polys(g):
    if g is None or g.is_empty: return Polygon()
    if g.geom_type in ('Polygon', 'MultiPolygon'): return g
    ps = []
    for p in getattr(g, 'geoms', []):
        if p.geom_type == 'Polygon': ps.append(p)
        elif p.geom_type == 'MultiPolygon': ps.extend(p.geoms)
    return MultiPolygon(ps) if ps else Polygon()
def safe(fn, *a):
    try: return polys(fn(*a, grid_size=G))
    except Exception:
        a = [polys(make_valid(x)).buffer(0) if hasattr(x, 'geom_type') else x for x in a]
        try: return polys(fn(*a, grid_size=G))
        except Exception: return polys(fn(*[polys(x).buffer(0.01) if hasattr(x,'geom_type') else x for x in a]))
def union_all(a): return safe(_s.union_all, polys_arr(a))
def polys_arr(a): return np.array([polys(make_valid(x)) for x in a])
def intersection(a, b): return safe(_s.intersection, polys(a), polys(b))
def difference(a, b): return safe(_s.difference, polys(a), polys(b))

W = sys.argv[1]
f = gpd.read_parquet(W + 'flma.parquet')
d = gpd.read_parquet(W + 'dated.parquet')

# class: easement vs government fee (by level) vs private/NGO fee
f['cls'] = np.where(f.easement, 'esmt', np.where(f.owner_lvl == 'private', 'ngo', f.owner_lvl))
prio = {'fed': 0, 'state': 1, 'wmd': 2, 'local': 3, 'ngo': 4, 'esmt': 5}
f['prio'] = f.cls.map(prio)
f = f.sort_values(['prio', 'TOTACRES'], ascending=[True, False]).reset_index(drop=True)
f['geometry'] = shapely.set_precision(f.geometry.values, 1.0)

# --- disjoint footprint: subtract all higher-priority polygons ---
geoms = f.geometry.values
tree = shapely.STRtree(geoms)
out = []
for i, g in enumerate(geoms):
    hits = [j for j in tree.query(g) if j < i]
    if hits:
        g = difference(g, union_all(geoms[hits]))
    out.append(g)
f['geometry'] = make_valid(np.array(out))
f = f[~f.geometry.is_empty]
f.to_parquet(W + 'disjoint_raw.parquet')
f = f.explode(index_parts=False)
f = f[f.geom_type == 'Polygon']
f = f[f.area > 4047 * 0.5].reset_index(drop=True)  # drop < 0.5 ac crumbs
print('disjoint pieces', len(f), 'acres', f.area.sum() / 4047)

# --- date assignment ---
d = d.reset_index(drop=True)
d['geometry'] = d.buffer(20, quad_segs=2)  # close hairline gaps between parcels and footprint
dg = d.geometry.values
dy = d.year.values
dsrc = d.src.values
dltf = d.ltf.values.astype(bool)
dtree = shapely.STRtree(dg)
SRC_RANK = {'dep': 0, 'ff': 1, 'padus': 2}

def date_piece(k):
    rows = []
    r = F[k]
    rem = polys(make_valid(r.geometry))
    base = dict(ma=r.MANAME, ma_id=int(r.MA_ID), cls=r.cls, mil=bool(r.military))
    hits = dtree.query(rem, predicate='intersects')
    # easements are dated only by easement records, fee land only by fee records
    hits = hits[dltf[hits] == (r.cls == 'esmt')]
    dated_area = {}
    if len(hits):
        for y in sorted(set(dy[hits])):
            idx = hits[dy[hits] == y]
            part = intersection(rem, union_all(dg[idx]))
            if part.is_empty or part.area < 100: continue
            src = sorted(dsrc[idx], key=SRC_RANK.get)[0]
            rows.append({**base, 'year': int(y), 'q': 'parcel', 'src': src, 'geometry': part})
            dated_area[int(y)] = dated_area.get(int(y), 0) + part.area
            rem = difference(rem, part)
            if rem.is_empty: break
    if not rem.is_empty and rem.area > 100:
        opened = intersection(polys(make_valid(rem.buffer(-40, quad_segs=2).buffer(40, quad_segs=2))), rem)
        sliver = difference(rem, opened)
        if dated_area and not sliver.is_empty:
            ydom = max(dated_area, key=dated_area.get)
            rows.append({**base, 'year': ydom, 'q': 'parcel', 'src': 'edge', 'geometry': sliver})
            rem = opened
        if not rem.is_empty and rem.area > 100:
            rows.append({**base, 'year': -1, 'q': 'resid', 'src': '',
                         'earliest': min(dated_area) if dated_area else -1, 'geometry': rem})
    return rows


F = list(f.itertuples())
from multiprocessing import Pool
with Pool(4) as pool:
    rows = [x for rs in pool.imap(date_piece, range(len(F)), chunksize=50) for x in rs]
o = gpd.GeoDataFrame(rows, crs=3086)
o['geometry'] = make_valid(o.geometry.values)
o['acres'] = o.area / 4046.86
o.to_parquet(W + 'pieces.parquet')
print(o.groupby(['q', 'cls']).acres.sum())
