import html,urllib.parse,pandas as pd,plotly.graph_objects as go,streamlit as st,folium
from streamlit_folium import st_folium
from services import candidates,profile,route
st.set_page_config(page_title='MoveWise UK v4',page_icon='🏡',layout='wide')
st.markdown('''<style>.stApp{background:#f6faf8}.hero{background:linear-gradient(120deg,#123f52,#0f766e);color:white;padding:26px 30px;border-radius:22px}.card{background:white;padding:20px;border-radius:16px;border:1px solid #dce9e4;margin:10px 0}.verdict{font-size:1.7rem;font-weight:800;color:#0f766e}.stButton button,.stDownloadButton button{background:#0f766e;color:white;border:none}[data-testid=stMetric]{background:white;border:1px solid #dce9e4;padding:10px;border-radius:14px}</style>''',unsafe_allow_html=True)
st.markdown('<div class=hero><h1>🏡 MoveWise UK v4</h1><p>A location-selection consultant: suitability, trade-offs, evidence and next investigations.</p></div>',unsafe_allow_html=True)
THEMES=['Travel','Parks','Shops','Schools','Leisure','Healthcare','Social life','Lower recorded crime']
if 'brief' not in st.session_state:st.session_state.brief=None
with st.sidebar:
 st.header('What matters to you?');weights={k:st.slider(k,0,10,7 if k in ['Travel','Parks','Healthcare'] else 5,key=k) for k in THEMES};radius=st.select_slider('Local radius',[1000,2000,3000,5000],3000,format_func=lambda x:f'{x/1000:g} km')
def pick(title,key,default):
 st.subheader(title);q=st.text_input('Address, postcode, village, town, city or county',default,key=key+'q',label_visibility='collapsed');rows=candidates(q) if q else []
 if not rows:st.warning('No UK match found. Add a county or postcode.');return None
 i=st.selectbox('Confirm the intended location',range(len(rows)),format_func=lambda n:rows[n]['label'],key=key+'s');return rows[i]
def weighted(p,w):
 keys=[k for k in THEMES if k in p['available'] and w[k]>0]
 if not keys:return None
 return sum(p['scores'][k]*w[k] for k in keys)/sum(w[k] for k in keys)
def status_line(s):return ('✅' if s['ok'] else '⚠️')+' **'+s['source']+'**: '+s['detail']
def describe(k,d):
 basis={'Travel':'nearby mapped rail and bus provision','Parks':'nearby mapped parks','Shops':'nearby mapped shops','Schools':'nearby mapped schools, not quality or admissions','Leisure':'nearby mapped leisure facilities','Healthcare':'nearby mapped healthcare facilities','Social life':'nearby mapped cafés, pubs and restaurants','Lower recorded crime':'the volume of returned Police.uk street-level records'}[k]
 if abs(d)<3:return f'{k} looks broadly similar in this dataset, based on {basis}.'
 return f'The destination looks {"stronger" if d>0 else "weaker"} for {k.lower()}, based on {basis}.'
def report(r):
 a,b,pa,pb,w=r['a'],r['b'],r['pa'],r['pb'],r['weights'];common=[k for k in THEMES if k in pa['available'] and k in pb['available']];va,vb=weighted(pa,w),weighted(pb,w);diff={k:pb['scores'][k]-pa['scores'][k] for k in common};rows=''.join(f'<tr><td>{k}</td><td>{pa["scores"][k]:.0f}</td><td>{pb["scores"][k]:.0f}</td><td>{diff[k]:+.0f}</td></tr>' for k in common);status=''.join('<li>'+html.escape(x['source']+': '+x['detail'])+'</li>' for x in pa['status']+pb['status']+[r['route_status']]);summary='Insufficient live evidence to calculate a responsible comparison.' if va is None or vb is None else f'Current {va:.0f}/100; destination {vb:.0f}/100; difference {vb-va:+.0f}.'
 return f'''<!doctype html><meta charset=utf-8><style>body{{font-family:Arial;max-width:950px;margin:40px auto;line-height:1.5;color:#17332d}}h1,h2{{color:#0f766e}}table{{border-collapse:collapse;width:100%}}td,th{{padding:9px;border-bottom:1px solid #ddd;text-align:left}}.note{{padding:15px;background:#fff4d6}}</style><h1>MoveWise UK v4 location-selection briefing</h1><h2>{html.escape(a['label'])} → {html.escape(b['label'])}</h2><p><b>{summary}</b></p><h2>Evidence scorecard</h2><table><tr><th>Theme</th><th>Current</th><th>Destination</th><th>Difference</th></tr>{rows}</table><h2>Source status</h2><ul>{status}</ul><h2>Next investigations</h2><ul><li>Check Area360 profiles for property, deprivation, schools, flood and noise context.</li><li>Use HM Land Registry Price Paid Data for actual local sales.</li><li>Check property-specific flood, planning, broadband, council tax and conveyancing searches.</li><li>Visit at weekday peak, evening and weekend periods.</li></ul><p class=note>Unavailable evidence is excluded, never treated as zero. Scores reflect provision in returned public data, not quality or a guarantee.</p>'''
