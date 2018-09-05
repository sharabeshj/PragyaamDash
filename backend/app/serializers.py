from rest_framework import serializers
from app.models import Profile,Dataset,Field,Setting,Table,Join

class ProfileSerializer(serializers.ModelSerializer):
    
    user = serializers.ReadOnlyField(source = 'user.username')
    datasets = serializers.SlugRelatedField( many = True, slug_field = 'name',read_only = True)

    class Meta:
        model = Profile
        fields = ('user','datasets')

class DatasetSeraializer(serializers.ModelSerializer):

    profile = serializers.ReadOnlyField(source = 'profile.user.username')
    fields = serializers.SlugRelatedField(many = True, slug_field='name',read_only = True)

    class Meta:
        model = Dataset
        fields = ('profile','name','fields')

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
    
    class Meta:
        model = None
        fields = '__all__'
