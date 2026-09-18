from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify

LOGO_EXTENSIONS = ["svg", "png", "jpg", "jpeg", "webp"]


def unique_slug(instance, value, max_length=50):
    """Slug of `value`, with -2, -3… added when another row already uses it."""
    base = (slugify(value) or "item")[:max_length].strip("-")
    model = type(instance)
    slug, number = base, 2
    while model.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
        suffix = f"-{number}"
        slug = f"{base[:max_length - len(suffix)]}{suffix}"
        number += 1
    return slug


class Restaurant(models.Model):
    """Single row holding the restaurant's details (always pk=1)."""

    name = models.CharField(max_length=120)
    tagline = models.CharField(max_length=160, blank=True)
    description = models.TextField(blank=True, help_text="One or two sentences.")
    logo = models.FileField(
        upload_to="brand/",
        blank=True,
        validators=[FileExtensionValidator(LOGO_EXTENSIONS)],
        help_text="SVG or transparent PNG, light artwork (it sits on the dark photo).",
    )
    hero_image = models.ImageField(
        upload_to="brand/", blank=True, help_text="Landscape, at least 1920 × 1080."
    )
    currency = models.CharField(
        max_length=3, default="LBP", help_text="ISO 4217 code, e.g. LBP, USD, EUR."
    )
    address = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.pk = 1
        self.currency = self.currency.upper()
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        return cls.objects.filter(pk=1).first()


class OpeningHours(models.Model):
    restaurant = models.ForeignKey(Restaurant, related_name="opening_hours", on_delete=models.CASCADE)
    days = models.CharField(max_length=60)
    hours = models.CharField(max_length=60)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name_plural = "opening hours"

    def __str__(self):
        return f"{self.days}: {self.hours}"


class SocialLink(models.Model):
    restaurant = models.ForeignKey(Restaurant, related_name="social_links", on_delete=models.CASCADE)
    label = models.CharField(max_length=40)
    url = models.URLField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.label


class Category(models.Model):
    name = models.CharField(max_length=80)
    slug = models.SlugField(
        unique=True, blank=True, help_text="Used in the menu address. Filled in from the name if left empty."
    )
    description = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(
        "shown on the menu", default=True, help_text="Hidden categories and their dishes disappear from the menu."
    )

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name)
        super().save(*args, **kwargs)


class Tag(models.Model):
    code = models.SlugField(
        unique=True,
        help_text="Lowercase, e.g. signature, vegan, vegetarian, gluten_free, spicy, new.",
    )

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return self.code

    @property
    def label(self):
        return self.code.replace("_", " ").replace("-", " ")


class Dish(models.Model):
    category = models.ForeignKey(Category, related_name="dishes", on_delete=models.PROTECT)
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True, blank=True, help_text="Filled in from the name if left empty.")
    description = models.TextField(blank=True)
    ingredients = models.JSONField(default=list, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    image = models.ImageField(upload_to="dishes/", help_text="Square photo, at least 600 × 600.")
    tags = models.ManyToManyField(Tag, blank=True, related_name="dishes")
    is_available = models.BooleanField(
        "available today", default=True, help_text="Unavailable dishes stay on the menu, greyed out."
    )
    is_published = models.BooleanField(
        "shown on the menu", default=True, help_text="Unpublished dishes are hidden from the menu."
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "dishes"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name)
        super().save(*args, **kwargs)
