import shutil
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from menu.models import Category, Dish, Restaurant, Tag
from menu.tests import image

MEDIA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA)
class PanelTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user("owner", password="a-long-password-1", is_staff=True)
        self.customer = User.objects.create_user("guest", password="a-long-password-1")
        self.category = Category.objects.create(name="Plates")

    def login(self):
        self.client.force_login(self.staff)

    def test_pages_require_sign_in(self):
        for name in ["overview", "restaurant", "category_list", "dish_list", "tag_list", "dish_create"]:
            response = self.client.get(reverse(f"dashboard:{name}"))
            self.assertRedirects(response, f"{reverse('dashboard:login')}?next={reverse(f'dashboard:{name}')}")

    def test_non_staff_cannot_sign_in_or_open_pages(self):
        response = self.client.post(reverse("dashboard:login"), {"username": "guest", "password": "a-long-password-1"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(reverse("dashboard:overview")).status_code, 403)

    def test_staff_sign_in(self):
        response = self.client.post(reverse("dashboard:login"), {"username": "owner", "password": "a-long-password-1"})
        self.assertRedirects(response, reverse("dashboard:overview"))

    def test_there_is_no_sign_up_or_admin(self):
        self.assertEqual(self.client.get("/panel/register/").status_code, 404)
        self.assertEqual(self.client.get("/admin/").status_code, 404)

    def test_every_page_renders(self):
        self.login()
        dish = Dish.objects.create(category=self.category, name="Mixed grill", price="10", image=image())
        tag = Tag.objects.create(code="spicy")
        urls = [
            reverse("dashboard:overview"), reverse("dashboard:restaurant"),
            reverse("dashboard:category_list"), reverse("dashboard:category_create"),
            reverse("dashboard:category_update", args=[self.category.pk]),
            reverse("dashboard:category_delete", args=[self.category.pk]),
            reverse("dashboard:dish_list"), reverse("dashboard:dish_list") + "?category=plates",
            reverse("dashboard:dish_create"), reverse("dashboard:dish_update", args=[dish.pk]),
            reverse("dashboard:dish_delete", args=[dish.pk]),
            reverse("dashboard:tag_list"), reverse("dashboard:tag_create"),
            reverse("dashboard:tag_update", args=[tag.pk]), reverse("dashboard:tag_delete", args=[tag.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_restaurant_create_and_edit_with_rows(self):
        self.login()
        data = {
            "name": "Nour", "currency": "usd",
            "hours-TOTAL_FORMS": "1", "hours-INITIAL_FORMS": "0",
            "hours-0-days": "Every day", "hours-0-hours": "11:00 – 23:00", "hours-0-order": "1",
            "social-TOTAL_FORMS": "1", "social-INITIAL_FORMS": "0",
            "social-0-label": "Instagram", "social-0-url": "https://instagram.com/nour", "social-0-order": "1",
        }
        response = self.client.post(reverse("dashboard:restaurant"), data)
        self.assertRedirects(response, reverse("dashboard:restaurant"))
        restaurant = Restaurant.load()
        self.assertEqual(restaurant.currency, "USD")
        self.assertEqual(restaurant.opening_hours.count(), 1)
        self.assertEqual(restaurant.social_links.count(), 1)

    def test_category_crud(self):
        self.login()
        self.client.post(reverse("dashboard:category_create"), {"name": "Mezze & salads", "order": 3, "is_active": "on"})
        category = Category.objects.get(name="Mezze & salads")
        self.assertEqual(category.slug, "mezze-salads")

        self.client.post(reverse("dashboard:category_update", args=[category.pk]),
                         {"name": "Mezze", "slug": "mezze", "order": 3})
        category.refresh_from_db()
        self.assertEqual((category.name, category.is_active), ("Mezze", False))

        self.client.post(reverse("dashboard:category_delete", args=[category.pk]))
        self.assertFalse(Category.objects.filter(pk=category.pk).exists())

    def test_category_with_dishes_is_not_deleted(self):
        self.login()
        Dish.objects.create(category=self.category, name="Kafta", price="10", image=image())
        self.client.post(reverse("dashboard:category_delete", args=[self.category.pk]))
        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())

    def test_dish_crud_and_toggle(self):
        self.login()
        tag = Tag.objects.create(code="vegan")
        response = self.client.post(reverse("dashboard:dish_create"), {
            "name": "Hummus", "category": self.category.pk, "price": "250000",
            "ingredients": "Chickpeas\nTahini\n\n Lemon ", "image": image("hummus.gif"),
            "tags": [tag.pk], "is_available": "on", "is_published": "on", "order": 1,
        })
        dish = Dish.objects.get(name="Hummus")
        self.assertRedirects(response, f"{reverse('dashboard:dish_list')}#category-{self.category.pk}")
        self.assertEqual(dish.ingredients, ["Chickpeas", "Tahini", "Lemon"])
        self.assertEqual(list(dish.tags.values_list("code", flat=True)), ["vegan"])
        old_file = Path(dish.image.path)

        # Edit without a new image keeps the old one; a new image replaces the file.
        self.client.post(reverse("dashboard:dish_update", args=[dish.pk]), {
            "name": "Hummus beiruti", "category": self.category.pk, "price": "300000",
            "ingredients": "Chickpeas", "image": image("beiruti.gif"), "is_published": "on", "order": 1,
        })
        dish.refresh_from_db()
        self.assertEqual(dish.name, "Hummus beiruti")
        self.assertFalse(dish.is_available)
        self.assertFalse(old_file.exists())

        self.client.post(reverse("dashboard:dish_toggle", args=[dish.pk]))
        dish.refresh_from_db()
        self.assertTrue(dish.is_available)

        image_path = Path(dish.image.path)
        self.client.post(reverse("dashboard:dish_delete", args=[dish.pk]))
        self.assertFalse(Dish.objects.filter(pk=dish.pk).exists())
        self.assertFalse(image_path.exists())

    def test_toggle_needs_post(self):
        self.login()
        dish = Dish.objects.create(category=self.category, name="Fries", price="1", image=image())
        self.assertEqual(self.client.get(reverse("dashboard:dish_toggle", args=[dish.pk])).status_code, 405)

    def test_tag_crud(self):
        self.login()
        self.client.post(reverse("dashboard:tag_create"), {"code": "Gluten_Free"})
        tag = Tag.objects.get(code="gluten_free")
        self.client.post(reverse("dashboard:tag_update", args=[tag.pk]), {"code": "new"})
        tag.refresh_from_db()
        self.assertEqual(tag.code, "new")
        self.client.post(reverse("dashboard:tag_delete", args=[tag.pk]))
        self.assertFalse(Tag.objects.exists())

    def test_logout(self):
        self.login()
        response = self.client.post(reverse("dashboard:logout"))
        self.assertRedirects(response, reverse("dashboard:login"))
