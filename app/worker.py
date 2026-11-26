import os,threading,time,json
from dotenv import load_dotenv
from . import db
from .brain import orchestrate
load_dotenv()
def run_cycle():
    state=db.snapshot()
    result=orchestrate(state)
    for role,data in result["reports"]:
        db.event(role,"Specialist research",data.get("report","")+"\n"+json.dumps(data.get("ideas",[]),ensure_ascii=False))
        for idea in data.get("ideas",[])[:int(os.getenv("MAX_OPPORTUNITIES","5"))]:
            if idea.get("title"): db.add_opp(idea)
    s=result.get("synthesis",{})
    db.event("director","Cycle synthesis",s.get("summary",""))
    if s.get("next_experiment"):
        db.event("director","Next experiment proposed",s["next_experiment"]+"\nHypothesis: "+s.get("hypothesis","")+"\nMetric: "+s.get("success_metric",""))
    ci=s.get("code_improvement",{})
    if ci.get("title"):
        with db.conn() as c:
            c.execute("INSERT INTO code_proposals(ts,title,rationale,patch) VALUES(?,?,?,?)",
             (db.now(),ci.get("title","Improvement"),ci.get("rationale",""),ci.get("patch","")))
    n=int(db.snapshot()["meta"].get("cycles","0"))+1
    db.meta("cycles",n); db.meta("status","running")
def loop():
    db.meta("status","running")
    while True:
        try: run_cycle()
        except Exception as e: db.event("system","Worker error",str(e)); db.meta("status","error")
        time.sleep(max(5,int(os.getenv("CYCLE_MINUTES","30")))*60)
def start():
    threading.Thread(target=loop,daemon=True,name="zero-to-profit-worker").start()
