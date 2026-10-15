import math, re, html, time
from collections import Counter
import requests
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="MoveWise UK", page_icon="🏡", layout="wide")
UA={"User-Agent":"MoveWise-UK-demo/1.0 educational Streamlit app"}
TIMEOUT=20

st.markdown("""<style>
.stApp{background:linear-gradient(180deg,#f4faf7 0,#ffffff 35%)}
.hero{padding:1.2rem 1.5rem;border-radius:20px;background:linear-gradient(120deg,#164e63,#0f766e);color:white;margin-bottom:1rem}
.hero h1{margin:0;font-size:2.25rem}.hero p{margin:.35rem 0 0;opacity:.92}
[data-testid="stMetric"]{background:#fff;border:1px solid #dce9e4;padding:12px;border-radius:14px}
.small{color:#53645f;font-size:.9rem}.winner{color:#0f766e;font-weight:700}
</style>""",unsafe_allow_html=True)
st.markdown('<div class="hero"><h1>🏡 MoveWise UK</h1><p>Compare where you live with somewhere you might move to, using your priorities.</p></div>',unsafe_allow_html=True)

@st.cache_data(ttl=86400, show_spinner=False)
def geocode(q):
    q=q.strip()
    pc=re.search(r"\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b",q.upper())
    if pc:
        r=requests.get("https://api.postcodes.io/postcodes/"+pc.group(1).replace(" ",""),timeout=TIMEOUT).json()
        if r.get("status")==200:
            x=r["result"]
            return {"label":x["postcode"],"lat":x["latitude"],"lon":x["longitude"],"admin":x.get("admin_district"),"region":x.get("region"),"country":x.get("country"),"parliamentary":x.get("parliamentary_constituency"),"source":"Postcodes.io"}
    r=requests.get("https://nominatim.openstreetmap.org/search",params={"q":q+", UK","format":"jsonv2","limit":1,"addressdetails":1},headers=UA,timeout=TIMEOUT)
    r.raise_for_status(); data=r.json()
    if not data: raise ValueError(f"Could not locate ‘{q}’. Try adding a postcode, county or nearby town.")
    x=data[0]; a=x.get("address",{})
    return {"label":x["display_name"],"lat":float(x["lat"]),"lon":float(x["lon"]),"admin":a.get("county") or a.get("city") or a.get("town"),"region":a.get("state"),"country":a.get("country"),"parliamentary":None,"source":"OpenStreetMap Nominatim"}

TAGS={
"Shops":"node[shop];way[shop];relation[shop]",
"Schools":"node[amenity=school];way[amenity=school];relation[amenity=school]",
"Parks":"node[leisure=park];way[leisure=park];relation[leisure=park]",
"Leisure":"node[leisure~\"fitness_centre|sports_centre|swimming_pool|golf_course\"];way[leisure~\"fitness_centre|sports_centre|swimming_pool|golf_course\"]",
"Healthcare":"node[amenity~\"hospital|clinic|doctors|pharmacy\"];way[amenity~\"hospital|clinic|doctors\"]",
"Food & drink":"node[amenity~\"restaurant|cafe|pub\"];way[amenity~\"restaurant|cafe|pub\"]",
"Rail":"node[railway=station]",
"Bus":"node[highway=bus_stop]"
}
@st.cache_data(ttl=21600, show_spinner=False)
def amenities(lat,lon,radius=3000):
    blocks=[]
    for n,t in TAGS.items(): blocks.append(f'{t}(around:{radius},{lat},{lon});')
    q='[out:json][timeout:35];('+''.join(blocks)+');out center tags;'
    r=requests.post("https://overpass-api.de/api/interpreter",data=q,headers=UA,timeout=50); r.raise_for_status()
    out={k:[] for k in TAGS}
    for e in r.json().get("elements",[]):
        tags=e.get("tags",{}); elat=e.get("lat") or e.get("center",{}).get("lat"); elon=e.get("lon") or e.get("center",{}).get("lon")
        if not elat: continue
        cat=None
        if "shop" in tags: cat="Shops"
        elif tags.get("amenity")=="school": cat="Schools"
        elif tags.get("leisure")=="park": cat="Parks"
        elif tags.get("leisure") in ["fitness_centre","sports_centre","swimming_pool","golf_course"]: cat="Leisure"
        elif tags.get("amenity") in ["hospital","clinic","doctors","pharmacy"]: cat="Healthcare"
        elif tags.get("amenity") in ["restaurant","cafe","pub"]: cat="Food & drink"
        elif tags.get("railway")=="station": cat="Rail"
        elif tags.get("highway")=="bus_stop": cat="Bus"
        if cat: out[cat].append({"name":tags.get("name",cat[:-1] if cat.endswith('s') else cat),"lat":elat,"lon":elon})
    return out

