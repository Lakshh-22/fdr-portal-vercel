"""Login."""
import re, os, json, csv, io, time, hashlib, datetime as dt
import jwt
from flask import Blueprint, request, jsonify, g, Response
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from config import UP, ALLOWED, SECRET
from database import db, setting, today, D, now
from security import auth, own, getf, nf
from services.audit import audit, chain_ok, hist
from services.fdr_service import lifecycle, flags, risk, fd, notify, scan

from services.notifier import dispatch
bp = Blueprint("auth", __name__)

@bp.post("/api/login")
def login():
    j = request.get_json(silent=True) or {}; u = db().execute("SELECT * FROM users WHERE username=?", (j.get("username", ""),)).fetchone()
    if not u or not check_password_hash(u["pw"], j.get("password", "")): return jsonify(error="Invalid username or password"), 401
    if u["status"] == "pending": return jsonify(error="Your registration is awaiting approval by AICTE. You can sign in once it is approved."), 403
    inst = db().execute("SELECT name FROM institutions WHERE id=?", (u["institution_id"],)).fetchone()
    return jsonify(token=jwt.encode({"uid": u["id"], "exp": time.time() + 86400}, SECRET, algorithm="HS256"),
                   user={"username": u["username"], "role": u["role"], "institution": inst["name"] if inst else None})

_hits = {}  # simple in-memory rate limit: 5 registrations per hour per IP

@bp.post("/api/register")
def register():
    c, j = db(), request.get_json(silent=True) or {}; ip = request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip(); t = time.time()
    _hits[ip] = [x for x in _hits.get(ip, []) if t - x < 3600]
    if len(_hits[ip]) >= 5: return jsonify(error="Too many registration attempts. Please try again later."), 429
    n, e, ph, u, p = (j.get("name") or "").strip(), (j.get("email") or "").strip(), (j.get("phone") or "").strip(), (j.get("username") or "").strip().lower(), j.get("password") or ""
    if not 3 <= len(n) <= 150: return jsonify(error="Enter the institution name"), 400
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", e): return jsonify(error="Enter a valid contact email"), 400
    if ph and not re.fullmatch(r"\+?[0-9 \-]{8,15}", ph): return jsonify(error="Enter a valid phone number"), 400
    if not re.fullmatch(r"[a-z0-9_]{3,30}", u): return jsonify(error="Username: 3-30 letters, digits or underscore"), 400
    if len(p) < 8: return jsonify(error="Password must be at least 8 characters"), 400
    if c.execute("SELECT 1 FROM institutions WHERE lower(name)=lower(?)", (n,)).fetchone() or c.execute("SELECT 1 FROM users WHERE username=?", (u,)).fetchone(): return jsonify(error="Institution or username already registered"), 409
    _hits[ip].append(t)
    cur = c.execute("INSERT INTO institutions(name,email,phone) VALUES(?,?,?)", (n, e, ph))
    c.execute("INSERT INTO users(username,pw,role,institution_id,status) VALUES(?,?,?,?,'pending')", (u, generate_password_hash(p), "institution", cur.lastrowid))
    audit(c, "registration", f"Registration request: {n} ({u})")
    subj = "[AICTE FDR] Institution registration request"
    dispatch(c, None, subj, f"Dear {n},\n\nYour registration request for the AICTE Security Deposit / FDR Portal has been received. You will be able to sign in after it is approved.\n\nUsername: {u}\n\n-- AICTE Regulation Bureau (automated message)", "AICTE FDR Portal: registration received, awaiting approval.", [("Registrant", e, ph)])
    dispatch(c, None, subj + f": {n}", f"A new institution has registered and awaits approval: {n} (username {u}). Please review it on the portal (Institutions page).", f"New FDR portal registration: {n}", [("Verification desk", setting(c, "desk_email", ""), setting(c, "desk_phone", ""))])
    c.commit(); return jsonify(ok=True), 201
