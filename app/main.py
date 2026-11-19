from __future__ import annotations
import json, os, re, uuid, wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

ROOT = Path(os.getenv("MYCOVER_DATA_DIR", "data")).resolve()
PROFILES = ROOT / "profiles"
PROFILES.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD = 50 * 1024 * 1024
app = FastAPI(title="MyCover.ai", version="0.1.0")

def now(): return datetime.now(timezone.utc).isoformat()
def safe_id(value: str):
    value = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip()).strip("-").lower()
    if not value: raise HTTPException(400, "Nome inválido.")
    return value[:48]
def folder_for(pid: str):
    p = PROFILES / safe_id(pid)
    if not p.is_dir(): raise HTTPException(404, "Perfil não encontrado.")
    return p
def load(path: Path, default: Any): return json.loads(path.read_text()) if path.exists() else default

class ProfileInput(BaseModel):
    name: str = Field(min_length=2, max_length=64)
    consent_confirmed: bool
    consent_note: str = Field(min_length=8, max_length=500)

@app.get("/", response_class=HTMLResponse)
def home():
    return HTMLResponse("""<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MyCover.ai</title><style>
body{margin:0;background:radial-gradient(circle at 20% 0,#38245f,#0b1020 58%);color:#f4f2ff;font:16px system-ui}main{max-width:850px;margin:8vh auto;padding:24px}.card{background:#171d32;border:1px solid #3b4564;border-radius:18px;padding:22px;margin:16px 0}h1{font-size:clamp(40px,8vw,68px);margin:0}p{color:#bac5df;line-height:1.5}input,button{font:inherit;padding:12px;border-radius:10px;border:1px solid #485575;background:#0d1426;color:white;margin:6px 0;width:100%;box-sizing:border-box}button{background:#7654e8;border:0;font-weight:700;cursor:pointer}.small{font-size:13px;color:#9eabc9}</style><main><p>GLITCHVIBES · VOICE LAB</p><h1>MyCover.ai</h1><p>Organize gravações autorizadas e acompanhe a evolução dos seus perfis de voz.</p><section class="card"><h2>Criar perfil</h2><form id="f"><input name="name" placeholder="Nome do perfil" required minlength="2"><input name="consent_note" placeholder="Como a autorização foi obtida" required minlength="8"><label><input style="width:auto" type="checkbox" name="consent_confirmed" required> Confirmo que a voz é minha ou tenho autorização explícita.</label><button>Criar perfil</button></form><p id="msg" class="small"></p></section><section class="card"><h2>Perfis</h2><div id="list">Carregando…</div></section><p class="small">Protótipo inicial: treinamento e geração de voz ainda dependem da configuração de um backend de IA compatível.</p></main><script>
async function load(){let r=await fetch('/api/profiles'),d=await r.json();document.querySelector('#list').innerHTML=d.profiles.map(p=>'<p><b>'+esc(p.name)+'</b> · '+p.samples+' gravações · '+esc(p.id)+'</p>').join('')||'Nenhum perfil ainda.'}function esc(s){return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
document.querySelector('#f').onsubmit=async e=>{e.preventDefault();let x=new FormData(e.target),r=await fetch('/api/profiles',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:x.get('name'),consent_note:x.get('consent_note'),consent_confirmed:x.get('consent_confirmed')==='on'})}),d=await r.json();document.querySelector('#msg').textContent=r.ok?'Perfil criado: '+d.id:(d.detail||'Erro');if(r.ok){e.target.reset();load()}};load();</script></html>""")

@app.get("/health")
def health(): return {"ok": True, "app": "MyCover.ai", "version": app.version, "model_backend": "not_configured"}

@app.get("/api/profiles")
def profiles():
    out=[]
    for p in PROFILES.iterdir():
        f=p/"profile.json"
        if p.is_dir() and f.exists():
            m=load(f,{})
            out.append({"id":p.name,"name":m.get("name",p.name),"samples":len(list((p/"samples").glob("*.wav")))})
    return {"profiles":sorted(out,key=lambda x:x["name"].lower())}

@app.post("/api/profiles")
def create_profile(data: ProfileInput):
    if not data.consent_confirmed: raise HTTPException(400,"Confirme a autorização da voz.")
    pid=f"{safe_id(data.name)}-{uuid.uuid4().hex[:6]}"; p=PROFILES/pid; (p/"samples").mkdir(parents=True)
    meta={"id":pid,"name":data.name,"created_at":now(),"consent_confirmed":True,"consent_note":data.consent_note,"dataset_revision":0,"experiments":[]}
    (p/"profile.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2))
    return {"id":pid,"name":data.name,"created_at":meta["created_at"]}

@app.post("/api/profiles/{pid}/samples")
async def upload_sample(pid: str, audio: UploadFile=File(...)):
    p=folder_for(pid)
    if Path(audio.filename or "").suffix.lower()!=".wav": raise HTTPException(415,"Envie um arquivo WAV.")
    target=p/"samples"/f"{uuid.uuid4().hex}.wav"; size=0
    try:
        with target.open("wb") as out:
            while chunk:=await audio.read(1024*1024):
                size+=len(chunk)
                if size>MAX_UPLOAD: raise HTTPException(413,"Limite de 50 MB.")
                out.write(chunk)
        with wave.open(str(target),"rb") as w:
            info={"channels":w.getnchannels(),"sample_rate":w.getframerate(),"duration_seconds":round(w.getnframes()/w.getframerate(),2)}
        if info["channels"] not in (1,2) or info["sample_rate"]<16000: raise HTTPException(400,"WAV deve ter 1 ou 2 canais e pelo menos 16 kHz.")
    except (wave.Error,EOFError):
        target.unlink(missing_ok=True); raise HTTPException(400,"Arquivo WAV inválido.")
    except Exception:
        target.unlink(missing_ok=True); raise
    mf=p/"profile.json"; m=load(mf,{}); m["dataset_revision"]=m.get("dataset_revision",0)+1
    mf.write_text(json.dumps(m,ensure_ascii=False,indent=2))
    return {"sample_id":target.stem,**info,"dataset_revision":m["dataset_revision"]}

@app.get("/api/profiles/{pid}/dataset")
def dataset(pid: str):
    p=folder_for(pid); m=load(p/"profile.json",{}); samples=[]
    for f in sorted((p/"samples").glob("*.wav")):
        try:
            with wave.open(str(f),"rb") as w: samples.append({"id":f.stem,"duration_seconds":round(w.getnframes()/w.getframerate(),2),"sample_rate":w.getframerate(),"channels":w.getnchannels()})
        except (wave.Error,ZeroDivisionError): samples.append({"id":f.stem,"error":"invalid_wav"})
    return {"profile_id":pid,"dataset_revision":m.get("dataset_revision",0),"samples":samples,"total_duration_seconds":round(sum(s.get("duration_seconds",0) for s in samples),2)}

@app.post("/api/profiles/{pid}/experiments")
def experiment(pid: str):
    p=folder_for(pid); mf=p/"profile.json"; m=load(mf,{})
    if not list((p/"samples").glob("*.wav")): raise HTTPException(400,"Adicione gravações primeiro.")
    e={"id":uuid.uuid4().hex[:12],"created_at":now(),"dataset_revision":m.get("dataset_revision",0),"status":"blocked","message":"Backend de treinamento não configurado; nenhum modelo foi treinado."}
    m.setdefault("experiments",[]).append(e); mf.write_text(json.dumps(m,ensure_ascii=False,indent=2)); return e

@app.get("/api/profiles/{pid}/experiments")
def experiments(pid: str): return {"experiments":load(folder_for(pid)/"profile.json",{}).get("experiments",[])}