@st.cache_data(ttl=3600,show_spinner=False)
def crimes(lat,lon):
    r=requests.get("https://data.police.uk/api/crimes-street/all-crime",params={"lat":lat,"lng":lon},timeout=30)
    if r.status_code!=200:return []
    return r.json()

@st.cache_data(ttl=86400,show_spinner=False)
def route(a,b):
    u=f"https://router.project-osrm.org/route/v1/driving/{a['lon']},{a['lat']};{b['lon']},{b['lat']}"
    r=requests.get(u,params={"overview":"false"},timeout=30).json()
    if r.get("code")!="Ok": return None
    x=r["routes"][0];return x["distance"]/1609.344,x["duration"]/60

def sat(n,cap): return min(100,100*n/cap)
def profile(loc,am,cr):
    c=len(cr);cats=Counter(x.get("category","other").replace("-"," ").title() for x in cr)
    scores={"Travel":.55*sat(len(am["Rail"]),3)+.45*sat(len(am["Bus"]),30),"Parks & nature":sat(len(am["Parks"]),10),"Shops":sat(len(am["Shops"]),80),"Schools":sat(len(am["Schools"]),15),"Leisure":sat(len(am["Leisure"]),15),"Healthcare":sat(len(am["Healthcare"]),20),"Social life":sat(len(am["Food & drink"]),70),"Lower recorded crime":max(0,100-c/8)}
    return scores,c,cats

def radar(home,dest):
    cats=list(home); fig=go.Figure()
    fig.add_trace(go.Scatterpolar(r=[home[x] for x in cats]+[home[cats[0]]],theta=cats+[cats[0]],fill='toself',name='Home',line_color='#2563eb'))
    fig.add_trace(go.Scatterpolar(r=[dest[x] for x in cats]+[dest[cats[0]]],theta=cats+[cats[0]],fill='toself',name='Destination',line_color='#f97316'))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True,range=[0,100])),height=460,margin=dict(l=50,r=50,t=30,b=30),legend=dict(orientation='h'))
    return fig

def report_html(h,d,hs,ds,weights,routeinfo):
    rows=''.join(f"<tr><td>{k}</td><td>{hs[k]:.0f}</td><td>{ds[k]:.0f}</td><td>{weights[k]}</td></tr>" for k in hs)
    htot=sum(hs[k]*weights[k] for k in hs)/sum(weights.values());dtot=sum(ds[k]*weights[k] for k in ds)/sum(weights.values())
    journey=f"{routeinfo[0]:.1f} miles; about {routeinfo[1]:.0f} minutes by car" if routeinfo else "Unavailable"
    return f"""<!doctype html><meta charset='utf-8'><title>MoveWise comparison</title><style>body{{font-family:Arial;max-width:900px;margin:40px auto;color:#17332d}}h1{{color:#0f766e}}table{{border-collapse:collapse;width:100%}}th,td{{padding:9px;border-bottom:1px solid #ddd;text-align:left}}.note{{background:#eef8f4;padding:14px;border-radius:10px}}</style><h1>MoveWise UK comparison</h1><h2>{html.escape(h['label'])} → {html.escape(d['label'])}</h2><p><b>Weighted indication:</b> Home {htot:.0f}/100; Destination {dtot:.0f}/100</p><p><b>Road journey:</b> {journey}</p><table><tr><th>Theme</th><th>Home</th><th>Destination</th><th>Your importance</th></tr>{rows}</table><p class='note'><b>Read before deciding:</b> Scores are relative indicators derived mainly from mapped amenities within 3 km and a recent Police.uk street-crime response. They are not quality ratings. Verify schools/admissions, flood and ground risk, broadband, transport timetables, planning, council tax, property condition and neighbourhood feel independently.</p>"""

with st.sidebar:
    st.header("Your priorities")
    st.caption("0 = ignore, 10 = essential")
    weights={k:st.slider(k,0,10,7 if k in ["Travel","Parks & nature","Shops"] else 5) for k in ["Travel","Parks & nature","Shops","Schools","Leisure","Healthcare","Social life","Lower recorded crime"]}
    st.divider(); radius=st.select_slider("Nearby-area radius",options=[1000,2000,3000,5000],value=3000,format_func=lambda x:f"{x/1000:g} km")

c1,c2=st.columns(2)
hq=c1.text_input("Home location",value="Marlow, Buckinghamshire",placeholder="Address, town, county or postcode")
dq=c2.text_input("Possible destination",placeholder="e.g. Bath, BA1 or a full address")
go=st.button("Compare the two areas",type="primary",use_container_width=True)

