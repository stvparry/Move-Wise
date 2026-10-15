import re,time,html,requests,pandas as pd,plotly.graph_objects as go,streamlit as st,folium
from streamlit_folium import st_folium
st.set_page_config(page_title='MoveWise UK v5.1',page_icon='🏡',layout='wide')
UA={'User-Agent':'MoveWise-UK-v5.1 educational demo'}; THEMES=['Travel','Parks','Shops','Schools','Leisure','Healthcare','Social life','Lower recorded crime']
SERVERS=['https://overpass.kumi.systems/api/interpreter','https://overpass-api.de/api/interpreter','https://overpass.nchc.org.tw/api/interpreter']
TAGS={'Shops':'[shop]','Schools':'[amenity=school]','Parks':'[leisure=park]','Leisure':'[leisure~"fitness_centre|sports_centre|swimming_pool|golf_course"]','Healthcare':'[amenity~"hospital|clinic|doctors|pharmacy"]','Social life':'[amenity~"restaurant|cafe|pub"]','Rail':'[railway=station]','Bus':'[highway=bus_stop]'}
def get(url,params=None,timeout=25,headers=None):
 r=requests.get(url,params=params,headers=headers or UA,timeout=timeout);r.raise_for_status();return r.json()
@st.cache_data(ttl=86400,show_spinner=False)
def candidates(text,limit=6):
 out=[];text=text.strip();pc=re.search(r'\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b',text.upper())
 if pc:
  try:
   x=get('https://api.postcodes.io/postcodes/'+pc.group(1).replace(' ',''))['result'];out.append({'label':f"{x['postcode']} · {x.get('admin_district','')}",'lat':x['latitude'],'lon':x['longitude'],'kind':'postcode'})
  except Exception:pass
 try:
  q=text if 'united kingdom' in text.lower() else text+', United Kingdom'
  for x in get('https://nominatim.openstreetmap.org/search',{'q':q,'format':'jsonv2','addressdetails':1,'limit':limit,'countrycodes':'gb'}):
   z={'label':x['display_name'],'lat':float(x['lat']),'lon':float(x['lon']),'kind':x.get('type','place')}
   if not any(abs(z['lat']-v['lat'])<.0001 and abs(z['lon']-v['lon'])<.0001 for v in out):out.append(z)
 except Exception:pass
 return out[:limit]
@st.cache_data(ttl=21600,show_spinner=False)
def amenities(lat,lon,radius):
 parts=[f'{typ}{tag}(around:{radius},{lat},{lon});' for tag in TAGS.values() for typ in ['node','way','relation']];query='[out:json][timeout:25];('+''.join(parts)+');out center tags;'
 for endpoint in SERVERS:
  try:
   rows=get(endpoint,{'data':query},45).get('elements',[]);out={k:[] for k in TAGS}
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
   if rows:return out,{'ok':True,'source':'OpenStreetMap/Overpass','detail':f'{len(rows)} map objects returned'}
  except Exception:time.sleep(.3)
 return {k:[] for k in TAGS},{'ok':False,'source':'OpenStreetMap/Overpass','detail':'No usable response from public endpoints'}
@st.cache_data(ttl=3600,show_spinner=False)
def police(lat,lon):
 try:
  x=get('https://data.police.uk/api/crimes-street/all-crime',{'lat':lat,'lng':lon},30);return x,{'ok':True,'source':'Police.uk','detail':f'{len(x)} records returned'}
 except Exception:return [],{'ok':False,'source':'Police.uk','detail':'Unavailable'}
@st.cache_data(ttl=3600,show_spinner=False)
def food(lat,lon,radius):
 try:
  h={**UA,'x-api-version':'2','Accept-Language':'en-GB'};x=get('https://api.ratings.food.gov.uk/Establishments',{'latitude':lat,'longitude':lon,'maxDistanceLimit':min(10,radius/1000),'pageSize':500},35,h).get('establishments',[]);vals=[]
  for z in x:
   try:vals.append(int(z.get('RatingValue')))
   except Exception:pass
  return {'count':len(x),'high':sum(v>=4 for v in vals)},{'ok':True,'source':'Food Standards Agency','detail':f'{len(x)} establishments returned'}
 except Exception:return None,{'ok':False,'source':'Food Standards Agency','detail':'Unavailable'}
