# Generated by Django 2.2 on 2021-02-22 05:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_auto_20210221_1342'),
    ]

    operations = [
        migrations.AddField(
            model_name='item',
            name='image',
            field=models.ImageField(default='null', upload_to=''),
            preserve_default=False,
        ),
    ]