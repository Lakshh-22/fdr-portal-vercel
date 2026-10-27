# AICTE Security Deposit / FDR Management Portal (SIH 26265)

```
fdr-portal/
├── backend/                 Flask REST API
│   ├── app.py               entry point (app factory)
│   ├── config.py            settings / environment variables
│   ├── database.py          schema + DB helpers
│   ├── security.py          JWT auth + role-based access
│   ├── seed.py              first-run demo data (8 institutions, 22 FDRs)
│   ├── routes/              auth, fdrs, workflow, dashboard, admin
│   ├── services/            fdr_service (rules, risk, scan), notifier (email/SMS), bank_adapter, audit, scanner
│   └── tests/test_api.py    API + SMTP tests
├── frontend/                web UI (no build step)
│   ├── index.html
│   ├── css/style.css
│   └── js/                  core, pages, modals, main
├── docs/                    ARCHITECTURE.md, API.md
├── tests/ui_smoke.js        renders every page for every role (needs server running)
├── requirements.txt · Procfile · .env.example
```

## Run (VS Code terminal, from this folder)
```
python -m venv .venv
.venv\Scripts\activate          (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python backend/app.py           ->  http://localhost:8000
```
Tests: `python backend/tests/test_api.py` (expects ALL TESTS PASSED).
Reset demo data: stop server, delete `backend/fdr.db`, start again.

## Demo logins (all institutions are FICTIONAL)
| Role | Login | Can do |
|---|---|---|
| Regulation Official | `official / official123` | verify, remarks, approve/reject release, add FDR for any institution, reports, audit, notification contacts, demo date |
| Admin | `admin / admin123` | all of the above + onboard institutions and edit their contact details |
| Institution | `greenfield / greenfield123` (also riverside, lakeview, sunrise, hilltop, northgate, eastwood, westbrook: `<name>123`) | add/edit own unverified FDR, upload, renew, request release, set own contact; sees only own data |

## New: registration, themes, OCR
- **Self-registration:** login page > *Register here*. The institution cannot sign in until an Official/Admin approves it on **Institutions > Registration requests** (rejecting deletes the request so the institution can re-apply). Registrant and verification desk get an email (simulated until SMTP is set). There is no email-ownership verification or CAPTCHA yet (basic per-IP rate limit only); mention this as future scope.
- **Light / Dark theme:** toggle in the top bar and on the login page; the choice is remembered (defaults to your system setting).
- **OCR:** *FDR Management > + Add FDR > choose a JPG/PNG/PDF*. Bank, FDR number, amount, issue date and maturity date are read from the document and filled in (verify before submitting). Runs in the browser (Tesseract.js, pdf.js), so it needs internet the first time to download the OCR engine; digital PDFs are read directly, scanned PDFs/photos via OCR. If OCR cannot read the file it falls back to the file name (`FDR_SBI_778299_500000.pdf`). Try `docs/samples/sample_fdr_receipt.png`. Accuracy depends on scan quality; always check the filled values.
- Tests: `node tests/ocr_parse.js` (parser; verified against real Tesseract output), `node tests/ui_smoke.js` (server running).

## Email / SMS alerts
- Triggers: reminders at 90/60/30/7 days before maturity, overdue escalation (Regional Officer, then Chairman after 30 days), new submission (to verification desk), verification mismatch and release decisions (to the institution).
- Recipients: institution contact + verification desk (+ Regional Officer / Chairman on escalation). Edit them on the **Notifications** page.
- **Go live:** copy `.env.example` to `.env`, fill SMTP (and/or Twilio) values, restart. Use **Notifications > Send test message** to check.
- Safety: while the *Demo date* slider is not at today, or for `.example` demo contacts, messages are only *simulated* (logged, never sent). Without credentials everything is simulated, and the delivery log shows exactly what would be sent.
- SMTP code is tested against a local mail server in `backend/tests/test_api.py`; the Twilio call is untested against the real service.

## Expected outcomes covered (PS 26265)
Repository, document management, verification + discrepancy detection, validity/maturity tracking, renewal history, release workflow, alerts + escalation (in-app, email, SMS), dashboard + reports, audit trail + access control, integration-ready bank adapter (`services/bank_adapter.py`). The dashboard also reports measurable impact: verification turnaround, share of bank-verified records, issues flagged automatically, reminders issued, estimated staff time saved (baseline and time-saving figures are stated assumptions; replace with AICTE figures).

## Host (Render.com)
Push to GitHub -> New Web Service. Build: `pip install -r requirements.txt`. Start: `gunicorn --chdir backend app:app --workers 1 --threads 4`. Env: `SECRET_KEY`.
Free tier: sleeps when idle, data resets on redeploy (demo data reloads automatically). For persistence attach a disk and set `DB_PATH`.

## Real vs simulated
Real: auth/roles, workflow, discrepancy rules, scanner, release rules, audit chain, document hashing.
Simulated until configured: bank verification (registry table behind an adapter), OCR (filename: `FDR_SBI_778299_500000.pdf`), email/SMS (live once SMTP/Twilio are set).
