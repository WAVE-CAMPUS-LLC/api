from django import template

register = template.Library()

@register.filter
def get_category(dictionary, key):
    return dictionary.get(key)