# AC, TV & Fridge Repair Service — Complete Project

A full-stack home appliance repair platform built exactly to the requirements document:

- **Backend**: Django 5 + Django REST Framework, JWT + OTP auth, SQLite (PostgreSQL-ready), Admin panel
- **Mobile App**: Flutter (single codebase — Customer + Technician modules)
- **Payments**: mock gateway flow (Razorpay/Stripe swap-in points marked)
- **Notifications**: in-app notification system with FCM stubs

## Project Structure

```
repair-service-project/
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── config/               # Django project
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   └── core/                 # Main app
│       ├── __init__.py
│       ├── apps.py
│       ├── models.py         # User, Category, Service, Booking, Payment, Review, Notification
│       ├── serializers.py
│       ├── views.py          # All API endpoints
│       ├── urls.py
│       ├── admin.py          # Full admin panel
│       └── management/
│           ├── __init__.py
│           └── commands/
│               ├── __init__.py
│               └── seed.py   # Seeds categories, services, demo users
├── mobile/                   # Flutter app
│   ├── pubspec.yaml
│   ├── analysis_options.yaml
│   └── lib/
│       ├── main.dart
│       ├── services/api_service.dart
│       ├── state/app_state.dart
│       └── screens/
│           ├── auth.dart          # Splash, Login, Register
│           ├── home.dart          # Home shell + category cards
│           ├── booking_flow.dart  # 5-step booking wizard
│           ├── bookings_screen.dart # Booking list + actions + pay + review
│           └── profile_screen.dart  # Profile, technician status, logout
├── run_backend.sh / run_backend.bat
└── README.md
```

## Quick Start — Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations core
python manage.py migrate
python manage.py seed           # categories + services + demo users
python manage.py runserver
```

API root: `http://127.0.0.1:8000/api/`
Admin panel: `http://127.0.0.1:8000/admin/`

**Demo accounts (created by seed):**

| Role | Username | Password |
|---|---|---|
| Admin | admin | admin123 |
| Customer | customer1 | cust123 |
| Technician | tech1 | tech123 (pre-approved) |

## Quick Start — Flutter App

```bash
cd mobile
flutter pub get
flutter run
```

**API URL**: the app defaults to `http://10.0.2.2:8000` (Android emulator).
For a physical device, run with your computer's LAN IP:

```bash
flutter run --dart-define=API_BASE_URL=http://192.168.x.x:8000
```

## Booking Lifecycle (as per requirements)

Pending → Assigned → Accepted → On the Way → Arrived → In Progress → Completed → Paid → Closed (+ Cancelled / Rejected)

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | /api/auth/register/ | Customer/technician registration |
| POST | /api/auth/login/ | JWT login |
| POST | /api/auth/otp/request/ | Request OTP |
| POST | /api/auth/otp/verify/ | Verify OTP, get JWT |
| GET/PATCH | /api/auth/profile/ | Profile |
| POST | /api/auth/change-password/ | Change password |
| GET | /api/categories/ | Appliance categories + services |
| GET | /api/services/ | Services (filter: ?category=) |
| GET/POST | /api/bookings/ | List / create bookings |
| GET | /api/bookings/{id}/ | Booking detail |
| POST | /api/bookings/{id}/accept/ | Technician accepts |
| POST | /api/bookings/{id}/reject/ | Technician rejects |
| POST | /api/bookings/{id}/on_the_way/ | Status update |
| POST | /api/bookings/{id}/arrived/ | Status update |
| POST | /api/bookings/{id}/start/ | Status update |
| POST | /api/bookings/{id}/complete/ | Status update |
| POST | /api/bookings/{id}/cancel/ | Customer cancels |
| POST | /api/bookings/{id}/assign-technician/ | Admin assigns |
| GET | /api/bookings/{id}/available-technicians/ | Nearby technicians (haversine) |
| POST | /api/bookings/{id}/pay/ | Initiate payment |
| POST | /api/bookings/{id}/pay/confirm/ | Confirm payment |
| POST | /api/reviews/ | Rate technician (post-completion) |
| GET | /api/notifications/ | My notifications |
| POST | /api/notifications/{id}/read/ | Mark read |
| GET | /api/technicians/ | Approved technicians |
| GET/PATCH | /api/technician/profile/ | Technician profile |
| GET | /api/technician/earnings/ | Technician earnings summary |

## Switching to PostgreSQL

Set env vars, no code changes:

```
DB_ENGINE=django.db.backends.postgresql
DB_NAME=repairservice
DB_USER=postgres
DB_PASSWORD=yourpass
DB_HOST=localhost
DB_PORT=5432
```

## Production integrations (clearly marked in code)

- **Payments**: `StartPaymentView` / `ConfirmPaymentView` in `core/views.py` — replace mock checkout with Razorpay/Stripe SDK calls.
- **Push notifications**: `notify()` in `core/models.py` — replace print stub with FCM (`firebase-admin`).
- **SMS OTP**: `RequestOTPView` — connect an SMS provider; in dev the OTP is returned in the response for testing.
- **Maps**: technician assignment uses haversine distance already; add Google Maps SDK in Flutter for map-based location picking.
