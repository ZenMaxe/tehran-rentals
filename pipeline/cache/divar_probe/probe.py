import json, requests, sys
S="https://api.divar.ir/v8/postlist/w/search"
H={"User-Agent":"Mozilla/5.0","Content-Type":"application/json"}
dist=json.load(open('cache/divar_districts.json'))['districts']
bysl={d['slug']:d for d in dist}
def q(data, pag=None):
    body={"city_ids":["1"],"search_data":{"form_data":{"data":data}}}
    if pag: body["pagination_data"]=pag
    r=requests.post(S,json=body,headers=H,timeout=30); return r.status_code, r.json()
def rows(j):
    out=[]
    for w in j.get('list_widgets',[]):
        if w['widget_type']=='POST_ROW':
            d=w['data']; out.append((d['token'],d['action']['payload']['web_info'].get('district_persian'),d.get('top_description_text'),d.get('middle_description_text')))
    return out
base={"category":{"str":{"value":"apartment-rent"}}}
for name in sys.argv[1:]:
    did=str(bysl[name]['id'])
    data=dict(base, districts={"repeated_string":{"value":[did]}})
    c,j=q(data); r=rows(j); print(name,did,c,len(r),j['pagination'].get('has_next_page'), j['search_data']['form_data']['data'].keys())
    for x in r[:6]: print('  ',x)
    c,j2=q(data, j['pagination']['data']); r2=rows(j2); print(' page2',c,len(r2),'overlap',len(set(a[0] for a in r)&set(a[0] for a in r2)), j2['pagination'].get('has_next_page'))
