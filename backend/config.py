"""Central configuration (override with environment variables)."""
import os
_env = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
if os.path.exists(_env):  # simple .env loader (no extra dependency)
    for _l in open(_env, encoding="utf-8"):
        _l = _l.strip()
        if _l and not _l.startswith("#") and "=" in _l: _k, _v = _l.split("=", 1); os.environ.setdefault(_k.strip(), _v.strip())
BASE = os.path.dirname(os.path.abspath(__file__))
# Vercel's filesystem is read-only except /tmp (ephemeral: demo data re-seeds on cold start)
_TMP = "/tmp" if os.getenv("VERCEL") else None
DB = os.getenv("DB_PATH", os.path.join(_TMP or BASE, "fdr.db"))
UP = os.path.join(_TMP or BASE, "uploads"); os.makedirs(UP, exist_ok=True)
FRONTEND = os.path.join(BASE, "..", "frontend")
SECRET = os.getenv("SECRET_KEY", "change-me-in-production")
PORT = int(os.getenv("PORT", 8000))
REMINDERS = [90, 60, 30, 7]                     # reminder thresholds (days before maturity)
ALLOWED = (".pdf", ".png", ".jpg", ".jpeg")      # permitted document types
MAX_UPLOAD = 5 * 1024 * 1024                     # 5 MB
