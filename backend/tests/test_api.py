"""Run: python backend/tests/test_api.py  (uses a temporary database)"""
import os, sys, tempfile, io
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "t.db")
import app as A
c = A.app.test_client()
def login(u, p): return {"Authorization": "Bearer " + c.post("/api/login", json={"username": u, "password": p}).get_json()["token"]}
off, ins = login("official", "official123"), login("greenfield", "greenfield123")
assert c.post("/api/login", json={"username": "x", "password": "y"}).status_code == 401
assert c.get("/api/fdrs").status_code == 401
d = c.get("/api/dashboard", headers=off).get_json(); print("dashboard", {k: d[k] for k in ("active", "expiring", "matured", "pending", "high_risk")})
fl = {f["fdr_number"]: f for f in c.get("/api/fdrs", headers=off).get_json()}
assert all(f["institution"] == "Greenfield Institute of Technology" for f in c.get("/api/fdrs", headers=ins).get_json()), "institution isolation"
assert c.post(f"/api/fdrs/{fl['IB902114']['id']}/verify", headers=ins).status_code == 403
print("mismatch ->", c.post(f"/api/fdrs/{fl['IB902114']['id']}/verify", headers=off).get_json())
print("not found ->", c.post(f"/api/fdrs/{fl['SBI120045']['id']}/verify", headers=off).get_json())
print("good ->", c.post(f"/api/fdrs/{fl['HD330918']['id']}/verify", headers=off).get_json())
r = c.post("/api/fdrs", headers=ins, json={"bank": "SBI", "fdr_number": "SBI999", "amount": 100000, "issue_date": "2026-10-01", "maturity_date": "2027-10-01"}); assert r.status_code == 201, r.data
nid = r.get_json()["id"]; assert c.post("/api/fdrs", headers=ins, json={"bank": "SBI", "fdr_number": "SBI999", "amount": 1, "issue_date": "2026-10-01", "maturity_date": "2027-10-01"}).status_code == 409
assert c.post(f"/api/fdrs/{nid}/upload", headers=ins, data={"file": (io.BytesIO(b"%PDF fake"), "x.pdf")}, content_type="multipart/form-data").status_code == 201
assert c.post(f"/api/fdrs/{nid}/upload", headers=ins, data={"file": (io.BytesIO(b"x"), "x.exe")}, content_type="multipart/form-data").status_code == 400
bb = fl["BB440276"]["id"]; print("approve ->", c.post(f"/api/fdrs/{bb}/decide_release", headers=off, json={"approve": True}).get_json())
rq = fl["SBI778201"]["id"]; assert c.post(f"/api/fdrs/{rq}/request_release", headers=ins).status_code == 200
assert c.post(f"/api/fdrs/{rq}/decide_release", headers=off, json={"approve": False, "remark": "need docs"}).status_code == 200
rn = c.post(f"/api/fdrs/{rq}/renew", headers=ins, json={"fdr_number": "SBI-R1", "amount": 500000, "maturity_date": "2028-01-01"}); assert rn.status_code == 201, rn.data
print("time shift ->", c.post("/api/time", headers=off, json={"offset": 120}).get_json())
print("notifications:", len(c.get("/api/notifications", headers=off).get_json()))
assert c.get("/api/reports/upcoming?fmt=csv", headers=off).data.startswith(b"FDR No")
print("audit chain intact:", c.get("/api/audit", headers=off).get_json()["intact"])
print("ALL TESTS PASSED")
ad = login("admin", "admin123")
assert c.get("/api/institutions", headers=off).status_code == 200 and c.get("/api/institutions", headers=ins).status_code == 403
assert c.post("/api/institutions", headers=ad, json={"name": "Test College", "username": "tcol", "password": "secret1"}).status_code == 201
iid = [i for i in c.get("/api/institutions", headers=off).get_json() if i["name"] == "Test College"][0]["id"]
assert c.post("/api/fdrs", headers=off, json={"institution_id": iid, "bank": "SBI", "fdr_number": "OFF1", "amount": 1000, "issue_date": "2026-01-01", "maturity_date": "2027-01-01"}).status_code == 201
assert len(c.get("/api/releases", headers=ins).get_json()) >= 1 and "to_verify" in c.get("/api/dashboard", headers=off).get_json()
print("EXTRA TESTS PASSED")

