# WAVE.

WAVE is a modern web application that simplifies event ticketing for college campuses. This app provides a hybrid Django + FastAPI architecture for web and mobile clients, allowing users to purchase, manage, and scan tickets for campus events, with comprehensive features for campus managers and organizations.

## Table of Contents

1. [Features](#features)
2. [Tech Stack](#tech-stack)
3. [Architecture Overview](#architecture-overview)
4. [API Documentation](#api-documentation)
5. [Setup and Installation](#setup-and-installation)
6. [Setting up apps](#app-creation)

## Features

-   **Event Management System**

    -   Event ticket purchasing and management
    -   QR code ticket scanning for entry and purchases
    -   Invite friends to form event groups ("crew")
    -   Real-time event updates and notifications

-   **Campus Administration**

    -   Campus manager dashboard for managing organizations
    -   Event approval workflows
    -   User management and role-based access control
    -   Analytics and reporting

-   **Modern API Architecture**
    -   FastAPI REST endpoints for mobile and web clients
    -   JWT-based authentication with refresh tokens
    -   Role-based access control middleware
    -   Real-time monitoring with OpenTelemetry
    -   Version checking for mobile app compatibility

## Tech Stack

-   **Backend Framework:** Django 5.1+ (Web) + FastAPI (API)
-   **Language:** Python 3.9+
-   **Frontend:** HTML, TailwindCSS, JavaScript
-   **Database:** PostgreSQL (Neon - Development, Supabase - Production)
-   **Authentication:** JWT tokens with refresh token rotation
-   **Real-time:** Django Channels + Redis
-   **Monitoring:** OpenTelemetry with distributed tracing
-   **Payment Processing:** Stripe
-   **File Storage:** AWS S3 via Django Storages
-   **Hosting:** Render
-   **Mobile App:** React Native
-   **Task Queue:** Celery with Redis
-   **Caching:** Redis

## Architecture Overview

WAVE uses a hybrid architecture combining Django and FastAPI:

### Django Web Application

-   Traditional Django views for web interface
-   Admin dashboard and content management
-   User authentication and session management
-   Template rendering with Tailwind CSS

### FastAPI API Layer

-   Modern REST API for mobile and web clients
-   Located in `apiManager/` directory
-   Modular app-based organization
-   Async/await support with Django ORM integration

### API Apps Structure

```
apiManager/
├── main.py                 # FastAPI application entry point
├── dependencies.py         # JWT authentication dependencies
├── middleware/            # Custom middleware (admin access, etc.)
├── apps/
│   ├── authenticationAPI/  # Login, logout, registration
│   ├── coreAPI/           # Events, categories, favorites
│   ├── accountManagementAPI/ # User profiles, settings
│   ├── eventManagementAPI/   # Event creation, management
│   ├── eventTicketsAPI/      # Ticket purchasing, RSVP
│   ├── socialAPI/           # Crew system, friend requests
│   ├── adminManagementAPI/   # Admin dashboard APIs
│   └── collegeManagementAPI/ # College/campus management
└── utilities/             # Shared utilities and helpers
```

## API Documentation

The FastAPI implementation provides automatically generated documentation:

-   **Interactive API Docs:** `/docs` (Swagger UI)
-   **Alternative Docs:** `/redoc` (ReDoc)
-   **OpenAPI Schema:** `/openapi.json`

### Key API Features

-   **Authentication Endpoints** (`/waveYourCampusAPIFromOAK/auth`)

    -   Login/logout with JWT tokens
    -   User registration and email verification
    -   Admin access validation

-   **Core Event APIs** (`/waveYourCampusAPIFromOAK/core`)

    -   Event discovery and search
    -   Event details and host profiles
    -   Favorites and RSVP management

-   **Social Features** (`/waveYourCampusAPIFromOAK/social`)

    -   Crew creation and management
    -   Friend requests and connections
    -   Social recommendations

-   **Ticket Management** (`/waveYourCampusAPIFromOAK/ticket`)
    -   Ticket purchasing with Stripe
    -   QR code generation
    -   Entry scanning and validation

### Authentication

The API uses JWT tokens with the following features:

-   Access tokens (6 months expiry)
-   Refresh tokens (1 year expiry)
-   Role-based access control
-   Automatic token refresh
-   Mobile app version checking

## Setup and Installation

### Prerequisites

Make sure you have the following installed on your machine:

-   Python 3.9+
-   Django 5.1+
-   FastAPI 0.115+
-   PostgreSQL (or SQLite for development)
-   Redis (for Celery and Channels)
-   Git

### Clone the Repository

```bash
git clone https://github.com/username/wave.git
cd wave
```

### Virtual Environment Setup

```python
# On Windows
python -m venv venv
venv\Scripts\activate

# On Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

### Install Dependencies

```python
pip install -r requirements.txt
```

### Environment Configuration

Create a `.env` file in the project root and add the required environment variables:

```python
# Django Settings
DEBUG=True
SECRET_KEY=your_secret_key
DATABASE_URL=postgres://user:password@localhost:5432/dbname

# FastAPI JWT Settings
ALGORITHM=HS256

# Redis Configuration
REDIS_URL=redis://localhost:6379

# Stripe Configuration
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...

# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_STORAGE_BUCKET_NAME=your_bucket_name

# OpenTelemetry Monitoring
OTEL_EXPORTER_OTLP_ENDPOINT=https://your-otel-endpoint
OTEL_EXPORTER_OTLP_AUTHORIZATION=your_auth_token

# Admin Access
SECRET_ADMIN_URL=your_admin_url
SECRET_ADMIN_KEY=your_admin_key
SECRET_ADMIN_USER=admin@example.com
```

### Database Setup

```python
# Create and apply migrations
python manage.py makemigrations
python manage.py migrate

# Create a superuser
python manage.py createsuperuser
```

### Development Servers

#### Start Django Web Server

```python
python manage.py runserver
```

#### Start FastAPI Server (Development)

```python
# Install uvicorn if not already installed
pip install uvicorn

# Run FastAPI directly
uvicorn apiManager.main:app --reload --port 8001
```

#### Start Background Services

```python
# Start Redis server (required for Celery and Channels)
redis-server

# Start Celery worker (in separate terminal)
celery -A wave_v1 worker --loglevel=info

# Start Celery beat (for scheduled tasks)
celery -A wave_v1 beat --loglevel=info
```

### Production Deployment

For production deployment, the FastAPI app is typically served alongside Django using:

-   Gunicorn with Uvicorn workers
-   Nginx as reverse proxy
-   Environment-specific configuration

## App Creation

To start a Django app within the project:

1. **Create Django App:**

```python
python manage.py startapp app_name
```

2. **Create FastAPI Module:**

```python
# Create directory structure
mkdir -p apiManager/apps/app_nameAPI
touch apiManager/apps/app_nameAPI/__init__.py
touch apiManager/apps/app_nameAPI/apiLogic.py
touch apiManager/apps/app_nameAPI/serializers.py
```

3. **Register Django App:**

```python
# In wave_v1/settings.py
INSTALLED_APPS = [
    'app_name',
    # ... other apps
]
```

4. **Create FastAPI Router:**

```python
# In apiManager/apps/app_nameAPI/apiLogic.py
from fastapi import APIRouter, Depends
from apiManager.dependencies import get_current_user

router = APIRouter()

@router.get("/ping")
async def ping():
    return {"message": "App API is running!"}
```

5. **Register API Router:**

```python
# In apiManager/main.py
from apiManager.apps.app_nameAPI.apiLogic import router as app_name_router

app.include_router(
    app_name_router,
    prefix="/waveYourCampusAPIFromOAK/app_name",
    tags=["App Name"]
)
```

6. **Apply Database Changes:**

```python
python manage.py makemigrations
python manage.py migrate
```

7. **Test Your Implementation:**

```python
# Start both servers and test
python manage.py runserver  # Django web interface
uvicorn apiManager.main:app --reload --port 8001  # FastAPI docs at localhost:8001/docs
```
