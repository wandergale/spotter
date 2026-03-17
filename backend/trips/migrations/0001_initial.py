from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='GeocodingCache',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('query', models.CharField(db_index=True, max_length=500, unique=True)),
                ('lat', models.FloatField()),
                ('lon', models.FloatField()),
                ('display_name', models.CharField(max_length=1000)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='TripRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('current_location', models.CharField(max_length=500)),
                ('pickup_location', models.CharField(max_length=500)),
                ('dropoff_location', models.CharField(max_length=500)),
                ('current_cycle_used', models.FloatField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='TripResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('response_data', models.JSONField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('trip_request', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='result',
                    to='trips.triprequest',
                )),
            ],
        ),
    ]