# ---- notifications, outbox, edit, metrics, real SMTP path (fake local mail server) ----
import socketserver, threading
GOT = []
class H(socketserver.StreamRequestHandler):
    def handle(self):
        w = lambda s: (self.wfile.write((s + "\r\n").encode()), self.wfile.flush()); w("220 test ESMTP"); data, buf = False, []
        while True:
            line = self.rfile.readline()
            if not line: break
            l = line.decode(errors="replace").rstrip("\r\n")
            if data:
                if l == ".": GOT.append("\n".join(buf)); data, buf = False, []; w("250 OK")
                else: buf.append(l)
                continue
            u = l.upper()
            if u.startswith(("EHLO", "HELO")): w("250 localhost")
            elif u.startswith("DATA"): data = True; w("354 go")
            elif u.startswith("QUIT"): w("221 bye"); break
            else: w("250 OK")
srv = socketserver.TCPServer(("127.0.0.1", 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
assert c.post("/api/time", headers=off, json={"offset": 0}).status_code == 200
ob = c.get("/api/outbox", headers=off).get_json(); assert ob and all(o["status"] in ("sent", "simulated", "failed") for o in ob); assert c.get("/api/outbox", headers=ins).status_code == 200
m = c.get("/api/dashboard", headers=off).get_json()["metrics"]; print("metrics", m); assert m["avg_verify_hours"] and m["messages"] > 0
assert "desk_email" in c.get("/api/notify_settings", headers=off).get_json()["settings"] and c.get("/api/notify_settings", headers=ins).status_code == 403
assert c.post("/api/notify_settings", headers=off, json={"desk_email": "desk@aicte.example"}).status_code == 200
assert c.put(f"/api/fdrs/{nid}", headers=ins, json={"amount": 120000}).status_code == 200
assert c.put(f"/api/fdrs/{fl['SBI664390']['id']}", headers=off, json={"amount": 1}).status_code == 400
sun = [i for i in c.get("/api/institutions", headers=off).get_json() if i["username"] == "sunrise"][0]["id"]
assert c.put(f"/api/institutions/{sun}", headers=ad, json={"email": "registrar@sunrise.test", "phone": ""}).status_code == 200
os.environ.update(SMTP_HOST="127.0.0.1", SMTP_PORT=str(srv.server_address[1]), SMTP_TLS="0")
assert c.post(f"/api/fdrs/{fl['IB902114']['id']}/verify", headers=off).status_code == 200
rows = [o for o in c.get("/api/outbox", headers=off).get_json() if "sunrise.test" in o["recipient"]]
print("live email ->", rows[0]["status"], rows[0]["recipient"]); assert rows and rows[0]["status"] == "sent" and any("IB902114" in g_ for g_ in GOT), (rows, GOT)
t = c.post("/api/notify_test", headers=off, json={"email": "me@college.test"}).get_json(); print("test msg ->", t); assert t["results"][0]["status"] == "sent"
assert c.post("/api/time", headers=off, json={"offset": 90}).status_code == 200
assert c.get("/api/outbox", headers=off).get_json()[0]["status"] == "simulated", "demo date must never send live"
print("NOTIFICATION TESTS PASSED")

# ---- self-registration with approval ----
ok_ = {"name": "Test Reg College", "email": "reg@testcol.test", "phone": "+919999999999", "username": "regcol", "password": "password1"}
assert c.post("/api/register", json=ok_).status_code == 201
assert c.post("/api/register", json=ok_).status_code == 409
assert c.post("/api/register", json={"name": "Bad", "email": "nope", "username": "x", "password": "1"}).status_code == 400
assert c.post("/api/login", json={"username": "regcol", "password": "password1"}).status_code == 403, "pending users must not sign in"
regs = c.get("/api/registrations", headers=off).get_json(); rid = [x["id"] for x in regs if x["username"] == "regcol"][0]
assert c.get("/api/registrations", headers=ins).status_code == 403
assert "Test Reg College" not in [i["name"] for i in c.get("/api/institutions", headers=off).get_json()]
assert c.get("/api/dashboard", headers=off).get_json()["reg_pending"] >= 1
assert c.post(f"/api/registrations/{rid}/decide", headers=off, json={"approve": True}).status_code == 200
lg = c.post("/api/login", json={"username": "regcol", "password": "password1"}); assert lg.status_code == 200
assert c.get("/api/dashboard", headers={"Authorization": "Bearer " + lg.get_json()["token"]}).get_json()["total"] == 0
assert "Test Reg College" in [i["name"] for i in c.get("/api/institutions", headers=off).get_json()]
assert c.post("/api/register", json=dict(ok_, name="Rejected College", username="rejcol")).status_code == 201
rj = [x["id"] for x in c.get("/api/registrations", headers=off).get_json() if x["username"] == "rejcol"][0]
assert c.post(f"/api/registrations/{rj}/decide", headers=off, json={"approve": False}).status_code == 200
assert c.post("/api/login", json={"username": "rejcol", "password": "password1"}).status_code == 401
assert c.get("/api/audit", headers=off).get_json()["intact"]
print("REGISTRATION TESTS PASSED")
