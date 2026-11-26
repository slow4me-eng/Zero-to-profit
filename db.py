import sqlite3
from pathlib import Path
from datetime import datetime, timezone
DB = Path("data/zero_to_profit.sqlite3")
def now(): return datetime.now(timezone.utc).isoformat()
def conn():
    DB.parent.mkdir(parents=True, exist_ok=True)
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, ts TEXT, role TEXT, title TEXT, body TEXT);
        CREATE TABLE IF NOT EXISTS opportunities(id INTEGER PRIMARY KEY, ts TEXT, title TEXT, customer TEXT, problem TEXT, offer TEXT, first_step TEXT, score INTEGER, status TEXT DEFAULT 'new');
        CREATE TABLE IF NOT EXISTS experiments(id INTEGER PRIMARY KEY, ts TEXT, opportunity_id INTEGER, hypothesis TEXT, action TEXT, success_metric TEXT, outcome TEXT DEFAULT 'pending');
        CREATE TABLE IF NOT EXISTS ledger(id INTEGER PRIMARY KEY, ts TEXT, kind TEXT, amount REAL, note TEXT, verified INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS code_proposals(id INTEGER PRIMARY KEY, ts TEXT, title TEXT, rationale TEXT, patch TEXT, test_result TEXT DEFAULT 'not_run', status TEXT DEFAULT 'proposed');
        """)
        c.execute("INSERT OR IGNORE INTO meta VALUES('status','starting')")
        c.execute("INSERT OR IGNORE INTO meta VALUES('cycles','0')")
def event(role,title,body):
    with conn() as c: c.execute("INSERT INTO events(ts,role,title,body) VALUES(?,?,?,?)",(now(),role,title,body))
def meta(k,v):
    with conn() as c: c.execute("INSERT OR REPLACE INTO meta VALUES(?,?)",(k,str(v)))
def add_opp(x):
    with conn() as c:
        c.execute("""INSERT INTO opportunities(ts,title,customer,problem,offer,first_step,score)
        VALUES(?,?,?,?,?,?,?)""",(now(),x.get("title","Untitled"),x.get("customer",""),x.get("problem",""),
        x.get("offer",""),x.get("first_step",""),max(1,min(10,int(x.get("score",5))))))
def add_experiment(opp_id,hypothesis,action,metric):
    with conn() as c: c.execute("INSERT INTO experiments(ts,opportunity_id,hypothesis,action,success_metric) VALUES(?,?,?,?,?)",(now(),opp_id,hypothesis,action,metric))
def snapshot():
    with conn() as c:
        rows=lambda q:[dict(r) for r in c.execute(q)]
        m={r["key"]:r["value"] for r in c.execute("SELECT * FROM meta")}
        income=c.execute("SELECT COALESCE(SUM(amount),0) n FROM ledger WHERE kind='income' AND verified=1").fetchone()["n"]
        costs=c.execute("SELECT COALESCE(SUM(amount),0) n FROM ledger WHERE kind='cost' AND verified=1").fetchone()["n"]
        return {"meta":m,"income":income,"costs":costs,"net":income-costs,
        "events":rows("SELECT * FROM events ORDER BY id DESC LIMIT 60"),
        "opportunities":rows("SELECT * FROM opportunities ORDER BY score DESC,id DESC LIMIT 40"),
        "experiments":rows("SELECT * FROM experiments ORDER BY id DESC LIMIT 30"),
        "ledger":rows("SELECT * FROM ledger ORDER BY id DESC LIMIT 30"),
        "code_proposals":rows("SELECT * FROM code_proposals ORDER BY id DESC LIMIT 10")}
