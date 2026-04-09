from django import template

register = template.Library()


@register.filter
def percentage(value, total):
    if not total:
        return "0%"
    return f"{(value / total) * 100:.1f}%"


@register.filter
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def dict_get(d, key):
    """Get a value from a dictionary by key."""
    if isinstance(d, dict):
        return d.get(key)
    return None
