import shutil
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from menu.models import Category, Dish, Offer, OfferItem, Restaurant, Tag
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
            reverse("dashboard:offer_list"), reverse("dashboard:offer_create"),
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
            "whatsapp_number": "+961 3 000 000", "delivery_fee": "2.50",
            "delivery_enabled": "on", "pickup_enabled": "on", "reservation_enabled": "on",
            "hours-TOTAL_FORMS": "1", "hours-INITIAL_FORMS": "0",
            "hours-0-days": "Every day", "hours-0-hours": "11:00 – 23:00", "hours-0-order": "1",
            "social-TOTAL_FORMS": "1", "social-INITIAL_FORMS": "0",
            "social-0-label": "Instagram", "social-0-url": "https://instagram.com/nour", "social-0-order": "1",
        }
        response = self.client.post(reverse("dashboard:restaurant"), data)
        self.assertRedirects(response, reverse("dashboard:restaurant"))
        restaurant = Restaurant.load()
        self.assertEqual(restaurant.currency, "USD")
        self.assertEqual(restaurant.whatsapp_number, "9613000000")
        self.assertTrue(restaurant.ordering_enabled)
        self.assertEqual(restaurant.opening_hours.count(), 1)
        self.assertEqual(restaurant.social_links.count(), 1)

    def test_restaurant_page_shows_the_ordering_fieldset(self):
        self.login()
        response = self.client.get(reverse("dashboard:restaurant"))
        self.assertContains(response, "Ordering on WhatsApp")
        for field in ["whatsapp_number", "delivery_fee", "delivery_enabled",
                      "pickup_enabled", "reservation_enabled", "delivery_note"]:
            with self.subTest(field=field):
                self.assertContains(response, f'name="{field}"')

    def test_reservation_alone_is_a_valid_setup(self):
        self.login()
        data = {
            "name": "Nour", "currency": "usd", "whatsapp_number": "9613000000",
            "reservation_enabled": "on",
            "hours-TOTAL_FORMS": "0", "hours-INITIAL_FORMS": "0",
            "social-TOTAL_FORMS": "0", "social-INITIAL_FORMS": "0",
        }
        self.assertRedirects(
            self.client.post(reverse("dashboard:restaurant"), data),
            reverse("dashboard:restaurant"),
        )
        restaurant = Restaurant.load()
        self.assertTrue(restaurant.ordering_enabled)
        self.assertFalse(restaurant.delivery_enabled)

    def test_ordering_needs_a_way_to_receive_the_order(self):
        self.login()
        data = {
            "name": "Nour", "currency": "usd", "whatsapp_number": "9613000000",
            "hours-TOTAL_FORMS": "0", "hours-INITIAL_FORMS": "0",
            "social-TOTAL_FORMS": "0", "social-INITIAL_FORMS": "0",
        }
        response = self.client.post(reverse("dashboard:restaurant"), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Offer at least one of delivery, pickup or table reservation")

    def test_empty_delivery_fee_means_free(self):
        self.login()
        data = {
            "name": "Nour", "currency": "usd", "whatsapp_number": "9613000000",
            "delivery_fee": "", "pickup_enabled": "on",
            "hours-TOTAL_FORMS": "0", "hours-INITIAL_FORMS": "0",
            "social-TOTAL_FORMS": "0", "social-INITIAL_FORMS": "0",
        }
        self.client.post(reverse("dashboard:restaurant"), data)
        self.assertEqual(Restaurant.load().delivery_fee, 0)

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


@override_settings(MEDIA_ROOT=MEDIA)
class OfferPanelTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user("owner", password="a-long-password-1", is_staff=True)
        self.client.force_login(self.staff)
        self.category = Category.objects.create(name="Plates")
        self.tawouk = Dish.objects.create(
            category=self.category, name="Tawouk", price="400000", image=image()
        )
        self.fattoush = Dish.objects.create(
            category=self.category, name="Fattoush", price="300000", image=image()
        )

    def rows(self, *items, total=None, initial=0):
        """Formset payload for the rows of dishes inside an offer."""
        data = {
            "items-TOTAL_FORMS": str(total if total is not None else len(items)),
            "items-INITIAL_FORMS": str(initial),
        }
        for index, (dish, quantity) in enumerate(items):
            data[f"items-{index}-dish"] = str(dish.pk) if dish else ""
            data[f"items-{index}-quantity"] = str(quantity)
            data[f"items-{index}-order"] = str(index + 1)
        return data

    def test_add_an_offer_with_its_dishes(self):
        data = {"name": "Family meal", "price": "900000", "order": "1", "is_active": "on"}
        data.update(self.rows((self.tawouk, 2), (self.fattoush, 1)))
        response = self.client.post(reverse("dashboard:offer_create"), data)
        self.assertRedirects(response, reverse("dashboard:offer_list"))

        offer = Offer.objects.get(name="Family meal")
        self.assertEqual(offer.slug, "family-meal")
        self.assertEqual(offer.items.count(), 2)
        self.assertEqual(offer.items.first().quantity, 2)
        self.assertEqual(offer.full_price, 1100000)

    def test_an_offer_needs_at_least_one_dish(self):
        data = {"name": "Empty", "price": "1000", "order": "1", "is_active": "on"}
        data.update({"items-TOTAL_FORMS": "0", "items-INITIAL_FORMS": "0"})
        response = self.client.post(reverse("dashboard:offer_create"), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add at least one dish to the offer.")
        self.assertFalse(Offer.objects.filter(name="Empty").exists())

    def test_a_row_without_a_dish_is_reported(self):
        data = {"name": "Halfway", "price": "1000", "order": "1", "is_active": "on"}
        data.update(self.rows((None, 2)))
        response = self.client.post(reverse("dashboard:offer_create"), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required.")
        self.assertFalse(Offer.objects.filter(name="Halfway").exists())

    def test_a_refused_new_offer_does_not_come_back_as_an_edit(self):
        """The offer was rolled back, so the page must not offer to delete it."""
        data = {"name": "Empty", "price": "1000", "order": "1", "is_active": "on"}
        data.update({"items-TOTAL_FORMS": "0", "items-INITIAL_FORMS": "0"})
        response = self.client.post(reverse("dashboard:offer_create"), data)
        self.assertContains(response, "Add an offer")
        self.assertNotContains(response, "/delete/")
        # What was typed is still in the form, ready to be finished.
        self.assertContains(response, 'value="Empty"')

    def test_the_same_dish_cannot_be_listed_twice(self):
        data = {"name": "Double", "price": "1000", "order": "1", "is_active": "on"}
        data.update(self.rows((self.tawouk, 1), (self.tawouk, 1)))
        response = self.client.post(reverse("dashboard:offer_create"), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "is in the offer twice")
        self.assertFalse(Offer.objects.filter(name="Double").exists())

    def test_editing_an_offer_keeps_its_rows(self):
        offer = Offer.objects.create(name="Family meal", price="900000")
        item = OfferItem.objects.create(offer=offer, dish=self.tawouk, quantity=2)

        data = {"name": "Family feast", "price": "950000", "order": "0", "is_active": "on",
                "slug": offer.slug}
        data.update(self.rows(total=1, initial=1))
        data.update({
            "items-0-id": str(item.pk), "items-0-offer": str(offer.pk),
            "items-0-dish": str(self.tawouk.pk), "items-0-quantity": "3", "items-0-order": "1",
        })
        response = self.client.post(reverse("dashboard:offer_update", args=[offer.pk]), data)
        self.assertRedirects(response, reverse("dashboard:offer_list"))
        offer.refresh_from_db()
        item.refresh_from_db()
        self.assertEqual(offer.name, "Family feast")
        self.assertEqual(item.quantity, 3)

    def test_offer_list_shows_what_is_inside(self):
        offer = Offer.objects.create(name="Family meal", price="900000")
        OfferItem.objects.create(offer=offer, dish=self.tawouk, quantity=2)
        response = self.client.get(reverse("dashboard:offer_list"))
        self.assertContains(response, "Family meal")
        self.assertContains(response, "2 × Tawouk")

    def test_delete_an_offer(self):
        offer = Offer.objects.create(name="Family meal", price="900000")
        OfferItem.objects.create(offer=offer, dish=self.tawouk, quantity=2)
        response = self.client.post(reverse("dashboard:offer_delete", args=[offer.pk]))
        self.assertRedirects(response, reverse("dashboard:offer_list"))
        self.assertFalse(Offer.objects.exists())
        # The dishes it held are untouched.
        self.assertTrue(Dish.objects.filter(pk=self.tawouk.pk).exists())

    def test_a_dish_inside_an_offer_is_not_deleted(self):
        offer = Offer.objects.create(name="Family meal", price="900000")
        OfferItem.objects.create(offer=offer, dish=self.tawouk, quantity=2)

        page = self.client.get(reverse("dashboard:dish_delete", args=[self.tawouk.pk]))
        self.assertContains(page, "Take the dish out of these offers first:")
        self.assertContains(page, "Family meal")

        self.client.post(reverse("dashboard:dish_delete", args=[self.tawouk.pk]))
        self.assertTrue(Dish.objects.filter(pk=self.tawouk.pk).exists())
