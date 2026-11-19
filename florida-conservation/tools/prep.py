"""Step 1: load sources, project to Florida Albers (EPSG:3086), derive years, save parquet."""
import sys, re, datetime as dt
import numpy as np, pandas as pd, geopandas as gpd, pyogrio
from shapely import make_valid

W = sys.argv[1]
CRS = 3086

def fix(g):
    g = g[g.geometry.notna() & ~g.geometry.is_empty].copy()
    g = g.to_crs(CRS)
    g['geometry'] = make_valid(g.geometry.values)
    g = g.explode(index_parts=False)
    g = g[g.geom_type.isin(['Polygon', 'MultiPolygon'])]
    return g

def ms_year(v):
    if v is None or (isinstance(v, float) and np.isnan(v)): return np.nan
    return (dt.datetime(1970, 1, 1) + dt.timedelta(milliseconds=float(v))).year

MON = {m: i for i, m in enumerate('JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC'.split(), 1)}
def str_year(s):
    if not isinstance(s, str): return np.nan
    ys = []
    for d, m, y in re.findall(r'(\d{2})-([A-Z]{3})-(\d{2})', s):
        if (d, m, y) == ('01', 'JAN', '00'): continue  # placeholder
        y = int(y); ys.append(1900 + y if y > 26 else 2000 + y)
    return min(ys) if ys else np.nan

# --- FNAI Florida Managed Areas (footprint) ---
f = fix(gpd.read_file(W + 'flma.geojson'))
f['suf'] = f.MATYPE.str[-2:]
ltf_share = (f.LTF_ACRES / f.TOTACRES.replace(0, np.nan)).fillna(0)
f['easement'] = f.suf.isin(['CE', 'AE']) | (ltf_share >= 0.5) | f.MANAME.str.contains('Easement', case=False)
own = f.OWNER.fillna('')
def owner_level(o, t2):
    if 'Water Management District' in o: return 'wmd'
    if o.startswith('US ') or 'National Aeronautics' in o or o.startswith('U.S.'): return 'fed'
    if 'Trustees of the Internal' in o or o.startswith('FL ') or 'Florida' in o or 'University' in o or 'State' in o: return 'state'
    if 'County' in o or 'City' in o or 'Town' in o or 'Village' in o or 'School' in o or 'Authority' in o: return 'local'
    if t2 == 'Federal': return 'fed'
    if t2 == 'State': return 'state'
    if t2 == 'Local': return 'local'
    return 'private'
f['owner_lvl'] = [owner_level(o, t) for o, t in zip(own, f.MATYPE2)]
f['military'] = own.str.contains('Air Force|Navy|Army|Military|Defense|Marine Corps', case=False)
f.to_parquet(W + 'flma.parquet')
print('flma', len(f), f.groupby(['easement', 'owner_lvl']).TOTACRES.sum())

# --- Florida Forever acquisitions (closing dates 2001+) ---
ff = fix(gpd.read_file(W + 'ff.geojson'))
ff['year'] = ff.CLOSE_DATE.map(ms_year)
ff['src'] = 'ff'
ff['ltf'] = ff.ACQ_TYPE.eq('LTF')
ff = ff[ff.year.notna()][['year', 'src', 'ltf', 'geometry']]
print('ff', len(ff), ff.year.min(), ff.year.max())

# --- DEP SOLARIS state-owned lands (deed dates) ---
s = fix(gpd.read_file(W + 'sol.geojson'))
s = s[s.CONSERVATION_STATUS_IND.fillna('').str.contains('Y') &
      ~s.LAND_ACTION_NAME.isin(['Disposed', 'Deleted Owned Land Record'])]
y1 = s.DOCUMENT_DATE.map(ms_year)
y2 = s.CLOSED_DATE.map(str_year)
s['year'] = y1.where(y1.notna() & (y1 >= 1845), y2)
s['src'] = 'dep'
s['ltf'] = False
print('sol dated share', s.year.notna().mean(), 'year range', s.year.min(), s.year.max())
print(s.year.value_counts().head(8))
s = s[s.year.notna()][['year', 'src', 'ltf', 'geometry']]

# --- USGS PAD-US 4.1 (establishment dates, mostly federal + NCED easements) ---
gdb = W + '../dl/PADUS4_1_StateFL.gdb'
pads = []
for layer, ltf in [('PADUS4_1Fee_State_FL', False), ('PADUS4_1Easement_State_FL', True)]:
    p = pyogrio.read_dataframe(gdb, layer=layer, columns=['Date_Est', 'Unit_Nm', 'Own_Type'])
    p['year'] = pd.to_numeric(p.Date_Est, errors='coerce')
    p = p[p.year >= 1845]
    p['src'] = 'padus'; p['ltf'] = ltf
    pads.append(fix(p)[['year', 'src', 'ltf', 'geometry']])
pad = pd.concat(pads)
print('padus dated', len(pad))

d = gpd.GeoDataFrame(pd.concat([s, ff, pad], ignore_index=True), crs=CRS)
d['year'] = d.year.astype(int)
d.to_parquet(W + 'dated.parquet')
print('dated total', len(d), d.groupby('src').size())
