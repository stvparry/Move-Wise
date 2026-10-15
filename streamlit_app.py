import html,pandas as pd,plotly.graph_objects as go,streamlit as st,folium
from streamlit_folium import st_folium
from data_services import candidates,profile,routing
st.set_page_config(page_title="MoveWise UK v2",page_icon="🏡",layout="wide")
st.markdown("""<style>.stApp{background:#f7faf9}.hero{padding:24px 30px;border-radius:22px;background:linear-gradient(120deg,#164e63,#0f766e);color:white}.hero h1{margin:0}[data-testid=stMetric]{background:white;border:1px solid #d9e7e2;padding:10px;border-radius:14px}.stButton button,.stDownloadButton button{background:#0f766e;color:white;border:none}</style>""",unsafe_allow_html=True)
st.markdown('<div class="hero"><h1>🏡 MoveWise UK v2</h1><p>Compare areas, build a personal relocation briefing, or explore a shortlist.</p></div>',unsafe_allow_html=True)
THEMES=['Travel','Parks','Shops','Schools','Leisure','Healthcare','Social life','Lower recorded crime']
with st.sidebar:
 mode=st.radio('Mode',['Compare two areas','Relocation adviser','Area explorer']);st.subheader('Your priorities');weights={k:st.slider(k,0,10,7 if k in ['Travel','Parks','Shops'] else 5,key=k) for k in THEMES};radius=st.select_slider('Nearby radius',[1000,2000,3000,5000],3000,format_func=lambda n:f'{n/1000:g} km')
def pick(title,key,default=''):
 st.markdown('#### '+title);q=st.text_input('Address, postcode, village, town, city or county',default,key=key+'q',label_visibility='collapsed')
 if not q:return None
 rows=candidates(q)
 if not rows:st.warning('No UK match found. Try adding a county or postcode.');return None
 i=st.selectbox('Choose the intended match',range(len(rows)),format_func=lambda n:rows[n]['label'],key=key+'s');st.caption('Recognised as: '+rows[i]['kind']);return rows[i]
def value(p):
 d=sum(weights.values()) or 1;return sum(p['scores'][k]*weights[k] for k in THEMES)/d
def show(a,b,pa,pb,context=''):
 va,vb=value(pa),value(pb);r=routing(a,b);cols=st.columns(3);cols[0].metric('Current area',f'{va:.0f}/100');cols[1].metric('Destination',f'{vb:.0f}/100',f'{vb-va:+.0f}');cols[2].metric('Approx. drive','Unavailable' if not r else f'{r[0]:.0f} mi · {r[1]/60:.1f} hr')
 for w in pa['warnings']+pb['warnings']:st.warning(w)
 fig=go.Figure();cats=THEMES
 for p,n,c in [(pa,'Current','#2563eb'),(pb,'Destination','#f97316')]:fig.add_trace(go.Scatterpolar(r=[p['scores'][x] for x in cats]+[p['scores'][cats[0]]],theta=cats+[cats[0]],fill='toself',name=n,line_color=c))
 fig.update_layout(polar=dict(radialaxis=dict(range=[0,100],visible=True)),height=450,margin=dict(t=30,b=30));st.plotly_chart(fig,use_container_width=True)
 dif={k:pb['scores'][k]-pa['scores'][k] for k in cats};order=sorted(cats,key=lambda k:dif[k],reverse=True);x,y=st.columns(2);x.success('**Likely gains**\n\n'+'\n\n'.join(f'• {k}: {dif[k]:+.0f}' for k in order[:3]));y.info('**Trade-offs to investigate**\n\n'+'\n\n'.join(f'• {k}: {dif[k]:+.0f}' for k in order[-3:]))
 if context:st.subheader('Personal brief');st.write(context)
 st.dataframe(pd.DataFrame({'Theme':cats,'Current':[round(pa['scores'][k]) for k in cats],'Destination':[round(pb['scores'][k]) for k in cats]}),hide_index=True,use_container_width=True)
 m=folium.Map(location=[(a['lat']+b['lat'])/2,(a['lon']+b['lon'])/2],zoom_start=9);folium.Marker([a['lat'],a['lon']],tooltip='Current',icon=folium.Icon(color='blue')).add_to(m);folium.Marker([b['lat'],b['lon']],tooltip='Destination',icon=folium.Icon(color='orange')).add_to(m);st_folium(m,height=420,use_container_width=True)
 checks=['Test the real commute at peak time and late evening.','Check school reports, admissions and catchments directly.','Obtain property-specific flood, drainage, ground, radon and environmental searches.','Check exact-address broadband and mobile coverage.','Review nearby planning applications and the council Local Plan.','Visit on a weekday, evening and weekend.','Compare council tax, parking, insurance, energy and maintenance costs.'];st.subheader('Questions to investigate');st.write('\n'.join('- '+q for q in checks))
 rows=''.join(f'<tr><td>{k}</td><td>{pa["scores"][k]:.0f}</td><td>{pb["scores"][k]:.0f}</td></tr>' for k in cats);report=f"<!doctype html><meta charset=utf-8><style>body{{font-family:Arial;max-width:900px;margin:40px auto}}td,th{{padding:9px;border-bottom:1px solid #ddd}}</style><h1>MoveWise UK v2</h1><h2>{html.escape(a['label'])} to {html.escape(b['label'])}</h2><p>Weighted indications: {va:.0f}/100 and {vb:.0f}/100.</p><table><tr><th>Theme</th><th>Current</th><th>Destination</th></tr>{rows}</table><h2>Checks</h2><ul>{''.join('<li>'+q+'</li>' for q in checks)}</ul><p>Mapped provision is not a quality rating. Verify important decisions independently.</p>";st.download_button('Download relocation report',report,'movewise_v2_report.html','text/html',use_container_width=True)
