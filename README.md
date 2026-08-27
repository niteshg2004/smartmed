# SmartMed

Medicine availability, stock prediction & safe alternative assistance system .

> **Status: Phase 1 complete** (project skeleton, full database schema, authentication + RBAC).
> Phases 2–10 (search, maps, inventory, ML, alternatives, OCR, dashboards, tests, docs) are being
> built incrementally — see `docs/PLAN.md` in this repo for the phase breakdown.

SmartMed is a **decision-support and availability platform** — it is not a medical diagnosis system
and never recommends medicine substitutions without professional (doctor/pharmacist) confirmation.

---

## 1. Requirements

- Python 3.12+
- pip / venv
- (Optional) PostgreSQL 14+ if you don't want to use the default SQLite database
- (Later phases) Tesseract OCR binary installed on your system for prescription OCR

## 2. Setup

```bash
# 1. Clone / enter the project
cd smartmed

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env and set a real SECRET_KEY (any long random string is fine for local dev).
# Leave DATABASE_URL blank to use SQLite (recommended for grading/demo).

# 5. Run database migrations
python manage.py makemigrations
python manage.py migrate

# 6. Load demo data (creates one admin, two pharmacy, one patient account)
python manage.py seed_demo_data

# 7. (Optional) create your own superuser instead of / in addition to the seeded admin
python manage.py createsuperuser

# 8. Train the ML stock-prediction model — available starting Phase 5
# python manage.py train_stock_model

# 9. Start the development server
python manage.py runserver

# 10. Run tests
python manage.py test tests accounts medicines pharmacies inventory prescriptions alternatives predictions
# or, equivalently, with pytest:
pytest
```

Then open **http://127.0.0.1:8000/** in your browser.

## 3. Demo accounts (created by `seed_demo_data`)

| Role | Email | Password |
|---|---|---|
| Admin/Pharmacist | admin@smartmed.demo | SmartMed@Demo123 |
| Pharmacy | pharmacy1@smartmed.demo | SmartMed@Demo123 |
| Pharmacy | pharmacy2@smartmed.demo | SmartMed@Demo123 |
| Patient | patient1@smartmed.demo | SmartMed@Demo123 |

Django admin is available at `/admin/` for the admin account.

## 4. What exists right now (Phase 1)

- Full database schema for every model in the spec: `User`, `Pharmacy`, `Medicine`, `Inventory`,
  `InventoryHistory`, `AlternativeCandidate`, `Prescription`, `PrescriptionMedicine`,
  `SearchHistory`, `AvailabilityRequest` — with proper FKs, indexes, and constraints.
- Custom `User` model: email-based login, three roles (`patient`, `pharmacy`, `admin`), custom
  RBAC permissions (`can_verify_alternatives`, `can_manage_medicines`, `can_manage_users`,
  `can_import_data`).
- Working authentication: server-rendered register/login/logout pages **and** a JSON API
  (`/api/v1/auth/register|login|logout|me/`) using DRF TokenAuthentication, with throttling on
  auth endpoints and password strength validation. Admin accounts cannot self-register through
  either surface.
- Shared DRF permission classes (`IsPatient`, `IsPharmacyRole`, `IsAdminRole`, `IsOwnerOrAdmin`,
  `IsOwnerPharmacyOrAdmin`) ready for every later app to reuse — including IDOR protection so
  e.g. one pharmacy can never edit another pharmacy's inventory.
- Role-routed dashboards for patients, pharmacy owners, and admins with live search, prescription,
  inventory, availability-request, analytics, and alternative-verification links.
- Consistent API error envelope (`smartmed/exceptions.py`).
- `seed_demo_data` management command (grows in later phases to add medicines/pharmacies/inventory).
- Automated tests for registration, login, RBAC role restriction, and URL/model registry smoke
  tests (`accounts/tests.py`, `tests/test_smoke.py`).

## 5. Project structure

```
smartmed/
├── manage.py
├── requirements.txt
├── .env.example
├── smartmed/           # project settings, root urls, wsgi/asgi, env loader, exception handler
├── accounts/           # custom User model, auth (web + API), RBAC permissions, seed command
├── medicines/          # Medicine, SearchHistory models (fuzzy search added Phase 2)
├── pharmacies/         # Pharmacy model (map/geocoding added Phase 3)
├── inventory/          # Inventory, InventoryHistory, AvailabilityRequest (logic added Phase 4)
├── prescriptions/      # Prescription, PrescriptionMedicine models (OCR pipeline added Phase 7)
├── alternatives/       # AlternativeCandidate model (matching + verification added Phase 6)
├── predictions/        # stock-out prediction API (added Phase 5, backed by ml/)
├── dashboard/          # role-routed dashboard views/templates
├── ml/                 # train.py / predict.py / preprocessing.py / models/ (added Phase 5)
├── data/demo/          # generated demo CSV/fixtures (added Phase 5)
├── data/imports/       # admin CSV import staging (added Phase 5/6)
├── templates/          # base template + per-app templates
├── static/             # CSS/JS
└── tests/              # project-wide smoke tests
```

## 6. A note on this environment

This codebase was written directly to disk in a sandboxed environment **without internet access**,
so `pip install` could not run here and the commands above have not been executed against a real
Django install in this session — they're written to correct, standard Django 5.x conventions but
you should run the Setup steps above yourself and report back anything that errors so it can be
fixed immediately.

## 7. Data & privacy notes

- All demo pharmacy/inventory data is explicitly flagged `is_demo_data=True` in the database and
  will be labeled "DEMO DATA" in the UI/API once those views are built (Phase 4–5) — never
  presented as real pharmacy stock.
- Prescription files are stored under randomized, non-guessable paths and are only ever served
  through owner-checked, authenticated views (never as a public static/media URL) — see
  `prescriptions/models.py`.
- `PRESCRIPTION_RETENTION_DAYS` (in `.env`) controls how long raw prescription images are kept;
  a cleanup command will be added when the OCR pipeline (Phase 7) lands.
