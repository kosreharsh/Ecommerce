# Generated by Django 2.2.5 on 2021-03-28 03:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0017_auto_20210309_1731'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='coupon',
        ),
        migrations.AddField(
            model_name='order',
            name='coupon',
            field=models.ManyToManyField(blank=True, to='main.Coupon'),
        ),
    ]