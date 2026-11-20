"""Step 3: resolve undated pieces, dissolve, simplify, write web data + yearly stats."""
import sys, json
import numpy as np, pandas as pd, geopandas as gpd
import shapely

W, OUT = sys.argv[1], sys.argv[2]
sys.path.insert(0, sys.argv[3])
from curated import YEARS  # {FNAI managed-area name: establishment year}

o = gpd.read_parquet(W + 'pieces_land.parquet')
res = o.q == 'resid'
cur = o.ma.map(YEARS)
o.loc[res & cur.notna(), 'year'] = cur[res & cur.notna()]
o.loc[res & cur.notna(), 'q'] = 'unit'
est = res & cur.isna() & (o.earliest > 0)
o.loc[est, 'year'] = o.loc[est, 'earliest']
o.loc[est, 'q'] = 'est'
unk = res & cur.isna() & ~(o.earliest > 0)
o.loc[unk, 'year'] = 0
o.loc[unk, 'q'] = 'none'
o['year'] = o.year.astype(int)
o['acres'] = o.area / 4046.86

# undated report for curation
r = o[o.q.isin(['none', 'est'])].groupby(['ma', 'cls', 'q']).acres.sum().sort_values(ascending=False)
r.head(80).to_csv(W + 'undated_report.csv')
print(o.groupby('q').acres.sum().round())

# yearly stats (unsimplified acreage)
from ownership import owner_class
fl_own = pd.read_parquet(W + 'flma.parquet', columns=['MA_ID', 'OWNER']).drop_duplicates('MA_ID')
own_map = dict(zip(fl_own.MA_ID.astype(int), fl_own.OWNER.map(owner_class)))
o['own'] = o.ma_id.map(own_map).fillna('private')
OWN = ['public', 'private', 'nonprofit', 'tribal']
o['grp'] = o.own
st = o.groupby(['year', 'grp', 'mil']).acres.sum().unstack(['grp', 'mil'], fill_value=0)
stats = {}
for y, row in st.iterrows():
    stats[int(y)] = {f'{g}{"_m" if m else ""}': round(float(v)) for (g, m), v in row.items() if v > 0}
lvl = o[o.grp == 'public'].groupby(['year', 'cls', 'mil']).acres.sum()
lv = {}
for (y, c, m), v in lvl.items():
    lv.setdefault(int(y), {})[c + ('_m' if m else '')] = round(float(v))

# dissolve per managed area / class / year, simplify for the web
d = o.dissolve(by=['ma_id', 'ma', 'cls', 'own', 'year', 'q', 'mil'], as_index=False, aggfunc={'acres': 'sum'})
d['geometry'] = shapely.simplify(d.geometry.values, 35, preserve_topology=True)
d['geometry'] = shapely.make_valid(d.geometry.values)
d = d[~d.geometry.is_empty & (d.acres >= 0.5)]
d = d.explode(index_parts=False)
d = d[d.geom_type == 'Polygon']
d = d[d.area > 4047 * 0.4]  # drop slivers under ~0.4 ac after simplification
d = d.dissolve(by=['ma_id', 'ma', 'cls', 'own', 'year', 'q', 'mil'], as_index=False, aggfunc={'acres': 'first'})
names = sorted(d.ma.unique())
ni = {n: i for i, n in enumerate(names)}
CLS = ['fed', 'state', 'wmd', 'local', 'ngo', 'esmt']
Q = ['parcel', 'unit', 'est', 'none']
d['o'] = d.own.map(OWN.index); d['e'] = (d.cls == 'esmt').astype(int); d['n'] = d.ma.map(ni); d['c'] = d.cls.map(CLS.index); d['k'] = d.q.map(Q.index)
d['y'] = d.year; d['m'] = d.mil.astype(int); d['a'] = d.acres.round().astype(int)
d[['n', 'c', 'o', 'e', 'k', 'y', 'm', 'a', 'geometry']].to_file(W + 'web_lands.geojson', driver='GeoJSON')

# basemap from the same 1:12,000 shoreline used to clip water
sh = gpd.read_file(W + 'shore.geojson').to_crs(3086)
co = sh[sh.WATER == 0].copy()
co['geometry'] = shapely.simplify(shapely.make_valid(co.geometry.values), 120, preserve_topology=True)
co = co.explode(index_parts=False); co = co[co.area > 4e5]
co = co.dissolve(by='NAME', as_index=False)
co[['NAME', 'geometry']].to_file(W + 'web_counties.geojson', driver='GeoJSON')
st = gpd.GeoDataFrame(geometry=[shapely.union_all(co.geometry.values, grid_size=1)], crs=3086)
st.to_file(W + 'web_state.geojson', driver='GeoJSON')
lk = pd.concat([gpd.read_file(W + 'water.geojson').to_crs(3086)[['geometry']], sh[sh.WATER == 1][['geometry']]])
lk['geometry'] = shapely.simplify(shapely.make_valid(lk.geometry.values), 80, preserve_topology=True)
lk = lk.explode(index_parts=False); lk = lk[lk.area > 4e6]
lk.to_file(W + 'web_lakes.geojson', driver='GeoJSON')

esm = o[(o.cls == 'esmt') & ~o.mil].groupby('year').acres.sum()
o['g3'] = np.where((o.cls == 'esmt') & (o.own != 'tribal'), 'esmt', np.where(o.own == 'public', 'public', 'other'))
st3 = o.groupby(['year', 'g3', 'mil']).acres.sum()
stats3 = {}
for (y, g, m), v in st3.items():
    stats3.setdefault(int(y), {})[g + ('_m' if m else '')] = round(float(v))
json.dump({'names': names, 'cls': CLS, 'own': OWN, 'stats3': stats3, 'easement': {int(y): round(float(v)) for y, v in esm.items()}, 'q': Q, 'stats': stats, 'levels': lv,
           'qacres': {k: round(float(v)) for k, v in o.groupby('q').acres.sum().items()}},
          open(OUT + 'meta.json', 'w'), separators=(',', ':'))
print('features', len(d))
