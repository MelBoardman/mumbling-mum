# Generated by Django 3.1 on 2020-09-08 19:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('items', '0004_item_sku'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='item',
            name='star_rating',
        ),
        migrations.AlterField(
            model_name='item',
            name='sku',
            field=models.CharField(blank=True, editable=False, max_length=254, null=True),
        ),
    ]
