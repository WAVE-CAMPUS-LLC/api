# WAVE Event Ticketing App

WAVE is a web application that simplifies event ticketing for college campuses. This app allows users to purchase, manage, and scan tickets for campus events, with features for campus managers and organizations.

## Table of Contents
1. [Features](#features)
2. [Tech Stack](#tech-stack)
3. [Setup and Installation](#setup-and-installation)
4. [Usage](#usage)
5. [Contribution Guidelines](#contribution-guidelines)
6. [License](#license)

## Features
- Event ticket purchasing system
- Campus manager dashboard for managing organizations and approving events
- QR code ticket scanning for entry and purchases
- Invite friends to form event groups ("crew")

## Tech Stack
- **Backend:** Django, Python
- **Frontend:** HTML, TailwindCSS, JavaScript
- **Database:** PostgreSQL (or SQLite for development)
- **Mobile App:** React Native (planned)
- **Others:** AJAX, (for future integration)

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


