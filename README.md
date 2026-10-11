# Mini CRM

A RESTful CRM API built with Django REST Framework.

Lightweight CRM system for small businesses and sales teams. Track clients, deals, 
activities and analyze your sales pipeline — all in one place.

## Features

### Core
- **Role-based access** — Admin, Manager, Sales Rep and Employee roles with different permissions
- **JWT authentication** — stateless authentication with access and refresh tokens
- **Email verification** — secure registration flow with email confirmation
- **Async tasks** — email sending and archiving via Celery + Redis

### Pipeline & Deals
- **Pipeline management** — track deals through stages: New Lead → Qualification → Proposal Sent → Negotiation → Closed Won / Closed Lost
- **Deal status** — New, In Progress, On Hold, Closed
- **Stage history** — full history of deal stage changes with timestamps and author
- **On Hold** — pause and resume deals; notifications for related activities are automatically cancelled and restored

### Activities
- **Activity types** — calls, emails, meetings, tasks, proposals, contract signings
- **Automated notifications** — get notified 1 hour before activity due date
- **Overdue tracking** — activities past due date without completion are marked as overdue
- **Activity log** — full change history for each activity

### Contacts & Companies
- **Contact management** — track leads and clients with status (Lead, Qualified, Prospect, Active, Dormant, Lost)
- **Lead sources** — track where contacts come from (Instagram, Facebook, Google Ads, LinkedIn, Referral, etc.)
- **Company linking** — associate contacts with companies
- **CSV import/export** — bulk upload contacts via CSV; export contacts and companies to CSV or Excel

### Archive
- **Manual archiving** — manually archive deals, pipelines and activities
- **Automatic archiving** triggered by:
  - Monthly scheduled task — on the 1st of each month, completed deals and their activities older than 1 month are archived
  - User removed from team — all their deals, pipelines and activities are archived
  - Team deleted — all deals, pipelines and activities of team members are archived
  - Product removed from team or deleted — all related deals, pipelines and activities are archived
  - User deleted from the system — all their data is archived
- **Unarchiving** — restore archived data; notifications for unfinished activities are restored if not overdue
- **Archive notifications** — users receive a notification with archive type and list of archived content

### Analytics
Analytics scope depends on role: Admin sees company-wide data and per-team/per-user breakdown; Manager sees own team and per Sales Rep; Sales Rep sees own data only.

**Deals analytics:**
- Total deals count
- Per stage: count, on hold count, total amount, conversion rate
- Won / Lost deals count
- Overall conversion rate (% won from total)
- Average amount of won deals
- Average deal duration (from creation to close)

**Activities analytics:**
- Total count
- Completed count
- Overdue count
- Per activity type: total, completed, overdue
- Average activities per won deal

**Contacts analytics:**
- Total contacts count
- New contacts per week / month
- Count per ContactStatus
- Count per LeadSource + closed deals per LeadSource

**Team analytics:**
- Per team: total deals, won deals, conversion rate, average won deal amount, completed activities, overdue activities, average activities per won deal, average deal duration

### Reports & Export
- Export deals, contacts and activities to CSV or Excel with filters
- Reports include related data (pipeline name, assigned user, contact, company)

---

## Tech Stack

- **Backend:** Django, Django REST Framework
- **Database:** PostgreSQL
- **Authentication:** JWT (djangorestframework-simplejwt)
- **Task Queue:** Celery + Redis
- **Documentation:** drf-spectacular (Swagger UI / ReDoc)

---

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL
- Redis
- Docker (optional)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/OlenaTsar/miniCRM.git
cd miniCRM/CRM
```

2. Create and activate virtual environment:
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file (see `.env.example`):
```bash
cp .env.example .env
```

5. Apply migrations:
```bash
python manage.py migrate
```

6. Run the development server:
```bash
python manage.py runserver
```

---

## Environment Variables

| Variable | Description | Example                     |
|---|---|-----------------------------|
| `SECRET_KEY` | Django secret key | `your-secret-key`           |
| `DEBUG` | Debug mode | `True`                      |
| `DB_NAME` | Database name | `minicrm`                   |
| `DB_USER` | Database user | `postgres`                  |
| `DB_PASSWORD` | Database password | `password`                  |
| `DB_HOST` | Database host | `localhost`                 |
| `DB_PORT` | Database port | `5432`                      |
| `JWT_ACCESS_LIFETIME` | JWT access token lifetime in minutes | `30`                        |
| `FRONTEND_URL` | Frontend URL for email links | `http://localhost:3000`     |

---

## Running Services

```bash
# Django server
python manage.py runserver

# Celery worker
celery -A CRM worker --loglevel=info --pool=solo

# Celery beat (scheduled tasks)
celery -A CRM beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler

# Redis (via Docker)
docker run -d -p 6379:6379 redis:alpine
```

---

## Running Tests

```bash
# run all tests
pytest

# with coverage report
pytest --cov=. --cov-report=term-missing
```

---
## API Overview

