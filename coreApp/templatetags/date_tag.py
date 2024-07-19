from django import template
import datetime

register = template.Library()


@register.filter
def custom_date(value):
    if isinstance(value, datetime.date):
        return (
            value.strftime("%d").lstrip("0")
            + get_day_suffix(value.day)
            + value.strftime(" %B")
        )
    return value


def get_day_suffix(day):
    if 4 <= day <= 20 or 24 <= day <= 30:
        return "th"
    else:
        return ["st", "nd", "rd"][day % 10 - 1]
