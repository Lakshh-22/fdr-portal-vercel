"""Hash-chained, tamper-evident audit trail."""
import hashlib
from database import now

def audit(c, actor, action):
    r = c.execute("SELECT hash FROM audit ORDER BY id DESC LIMIT 1").fetchone(); prev = r["hash"] if r else "0"; at = now()
    h = hashlib.sha256(f"{prev}|{actor}|{action}|{at}".encode()).hexdigest()
    c.execute("INSERT INTO audit(actor,action,at,prev,hash) VALUES(?,?,?,?,?)", (actor, action, at, prev, h))

def chain_ok(c):
    prev = "0"
    for r in c.execute("SELECT * FROM audit ORDER BY id"):
        if r["prev"] != prev or r["hash"] != hashlib.sha256(f"{r['prev']}|{r['actor']}|{r['action']}|{r['at']}".encode()).hexdigest(): return False
        prev = r["hash"]
    return True

def hist(c, fid, actor, action):
    c.execute("INSERT INTO history(fdr_id,action,actor,at) VALUES(?,?,?,?)", (fid, action, actor, now())); audit(c, actor, action)
