import html,pandas as pd,plotly.graph_objects as go,streamlit as st,folium
from streamlit_folium import st_folium
from data_services import candidates,profile,routing
st.set_page_config(page_title='MoveWise UK v3',page_icon='🏡',layout='wide')
st.markdown('''<style>.stApp{background:#f7faf9}.hero{padding:24px 30px;border-radius:22px;background:linear-gradient(120deg,#164e63,#0f766e);color:white}.hero h1{margin:0}.result{padding:22px;border-radius:18px;background:white;border-left:8px solid #0f766e;box-shadow:0 3px 15px #00000012;margin:12px 0}.verdict{font-size:1.55rem;font-weight:750;color:#115e59}.stButton button,.stDownloadButton button{background:#0f766e;color:white;border:none}[data-testid=stMetric]{background:white;border:1px solid #d9e7e2;padding:10px;border-radius:14px}</style>''',unsafe_allow_html=True)
st.markdown('<div class="hero"><h1>🏡 MoveWise UK v3</h1><p>Your relocation summary first, with evidence and a downloadable report beneath it.</p></div>',unsafe_allow_html=True)
THEMES=['Travel','Parks','Shops','Schools','Leisure','Healthcare','Social life','Lower recorded crime']
if 'result' not in st.session_state:st.session_state.result=None
with st.sidebar:
 mode=st.radio('Mode',['Compare two areas','Relocation adviser','Area explorer']);st.subheader('Your priorities');weights={k:st.slider(k,0,10,7 if k in ['Travel','Parks','Shops'] else 5,key=k) for k in THEMES};radius=st.select_slider('Nearby radius',[1000,2000,3000,5000],3000,format_func=lambda n:f'{n/1000:g} km')
def pick(title,key,default=''):
 st.markdown('#### '+title);q=st.text_input('Address, postcode, village, town, city or county',default,key=key+'q',label_visibility='collapsed')
 if not q:return None
 rows=candidates(q)
 if not rows:st.warning('No UK match found. Add a county or postcode.');return None
 i=st.selectbox('Choose the intended match',range(len(rows)),format_func=lambda n:rows[n]['label'],key=key+'s');st.caption('Recognised as: '+rows[i]['kind']);return rows[i]
def val(p,w):
 d=sum(w.values()) or 1;return sum(p['scores'][k]*w[k] for k in THEMES)/d
def explanation(k,d):
 direction='stronger' if d>0 else 'weaker';basis={'Travel':'mapped rail stations and bus stops','Parks':'mapped parks','Shops':'mapped shops','Schools':'mapped schools, not quality or admissions','Leisure':'mapped sports and leisure facilities','Healthcare':'mapped healthcare facilities','Social life':'mapped cafés, pubs and restaurants','Lower recorded crime':'the returned Police.uk street-level record volume'}[k]
 return f'The destination looks {direction} on {k.lower()}, based on {basis} within the selected radius.'
def stars(delta):
 a=abs(delta)
 if a>=20:return '★★★★★','Strong difference'
 if a>=12:return '★★★★☆','Clear difference'
 if a>=5:return '★★★☆☆','Moderate difference'
 return '★★☆☆☆','Broadly similar'
