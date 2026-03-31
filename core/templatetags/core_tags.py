from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def replace(value, arg):
    """
    Usage: {{ value|replace:"old,new" }}
    """
    if ',' not in arg:
        return value
    old, new = arg.split(',')
    return value.replace(old, new)
