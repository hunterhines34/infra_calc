# Project Setup Guide

This will allow you to run the project locally.

## Prerequisites

- Python 3.10 or higher
- pip (Python package installer)

## Installation Steps

### 1. Clone the Repository

```bash
mkdir infrastructure_calc
cd infrastructure_calc
git clone https://github.com/hunterhines34/infrastructure_calc.git
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate
```

OR on Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Setup .env file
Create a .env file in the root directory and add the following variables:

```
SECRET_KEY=<your-secret-key>
DEBUG=True
ALLOWED_HOSTS=<your-host>
```

### 5. Setup database

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Create Superuser

```bash
python manage.py createsuperuser
```

### 7. Run the Development Server

```bash
python manage.py runserver
```

This will start the development server, and you can access the application at `http://localhost:8000`.
