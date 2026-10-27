"""Dashboard, reports and notifications."""
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

bp = Blueprint("dashboard", __name__)

@bp.get("/api/dashboard")
@auth()
def dash():
    c, t = db(), today(db()); v = [fd(c, f, t) for f in c.execute("SELECT * FROM fdrs") if own(f)]; cnt = lambda l: sum(r["lifecycle"] == l for r in v)
    mo = {}
    for r in v:
        if r["state"] not in ("RELEASED", "RENEWED"): mo[r["maturity_date"][:7]] = mo.get(r["maturity_date"][:7], 0) + 1
    val = {}
    for r in v: val[r["lifecycle"]] = val.get(r["lifecycle"], 0) + r["amount"]
    return jsonify(date=t.isoformat(), offset=int(setting(c, "offset")), active=cnt("Active"), expiring=cnt("Expiring"), matured=cnt("Matured"), renewed=cnt("Renewed"), released=cnt("Released"),
        pending=sum(r["state"] in ("SUBMITTED", "DISCREPANCY", "RELEASE_REQ") for r in v), total=len(v), reg_pending=c.execute("SELECT COUNT(*) n FROM users WHERE status='pending'").fetchone()["n"], total_value=sum(r["amount"] for r in v if r["state"] not in ("RELEASED", "RENEWED")),
        to_verify=sum(r["state"] in ("SUBMITTED", "DISCREPANCY") for r in v), rel_pending=sum(r["state"] == "RELEASE_REQ" for r in v), high_risk=sum(r["risk"] >= 50 for r in v), months=mo, value=val,
        top=sorted(v, key=lambda r: -r["risk"])[:5], metrics=metrics(c, v))

@bp.get("/api/reports/<kind>")
@auth()
def report(kind):
    c, t = db(), today(db()); v = [fd(c, f, t) for f in c.execute("SELECT * FROM fdrs ORDER BY maturity_date") if own(f)]
    pick = {"pending": lambda r: r["state"] in ("SUBMITTED", "DISCREPANCY"), "upcoming": lambda r: 0 <= r["days"] <= 90 and r["state"] not in ("RELEASED", "RENEWED"), "missing": lambda r: bool(r["flags"])}.get(kind)
    if not pick: return nf()
    rows = [r for r in v if pick(r)]
    if request.args.get("fmt") == "csv":
        s = io.StringIO(); w = csv.writer(s); w.writerow(["FDR No", "Institution", "Bank", "Amount", "Maturity", "Days", "State", "Risk", "Flags"])
        for r in rows: w.writerow([r["fdr_number"], r["institution"], r["bank"], r["amount"], r["maturity_date"], r["days"], r["state"], r["risk"], "; ".join(r["flags"])])
        return Response(s.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename={kind}_report.csv"})
    return jsonify(rows)

@bp.get("/api/notifications")
@auth()
def notifs():
    c = db(); q = "SELECT * FROM notifs ORDER BY id DESC LIMIT 100" if g.u["role"] != "institution" else "SELECT * FROM notifs WHERE institution_id=%d ORDER BY id DESC LIMIT 100" % g.u["institution_id"]
    return jsonify([dict(r) | {"fdr_number": (c.execute("SELECT fdr_number FROM fdrs WHERE id=?", (r["fdr_id"],)).fetchone() or {"fdr_number": ""})["fdr_number"]} for r in c.execute(q)])

def metrics(c, v):
    """Measurable-impact figures for the dashboard, computed from workflow data."""
    hrs = []
    for r in v:
        h = c.execute("SELECT action, at FROM history WHERE fdr_id=? ORDER BY id", (r["id"],)).fetchall()
        a = next((x["at"] for x in h if x["action"].endswith("submitted")), None); b = next((x["at"] for x in h if x["action"].startswith("Bank verification")), None)
        if a and b: hrs.append(max(0, (dt.datetime.fromisoformat(b) - dt.datetime.fromisoformat(a)).total_seconds() / 3600))
    live = [r for r in v if r["state"] not in ("RELEASED", "RENEWED")]; due = [r for r in live if r["days"] <= 90]; ids = [r["id"] for r in v] or [0]; q = ",".join("?" * len(ids))
    rem = c.execute(f"SELECT COUNT(*) n FROM notifs WHERE fdr_id IN ({q})", ids).fetchone()["n"]; msgs = c.execute(f"SELECT COUNT(*) n FROM outbox WHERE fdr_id IN ({q})", ids).fetchone()["n"]
    return dict(avg_verify_hours=round(sum(hrs) / len(hrs), 1) if hrs else None, verified_pct=round(100 * sum(r["bank_status"] == "VERIFIED" for r in live) / len(live)) if live else 0,
                issues_flagged=sum(bool(r["flags"]) for r in v), reminders=rem, messages=msgs, reminded_pct=round(100 * sum(r["last_rem"] is not None for r in due) / len(due)) if due else 100,
                hours_saved=round((len(hrs) * 15 + rem * 5) / 60, 1))

@bp.get("/api/outbox")
@auth()
def outbox():
    c = db(); q = "SELECT o.*, f.fdr_number FROM outbox o LEFT JOIN fdrs f ON f.id=o.fdr_id"
    rows = c.execute(q + " WHERE f.institution_id=? ORDER BY o.id DESC LIMIT 100", (g.u["institution_id"],)) if g.u["role"] == "institution" else c.execute(q + " ORDER BY o.id DESC LIMIT 100")
    return jsonify([dict(r) for r in rows])
