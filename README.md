# Restaurant menu: Django back end

A control panel for editing the menu, and the read-only REST API the front end (`../restaurant-menu-simple`) reads.

| Address | What it is |
|---|---|
| `/panel/` | Control panel (staff accounts only) |
| `/api/v1/restaurant/` | Restaurant details |
| `/api/v1/categories/` | Categories shown on the menu |
| `/api/v1/dishes/?category=<slug>` | Dishes of one category |

The API follows `restaurant-menu-simple/docs/API.md` exactly.

## Setup (Windows, PowerShell)

```powershell
.venv\Scripts\Activate.ps1           # or: .venv\Scripts\activate.bat in cmd
pip install -r requirements.txt       # already done
python manage.py migrate              # already done
python manage.py seed_menu            # already done: mock data + images copied to media/
python manage.py createsuperuser      # the only way to create a panel account
python manage.py runserver
```

Sign in at http://127.0.0.1:8000/panel/.

There is no sign-up page. To add more people, run `createsuperuser` again, or
create a staff user from `python manage.py shell`. Only accounts with
`is_staff` can sign in. To change a password: `python manage.py changepassword <username>`.

## The panel

- **Restaurant**: name, tagline, description, logo, hero photo, currency, contact, opening hours, social links.
- **Categories**: add, edit, delete, order, hide. A category with dishes can't be deleted.
- **Dishes**: add, edit, delete, photo upload with preview, tags, "available today" toggle, hide.
- **Tags**: add, edit, delete.

Replacing or deleting a photo also removes the old file from `media/`.

## Reloading the starting data

```powershell
python manage.py seed_menu --reset    # deletes the current menu first
python manage.py seed_menu --source C:\path\to\restaurant-menu-simple
```

## Tests

```powershell
python manage.py test
```

## Settings (environment variables)

| Variable | Default | Purpose |
|---|---|---|
| `DJANGO_DEBUG` | `1` | `0` in production |
| `DJANGO_SECRET_KEY` | dev key | Required when `DJANGO_DEBUG=0` |
| `DJANGO_ALLOWED_HOSTS` | `127.0.0.1,localhost` | Comma-separated |
| `CORS_ALLOWED_ORIGINS` | `http://127.0.0.1:5500,http://localhost:5500` | Where the front end is served |
| `MENU_SITE_URL` | `http://127.0.0.1:5500/` | "View the menu" link in the panel |

In production, run `python manage.py collectstatic` and let the web server serve
`staticfiles/` and `media/` (Django serves `/media/` only when `DEBUG` is on).