if mode in ['Compare two areas','Relocation adviser']:
 c1,c2=st.columns(2)
 with c1:a=pick('Current area','a','Marlow, Buckinghamshire')
 with c2:b=pick('Possible destination','b','Rickmansworth, Hertfordshire' if mode=='Compare two areas' else '')
 context=''
 if mode=='Relocation adviser':
  c1,c2=st.columns(2);budget=c1.number_input('Approximate budget (£)',0,10000000,750000,25000);household=c2.selectbox('Household',['Not specified','One person','Couple','Family','Other']);likes=st.text_area('Things you value',placeholder='Walking, cafés, theatre, rail access…');avoid=st.text_area('Things to avoid',placeholder='Heavy traffic, aircraft noise, urban sprawl…');context=f'Household: {household}. Budget: £{budget:,.0f}. Values: {likes or "not stated"}. Avoid: {avoid or "not stated"}.'
 if st.button('Build briefing',type='primary',use_container_width=True) and a and b:
  with st.spinner('Gathering evidence with fallback services…'):show(a,b,profile(a,radius),profile(b,radius),context)
else:
 st.info('Enter up to four places you are considering. V2 compares your shortlist rather than inventing destinations.');raw=st.text_area('Candidate areas, one per line','Henley-on-Thames\nRickmansworth\nGuildford')
 if st.button('Explore shortlist',type='primary',use_container_width=True):
  results=[]
  with st.spinner('Resolving and comparing locations…'):
   for name in [x.strip() for x in raw.splitlines() if x.strip()][:4]:
    c=candidates(name,1)
    if c:
     p=profile(c[0],radius);results.append((c[0],p,value(p)))
  if results:
   results.sort(key=lambda x:x[2],reverse=True);st.dataframe(pd.DataFrame([{'Area':x[0]['label'],'Indication':round(x[2]),**{k:round(x[1]['scores'][k]) for k in THEMES}} for x in results]),hide_index=True,use_container_width=True);st.caption('Ranks only the areas entered, using available mapped evidence and your sliders.')
  else:st.error('None of the candidate areas could be resolved.')
st.divider();st.caption('Public data may be incomplete or temporarily unavailable. Scores are orientation aids, not professional property advice.')
