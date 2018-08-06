from django.shortcuts import render
from django.contrib.auth.models import User

from api.models import Profile,Dataset,Field,Setting,Table,Join
from api.serializers import ProfileSerializer,DatasetSeraializer,FieldSerializer,SettingSerializer,GeneralSerializer,TableSerializer,JoinSerializer,DynamicFieldsModelSerializer
from api.utils import get_model,dictfetchall

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import Http404
from rest_framework import permissions

from django.contrib import admin
from django.core.management import call_command
from django.db import connection
from django.core.cache import caches

import collections
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
            serializer.save(profile = profile)
            dataset = Dataset.objects.filter(profile__user = request.user).get(name = data['name'])
            for f in data['fields']:
                field_serializer = FieldSerializer(data = f)
                if field_serializer.is_valid():
                    field_serializer.save(dataset = dataset)
                for s in f['settings']:
                    field = Field.objects.filter(dataset__name = data['name']).get(name = f['name'])
                    settings_serializer = SettingSerializer(data = s)
                    if settings_serializer.is_valid():
                        settings_serializer.save(field = field)
            for t in data['tables']:
                table_serializer = TableSerializer(data = t)
                if table_serializer.is_valid():
                    table_serializer.save(dataset = dataset)
            for j in data['joins']:
                join_serializer = JoinSerializer(data = j)
                if join_serializer.is_valid():
                    join_serializer.save(dataset = dataset)
            model = dataset.get_django_model()
            admin.site.register(model)
            call_command('makemigrations')
            call_command('migrate')
            return Response({'message' : 'success'},status=status.HTTP_201_CREATED)
        return Response(serializer.errors,status = status.HTTP_400_BAD_REQUEST)


class DatasetDetail(APIView):

    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    def get_object(self,user,name):
        try:
            return Dataset.objects.filter(profile__user = user).get(name = name)

        except Dataset.DoesNotexist:
            return Http404


    def post(self,request):
        
        dataset = self.get_object(request.user,request.data['name'])
        model = dataset.get_django_model()
        GeneralSerializer.Meta.model = model
        
        if request.data['view_mode'] == 'view':
            data_subset = model.objects.all()
            data_serializer = GeneralSerializer(data_subset,many = True)
            return Response(data_serializer.data,status=status.HTTP_200_OK)
        else:
            tables = Table.objects.filter(dataset = dataset)
            joins = Join.objects.filter(dataset =  dataset)
            model_fields = [f.name for f in model._meta.get_fields()]
            model_data = []
            for t in tables:
                table_model = get_model(t.name,model._meta.app_label)
                DynamicFieldsModelSerializer.Meta.model = table_model
                cursor = connection.cursor()
                cursor.execute('select * from %s'%(t.name))
                table_data = dictfetchall(cursor)
                context = {
                    "request" : request,
                }
                print(table_data)
                dynamic_serializer = DynamicFieldsModelSerializer(table_data,many = True,fields = set(model_fields))
                model_data.extend(dynamic_serializer.data)
                del table_model
                # try:
                #     del caches[model._meta.app_label][t.name]
                # except KeyError:
                #     pass
            all_model_data=[]
            for x in model_data:
                all_model_data += list(x.items())
            all_model_data_dict = collections.defaultdict(list)
            for x in all_model_data:
                all_model_data_dict[x[0]].append(x[1])
            print(dict(all_model_data_dict))
            i = 0
            all_model_data_list = []
            d = {}

            for key,value in dict(all_model_data_dict).items():
                d.update({key : value[i]})
            
            all_model_data_list.append(d)
            print(all_model_data_list)
            serializer = GeneralSerializer(data = all_model_data_list,many = True)
            if serializer.is_valid():
                print('hi')
                serializer.save()
            else:
                return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
            data_subset = model.objects.all()
            data_serializer = GeneralSerializer(data_subset,many = True)
            return Response(data_serializer.data,status=status.HTTP_200_OK)
        return Response({'message' : 'error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)