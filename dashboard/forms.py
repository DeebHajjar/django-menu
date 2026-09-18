from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

from menu.models import Category, Dish, OpeningHours, Restaurant, SocialLink, Tag


class PanelFormMixin:
    """Gives every widget the panel's CSS class."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple)):
                continue
            if isinstance(widget, forms.ClearableFileInput):
                widget.attrs.setdefault("class", "file-input")
                widget.attrs.setdefault("data-preview", "")
                continue
            widget.attrs.setdefault("class", "input")


class StaffAuthenticationForm(PanelFormMixin, AuthenticationForm):
    """Only active staff accounts may sign in to the panel."""

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_staff:
            raise ValidationError(self.error_messages["invalid_login"], code="invalid_login",
                                  params={"username": self.username_field.verbose_name})


class RestaurantForm(PanelFormMixin, forms.ModelForm):
    class Meta:
        model = Restaurant
        fields = [
            "name", "tagline", "description", "currency", "logo", "hero_image",
            "address", "phone", "email",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "currency": forms.TextInput(attrs={"maxlength": 3, "style": "text-transform: uppercase"}),
            "logo": forms.ClearableFileInput(attrs={"accept": ".svg,.png,.jpg,.jpeg,.webp"}),
            "hero_image": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }

    def clean_currency(self):
        currency = self.cleaned_data["currency"].strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            raise ValidationError("Use a three-letter code such as LBP, USD or EUR.")
        return currency


class OpeningHoursForm(PanelFormMixin, forms.ModelForm):
    class Meta:
        model = OpeningHours
        fields = ["days", "hours", "order"]
        widgets = {"order": forms.NumberInput(attrs={"min": 0})}


class SocialLinkForm(PanelFormMixin, forms.ModelForm):
    class Meta:
        model = SocialLink
        fields = ["label", "url", "order"]
        widgets = {"order": forms.NumberInput(attrs={"min": 0})}


OpeningHoursFormSet = forms.inlineformset_factory(
    Restaurant, OpeningHours, form=OpeningHoursForm, extra=1, can_delete=True
)
SocialLinkFormSet = forms.inlineformset_factory(
    Restaurant, SocialLink, form=SocialLinkForm, extra=1, can_delete=True
)


class CategoryForm(PanelFormMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "slug", "description", "order", "is_active"]
        widgets = {"order": forms.NumberInput(attrs={"min": 0})}


class IngredientsField(forms.CharField):
    """Edits a list of ingredients as a textarea, one per line."""

    widget = forms.Textarea(attrs={"rows": 4})

    def prepare_value(self, value):
        if isinstance(value, list):
            return "\n".join(value)
        return value

    def to_python(self, value):
        value = super().to_python(value)
        return [line.strip() for line in value.splitlines() if line.strip()]


class DishForm(PanelFormMixin, forms.ModelForm):
    ingredients = IngredientsField(required=False, help_text="One ingredient per line.")

    class Meta:
        model = Dish
        fields = [
            "name", "category", "price", "ingredients", "description", "image", "tags",
            "is_available", "is_published", "order", "slug",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "price": forms.NumberInput(attrs={"min": 0, "step": "0.01"}),
            "order": forms.NumberInput(attrs={"min": 0}),
            "image": forms.ClearableFileInput(attrs={"accept": "image/*"}),
            "tags": forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].empty_label = "Choose a category"
        self.fields["tags"].queryset = Tag.objects.all()


class TagForm(PanelFormMixin, forms.ModelForm):
    class Meta:
        model = Tag
        fields = ["code"]

    def clean_code(self):
        return self.cleaned_data["code"].strip().lower()
