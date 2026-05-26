from django.db import migrations

def seed_source_types(apps, schema_editor):
    SourceType = apps.get_model('core', 'SourceType')
    SourceType.objects.get_or_create(code='sap_fuel', defaults={'label': 'SAP Fuel & Procurement', 'scope': 1})
    SourceType.objects.get_or_create(code='utility_elec', defaults={'label': 'Utility Electricity', 'scope': 2})
    SourceType.objects.get_or_create(code='corporate_travel', defaults={'label': 'Corporate Travel', 'scope': 3})

def unseed_source_types(apps, schema_editor):
    SourceType = apps.get_model('core', 'SourceType')
    SourceType.objects.all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_source_types, reverse_code=unseed_source_types),
    ]
