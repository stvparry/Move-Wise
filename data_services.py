import re,time,requests
from collections import Counter
UA={"User-Agent":"MoveWise-UK-v3 educational demo"}
SERVERS=["https://overpass-api.de/api/interpreter","https://overpass.kumi.systems/api/interpreter","https://overpass.nchc.org.tw/api/interpreter"]
TAGS={"Shops":'[shop]',"Schools":'[amenity=school]',"Parks":'[leisure=park]',"Leisure":'[leisure~"fitness_centre|sports_centre|swimming_pool|golf_course"]',"Healthcare":'[amenity~"hospital|clinic|doctors|pharmacy"]',"Social life":'[amenity~"restaurant|cafe|pub"]',"Rail":'[railway=station]',"Bus":'[highway=bus_stop]'}
def js(url,params=None,timeout=20,method="get",data=None):
 r=requests.request(method,url,params=params,data=data,headers=UA,timeout=timeout);r.raise_for_status();return r.json()
def candidates(text,limit=6):
 text=text.strip();out=[];pc=re.search(r"\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b",text.upper())
 if pc:
  try:
   x=js("https://api.postcodes.io/postcodes/"+pc.group(1).replace(" ",""))["result"];out.append({"label":f"{x['postcode']} · {x.get('admin_district','')}","lat":x['latitude'],"lon":x['longitude'],"kind":"postcode"})
  except Exception:pass
 try:
  q=text if any(k in text.lower() for k in ['united kingdom','england','wales','scotland','northern ireland']) else text+", United Kingdom"
  for x in js("https://nominatim.openstreetmap.org/search",{"q":q,"format":"jsonv2","addressdetails":1,"limit":limit,"countrycodes":"gb"}):
   z={"label":x["display_name"],"lat":float(x["lat"]),"lon":float(x["lon"]),"kind":x.get("type","place")}
   if not any(abs(z['lat']-a['lat'])<.0001 and abs(z['lon']-a['lon'])<.0001 for a in out):out.append(z)
 except Exception:pass
 return out[:limit]
def amenities(lat,lon,radius):
 bits=[]
 for tag in TAGS.values():
  for obj in ['node','way','relation']:bits.append(f'{obj}{tag}(around:{radius},{lat},{lon});')
 query='[out:json][timeout:30];('+''.join(bits)+');out center tags;'
 for endpoint in SERVERS:
  try:
   rows=js(endpoint,timeout=45,method='post',data=query).get('elements',[]);out={k:[] for k in TAGS}
   for e in rows:
    t=e.get('tags',{});m=[]
    if 'shop' in t:m+=['Shops']
    if t.get('amenity')=='school':m+=['Schools']
    if t.get('leisure')=='park':m+=['Parks']
    if t.get('leisure') in ['fitness_centre','sports_centre','swimming_pool','golf_course']:m+=['Leisure']
    if t.get('amenity') in ['hospital','clinic','doctors','pharmacy']:m+=['Healthcare']
    if t.get('amenity') in ['restaurant','cafe','pub']:m+=['Social life']
    if t.get('railway')=='station':m+=['Rail']
    if t.get('highway')=='bus_stop':m+=['Bus']
    for k in m:out[k].append(t.get('name','Unnamed'))
   return out,None
  except Exception:time.sleep(.4)
 return {k:[] for k in TAGS},'Local amenity data is temporarily unavailable. The remaining evidence is still shown.'
def profile(loc,radius):
 am,w=amenities(loc['lat'],loc['lon'],radius)
 try:cr=js('https://data.police.uk/api/crimes-street/all-crime',{'lat':loc['lat'],'lng':loc['lon']},30);cw=None
 except Exception:cr=[];cw='Police.uk data is temporarily unavailable.'
 caps={'Shops':80,'Schools':15,'Parks':10,'Leisure':15,'Healthcare':20,'Social life':70};s={k:min(100,len(am[k])*100/caps[k]) for k in caps};s['Travel']=min(100,len(am['Rail'])*35+len(am['Bus'])*2);s['Lower recorded crime']=max(0,100-len(cr)/8) if not cw else 50
 return {'scores':s,'counts':{k:len(v) for k,v in am.items()},'crime':len(cr),'warnings':[x for x in [w,cw] if x],'crime_categories':Counter(x.get('category','other') for x in cr)}
def routing(a,b):
 try:
  x=js(f"https://router.project-osrm.org/route/v1/driving/{a['lon']},{a['lat']};{b['lon']},{b['lat']}",{'overview':'false'},30)['routes'][0];return x['distance']/1609.344,x['duration']/60
 except Exception:return None
