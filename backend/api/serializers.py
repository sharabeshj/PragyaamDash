from rest_framework import serializers
from api.models import Profile,Dataset,Field,Setting

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
        fields = ('dataset','name','type','settings')

class SettingSerializer(serializers.ModelSerializer):

    field = serializers.ReadOnlyField(source = 'field.name')

    class Meta:
        model = Setting
        fields = ('field','name','value')