from rest_framework import serializers
from app.models import Dataset,Field,Setting,Table,Join,Report, SharedReport, Dashboard
import uuid

class DatasetSeraializer(serializers.ModelSerializer):

    fields = serializers.SlugRelatedField(many = True, slug_field='name',read_only = True)
    dataset_id = serializers.UUIDField(default = uuid.uuid4)

    class Meta:
        model = Dataset
        fields = ('dataset_id','organization_id','name','fields','user', 'sql', 'mode')

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

    class Meta:
        model = Report
        fields = ('report_id','dataset','user','organization_id','data')


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

    class Meta:
        model = Dashboard
        fields = ('dashboard_id', 'organization_id','reports', 'user')