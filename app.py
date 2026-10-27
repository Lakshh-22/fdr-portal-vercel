"""Vercel entry point (root app.py is auto-detected as the Flask app).
Loads the real app from backend/app.py so your local `python backend/app.py` still works unchanged."""
import os, sys, importlib.util
_B = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
sys.path.insert(0, _B)
_spec = importlib.util.spec_from_file_location("fdr_backend_app", os.path.join(_B, "app.py"))
_m = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_m)
app = _m.app
 