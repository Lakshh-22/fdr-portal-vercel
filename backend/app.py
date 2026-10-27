"""AICTE Security Deposit / FDR Portal: backend entry point.  Run:  python backend/app.py"""
import threading
from flask import Flask
import config
from database import close_db
from seed import init_db
from services.scanner import scanner
from routes import auth, fdrs, workflow, dashboard, admin


def create_app():
    app = Flask(__name__, static_folder=config.FRONTEND, static_url_path="")
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_UPLOAD
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0   # browsers always re-check static files, so updates show immediately
    app.teardown_appcontext(close_db)
    for m in (auth, fdrs, workflow, dashboard, admin): app.register_blueprint(m.bp)

    @app.get("/")
    def index(): return app.send_static_file("index.html")

    init_db(); threading.Thread(target=scanner, daemon=True).start()
    return app


app = create_app()
if __name__ == "__main__": app.run(host="0.0.0.0", port=config.PORT, debug=False)
