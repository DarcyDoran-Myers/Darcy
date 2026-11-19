import json, sys, urllib.request, urllib.parse, time, concurrent.futures as cf
def get(url, params):
    data = urllib.parse.urlencode(params).encode()
    for i in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=180) as r:
                return json.load(r)
        except Exception as e:
            print('retry', e, file=sys.stderr); time.sleep(3*(i+1))
    raise SystemExit('failed')
def fetch(layer, out, fields, where='1=1', page=1000, offset=None):
    ids = get(layer+'/query', {'where':where,'returnIdsOnly':'true','f':'json'})
    oids = sorted(ids['objectIds']); print(out, len(oids), file=sys.stderr)
    chunks = [oids[i:i+page] for i in range(0,len(oids),page)]
    def one(ch):
        p = {'objectIds':','.join(map(str,ch)),'outFields':fields,'outSR':'4326','f':'geojson','returnGeometry':'true'}
        if offset: p['maxAllowableOffset']=offset
        return get(layer+'/query', p)['features']
    feats=[]
    with cf.ThreadPoolExecutor(6) as ex:
        for f in ex.map(one, chunks): feats+=f
    json.dump({'type':'FeatureCollection','features':feats}, open(out,'w'))
    print(out,'done',len(feats), file=sys.stderr)
W='/tmp/claude-0/-home-user-Darcy/c2bff291-be31-54b8-be92-bb527f50778d/scratchpad/work/'
which=sys.argv[1]
if which=='flma':
    fetch('https://services.arcgis.com/9Jk4Zl9KofTtvg3x/arcgis/rest/services/FL_Conservation_Lands_web/FeatureServer/9', W+'flma.geojson','MANAME,MATYPE,MANAGING_A,MATYPE2,OWNER,TOTACRES,LTF_ACRES,ESMT_HOLD,COUNTY,MA_ID', page=500)
if which=='ff':
    fetch('https://services.arcgis.com/9Jk4Zl9KofTtvg3x/arcgis/rest/services/Florida_Forever_Acquisitions/FeatureServer/2', W+'ff.geojson','PAR_NAME,PRJ_NAME,MA_NAME,MA_ID,ACQ_TYPE,CLOSE_DATE,MAN_AGNCY,ACRES', page=1000)
if which=='sol':
    fetch('https://ca.dep.state.fl.us/arcgis/rest/services/OpenData/STATE_OWNED_LANDS/MapServer/0', W+'sol.geojson','OBJECTID,PROJECT_NAME,DOCUMENT_DATE,CLOSED_DATE,PARCEL_AC,CONSERVATION_STATUS_IND,LAND_ACTION_NAME,MANAGING_AGENCY_NAME,FUNDING_SOURCE_NAME', page=1000, offset=0.00002)
