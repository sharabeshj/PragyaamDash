from rest_framework import serializers
from app.models import Dataset,Field,Setting,Table,Join,Report, SharedReport, Dashboard, Filter, DashboardReportOptions, SharedDashboard
from django_celery_beat.models import PeriodicTask,CrontabSchedule
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

class CrontabSeriaizer(serializers.ModelSerializer):
    class Meta:
        model = CrontabSchedule
        fields = ('minute','hour','day_of_week', 'day_of_month','month_of_year')

class PeriodicTaskSerializer(serializers.ModelSerializer):
    
    crontab = CrontabSeriaizer(read_only = True)
    class Meta:
        model = PeriodicTask
        fields = '__all__'
class DatasetUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dataset
        fields = '__all__'


class DatasetSerializer(serializers.ModelSerializer):

    scheduler = serializers.ReadOnlyField(source = 'scheduler.id', allow_null=True)
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
class FilterUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Filter
        fields = '__all__'



class FilterSerializer(serializers.ModelSerializer):

    filter_id = serializers.UUIDField(default = uuid.uuid4)
    activate = serializers.BooleanField(default = True)
    options = serializers.JSONField()
    report = serializers.ReadOnlyField(source='report.report_id',allow_null = True)
    dashboard = serializers.ReadOnlyField(source='dashboard.dashboard_id',allow_null = True)

    class Meta:
        model = Filter
        fields = '__all__'

class ReportUpdateSerializer(serializers.ModelSerializer):
     class Meta:
        model = Report
        fields = ('organization_id','dataset','worksheet','user','userId','report_id','data','last_updated_at')

class ReportSerializer(serializers.ModelSerializer):

    dataset = DatasetSerializer(read_only=True)
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



class DashboardUpdateSerializer(serializers.ModelSerializer):
    reports = ReportSerializer(many=True, read_only=True)
    dashboard_report_options = DashboardReportOptionsSerializer(many=True, read_only = True)
    shared_users = SharedDashboardSerializer(many=True,read_only = True)
    description = serializers.JSONField()
    filters = FilterSerializer(many=True, read_only=True)
    class Meta:
        model = Dashboard
        fields = '__all__'


class DashboardSerializer(serializers.ModelSerializer):

    dashboard_id = serializers.UUIDField(default = uuid.uuid4)
    reports = ReportSerializer(many=True, read_only=True)
    dashboard_report_options = DashboardReportOptionsSerializer(many=True, read_only = True)
    shared_users = SharedDashboardSerializer(many=True,read_only = True)
    description = serializers.JSONField()
    filters = FilterSerializer(many=True, read_only=True)

    class Meta:
        model = Dashboard
        fields = '__all__'

