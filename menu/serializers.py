from rest_framework import serializers

from .models import Category, Dish, OpeningHours, Restaurant, SocialLink


class OpeningHoursSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpeningHours
        fields = ["days", "hours"]


class SocialLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialLink
        fields = ["label", "url"]


class OrderingSerializer(serializers.ModelSerializer):
    """
    Everything the menu's cart needs, in one block.

    `enabled` is the only flag the front end has to read: false means no
    number is set, or neither way of receiving the order is offered, and the
    cart stays out of the menu entirely.
    """

    enabled = serializers.BooleanField(source="ordering_enabled", read_only=True)

    class Meta:
        model = Restaurant
        fields = [
            "enabled", "whatsapp_number", "delivery_fee",
            "delivery_enabled", "pickup_enabled", "reservation_enabled", "delivery_note",
        ]


class RestaurantSerializer(serializers.ModelSerializer):
    opening_hours = OpeningHoursSerializer(many=True, read_only=True)
    social_links = SocialLinkSerializer(many=True, read_only=True)
    ordering = serializers.SerializerMethodField()

    class Meta:
        model = Restaurant
        fields = [
            "name", "tagline", "description", "logo", "hero_image", "currency",
            "address", "phone", "email", "opening_hours", "social_links", "ordering",
        ]

    def get_ordering(self, obj):
        return OrderingSerializer(obj, context=self.context).data


class CategorySerializer(serializers.ModelSerializer):
    # Categories have no picture in this design; kept for the API contract.
    image = serializers.SerializerMethodField()
    dish_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ["id", "slug", "name", "description", "image", "order", "dish_count"]

    def get_image(self, obj):
        return None


class DishSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    tags = serializers.SlugRelatedField(slug_field="code", many=True, read_only=True)

    class Meta:
        model = Dish
        fields = [
            "id", "slug", "name", "description", "ingredients", "price", "image",
            "category", "tags", "is_available", "order",
        ]
