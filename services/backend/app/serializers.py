from rest_framework import serializers
from app.models import Dataset,Field,Setting,Table,Join,Report, SharedReport, Dashboard, Filter, DashboardReportOptions, SharedDashboard
from django_celery_beat.models import PeriodicTask
import uuid

class SettingSerializer(serializers.ModelSerializer):

    field = serializers.ReadOnlyField(source = 'field.name')

    class Meta:
        model = Setting
        fields = ('field','name','value')

class TableSerializer(serializers.ModelSerializer):

    dataset = serializers.ReadOnlyField(source = 'dataset.dataset_id')

    class Meta:
        model = Table
        fields = ('dataset','name','key')

class JoinSerializer(serializers.ModelSerializer):

    dataset = serializers.ReadOnlyField(source = 'dataset.dataset_id')

    class Meta:
        model = Join
        fields = ('dataset','key','type','field_1','field_2','worksheet_1','worksheet_2')

class FieldSerializer(serializers.ModelSerializer):

    dataset = serializers.ReadOnlyField(source = 'dataset.dataset_id')
    settings = SettingSerializer(many = True,read_only = True)

    class Meta:
        model = Field
        fields = ('dataset','name','worksheet','type','settings')

class DatasetSerializer(serializers.ModelSerializer):

    scheduler = serializers.ReadOnlyField(source='periodicTask.id')
    fields = FieldSerializer(many = True,read_only = True)
    joins = JoinSerializer(many=True, read_only = True)
    tables = TableSerializer(many=True,read_only=True)
    dataset_id = serializers.UUIDField(default = uuid.uuid4)
    model = serializers.JSONField()

    class Meta:
        model = Dataset
        fields = ('dataset_id','organization_id','name','fields','joins','tables','user', 'userId', 'sql', 'mode','model', 'scheduler','last_refreshed_at')

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

class FilterSerializer(serializers.ModelSerializer):

    filter_id = serializers.UUIDField(default = uuid.uuid4)
    activate = serializers.BooleanField(default = True)
    options = serializers.JSONField()
    report = serializers.ReadOnlyField(source='report.report_id',allow_null = True)
    dashboard_reports = serializers.ReadOnlyField(source='dashboard_report_options.dashboard.dashboard_id',allow_null = True)

    class Meta:
        model = Filter
        fields = ('filter_id', 'field_name', 'options','activate','report','dashboard_reports')


class ReportSerializer(serializers.ModelSerializer):

    dataset = serializers.ReadOnlyField(source='dataset.dataset_id')
    report_id = serializers.UUIDField(default = uuid.uuid4)
    filters = FilterSerializer(many=True, read_only=True)

    class Meta:
        model = Report
        fields = ('report_id','worksheet','dataset','user','userId','organization_id','data', 'filters','last_updated_at')


class SharedReportSerializer(serializers.ModelSerializer):

    report = serializers.ReadOnlyField(source = 'report.name')
    view = serializers.BooleanField(default=False)
    edit = serializers.BooleanField(default=False)
    delete = serializers.BooleanField(default=False)

    class Meta:
        model = SharedReport
        fields = ('report', 'shared_user_id','user_id','view','edit','delete')


class DashboardReportOptionsSerializer(serializers.ModelSerializer):

    filters = FilterSerializer(many=True, read_only=True)
    dashboard = serializers.ReadOnlyField(source = 'dashboard.dashboard_id')
    report = serializers.ReadOnlyField(source = 'report.report_id')
    reportOptions = serializers.JSONField()

    class Meta:
        model = DashboardReportOptions
        fields = '__all__'

class SharedDashboardSerializer(serializers.ModelSerializer):

    dashboard = serializers.ReadOnlyField(source = 'dashboard.dashboard_id')

    class Meta:
        model = SharedDashboard
        fields = ('dashboard', 'shared_user_id', 'user_id', 'view', 'edit', 'delete')


class DashboardSerializer(serializers.ModelSerializer):

    dashboard_id = serializers.UUIDField(default = uuid.uuid4)
    reports = ReportSerializer(many=True, read_only=True)
    dashboard_report_options = DashboardReportOptionsSerializer(many=True, read_only = True)
    shared_users = SharedDashboardSerializer(many=True,read_only = True)
    description = serializers.JSONField()

    class Meta:
        model = Dashboard
        fields = '__all__'

