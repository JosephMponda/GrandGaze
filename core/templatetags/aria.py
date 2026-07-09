from django import template

register = template.Library()


@register.filter(name="aria_field")
def aria_field(field):
    """Add aria-describedby to field widget when errors exist."""
    if field.errors and field.id_for_label:
        field.field.widget.attrs["aria-describedby"] = f"{field.id_for_label}_error"
    return field
