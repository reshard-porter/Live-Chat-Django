# Django Live Chat — Restored

An updated, **standalone Django 5.2 Q&A application** based on the legacy
`django-livechat` project. It lets staff schedule a session, visitors submit
questions, moderators approve questions, and staff post answers. It **is not**
a WebSocket chat / instant messaging app. Refresh the page to see new answers.

## Quick start (Windows / macOS / Linux)

Use **Python 3.10–3.13** (Python 3.13 works with Django 5.2) and a terminal in
this folder, where `manage.py` is located.

1. Create a virtual environment:

   ```bash
   python -m venv .venv
   ```

2. Activate it:

   - **Windows PowerShell:** `.venv\Scripts\Activate.ps1`
   - **Windows Command Prompt:** `.venv\Scripts\activate.bat`
   - **macOS / Linux:** `source .venv/bin/activate`

   If `python` is not found on Windows, use `py` for the first step, then `python`.

3. Install Django and initialize the SQLite database:

   ```bash
   python -m pip install -r requirements.txt
   python manage.py migrate
   python manage.py createsuperuser
   ```

4. Create a session that's already open for questions and start the server:

   ```bash
   python manage.py create_demo_chat
   python manage.py runserver
   ```

5. Open these URLs in your browser:

   - **Home:** http://127.0.0.1:8000/
   - **Demo Q&A:** http://127.0.0.1:8000/livechat/demo-live-chat/
   - **Admin:** http://127.0.0.1:8000/admin/
   - **Archive:** http://127.0.0.1:8000/livechat/archive/

   Ask a question in the demo page. Log into `/admin/`, open **Live chats**,
   click the demo chat, then **Moderate questions / reply**. Approve the question
   and write an answer. Reload the public page to see it.

## Create your own Q&A session

In Django admin, add a **Live chat** with a unique URL slug, title, expert,
start time, and end time. The end time must be *after* the start time. Session
start/end times are displayed in `DJANGO_TIME_ZONE` (default `UTC`).

Before the start time, questions cannot be submitted. During the session,
visitors can submit questions which await moderator approval. After the end
time, or if the session is cancelled, archived, or closed, submissions stop.
`maximum_questions` is optional; a value of `0` closes all submissions.

Staff can manage questions individually from **Live chat questions** in admin
or use the **Moderate questions / reply** link on the session edit screen.
The archive lists sessions whose end times have passed. If you disable
anonymous submissions, create regular user accounts in the admin and have
participants log in at `/accounts/login/`.

## Run tests

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test livechat
```

## Installing as a Django app in an existing site

Install this repository with `python -m pip install -e .`, add
`livechat.apps.LivechatConfig` to `INSTALLED_APPS`, include
`path('', include('livechat.urls'))` in your URL patterns, run `migrate`, and
serve the app's static files. This app depends on Django's `auth`,
`contenttypes`, `sessions`, `messages` and `staticfiles` apps. The optional
context processor `livechat.context_processors.current_livechat` provides a
current-session reference to your own templates. Template tags are available
from `{% load livechat_tags %}`:

- `{% live_chat_banner %}`
- `{% show_live_chat %}`
- `{% archive_live_chat %}`
- `{% get_livechat_for_article article "chat" %}`

The templates ship with their own base HTML, so no external `base.html` or
Jmbo theme is needed. The templates assume the `livechat` URL namespace is
configured. To display the current chat in another page, render
`{% show_live_chat %}` from a template using a `RequestContext`.

## Settings (environment variables)

| Setting | Default | What it does |
| --- | --- | --- |
| `DJANGO_DEBUG` | `1` | Development mode only; set `0` in production |
| `DJANGO_SECRET_KEY` | Development-only fallback | **Required** with `DJANGO_DEBUG=0` |
| `DJANGO_ALLOWED_HOSTS` | `127.0.0.1,localhost` | Comma-separated hostnames |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Empty | Full trusted HTTPS origins if needed |
| `DJANGO_TIME_ZONE` | `UTC` | Session time-zone display and input |
| `LIVECHAT_ALLOW_ANONYMOUS` | `1` | Set `0` to require login for asking questions |
| `LIVECHAT_QUESTION_COOLDOWN_SECONDS` | `30` | Simple anti-spam cooldown; set `0` to turn it off |

For a public deployment, set `DJANGO_DEBUG=0`, use a random secret key, configure
`ALLOWED_HOSTS`, HTTPS and a production WSGI/ASGI server (e.g. Gunicorn), and
serve static assets with a suitable static server / WhiteNoise. Replace
SQLite and the in-memory development cache if traffic or multiple workers
are expected. Add real spam protection / CAPTCHA and stricter rate limits
before making anonymous posting publicly available.

## Important compatibility / migration warning

The uploaded project was written for **Django 1.4.5 / Python 2 / South / Jmbo**,
with the old `django.contrib.comments`, `django-category` and other removed or
unmaintained packages. Its archive route, admin popup, comment counts, timing
logic, and templates were not compatible with supported Python/Django releases.

This restoration deliberately **replaces those old integrations** with
built-in Django models and the current Django admin. The data schema is **not
compatible with the original South migrations**. The old source code and
migrations are preserved intact in `legacy_source/original-django-livechat-develop.zip`
for reference. **Do not run this project's `migrate` against an original
production database.** Back up the old database and write a one-time data
conversion for LiveChat records, comments, and answers if that data matters.
No legacy-data import is bundled, because its exact source schema and
custom Jmbo content model cannot be safely inferred from this ZIP alone.

## Changes made

- Migrated to Python 3 and Django 5.2 with native Django migrations.
- Removed unsupported Jmbo, South, custom comment tags and legacy URLs.
- Fixed the archive view, detail lookup, pagination and old admin syntax.
- Fixed session start/end checks and the five-day banner window.
- Enforced server-side schedule/question-limit checks when posting questions.
- Added question moderation, staff replies, CSRF protection and escaping.
- Added a runnable Django project, sample data command and automated tests.

## Verification

The repaired project includes Django tests and native migrations. If the
recovery is reviewed in an offline environment without Django already installed,
Python compilation and static checks can run, but the Django integration tests
must be executed after installing the requirements on your machine.
