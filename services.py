import re,time,requests
from collections import Counter
UA={'User-Agent':'MoveWise-UK-v4 educational relocation demo'}
OVERPASS=['https://overpass.kumi.systems/api/interpreter','https://overpass-api.de/api/interpreter','https://overpass.nchc.org.tw/api/interpreter']
TAGS={'Shops':'[shop]','Schools':'[amenity=school]','Parks':'[leisure=park]','Leisure':'[leisure~"fitness_centre|sports_centre|swimming_pool|golf_course"]','Healthcare':'[amenity~"hospital|clinic|doctors|pharmacy"]','Social life':'[amenity~"restaurant|cafe|pub"]','Rail':'[railway=station]','Bus':'[highway=bus_stop]'}
def get(url,params=None,timeout=25):
 r=requests.get(url,params=params,headers=UA,timeout=timeout);r.raise_for_status();return r.json()
def candidates(text,limit=6):
 out=[];text=text.strip();pc=re.search(r'\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b',text.upper())
 if pc:
  try:
   x=get('https://api.postcodes.io/postcodes/'+pc.group(1).replace(' ',''))['result'];out.append({'label':f"{x['postcode']} · {x.get('admin_district','')} · {x.get('region','')}",'lat':x['latitude'],'lon':x['longitude'],'kind':'postcode','admin':x.get('admin_district',''),'region':x.get('region',''),'codes':x.get('codes',{})})
  except Exception:pass
 try:
  q=text if 'united kingdom' in text.lower() else text+', United Kingdom'
  for x in get('https://nominatim.openstreetmap.org/search',{'q':q,'format':'jsonv2','addressdetails':1,'limit':limit,'countrycodes':'gb'}):
   a=x.get('address',{});z={'label':x['display_name'],'lat':float(x['lat']),'lon':float(x['lon']),'kind':x.get('type','place'),'admin':a.get('county') or a.get('city') or a.get('town') or '','region':a.get('state',''),'codes':{}}
   if not any(abs(z['lat']-v['lat'])<.0001 and abs(z['lon']-v['lon'])<.0001 for v in out):out.append(z)
 except Exception:pass
 return out[:limit]
def amenities(lat,lon,radius):
 parts=[]
 for tag in TAGS.values():
  for typ in ['node','way','relation']:parts.append(f'{typ}{tag}(around:{radius},{lat},{lon});')
 query='[out:json][timeout:25];('+''.join(parts)+');out center tags;'
 for endpoint in OVERPASS:
  try:
   r=requests.get(endpoint,params={'data':query},headers=UA,timeout=45);r.raise_for_status();rows=r.json().get('elements',[]);out={k:[] for k in TAGS}
   for e in rows:
    t=e.get('tags',{});cats=[]
    if 'shop' in t:cats+=['Shops']
    if t.get('amenity')=='school':cats+=['Schools']
    if t.get('leisure')=='park':cats+=['Parks']
    if t.get('leisure') in ['fitness_centre','sports_centre','swimming_pool','golf_course']:cats+=['Leisure']
    if t.get('amenity') in ['hospital','clinic','doctors','pharmacy']:cats+=['Healthcare']
    if t.get('amenity') in ['restaurant','cafe','pub']:cats+=['Social life']
    if t.get('railway')=='station':cats+=['Rail']
    if t.get('highway')=='bus_stop':cats+=['Bus']
    for c in cats:out[c].append(t.get('name','Unnamed'))
   if rows:return out,{'ok':True,'source':'OpenStreetMap/Overpass','detail':f'{len(rows)} map objects returned'}
  except Exception:time.sleep(.4)
 return {k:[] for k in TAGS},{'ok':False,'source':'OpenStreetMap/Overpass','detail':'All public endpoints failed or returned no objects'}
def crime(lat,lon):
 try:
  rows=get('https://data.police.uk/api/crimes-street/all-crime',{'lat':lat,'lng':lon},30);return rows,{'ok':True,'source':'Police.uk','detail':f'{len(rows)} recent street-level records returned'}
 except Exception:return [],{'ok':False,'source':'Police.uk','detail':'Service unavailable'}
def route(a,b):
 try:
  x=get(f"https://router.project-osrm.org/route/v1/driving/{a['lon']},{a['lat']};{b['lon']},{b['lat']}",{'overview':'false'},30)['routes'][0];return (x['distance']/1609.344,x['duration']/60),{'ok':True,'source':'OSRM','detail':'Approximate road route, no live traffic'}
 except Exception:return None,{'ok':False,'source':'OSRM','detail':'Service unavailable'}
def profile(loc,radius):
 am,ast=amenities(loc['lat'],loc['lon'],radius);cr,cst=crime(loc['lat'],loc['lon']);scores={};available=[]
 if ast['ok']:
  caps={'Shops':80,'Schools':15,'Parks':10,'Leisure':15,'Healthcare':20,'Social life':70};scores.update({k:min(100,len(am[k])*100/caps[k]) for k in caps});scores['Travel']=min(100,len(am['Rail'])*35+len(am['Bus'])*2);available+=list(caps)+['Travel']
 if cst['ok']:scores['Lower recorded crime']=max(0,100-len(cr)/8);available+=['Lower recorded crime']
 return {'scores':scores,'available':available,'counts':{k:len(v) for k,v in am.items()},'crime_count':len(cr),'crime_categories':Counter(x.get('category','other').replace('-',' ').title() for x in cr),'status':[ast,cst]}
