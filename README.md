# WAVE.

WAVE is a web application that simplifies event ticketing for college campuses. This app allows users to purchase, manage, and scan tickets for campus events, with features for campus managers and organizations.

## Table of Contents

1. [Features](#features)
2. [Tech Stack](#tech-stack)
3. [Setup and Installation](#setup-and-installation)
4. [Setting up apps](#app-creation)

## Features

- Event ticket purchasing system
- Campus manager dashboard for managing organizations and approving events
- QR code ticket scanning for entry and purchases
- Invite friends to form event groups ("crew")

## Tech Stack

- **Backend:** Django, Python
- **Frontend:** HTML, TailwindCSS, JavaScript
- **Database:** PostgreSQL (Neon - Development, Supabase - Production)
- **Hosting:** Render
- **Payment Processing:** Stripe
- **Mobile App:** React Native

## Setup and Installation

### Prerequisites

Make sure you have the following installed on your machine:

- Python 3.9+
- Django 4.0+
- PostgreSQL (or SQLite for development)
- Git

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

# On Mac
python3 -m venv venv
source venv\bin\activate
```

### Install Dependencies

```python
pip install -r requirements.txt
```

### Create a .env file in the project root and add the required environment variables (Obtain the correct environment variable values from a team member)

```python
# Example of what it should look like
DEBUG=True
DATABASE_URL=postgres://user:password@localhost:5432/dbname
SECRET_KEY=your_secret_key
...
```

### Migrate the Database

```python
python manage.py makemigrations
python manage.py migrate
```

### Create a Superuser

```python
python manage.py createsuperuser
```

### Run development server

```python
python manage.py runserver
```

## App Creation

To start a Django app within the project, you need to use the #startapp command.

1. Navigate to project root directory (where manage.py is located)
2. Create a new app using the startapp command:

```python
python manage.py startapp app_name
```

3. Register the app in the project's settings.py file by adding the app name to the INSTALLED_APPS list:

```python
INSTALLED_APPS = [
  'app_name',
]
```

4. Define models, views, URLs.
   Models: Define your database models in models.py
   Views: Handle the logic in the views.py
   URL's: Add URL routing for your app by creating a urls.py file and linking it to your project's main urls.py

5. Migrate database changes:

```python
python manage.py makemigrations
python manage.py migrate
```

6. Run development server:

```python
python manage.py runserver
```
