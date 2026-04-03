# TrendOptimizer

TrendOptimizer is a Django project with a `marketing` app. It is set up for local development using SQLite.

## Quick Start

1. Create and activate a virtual environment (any location is fine).
2. Install Django:

```bash
pip install django
```

3. Apply migrations:

```bash
python Myproject/manage.py migrate
```

4. Run the development server:

```bash
python Myproject/manage.py runserver
```

Then open `http://127.0.0.1:8000/`.

## Project Structure

- `Myproject/` - Django project root (settings, urls, wsgi)
- `Myproject/marketing/` - Main app
- `Myproject/db.sqlite3` - Local SQLite database

## Configuration

- Optional environment variables can be stored in `Myproject/.env` (this file is git-ignored).

## Tests

```bash
python Myproject/manage.py test
```
