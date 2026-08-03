# Aureate SaaS - Deployment Guide

This document describes the production setup details for deploying Aureate to real jewelry shops.

## Environment Variables
Ensure the following are defined in the environment or `.env` file:
- `SECRET_KEY`: Long, random string for cryptographic signatures.
- `DEBUG`: Set to `False` in production.
- `DB_ENGINE`: Set to `django.db.backends.postgresql`.
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`: Credentials for PostgreSQL instance.
- `ALLOWED_HOSTS`: Set to the app domain/subdomains (e.g. `*.aureate.com`).

## Static and Media Assets
- **Static files collection**:
  Run `python manage.py collectstatic --noinput` to compile static assets into the `staticfiles` folder.
- **Media uploads**:
  Store uploaded images (e.g. jewelry photos, repair tags) securely. Standard local storage or S3 buckets can be integrated.

## Application Server & Reverse Proxy
- **Gunicorn**:
  Use Gunicorn as the WSGI server. Run:
  `gunicorn jewellery_saas.wsgi:application --bind 0.0.0.0:8000 --workers 3`
- **Nginx**:
  Configure Nginx as a reverse proxy, proxying requests to port 8000, handling SSL terminations, and serving static files directly.
