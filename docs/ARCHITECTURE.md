# Architecture

```
 Browser (frontend/: HTML + CSS + JS)
        |  HTTPS, JSON, JWT bearer token
        v
 Flask REST API (backend/routes/*)  --- role check on every call (security.py)
        |
        +-- services/fdr_service.py   lifecycle, discrepancy rules, risk score, reminders, escalation
        +-- services/audit.py         hash-chained audit log (SHA-256 of previous entry)
        +-- services/scanner.py       background maturity scan every 6 h
        +-- services/notifier.py      email (SMTP) + SMS (Twilio), outbox log, demo-safe
        +-- services/bank_adapter.py  bank verification adapter (mock now, real API later)
        |
        v
 SQLite database (backend/fdr.db)  <- schema in database.py, demo data in seed.py
 Uploaded documents (backend/uploads/) with SHA-256 integrity hash
 Mock bank registry (table bank_registry) <- replace with real bank API when authorised
```

## Data model (13 tables)
institutions, users, fdrs, docs, history, releases, notifs, audit, bank_registry, settings, outbox

## Key rules
- Submitted vs bank-confirmed data stored separately (`fdrs` columns vs `bank_conf`).
- Discrepancy flags: missing document, maturity <= issue date, amount/date/bank mismatch, not found at bank.
- Risk score 0-100: unverified +30, flags +25, overdue +30 / <=30d +20 / <=90d +10. High risk >= 50.
- Reminders at 90/60/30/7 days; overdue escalation: Regional Officer, then Chairman after 30 days.
- Release approval is blocked unless the FDR is bank-verified with no discrepancy.
- Institution users can only read/write their own institution's records (enforced in the API).

## Production path
SQLite -> PostgreSQL (only database.py and the SQL placeholders change), real bank verification API,
e-mail/SMS gateway in `notify()`, HTTPS, encrypted document storage, AICTE SSO.
