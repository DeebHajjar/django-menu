from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, DishViewSet, OfferViewSet, RestaurantView

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("dishes", DishViewSet, basename="dish")
router.register("offers", OfferViewSet, basename="offer")

urlpatterns = [
    path("restaurant/", RestaurantView.as_view(), name="restaurant"),
    path("", include(router.urls)),
]
