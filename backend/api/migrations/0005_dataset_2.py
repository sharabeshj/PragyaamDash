# Generated by Django 2.0.7 on 2018-08-07 22:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_test_table_2'),
    ]

    operations = [
        migrations.CreateModel(
            name='dataset_2',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('field_2', models.CharField(max_length=20)),
                ('field_4', models.TextField()),
            ],
        ),
    ]
