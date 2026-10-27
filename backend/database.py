"""Database layer: schema, connection helpers, demo-date handling."""
import sqlite3, datetime as dt
from flask import g
from config import DB

SCHEMA = """
CREATE TABLE IF NOT EXISTS institutions(id INTEGER PRIMARY KEY, name TEXT UNIQUE, email TEXT, phone TEXT);
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE, pw TEXT, role TEXT, institution_id INTEGER, status TEXT DEFAULT 'active');
CREATE TABLE IF NOT EXISTS fdrs(id INTEGER PRIMARY KEY, institution_id INTEGER, bank TEXT, fdr_number TEXT UNIQUE, amount REAL,
  issue_date TEXT, maturity_date TEXT, state TEXT DEFAULT 'SUBMITTED', bank_status TEXT DEFAULT 'UNCHECKED', bank_conf TEXT,
  last_rem INTEGER, renewed_from INTEGER);
CREATE TABLE IF NOT EXISTS docs(id INTEGER PRIMARY KEY, fdr_id INTEGER, name TEXT, sha256 TEXT, path TEXT, at TEXT);
CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY, fdr_id INTEGER, action TEXT, actor TEXT, at TEXT);
CREATE TABLE IF NOT EXISTS releases(id INTEGER PRIMARY KEY, fdr_id INTEGER, reason TEXT, status TEXT DEFAULT 'PENDING', remark TEXT);
CREATE TABLE IF NOT EXISTS notifs(id INTEGER PRIMARY KEY, fdr_id INTEGER, institution_id INTEGER, message TEXT, level TEXT, at TEXT);
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, actor TEXT, action TEXT, at TEXT, prev TEXT, hash TEXT);
CREATE TABLE IF NOT EXISTS bank_registry(fdr_number TEXT PRIMARY KEY, bank TEXT, amount REAL, maturity_date TEXT);
CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS outbox(id INTEGER PRIMARY KEY, fdr_id INTEGER, channel TEXT, recipient TEXT, subject TEXT, body TEXT, status TEXT, detail TEXT, at TEXT);
"""

def conn():
    c = sqlite3.connect(DB, timeout=10); c.row_factory = sqlite3.Row; return c

def db():
    if "db" not in g: g.db = conn()
    return g.db

def close_db(_):
    c = g.pop("db", None)
    if c: c.close()

def setting(c, k, d="0"):
    r = c.execute("SELECT v FROM settings WHERE k=?", (k,)).fetchone(); return r["v"] if r else d

def today(c): return dt.date.today() + dt.timedelta(days=int(setting(c, "offset")))

def D(s): return dt.date.fromisoformat(s)

def now(): return dt.datetime.utcnow().isoformat(timespec="seconds")
