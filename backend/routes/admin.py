"""Institutions, maturity scan, demo date, audit log."""
import os, json, csv, io, time, hashlib, datetime as dt
import jwt
from flask import Blueprint, request, jsonify, g, Response
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from config import UP, ALLOWED, SECRET
from database import db, setting, today, D, now
from security import auth, own, getf, nf
from services.audit import audit, chain_ok, hist
from services.fdr_service import lifecycle, flags, risk, fd, notify, scan

from services import notifier
from services.notifier import dispatch
bp = Blueprint("admin", __name__)
KEYS = ["desk_email", "desk_phone", "regional_email", "regional_phone", "chairman_email", "chairman_phone"]

@bp.post("/api/scan")
@auth("official", "admin")
def run_scan():
    c = db(); n = scan(c); audit(c, g.u["username"], f"Manual scan: {n} new alerts"); c.commit(); return jsonify(new_alerts=n)

@bp.post("/api/time")
@auth("official", "admin")
def set_time():
    c = db(); off = max(0, min(400, int((request.get_json(silent=True) or {}).get("offset", 0))))
    c.execute("INSERT OR REPLACE INTO settings VALUES('offset',?)", (str(off),)); audit(c, g.u["username"], f"Demo date shifted +{off}d"); n = scan(c); return jsonify(offset=off, new_alerts=n)

@bp.get("/api/audit")
@auth("official", "admin")
def audit_list():
    c = db(); return jsonify(intact=chain_ok(c), rows=[dict(r) for r in c.execute("SELECT actor,action,at,hash FROM audit ORDER BY id DESC LIMIT 80")])

@bp.get("/api/institutions")
@auth("official", "admin")
def inst_list():
    c, t, out = db(), today(db()), []
    for i in c.execute("SELECT * FROM institutions i WHERE EXISTS (SELECT 1 FROM users u WHERE u.institution_id=i.id AND u.status='active') ORDER BY name").fetchall():
        v = [fd(c, f, t) for f in c.execute("SELECT * FROM fdrs WHERE institution_id=?", (i["id"],))]; live = [r for r in v if r["state"] not in ("RELEASED", "RENEWED")]
        u = c.execute("SELECT username FROM users WHERE institution_id=?", (i["id"],)).fetchone()
        out.append(dict(id=i["id"], name=i["name"], username=u["username"] if u else "", email=i["email"] or "", phone=i["phone"] or "", fdrs=len(v), value=sum(r["amount"] for r in live),
                        pending=sum(r["state"] in ("SUBMITTED", "DISCREPANCY", "RELEASE_REQ") for r in v), attention=sum(r["lifecycle"] in ("Expiring", "Matured") for r in live)))
    return jsonify(out)

@bp.post("/api/institutions")
@auth("admin")
def inst_new():
    c, j = db(), request.get_json(silent=True) or {}; n, u, p = (j.get("name") or "").strip(), (j.get("username") or "").strip().lower(), j.get("password") or ""
    if len(n) < 3 or len(u) < 3 or len(p) < 6: return jsonify(error="Name, username (3+) and password (6+ chars) required"), 400
    if c.execute("SELECT 1 FROM institutions WHERE name=?", (n,)).fetchone() or c.execute("SELECT 1 FROM users WHERE username=?", (u,)).fetchone(): return jsonify(error="Institution or username already exists"), 409
    cur = c.execute("INSERT INTO institutions(name,email,phone) VALUES(?,?,?)", (n, (j.get("email") or "").strip(), (j.get("phone") or "").strip())); c.execute("INSERT INTO users(username,pw,role,institution_id) VALUES(?,?,?,?)", (u, generate_password_hash(p), "institution", cur.lastrowid))
    audit(c, g.u["username"], f"Institution onboarded: {n}"); c.commit(); return jsonify(id=cur.lastrowid), 201

@bp.put("/api/institutions/<int:iid>")
@auth("admin", "institution")
def inst_update(iid):
    c, j = db(), request.get_json(silent=True) or {}
    if g.u["role"] == "institution" and g.u["institution_id"] != iid: return jsonify(error="Not permitted for your role"), 403
    if not c.execute("SELECT 1 FROM institutions WHERE id=?", (iid,)).fetchone(): return nf()
    c.execute("UPDATE institutions SET email=?, phone=? WHERE id=?", ((j.get("email") or "").strip()[:120], (j.get("phone") or "").strip()[:30], iid))
    audit(c, g.u["username"], f"Contact details updated (institution {iid})"); c.commit(); return jsonify(ok=True)

@bp.get("/api/my_contact")
@auth("institution")
def my_contact():
    i = db().execute("SELECT * FROM institutions WHERE id=?", (g.u["institution_id"],)).fetchone(); return jsonify(id=i["id"], name=i["name"], email=i["email"] or "", phone=i["phone"] or "")

@bp.get("/api/notify_settings")
@auth("official", "admin")
def ns_get():
    c = db(); return jsonify(settings={k: setting(c, k, "") for k in KEYS}, channels=notifier.channels(), demo=int(setting(c, "offset")) != 0)

@bp.post("/api/notify_settings")
@auth("official", "admin")
def ns_set():
    c, j = db(), request.get_json(silent=True) or {}
    for k in KEYS:
        if k in j: c.execute("INSERT OR REPLACE INTO settings VALUES(?,?)", (k, str(j[k]).strip()[:120]))
    audit(c, g.u["username"], "Notification contacts updated"); c.commit(); return jsonify(ok=True)

@bp.post("/api/notify_test")
@auth("official", "admin")
def ns_test():
    c, j, res = db(), request.get_json(silent=True) or {}, []
    for ch, key in (("email", "email"), ("sms", "phone")):
        to = (j.get(key) or "").strip()
        if to:
            st, d = notifier.send_now(c, ch, to, "[AICTE FDR] Test message", "This is a test message from the AICTE FDR Portal."); res.append(dict(channel=ch, status=st, detail=d))
    c.commit(); return jsonify(results=res) if res else (jsonify(error="Enter an email or phone number"), 400)

@bp.get("/api/registrations")
@auth("official", "admin")
def reg_list():
    return jsonify([dict(r) for r in db().execute("SELECT i.id, i.name, i.email, i.phone, u.username FROM institutions i JOIN users u ON u.institution_id=i.id WHERE u.status='pending' ORDER BY i.id")])

@bp.post("/api/registrations/<int:iid>/decide")
@auth("official", "admin")
def reg_decide(iid):
    c, ok = db(), (request.get_json(silent=True) or {}).get("approve") is True
    r = c.execute("SELECT i.*, u.id uid FROM institutions i JOIN users u ON u.institution_id=i.id WHERE i.id=? AND u.status='pending'", (iid,)).fetchone()
    if not r: return nf()
    if ok: c.execute("UPDATE users SET status='active' WHERE id=?", (r["uid"],))
    else: c.execute("DELETE FROM users WHERE id=?", (r["uid"],)); c.execute("DELETE FROM institutions WHERE id=?", (iid,))
    audit(c, g.u["username"], f"Registration {'approved' if ok else 'rejected'}: {r['name']}")
    msg = "approved. You can now sign in to the portal." if ok else "not approved. Please contact the AICTE Regulation Bureau."
    dispatch(c, None, "[AICTE FDR] Registration " + ("approved" if ok else "not approved"), f"Dear {r['name']},\n\nYour registration request has been {msg}\n\n-- AICTE Regulation Bureau (automated message)", f"AICTE FDR Portal: registration {msg}", [("Registrant", r["email"], r["phone"])])
    c.commit(); return jsonify(ok=True)
