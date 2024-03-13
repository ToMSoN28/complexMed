# Generated by Django 5.0.2 on 2024-03-02 12:59

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Patient',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=100)),
                ('last_name', models.CharField(max_length=100)),
                ('birthday', models.DateTimeField()),
                ('pesel', models.CharField(max_length=11, unique=True)),
                ('phone_number', models.CharField(max_length=15)),
            ],
        ),
        migrations.CreateModel(
            name='Visit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('free', 'Free'), ('occupied', 'Occupied')], default='free', max_length=10)),
                ('name', models.CharField(max_length=255)),
                ('date', models.DateField()),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('progress', models.TextField()),
                ('results', models.TextField()),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('room', models.CharField(max_length=50)),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='complexApp.patient')),
            ],
        ),
        migrations.AddField(
            model_name='patient',
            name='visits',
            field=models.ManyToManyField(blank=True, related_name='patient_visits', to='complexApp.visit'),
        ),
        migrations.CreateModel(
            name='Worker',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_doctor', models.BooleanField(default=False)),
                ('is_receptionist', models.BooleanField(default=False)),
                ('is_manager', models.BooleanField(default=False)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('visits', models.ManyToManyField(blank=True, related_name='doctor_visits', to='complexApp.visit')),
            ],
        ),
        migrations.AddField(
            model_name='visit',
            name='doctor',
            field=models.ForeignKey(limit_choices_to={'is_doctor': True}, on_delete=django.db.models.deletion.CASCADE, to='complexApp.worker'),
        ),
    ]
