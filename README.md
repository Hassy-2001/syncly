# Syncly

Syncly is a Django community chat application with themed rooms, private rooms, profile photos, OAuth login, password recovery, messaging, reactions, notifications, rate limiting, and a responsive yellow/black UI.

## Local Development

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and fill in local email/OAuth values.
4. Run migrations:

```bash
python manage.py migrate
```

5. Start the server:

```bash
python manage.py runserver
```

## Production Checklist

Use `.env.production.example` as the production variable template.

Required production values:

- `DEBUG=False`
- `SECRET_KEY`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `DATABASE_URL`
- `REDIS_URL`
- Email SMTP settings
- Google OAuth client ID and secret

Recommended production services:

- PostgreSQL for `DATABASE_URL`
- Redis for cache/rate limiting
- S3, Cloudinary, or another external media storage provider for uploads
- HTTPS with `SECURE_SSL_REDIRECT=True`

Deployment commands:

```bash
python manage.py collectstatic --no-input
python manage.py migrate --no-input
gunicorn studbud.wsgi:application
```

Security checks:

```bash
python manage.py check --deploy
```

Important: local `media/` uploads are not production-safe on serverless platforms. Configure persistent external media storage before accepting real customer uploads.
