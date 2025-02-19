from django import template
from datetime import datetime
import pytz

register = template.Library()

@register.filter(name='timestamp')
def convert_timestamp(timestamp):
    """Convert a Unix timestamp to a datetime object."""
    try:
        # Convert the timestamp to an integer if it's not already
        ts = int(float(timestamp))
        # Create a UTC datetime from timestamp
        dt = datetime.fromtimestamp(ts, tz=pytz.UTC)
        return dt
    except (ValueError, TypeError):
        return None 