from django import forms
from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from menu.models import Category, Dish, Restaurant, Tag

from .forms import (
    CategoryForm,
    DishForm,
    OpeningHoursFormSet,
    RestaurantForm,
    SocialLinkFormSet,
    StaffAuthenticationForm,
    TagForm,
)


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Panel pages: signed-in, active staff accounts only."""

    def test_func(self):
        user = self.request.user
        return user.is_active and user.is_staff


class LoginView(auth_views.LoginView):
    template_name = "dashboard/login.html"
    authentication_form = StaffAuthenticationForm
    redirect_authenticated_user = True


class LogoutView(auth_views.LogoutView):
    pass


class SuccessMessageMixin:
    """Flash message after a create, update or delete."""

    success_verb = "saved"

    def success_message(self):
        return f"“{self.object}” was {self.success_verb}."

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, self.success_message())
        return response


# Overview ----------------------------------------------------------------

class OverviewView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/overview.html"
    section = "overview"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dishes = Dish.objects.all()
        context.update(
            category_count=Category.objects.count(),
            hidden_category_count=Category.objects.filter(is_active=False).count(),
            dish_count=dishes.count(),
            unavailable_count=dishes.filter(is_available=False).count(),
            unpublished_count=dishes.filter(is_published=False).count(),
            tag_count=Tag.objects.count(),
            categories=Category.objects.annotate(dish_total=Count("dishes")),
        )
        return context


# Restaurant --------------------------------------------------------------

class RestaurantView(StaffRequiredMixin, View):
    template_name = "dashboard/restaurant_form.html"
    section = "restaurant"

    def get_forms(self, data=None, files=None):
        restaurant = Restaurant.load() or Restaurant()
        return (
            RestaurantForm(data, files, instance=restaurant),
            OpeningHoursFormSet(data, instance=restaurant, prefix="hours"),
            SocialLinkFormSet(data, instance=restaurant, prefix="social"),
        )

    def render_forms(self, form, hours, social):
        return render(self.request, self.template_name, {
            "view": self, "form": form, "hours_formset": hours, "social_formset": social,
        })

    def get(self, request):
        return self.render_forms(*self.get_forms())

    def post(self, request):
        form, hours, social = self.get_forms(request.POST, request.FILES)
        if form.is_valid() and hours.is_valid() and social.is_valid():
            with transaction.atomic():
                restaurant = form.save()
                hours.instance = social.instance = restaurant
                hours.save()
                social.save()
            messages.success(request, "The restaurant details were saved.")
            return redirect("dashboard:restaurant")
        messages.error(request, "Some fields need attention. See the notes below.")
        return self.render_forms(form, hours, social)


# Categories --------------------------------------------------------------

class CategoryMixin(StaffRequiredMixin):
    model = Category
    form_class = CategoryForm
    section = "categories"
    success_url = reverse_lazy("dashboard:category_list")


class CategoryListView(CategoryMixin, ListView):
    template_name = "dashboard/category_list.html"

    def get_queryset(self):
        return Category.objects.annotate(
            dish_total=Count("dishes"),
            dish_shown=Count("dishes", filter=Q(dishes__is_published=True)),
        )


class CategoryCreateView(CategoryMixin, SuccessMessageMixin, CreateView):
    template_name = "dashboard/category_form.html"
    success_verb = "added"


class CategoryUpdateView(CategoryMixin, SuccessMessageMixin, UpdateView):
    template_name = "dashboard/category_form.html"


class CategoryDeleteView(CategoryMixin, DeleteView):
    template_name = "dashboard/confirm_delete.html"
    form_class = forms.Form  # the confirmation has no fields

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            kind="category",
            blockers=self.object.dishes.all(),
            blocker_message="Move these dishes to another category or delete them first:",
            cancel_url=reverse("dashboard:category_list"),
        )
        return context

    def form_valid(self, form):
        if self.object.dishes.exists():
            messages.error(self.request, f"“{self.object}” still has dishes, so it was not deleted.")
            return redirect("dashboard:category_delete", pk=self.object.pk)
        messages.success(self.request, f"“{self.object}” was deleted.")
        return super().form_valid(form)


# Dishes ------------------------------------------------------------------

class DishMixin(StaffRequiredMixin):
    model = Dish
    form_class = DishForm
    section = "dishes"

    def get_success_url(self):
        return f"{reverse('dashboard:dish_list')}#category-{self.object.category_id}"


class DishListView(DishMixin, TemplateView):
    template_name = "dashboard/dish_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dishes = Dish.objects.prefetch_related("tags")
        categories = Category.objects.prefetch_related(Prefetch("dishes", queryset=dishes))
        selected = self.request.GET.get("category", "")
        if selected:
            categories = categories.filter(slug=selected)
        restaurant = Restaurant.load()
        context.update(
            categories=categories,
            all_categories=Category.objects.all(),
            selected=selected,
            currency=restaurant.currency if restaurant else "LBP",
        )
        return context


class DishCreateView(DishMixin, SuccessMessageMixin, CreateView):
    template_name = "dashboard/dish_form.html"
    success_verb = "added"

    def get_initial(self):
        initial = super().get_initial()
        category = Category.objects.filter(slug=self.request.GET.get("category")).first()
        if category:
            initial["category"] = category
        return initial


class DishUpdateView(DishMixin, SuccessMessageMixin, UpdateView):
    template_name = "dashboard/dish_form.html"


class DishDeleteView(DishMixin, DeleteView):
    template_name = "dashboard/confirm_delete.html"
    form_class = forms.Form  # the confirmation has no fields

    def get_success_url(self):
        return reverse("dashboard:dish_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(kind="dish", cancel_url=reverse("dashboard:dish_list"))
        return context

    def form_valid(self, form):
        messages.success(self.request, f"“{self.object}” was deleted.")
        return super().form_valid(form)


class DishToggleView(StaffRequiredMixin, View):
    """Flips "available today" from the dish list (POST only)."""

    def post(self, request, pk):
        dish = get_object_or_404(Dish, pk=pk)
        dish.is_available = not dish.is_available
        dish.save(update_fields=["is_available"])
        state = "available" if dish.is_available else "not available today"
        messages.success(request, f"“{dish}” is now {state}.")
        return redirect(f"{reverse('dashboard:dish_list')}#dish-{dish.pk}")


# Tags --------------------------------------------------------------------

class TagMixin(StaffRequiredMixin):
    model = Tag
    form_class = TagForm
    section = "tags"
    success_url = reverse_lazy("dashboard:tag_list")


class TagListView(TagMixin, ListView):
    template_name = "dashboard/tag_list.html"

    def get_queryset(self):
        return Tag.objects.annotate(dish_total=Count("dishes"))


class TagCreateView(TagMixin, SuccessMessageMixin, CreateView):
    template_name = "dashboard/tag_form.html"
    success_verb = "added"


class TagUpdateView(TagMixin, SuccessMessageMixin, UpdateView):
    template_name = "dashboard/tag_form.html"


class TagDeleteView(TagMixin, DeleteView):
    template_name = "dashboard/confirm_delete.html"
    form_class = forms.Form  # the confirmation has no fields

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            kind="tag",
            note=f"It will be removed from {self.object.dishes.count()} dish(es). The dishes themselves stay.",
            cancel_url=reverse("dashboard:tag_list"),
        )
        return context

    def form_valid(self, form):
        messages.success(self.request, f"“{self.object}” was deleted.")
        return super().form_valid(form)