def make_report(r):
 a,b,pa,pb,w,context=r['a'],r['b'],r['pa'],r['pb'],r['weights'],r['context'];va,vb=val(pa,w),val(pb,w);dif={k:pb['scores'][k]-pa['scores'][k] for k in THEMES};order=sorted(THEMES,key=lambda k:dif[k],reverse=True);journey=r['route'];rows=''.join(f'<tr><td>{k}</td><td>{pa["scores"][k]:.0f}</td><td>{pb["scores"][k]:.0f}</td><td>{dif[k]:+.0f}</td></tr>' for k in THEMES);gain=''.join(f'<li><b>{k}</b>: {explanation(k,dif[k])}</li>' for k in order[:3]);trade=''.join(f'<li><b>{k}</b>: {explanation(k,dif[k])}</li>' for k in order[-3:]);drive='Unavailable' if not journey else f'{journey[0]:.0f} miles, about {journey[1]/60:.1f} hours without live traffic';ctx=f'<h2>Personal brief</h2><p>{html.escape(context)}</p>' if context else ''
 return f'''<!doctype html><meta charset=utf-8><title>MoveWise UK v3 report</title><style>body{{font-family:Arial;max-width:920px;margin:40px auto;color:#17332d;line-height:1.5}}h1,h2{{color:#0f766e}}.hero{{background:#eaf6f2;padding:20px;border-radius:14px}}table{{border-collapse:collapse;width:100%}}th,td{{padding:9px;border-bottom:1px solid #ddd;text-align:left}}.note{{background:#fff5dd;padding:14px}}</style><h1>MoveWise UK v3 relocation report</h1><div class=hero><h2>{html.escape(a['label'])} to {html.escape(b['label'])}</h2><p><b>Weighted indications:</b> {va:.0f}/100 and {vb:.0f}/100. Difference {vb-va:+.0f}.</p><p><b>Approximate drive:</b> {drive}</p></div>{ctx}<h2>Likely gains</h2><ul>{gain}</ul><h2>Trade-offs to investigate</h2><ul>{trade}</ul><h2>Evidence scorecard</h2><table><tr><th>Theme</th><th>Current</th><th>Destination</th><th>Difference</th></tr>{rows}</table><h2>Due diligence</h2><ul><li>Visit at different times and test the real commute.</li><li>Check school quality, admissions and catchments directly.</li><li>Obtain property-specific flood, drainage, ground and environmental searches.</li><li>Check exact-address broadband, mobile coverage, planning and Local Plan proposals.</li><li>Compare council tax, parking, insurance, energy and maintenance costs.</li></ul><p class=note>Scores indicate nearby mapped provision, not quality. Public data may be incomplete. This is an orientation report, not professional property advice.</p>'''
def render(r):
 a,b,pa,pb,w,context=r['a'],r['b'],r['pa'],r['pb'],r['weights'],r['context'];va,vb=val(pa,w),val(pb,w);delta=vb-va;dif={k:pb['scores'][k]-pa['scores'][k] for k in THEMES};order=sorted(THEMES,key=lambda k:dif[k],reverse=True);symbol,label=stars(delta);winner='destination' if delta>3 else 'current area' if delta<-3 else 'neither area decisively'
 st.success('Analysis complete. Your results are shown below and remain on screen until you run another comparison.')
 st.markdown('<div id="results"></div>',unsafe_allow_html=True)
 st.markdown(f'<div class="result"><div class="verdict">{label}: {symbol}</div><h2>Executive summary</h2><p><b>{html.escape(b["label"])}</b> scores <b>{abs(delta):.0f} points {"higher" if delta>=0 else "lower"}</b> than the current area for the priorities selected. The weighted evidence favours <b>{winner}</b>.</p><p>This is a directional comparison of nearby mapped provision and returned public data, not a judgement on individual properties or neighbourhood quality.</p></div>',unsafe_allow_html=True)
 c=st.columns(3);c[0].metric('Current area',f'{va:.0f}/100');c[1].metric('Destination',f'{vb:.0f}/100',f'{delta:+.0f}');c[2].metric('Approx. drive','Unavailable' if not r['route'] else f'{r["route"][0]:.0f} mi · {r["route"][1]/60:.1f} hr')
 x,y=st.columns(2)
 with x:
  st.subheader('Top potential gains')
  for k in order[:3]:st.markdown(f'**✓ {k} ({dif[k]:+.0f})**  \n{explanation(k,dif[k])}')
 with y:
  st.subheader('Main trade-offs')
  for k in order[-3:]:st.markdown(f'**⚠ {k} ({dif[k]:+.0f})**  \n{explanation(k,dif[k])}')
 if context:st.info('Personal brief: '+context)
 report=make_report(r);st.download_button('⬇ Download full relocation report',report,'movewise_v3_report.html','text/html',type='primary',use_container_width=True)
 with st.expander('View charts, scorecard and map',expanded=False):
  fig=go.Figure()
  for p,n,cx in [(pa,'Current','#2563eb'),(pb,'Destination','#f97316')]:fig.add_trace(go.Scatterpolar(r=[p['scores'][k] for k in THEMES]+[p['scores'][THEMES[0]]],theta=THEMES+[THEMES[0]],fill='toself',name=n,line_color=cx))
  fig.update_layout(polar=dict(radialaxis=dict(range=[0,100],visible=True)),height=450,margin=dict(t=30,b=30));st.plotly_chart(fig,use_container_width=True)
  st.dataframe(pd.DataFrame({'Theme':THEMES,'Current':[round(pa['scores'][k]) for k in THEMES],'Destination':[round(pb['scores'][k]) for k in THEMES],'Difference':[round(dif[k]) for k in THEMES]}),hide_index=True,use_container_width=True)
  m=folium.Map(location=[(a['lat']+b['lat'])/2,(a['lon']+b['lon'])/2],zoom_start=9);folium.Marker([a['lat'],a['lon']],tooltip='Current',icon=folium.Icon(color='blue')).add_to(m);folium.Marker([b['lat'],b['lon']],tooltip='Destination',icon=folium.Icon(color='orange')).add_to(m);st_folium(m,height=420,use_container_width=True)
 for warning in pa['warnings']+pb['warnings']:st.warning(warning)