c1,c2=st.columns(2)
with c1:a=pick('Where you live now','a','Marlow, Buckinghamshire')
with c2:b=pick('Where you are considering','b','Rickmansworth, Hertfordshire')
st.subheader('Your situation')
x,y=st.columns(2);budget=x.number_input('Approximate budget (£)',0,10000000,750000,25000);household=y.selectbox('Household',['Not specified','One person','Couple','Family','Other']);likes=st.text_area('What would make the move worthwhile?',placeholder='Beautiful walks, restaurants, rail, healthcare, culture…');concerns=st.text_area('What would make you regret it?',placeholder='Traffic, aircraft noise, flooding, urban sprawl…')
if st.button('Create my location-selection briefing',type='primary',use_container_width=True) and a and b:
 with st.spinner('Consulting available live data sources…'):
  pa,pb=profile(a,radius),profile(b,radius);rt,rts=route(a,b);st.session_state.brief={'a':a,'b':b,'pa':pa,'pb':pb,'route':rt,'route_status':rts,'weights':weights.copy(),'budget':budget,'household':household,'likes':likes,'concerns':concerns}
r=st.session_state.brief
if r:
 a,b,pa,pb,w=r['a'],r['b'],r['pa'],r['pb'],r['weights'];common=[k for k in THEMES if k in pa['available'] and k in pb['available']];va,vb=weighted(pa,w),weighted(pb,w)
 st.success('Briefing complete. Results are shown here and remain visible in this session.')
 if va is None or vb is None:st.markdown('<div class=card><div class=verdict>Evidence incomplete</div><p>The live sources did not return enough comparable evidence for a responsible verdict. MoveWise has not converted missing data into zeroes.</p></div>',unsafe_allow_html=True)
 else:
  delta=vb-va;label='Strong case to investigate' if delta>=12 else 'Promising candidate' if delta>=5 else 'Broadly comparable' if delta>-5 else 'Trade-offs may outweigh gains'
  st.markdown(f'<div class=card><div class=verdict>{label}</div><h2>Would this location suit you?</h2><p><b>{html.escape(b["label"])}</b> scores <b>{vb:.0f}/100</b> against <b>{va:.0f}/100</b> for the current area, using only evidence successfully returned and the priorities selected.</p><p>{html.escape(r["likes"] or "No personal likes entered.")} Budget context: £{r["budget"]:,.0f}; household: {html.escape(r["household"])}.</p></div>',unsafe_allow_html=True)
  dif={k:pb['scores'][k]-pa['scores'][k] for k in common};order=sorted(common,key=lambda k:dif[k],reverse=True);g,t=st.columns(2)
  with g:
   st.subheader('Best reasons to investigate')
   for k in order[:3]:st.write('✅ **'+k+f' ({dif[k]:+.0f})**  \n'+describe(k,dif[k]))
  with t:
   st.subheader('Biggest cautions')
   for k in order[-3:]:st.write('⚠️ **'+k+f' ({dif[k]:+.0f})**  \n'+describe(k,dif[k]))
 m1,m2,m3=st.columns(3);m1.metric('Current indication','N/A' if va is None else f'{va:.0f}/100');m2.metric('Destination indication','N/A' if vb is None else f'{vb:.0f}/100');m3.metric('Approx. drive','Unavailable' if not r['route'] else f'{r["route"][0]:.0f} mi · {r["route"][1]/60:.1f} hr')
 st.download_button('⬇ Download full consultant briefing',report(r),'movewise_v4_briefing.html','text/html',type='primary',use_container_width=True)
 with st.expander('Evidence, chart and map',expanded=False):
  if common:
   df=pd.DataFrame({'Theme':common,'Current':[round(pa['scores'][k]) for k in common],'Destination':[round(pb['scores'][k]) for k in common]});st.dataframe(df,hide_index=True,use_container_width=True)
   fig=go.Figure();fig.add_trace(go.Bar(name='Current',x=common,y=[pa['scores'][k] for k in common]));fig.add_trace(go.Bar(name='Destination',x=common,y=[pb['scores'][k] for k in common]));fig.update_layout(barmode='group',yaxis_range=[0,100]);st.plotly_chart(fig,use_container_width=True)
  mapx=folium.Map(location=[(a['lat']+b['lat'])/2,(a['lon']+b['lon'])/2],zoom_start=9);folium.Marker([a['lat'],a['lon']],tooltip='Current',icon=folium.Icon(color='blue')).add_to(mapx);folium.Marker([b['lat'],b['lon']],tooltip='Destination',icon=folium.Icon(color='orange')).add_to(mapx);st_folium(mapx,height=400,use_container_width=True)
 with st.expander('Data-source health and provenance',expanded=True):
  st.markdown('#### Current location');[st.markdown(status_line(s)) for s in pa['status']];st.markdown('#### Destination');[st.markdown(status_line(s)) for s in pb['status']];st.markdown(status_line(r['route_status']));st.caption('A failed source is excluded from scoring. It is never recorded as a genuine zero.')
 st.subheader('Independent research desk')
 q=urllib.parse.quote_plus((b.get('label') or '').split(',')[0]);c1,c2,c3=st.columns(3);c1.link_button('Open Area360','https://area360.uk/',use_container_width=True);c2.link_button('HM Land Registry data','https://landregistry.data.gov.uk/',use_container_width=True);c3.link_button('UK public data catalogue','https://www.data.gov.uk/',use_container_width=True)
 st.warning('Area360 is provided as an independent research hand-off. V4 does not scrape Area360 or imply access to a public Area360 API.')
st.caption('MoveWise UK v4 · Missing data is excluded rather than converted into zero. Verify all important decisions independently.')
