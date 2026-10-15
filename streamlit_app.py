import html,urllib.parse,pandas as pd,plotly.graph_objects as go,streamlit as st,folium
from streamlit_folium import st_folium
from services import candidates,profile,route,food_hygiene,flood_context
st.set_page_config(page_title='MoveWise UK v5',page_icon='🏡',layout='wide')
st.markdown('''<style>.stApp{background:#f6faf8}.hero{background:linear-gradient(120deg,#123f52,#0f766e);color:white;padding:26px 30px;border-radius:22px}.card{background:white;padding:20px;border-radius:16px;border:1px solid #dce9e4;margin:10px 0}.verdict{font-size:1.7rem;font-weight:800;color:#0f766e}.stButton button,.stDownloadButton button{background:#0f766e;color:white;border:none}[data-testid=stMetric]{background:white;border:1px solid #dce9e4;padding:10px;border-radius:14px}</style>''',unsafe_allow_html=True)
st.markdown('<div class=hero><h1>🏡 MoveWise UK v5</h1><p>A more personal location-selection consultant, using live evidence where available.</p></div>',unsafe_allow_html=True)
THEMES=['Travel','Parks','Shops','Schools','Leisure','Healthcare','Social life','Lower recorded crime']
if 'brief5' not in st.session_state:st.session_state.brief5=None
with st.sidebar:
 st.header('Location priorities');weights={k:st.slider(k,0,10,7 if k in ['Travel','Parks','Healthcare'] else 5,key=k) for k in THEMES};radius=st.select_slider('Local radius',[1000,2000,3000,5000],3000,format_func=lambda x:f'{x/1000:g} km')
def pick(title,key,default):
 st.subheader(title);q=st.text_input('Address, postcode, village, town, city or county',default,key=key+'q',label_visibility='collapsed');rows=candidates(q) if q else []
 if not rows:st.warning('No UK match found. Add a county or postcode.');return None
 i=st.selectbox('Confirm intended location',range(len(rows)),format_func=lambda n:rows[n]['label'],key=key+'s');return rows[i]
def weighted(p,w):
 keys=[k for k in THEMES if k in p['available'] and w[k]>0];return None if not keys else sum(p['scores'][k]*w[k] for k in keys)/sum(w[k] for k in keys)
def status(s):return ('✅' if s['ok'] else '⚠️')+f" **{s['source']}**: {s['detail']}"
def profile_text(u):
 bits=[f"Age/life stage: {u['age']}",f"Household: {u['household']}",f"Work: {u['work']}",f"Home-working: {u['homework']}",f"Cars: {u['cars']}",f"Mobility/access: {u['mobility']}",f"Children/schools: {u['children']}",f"Property: {u['property']}",f"Budget: £{u['budget']:,.0f}"]
 return '. '.join(bits)+'.'
def fit_notes(u):
 out=[]
 if u['work'] not in ['Retired','Not working'] or u['homework']!='Never':out.append('Work pattern makes broadband quality and a tested peak-time commute material.')
 if u['age'] in ['65–74','75+'] or u['mobility']!='No particular requirement':out.append('Healthcare proximity, walkability, gradients and step-free transport deserve extra on-the-ground checks.')
 if u['children']!='No school requirement':out.append('School counts are not enough: check phase, Ofsted report, admissions, catchment and available places.')
 if u['cars']=='No car':out.append('Prioritise all-day public transport, grocery access and healthcare journeys rather than road distance.')
 if u['property'] in ['Flat','Bungalow']:out.append('Confirm local stock, service charges or scarcity before relying on the area-level verdict.')
 return out or ['No dominant household constraint was selected; the briefing follows the priority sliders and free-text preferences.']