if mode in ['Compare two areas','Relocation adviser']:
 c1,c2=st.columns(2)
 with c1:a=pick('Current area','a','Marlow, Buckinghamshire')
 with c2:b=pick('Possible destination','b','Rickmansworth, Hertfordshire' if mode=='Compare two areas' else '')
 context=''
 if mode=='Relocation adviser':
  c1,c2=st.columns(2);budget=c1.number_input('Approximate budget (£)',0,10000000,750000,25000);household=c2.selectbox('Household',['Not specified','One person','Couple','Family','Other']);likes=st.text_area('Things you value');avoid=st.text_area('Things to avoid');context=f'Household: {household}. Budget: £{budget:,.0f}. Values: {likes or "not stated"}. Avoid: {avoid or "not stated"}.'
 if st.button('Build and show briefing',type='primary',use_container_width=True) and a and b:
  with st.spinner('Building the visible summary and full report…'):st.session_state.result={'a':a,'b':b,'pa':profile(a,radius),'pb':profile(b,radius),'weights':weights.copy(),'context':context,'route':routing(a,b),'mode':mode}
 if st.session_state.result and st.session_state.result.get('mode')==mode:render(st.session_state.result)
else:
 st.info('Enter up to four candidate areas, one per line. Results will appear immediately below the button.');raw=st.text_area('Candidate areas','Henley-on-Thames\nRickmansworth\nGuildford')
 if st.button('Build and show shortlist',type='primary',use_container_width=True):
  results=[]
  with st.spinner('Comparing shortlist…'):
   for name in [x.strip() for x in raw.splitlines() if x.strip()][:4]:
    c=candidates(name,1)
    if c:
     p=profile(c[0],radius);results.append({'Area':c[0]['label'],'Indication':round(val(p,weights)),**{k:round(p['scores'][k]) for k in THEMES}})
  st.session_state.shortlist=results
 if st.session_state.get('shortlist'):
  st.success('Shortlist complete. Results are shown below.');df=pd.DataFrame(st.session_state.shortlist).sort_values('Indication',ascending=False);st.subheader('Priority-weighted shortlist');st.dataframe(df,hide_index=True,use_container_width=True);st.download_button('⬇ Download shortlist CSV',df.to_csv(index=False),'movewise_v3_shortlist.csv','text/csv',use_container_width=True)
st.divider();st.caption('MoveWise UK v3 · Public data may be incomplete. Scores are orientation aids, not professional property advice.')
