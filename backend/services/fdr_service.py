"""Business logic: lifecycle, discrepancy rules, risk score, notifications, maturity scan."""
import json
from config import REMINDERS
from database import D, today, now, setting
from services.notifier import dispatch
from services.audit import audit

def lifecycle(f, t):
    if f["state"] in ("RELEASED", "RENEWED"): return f["state"].title()
    d = (D(f["maturity_date"]) - t).days
    return "Matured" if d < 0 else "Expiring" if d <= 90 else "Active"

def flags(c, f):
    o = []
    if not c.execute("SELECT 1 FROM docs WHERE fdr_id=?", (f["id"],)).fetchone(): o.append("Missing FDR document")
    if f["maturity_date"] <= f["issue_date"]: o.append("Maturity not after issue date")
    if f["bank_status"] == "NOT_FOUND": o.append("Not found in bank registry")
    if f["bank_status"] == "MISMATCH":
        b = json.loads(f["bank_conf"] or "{}")
        if b.get("amount") != f["amount"]: o.append(f"Amount mismatch (bank: {b.get('amount')})")
        if b.get("maturity_date") != f["maturity_date"]: o.append(f"Maturity mismatch (bank: {b.get('maturity_date')})")
        if b.get("bank") != f["bank"]: o.append(f"Bank mismatch (bank: {b.get('bank')})")
    return o

def risk(c, f, t):
    if f["state"] in ("RELEASED", "RENEWED"): return 0
    d = (D(f["maturity_date"]) - t).days; r = 0
    if f["bank_status"] != "VERIFIED": r += 30
    if flags(c, f): r += 25
    return min(100, r + (30 if d < 0 else 20 if d <= 30 else 10 if d <= 90 else 0))

def fd(c, f, t, full=False):
    o = dict(f); o["bank_conf"] = json.loads(f["bank_conf"]) if f["bank_conf"] else None
    o["institution"] = c.execute("SELECT name FROM institutions WHERE id=?", (f["institution_id"],)).fetchone()["name"]
    o["days"] = (D(f["maturity_date"]) - t).days; o["lifecycle"] = lifecycle(f, t); o["risk"] = risk(c, f, t); o["flags"] = flags(c, f)
    o["docs"] = [dict(r) for r in c.execute("SELECT id,name,sha256,at FROM docs WHERE fdr_id=?", (f["id"],))]
    if full:
        o["history"] = [dict(r) for r in c.execute("SELECT action,actor,at FROM history WHERE fdr_id=? ORDER BY id DESC", (f["id"],))]
        o["release"] = (lambda r: dict(r) if r else None)(c.execute("SELECT * FROM releases WHERE fdr_id=? ORDER BY id DESC", (f["id"],)).fetchone())
    return o

def _inst(c, f): return c.execute("SELECT * FROM institutions WHERE id=?", (f["institution_id"],)).fetchone()


def _contacts(c, f, code):
    i = _inst(c, f); out = [("Institution", i["email"], i["phone"]), ("Verification desk", setting(c, "desk_email", ""), setting(c, "desk_phone", ""))]
    if code <= -1: out.append(("Regional Officer", setting(c, "regional_email", ""), setting(c, "regional_phone", "")))
    if code <= -2: out.append(("Chairman", setting(c, "chairman_email", ""), setting(c, "chairman_phone", "")))
    return [x for x in out if x[1] or x[2]]


def _body(c, f, headline, action):
    return (f"Dear {_inst(c, f)['name']},\n\n{headline}\n\nFDR number : {f['fdr_number']}\nBank       : {f['bank']}\nAmount     : Rs {f['amount']:,.0f}\nMaturity   : {f['maturity_date']}\n\n{action}\n\n"
            "-- AICTE Regulation Bureau, Security Deposit / FDR Management Portal\n(This is an automated message.)")


def _emit(c, f, msg, level, subject, body, recips):
    c.execute("INSERT INTO notifs(fdr_id,institution_id,message,level,at) VALUES(?,?,?,?,?)", (f["id"], f["institution_id"], msg, level, now()))
    dispatch(c, f["id"], subject, body, f"AICTE FDR {f['fdr_number']}: {msg}", recips)


def notify(c, f, msg, level, code=0):
    act = "Please renew or replace the FDR, or submit a release request on the portal, before the maturity date." if code == 0 else "Immediate action is required. The case has been escalated for follow-up."
    _emit(c, f, msg, level, f"[AICTE FDR] {'Reminder' if code == 0 else 'OVERDUE'}: {f['fdr_number']}", _body(c, f, msg, act), _contacts(c, f, code))


def announce(c, f, msg, to="inst"):
    i = _inst(c, f); r = [("Institution", i["email"], i["phone"])] if to == "inst" else [("Verification desk", setting(c, "desk_email", ""), setting(c, "desk_phone", ""))]
    _emit(c, f, msg, "info", f"[AICTE FDR] {f['fdr_number']}: {msg}", _body(c, f, msg, "Please log in to the portal for details."), [x for x in r if x[1] or x[2]])


def scan(c):
    """Reminders at 90/60/30/7 days; overdue escalation (Regional Officer, then Chairman after 30 days). Idempotent per threshold."""
    t, n = today(c), 0
    for f in c.execute("SELECT * FROM fdrs WHERE state NOT IN ('RELEASED','RENEWED')").fetchall():
        d = (D(f["maturity_date"]) - t).days
        if d < 0:
            code, who = (-2, "Chairman") if -d > 30 else (-1, "Regional Officer")
            if f["last_rem"] != code:
                notify(c, f, f"{f['fdr_number']} overdue by {-d}d: escalated to {who}", "error", code)
                c.execute("UPDATE fdrs SET last_rem=? WHERE id=?", (code, f["id"])); audit(c, "system", f"Escalation {f['fdr_number']} -> {who}"); n += 1
        else:
            k = next((x for x in sorted(REMINDERS) if x >= d), None)
            if k is not None and f["last_rem"] != k:
                notify(c, f, f"{f['fdr_number']} matures in {d} days ({k}-day reminder)", "error" if k <= 7 else "warning")
                c.execute("UPDATE fdrs SET last_rem=? WHERE id=?", (k, f["id"])); audit(c, "system", f"Reminder {f['fdr_number']} ({k}d)"); n += 1
    c.commit(); return n
