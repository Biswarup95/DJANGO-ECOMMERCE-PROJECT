# Generated by Django 5.0.4 on 2024-05-13 08:02

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='category',
            old_name='slug_field',
            new_name='slug',
        ),
        migrations.RenameField(
            model_name='product',
            old_name='slug_field',
            new_name='slug',
        ),
    ]
