# Generated by Django 2.0.7 on 2018-09-05 17:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0019_delete_worksheet 2'),
    ]

    operations = [
        migrations.CreateModel(
            name='Worksheet 2',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=20)),
                ('price', models.IntegerField()),
                ('sales_info', models.CharField(max_length=20)),
            ],
            options={
                'db_table': 'Worksheet 2',
            },
        ),
    ]
