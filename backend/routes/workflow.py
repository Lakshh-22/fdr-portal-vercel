"""Verification, remarks, renewal and release/refund workflow."""
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

from services.bank_adapter import lookup as bank_lookup
from services.fdr_service import announce
bp = Blueprint("workflow", __name__)

@bp.post("/api/fdrs/<int:fid>/verify")
@auth("official", "admin")
def verify(fid):
    c, f = db(), getf(fid)
    if not f: return nf()
    r = bank_lookup(c, f["fdr_number"])
    if not r: st, conf = "NOT_FOUND", None
    else:
        conf = {"bank": r["bank"], "amount": r["amount"], "maturity_date": r["maturity_date"]}
        st = "VERIFIED" if (r["bank"], r["amount"], r["maturity_date"]) == (f["bank"], f["amount"], f["maturity_date"]) else "MISMATCH"
    c.execute("UPDATE fdrs SET bank_status=?, bank_conf=?, state=? WHERE id=?", (st, json.dumps(conf) if conf else None, "VERIFIED" if st == "VERIFIED" else "DISCREPANCY", fid))
    hist(c, fid, g.u["username"], f"Bank verification: {st}")
    if st != "VERIFIED": announce(c, f, f"Bank verification result: {st.replace('_', ' ')}. Please review the submitted details.")
    c.commit(); return jsonify(bank_status=st)

@bp.post("/api/fdrs/<int:fid>/remark")
@auth("official", "admin")
def remark(fid):
    c, f, tx = db(), getf(fid), (request.get_json(silent=True) or {}).get("text", "").strip()[:300]
    if not f or not tx: return jsonify(error="Remark required"), 400
    hist(c, fid, g.u["username"], f"Scrutiny remark: {tx}"); c.commit(); return jsonify(ok=True)

@bp.post("/api/fdrs/<int:fid>/renew")
@auth("institution")
def renew(fid):
    c, f, j = db(), getf(fid), request.get_json(silent=True) or {}
    if not f or f["state"] in ("RENEWED", "RELEASED"): return jsonify(error="Cannot renew this FDR"), 400
    try: n, amt, m = j["fdr_number"].strip(), float(j["amount"]), j["maturity_date"]; D(m); assert n and amt > 0 and m > today(c).isoformat()
    except Exception: return jsonify(error="Enter new FDR number, amount and a future maturity date"), 400
    if c.execute("SELECT 1 FROM fdrs WHERE fdr_number=?", (n,)).fetchone(): return jsonify(error="Duplicate FDR number"), 409
    cur = c.execute("INSERT INTO fdrs(institution_id,bank,fdr_number,amount,issue_date,maturity_date,renewed_from) VALUES(?,?,?,?,?,?,?)", (f["institution_id"], j.get("bank") or f["bank"], n, amt, today(c).isoformat(), m, fid))
    c.execute("UPDATE fdrs SET state='RENEWED' WHERE id=?", (fid,)); hist(c, cur.lastrowid, g.u["username"], f"Renewal of {f['fdr_number']}")
    hist(c, fid, g.u["username"], f"Renewed as {n}"); c.commit(); return jsonify(id=cur.lastrowid), 201

@bp.post("/api/fdrs/<int:fid>/request_release")
@auth("institution")
def req_rel(fid):
    c, f = db(), getf(fid)
    if not f or f["state"] != "VERIFIED": return jsonify(error="Only bank-verified FDRs can be released"), 400
    c.execute("INSERT INTO releases(fdr_id,reason) VALUES(?,?)", (fid, (request.get_json(silent=True) or {}).get("reason", "")))
    c.execute("UPDATE fdrs SET state='RELEASE_REQ' WHERE id=?", (fid,)); hist(c, fid, g.u["username"], "Release/refund requested"); c.commit(); return jsonify(ok=True)

@bp.post("/api/fdrs/<int:fid>/decide_release")
@auth("official", "admin")
def decide(fid):
    c, f, j = db(), getf(fid), request.get_json(silent=True) or {}; ok = j.get("approve") is True
    rr = c.execute("SELECT * FROM releases WHERE fdr_id=? AND status='PENDING'", (fid,)).fetchone()
    if not f or not rr: return jsonify(error="No pending release request"), 400
    if ok and (f["bank_status"] != "VERIFIED" or flags(c, f)): return jsonify(error="Cannot approve: not bank-verified or discrepancies exist"), 400
    c.execute("UPDATE releases SET status=?, remark=? WHERE id=?", ("APPROVED" if ok else "REJECTED", j.get("remark", ""), rr["id"]))
    c.execute("UPDATE fdrs SET state=? WHERE id=?", ("RELEASED" if ok else "VERIFIED", fid)); hist(c, fid, g.u["username"], "Release " + ("APPROVED" if ok else "REJECTED")); announce(c, f, "Release request " + ("approved" if ok else "rejected")); c.commit(); return jsonify(ok=True)

@bp.get("/api/releases")
@auth()
def rel_list():
    c, t, rows = db(), today(db()), []
    for r in c.execute("SELECT * FROM releases ORDER BY (status='PENDING') DESC, id DESC").fetchall():
        f = c.execute("SELECT * FROM fdrs WHERE id=?", (r["fdr_id"],)).fetchone()
        if f and own(f): rows.append(dict(r) | {"fdr": fd(c, f, t)})
    return jsonify(rows)
