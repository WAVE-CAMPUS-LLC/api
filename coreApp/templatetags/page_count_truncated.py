
from django import template

register = template.Library()

@register.filter
def page_count_truncated(page_count):
    if page_count >= 6:
       
        return list(range(1,4)) + ['...'] + list(range(page_count-2, page_count+1))
    else:
        return range(1, page_count+1)