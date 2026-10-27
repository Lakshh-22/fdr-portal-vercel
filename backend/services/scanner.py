"""Background maturity scanner (runs every 6 hours)."""
import time
from database import conn
from services.fdr_service import scan

def scanner():
    while True:
        time.sleep(6 * 3600)
        try: c = conn(); scan(c); c.close()
        except Exception: pass
