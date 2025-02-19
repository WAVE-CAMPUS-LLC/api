from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('eventManagementApp', '0002_privacy_to_display_fields'),
    ]

    operations = [
        migrations.RunSQL(
            # Forward SQL - Drop any remaining references to the privacy column
            "DROP INDEX IF EXISTS eventManagementApp_event_privacy_idx;",
            # Reverse SQL - Do nothing
            "SELECT 1;"
        ),
    ]
