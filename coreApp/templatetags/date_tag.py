from django import template
import datetime
from decimal import Decimal

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


@register.filter
def calculate_service_fee(price):
    """Calculate the service fee (7% of price + $0.99)"""
    try:
        price = float(price)
        return round(price * 0.07 + 0.99, 2)
    except (ValueError, TypeError):
        return 0


@register.filter
def calculate_total_price(price):
    """Calculate the total price (price + service fee)"""
    try:
        price = float(price)
        service_fee = price * 0.07 + 0.99
        return round(price + service_fee, 2)
    except (ValueError, TypeError):
        return 0
