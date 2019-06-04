from rest_framework import serializers
from app.models import Dataset,Field,Setting,Table,Join,Report, SharedReport, Dashboard, Filter, DashboardReportOptions, SharedDashboard
from django_celery_beat.models import PeriodicTask
import uuid

class DatasetSeraializer(serializers.ModelSerializer):

    scheduler = serializers.ReadOnlyField(source='periodicTask.last_run_at')
    fields = serializers.SlugRelatedField(many = True, slug_field='name',read_only = True)
    dataset_id = serializers.UUIDField(default = uuid.uuid4)

    class Meta:
        model = Dataset
        fields = ('dataset_id','organization_id','name','fields','user', 'sql', 'mode', 'scheduler')

class FieldSerializer(serializers.ModelSerializer):

    dataset = serializers.ReadOnlyField(source = 'dataset.name')
    settings = serializers.SlugRelatedField(many = True, slug_field='name',read_only = True)

    class Meta:
        model = Field
        fields = ('dataset','name','worksheet','type','settings')

class SettingSerializer(serializers.ModelSerializer):

    field = serializers.ReadOnlyField(source = 'field.name')

    class Meta:
        model = Setting
        fields = ('field','name','value')

class TableSerializer(serializers.ModelSerializer):

    dataset = serializers.ReadOnlyField(source = 'dataset.name')

    class Meta:
        model = Table
        fields = ('dataset','name')

class JoinSerializer(serializers.ModelSerializer):

    dataset = serializers.ReadOnlyField(source = 'dataset.name')

    class Meta:
        model = Join
        fields = ('dataset','type','field','worksheet_1','worksheet_2')

class GeneralSerializer(serializers.ModelSerializer):

    class Meta:
        model = None
        fields = '__all__'


class DynamicFieldsModelSerializer(serializers.ModelSerializer):

    def __init__(self,*args,**kwargs):

        fields = kwargs.pop('fields', None)

        super(DynamicFieldsModelSerializer,self).__init__(*args,**kwargs)

        if fields is not None:

            allowed = set(fields)
            existing = set(self.fields.keys())
            for field_name in existing - allowed:
                self.fields.pop(field_name)
            print(self.fields)
    
    class Meta:
        model = None
        fields = '__all__'


class ReportSerializer(serializers.ModelSerializer):

    dataset = serializers.ReadOnlyField(source = 'dataset.name')
    report_id = serializers.UUIDField(default = uuid.uuid4)
    filters = serializers.SlugRelatedField(many=True, slug_field = 'field_name', read_only=True)

    class Meta:
        model = Report
        fields = ('report_id','dataset','user','organization_id','data', 'filters')


class SharedReportSerializer(serializers.ModelSerializer):

    report = serializers.ReadOnlyField(source = 'report.name')
    view = serializers.BooleanField(default=False)
    edit = serializers.BooleanField(default=False)
    delete = serializers.BooleanField(default=False)

    class Meta:
        model = SharedReport
        fields = ('report', 'shared_user_id','user_id','view','edit','delete')


class DashboardSerializer(serializers.ModelSerializer):

    dashboard_id = serializers.UUIDField(default = uuid.uuid4)
    reports = serializers.SlugRelatedField(many = True, slug_field='name',read_only = True)
    dashboard_report_options = serializers.PrimaryKeyRelatedField(many=True, read_only = True)

    class Meta:
        model = Dashboard
        fields = ('dashboard_id', 'organization_id','name', 'description', 'reports', 'user','dashboard_report_options')

class DashboardReportOptionsSerializer(serializers.ModelSerializer):

    filters = serializers.SlugRelatedField(many = True, slug_field = 'field_name', read_only=True)
    dashboard = serializers.ReadOnlyField(source = 'dashboard.name')
    report = serializers.ReadOnlyField(source = 'report.report_id')

    class Meta:
        model = DashboardReportOptions
        fields = ('dashboard','report', 'filters', 'reportOptions')

class SharedDashboardSerializer(serializers.ModelSerializer):

    dashboard = serializers.ReadOnlyField(source = 'dashbaord.name')

    class Meta:
        model = SharedDashboard
        fields = ('dashbaoard', 'shared_user_id', 'user_id', 'view', 'edit', 'delete')

class FilterSerializer(serializers.ModelSerializer):

    filter_id = serializers.UUIDField(default = uuid.uuid4)

    class Meta:
        model = Filter
        fields = ('filter_id', 'field_name', 'field_operation', 'options')

