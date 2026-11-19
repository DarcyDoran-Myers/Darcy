"""Step 2b: remove open water (ocean, bays, Lake Okeechobee, lakes/rivers >= ~1,000 ac) from dated pieces."""
import sys, os
import numpy as np, geopandas as gpd, shapely
from shapely import box

W = sys.argv[1]
def polys(g):
    if g.is_empty or g.geom_type in ('Polygon', 'MultiPolygon'): return g
    ps = [p for p in getattr(g, 'geoms', []) if p.geom_type in ('Polygon', 'MultiPolygon')]
    return shapely.union_all(ps) if ps else shapely.Polygon()

G = 0.5
shore = gpd.read_file(W + 'shore.geojson').to_crs(3086)
land = polys(shapely.union_all(shapely.make_valid(shore[shore.WATER == 0].geometry.values), grid_size=G))
lakes = gpd.read_file(W + 'water.geojson').to_crs(3086)
lakes = polys(shapely.union_all(shapely.make_valid(lakes.geometry.values), grid_size=G))

o = gpd.read_parquet(W + 'pieces.parquet')
xmin, ymin, xmax, ymax = o.total_bounds
# water = everything in the extent that is not land, plus large inland water; tiled for fast local differencing
tiles = [box(x, y, x + 20000, y + 20000) for x in np.arange(xmin - 1000, xmax + 1000, 20000)
         for y in np.arange(ymin - 1000, ymax + 1000, 20000)]
wt = []
for t in tiles:
    lt = polys(shapely.intersection(land, t, grid_size=G))
    w = polys(shapely.union(polys(shapely.difference(t, lt, grid_size=G)),
                            polys(shapely.intersection(lakes, t, grid_size=G)), grid_size=G))
    if not w.is_empty: wt.append(w)
wt = np.array(wt)
tree = shapely.STRtree(wt)
print('water tiles', len(wt))

before = o.area.sum()
out = []
for g in o.geometry.values:
    hits = tree.query(g, predicate='intersects')
    if len(hits):
        try: g = shapely.difference(polys(g), shapely.union_all(wt[hits], grid_size=G), grid_size=G)
        except Exception: g = shapely.difference(g.buffer(0), shapely.union_all(wt[hits]).buffer(0))
        g = polys(shapely.make_valid(g))
    out.append(g)
o['geometry'] = out
o = o[~o.geometry.is_empty & (o.area > 400)]
print('acres before %.0f after %.0f' % (before / 4046.86, o.area.sum() / 4046.86))
o.to_parquet(W + 'pieces_land.parquet')