if go:
  if not hq or not dq: st.warning("Enter both locations.")
  else:
    try:
      with st.spinner("Finding both places and gathering local evidence…"):
        h=geocode(hq); d=geocode(dq); ha=amenities(h['lat'],h['lon'],radius); da=amenities(d['lat'],d['lon'],radius); hc=crimes(h['lat'],h['lon']); dc=crimes(d['lat'],d['lon']); ri=route(h,d)
      hs,hn,hcats=profile(h,ha,hc);ds,dn,dcats=profile(d,da,dc)
      denom=sum(weights.values()) or 1; htot=sum(hs[k]*weights[k] for k in hs)/denom;dtot=sum(ds[k]*weights[k] for k in ds)/denom
      st.subheader("At a glance")
      a,b,c=st.columns(3);a.metric("Home weighted indication",f"{htot:.0f}/100");b.metric("Destination weighted indication",f"{dtot:.0f}/100",f"{dtot-htot:+.0f} vs home");c.metric("Approx. drive" if ri else "Road route","Unavailable" if not ri else f"{ri[0]:.0f} mi · {ri[1]/60:.1f} hr")
      if dtot>htot: st.success("On your chosen priorities, the destination currently comes out ahead. Treat this as a question-generator, not a verdict.")
      elif htot>dtot: st.info("Your present area currently scores more strongly on the priorities selected. The destination may still win on property, lifestyle or street-level factors not captured here.")
      else: st.info("The two locations are evenly matched on your selected priorities.")
      t1,t2,t3,t4=st.tabs(["Comparison","Map","Evidence","House-hunter checklist"])
      with t1:
        st.plotly_chart(radar(hs,ds),use_container_width=True)
        df=pd.DataFrame({"Theme":list(hs),"Home":[round(hs[x]) for x in hs],"Destination":[round(ds[x]) for x in ds],"Importance":[weights[x] for x in hs]})
        st.dataframe(df,hide_index=True,use_container_width=True)
      with t2:
        m=folium.Map(location=[(h['lat']+d['lat'])/2,(h['lon']+d['lon'])/2],zoom_start=8)
        folium.Marker([h['lat'],h['lon']],tooltip="Home",icon=folium.Icon(color="blue",icon="home")).add_to(m);folium.Marker([d['lat'],d['lon']],tooltip="Destination",icon=folium.Icon(color="orange",icon="star")).add_to(m)
        st_folium(m,use_container_width=True,height=500)
      with t3:
        for title,loc,am,n,cats in [("Home",h,ha,hn,hcats),("Destination",d,da,dn,dcats)]:
          st.markdown(f"### {title}: {loc['label']}");st.caption(f"Administrative area: {loc.get('admin') or 'not returned'} · Location source: {loc['source']}")
          cols=st.columns(4)
          for i,k in enumerate(TAGS): cols[i%4].metric(k,len(am[k]))
          st.write(f"Police.uk street-level records returned: **{n}**. This is not a population-adjusted crime rate and must not be used as a direct safety verdict.")
          if cats: st.caption("Largest returned categories: "+", ".join(f"{k} ({v})" for k,v in cats.most_common(5)))
      with t4:
        st.markdown("""#### Verify before committing
- Visit on a weekday, evening and weekend; listen for road, rail, aircraft and nightlife noise.
- Test the real commute at the times you would travel, including parking and the last return service.
- Check Ofsted reports **and** current admissions/catchment rules directly with the local authority.
- Obtain property-specific flood, drainage, mining, radon, planning, title and environmental searches.
- Check exact-address broadband and mobile coverage, not postcode averages.
- Compare council tax, insurance, energy/EPC, parking permits and likely maintenance costs.
- Search nearby planning applications and the council's Local Plan.
- Walk to shops, green space and transport rather than relying only on map distance.
- Speak to neighbours and a local independent agent, while treating opinions as subjective.
- For a shortlisted property, commission the appropriate RICS survey.""")
      rep=report_html(h,d,hs,ds,weights,ri)
      st.download_button("Download comparison report (HTML)",rep,file_name="movewise_comparison.html",mime="text/html",use_container_width=True)
      st.caption("Data transparency: mapped amenities can be missing or duplicated. Crime data coverage and dates vary. Scores measure nearby provision, not quality. Route times exclude live traffic.")
    except Exception as e: st.error(f"The comparison could not be completed: {e}")

with st.expander("What could a later version add?"):
 st.write("Property prices and sold-price trends, EPCs, broadband by address, Ofsted and admissions, flood and environmental risk, council tax, deprivation and census indicators, commute timetables, planning applications, GP access, air quality, weather, configurable report branding and optional paid property-data APIs.")
