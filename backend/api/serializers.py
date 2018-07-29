from rest_framework import serializers
from api.models import Profile,Dataset

class ProfileSerializer(serializers.ModelSerializer):
    
    user = serializers.PrimaryKeyRelatedField(source = 'users.id')

    class Meta:
        model = Profile
        fields = ('user')
    