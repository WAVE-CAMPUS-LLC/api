from django.db import migrations, models

def migrate_privacy_to_display_fields(apps, schema_editor):
    Event = apps.get_model('eventManagementApp', 'Event')
    
    # Update all events
    events = Event.objects.all()
    for event in events:
        # In case privacy field doesn't exist, use a default value
        privacy_value = getattr(event, 'privacy', 'Discoverable')
        
        if privacy_value == "Discoverable":
            event.forAllDisplay = True
            event.forCollegesDisplay = False
        elif privacy_value in ["Private (College)", "Invite Only", "Private (Organization)"]:
            event.forAllDisplay = True
            event.forCollegesDisplay = True
        else:
            # Default values for any other case
            event.forAllDisplay = True
            event.forCollegesDisplay = False
        event.save()

def reverse_migrate(apps, schema_editor):
    Event = apps.get_model('eventManagementApp', 'Event')
    for event in Event.objects.all():
        # Convert back to privacy field
        if event.forAllDisplay and not event.forCollegesDisplay:
            event.privacy = "Discoverable"
        elif event.forAllDisplay and event.forCollegesDisplay:
            event.privacy = "Private (College)"
        event.save()

class Migration(migrations.Migration):

    dependencies = [
        ('eventManagementApp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='forAllDisplay',
            field=models.BooleanField(default=True, verbose_name='Make event discoverable by all?'),
        ),
        migrations.AddField(
            model_name='event',
            name='forCollegesDisplay',
            field=models.BooleanField(default=False, verbose_name='Make event discoverable in colleges?'),
        ),
        migrations.RunPython(migrate_privacy_to_display_fields, reverse_migrate),
        migrations.AlterField(
            model_name='event',
            name='privacy',
            field=models.CharField(default='', max_length=23, null=True, blank=True),
        ),
        migrations.RemoveField(
            model_name='event',
            name='privacy',
        ),
    ]
