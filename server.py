
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import requests, re, os, urllib.parse, pathlib, mimetypes

app=FastAPI(title="Music Finder")
ROOT=pathlib.Path(__file__).parent
DOWNLOADS=ROOT/"downloads"
DOWNLOADS.mkdir(exist_ok=True)

@app.get("/api/search")
def search(q: str = Query(..., min_length=1)):
    q=q.strip()
    results=[]
    # Internet Archive: public/free media and downloadable files
    try:
        u="https://archive.org/advancedsearch.php"
        params={"q":f'(title:({q}) OR creator:({q}) OR description:({q})) AND mediatype:audio',
                "fl[]":["identifier,title,creator,year,description"],
                "rows":30,"page":1,"output":"json"}
        data=requests.get(u,params=params,timeout=20).json()
        for d in data.get("response",{}).get("docs",[]):
            ident=d.get("identifier")
            if not ident: continue
            results.append({
                "source":"Internet Archive",
                "title":d.get("title") or ident,
                "artist":d.get("creator") or "",
                "year":d.get("year") or "",
                "id":ident,
                "download":f"/api/download?source=archive&id={urllib.parse.quote(ident)}",
                "source_url":f"https://archive.org/details/{urllib.parse.quote(ident)}"
            })
    except Exception:
        pass

    # Audius public API: discovery/open streams; download button is offered only when provider exposes a file URL.
    try:
        r=requests.get("https://api.audius.co/v1/tracks/search",
                       params={"query":q,"limit":20},timeout=20)
        data=r.json()
        for d in data.get("data",[]):
            tid=d.get("id")
            if not tid: continue
            results.append({
                "source":"Audius",
                "title":d.get("title") or "",
                "artist":(d.get("user") or {}).get("name",""),
                "year":"",
                "id":tid,
                "download":f"/api/audius/{urllib.parse.quote(tid)}",
                "source_url":f"https://audius.co/{urllib.parse.quote((d.get('user') or {}).get('handle',''))}/{urllib.parse.quote(d.get('permalink',''))}"
            })
    except Exception:
        pass
    return {"results":results[:50]}

@app.get("/api/audius/{track_id}")
def audius(track_id:str):
    # Resolve an Audius stream. This endpoint is for tracks made available by Audius.
    for host in ["https://api.audius.co"]:
        try:
            r=requests.get(f"{host}/v1/tracks/{track_id}/stream",timeout=20,allow_redirects=True)
            if r.ok and r.url:
                return HTMLResponse(f'<html><body><a href="{r.url}" download>Download/Play track</a></body></html>')
        except Exception: pass
    return HTMLResponse("This track is not currently available for direct download.",status_code=404)

@app.get("/api/download")
def download(source:str,id:str):
    if source!="archive":
        return HTMLResponse("Unsupported source",status_code=400)
    meta=requests.get(f"https://archive.org/metadata/{urllib.parse.quote(id)}",timeout=20).json()
    files=meta.get("files",[])
    # Conservative: only offer common audio files explicitly marked as downloadable.
    candidates=[]
    for f in files:
        name=f.get("name","")
        if re.search(r'\.(mp3|flac|ogg|wav|m4a)$',name,re.I) and not f.get("private"):
            candidates.append(f)
    if not candidates:
        return HTMLResponse("No downloadable audio file was exposed by this item.",status_code=404)
    # Prefer MP3, then other audio formats.
    candidates.sort(key=lambda f:(not f["name"].lower().endswith(".mp3"), len(f["name"])))
    f=candidates[0]
    url="https://archive.org/download/"+urllib.parse.quote(id,safe="")+"/"+urllib.parse.quote(f["name"],safe="")
    # Stream proxy into browser download; limit isn't imposed here, but the archive/provider controls access.
    r=requests.get(url,timeout=60,stream=True)
    r.raise_for_status()
    ctype=f.get("format") or mimetypes.guess_type(f["name"])[0] or "application/octet-stream"
    safe=re.sub(r'[^A-Za-z0-9._ -]','_',pathlib.Path(f["name"]).name)
    out=DOWNLOADS/safe
    with open(out,"wb") as w:
        for chunk in r.iter_content(1024*1024):
            if chunk: w.write(chunk)
    return FileResponse(out,media_type=ctype,filename=safe)

@app.get("/health")
def health(): return {"ok":True}

app.mount("/",StaticFiles(directory=str(ROOT/"static"),html=True),name="static")
