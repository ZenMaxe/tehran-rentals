import json, requests, time, collections
S="https://api.divar.ir/v8/postlist/w/search"; H={"User-Agent":"Mozilla/5.0"}
data={"category":{"str":{"value":"apartment-rent"}},"districts":{"repeated_string":{"value":["278"]}},
 "credit":{"number_range":{"maximum":"500000000"}},"rent":{"number_range":{"maximum":"17000000"}}}
for dr in (False, True):
    pag=None; seq=[]
    for p in range(6):
        body={"city_ids":["1"],"search_data":{"form_data":{"data":data}},"disable_recommendation":dr}
        if pag: body["pagination_data"]=pag
        j=requests.post(S,json=body,headers=H,timeout=30).json(); time.sleep(1.2)
        for w in j.get("list_widgets",[]):
            t=w["widget_type"]; seq.append(t if t!="POST_ROW" else "P")
            if t!="POST_ROW": print(dr,p,t,json.dumps(w.get("data"),ensure_ascii=False)[:300])
        if not j["pagination"].get("has_next_page"): break
        pag=j["pagination"]["data"]
    print("disable_recommendation",dr,"pages",p+1,collections.Counter(seq), "".join(s[0] for s in seq))
