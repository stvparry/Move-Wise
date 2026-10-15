
def food_hygiene(lat,lon,radius_km=3):
 try:
  headers={**UA,'x-api-version':'2','Accept-Language':'en-GB'}
  p={'latitude':lat,'longitude':lon,'maxDistanceLimit':min(10,radius_km),'pageSize':500}
  r=requests.get('https://api.ratings.food.gov.uk/Establishments',params=p,headers=headers,timeout=35);r.raise_for_status();rows=r.json().get('establishments',[])
  ratings=[]
  for x in rows:
   try:ratings.append(int(x.get('RatingValue')))
   except Exception:pass
  return {'count':len(rows),'rated':len(ratings),'high':sum(v>=4 for v in ratings),'average':sum(ratings)/len(ratings) if ratings else None,'examples':[x.get('BusinessName') for x in rows[:5]]},{'ok':True,'source':'Food Standards Agency','detail':f'{len(rows)} establishments returned'}
 except Exception:return None,{'ok':False,'source':'Food Standards Agency','detail':'Live hygiene-rating search unavailable'}
def flood_context(lat,lon):
 try:
  p={'lat':lat,'long':lon,'dist':10};rows=get('https://environment.data.gov.uk/flood-monitoring/id/floods',p,30).get('items',[])
  return {'active_warnings':len(rows),'descriptions':[x.get('description') for x in rows[:5]]},{'ok':True,'source':'Environment Agency','detail':f'{len(rows)} active warnings/alerts returned within query area'}
 except Exception:return None,{'ok':False,'source':'Environment Agency','detail':'Real-time flood-monitoring context unavailable'}
