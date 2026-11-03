"""Formatting helpers for analysis templates."""

from django import template
from django.utils.formats import number_format

from ..presenters import f1 as format_f1

register = template.Library()


@register.filter
def f1(value):
    """Thesis F1 with four decimals in the active locale, or "–" when the thesis has no value."""
    return format_f1(value)


@register.filter
def seconds(milliseconds):
    """Duration in milliseconds as seconds ("1,2" in Indonesian; two decimals below one second)."""
    if milliseconds in (None, ""):
        return "–"
    value = int(milliseconds) / 1000
    return number_format(value, 1 if value >= 1 else 2)