@st.cache_data(ttl=900,show_spinner=False)
def flood(lat,lon):
 try:
  x=get('https://environment.data.gov.uk/flood-monitoring/id/floods',{'lat':lat,'long':lon,'dist':10},30).get('items',[]);return {'count':len(x)},{'ok':True,'source':'Environment Agency','detail':f'{len(x)} active warnings/alerts returned'}
 except Exception:return None,{'ok':False,'source':'Environment Agency','detail':'Unavailable'}
@st.cache_data(ttl=86400,show_spinner=False)
def routing(a_lat,a_lon,b_lat,b_lon):
 try:
  x=get(f'https://router.project-osrm.org/route/v1/driving/{a_lon},{a_lat};{b_lon},{b_lat}',{'overview':'false'},30)['routes'][0];return (x['distance']/1609.344,x['duration']/60),{'ok':True,'source':'OSRM','detail':'Approximate route without live traffic'}
 except Exception:return None,{'ok':False,'source':'OSRM','detail':'Unavailable'}
def build(loc,radius):
 am,ast=amenities(loc['lat'],loc['lon'],radius);cr,cst=police(loc['lat'],loc['lon']);scores={};avail=[]
 if ast['ok']:
  caps={'Shops':80,'Schools':15,'Parks':10,'Leisure':15,'Healthcare':20,'Social life':70};scores.update({k:min(100,len(am[k])*100/caps[k]) for k in caps});scores['Travel']=min(100,len(am['Rail'])*35+len(am['Bus'])*2);avail+=list(caps)+['Travel']
 if cst['ok']:scores['Lower recorded crime']=max(0,100-len(cr)/8);avail+=['Lower recorded crime']
 return {'scores':scores,'available':avail,'status':[ast,cst]}
def weighted(p,w):
 k=[x for x in THEMES if x in p['available'] and w[x]>0];return None if not k else sum(p['scores'][x]*w[x] for x in k)/sum(w[x] for x in k)
def picker(title,key,default):
 st.subheader(title);q=st.text_input('Address, postcode, village, town, city or county',default,key=key+'q',label_visibility='collapsed');rows=candidates(q) if q else []
 if not rows:st.warning('No location match found.');return None
 i=st.selectbox('Confirm intended location',range(len(rows)),format_func=lambda n:rows[n]['label'],key=key+'s');return rows[i]
st.markdown('''<style>.hero{background:linear-gradient(120deg,#123f52,#0f766e);color:white;padding:25px;border-radius:20px}.card{background:white;padding:20px;border-radius:15px;border:1px solid #dce9e4}.stButton button,.stDownloadButton button{background:#0f766e;color:white}</style>''',unsafe_allow_html=True)
st.markdown('<div class=hero><h1>🏡 MoveWise UK v5.1</h1><p>Personal location-selection consultant with live-source checks.</p></div>',unsafe_allow_html=True)
if 'result51' not in st.session_state:st.session_state.result51=None
with st.sidebar:
 st.header('Priorities');weights={k:st.slider(k,0,10,7 if k in ['Travel','Parks','Healthcare'] else 5,key=k) for k in THEMES};radius=st.select_slider('Local radius',[1000,2000,3000,5000],3000,format_func=lambda x:f'{x/1000:g} km')
c1,c2=st.columns(2)
with c1:a=picker('Current location','a','Marlow, Buckinghamshire')
with c2:b=picker('Possible destination','b','Rickmansworth, Hertfordshire')
with st.expander('Tell MoveWise about the household',expanded=True):
 c1,c2,c3=st.columns(3);age=c1.selectbox('Age/life stage',['Under 25','25–39','40–54','55–64','65–74','75+','Mixed ages']);house=c2.selectbox('Household',['One person','Couple','Family with young children','Family with teenagers','Multi-generational','Other']);work=c3.selectbox('Work status',['Office/site-based','Hybrid','Home-based','Self-employed','Retired','Not working','Mixed household'])
 c1,c2,c3=st.columns(3);cars=c1.selectbox('Car access',['No car','One car','Two or more cars']);mobility=c2.selectbox('Accessibility',['No particular requirement','Prefer level walking','Step-free transport important','Mobility aid/wheelchair important']);schools=c3.selectbox('School requirement',['None','Nursery','Primary','Secondary','Sixth form/college','Several phases'])
 c1,c2=st.columns(2);prop=c1.selectbox('Preferred property',['No preference','Flat','Terraced','Semi-detached','Detached','Bungalow','Rural/smallholding']);budget=c2.number_input('Budget (£)',0,10000000,750000,25000);commute=st.text_input('Regular work/family/care destination');must=st.text_area('Must-haves');avoid=st.text_area('Deal-breakers')
