"""Creates the schema and loads demo data on first run.
ALL institutions, contacts and FDR numbers below are FICTIONAL; any resemblance to real entities is coincidental."""
import json, hashlib, datetime as dt
from werkzeug.security import generate_password_hash
from database import conn, SCHEMA
from services.audit import audit
from services.fdr_service import scan

INSTITUTIONS = [("Greenfield Institute of Technology", "greenfield"), ("Riverside College of Engineering", "riverside"), ("Lakeview Technical Institute", "lakeview"), ("Sunrise Polytechnic College", "sunrise"),
                ("Hilltop Institute of Engineering", "hilltop"), ("Northgate Institute of Technology", "northgate"), ("Eastwood Technical College", "eastwood"), ("Westbrook College of Engineering", "westbrook")]
# (institution#, bank, fdr no, amount, issued(d), matures(d), state, has doc, registry: 0 none/1 ok/2 maturity mismatch/3 amount mismatch, renews fdr#)
ROWS = [(1, "SBI", "SBI778201", 5e5, -300, 65, "VERIFIED", 1, 1, 0), (2, "Canara Bank", "CB551029", 1e6, -700, -12, "VERIFIED", 1, 1, 0), (3, "HDFC Bank", "HD330918", 5e5, -100, 260, "SUBMITTED", 1, 1, 0),
        (4, "Indian Bank", "IB902114", 2.5e5, -340, 25, "SUBMITTED", 1, 3, 0), (5, "SBI", "SBI120045", 7.5e5, -50, 315, "SUBMITTED", 0, 0, 0), (1, "Bank of Baroda", "BB440276", 5e5, -500, -60, "RELEASE_REQ", 1, 1, 0),
        (3, "SBI", "SBI664390", 1e6, -30, 335, "VERIFIED", 1, 1, 0), (2, "HDFC Bank", "HD998871", 5e5, -360, 5, "VERIFIED", 1, 1, 0), (6, "Canara Bank", "CB210877", 5e5, -200, 165, "VERIFIED", 1, 1, 0),
        (6, "SBI", "SBI330412", 1e6, -420, 48, "SUBMITTED", 1, 1, 0), (7, "Union Bank", "UB775120", 7.5e5, -380, 12, "DISCREPANCY", 1, 2, 0), (7, "Punjab National Bank", "PNB663019", 5e5, -90, 275, "SUBMITTED", 0, 0, 0),
        (8, "Indian Bank", "IB118834", 2.5e5, -600, -25, "VERIFIED", 1, 1, 0), (8, "HDFC Bank", "HD772601", 5e5, -150, 215, "VERIFIED", 1, 1, 0), (4, "SBI", "SBI540988", 5e5, -710, -40, "RELEASED", 1, 1, 0),
        (5, "Canara Bank", "CB908211", 1e6, -390, -5, "RENEWED", 1, 1, 0), (5, "Canara Bank", "CB908299", 1e6, -4, 361, "VERIFIED", 1, 1, 16), (1, "HDFC Bank", "HD450102", 1e6, -60, 305, "VERIFIED", 1, 1, 0),
        (2, "SBI", "SBI908134", 7.5e5, -250, 115, "VERIFIED", 1, 1, 0), (3, "Indian Bank", "IB660921", 5e5, -340, 35, "RELEASE_REQ", 1, 1, 0), (6, "Bank of Baroda", "BB301288", 2.5e5, -20, 345, "SUBMITTED", 1, 1, 0),
        (4, "Canara Bank", "CB427765", 5e5, -330, 60, "VERIFIED", 1, 1, 0)]


def migrate(c):  # upgrade databases created by older versions
    if "status" not in [r["name"] for r in c.execute("PRAGMA table_info(users)")]: c.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'active'")
    for col in ("email", "phone"):
        if col not in [r["name"] for r in c.execute("PRAGMA table_info(institutions)")]: c.execute(f"ALTER TABLE institutions ADD COLUMN {col} TEXT")


