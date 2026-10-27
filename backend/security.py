"""JWT authentication and role-based access control."""
from functools import wraps
import jwt
from flask import request, jsonify, g
from config import SECRET
from database import db

def auth(*roles):
    def deco(fn):
        @wraps(fn)
        def w(*a, **kw):
            tok = (request.headers.get("Authorization", "")[7:]) or request.args.get("t", "")
            try: p = jwt.decode(tok, SECRET, algorithms=["HS256"])
            except Exception: return jsonify(error="Login required"), 401
            u = db().execute("SELECT * FROM users WHERE id=?", (p["uid"],)).fetchone()
            if not u: return jsonify(error="Login required"), 401
            if roles and u["role"] not in roles: return jsonify(error="Not permitted for your role"), 403
            g.u = u; return fn(*a, **kw)
        return w
    return deco

def own(f): return g.u["role"] != "institution" or f["institution_id"] == g.u["institution_id"]

def getf(fid):
    f = db().execute("SELECT * FROM fdrs WHERE id=?", (fid,)).fetchone()
    return f if f and own(f) else None

def nf(): return jsonify(error="Not found"), 404
