# Restaurant menu: Django back end

A control panel for editing the menu, and the read-only REST API the front end (`../restaurant-menu-simple`) reads.

| Address | What it is |
|---|---|
| `/panel/` | Control panel (staff accounts only) |
| `/api/v1/restaurant/` | Restaurant details, including the `ordering` block |
| `/api/v1/categories/` | Categories shown on the menu |
| `/api/v1/dishes/?category=<slug>` | Dishes of one category |
| `/api/v1/offers/` | Offers: several dishes for one price |

The API follows `restaurant-menu-simple-cart/docs/API.md` exactly. The older
`restaurant-menu-simple`, `restaurant-menu` and `restaurant-menu-light` front
ends ignore fields they do not know, so `ordering` does not disturb them.

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

- **Restaurant**: name, tagline, description, logo, hero photo, currency, contact, opening hours, social links, and ordering on WhatsApp.
- **Categories**: add, edit, delete, order, hide. A category with dishes can't be deleted.
- **Dishes**: add, edit, delete, photo upload with preview, tags, "available today" toggle, hide.
- **Tags**: add, edit, delete.
- **Offers**: add, edit, delete. An offer is a name, a price for the whole
  thing, an optional photo, and rows of dish + quantity. It needs at least one
  dish, and the same dish cannot be listed twice — raise its quantity instead.
  An offer stops being orderable on the menu while any dish inside it is
  unavailable or hidden, and a dish that is part of an offer cannot be deleted
  until it is taken out of it.

Replacing or deleting a photo also removes the old file from `media/`.

### Ordering on WhatsApp

The menu can collect dishes in a cart and hand the finished order to WhatsApp.
Nothing is stored here: the front end opens `wa.me` with the order written out,
and the conversation is the only record. There is no order endpoint and no
order table.

The **Restaurant** page carries the settings, and they come back under
`ordering` in `/api/v1/restaurant/`:

| Field | What it does |
|---|---|
| WhatsApp number for orders | Where orders are sent. Digits only, full international form: `9613000000`. **Empty means no cart on the menu at all.** A number typed as `+961 3 000 000` or `00961…` is cleaned up on save |
| Delivery fee | Added to the order when the customer chooses delivery, in the restaurant's currency. Empty or `0` shows as "Free" |
| Home delivery offered / Pickup offered / Table reservation offered | Each one off removes that choice from the cart. All three off is refused while a number is set — clear the number instead |
| Pickup | Asks the customer what time they will collect the order, for **today**. It arrives as "Pickup time (today): 6:30 PM" |
| Table reservation | Asks the customer for the party size and a time, and books it for **today** — there is no date field. The chosen dishes go with it as a pre-order |
| Delivery note | One line under the delivery choice, e.g. "Delivery inside Chhim only" |

The customer's name, the delivery address and any note go into the message
only; they are never sent to this server.

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
| `CORS_ALLOWED_ORIGINS` | `http://127.0.0.1:5500,http://localhost:5500,https://deebhajjar.github.io` | Where the front end is served: scheme and host only, no path |
| `MENU_SITE_URL` | `http://127.0.0.1:5500/` | "View the menu" link in the panel |

In production, run `python manage.py collectstatic` and let the web server serve
`staticfiles/` and `media/` (Django serves `/media/` only when `DEBUG` is on).
