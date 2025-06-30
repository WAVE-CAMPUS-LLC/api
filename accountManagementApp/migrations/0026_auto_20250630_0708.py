from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accountManagementApp", "0025_auto_20250630_0657"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                -- Clean up double-encoded JSON strings like '"\\"night\\""' to just '"night"'
                UPDATE "accountManagementApp_userpreferences" 
                SET preffered_times = (preffered_times #>> '{}')::jsonb
                WHERE preffered_times::text ~ '^".*"$' 
                AND preffered_times::text ~ '\\\\"';
            """,
            reverse_sql="""
                -- No reverse needed since we're just cleaning data
                SELECT 1;
            """,
        ),
    ]
