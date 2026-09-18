from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),

    path("", views.OverviewView.as_view(), name="overview"),
    path("restaurant/", views.RestaurantView.as_view(), name="restaurant"),

    path("categories/", views.CategoryListView.as_view(), name="category_list"),
    path("categories/add/", views.CategoryCreateView.as_view(), name="category_create"),
    path("categories/<int:pk>/", views.CategoryUpdateView.as_view(), name="category_update"),
    path("categories/<int:pk>/delete/", views.CategoryDeleteView.as_view(), name="category_delete"),

    path("dishes/", views.DishListView.as_view(), name="dish_list"),
    path("dishes/add/", views.DishCreateView.as_view(), name="dish_create"),
    path("dishes/<int:pk>/", views.DishUpdateView.as_view(), name="dish_update"),
    path("dishes/<int:pk>/delete/", views.DishDeleteView.as_view(), name="dish_delete"),
    path("dishes/<int:pk>/toggle/", views.DishToggleView.as_view(), name="dish_toggle"),

    path("tags/", views.TagListView.as_view(), name="tag_list"),
    path("tags/add/", views.TagCreateView.as_view(), name="tag_create"),
    path("tags/<int:pk>/", views.TagUpdateView.as_view(), name="tag_update"),
    path("tags/<int:pk>/delete/", views.TagDeleteView.as_view(), name="tag_delete"),
]