if st.button('Create personalised briefing',type='primary',use_container_width=True) and a and b:
 with st.spinner('Checking live sources…'):
  pa,pb=build(a,radius),build(b,radius);fa,fas=food(a['lat'],a['lon'],radius);fb,fbs=food(b['lat'],b['lon'],radius);fla,flas=flood(a['lat'],a['lon']);flb,flbs=flood(b['lat'],b['lon']);rt,rts=routing(a['lat'],a['lon'],b['lat'],b['lon']);st.session_state.result51={'a':a,'b':b,'pa':pa,'pb':pb,'fa':fa,'fb':fb,'fla':fla,'flb':flb,'statuses':pa['status']+pb['status']+[fas,fbs,flas,flbs,rts],'route':rt,'weights':weights.copy(),'user':{'age':age,'house':house,'work':work,'cars':cars,'mobility':mobility,'schools':schools,'prop':prop,'budget':budget,'commute':commute,'must':must,'avoid':avoid}}
r=st.session_state.result51
if r:
 va,vb=weighted(r['pa'],r['weights']),weighted(r['pb'],r['weights']);common=[k for k in THEMES if k in r['pa']['available'] and k in r['pb']['available']];st.success('Briefing complete. Missing sources are excluded, not shown as zero.')
 if va is None:st.error('Insufficient comparable live evidence for a numerical verdict.')
 else:
  d=vb-va;st.markdown(f'<div class=card><h2>{"Promising candidate" if d>=4 else "Broadly comparable" if d>-4 else "Current location scores more strongly"}</h2><p>Destination <b>{vb:.0f}/100</b>; current location <b>{va:.0f}/100</b>; difference <b>{d:+.0f}</b>.</p><p><b>Household:</b> {html.escape(age)}, {html.escape(house)}, {html.escape(work)}, {html.escape(prop)}, budget £{budget:,.0f}.</p></div>',unsafe_allow_html=True)
 st.subheader('Household-fit prompts')
 if work in ['Office/site-based','Hybrid']:st.write('• Test the actual peak-time commute to '+(commute or 'the regular destination')+'.')
 if age in ['65–74','75+'] or mobility!='No particular requirement':st.write('• Check gradients, step-free transport, GP access and day-to-day walkability.')
 if schools!='None':st.write('• Verify Ofsted, admissions, catchment and available places. Counts alone are insufficient.')
 if cars=='No car':st.write('• Test food shopping, healthcare and evening journeys without a car.')
 c1,c2,c3=st.columns(3);c1.metric('Current','N/A' if va is None else f'{va:.0f}/100');c2.metric('Destination','N/A' if vb is None else f'{vb:.0f}/100');c3.metric('Drive','Unavailable' if not r['route'] else f'{r["route"][0]:.0f} mi · {r["route"][1]/60:.1f} hr')
 st.subheader('Additional live signals');x,y=st.columns(2);x.write('**Food Standards Agency**');x.write(f"Current: {r['fa']['count']} establishments; destination: {r['fb']['count']} establishments." if r['fa'] and r['fb'] else 'FSA data unavailable.');y.write('**Environment Agency live context**');y.write(f"Current: {r['fla']['count']} active alerts; destination: {r['flb']['count']} active alerts." if r['fla'] and r['flb'] else 'Flood-monitoring data unavailable.');y.caption('Not a property-level flood-risk search.')
 if common:
  df=pd.DataFrame({'Theme':common,'Current':[round(r['pa']['scores'][k]) for k in common],'Destination':[round(r['pb']['scores'][k]) for k in common]});st.dataframe(df,hide_index=True,use_container_width=True)
 report=f"<!doctype html><meta charset=utf-8><h1>MoveWise UK v5.1</h1><h2>{html.escape(r['a']['label'])} to {html.escape(r['b']['label'])}</h2><p>Current: {'N/A' if va is None else f'{va:.0f}/100'}; destination: {'N/A' if vb is None else f'{vb:.0f}/100'}.</p><p>Household: {html.escape(str(r['user']))}</p><p>Missing sources were excluded, not scored as zero.</p>";st.download_button('Download briefing',report,'movewise_v5_1_briefing.html','text/html',use_container_width=True)
 with st.expander('Source health',expanded=True):
  for s in r['statuses']:st.markdown(('✅' if s['ok'] else '⚠️')+f" **{s['source']}**: {s['detail']}")
st.caption('MoveWise UK v5.1 · Verify material property decisions independently.')
