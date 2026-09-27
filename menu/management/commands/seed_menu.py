"""
Loads the front end's mock data (mock/*.json) and copies its images into MEDIA_ROOT.

    python manage.py seed_menu
    python manage.py seed_menu --source ../restaurant-menu-simple
    python manage.py seed_menu --reset      # delete the current menu first
"""
import json
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from menu.models import Category, Dish, Offer, OfferItem, OpeningHours, Restaurant, SocialLink, Tag

DEFAULT_SOURCE = settings.BASE_DIR.parent / "restaurant-menu-simple"
# The labels the front end knows (TAG_LABELS in js/components/dishCard.js).
KNOWN_TAGS = ["signature", "vegan", "vegetarian", "gluten_free", "spicy", "new"]


class Command(BaseCommand):
    help = "Load the starting menu from the front end's mock JSON files and copy the images to media/."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            type=Path,
            default=DEFAULT_SOURCE,
            help=f"Front-end folder containing mock/ and assets/ (default: {DEFAULT_SOURCE}).",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete the restaurant, categories, dishes and tags before loading.",
        )

    def handle(self, *args, source, reset, **options):
        source = source.resolve()
        mock = source / "mock"
        if not mock.is_dir():
            raise CommandError(f"No mock/ folder in {source}. Pass --source <front-end folder>.")

        restaurant_data = self.read_json(mock / "restaurant.json")
        categories_data = self.read_json(mock / "categories.json")
        dishes_data = self.read_json(mock / "dishes.json")
        # Offers came later than the other files: a front end without them still seeds.
        offers_path = mock / "offers.json"
        offers_data = self.read_json(offers_path) if offers_path.is_file() else []

        if not reset and (Category.objects.exists() or Dish.objects.exists()):
            raise CommandError("The menu already has data. Run again with --reset to replace it.")

        with transaction.atomic():
            if reset:
                OfferItem.objects.all().delete()
                Offer.objects.all().delete()
                Dish.objects.all().delete()
                Category.objects.all().delete()
                Tag.objects.all().delete()
                Restaurant.objects.all().delete()

            self.load_restaurant(restaurant_data, source)
            categories = self.load_categories(categories_data)
            count = self.load_dishes(dishes_data, categories, source)
            for code in KNOWN_TAGS:
                Tag.objects.get_or_create(code=code)
            offers = self.load_offers(offers_data, source)

        self.stdout.write(self.style.SUCCESS(
            f"Loaded the restaurant, {len(categories)} categories, {count} dishes, "
            f"{offers} offers and {Tag.objects.count()} tags. "
            f"Images copied to {settings.MEDIA_ROOT}."
        ))

    def load_offers(self, rows, source):
        """Each row names its dishes by slug, so the dishes must exist already."""
        dishes = {dish.slug: dish for dish in Dish.objects.all()}
        loaded = 0
        for order, row in enumerate(rows, start=1):
            offer = Offer(
                name=row["name"],
                slug=row.get("slug", ""),
                description=row.get("description", ""),
                price=Decimal(str(row["price"])),
                is_active=row.get("is_active", True),
                order=row.get("order", order),
            )
            self.attach_file(offer, "image", source, row.get("image"))
            offer.save()

            for position, item in enumerate(row.get("items", []), start=1):
                dish = dishes.get(item["dish"])
                if dish is None:
                    self.stderr.write(self.style.WARNING(
                        f"Offer “{offer.name}”: no dish with slug “{item['dish']}”, row skipped."
                    ))
                    continue
                OfferItem.objects.create(
                    offer=offer, dish=dish, quantity=item.get("quantity", 1), order=position
                )
            loaded += 1
        return loaded

    def read_json(self, path):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise CommandError(f"Could not read {path}: {error}") from error

    def attach_file(self, instance, field, source, relative_path):
        """Copies source/relative_path into the model's file field (skips missing files)."""
        if not relative_path:
            return
        path = source / relative_path
        if not path.is_file():
            self.stderr.write(self.style.WARNING(f"Image not found, skipped: {path}"))
            return
        with path.open("rb") as handle:
            getattr(instance, field).save(path.name, File(handle), save=False)

    def load_restaurant(self, data, source):
        ordering = data.get("ordering") or {}
        restaurant = Restaurant(
            name=data.get("name", "Restaurant"),
            tagline=data.get("tagline", ""),
            description=data.get("description", ""),
            currency=data.get("currency", "LBP"),
            address=data.get("address", ""),
            phone=data.get("phone", ""),
            email=data.get("email", ""),
            whatsapp_number=ordering.get("whatsapp_number", ""),
            delivery_fee=ordering.get("delivery_fee", 0) or 0,
            delivery_enabled=ordering.get("delivery_enabled", True),
            pickup_enabled=ordering.get("pickup_enabled", True),
            reservation_enabled=ordering.get("reservation_enabled", True),
            delivery_note=ordering.get("delivery_note", ""),
        )
        self.attach_file(restaurant, "logo", source, data.get("logo"))
        self.attach_file(restaurant, "hero_image", source, data.get("hero_image"))
        restaurant.save()

        for order, row in enumerate(data.get("opening_hours", []), start=1):
            OpeningHours.objects.create(restaurant=restaurant, days=row["days"], hours=row["hours"], order=order)
        for order, link in enumerate(data.get("social_links", []), start=1):
            SocialLink.objects.create(restaurant=restaurant, label=link["label"], url=link["url"], order=order)

    def load_categories(self, rows):
        categories = {}
        for row in rows:
            category = Category.objects.create(
                name=row["name"],
                slug=row.get("slug", ""),
                description=row.get("description", ""),
                order=row.get("order", 0),
            )
            categories[category.slug] = category
        return categories

    def load_dishes(self, rows, categories, source):
        count = 0
        for row in rows:
            category = categories.get(row.get("category"))
            if category is None:
                self.stderr.write(self.style.WARNING(f"Unknown category for {row.get('name')!r}, skipped."))
                continue
            dish = Dish(
                category=category,
                name=row["name"],
                slug=row.get("slug", ""),
                description=row.get("description", ""),
                ingredients=row.get("ingredients", []),
                price=Decimal(str(row.get("price", "0"))),
                is_available=row.get("is_available", True),
                order=row.get("order", 0),
            )
            self.attach_file(dish, "image", source, row.get("image"))
            dish.save()
            dish.tags.set([Tag.objects.get_or_create(code=code)[0] for code in row.get("tags", [])])
            count += 1
        return count
