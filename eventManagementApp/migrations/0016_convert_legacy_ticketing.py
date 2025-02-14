from django.db import migrations

def update_ticketing_values(apps, schema_editor):
    Event = apps.get_model('eventManagementApp', 'Event')
    # Update any remaining events with legacy ticketing values
    Event.objects.filter(ticketing='RSVP Required').update(ticketing='Free')
    Event.objects.filter(ticketing='Invite Required').update(ticketing='Free')
    # Catch any other non-standard values
    Event.objects.exclude(ticketing__in=['Paid', 'Free', '']).update(ticketing='Free')

def reverse_migration(apps, schema_editor):
    pass  # No reverse migration needed as we can't determine original values

class Migration(migrations.Migration):
    dependencies = [
        ('eventManagementApp', '0015_update_event_ticketing_choices'),  # Make sure this runs after the other changes
    ]

    operations = [
        migrations.RunPython(update_ticketing_values, reverse_migration),
    ]