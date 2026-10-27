# API (all except /api/login need `Authorization: Bearer <token>`)
| Method | Path | Roles | Purpose |
|---|---|---|---|
| POST | /api/login | public | JWT login |
| GET | /api/dashboard | all | counts, charts data, top-risk FDRs |
| GET/POST | /api/fdrs | all (own scope) | list/search, create (official must pass institution_id) |
| GET | /api/fdrs/{id} | all (own scope) | detail with history, documents, flags |
| POST | /api/fdrs/{id}/upload | all | multipart `file` (pdf/png/jpg, 5 MB), stores SHA-256 |
| POST | /api/fdrs/{id}/verify | official, admin | mock bank verification |
| POST | /api/fdrs/{id}/remark | official, admin | scrutiny remark |
| POST | /api/fdrs/{id}/renew | institution | renewal / replacement |
| POST | /api/fdrs/{id}/request_release | institution | release/refund request (VERIFIED only) |
| POST | /api/fdrs/{id}/decide_release | official, admin | approve/reject |
| GET | /api/releases | all (own scope) | release requests |
| GET | /api/reports/{pending,upcoming,missing}[?fmt=csv] | all (own scope) | reports |
| GET | /api/notifications | all (own scope) | reminders and escalations |
| POST | /api/scan | official, admin | run maturity scan now |
| POST | /api/time | official, admin | demo date shift (0-400 days) |
| GET | /api/audit | official, admin | audit log + chain integrity |
| GET/POST | /api/institutions | official, admin / admin | list, onboard institution + login |
| PUT | /api/fdrs/{id} | owner / official | edit an unverified FDR (resets verification) |
| GET | /api/outbox | all (own scope) | email/SMS delivery log |
| GET/POST | /api/notify_settings | official, admin | desk / Regional Officer / Chairman contacts, channel status |
| POST | /api/notify_test | official, admin | send a test email / SMS |
| GET | /api/my_contact | institution | own contact details |
| PUT | /api/institutions/{id} | admin, own institution | update contact email / phone |
| POST | /api/register | public | institution self-registration (pending approval, rate-limited) |
| GET | /api/registrations | official, admin | pending registrations |
| POST | /api/registrations/{institution_id}/decide | official, admin | `{approve: true/false}` |
