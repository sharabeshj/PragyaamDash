from django.shortcuts import render
from django.contrib.auth.models import User

from app.models import Dataset,Field,Setting,Table,Join,Profile,Report
from app.serializers import DatasetSeraializer,FieldSerializer,SettingSerializer,GeneralSerializer,TableSerializer,JoinSerializer,DynamicFieldsModelSerializer,ProfileSerializer,ReportSerializer
from app.utils import get_model,dictfetchall, getColumnList

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import Http404
from rest_framework import permissions,exceptions
from rest_framework import viewsets,generics
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.authtoken.models import Token

from django.contrib import admin
from django.core.management import call_command
from django.db import connections
from django.core.cache import caches
from django.db.migrations.recorder import MigrationRecorder
from django.core.management.commands import sqlmigrate
from django.urls import resolve
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User

import collections
import json
import time
from django_pandas.io import read_frame
# import matplotlib.pyplot as plt
# import mpld3
import numpy as np
import random
import os
import requests
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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

class LoginView(APIView):

    permission_classes = (permissions.AllowAny, )
    
    def post(self, request):
        
        data = { 'organization_id': request.data['organisation_id'], 'email': request.data['user_email'], 'password': request.data['password'], 'source' : 'web', 'timestamp' : time.time() }
        status = requests.post('http://dev-blr-b.pragyaam.in/api/login', data = data)
        if status.status_code == 200:
            res_data = json.loads(status.text)['data']
            user = authenticate(username=request.data['user_email'], password=request.data['password'])
            if user is not None:
                if user.is_active:
                    login(request, user)
                    auth_token,_ = Token.objects.get_or_create(user=user)
                    return Response({ 'status': 'success', 'data' : {'token': res_data['token'], 'auth_token': auth_token.key, 'orgId': res_data['organizationId'], 'userId': res_data['userId']}})
            else:
                try:
                    new_user = User(username=request.data['user_email'])
                    new_user.set_password(request.data['password'])
                    new_user.save()
                    with connections['rds'].cursor() as cursor:
                        cursor.execute("select SQL_NO_CACHE database_name from organizations where organization_id='{}';".format(request.data['organisation_id']))
                        data = cursor.fetchone()
                    profile = Profile.objects.create(user=new_user, organisation_id=data[0], user_email=request.data['user_email'])
                except Exception as e:
                    return Response("error", status = status.HTTP_500_INTERNAL_SERVER_ERROR)
                try:
                    user = authenticate(username=request.data['user_email'], password=request.data['password'])
                    if user is not None:
                        if user.is_active:
                            login(request, user)
                            auth_token,_ = Token.objects.get_or_create(user=user)
                            return Response({ 'status': 'success', 'data' : {'token': res_data['token'], 'auth_token': auth_token.key, 'orgId': res_data['organizationId'], 'userId': res_data['userId']}})
                except Exception as e:
                    return Response("error", status = status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response("error", status = status.HTTP_400_BAD_REQUEST)

class DatasetList(APIView):

    permission_classes = (permissions.IsAuthenticated,)

    def get(self,request):
        
        profile = Profile.objects.get(user = request.user)
        datasets = Dataset.objects.filter(profile=profile)
        serializer = DatasetSeraializer(datasets, many = True)
        for x in serializer.data:
            if x['mode'] == 'SQL':
                with connections['default'].cursor() as cursor:
                    x['fields'] = getColumnList(x['name'],cursor)

        return Response(serializer.data,status = status.HTTP_200_OK)

    def post(self,request):

        if request.data['mode'] == 'VIZ':
            data = request.data
            profile = Profile.objects.get(user = request.user)
            # -- Role Authorization -- #
            serializer = DatasetSeraializer(data = data)
            if serializer.is_valid():
                serializer.save(profile = profile)
                dataset = Dataset.objects.get(name = data['name'])
                for f in data['fields']:
                    field_serializer = FieldSerializer(data = f)
                    if field_serializer.is_valid():
                        field_serializer.save(dataset = dataset)
                    for s in f['settings']:
                        field = Field.objects.filter(dataset__name = data['name']).filter(worksheet = f['worksheet']).get(name = f['name'])
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
                call_command('migrate', database = 'default',fake = True)
                last_migration = MigrationRecorder.Migration.objects.latest('id')
                last_migration_object = sqlmigrate.Command()
                last_migration_sql = last_migration_object.handle(app_label = last_migration.app, migration_name = last_migration.name,database = 'default', backwards = False)
                for item in last_migration_sql.split('\n'):
                    if item.split(' ')[0] == 'CREATE':
                        with connections['default'].cursor() as cursor:
                            cursor.execute(item)
                return Response({'message' : 'success'},status=status.HTTP_201_CREATED)

        else:
            data = request.data
            try:
                profile = Profile.objects.get(user=request.user)
                # -- Role Authorization -- #
                if profile.organisation_id not in connections.databases:
                    connections.databases[profile.organisation_id] = {
                        'ENGINE' : 'django.db.backends.mysql',
                        'NAME' : profile.organisation_id,
                        'OPTIONS' : {
                            'read_default_file' : os.path.join(BASE_DIR, 'cred_dynamic.cnf'),
                        }
                    }
                with connections[profile.organisation_id].cursor() as cursor:
                    # sql = data['sql'][:-1]
                    # createSql = 'CREATE TABLE "{}" AS select * from dblink({}dbname={}{}, {}{}{});'.format(data['name'], "'",os.environ['RDS_DB_NAME'], "'","'",sql.replace('`','"'),"'")
                    # cursor.execute(data['sql'][:-1])
                    # print(resolve(request.path).app_name)
                    dataset_model = get_model(data['name'],Dataset._meta.app_label,cursor, 'CREATE', data['sql'][:-1])
                    admin.site.register(dataset_model)
                del connections[profile.organisation_id]
                call_command('makemigrations')
                call_command('migrate', database='default', fake=True)
                last_migration = MigrationRecorder.Migration.objects.latest('id')
                last_migration_object = sqlmigrate.Command()
                last_migration_sql = last_migration_object.handle(app_label = last_migration.app, migration_name = last_migration.name, database = 'default', backwards = False)
                for item in last_migration_sql.split('\n'):
                    if item.split(' ')[0] == 'CREATE':
                       with connections['default'].cursor() as cur:
                            cur.execute(item)
            except Exception as e:
                return Response("error", status = status.HTTP_400_BAD_REQUEST)
                
            profile = Profile.objects.get(user = request.user)
            data['mode'] = 'SQL'
            data['sql'] = data['sql'][:-1].replace('`','"')
            serializer = DatasetSeraializer(data = data)
            if serializer.is_valid():
                serializer.save(profile = profile)
            return Response({'message' : 'success'},status=status.HTTP_201_CREATED)

        return Response(serializer.errors,status = status.HTTP_400_BAD_REQUEST)

class DatasetDetail(APIView):

    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self,dataset_id,user):
        try:
            return Dataset.objects.filter(profile = user.profile).get(dataset_id = dataset_id)

        except Dataset.DoesNotexist:
            return Http404


    def post(self,request):
        
        # -- Role Authorization -- #
        dataset = self.get_object(request.data['dataset_id'],request.user)
        if dataset.mode == 'SQL':
            try:
                with connections['default'].cursor() as cursor:
                    # cursor.execute('select * from "{}"'.format(dataset.name))
                    dataset_model = get_model(dataset.name, Dataset._meta.app_label, cursor, 'READ_POSTGRES')

                    if request.data['view_mode'] == 'view':
                        data_subset = dataset_model.objects.all() 
                        query = data_subset.query.__str__().replace('"{}"."id", '.format(dataset.name),"")
                        cursor.execute(query)
                        data = dictfetchall(cursor)
                        call_command('makemigrations')
                        call_command('migrate',database = 'default', fake = True)
                        return Response(data,status=status.HTTP_200_OK)
                    else:
                        cursor.execute('DELETE FROM "{}"'.format(dataset.name))
                        # cursor.execute("INSERT INTO {} select * from dblink('dbname={}' , {})".format(dataset.name, os.environ['RDS_DB_NAME'], dataset.sql))
                        profile = Profile.objects.get(user=request.user)
                        if profile.organisation_id not in connections.databases:
                            connections.databases[profile.organisation_id] = {
                                'ENGINE' : 'django.db.backends.mysql',
                                'NAME' : profile.organisation_id,
                                'OPTIONS' : {
                                    'read_default_file' : os.path.join(BASE_DIR, 'cred_dynamic.cnf'),
                                }
                            }
                        with connections[profile.organisation_id].cursor() as cur:
                            cur.execute(dataset.sql.replace('"', '`'))
                            dataset_data = dictfetchall(cur)
                            serializer = GeneralSerializer(data = dataset_data, many = True)
                        del connections[profile.organisation_id]
                        GeneralSerializer.Meta.model = dataset_model
                        if serializer.is_valid(raise_exception = True):
                            serializer.save()
                        else:
                            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
                        data_subset = dataset_model.objects.all()
                        query = data_subset.query.__str__().replace('"{}"."id", '.format(dataset.name),"")
                        cursor.execute(query)
                        data = dictfetchall(cursor)
                        call_command('makemigrations')
                        call_command('migrate', database = 'default',fake = True)
                        return Response(data,status=status.HTTP_200_OK)
            except Exception as e:
                return Response("error",status=status.HTTP_400_BAD_REQUEST)

        else:
            model = dataset.get_django_model()
            GeneralSerializer.Meta.model = model
            
            if request.data['view_mode'] == 'view':
                data_subset = model.objects.all()
                data_serializer = GeneralSerializer(data_subset,many = True)
                return Response(data_serializer.data,status=status.HTTP_200_OK)
            else:
                tables = Table.objects.filter(dataset = dataset)
                joins = Join.objects.filter(dataset =  dataset)
                model_fields = [f.name for f in model._meta.get_fields() if f.name is not 'id']
                model_data = []
                data = []
                model.objects.all().delete()

                for t in tables:
                    profile = Profile.objects.get(user=request.user)
                    if profile.organisation_id not in connections.databases:
                        connections.databases[profile.organisation_id] = {
                            'ENGINE' : 'django.db.backends.mysql',
                            'NAME' : profile.organisation_id,
                            'OPTIONS' : {
                                'read_default_file' : os.path.join(BASE_DIR, 'cred_dynamic.cnf'),
                            }
                        }
                    with connections[profile.organisation_id].cursor() as cursor:
                        cursor.execute('select SQL_NO_CACHE * from `%s`'%(t.name))
                        table_data = dictfetchall(cursor)
                        # print(table_data)

                        table_model = get_model(t.name,model._meta.app_label,cursor, 'READ')
                        DynamicFieldsModelSerializer.Meta.model = table_model
                        
                        context = {
                            "request" : request,
                        }
                        
                        dynamic_serializer = DynamicFieldsModelSerializer(table_data,many = True,fields = set(model_fields))
                        # print(dynamic_serializer.data)
                        model_data.append({ 'name' : t.name,'data' : dynamic_serializer.data})
                    del connections[profile.organisation_id]
                    call_command('makemigrations')
                    call_command('migrate', database = 'default',fake = True)
                        # del table_model
                        # try:
                        #     del caches[model._meta.app_label][t.name]
                        # except KeyError:
                        #     pass
                join_model_data=[]

                id_count = 0
                
                if joins.count() == 0:
                    for x in model_data:
                        for a in x['data']:
                            id_count +=1
                            join_model_data.append({**dict(a),'id' : id_count })

                else:
                    for join in joins:

                        print(join.type)

                        if join.type == 'Inner-Join':
                            for d in model_data:
                                if d['name'] == join.worksheet_1:
                                    
                                    for x in d['data']:
                                        # print(d['table_data'])
                                        check = []
                                        for a in model_data:
                                            if a['name'] == join.worksheet_2:
                                                X = dict(x)
                                                # print(a['table_data'])
                                                for c in a['data']:
                                                    C = dict(c)
                                                    if C[join.field] == X[join.field]:
                                                        check.append(C)
                                                        # print(check)
                                                if check != []:
                                                    for z in check:
                                                        id_count += 1 
                                                        join_model_data.append({**X,**z,'id' : id_count})
                                                break
                            
                            continue
                        if join.type == 'Left-Join':
                            print(model_data)
                            for d in model_data:
                                if d['name'] == join.worksheet_1:
                                    
                                    for x in d['data']:
                                        check = []
                                        for a in model_data:
                                            if a['name'] == join.worksheet_2:
                                                X = dict(x)
                                                for c in a['data']:
                                                    C = dict(c)
                                                    if C[join.field] == X[join.field]:
                                                        check.append(C)
                                                if check == []:
                                                    id_count += 1
                                                    join_model_data.append({**X, 'id' : id_count})
                                                else:
                                                    for z in check:
                                                        id_count += 1
                                                        join_model_data.append({**X,**z, 'id' : id_count})
                                                print(join_model_data)
                                                break       
                            continue
                        if join.type == 'Right-Join':
                            # print('came')
                            for d in model_data:
                                if d['name'] == join.worksheet_2:
                                    
                                    for x in d['data']:
                                        for a in model_data:
                                            if a['name'] == join.worksheet_1:
                                                check = []
                                                X = dict(x)
                                                for c in a['data']:
                                                    C = dict(c)
                                                    if C[join.field] == X[join.field]:
                                                        check.append(C)
                                                if check == []:
                                                    # print({**dict(x)})
                                                    id_count += 1
                                                    join_model_data.append({**X, 'id' : id_count})
                                                else:
                                                    for z in check:
                                                        print({**z,**X})
                                                        id_count += 1
                                                        join_model_data.append({**z,**X, 'id' : id_count})  
                                                break
                            # print(join_model_data)     
                            continue
                        if join.type == 'Outer-Join':
                            for d in model_data:
                                if d['name'] == join.worksheet_1:
                                    
                                    for x in d['data']:
                                        check = []
                                        for a in model_data:
                                            if a['name'] == join.worksheet_2:
                                                X = dict(x)
                                                for c in a['data']:
                                                    C = dict(c)
                                                    if C[join.field] == X[join.field]:
                                                        check.append(C)
                                                
                                                for z in check:
                                                    id_count += 1
                                                    join_model_data.append({**X,**z, 'id' : id_count})
                                                break
                                break
                                    

                            for d in model_data:
                        
                                for x in d['data']:
                                    check = []
                                    X = dict(x)
                                    f = 0
                                    for c in join_model_data:
                                        C = dict(c)
                                        if C[join.field] == X[join.field]:
                                            f = 1
                                    if f == 0:
                                        id_count+=1
                                        join_model_data.append({**X, 'id' : id_count})

                            continue



                # for join in joins:

                #     if join.type == 'Inner-Join':
                #         check = []
                #         for d in model_data:
                #             pass = 0
                #             check_1 = collections.OrderedDict([])
                #             for key,value in d.items():
                #                 # print(d['table_data'])
                #                 if key == join.field :
                #                     pass_2 = 0 
                #                     for x in model_data:
                #                         for k,v in x.items():
                #                             if k == join.field and v == value:
                #                                 for a in check:
                #                                     for b,c in a.items():
                #                                         if b == k and c == v:
                #                                             pass_2 = 1
                #                                 if not pass_2:
                #                                     check_1.update(x)
                #                                     pass = 1
                #                     check.append(check_1)

                #             if not pass:
                #                 check.append(d)

                #         all_model_data.append(check)
                #         continue
                #     if join.type == 'Left-Join':
                #         check = []
                #         for d in model_data:
                #             pass = 0
                #             check_1 = collections.OrderedDict()
                #             for key,value in d.items():
                #                 # print(d['table_data'])
                #                 if key == join.field :
                #                     pass_2 = 0 
                #                     for x in model_data:
                #                         for k,v in x.items():
                #                             if k == join.field and v == value:
                #                                 for a in check:
                #                                     for b,c in a.items():
                #                                         if b == k and c == v:
                #                                             pass_2 = 1
                #                                 if not pass_2:
                #                                     check_1.update(x)
                #                                     pass = 1
                #                     check.append(check_1)

                #             if not pass:
                #                 check.append(d)

                #         all_model_data.append(check)
                #         continue
                #     if join.type == 'Right-Join':
                #         check = []
                #         for d in model_data:
                #             pass = 0
                #             check_1 = collections.OrderedDict()
                #             for key,value in d.items():
                #                 # print(d['table_data'])
                #                 if key == join.field :
                #                     pass_2 = 0 
                #                     for x in model_data:
                #                         for k,v in x.items():
                #                             if k == join.field and v == value:
                #                                 for a in check:
                #                                     for b,c in a.items():
                #                                         if b == k and c == v:
                #                                             pass_2 = 1
                #                                 if not pass_2:
                #                                     check_1.update(x)
                #                                     pass = 1
                #                     check.append(check_1)

                #             if not pass:
                #                 check.append(d)

                #         all_model_data.append(check)
                #         continue

                #     if join.type == 'Outer-Join':
                #         continue
                # for x in model_data:
                #     all_model_data += list(x.items())
                # all_model_data_dict = collections.defaultdict(list)
                # for x in all_model_data:
                #     all_model_data_dict[x[0]].append(x[1])
                # # print(dict(all_model_data_dict))
                # all_model_data_list = []
                # max=0

                # for key,value in dict(all_model_data_dict).items():
                #     count=0
                #     for i in value:
                #         count+=1
                #     if count>=max: max=count
                # print(max)
                # for x in range(max):
                #     d = {}
                #     for key,value in dict(all_model_data_dict).items():
                #         try:
                #             d.update({key : value[x]})
                #             # print(value[x])
                #         except:
                #             pass
                        
                #     all_model_data_list.append(d)
                # print(json.dumps(join_model_data))
                serializer = GeneralSerializer(data = join_model_data,many = True)
                if serializer.is_valid(raise_exception = True):
                    print('hi')
                    model.objects.bulk_create([model(**params) for params in serializer.validated_data])
                else:
                    return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
                data_subset = model.objects.all()
                data_serializer = GeneralSerializer(data_subset,many = True)
                return Response(data_serializer.data,status=status.HTTP_200_OK)
        return Response({'message' : 'error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
class ReportGenerate(viewsets.ViewSet):

    permission_classes = (permissions.IsAuthenticated,)
    color_choices = ["#3e95cd", "#8e5ea2","#3cba9f","#e8c3b9","#c45850","#66FF66","#FB4D46", "#00755E", "#FFEB00", "#FF9933"]

    def report_options(self,request):

        report_type = request.data['type']
        if report_type == 'hor_bar':
            return Response({'options' : ['X_field','Y_field']})

    def get_object(self,dataset_id,user):
        try:
            return Dataset.objects.filter(profile = user.profile).get(dataset_id = dataset_id)

        except Dataset.DoesNotexist:
            return Http404
    
    def func(self, pct, allvals):
        absolute = int(pct/100.*np.sum(allvals))
        return "{:.1f}%\n({:d})".format(pct, absolute)

    def report_generate(self,request):

        report_type = request.data['type']
        model = {}
        data = []
        if request.data['op_table'] == 'dataset':
            dataset = request.data['dataset']
            dataset_detail = self.get_object(dataset,request.user)
            
            if dataset_detail.mode == 'SQL':
                with connections['default'].cursor as cursor:
                    # cursor.execute("select SQL_NO_CACHE * from '{}'".format(dataset.name))
                    # table_data = dictfetchall(cursor)

                    model = get_model(dataset.name, __package__.rsplit('.',1)[-1], cursor, 'READ_POSTGRES')
                    data = model.objects.all()
            else:        
                model = dataset_detail.get_django_model()
                data = model.objects.all()
        else:
            with connections['default'].cursor() as cursor:
                cursor.execute("select SQL_NO_CACHE * from '{}'".format(dataset.name))
                data = dictfetchall(cursor)

        df = read_frame(data)

        if report_type == 'horizontalBar':
            X_field = request.data['options']['X_field']
            Y_field = request.data['options']['Y_field']
            group_by = request.data['options']['group_by']
            measure_operation = request.data['options']['measure_operation']

            all_fields = []
            all_fields.extend([X_field,Y_field])
            if len(group_by) > 0:
                all_fields.extend([group_by])
            df_required = df.loc[:,df.columns.isin(all_fields)]
            data = {
                'labels' : np.unique(np.array(df_required.loc[:,X_field])),
                'datasets' : []
            }

            add = []
            curr = []

            if len(group_by) > 0:
                op_dict = collections.defaultdict(lambda: collections.defaultdict(int))
                if measure_operation == "LAST":

                    for x in df_required.groupby([group_by]).groups.keys():
                        
                        df_group = df_required.groupby([group_by]).get_group(x)
                        
                        curr = np.array(df_group[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]

                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "SUM":
                    
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].sum()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)
                
                if measure_operation == "COUNT":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].count()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict['{}'.format(c[2])]['{}'.format(c[0])] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "COUNT DISTINCT":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False).agg({ Y_field : pd.Series.nunique})
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict['{}'.format(c[2])]['{}'.format(c[0])] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "MAX":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].max()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "MIN":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].min()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "AVERAGE":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].mean()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

            else:
                op_dict = collections.defaultdict(int)
                if measure_operation == "LAST":

                    curr = []

                    curr.extend(df_required.loc[:,[X_field,Y_field]].values)

                    for c in curr:
                        op_dict[c[0]] = c[1]
            
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])                        
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                            
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })

                    
                
                if measure_operation == "SUM":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].sum().reset_index().values)
                    
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                        
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })
                
                if measure_operation == "COUNT":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].count().reset_index().values)
                    for c in curr:
                        op_dict['{}'.format(c[0])] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                        
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })

                if measure_operation == "COUNT DISTINCT":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].nunique().reset_index().values)
                    for c in curr:
                        op_dict['{}'.format(c[0])] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                        
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })

                if measure_operation == "MAX":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].max().reset_index().values)
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                        
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })

                if measure_operation == "MIN":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].min().reset_index().values)
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                        
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })

                if measure_operation == "AVERAGE":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].mean().reset_index().values)
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                        
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })

            return Response({ 'data' : data }, status = status.HTTP_200_OK)
        
        if report_type == 'line':
            X_field = request.data['options']['X_field']
            Y_field = request.data['options']['Y_field']
            group_by = request.data['options']['group_by']
            measure_operation = request.data['options']['measure_operation']

            all_fields = []
            all_fields.extend([X_field,Y_field])
            if len(group_by) > 0:
                all_fields.extend([group_by])
            df_required = df.loc[:,df.columns.isin(all_fields)]

            data = {
                'labels' : np.unique(np.array(df_required.loc[:,X_field])),
                'datasets' : []
            }

            add = []
            curr = []
            op_dict = collections.defaultdict(list)

            if len(group_by) > 0:
                op_dict = collections.defaultdict(lambda: collections.defaultdict(int))
                if measure_operation == "LAST":

                    for x in df_required.groupby([group_by]).groups.keys():
                        
                        df_group = df_required.groupby([group_by]).get_group(x)
                        
                        curr = np.array(df_group[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]

                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'fill' : False,'borderColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen) 
                        
                if measure_operation == "SUM":
                    
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].sum()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'fill' : False,'borderColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)
                
                if measure_operation == "COUNT":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].count()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict['{}'.format(c[2])]['{}'.format(c[0])] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'fill' : False,'borderColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "COUNT DISTINCT":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False).agg({ Y_field : pd.Series.nunique})
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[''.format(c[2])]['{}'.format(c[0])] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'fill' : False,'borderColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "MAX":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].max()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'fill' : False,'borderColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "MIN":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].min()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'fill' : False,'borderColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "AVERAGE":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].mean()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'fill' : False,'borderColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)
                
            else:
                op_dict = collections.defaultdict(int)
                if measure_operation == "LAST":

                    curr = []

                    curr.extend(df_required.loc[:,[X_field,Y_field]].values)

                    for c in curr:
                        op_dict[c[0]] = c[1]
                                  
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    data['datasets'].append({ 'label' : Y_field, 'fill' : False,'borderColor' : random.choice(self.color_choices) , 'data' : new_add })
                    

                if measure_operation == "SUM":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].sum().reset_index().values)
                    
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                    data['datasets'].append({ 'label' : group_by, 'fill' : False,'borderColor' : random.choice(self.color_choices), 'data' : new_add })    
                
                if measure_operation == "COUNT":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].count().reset_index().values)
                    for c in curr:
                        op_dict['{}'.format(c[0])] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                    data['datasets'].append({ 'label' : group_by, 'fill' : False,'borderColor' : random.choice(self.color_choices), 'data' : new_add })    

                if measure_operation == "COUNT DISTINCT":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].nunique().reset_index().values)
                    for c in curr:
                        op_dict['{}'.format(c[0])] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                    data['datasets'].append({ 'label' : group_by, 'fill' : False,'borderColor' : random.choice(self.color_choices), 'data' : new_add })    

                if measure_operation == "MAX":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].max().reset_index().values)
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                    data['datasets'].append({ 'label' : group_by, 'fill' : False,'borderColor' : random.choice(self.color_choices), 'data' : new_add })    

                if measure_operation == "MIN":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].min().reset_index().values)
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                    data['datasets'].append({ 'label' : group_by, 'fill' : False,'borderColor' : random.choice(self.color_choices), 'data' : new_add })    

                if measure_operation == "AVERAGE":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].mean().reset_index().values)
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                    data['datasets'].append({ 'label' : group_by, 'fill' : False,'borderColor' : random.choice(self.color_choices), 'data' : new_add })    


            return Response({ 'data' : data}, status = status.HTTP_200_OK)
        
        if report_type == 'bar':
            X_field = request.data['options']['X_field']
            Y_field = request.data['options']['Y_field']
            group_by = request.data['options']['group_by']
            measure_operation = request.data['options']['measure_operation']

            all_fields = []
            all_fields.extend([X_field,Y_field])
            if len(group_by) > 0:
                all_fields.extend([group_by])
            df_required = df.loc[:,df.columns.isin(all_fields)]
            data = {
                'labels' : np.unique(np.array(df_required.loc[:,X_field])),
                'datasets' : []
            }

            add = []
            curr = []

            if len(group_by) > 0:
                op_dict = collections.defaultdict(lambda: collections.defaultdict(int))
                if measure_operation == "LAST":

                    for x in df_required.groupby([group_by]).groups.keys():
                        
                        df_group = df_required.groupby([group_by]).get_group(x)
                        
                        curr = np.array(df_group[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]

                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "SUM":
                    
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].sum()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)
                
                if measure_operation == "COUNT":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].count()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict['{}'.format(c[2])]['{}'.format(c[0])] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "COUNT DISTINCT":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False).agg({ Y_field : pd.Series.nunique})
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict['{}'.format(c[2])]['{}'.format(c[0])] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "MAX":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].max()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "MIN":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].min()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "AVERAGE":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].mean()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

            else:
                op_dict = collections.defaultdict(int)
                if measure_operation == "LAST":

                    curr = []

                    curr.extend(df_required.loc[:,[X_field,Y_field]].values)

                    for c in curr:
                        op_dict[c[0]] = c[1]
            
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])                        
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                            
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })

                    
                
                if measure_operation == "SUM":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].sum().reset_index().values)
                    
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                        
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })
                
                if measure_operation == "COUNT":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].count().reset_index().values)
                    for c in curr:
                        op_dict['{}'.format(c[0])] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                        
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })

                if measure_operation == "COUNT DISTINCT":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].nunique().reset_index().values)
                    for c in curr:
                        op_dict['{}'.format(c[0])] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                        
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })

                if measure_operation == "MAX":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].max().reset_index().values)
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                        
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })

                if measure_operation == "MIN":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].min().reset_index().values)
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                        
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })

                if measure_operation == "AVERAGE":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].mean().reset_index().values)
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                        
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })

            return Response({ 'data' : data }, status = status.HTTP_200_OK)

        if report_type == 'pie':
            X_field = request.data['options']['X_field']
            Y_field = request.data['options']['Y_field']
            group_by = request.data['options']['group_by']
            measure_operation = request.data['options']['measure_operation']

            all_fields = []
            all_fields.extend([X_field,Y_field])
            if len(group_by) > 0:
                all_fields.extend([group_by])
            df_required = df.loc[:,df.columns.isin(all_fields)]
            data = {
                'labels' : np.unique(np.array(df_required.loc[:,X_field])),
                'datasets' : []
            }

            add = []
            curr = []

            if len(group_by) > 0:
                op_dict = collections.defaultdict(lambda: collections.defaultdict(int))
                if measure_operation == "LAST":

                    for x in df_required.groupby([group_by]).groups.keys():
                        
                        df_group = df_required.groupby([group_by]).get_group(x)
                        
                        curr = np.array(df_group[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]

                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "SUM":
                    
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].sum()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)
                
                if measure_operation == "COUNT":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].count()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict['{}'.format(c[2])]['{}'.format(c[0])] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "COUNT DISTINCT":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False).agg({ Y_field : pd.Series.nunique})
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict['{}'.format(c[2])]['{}'.format(c[0])] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "MAX":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].max()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "MIN":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].min()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "AVERAGE":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].mean()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

            else:
                op_dict = collections.defaultdict(int)
                if measure_operation == "LAST":

                    curr = []

                    curr.extend(df_required.loc[:,[X_field,Y_field]].values)

                    for c in curr:
                        op_dict[c[0]] = c[1]
            
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])                        
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                            
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })

                    
                
                if measure_operation == "SUM":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].sum().reset_index().values)
                    
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                        
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })
                
                if measure_operation == "COUNT":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].count().reset_index().values)
                    for c in curr:
                        op_dict['{}'.format(c[0])] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                        
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })

                if measure_operation == "COUNT DISTINCT":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].nunique().reset_index().values)
                    for c in curr:
                        op_dict['{}'.format(c[0])] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                        
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })

                if measure_operation == "MAX":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].max().reset_index().values)
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                        
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })

                if measure_operation == "MIN":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].min().reset_index().values)
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                        
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })

                if measure_operation == "AVERAGE":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].mean().reset_index().values)
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                        
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })

            return Response({ 'data' : data }, status = status.HTTP_200_OK)

        if report_type == 'doughnut':
            X_field = request.data['options']['X_field']
            Y_field = request.data['options']['Y_field']
            group_by = request.data['options']['group_by']
            measure_operation = request.data['options']['measure_operation']

            all_fields = []
            all_fields.extend([X_field,Y_field])
            if len(group_by) > 0:
                all_fields.extend([group_by])
            df_required = df.loc[:,df.columns.isin(all_fields)]
            data = {
                'labels' : np.unique(np.array(df_required.loc[:,X_field])),
                'datasets' : []
            }

            add = []
            curr = []

            if len(group_by) > 0:
                op_dict = collections.defaultdict(lambda: collections.defaultdict(int))
                if measure_operation == "LAST":

                    for x in df_required.groupby([group_by]).groups.keys():
                        
                        df_group = df_required.groupby([group_by]).get_group(x)
                        
                        curr = np.array(df_group[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]

                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "SUM":
                    
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].sum()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)
                
                if measure_operation == "COUNT":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].count()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict['{}'.format(c[2])]['{}'.format(c[0])] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "COUNT DISTINCT":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False).agg({ Y_field : pd.Series.nunique})
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict['{}'.format(c[2])]['{}'.format(c[0])] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "MAX":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].max()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "MIN":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].min()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "AVERAGE":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].mean()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

            else:
                op_dict = collections.defaultdict(int)
                if measure_operation == "LAST":

                    curr = []

                    curr.extend(df_required.loc[:,[X_field,Y_field]].values)

                    for c in curr:
                        op_dict[c[0]] = c[1]
            
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])                        
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                            
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })

                    
                
                if measure_operation == "SUM":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].sum().reset_index().values)
                    
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                        
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })
                
                if measure_operation == "COUNT":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].count().reset_index().values)
                    for c in curr:
                        op_dict['{}'.format(c[0])] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                        
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })

                if measure_operation == "COUNT DISTINCT":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].nunique().reset_index().values)
                    for c in curr:
                        op_dict['{}'.format(c[0])] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                        
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })

                if measure_operation == "MAX":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].max().reset_index().values)
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                        
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })

                if measure_operation == "MIN":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].min().reset_index().values)
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                        
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })

                if measure_operation == "AVERAGE":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].mean().reset_index().values)
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                        
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })

            return Response({ 'data' : data }, status = status.HTTP_200_OK)
        
        if report_type == 'scatter':
            X_field = request.data['options']['X_field']
            Y_field = request.data['options']['Y_field']
            group_by = request.data['options']['group_by']
            measure_operation = request.data['options']['measure_operation']

            all_fields = []
            all_fields.extend([X_field,Y_field])
            if len(group_by) > 0:
                all_fields.extend([group_by])
            df_required = df.loc[:,df.columns.isin(all_fields)]
            data = {
                'datasets' : []
            }

            add = []
            curr = []

            if len(group_by) > 0:
                op_dict = collections.defaultdict(lambda: collections.defaultdict(int))
                if measure_operation == "LAST":

                    for x in df_required.groupby([group_by]).groups.keys():
                        
                        df_group = df_required.groupby([group_by]).get_group(x)
                        
                        curr = np.array(df_group[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]

                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in np.unique(np.array(df_required.loc[:,X_field])):
                            new_add.append({
                                'x' : x,
                                'y' : op_dict[group][x]})
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "SUM":
                    
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].sum()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in np.unique(np.array(df_required.loc[:,X_field])):
                            new_add.append({
                                'x' : x,
                                'y' : op_dict[group][x]})
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)
                
                if measure_operation == "COUNT":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].count()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict['{}'.format(c[2])]['{}'.format(c[0])] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in np.unique(np.array(df_required.loc[:,X_field])):
                            new_add.append({
                                'x' : x,
                                'y' : op_dict[group][x]})
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "COUNT DISTINCT":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False).agg({ Y_field : pd.Series.nunique})
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict['{}'.format(c[2])]['{}'.format(c[0])] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in np.unique(np.array(df_required.loc[:,X_field])):
                            new_add.append({
                                'x' : x,
                                'y' : op_dict[group][x]})
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "MAX":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].max()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in np.unique(np.array(df_required.loc[:,X_field])):
                            new_add.append({
                                'x' : x,
                                'y' : op_dict[group][x]})
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "MIN":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].min()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in np.unique(np.array(df_required.loc[:,X_field])):
                            new_add.append({
                                'x' : x,
                                'y' : op_dict[group][x]})
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "AVERAGE":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].mean()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in np.unique(np.array(df_required.loc[:,X_field])):
                            new_add.append({
                                'x' : x,
                                'y' : op_dict[group][x]})
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

            else:
                op_dict = collections.defaultdict(int)
                if measure_operation == "LAST":

                    curr = []

                    curr.extend(df_required.loc[:,[X_field,Y_field]].values)

                    for c in curr:
                        op_dict[c[0]] = c[1]
            
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(np.unique(np.array(df_required.loc[:,X_field]))))])                        
                    new_add = []
                    for d in np.unique(np.array(df_required.loc[:,X_field])):
                        new_add.append({
                            'x' : d,
                            'y' : op_dict[d]})
                            
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })

                    
                
                if measure_operation == "SUM":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].sum().reset_index().values)
                    
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in np.unique(np.array(df_required.loc[:,X_field])):
                        new_add.append({
                            'x' : d,
                            'y' : op_dict[d]})
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(np.unique(np.array(df_required.loc[:,X_field]))))])
                        
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })
                
                if measure_operation == "COUNT":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].count().reset_index().values)
                    for c in curr:
                        op_dict['{}'.format(c[0])] = c[1]
                                
                    new_add = []
                    for d in np.unique(np.array(df_required.loc[:,X_field])):
                        new_add.append({
                            'x' : d,
                            'y' : op_dict[d]})
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(np.unique(np.array(df_required.loc[:,X_field]))))])
                        
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })

                if measure_operation == "COUNT DISTINCT":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].nunique().reset_index().values)
                    for c in curr:
                        op_dict['{}'.format(c[0])] = c[1]
                                
                    new_add = []
                    for d in np.unique(np.array(df_required.loc[:,X_field])):
                        new_add.append({
                            'x' : d,
                            'y' : op_dict[d]})
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(np.unique(np.array(df_required.loc[:,X_field]))))])
                        
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })

                if measure_operation == "MAX":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].max().reset_index().values)
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in np.unique(np.array(df_required.loc[:,X_field])):
                        new_add.append({
                            'x' : d,
                            'y' : op_dict[d]})
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(np.unique(np.array(df_required.loc[:,X_field]))))])
                        
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })

                if measure_operation == "MIN":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].min().reset_index().values)
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in np.unique(np.array(df_required.loc[:,X_field])):
                        new_add.append({
                            'x' : d,
                            'y' : op_dict[d]})
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(np.unique(np.array(df_required.loc[:,X_field]))))])
                        
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })

                if measure_operation == "AVERAGE":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].mean().reset_index().values)
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in np.unique(np.array(df_required.loc[:,X_field])):    
                        new_add.append({
                            'x' : d,
                            'y' : op_dict[d]})
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(np.unique(np.array(df_required.loc[:,X_field]))))])
                        
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })

            return Response({ 'data' : data }, status = status.HTTP_200_OK)
        
        if report_type == 'bubble':
            X_field = request.data['options']['X_field']
            Y_field = request.data['options']['Y_field']
            group_by = request.data['options']['group_by']
            measure_operation = request.data['options']['measure_operation']

            all_fields = []
            all_fields.extend([X_field,Y_field])
            if len(group_by) > 0:
                all_fields.extend([group_by])
            df_required = df.loc[:,df.columns.isin(all_fields)]
            data = {
                'datasets' : []
            }

            add = []
            curr = []

            if len(group_by) > 0:
                op_dict = collections.defaultdict(lambda: collections.defaultdict(int))
                if measure_operation == "LAST":

                    for x in df_required.groupby([group_by]).groups.keys():
                        
                        df_group = df_required.groupby([group_by]).get_group(x)
                        
                        curr = np.array(df_group[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]

                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])
                    r = []
                    r.extend([random.randint(15,30) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])
                    for group in op_dict.keys():        
                        
                        border_color_chosen = random.choice(colors)    
                        color_chosen = '{}66'.format(border_color_chosen)
                        r_chosen = random.choice(r)    

                        new_add = []
                        for x in np.unique(np.array(df_required.loc[:,X_field])):
                            new_add.append({
                                'x' : x,
                                'y' : op_dict[group][x],
                                'r' : r_chosen })
                        data['datasets'].append({ 'label' : group, 'borderColor' : border_color_chosen,'hoverBackgroundColor' : color_chosen,'backgroundColor' : color_chosen, 'data' : new_add })
                        if len(colors) > 1:
                            colors.remove(border_color_chosen)

                if measure_operation == "SUM":
                    
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].sum()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])
                    r = []
                    r.extend([random.randint(15,30) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])
                    for group in op_dict.keys():        

                        border_color_chosen = random.choice(colors)    
                        color_chosen = '{}66'.format(border_color_chosen)
                        r_chosen = random.choice(r)    

                        new_add = []
                        for x in np.unique(np.array(df_required.loc[:,X_field])):
                            new_add.append({
                                'x' : x,
                                'y' : op_dict[group][x],
                                'r' : r_chosen })
                        data['datasets'].append({ 'label' : group, 'borderColor' : border_color_chosen,'hoverBackgroundColor' : color_chosen,'backgroundColor' : color_chosen, 'data' : new_add })
                        if len(colors) > 1:
                            colors.remove(border_color_chosen)
                
                if measure_operation == "COUNT":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].count()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict['{}'.format(c[2])]['{}'.format(c[0])] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])
                    r = []
                    r.extend([random.randint(15,30) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])
                    for group in op_dict.keys():        

                        border_color_chosen = random.choice(colors)    
                        color_chosen = '{}66'.format(border_color_chosen)
                        r_chosen = random.choice(r)    

                        new_add = []
                        for x in np.unique(np.array(df_required.loc[:,X_field])):
                            new_add.append({
                                'x' : x,
                                'y' : op_dict[group][x],
                                'r' : r_chosen })
                        data['datasets'].append({ 'label' : group, 'borderColor' : border_color_chosen,'hoverBackgroundColor' : color_chosen,'backgroundColor' : color_chosen, 'data' : new_add })
                        if len(colors) > 1:
                            colors.remove(border_color_chosen)

                if measure_operation == "COUNT DISTINCT":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False).agg({ Y_field : pd.Series.nunique})
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict['{}'.format(c[2])]['{}'.format(c[0])] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])
                    r = []
                    r.extend([random.randint(15,30) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])
                    for group in op_dict.keys():        

                        border_color_chosen = random.choice(colors)    
                        color_chosen = '{}66'.format(border_color_chosen)
                        r_chosen = random.choice(r)    

                        new_add = []
                        for x in np.unique(np.array(df_required.loc[:,X_field])):
                            new_add.append({
                                'x' : x,
                                'y' : op_dict[group][x],
                                'r' : r_chosen })
                        data['datasets'].append({ 'label' : group, 'borderColor' : border_color_chosen,'hoverBackgroundColor' : color_chosen,'backgroundColor' : color_chosen, 'data' : new_add })
                        if len(colors) > 1:
                            colors.remove(border_color_chosen)

                if measure_operation == "MAX":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].max()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])
                    r = []
                    r.extend([random.randint(15,30) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])
                    for group in op_dict.keys():        

                        border_color_chosen = random.choice(colors)    
                        color_chosen = '{}66'.format(border_color_chosen)
                        r_chosen = random.choice(r)    

                        new_add = []
                        for x in np.unique(np.array(df_required.loc[:,X_field])):
                            new_add.append({
                                'x' : x,
                                'y' : op_dict[group][x],
                                'r' : r_chosen })
                        data['datasets'].append({ 'label' : group, 'borderColor' : border_color_chosen,'hoverBackgroundColor' : color_chosen,'backgroundColor' : color_chosen, 'data' : new_add })
                        if len(colors) > 1:
                            colors.remove(border_color_chosen)

                if measure_operation == "MIN":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].min()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])
                    r = []
                    r.extend([random.randint(15,30) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])
                    for group in op_dict.keys():        

                        border_color_chosen = random.choice(colors)    
                        color_chosen = '{}66'.format(border_color_chosen)
                        r_chosen = random.choice(r)    

                        new_add = []
                        for x in np.unique(np.array(df_required.loc[:,X_field])):
                            new_add.append({
                                'x' : x,
                                'y' : op_dict[group][x],
                                'r' : r_chosen })
                        data['datasets'].append({ 'label' : group, 'borderColor' : border_color_chosen,'hoverBackgroundColor' : color_chosen,'backgroundColor' : color_chosen, 'data' : new_add })
                        if len(colors) > 1:
                            colors.remove(border_color_chosen)

                if measure_operation == "AVERAGE":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].mean()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])
                    r = []
                    r.extend([random.randint(15,30) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])
                    for group in op_dict.keys():        

                        border_color_chosen = random.choice(colors)    
                        color_chosen = '{}66'.format(border_color_chosen)
                        r_chosen = random.choice(r)    

                        new_add = []
                        for x in np.unique(np.array(df_required.loc[:,X_field])):
                            new_add.append({
                                'x' : x,
                                'y' : op_dict[group][x],
                                'r' : r_chosen })
                        data['datasets'].append({ 'label' : group, 'borderColor' : border_color_chosen,'hoverBackgroundColor' : color_chosen,'backgroundColor' : color_chosen, 'data' : new_add })                
                        if len(colors) > 1:
                            colors.remove(border_color_chosen)

            else:
                op_dict = collections.defaultdict(int)
                if measure_operation == "LAST":

                    curr = []

                    curr.extend(df_required.loc[:,[X_field,Y_field]].values)

                    for c in curr:
                        op_dict[c[0]] = c[1]
            
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(np.unique(np.array(df_required.loc[:,X_field]))))])                        
                    background_colors = ['{}66'.format(x) for x in colors]
                    new_add = []
                    for d in np.unique(np.array(df_required.loc[:,X_field])):
                        new_add.append({
                            'x' : d,
                            'y' : op_dict[d],
                            'r' : random.randint(15,30)})
                            
                    data['datasets'].append({ 'label' : Y_field, 'borderColor' : colors,'hoverBackgroundColor' : background_colors,'backgroundColor' : background_colors, 'data' : new_add })

                    
                
                if measure_operation == "SUM":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].sum().reset_index().values)
                    
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in np.unique(np.array(df_required.loc[:,X_field])):
                        new_add.append({
                            'x' : d,
                            'y' : op_dict[d],
                            'r' : random.randint(15,30)})
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(np.unique(np.array(df_required.loc[:,X_field]))))])                        
                    background_colors = ['{}66'.format(x) for x in colors]
                    
                    data['datasets'].append({ 'label' : Y_field, 'borderColor' : colors,'hoverBackgroundColor' : background_colors,'backgroundColor' : background_colors, 'data' : new_add })
                
                if measure_operation == "COUNT":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].count().reset_index().values)
                    for c in curr:
                        op_dict['{}'.format(c[0])] = c[1]
                                
                    new_add = []
                    for d in np.unique(np.array(df_required.loc[:,X_field])):
                        new_add.append({
                            'x' : d,
                            'y' : op_dict[d],
                            'r' : random.randint(15,30)})
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(np.unique(np.array(df_required.loc[:,X_field]))))])                        
                    background_colors = ['{}66'.format(x) for x in colors]
                    
                    data['datasets'].append({ 'label' : Y_field, 'borderColor' : colors,'hoverBackgroundColor' : background_colors,'backgroundColor' : background_colors, 'data' : new_add })

                if measure_operation == "COUNT DISTINCT":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].nunique().reset_index().values)
                    for c in curr:
                        op_dict['{}'.format(c[0])] = c[1]
                                
                    new_add = []
                    for d in np.unique(np.array(df_required.loc[:,X_field])):
                        new_add.append({
                            'x' : d,
                            'y' : op_dict[d],
                            'r' : random.randint(15,30)})
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(np.unique(np.array(df_required.loc[:,X_field]))))])                        
                    background_colors = ['{}66'.format(x) for x in colors]
                    
                    data['datasets'].append({ 'label' : Y_field, 'borderColor' : colors,'hoverBackgroundColor' : background_colors,'backgroundColor' : background_colors, 'data' : new_add })

                if measure_operation == "MAX":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].max().reset_index().values)
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in np.unique(np.array(df_required.loc[:,X_field])):
                        new_add.append({
                            'x' : d,
                            'y' : op_dict[d],
                            'r' : random.randint(15,30)})
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(np.unique(np.array(df_required.loc[:,X_field]))))])                        
                    background_colors = ['{}66'.format(x) for x in colors]
                    
                    data['datasets'].append({ 'label' : Y_field, 'borderColor' : colors,'hoverBackgroundColor' : background_colors,'backgroundColor' : background_colors, 'data' : new_add })

                if measure_operation == "MIN":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].min().reset_index().values)
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in np.unique(np.array(df_required.loc[:,X_field])):
                        new_add.append({
                            'x' : d,
                            'y' : op_dict[d],
                            'r' : random.randint(15,30)})
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(np.unique(np.array(df_required.loc[:,X_field]))))])                        
                    background_colors = ['{}66'.format(x) for x in colors]
                    
                    data['datasets'].append({ 'label' : Y_field, 'borderColor' : colors,'hoverBackgroundColor' : background_colors,'backgroundColor' : background_colors, 'data' : new_add })

                if measure_operation == "AVERAGE":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].mean().reset_index().values)
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in np.unique(np.array(df_required.loc[:,X_field])):    
                        new_add.append({
                            'x' : d,
                            'y' : op_dict[d],
                            'r' : random.randint(15,30)})
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(np.unique(np.array(df_required.loc[:,X_field]))))])                        
                    background_colors = ['{}66'.format(x) for x in colors]
                    
                    data['datasets'].append({ 'label' : Y_field, 'borderColor' : colors,'hoverBackgroundColor' : background_colors,'backgroundColor' : background_colors, 'data' : new_add })

            return Response({ 'data' : data }, status = status.HTTP_200_OK)

        if report_type == "radar":
            X_field = request.data['options']['X_field']
            Y_field = request.data['options']['Y_field']
            group_by = request.data['options']['group_by']
            measure_operation = request.data['options']['measure_operation']

            all_fields = []
            all_fields.extend([X_field,Y_field])
            if len(group_by) > 0:
                all_fields.extend([group_by])
            df_required = df.loc[:,df.columns.isin(all_fields)]

            data = {
                'labels' : np.unique(np.array(df_required.loc[:,X_field])),
                'datasets' : []
            }

            add = []
            curr = []
            op_dict = collections.defaultdict(list)

            if len(group_by) > 0:
                op_dict = collections.defaultdict(lambda: collections.defaultdict(int))
                if measure_operation == "LAST":

                    for x in df_required.groupby([group_by]).groups.keys():
                        
                        df_group = df_required.groupby([group_by]).get_group(x)
                        
                        curr = np.array(df_group[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]

                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    
                        background_color = '{}66'.format(color_chosen)
                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'fill' : True,'backgroundColor' : background_color,'borderColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen) 
                        
                if measure_operation == "SUM":
                    
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].sum()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    
                        background_color = '{}66'.format(color_chosen)
                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'fill' : True,'backgroundColor' : background_color,'borderColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen) 
                
                if measure_operation == "COUNT":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].count()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict['{}'.format(c[2])]['{}'.format(c[0])] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    
                        background_color = '{}66'.format(color_chosen)
                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'fill' : True,'backgroundColor' : background_color,'borderColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen) 

                if measure_operation == "COUNT DISTINCT":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False).agg({ Y_field : pd.Series.nunique})
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[''.format(c[2])]['{}'.format(c[0])] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    
                        background_color = '{}66'.format(color_chosen)
                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'fill' : True,'backgroundColor' : background_color,'borderColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen) 

                if measure_operation == "MAX":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].max()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    
                        background_color = '{}66'.format(color_chosen)
                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'fill' : True,'backgroundColor' : background_color,'borderColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen) 

                if measure_operation == "MIN":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].min()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    
                        background_color = '{}66'.format(color_chosen)
                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'fill' : True,'backgroundColor' : background_color,'borderColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen) 

                if measure_operation == "AVERAGE":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].mean()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    
                        background_color = '{}66'.format(color_chosen)
                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'fill' : True,'backgroundColor' : background_color,'borderColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen) 
                
            else:
                op_dict = collections.defaultdict(int)
                if measure_operation == "LAST":

                    curr = []

                    curr.extend(df_required.loc[:,[X_field,Y_field]].values)

                    for c in curr:
                        op_dict[c[0]] = c[1]
                                  
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    border_color_chosen = random.choice(self.color_choices)
                    background_color = '{}66'.format(border_color_chosen)
                    data['datasets'].append({ 'label' : Y_field, 'fill' : True,'borderColor' : border_color_chosen, 'backgroundColor' : background_color , 'data' : new_add })
                    

                if measure_operation == "SUM":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].sum().reset_index().values)
                    
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                    border_color_chosen = random.choice(self.color_choices)
                    background_color = '{}66'.format(border_color_chosen)
                    data['datasets'].append({ 'label' : Y_field, 'fill' : True,'borderColor' : border_color_chosen, 'backgroundColor' : background_color , 'data' : new_add })                
                if measure_operation == "COUNT":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].count().reset_index().values)
                    for c in curr:
                        op_dict['{}'.format(c[0])] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                    border_color_chosen = random.choice(self.color_choices)
                    background_color = '{}66'.format(border_color_chosen)
                    data['datasets'].append({ 'label' : Y_field, 'fill' : True,'borderColor' : border_color_chosen, 'backgroundColor' : background_color , 'data' : new_add })

                if measure_operation == "COUNT DISTINCT":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].nunique().reset_index().values)
                    for c in curr:
                        op_dict['{}'.format(c[0])] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                    border_color_chosen = random.choice(self.color_choices)
                    background_color = '{}66'.format(border_color_chosen)
                    data['datasets'].append({ 'label' : Y_field, 'fill' : True,'borderColor' : border_color_chosen, 'backgroundColor' : background_color , 'data' : new_add })

                if measure_operation == "MAX":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].max().reset_index().values)
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                    border_color_chosen = random.choice(self.color_choices)
                    background_color = '{}66'.format(border_color_chosen)
                    data['datasets'].append({ 'label' : Y_field, 'fill' : True,'borderColor' : border_color_chosen, 'backgroundColor' : background_color , 'data' : new_add })

                if measure_operation == "MIN":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].min().reset_index().values)
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                    border_color_chosen = random.choice(self.color_choices)
                    background_color = '{}66'.format(border_color_chosen)
                    data['datasets'].append({ 'label' : Y_field, 'fill' : True,'borderColor' : border_color_chosen, 'backgroundColor' : background_color , 'data' : new_add })

                if measure_operation == "AVERAGE":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].mean().reset_index().values)
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                    border_color_chosen = random.choice(self.color_choices)
                    background_color = '{}66'.format(border_color_chosen)
                    data['datasets'].append({ 'label' : Y_field, 'fill' : True,'borderColor' : border_color_chosen, 'backgroundColor' : background_color , 'data' : new_add })


            return Response({ 'data' : data}, status = status.HTTP_200_OK)

        if report_type == "polarArea":
            X_field = request.data['options']['X_field']
            Y_field = request.data['options']['Y_field']
            group_by = request.data['options']['group_by']
            measure_operation = request.data['options']['measure_operation']

            all_fields = []
            all_fields.extend([X_field,Y_field])
            if len(group_by) > 0:
                all_fields.extend([group_by])
            df_required = df.loc[:,df.columns.isin(all_fields)]
            data = {
                'labels' : np.unique(np.array(df_required.loc[:,X_field])),
                'datasets' : []
            }

            add = []
            curr = []

            if len(group_by) > 0:
                op_dict = collections.defaultdict(lambda: collections.defaultdict(int))
                if measure_operation == "LAST":

                    for x in df_required.groupby([group_by]).groups.keys():
                        
                        df_group = df_required.groupby([group_by]).get_group(x)
                        
                        curr = np.array(df_group[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]

                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "SUM":
                    
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].sum()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)
                
                if measure_operation == "COUNT":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].count()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict['{}'.format(c[2])]['{}'.format(c[0])] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "COUNT DISTINCT":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False).agg({ Y_field : pd.Series.nunique})
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict['{}'.format(c[2])]['{}'.format(c[0])] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "MAX":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].max()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "MIN":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].min()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "AVERAGE":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].mean()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

            else:
                op_dict = collections.defaultdict(int)
                if measure_operation == "LAST":

                    curr = []

                    curr.extend(df_required.loc[:,[X_field,Y_field]].values)

                    for c in curr:
                        op_dict[c[0]] = c[1]
            
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])                        
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                            
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })

                    
                
                if measure_operation == "SUM":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].sum().reset_index().values)
                    
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                        
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })
                
                if measure_operation == "COUNT":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].count().reset_index().values)
                    for c in curr:
                        op_dict['{}'.format(c[0])] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                        
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })

                if measure_operation == "COUNT DISTINCT":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].nunique().reset_index().values)
                    for c in curr:
                        op_dict['{}'.format(c[0])] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                        
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })

                if measure_operation == "MAX":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].max().reset_index().values)
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                        
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })

                if measure_operation == "MIN":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].min().reset_index().values)
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                        
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })

                if measure_operation == "AVERAGE":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].mean().reset_index().values)
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
                        
                    data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })

            return Response({ 'data' : data }, status = status.HTTP_200_OK)

        if report_type == 'bar_mix':
            X_field = request.data['options']['X_field']
            Y_field = request.data['options']['Y_field']
            group_by = request.data['options']['group_by']
            measure_operation = request.data['options']['measure_operation']

            all_fields = []
            all_fields.extend([X_field,Y_field])
            if len(group_by) > 0:
                all_fields.extend([group_by])
            df_required = df.loc[:,df.columns.isin(all_fields)]
            data = {
                'labels' : np.unique(np.array(df_required.loc[:,X_field])),
                'datasets' : []
            }

            add = []
            curr = []

            if len(group_by) > 0:
                op_dict = collections.defaultdict(lambda: collections.defaultdict(int))
                if measure_operation == "LAST":

                    for x in df_required.groupby([group_by]).groups.keys():
                        
                        df_group = df_required.groupby([group_by]).get_group(x)
                        
                        curr = np.array(df_group[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]

                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'type' : 'bar','label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                        data['datasets'].append({ 'type': 'line','label' : group, 'fill' : True,'backgroundColor' : '{}66'.format(color_chosen),'borderColor' : color_chosen, 'data' : new_add })
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "SUM":
                    
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].sum()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'type' : 'bar','label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                        data['datasets'].append({ 'type': 'line','label' : group, 'fill' : True,'backgroundColor' : '{}66'.format(color_chosen),'borderColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)
                
                if measure_operation == "COUNT":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].count()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict['{}'.format(c[2])]['{}'.format(c[0])] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'type' : 'bar','label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                        data['datasets'].append({ 'type': 'line','label' : group, 'fill' : True,'backgroundColor' : '{}66'.format(color_chosen),'borderColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "COUNT DISTINCT":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False).agg({ Y_field : pd.Series.nunique})
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict['{}'.format(c[2])]['{}'.format(c[0])] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'type' : 'bar','label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                        data['datasets'].append({ 'type': 'line','label' : group, 'fill' : True,'backgroundColor' : '{}66'.format(color_chosen),'borderColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "MAX":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].max()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'type' : 'bar','label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                        data['datasets'].append({ 'type': 'line','label' : group, 'fill' : True,'backgroundColor' : '{}66'.format(color_chosen),'borderColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "MIN":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].min()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'type' : 'bar','label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                        data['datasets'].append({ 'type': 'line','label' : group, 'fill' : True,'backgroundColor' : '{}66'.format(color_chosen),'borderColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "AVERAGE":
                    df_group_sum = df_required.groupby([group_by, X_field],as_index=False)[Y_field].mean()
                    for x in df_group_sum.groupby([group_by]).groups.keys():
                        
                        curr = np.array(df_group_sum[[X_field,Y_field,group_by]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                    colors=[]
                    colors.extend([random.choice(self.color_choices) for _ in range(len(df_required.groupby([group_by]).groups.keys()))])

                    for group in op_dict.keys():        

                        color_chosen = random.choice(colors)    

                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'type' : 'bar','label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                        data['datasets'].append({ 'type': 'line','label' : group, 'fill' : True,'backgroundColor' : '{}66'.format(color_chosen),'borderColor' : color_chosen, 'data' : new_add })
                
                        if len(colors) > 1:
                            colors.remove(color_chosen)

            else:
                op_dict = collections.defaultdict(int)
                if measure_operation == "LAST":

                    curr = []

                    curr.extend(df_required.loc[:,[X_field,Y_field]].values)

                    for c in curr:
                        op_dict[c[0]] = c[1]
                        
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    color_chosen = random.choice(self.color_choices)
                    data['datasets'].append({ 'type' : 'bar','label' : Y_field, 'backgroundColor' : color_chosen, 'data' : new_add })
                    data['datasets'].append({ 'type' : 'line','label' : Y_field, 'fill' : True,'backgroundColor' : '{}66'.format(color_chosen),'borderColor' : color_chosen , 'data' : new_add })  
                
                if measure_operation == "SUM":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].sum().reset_index().values)
                    
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                
                    color_chosen = random.choice(self.color_choices)
                    data['datasets'].append({ 'type' : 'bar','label' : Y_field, 'backgroundColor' : color_chosen, 'data' : new_add })
                    data['datasets'].append({ 'type' : 'line','label' : Y_field, 'fill' : True,'backgroundColor' : '{}66'.format(color_chosen),'borderColor' : color_chosen , 'data' : new_add })
                
                if measure_operation == "COUNT":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].count().reset_index().values)
                    for c in curr:
                        op_dict['{}'.format(c[0])] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    color_chosen = random.choice(self.color_choices)
                    data['datasets'].append({ 'type' : 'bar','label' : Y_field, 'backgroundColor' : color_chosen, 'data' : new_add })
                    data['datasets'].append({ 'type' : 'line','label' : Y_field, 'fill' : True,'backgroundColor' : '{}66'.format(color_chosen),'borderColor' : color_chosen , 'data' : new_add })

                if measure_operation == "COUNT DISTINCT":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].nunique().reset_index().values)
                    for c in curr:
                        op_dict['{}'.format(c[0])] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    color_chosen = random.choice(self.color_choices)
                    data['datasets'].append({ 'type' : 'bar','label' : Y_field, 'backgroundColor' : color_chosen, 'data' : new_add })
                    data['datasets'].append({ 'type' : 'line','label' : Y_field, 'fill' : True,'backgroundColor' : '{}66'.format(color_chosen),'borderColor' : color_chosen , 'data' : new_add })

                if measure_operation == "MAX":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].max().reset_index().values)
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    color_chosen = random.choice(self.color_choices)
                    data['datasets'].append({ 'type' : 'bar','label' : Y_field, 'backgroundColor' : color_chosen, 'data' : new_add })
                    data['datasets'].append({ 'type' : 'line','label' : Y_field, 'fill' : True,'backgroundColor' : '{}66'.format(color_chosen),'borderColor' : color_chosen , 'data' : new_add })

                if measure_operation == "MIN":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].min().reset_index().values)
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    color_chosen = random.choice(self.color_choices)
                    data['datasets'].append({ 'type' : 'bar','label' : Y_field, 'backgroundColor' : color_chosen, 'data' : new_add })
                    data['datasets'].append({ 'type' : 'line','label' : Y_field, 'fill' : True,'backgroundColor' : '{}66'.format(color_chosen),'borderColor' : color_chosen , 'data' : new_add })

                if measure_operation == "AVERAGE":
                    curr = []
                    curr.extend(df_required.groupby([X_field])[Y_field].mean().reset_index().values)
                    for c in curr:
                        op_dict[c[0]] = c[1]
                                
                    new_add = []
                    for d in data['labels']:
                        new_add.append(op_dict[d])
                    
                    color_chosen = random.choice(self.color_choices)
                    data['datasets'].append({ 'type' : 'bar','label' : Y_field, 'backgroundColor' : color_chosen, 'data' : new_add })
                    data['datasets'].append({ 'type' : 'line','label' : Y_field, 'fill' : True,'backgroundColor' : '{}66'.format(color_chosen),'borderColor' : color_chosen , 'data' : new_add })

            return Response({ 'data' : data }, status = status.HTTP_200_OK)
        return Response('error',status = status.HTTP_400_BAD_REQUEST)


