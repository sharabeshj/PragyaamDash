# Generated by Django 2.0.7 on 2018-09-05 16:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0002_dataset_2'),
    ]

    operations = [
        migrations.CreateModel(
            name='Worksheet 1',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=20)),
                ('price', models.IntegerField()),
                ('date_of_birth', models.CharField(max_length=20)),
                ('sl_no', models.IntegerField()),
                ('quality_no', models.IntegerField()),
                ('address', models.CharField(max_length=20)),
                ('pincode', models.CharField(max_length=20)),
                ('zip_code', models.CharField(max_length=20)),
                ('sales_data', models.CharField(max_length=20)),
            ],
            options={
                'db_table': 'Worksheet 1',
            },
        ),
    ]
