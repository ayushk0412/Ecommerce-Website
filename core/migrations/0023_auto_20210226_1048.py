# Generated by Django 2.2 on 2021-02-26 05:18

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_refund'),
    ]

    operations = [
        migrations.RenameField(
            model_name='refund',
            old_name='Order',
            new_name='order',
        ),
    ]