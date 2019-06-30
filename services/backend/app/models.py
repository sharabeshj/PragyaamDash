from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import ValidationError
from django_mysql.models import JSONField
from django_celery_beat.models import PeriodicTask

from app.utils import create_model

import uuid

# Create your models here.

class Dataset(models.Model):

    mode_choices = (
        ('VIZ', 'VIZ'),
        ('SQL', 'SQL'),
    )
     
    organization_id = models.CharField(max_length = 30)
    user = models.CharField(max_length = 100)
    userId = models.CharField(max_length=30)
    name = models.CharField(max_length = 50)
    dataset_id = models.UUIDField(primary_key = True, default = uuid.uuid4, editable = False)
    sql = models.TextField(null=True)
    mode = models.CharField(max_length = 3, choices = mode_choices, default = 'VIZ')
    model = JSONField()
    scheduler = models.ForeignKey(PeriodicTask, null=True,related_name = 'datasets', on_delete = models.SET_NULL)
    last_refreshed_at = models.DateTimeField(null = True)

    def __str__(self):
         return self.name

    def get_django_model(self):

        fields = [(f.name, f.get_django_field()) for f in self.fields.all()]
        fields.append(tuple(('id',getattr(models,'IntegerField')(**dict([('primary_key' ,True)])))))

        return create_model(self.name, dict(fields), self._meta.app_label,options={'db_table' : self.name})

    class Meta:
        unique_together = (('user','name'),)
    
def is_valid_field(field_data):

    if hasattr(models,field_data) and issubclass(getattr(models, field_data), models.Field):
        return
    raise ValidationError("This is not a valid field type.")

class Field(models.Model):
    
    dataset = models.ForeignKey(Dataset, related_name = 'fields',on_delete = models.CASCADE)
    name = models.CharField(max_length =  50)
    type = models.CharField(max_length = 50, validators = [is_valid_field])
    worksheet = models.CharField(max_length = 50)

    def get_django_field(self):

        settings = [(s.name,s.value) for s in self.settings.all()]
        settings.append(tuple(('blank',True)))
        settings.append(tuple(('null',True)))

        return getattr(models, self.type)(**dict(settings))
    
    class Meta:
        unique_together = (('dataset','name','worksheet'),)
    
class Setting(models.Model):

    field = models.ForeignKey(Field, related_name = 'settings',on_delete = models.CASCADE)
    name = models.CharField(max_length = 50)
    value = models.IntegerField()

    class Meta:
        unique_together = (('field','name'))


class Table(models.Model):

    dataset = models.ForeignKey(Dataset,related_name = 'tables',on_delete = models.CASCADE)
    name = models.CharField(max_length = 50)
    key = models.CharField(max_length = 100)

    def __str__(self):
        return self.name

class Join(models.Model):

    dataset = models.ForeignKey(Dataset,related_name = 'joins',on_delete = models.CASCADE)
    type = models.CharField(max_length = 50)
    field_1 = models.CharField(max_length = 50)
    field_2 = models.CharField(max_length = 50)
    worksheet_1 = models.CharField(max_length = 50)
    worksheet_2 = models.CharField(max_length = 50)
    key = models.CharField(max_length = 100)

class Dashboard(models.Model):

    dashboard_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable = False)
    user = models.CharField(max_length=100)
    userId = models.CharField(max_length=30)
    organization_id = models.CharField(max_length = 30)
    name = models.CharField(max_length = 50)
    description = JSONField()
    last_updated_at = models.DateTimeField(null = True)

class Report(models.Model):
    
    organization_id = models.CharField(max_length = 30)
    dataset = models.ForeignKey(Dataset,related_name = 'reports',null = True, on_delete = models.CASCADE)
    worksheet = models.CharField(max_length = 50, null = True)
    dashboards = models.ManyToManyField(Dashboard, related_name = 'reports')
    user = models.CharField(max_length=100)
    userId = models.CharField(max_length=30)
    report_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable = False)
    data = JSONField()
    last_updated_at = models.DateTimeField(null = True)

class DashboardReportOptions(models.Model):

    dashboard = models.ForeignKey(Dashboard, related_name='dashboard_report_options', on_delete=models.CASCADE)
    report = models.ForeignKey(Report, related_name = 'dashboard_report_options', on_delete = models.CASCADE)
    reportOptions = JSONField()

class Filter(models.Model):

    filter_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable = False)
    dataset = models.ForeignKey(Dataset, related_name = 'filters', on_delete = models.CASCADE)
    report = models.ForeignKey(Report, null = True,related_name='filters',on_delete = models.CASCADE)
    dashboard_reports = models.ManyToManyField(DashboardReportOptions, blank = True, related_name = 'filters')
    user = models.CharField(max_length=30)
    organization_id = models.CharField(max_length = 30)
    field_name = models.CharField(max_length = 50)
    options = JSONField()
    activate = models.BooleanField(default=True)

class SharedReport(models.Model):

    report = models.ForeignKey(Report, related_name = 'shared', on_delete= models.CASCADE)
    shared_user_id = models.CharField(max_length=30)
    user_id = models.CharField(max_length=30)
    view = models.BooleanField(default= False)
    edit = models.BooleanField(default=False)
    delete = models.BooleanField(default=False)

class SharedDashboard(models.Model):

    dashboard = models.ForeignKey(Dashboard, related_name = 'shared_users', on_delete = models.CASCADE)
    shared_user_id = models.CharField(max_length=30)
    user_id = models.CharField(max_length=30)
    view = models.BooleanField(default= False)
    edit = models.BooleanField(default=False)
    delete = models.BooleanField(default=False)