def init_db():
    c = conn(); c.executescript(SCHEMA); migrate(c)
    if not c.execute("SELECT 1 FROM users").fetchone():
        c.execute("INSERT INTO users(username,pw,role) VALUES(?,?,?)", ("admin", generate_password_hash("admin123"), "admin"))
        c.execute("INSERT INTO users(username,pw,role) VALUES(?,?,?)", ("official", generate_password_hash("official123"), "official"))
        for k, (n, u) in enumerate(INSTITUTIONS, 1):
            cur = c.execute("INSERT INTO institutions(name,email,phone) VALUES(?,?,?)", (n, f"registrar@{u}.example", f"+9100000000{k:02d}"))
            c.execute("INSERT INTO users(username,pw,role,institution_id) VALUES(?,?,?,?)", (u, generate_password_hash(u + "123"), "institution", cur.lastrowid))
        for k, v in {"desk_email": "verification.desk@aicte.example", "desk_phone": "+910000000101", "regional_email": "regional.officer@aicte.example", "regional_phone": "+910000000102",
                     "chairman_email": "chairman.office@aicte.example", "chairman_phone": "+910000000103"}.items(): c.execute("INSERT OR IGNORE INTO settings VALUES(?,?)", (k, v))
        iso = lambda n: (dt.date.today() + dt.timedelta(days=n)).isoformat(); ts = lambda d: f"{iso(min(d, 0))}T10:00:00"  # portal event times
        for k, (i, b, n, a, s_, m, st, doc, reg, rf) in enumerate(ROWS, 1):
            sd = -1 if st == "SUBMITTED" else max(s_, -120)  # day the FDR was submitted on the portal
            ver = st in ("VERIFIED", "RELEASE_REQ", "RELEASED", "RENEWED") and reg == 1; bs = "VERIFIED" if ver else "MISMATCH" if reg == 2 else "UNCHECKED"
            conf = json.dumps({"bank": b, "amount": a, "maturity_date": iso(m + (10 if reg == 2 else 0))}) if bs != "UNCHECKED" else None
            c.execute("INSERT INTO fdrs(institution_id,bank,fdr_number,amount,issue_date,maturity_date,state,bank_status,bank_conf,renewed_from) VALUES(?,?,?,?,?,?,?,?,?,?)", (i, b, n, a, iso(s_), iso(m), st, bs, conf, rf or None))
            if doc: c.execute("INSERT INTO docs(fdr_id,name,sha256,path,at) VALUES(?,?,?,?,?)", (k, f"FDR_{n}.pdf", hashlib.sha256(n.encode()).hexdigest(), "", ts(sd)))
            if reg: c.execute("INSERT INTO bank_registry VALUES(?,?,?,?)", (n, b, a * 0.8 if reg == 3 else a, iso(m + (10 if reg == 2 else 0))))
            ev = [(f"FDR {n} submitted", ts(sd))] + ([("Bank verification: VERIFIED", ts(sd + 1 + k % 3))] if ver else [("Bank verification: MISMATCH", ts(sd + 1 + k % 3))] if reg == 2 else []) \
                + ([(f"Renewal of {ROWS[rf - 1][2]}", ts(sd))] if rf else []) + ([("Renewed as CB908299", ts(-4))] if st == "RENEWED" else []) \
                + ([("Release/refund requested", ts(-20))] if st in ("RELEASE_REQ", "RELEASED") else []) + ([("Release APPROVED", ts(-15))] if st == "RELEASED" else [])
            for e, at in ev: c.execute("INSERT INTO history(fdr_id,action,actor,at) VALUES(?,?,?,?)", (k, e, "seed", at))
            if st in ("RELEASE_REQ", "RELEASED"): c.execute("INSERT INTO releases(fdr_id,reason,status) VALUES(?,?,?)", (k, "Approval cycle complete; refund requested", "APPROVED" if st == "RELEASED" else "PENDING"))
        audit(c, "system", "Demo data seeded"); c.commit(); scan(c)
    c.close()
