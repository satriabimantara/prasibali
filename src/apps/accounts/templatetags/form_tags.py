"""Render form fields with the DESIGN.md form pattern (label above, errors below, ARIA links)."""

from django import forms, template

register = template.Library()


def widget_kind(field):
    widget = field.field.widget
    if isinstance(widget, forms.CheckboxInput):
        return "checkbox"
    if isinstance(widget, forms.Select | forms.SelectMultiple):
        return "select"
    if isinstance(widget, forms.Textarea):
        return "textarea"
    if isinstance(widget, forms.HiddenInput):
        return "hidden"
    return "input"


@register.inclusion_tag("partials/form_field.html")
def form_field(field, label_override=None):
    """Render one bound field. `label_override` replaces the label text (still escaped)."""
    kind = widget_kind(field)
    describedby = []
    if field.errors:
        describedby.append(f"{field.auto_id}_error")
    if field.help_text:
        describedby.append(f"{field.auto_id}_helptext")

    attrs = {"class": {"checkbox": "checkbox", "select": "select", "textarea": "input"}.get(kind, "input")}
    if describedby:
        attrs["aria-describedby"] = " ".join(describedby)
    if field.errors:
        attrs["aria-invalid"] = "true"
    # Allauth sets placeholders that duplicate the label; DESIGN.md: placeholder never replaces a label.
    field.field.widget.attrs.pop("placeholder", None)

    return {
        "field": field,
        "kind": kind,
        "widget": field.as_widget(attrs=attrs),
        "label": label_override or field.label,
    }
