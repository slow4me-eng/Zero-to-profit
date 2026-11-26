import os,base64
from fastapi import FastAPI,Request,HTTPException
from fastapi.responses import HTMLResponse,JSONResponse
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv
from . import db
from .worker import start,run_cycle
load_dotenv()
app=FastAPI(title="ZERO TO PROFIT")
class LedgerEntry(BaseModel):
    kind:str
    amount:float
    note:str
    verified:bool=False
class Outcome(BaseModel):
    outcome:str
PAGE=r"""<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>ZERO TO PROFIT</title>
<style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#0b1020;color:#eef2ff;font:15px system-ui}main{max-width:1100px;margin:auto;padding:22px}
h1{font-size:27px;margin:4px 0}.sub,.muted{color:#98a6c5}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.card{background:#151e33;border:1px solid #263653;border-radius:14px;padding:16px;margin:12px 0;overflow-wrap:anywhere}
.metric{font-size:27px;font-weight:700;margin-top:8px}.section{font-size:19px;margin:0 0 10px}
.row{padding:12px 0;border-top:1px solid #293752}.tag{font-size:12px;color:#8fe0b3}.btn{background:#6d8cff;color:white;border:0;border-radius:9px;padding:10px 13px;font-weight:600}
input,select{background:#0c1427;color:white;border:1px solid #394968;border-radius:8px;padding:9px;max-width:100%}
form{display:flex;gap:8px;flex-wrap:wrap}.two{display:grid;grid-template-columns:1fr 1fr;gap:12px}
@media(max-width:700px){main{padding:14px}.grid{grid-template-columns:1fr 1fr}.two{grid-template-columns:1fr}.metric{font-size:22px}}
</style></head><body><main>
<h1>ZERO TO PROFIT</h1><div class="sub">Autonomous opportunity discovery · starting capital €0 · refreshes every 10 seconds</div>
<div class="grid">
<div class="card"><div class="muted">STATUS</div><div class="metric" id="status">…</div></div>
<div class="card"><div class="muted">RESEARCH CYCLES</div><div class="metric" id="cycles">0</div></div>
<div class="card"><div class="muted">VERIFIED INCOME</div><div class="metric" id="income">€0</div></div>
<div class="card"><div class="muted">VERIFIED NET</div><div class="metric" id="net">€0</div></div>
</div>
<div class="two"><section class="card"><h2 class="section">Opportunity pipeline</h2><div id="opps"></div></section>
<section class="card"><h2 class="section">Agent activity / memory</h2><div id="events"></div></section></div>
<section class="card"><h2 class="section">Experiments & learning</h2><div id="experiments"></div></section>
<section class="card"><h2 class="section">Verified money ledger</h2><p class="muted">Only mark income or costs verified when they actually happened.</p>
<form id="ledger"><select name="kind"><option value="income">Income</option><option value="cost">Cost</option></select><input name="amount" type="number" min="0.01" step="0.01" placeholder="EUR" required><input name="note" placeholder="What was it?" required><label><input type="checkbox" name="verified"> Verified</label><button class="btn">Record</button></form><div id="entries"></div></section>
<section class="card"><h2 class="section">Self-improvement lab</h2><p class="muted">The agent records code improvement proposals for review. Live arbitrary code replacement is deliberately not enabled.</p><div id="code"></div></section>
<div class="muted">No earnings are implied by research reports. Hosting uptime and model API availability depend on your provider and plan.</div>
</main><script>
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function refresh(){let d=await(await fetch('/api/state')).json();let m=d.meta;
status.textContent=m.status||'unknown';cycles.textContent=m.cycles||'0';income.textContent='€'+Number(d.income).toFixed(2);net.textContent='€'+Number(d.net).toFixed(2);
opps.innerHTML=d.opportunities.map(x=>`<div class="row"><b>${esc(x.title)}</b> <span class="tag">score ${x.score}/10</span><p>${esc(x.problem)}</p><p><b>Buyer:</b> ${esc(x.customer)}</p><p><b>Offer:</b> ${esc(x.offer)}</p><p><b>First step:</b> ${esc(x.first_step)}</p></div>`).join('')||'Waiting for first cycle.';
events.innerHTML=d.events.map(x=>`<div class="row"><b>${esc(x.role)} · ${esc(x.title)}</b><p>${esc(x.body)}</p><small class="muted">${esc(x.ts)}</small></div>`).join('')||'No activity yet.';
experiments.innerHTML=d.experiments.map(x=>`<div class="row"><b>${esc(x.hypothesis)}</b><p>${esc(x.action)} · Metric: ${esc(x.success_metric)}</p>${esc(x.outcome)}</div>`).join('')||'Next experiments appear in activity feed.';
entries.innerHTML=d.ledger.map(x=>`<div class="row">${esc(x.kind)} €${Number(x.amount).toFixed(2)} · ${esc(x.note)} · ${x.verified?'verified':'unverified'}</div>`).join('');
code.innerHTML=d.code_proposals.map(x=>`<div class="row"><b>${esc(x.title)}</b><p>${esc(x.rationale)}</p><span class="tag">${esc(x.status)} · ${esc(x.test_result)}</span></div>`).join('')||'No code proposals yet.'}
document.getElementById('ledger').addEventListener('submit',async e=>{e.preventDefault();let f=new FormData(e.target);await fetch('/api/ledger',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind:f.get('kind'),amount:Number(f.get('amount')),note:f.get('note'),verified:f.has('verified')})});e.target.reset();refresh()});
refresh();setInterval(refresh,10000);
</script></body></html>"""
@app.middleware("http")
async def auth(request:Request,call_next):
    password=os.getenv("DASHBOARD_PASSWORD","").strip()
    if password and request.url.path not in ("/health",):
        h=request.headers.get("authorization","")
        good=False
        if h.startswith("Basic "):
            try: good=base64.b64decode(h[6:]).decode().split(":",1)[1]==password
            except Exception: pass
        if not good: return JSONResponse({"detail":"Dashboard password required"},401,headers={"WWW-Authenticate":'Basic realm="ZERO TO PROFIT"'})
    return await call_next(request)
@app.on_event("startup")
def startup(): db.init(); start()
@app.get("/",response_class=HTMLResponse)
def home(): return PAGE
@app.get("/health")
def health(): return {"ok":True}
@app.get("/api/state")
def state(): return db.snapshot()
@app.post("/api/ledger")
def ledger(x:LedgerEntry):
    if x.kind not in ("income","cost") or x.amount<=0: raise HTTPException(400,"Invalid ledger entry")
    with db.conn() as c: c.execute("INSERT INTO ledger(ts,kind,amount,note,verified) VALUES(?,?,?,?,?)",(db.now(),x.kind,x.amount,x.note,int(x.verified)))
    db.event("finance","Ledger entry",f"{x.kind} €{x.amount:.2f}: {x.note}; verified={x.verified}")
    return {"ok":True}
@app.post("/api/run-cycle")
def trigger(): run_cycle(); return {"ok":True}
def run(): uvicorn.run("app.main:app",host="0.0.0.0",port=int(os.getenv("PORT","8000")))