def make_report(r):
 a,b,pa,pb,w,u=r['a'],r['b'],r['pa'],r['pb'],r['weights'],r['user'];common=[k for k in THEMES if k in pa['available'] and k in pb['available']];va,vb=weighted(pa,w),weighted(pb,w);rows=''.join(f'<tr><td>{k}</td><td>{pa["scores"][k]:.0f}</td><td>{pb["scores"][k]:.0f}</td><td>{pb["scores"][k]-pa["scores"][k]:+.0f}</td></tr>' for k in common);sources=pa['status']+pb['status']+[r['route_status'],r['fa_status'],r['fb_status'],r['flooda_status'],r['floodb_status']];summary='Insufficient comparable live evidence' if va is None or vb is None else f'Current {va:.0f}/100; destination {vb:.0f}/100; difference {vb-va:+.0f}'
 return f'''<!doctype html><meta charset=utf-8><style>body{{font-family:Arial;max-width:950px;margin:40px auto;line-height:1.5;color:#17332d}}h1,h2{{color:#0f766e}}table{{border-collapse:collapse;width:100%}}td,th{{padding:9px;border-bottom:1px solid #ddd;text-align:left}}.note{{background:#fff4d6;padding:14px}}</style><h1>MoveWise UK v5 briefing</h1><h2>{html.escape(a['label'])} → {html.escape(b['label'])}</h2><p><b>{summary}</b></p><h2>Household profile</h2><p>{html.escape(profile_text(u))}</p><ul>{''.join('<li>'+html.escape(x)+'</li>' for x in fit_notes(u))}</ul><h2>Evidence scorecard</h2><table><tr><th>Theme</th><th>Current</th><th>Destination</th><th>Difference</th></tr>{rows}</table><h2>Source health</h2><ul>{''.join('<li>'+html.escape(s['source']+': '+s['detail'])+'</li>' for s in sources)}</ul><p class=note>Missing data is excluded, not scored as zero. Food-hygiene counts indicate establishments returned, not overall restaurant quality. Environment Agency information is real-time monitoring context, not a property flood-risk search.</p>'''
a1,a2=st.columns(2)
with a1:a=pick('Current location','a','Marlow, Buckinghamshire')
with a2:b=pick('Possible destination','b','Rickmansworth, Hertfordshire')
with st.expander('1. Tell MoveWise about the household',expanded=True):
 c1,c2,c3=st.columns(3);age=c1.selectbox('Age or life stage',['Under 25','25–39','40–54','55–64','65–74','75+','Mixed adult ages']);household=c2.selectbox('Household unit',['One person','Couple','Family with young children','Family with teenagers','Multi-generational','Shared household','Other']);work=c3.selectbox('Work status',['Office/site-based','Hybrid','Home-based','Self-employed','Retired','Not working','Mixed household'])
 c1,c2,c3=st.columns(3);homework=c1.selectbox('Home working',['Never','Occasionally','2–3 days a week','Most/all days','Mixed household']);cars=c2.selectbox('Car access',['No car','One car','Two or more cars']);mobility=c3.selectbox('Mobility/accessibility',['No particular requirement','Prefer level walking','Step-free transport important','Mobility aid/wheelchair access important'])
 c1,c2,c3=st.columns(3);children=c1.selectbox('School requirement',['No school requirement','Nursery/early years','Primary','Secondary','Sixth form/college','Several phases']);property_type=c2.selectbox('Preferred property',['No preference','Flat','Terraced','Semi-detached','Detached','Bungalow','Rural/smallholding']);budget=c3.number_input('Approximate budget (£)',0,10000000,750000,25000)
 commute=st.text_input('Regular work, family or care destination',placeholder='e.g. Paddington twice weekly, Heathrow monthly, family in Oxford');must=st.text_area('Must-haves',placeholder='Walkable centre, river walks, GP, station, tennis, cafés…');avoid=st.text_area('Deal-breakers',placeholder='Aircraft noise, steep hills, flood concern, isolation, nightlife…')
optional=st.expander('2. Optional property-data enhancement',expanded=False)
with optional:
 st.info('V5 uses free live sources without keys. A future connector can use a paid Homedata API key for property-level sold prices, EPC, broadband, schools, planning and flood risk. Do not paste a valuable key into a public app unless it is stored as a Streamlit secret.');st.text_input('Optional Homedata API key (not used in this release)',type='password',disabled=True)
if st.button('Create personalised location briefing',type='primary',use_container_width=True) and a and b:
 user={'age':age,'household':household,'work':work,'homework':homework,'cars':cars,'mobility':mobility,'children':children,'property':property_type,'budget':budget,'commute':commute,'must':must,'avoid':avoid}
 with st.spinner('Consulting live map, crime, food hygiene, flood-monitoring and routing sources…'):
  pa,pb=profile(a,radius),profile(b,radius);rt,rts=route(a,b);fa,fas=food_hygiene(a['lat'],a['lon'],radius/1000);fb,fbs=food_hygiene(b['lat'],b['lon'],radius/1000);fla,flas=flood_context(a['lat'],a['lon']);flb,flbs=flood_context(b['lat'],b['lon']);st.session_state.brief5={'a':a,'b':b,'pa':pa,'pb':pb,'route':rt,'route_status':rts,'fa':fa,'fb':fb,'fa_status':fas,'fb_status':fbs,'flooda':fla,'floodb':flb,'flooda_status':flas,'floodb_status':flbs,'weights':weights.copy(),'user':user}
