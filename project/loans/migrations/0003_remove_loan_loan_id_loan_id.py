# Generated by Django 5.1.3 on 2024-11-14 23:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('loans', '0002_rename_customer_loan_customer_id_remove_customer_id_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='loan',
            name='loan_id',
        ),
        migrations.AddField(
            model_name='loan',
            name='id',
            field=models.BigAutoField(auto_created=True, default='1', primary_key=True, serialize=False, verbose_name='ID'),
            preserve_default=False,
        ),
    ]
