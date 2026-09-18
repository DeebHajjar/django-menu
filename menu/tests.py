import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from .models import Category, Dish, OpeningHours, Restaurant, SocialLink, Tag

MEDIA = tempfile.mkdtemp()

# 1×1 GIF, a valid image for ImageField.
PIXEL = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00"
    b",\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)


def image(name="dish.gif"):
    return SimpleUploadedFile(name, PIXEL, content_type="image/gif")


@override_settings(MEDIA_ROOT=MEDIA)
class ApiTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        restaurant = Restaurant.objects.create(name="Nour", currency="lbp")
        OpeningHours.objects.create(restaurant=restaurant, days="Every day", hours="11:00 – 23:00")
        SocialLink.objects.create(restaurant=restaurant, label="Instagram", url="https://instagram.com/nour")
        self.sandwiches = Category.objects.create(name="Sandwiches", order=1)
        self.hidden = Category.objects.create(name="Secret", order=2, is_active=False)
        vegan = Tag.objects.create(code="vegan")
        self.dish = Dish.objects.create(
            category=self.sandwiches, name="Falafel sandwich", price="350000.00",
            ingredients=["Falafel", "Tahini"], image=image(), order=1,
        )
        self.dish.tags.add(vegan)
        Dish.objects.create(category=self.sandwiches, name="Draft", price="1", image=image(), is_published=False)
        Dish.objects.create(category=self.hidden, name="Hidden", price="1", image=image())

    def test_restaurant(self):
        data = self.client.get("/api/v1/restaurant/").json()
        self.assertEqual(data["name"], "Nour")
        self.assertEqual(data["currency"], "LBP")
        self.assertIsNone(data["logo"])
        self.assertEqual(data["opening_hours"], [{"days": "Every day", "hours": "11:00 – 23:00"}])
        self.assertEqual(data["social_links"], [{"label": "Instagram", "url": "https://instagram.com/nour"}])

    def test_restaurant_missing_is_404(self):
        Restaurant.objects.all().delete()
        self.assertEqual(self.client.get("/api/v1/restaurant/").status_code, 404)

    def test_categories_hide_inactive_and_count_published_dishes(self):
        data = self.client.get("/api/v1/categories/").json()
        self.assertEqual(data, [{
            "id": self.sandwiches.id, "slug": "sandwiches", "name": "Sandwiches", "description": "",
            "image": None, "order": 1, "dish_count": 1,
        }])

    def test_dishes_by_category(self):
        data = self.client.get("/api/v1/dishes/", {"category": "sandwiches"}).json()
        self.assertEqual(len(data), 1)
        dish = data[0]
        self.assertEqual(dish["slug"], "falafel-sandwich")
        self.assertEqual(dish["price"], "350000.00")
        self.assertEqual(dish["category"], "sandwiches")
        self.assertEqual(dish["tags"], ["vegan"])
        self.assertEqual(dish["ingredients"], ["Falafel", "Tahini"])
        self.assertTrue(dish["image"].startswith("http://testserver/media/dishes/"))

    def test_unknown_or_hidden_category_returns_empty_list(self):
        self.assertEqual(self.client.get("/api/v1/dishes/", {"category": "nope"}).json(), [])
        self.assertEqual(self.client.get("/api/v1/dishes/", {"category": "secret"}).json(), [])

    def test_api_is_read_only(self):
        self.assertEqual(self.client.post("/api/v1/dishes/", {"name": "x"}).status_code, 405)
        self.assertEqual(self.client.delete(f"/api/v1/dishes/{self.dish.slug}/").status_code, 405)

    def test_cors_allows_front_end(self):
        response = self.client.get("/api/v1/categories/", HTTP_ORIGIN="http://127.0.0.1:5500")
        self.assertEqual(response["Access-Control-Allow-Origin"], "http://127.0.0.1:5500")

    def test_slugs_are_unique(self):
        other = Category.objects.create(name="Sandwiches")
        self.assertEqual(other.slug, "sandwiches-2")