r=st.session_state.brief5
if r:
 a,b,pa,pb,w,u=r['a'],r['b'],r['pa'],r['pb'],r['weights'],r['user'];va,vb=weighted(pa,w),weighted(pb,w);common=[k for k in THEMES if k in pa['available'] and k in pb['available']]
 st.success('Personalised briefing complete. Missing sources have not been converted into zeroes.')
 if va is None or vb is None:st.markdown('<div class=card><div class=verdict>Evidence incomplete</div><p>There is not enough comparable live evidence for a numerical verdict. The household-fit and source results remain useful.</p></div>',unsafe_allow_html=True)
 else:
  d=vb-va;label='Strong candidate for further investigation' if d>=10 else 'Promising candidate' if d>=4 else 'Broadly comparable' if d>-4 else 'Current location remains stronger on selected evidence';st.markdown(f'<div class=card><div class=verdict>{label}</div><h2>Location consultant summary</h2><p>The destination scores <b>{vb:.0f}/100</b>, versus <b>{va:.0f}/100</b> for the current location, using only sources that returned comparable data.</p><p><b>Household context:</b> {html.escape(profile_text(u))}</p></div>',unsafe_allow_html=True)
 st.subheader('What the household profile changes');[st.write('• '+x) for x in fit_notes(u)]
 c1,c2,c3=st.columns(3);c1.metric('Current','N/A' if va is None else f'{va:.0f}/100');c2.metric('Destination','N/A' if vb is None else f'{vb:.0f}/100');c3.metric('Approx. drive','Unavailable' if not r['route'] else f'{r["route"][0]:.0f} mi · {r["route"][1]/60:.1f} hr')
 st.subheader('Additional live signals')
 x,y=st.columns(2)
 with x:
  st.markdown('#### Food and eating-out footprint')
  for name,data in [('Current',r['fa']),('Destination',r['fb'])]:st.write(f'**{name}:** unavailable' if not data else f"**{name}:** {data['count']} establishments returned; {data['high']} had numeric ratings of 4 or 5.")
 with y:
  st.markdown('#### Real-time flood-monitoring context')
  for name,data in [('Current',r['flooda']),('Destination',r['floodb'])]:st.write(f'**{name}:** unavailable' if not data else f"**{name}:** {data['active_warnings']} active warnings/alerts returned by the nearby query.")
  st.caption('This is not property-level flood risk. Check the official long-term flood maps and conveyancing searches.')
 st.download_button('⬇ Download V5 consultant briefing',make_report(r),'movewise_v5_briefing.html','text/html',type='primary',use_container_width=True)
 with st.expander('Evidence scorecard, chart and map'):
  if common:
   df=pd.DataFrame({'Theme':common,'Current':[round(pa['scores'][k]) for k in common],'Destination':[round(pb['scores'][k]) for k in common]});st.dataframe(df,hide_index=True,use_container_width=True);fig=go.Figure();fig.add_bar(name='Current',x=common,y=[pa['scores'][k] for k in common]);fig.add_bar(name='Destination',x=common,y=[pb['scores'][k] for k in common]);fig.update_layout(barmode='group',yaxis_range=[0,100]);st.plotly_chart(fig,use_container_width=True)
  m=folium.Map(location=[(a['lat']+b['lat'])/2,(a['lon']+b['lon'])/2],zoom_start=9);folium.Marker([a['lat'],a['lon']],tooltip='Current').add_to(m);folium.Marker([b['lat'],b['lon']],tooltip='Destination').add_to(m);st_folium(m,height=400,use_container_width=True)
 with st.expander('Source health and provenance',expanded=True):
  for s in pa['status']+pb['status']+[r['route_status'],r['fa_status'],r['fb_status'],r['flooda_status'],r['floodb_status']]:st.markdown(status(s))
 st.subheader('Deeper research')
 c1,c2,c3,c4=st.columns(4);c1.link_button('Area360','https://area360.uk/',use_container_width=True);c2.link_button('AreaChecker','https://areachecker.co.uk/',use_container_width=True);c3.link_button('NestScope','https://www.nestscope.uk/',use_container_width=True);c4.link_button('Land Registry','https://landregistry.data.gov.uk/',use_container_width=True)
st.caption('MoveWise UK v5 · Free public APIs can be incomplete or unavailable. Verify material decisions independently.')
