from django.db.models import Count, Q
from django.http import Http404
from rest_framework import generics, viewsets

from .models import Category, Dish, Restaurant
from .serializers import CategorySerializer, DishSerializer, RestaurantSerializer


class RestaurantView(generics.RetrieveAPIView):
    serializer_class = RestaurantSerializer

    def get_object(self):
        restaurant = Restaurant.objects.prefetch_related("opening_hours", "social_links").filter(pk=1).first()
        if restaurant is None:
            raise Http404
        return restaurant


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CategorySerializer
    lookup_field = "slug"

    def get_queryset(self):
        return Category.objects.filter(is_active=True).annotate(
            dish_count=Count("dishes", filter=Q(dishes__is_published=True))
        )


class DishViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DishSerializer
    lookup_field = "slug"

    def get_queryset(self):
        queryset = (
            Dish.objects.filter(is_published=True, category__is_active=True)
            .select_related("category")
            .prefetch_related("tags")
        )
        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category__slug=category)
        return queryset