### Authentication
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register/` | Register a new user |
| GET | `/api/auth/verify-email/{token}/` | Verify email |
| POST | `/api/auth/login/` | Login, returns JWT tokens |
| POST | `/api/auth/token/refresh/` | Refresh access token |
| POST | `/api/auth/logout/` | Logout, blacklists refresh token |
| POST | `/api/auth/password-reset/` | Request password reset |
| POST | `/api/auth/password-reset/confirm/{token}/` | Confirm password reset |

### Users
| Method | Endpoint | Admin | Manager | Sales Rep |
|---|---|---|---|---|
| GET | `/api/users/` | ✅ | ✅ own team | ❌ |
| GET | `/api/users/{id}/` | ✅ | ✅ own team | ❌ |
| PATCH | `/api/users/{id}/` | ✅ | ✅ own team | ❌ |
| DELETE | `/api/users/{id}/` | ✅ | ❌ | ❌ |
| GET | `/api/users/me/` | ✅ | ✅ | ✅ |
| PATCH | `/api/users/me/` | ✅ | ✅ | ✅ |

### Teams
| Method | Endpoint | Admin | Manager | Sales Rep |
|---|---|---|---|---|
| GET | `/api/teams/` | ✅ | ✅ own team | ❌ |
| POST | `/api/teams/` | ✅ | ❌ | ❌ |
| GET | `/api/teams/{id}/` | ✅ | ✅ own team | ❌ |
| PATCH | `/api/teams/{id}/` | ✅ | ✅ own team | ❌ |
| DELETE | `/api/teams/{id}/` | ✅ | ❌ | ❌ |
| POST | `/api/teams/{id}/add-user/` | ✅ | ❌ | ❌ |
| POST | `/api/teams/{id}/remove-user/` | ✅ | ✅ own team | ❌ |
| POST | `/api/teams/{id}/add-product/` | ✅ | ✅ own team | ❌ |
| POST | `/api/teams/{id}/remove-product/` | ✅ | ✅ own team | ❌ |

### Contacts
| Method | Endpoint | Admin | Manager | Sales Rep |
|---|---|---|---|---|
| GET | `/api/contacts/` | ✅ | ✅ | ✅ |
| POST | `/api/contacts/` | ✅ | ✅ | ✅ |
| GET | `/api/contacts/{id}/` | ✅ | ✅ | ✅ |
| PATCH | `/api/contacts/{id}/` | ✅ | ✅ | ✅ |
| DELETE | `/api/contacts/{id}/` | ✅ | ✅ | ✅ |
| POST | `/api/contacts-import/` | ✅ | ✅ | ✅ |
| GET | `/api/contacts-export/` | ✅ | ✅ | ✅ |

### Companies
| Method | Endpoint | Admin | Manager | Sales Rep |
|---|---|---|---|---|
| GET | `/api/companies/` | ✅ | ✅ | ✅ |
| POST | `/api/companies/` | ✅ | ✅ | ✅ |
| GET | `/api/companies/{id}/` | ✅ | ✅ | ✅ |
| PATCH | `/api/companies/{id}/` | ✅ | ✅ | ✅ |
| DELETE | `/api/companies/{id}/` | ✅ | ✅ | ✅ |
| POST | `/api/companies/{id}/add-contact/` | ✅ | ✅ | ✅ |
| POST | `/api/companies/{id}/remove-contact/` | ✅ | ✅ | ✅ |

### Products
| Method | Endpoint | Admin | Manager | Sales Rep |
|---|---|---|---|---|
| GET | `/api/products/` | ✅ | ✅ | ✅ |
| POST | `/api/products/` | ✅ | ✅ | ❌ |
| GET | `/api/products/{id}/` | ✅ | ✅ | ✅ |
| PATCH | `/api/products/{id}/` | ✅ | ✅ | ❌ |
| DELETE | `/api/products/{id}/` | ✅ | ✅ | ❌ |

### Pipelines
| Method | Endpoint | Admin | Manager | Sales Rep |
|---|---|---|---|---|
| GET | `/api/pipelines/` | ✅ | ✅ own team | ✅ own |
| POST | `/api/pipelines/` | ✅ | ✅ | ✅ |
| GET | `/api/pipelines/{id}/` | ✅ | ✅ own team | ✅ own |
| PATCH | `/api/pipelines/{id}/` | ✅ | ✅ own team | ✅ own |
| DELETE | `/api/pipelines/{id}/` | ✅ | ✅ own team | ✅ own |

### Deals
| Method | Endpoint | Admin | Manager | Sales Rep |
|---|---|---|---|---|
| GET | `/api/deals/` | ✅ | ✅ own team | ✅ own |
| POST | `/api/deals/` | ✅ | ✅ | ✅ |
| GET | `/api/deals/{id}/` | ✅ | ✅ own team | ✅ own |
| PATCH | `/api/deals/{id}/` | ✅ | ✅ own team | ✅ own |
| DELETE | `/api/deals/{id}/` | ✅ | ✅ own team | ✅ own |
| POST | `/api/deals/{id}/change-stage/` | ✅ | ✅ own team | ✅ own |
| POST | `/api/deals/{id}/hold/` | ✅ | ✅ own team | ✅ own |
| GET | `/api/deals/{id}/stage-history/` | ✅ | ✅ own team | ✅ own |

### Activities
| Method | Endpoint | Admin | Manager | Sales Rep |
|---|---|---|---|---|
| GET | `/api/activities/` | ✅ | ✅ own team | ✅ own |
| POST | `/api/activities/` | ✅ | ✅ | ✅ |
| GET | `/api/activities/{id}/` | ✅ | ✅ own team | ✅ own |
| PATCH | `/api/activities/{id}/` | ✅ | ✅ own team | ✅ own |
| DELETE | `/api/activities/{id}/` | ✅ | ✅ own team | ✅ own |
| POST | `/api/activities/{id}/mark-as-completed/` | ✅ | ✅ own team | ✅ own |
| GET | `/api/activities/{id}/activity-log/` | ✅ | ✅ own team | ✅ own |

### Notifications
| Method | Endpoint | Admin | Manager | Sales Rep |
|---|---|---|---|---|
| GET | `/api/notifications/` | ✅ own | ✅ own | ✅ own |
| GET | `/api/notifications/{id}/` | ✅ own | ✅ own | ✅ own |
| DELETE | `/api/notifications/{id}/` | ✅ own | ✅ own | ✅ own |
| POST | `/api/notifications/{id}/mark-as-read/` | ✅ own | ✅ own | ✅ own |

### Activity Scripts
| Method | Endpoint | Admin | Manager | Sales Rep |
|---|---|---|---|---|
| GET | `/api/activity-scripts/` | ✅ | ✅ | ✅ |
| POST | `/api/activity-scripts/` | ✅ | ✅ | ✅ |
| GET | `/api/activity-scripts/{id}/` | ✅ | ✅ | ✅ |
| PATCH | `/api/activity-scripts/{id}/` | ✅ | ✅ own team | ✅ own |
| DELETE | `/api/activity-scripts/{id}/` | ✅ | ✅ own team | ✅ own |

### Analytics
| Method | Endpoint | Admin | Manager | Sales Rep |
|---|---|---|---|---|
| GET | `/api/analytics/dashboard/` | ✅ | ✅ own team | ❌ |
| GET | `/api/analytics/dashboard/my/` | ✅ own | ✅ own | ✅ own |
| GET | `/api/analytics/deals/` | ✅ | ✅ own team | ✅ own |
| GET | `/api/analytics/deals/by-pipeline/` | ✅ | ✅ own team | ✅ own |
| GET | `/api/analytics/deals/by-team/` | ✅ | ❌ | ❌ |
| GET | `/api/analytics/activities/` | ✅ | ✅ own team | ✅ own |
| GET | `/api/analytics/activities/by-pipeline/` | ✅ | ✅ own team | ✅ own |
| GET | `/api/analytics/activities/by-team/` | ✅ | ❌ | ❌ |
| GET | `/api/analytics/contacts/` | ✅ | ✅ own team | ✅ own |
| GET | `/api/analytics/contacts/by-pipeline/` | ✅ | ✅ own team | ✅ own |
| GET | `/api/analytics/contacts/by-team/` | ✅ | ❌ | ❌ |
| GET | `/api/analytics/teams/` | ✅ | ❌ | ❌ |

### Reports
| Method | Endpoint | Admin | Manager | Sales Rep |
|---|---|---|---|---|
| GET | `/api/reports/deals/` | ✅ | ✅ own team | ✅ own |
| GET | `/api/reports/activities/` | ✅ | ✅ own team | ✅ own |
| GET | `/api/reports/contacts/` | ✅ | ✅ | ✅ |

### Archive
| Method | Endpoint | Admin | Manager | Sales Rep |
|---|---|---|---|---|
| GET | `/api/archive/` | ✅ | ✅ own team | ✅ own |
| POST | `/api/archive/` | ✅ | ✅ | ✅ |
| GET | `/api/archive/{id}/` | ✅ | ✅ own team | ✅ own |
| DELETE | `/api/archive/{id}/` | ✅ | ✅ own team | ✅ own |
| POST | `/api/archive/unarchive/` | ✅ | ✅ own team | ✅ own |

### API Documentation
| Endpoint | Description |
|---|---|
| `/api/docs/` | Swagger UI — interactive API documentation |
| `/api/redoc/` | ReDoc — API reference |


## User Roles

| Role | Description                                                                                                   |
|---|---------------------------------------------------------------------------------------------------------------|
| **Admin** | Full access  — manages users, adds them to teams, <br/>creates teams, deals, contacts and has access to everything |
| **Manager** | Manages pipelines, deals, sees full team analytics, <br/>can assign activities and deals to Sales Reps (within own team only)                                                                        |
| **Sales Rep** | Access to own deals, activities, pipelines and own analytics only                                                                                       |
| **Employee** | Newly registered user with no access to anything except own account page                                                                            |

---

## API Documentation

Interactive API documentation is available at:
- **Swagger UI:** `http://localhost:8000/api/docs/`
- **ReDoc:** `http://localhost:8000/api/redoc/`
