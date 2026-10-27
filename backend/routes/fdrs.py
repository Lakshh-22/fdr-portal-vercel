"""FDR repository: list, detail, create, document upload."""
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

from services.fdr_service import announce
bp = Blueprint("fdrs", __name__)

@bp.get("/api/fdrs")
@auth()
def fdrs():
    c, t = db(), today(db()); q = request.args.get("q", "").lower(); st = request.args.get("state", "")
    rows = [fd(c, f, t) for f in c.execute("SELECT * FROM fdrs ORDER BY maturity_date") if own(f)]
    rows = [r for r in rows if (not q or q in (r["fdr_number"] + r["institution"] + r["bank"]).lower()) and (not st or st in (r["state"], r["lifecycle"]))]
    return jsonify(rows)

@bp.get("/api/fdrs/<int:fid>")
@auth()
def fdr_one(fid):
    f = getf(fid); return jsonify(fd(db(), f, today(db()), True)) if f else nf()

@bp.post("/api/fdrs")
@auth()
def fdr_new():
    c, j = db(), request.get_json(silent=True) or {}
    inst = g.u["institution_id"] if g.u["role"] == "institution" else j.get("institution_id")
    if not inst or not c.execute("SELECT 1 FROM institutions WHERE id=?", (inst,)).fetchone(): return jsonify(error="Select an institution"), 400
    try:
        amt = float(j["amount"]); n = j["fdr_number"].strip(); bank = j["bank"].strip(); i, m = j["issue_date"], j["maturity_date"]; D(i); D(m)
        assert amt > 0 and n and bank
    except Exception: return jsonify(error="Fill bank, FDR number, positive amount and valid dates"), 400
    if m <= i: return jsonify(error="Maturity date must be after issue date"), 400
    if c.execute("SELECT 1 FROM fdrs WHERE fdr_number=?", (n,)).fetchone(): return jsonify(error="Duplicate FDR number"), 409
    cur = c.execute("INSERT INTO fdrs(institution_id,bank,fdr_number,amount,issue_date,maturity_date) VALUES(?,?,?,?,?,?)", (inst, bank, n, amt, i, m))
    hist(c, cur.lastrowid, g.u["username"], f"FDR {n} submitted")
    announce(c, c.execute("SELECT * FROM fdrs WHERE id=?", (cur.lastrowid,)).fetchone(), "New FDR submitted and awaiting bank verification", "desk")
    c.commit(); return jsonify(id=cur.lastrowid), 201

@bp.post("/api/fdrs/<int:fid>/upload")
@auth()
def upload(fid):
    c, f, fl = db(), getf(fid), request.files.get("file")
    if not f: return nf()
    if not fl or not fl.filename.lower().endswith(ALLOWED): return jsonify(error="Only PDF/PNG/JPG up to 5 MB"), 400
    data = fl.read(); h = hashlib.sha256(data).hexdigest(); name = secure_filename(fl.filename); p = os.path.join(UP, f"{h[:12]}_{name}")
    open(p, "wb").write(data); c.execute("INSERT INTO docs(fdr_id,name,sha256,path,at) VALUES(?,?,?,?,?)", (fid, name, h, p, now()))
    hist(c, fid, g.u["username"], f"Document uploaded: {name} (sha256 {h[:12]})"); c.commit(); return jsonify(sha256=h), 201

@bp.put("/api/fdrs/<int:fid>")
@auth()
def fdr_edit(fid):
    c, f, j = db(), getf(fid), request.get_json(silent=True) or {}
    if not f: return nf()
    if f["state"] not in ("SUBMITTED", "DISCREPANCY"): return jsonify(error="Only unverified FDRs can be edited"), 400
    try:
        bank, n = (j.get("bank") or f["bank"]).strip(), (j.get("fdr_number") or f["fdr_number"]).strip(); amt = float(j.get("amount", f["amount"]))
        i, m = j.get("issue_date") or f["issue_date"], j.get("maturity_date") or f["maturity_date"]; D(i); D(m); assert amt > 0 and n and bank
    except Exception: return jsonify(error="Invalid values"), 400
    if m <= i: return jsonify(error="Maturity date must be after issue date"), 400
    if n != f["fdr_number"] and c.execute("SELECT 1 FROM fdrs WHERE fdr_number=?", (n,)).fetchone(): return jsonify(error="Duplicate FDR number"), 409
    c.execute("UPDATE fdrs SET bank=?,fdr_number=?,amount=?,issue_date=?,maturity_date=?,state='SUBMITTED',bank_status='UNCHECKED',bank_conf=NULL,last_rem=NULL WHERE id=?", (bank, n, amt, i, m, fid))
    hist(c, fid, g.u["username"], "Details edited (bank re-verification required)"); c.commit(); return jsonify(ok=True)
