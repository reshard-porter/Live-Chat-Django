# Repair report

## Review of uploaded source (48 ZIP entries)

The original archive was a **Django reusable app**, not a runnable Django
project. It contained no `manage.py`, no runnable root URL configuration,
and no current Django settings. Code and tests targeted Python 2.7 and
Django 1.4.5. Some referenced templates, dependencies, and files weren't
included (for example `base.html`, old Jmbo tags, and a valid test image).

### Original failures found and addressed

| Area | Original issue | Resolution |
| --- | --- | --- |
| Runtime | `django==1.4.5`, Python 2 syntax and unmaintained packages | Current Python/Django-compatible code and requirements |
| Migrations | South migrations incompatible with modern Django | Native `0001_initial` migration; original retained in archived ZIP |
| Imports | `django.conf.urls.defaults`, `django.contrib.comments`, `django.core.urlresolvers`, `contenttypes.generic` removed | Modern Django URL, model and content-type APIs |
| Project bootstrap | No root project or `manage.py` | Added `config`, `manage.py`, local SQLite settings |
| Archive view | `DetailView.get_object()` returned a queryset | Working `ListView`, chronological archive and pagination |
| Detail view | `TemplateView` ignored slug, could render the wrong chat | `DetailView` resolves `slug` and renders selected chat |
| Session time | `is_in_progress` checked start only, never checked end | Starts and ends checked using timezone-aware datetimes |
| Banner | Unbounded future window, wrong ordering / latest selection | Current chat first, then nearest within five days |
| Question limit | Off-by-one `>= maximum_questions - 1` | Zero, one, unlimited cases handled correctly |
| Missing current chat | Tag assumed a chat always exists | Safe empty state |
| Admin | Python 2 `except ... , e`, old URL and popup JS | Modern admin actions, inline replies, staff moderation page |
| Admin CSRF | Archive could be triggered from GET | State-changing actions require a POST |
| Public form | Deprecated comments tags and missing dependencies | CSRF-protected, validated Django question form |
| Security | Unescaped `|safe` descriptions and no spam safeguards | Default escaping, moderation, honeypot, short cooldown |
| Templates | Depended on unavailable `base.html` and Jmbo/AskMAMA tags | Standalone templates and bundled responsive CSS |
| Tests | Old Jmbo fixtures, pytest / South requirements, zero-byte image | Modern Django `TestCase` coverage and demo command |

## Intentional changes

- Chat means **scheduled moderated Q&A**, not peer-to-peer messaging or WebSockets.
- Public questions use `LiveChatQuestion` instead of Django's removed comments system.
- Staff replies use a foreign key to `LiveChatQuestion` instead of the old
  `comments.Comment` table. Category/site filtering and Jmbo publishing hooks
  aren't included in this standalone edition.
- The new database isn't automatically compatible with a legacy Jmbo/South database.
  Preserve a complete backup if you have real old data.

## Verification and remaining checks

- Inspected every entry of the uploaded archive (48 ZIP entries).
- New Python source modules parse and compile under Python 3.13.
- Examined URLs, templates, models, admin permissions, CSRF, tests, migrations,
  settings, and packaging for leftover legacy references.
- Confirmed that Django 5.2 supports Python 3.13 using official Django docs.
- **Not run here:** `manage.py check`, `migrate`, `makemigrations --check`,
  `manage.py test`, or a browser smoke test. Django isn't installed in the
  offline execution environment and `pip` couldn't reach package servers.

After extracting the repaired ZIP, follow the quick start in `README.md`
and run all three checks listed in its **Run tests** section. Any deployment
or migration of existing database records should be validated separately.
