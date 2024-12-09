# Generated by Django 4.2.7 on 2024-12-08 18:56

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0002_useractivity'),
    ]

    operations = [
        migrations.AlterField(
            model_name='serverconfiguration',
            name='project',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='servers', to='projects.project'),
        ),
    ]