class ReportList(APIView):

    permission_classes = (permissions.IsAuthenticated,)
    
    def get(self,request):

        reports = Report.objects.filter(profile = request.user.profile).all()
        serializer = ReportSerializer(reports, many=True)

        return Response(serializer.data, status = status.HTTP_200_OK)
    
    def get_object(self,dataset_id,user):
        try:
            return Dataset.objects.filter(profile = user.profile).get(dataset_id = dataset_id)
        except:
            return Http404

    
    def get_report_object(self,report_id,user):
        try:
            return Report.objects.filter(profile = user.profile).get(report_id = report_id)
        except:
            return Http404

    def post(self, request):
        data = request.data
        if data['op_table'] == 'dataset':
            dataset = self.get_object(data['dataset_id'],request.user)
        serializer = ReportSerializer(data = data)

        if serializer.is_valid():
            if data['op_table'] == 'dataset':
                serializer.save(profile = request.user.profile, dataset = dataset)
            else:
                serializer.save(user_id = request.user.user_id, worksheet = data['worksheet_id'])

            return Response(serializer.data,status = status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)
    
    def put(self,request):

        data = request.data
        print(data)
        report = self.get_report_object(data['report_id'], request.user)

        serializer = ReportSerializer(report, data = data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status = status.HTTP_200_OK)
        
        return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)