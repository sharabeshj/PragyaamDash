from django.shortcuts import render
from django.contrib.auth.models import User

from api.models import Profile,Dataset,Field,Setting
from api.serializers import ProfileSerializer,DatasetSeraializer,FieldSerializer,SettingSerializer

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import Http404
from rest_framework import permissions

# Create your views here.

class ProfileDetail(APIView):

    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    def get_object(self,user):
        try: 
            return Profile.objects.get(user = user)
        except Profile.DoesNotexist:
            raise Http404
    
    def get(self,request):
        
        profile = self.get_object(request.user)
        serializer = ProfileSerializer(profile)
        return Response(serializer.data,status=status.HTTP_200_OK)

class DatasetList(APIView):

    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    def get(self,request):
        
        datasets = Dataset.objects.all()
        serializer = DatasetSeraializer(datasets, many = True)

        return Response(serializer.data,status = status.HTTP_200_OK)

    def post(self,request):

        data = request.data
        profile = Profile.objects.get(user = request.user)
        serializer = DatasetSeraializer(data = data)
        if serializer.is_valid():
            print('hi')
            serializer.save(profile = profile)
            for f in data['fields']:
                dataset = Dataset.objects.get(name = data['name'])
                field_serializer = FieldSerializer(data = f)
                if field_serializer.is_valid():
                    field_serializer.save(dataset = dataset)
                for s in f['settings']:
                    field = Field.objects.get(name = f['name'])
                    settings_serializer = SettingSerializer(data = s)
                    if settings_serializer.is_valid():
                        settings_serializer.save(field = field)
            return Response({'message' : 'success'},status=status.HTTP_201_CREATED)
        return Response(serializer.errors,status = status.HTTP_400_BAD_REQUEST)


class DatasetDetail(APIView):

    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    def get(self,request):
        pass
