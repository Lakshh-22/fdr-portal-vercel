"""Email (SMTP) and SMS (Twilio) delivery with an outbox log.
Live sending happens only when credentials are configured, the demo date is not shifted, and the recipient is not a demo contact.
Otherwise the message is recorded as 'simulated' so the full flow can still be demonstrated."""
import os, ssl, smtplib, base64, urllib.request, urllib.parse
from email.message import EmailMessage
from database import setting, now


def channels():
    return {"email": bool(os.getenv("SMTP_HOST")), "sms": bool(os.getenv("TWILIO_SID") and os.getenv("TWILIO_TOKEN") and os.getenv("TWILIO_FROM"))}


def is_demo_addr(x): return x.lower().endswith(".example") or x.startswith("+910000")


def send_email(to, subject, body):
    host, user = os.getenv("SMTP_HOST"), os.getenv("SMTP_USER")
    m = EmailMessage(); m["From"] = os.getenv("SMTP_FROM", user or "fdr-portal@localhost"); m["To"] = to; m["Subject"] = subject; m.set_content(body)
    with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "587")), timeout=15) as s:
        if os.getenv("SMTP_TLS", "1") == "1": s.starttls(context=ssl.create_default_context())
        if user: s.login(user, os.getenv("SMTP_PASS", ""))
        s.send_message(m)


def send_sms(to, body):  # Twilio REST API; swap this function for MSG91 / Fast2SMS if preferred
    sid, tok = os.getenv("TWILIO_SID"), os.getenv("TWILIO_TOKEN")
    req = urllib.request.Request(f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json", data=urllib.parse.urlencode({"To": to, "From": os.getenv("TWILIO_FROM"), "Body": body[:300]}).encode())
    req.add_header("Authorization", "Basic " + base64.b64encode(f"{sid}:{tok}".encode()).decode()); urllib.request.urlopen(req, timeout=15).read()


def _send(c, fid, ch, to, subject, body, demo):
    if demo: st, d = "simulated", "demo date active"
    elif is_demo_addr(to): st, d = "simulated", "demo contact"
    elif not channels()[ch]: st, d = "simulated", "channel not configured"
    else:
        try: (send_email(to, subject, body) if ch == "email" else send_sms(to, body)); st, d = "sent", ""
        except Exception as e: st, d = "failed", str(e)[:200]
    c.execute("INSERT INTO outbox(fdr_id,channel,recipient,subject,body,status,detail,at) VALUES(?,?,?,?,?,?,?,?)", (fid, ch, to, subject, body, st, d, now()))
    return st, d


def dispatch(c, fid, subject, body, sms, recips):
    demo = int(setting(c, "offset")) != 0
    for label, email, phone in recips:
        if email: _send(c, fid, "email", f"{email}", subject, body, demo)
        if phone: _send(c, fid, "sms", f"{phone}", subject, sms, demo)


def send_now(c, ch, to, subject, body): return _send(c, None, ch, to, subject, body, False)
