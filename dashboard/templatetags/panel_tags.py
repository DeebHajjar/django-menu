from decimal import Decimal, InvalidOperation

from django import forms, template

register = template.Library()

# Same as currencyLabels in the front end's js/config.js.
CURRENCY_LABELS = {"LBP": "L.L."}


@register.filter
def price(value, currency="LBP"):
    """400000.00 → "400,000 L.L.", 18.50 → "18.50 USD" (decimals only when present)."""
    try:
        amount = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return value
    number = f"{amount:,.0f}" if amount == amount.to_integral_value() else f"{amount:,.2f}"
    currency = (currency or "LBP").upper()
    return f"{number} {CURRENCY_LABELS.get(currency, currency)}".strip()


@register.filter
def is_checkbox(field):
    return isinstance(field.field.widget, forms.CheckboxInput)


@register.filter
def is_multi_checkbox(field):
    return isinstance(field.field.widget, forms.CheckboxSelectMultiple)


@register.filter
def is_file(field):
    return isinstance(field.field.widget, forms.ClearableFileInput)
