from django.shortcuts import render

from app.models import Dataset,Field,Setting,Table,Join,Report
from app.serializers import DatasetSeraializer,FieldSerializer,SettingSerializer,GeneralSerializer,TableSerializer,JoinSerializer,DynamicFieldsModelSerializer,ReportSerializer, DashboardSerializer,SharedReportSerializer
from app.utils import get_model,dictfetchall, getColumnList
from app.Authentication import  GridBackendAuthentication,  GridBackendDatasetPermissions, GridBackendReportPermissions, GridBackendDashboardPermissions

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import Http404
from rest_framework import permissions,exceptions
from rest_framework import viewsets

from django.contrib import admin
from django.core.management import call_command
from django.db import connections
from django.core.cache import caches
from django.db.migrations.recorder import MigrationRecorder
from django.core.management.commands import sqlmigrate
from django.urls import resolve

import collections
import simplejson as json
import time
from django_pandas.io import read_frame
# import matplotlib.pyplot as plt
# import mpld3
import numpy as np
import random
import os
import requests
import pandas as pd
import redis
import shutil
import subprocess
import pickle
import zlib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Create your views here.



class DatasetList(APIView):

    permission_classes = (permissions.IsAuthenticated&GridBackendDatasetPermissions,)
    authentication_classes = (GridBackendAuthentication,)

    def get(self,request):
        
        datasets = Dataset.objects.filter(user=request.user.username)
        serializer = DatasetSeraializer(datasets, many = True)
        for x in serializer.data:
            if x['mode'] == 'SQL':
                with connections['default'].cursor() as cursor:
                    x['fields'] = getColumnList(x['name'],cursor)

        return Response(serializer.data,status = status.HTTP_200_OK)

    def post(self,request):
        data = request.data
        data['organization_id'] = request.user.organization_id
        data['user'] = request.user.username
        with connections['default'].cursor() as cursor:
            cursor.execute('SELECT database_name from organizations where organization_id={}'.format(request.user.organization_id))
            database_name = cursor.fetchone()
        if request.data['mode'] == 'VIZ':
            # -- Role Authorization -- #
            
            serializer = DatasetSeraializer(data = data)
            if serializer.is_valid():
                serializer.save(user = request.user.username)
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
            try:
                # -- Role Authorization -- #
                if request.user.organization_id not in connections.databases:
                    connections.databases[user.organization_id] = {
                        'ENGINE' : 'django.db.backends.mysql',
                        'NAME' : database_name,
                        'OPTIONS' : {
                            'read_default_file' : os.path.join(BASE_DIR, 'cred_dynamic.cnf'),
                        }
                    }
                with connections[request.user.organization_id].cursor() as cursor:
                    # sql = data['sql'][:-1]
                    # createSql = 'CREATE TABLE "{}" AS select * from dblink({}dbname={}{}, {}{}{});'.format(data['name'], "'",os.environ['RDS_DB_NAME'], "'","'",sql.replace('`','"'),"'")
                    # cursor.execute(data['sql'][:-1])
                    # print(resolve(request.path).app_name)
                    dataset_model = get_model(data['name'],Dataset._meta.app_label,cursor, 'CREATE', data['sql'][:-1])
                    admin.site.register(dataset_model)
                del connections[user.organization_id]
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
                
            user = user.objects.get(user = request.user)
            data['mode'] = 'SQL'
            serializer = DatasetSeraializer(data = data)
            if serializer.is_valid():
                serializer.save(user = user)
            return Response({'message' : 'success'},status=status.HTTP_201_CREATED)

        return Response(serializer.errors,status = status.HTTP_400_BAD_REQUEST)

class DatasetDetail(APIView):

    permission_classes = (permissions.IsAuthenticated&GridBackendDatasetPermissions,)
    authentication_classes = (GridBackendAuthentication,)

    def get_object(self,dataset_id,user):
        try:
            return Dataset.objects.filter(user = user.username).get(dataset_id = dataset_id)

        except Dataset.DoesNotexist:
            raise Http404
    

    def load_data(self, location):
        subprocess.call('rdb --c protocol {} | redis-cli -n 0 --pipe'.format(location), shell=True)

    def post(self,request):
        
        # -- Role Authorization -- #
        dataset = self.get_object(request.data['dataset_id'],request.user)
        user = request.user
        with connections['rds'].cursor() as cursor:
            cursor.execute('select database_name from organizations where organization_id="{}";'.format(request.user.organization_id))
            database_name = cursor.fetchone()
        r = redis.Redis(host='127.0.0.1', port=6379, db=0)
        if dataset.mode == 'SQL':
            if request.data['view_mode'] == 'view':
                try:
                    self.load_data(os.path.join(BASE_DIR,'{}.rdb'.format(user.organization_id)))
                except Exception as e:
                    print(e)
                    return Response(status=status.HTTP_204_NO_CONTENT)
                data = []
                print(r.dbsize())
                for x in range(1,r.dbsize()+1):
                    data.append(json.dumps(r.hgetall('{}.{}.{}'.format(user.organization_id, dataset.dataset_id, str(x)))))
                r.flushdb()  
                return Response(data,status=status.HTTP_200_OK)
            else:
                r.config_set('dbfilename', '{}.rdb'.format(user.organization_id))
                r.config_rewrite()
                try:
                    self.load_data(os.path.join(BASE_DIR, '{}.rdb'.format(user.organization_id)))
                except:
                    pass
                if profile.organization_id not in connections.databases:
                    connections.databases[profile.organization_id] = {
                        'ENGINE' : 'django.db.backends.mysql',
                        'NAME' : database_name,
                        'OPTIONS' : {
                            'read_default_file' : os.path.join(BASE_DIR, 'cred_dynamic.cnf'),
                        }
                    }
                with connections[user.organization_id].cursor() as cur:
                    cur.execute(dataset.sql.replace('"', '`'))
                    dataset_data = dictfetchall(cur)
                    serializer = GeneralSerializer(data = dataset_data, many = True)
                table_data = serializer.data
                p = r.pipeline()
                for a in table_data:
                    id_count +=1
                    p.hmset('{}.{}.{}'.format(user.organization_id, dataset.dataset_id ,str(id_count)), {**dict(a)})
                try:
                    p.execute()
                except Exception as e:        
                    print(e)
                del connections[user.organization_id]
                data = []
                for x in range(1,id_count+1):
                    for c in model_fields:
                        r.hsetnx('{}.{}.{}'.format(user.organization_id, dataset.dataset_id ,str(x)),c,"")
                    data.append(json.dumps(r.hgetall('{}.{}.{}'.format(user.organization_id, dataset.dataset_id ,str(x)))))
                r.save()
                try:
                    shutil.copy(os.path.join('/var/lib/redis/6379', '{}.rdb'.format(user.organization_id)),BASE_DIR)
                except Exception as e:
                    print(e)
                r.flushdb()
                r.config_set('dbfilename', 'dump.rdb')
                r.config_rewrite()   
                return Response(data,status=status.HTTP_200_OK)

        else:
            if request.data['view_mode'] == 'view':
                try:
                    self.load_data(os.path.join(BASE_DIR,'{}.rdb'.format(user.organization_id)))
                except Exception as e:
                    print(e)
                    return Response(status=status.HTTP_204_NO_CONTENT)
                data = []
                print(r.dbsize())
                for x in range(1,r.dbsize()+1):
                    data.append(json.dumps(r.hgetall('{}.{}.{}'.format(user.organization_id, dataset.dataset_id, str(x)))))
                r.flushdb()  
                return Response(data,status=status.HTTP_200_OK)
            else:
                model = dataset.get_django_model()
                tables = Table.objects.filter(dataset = dataset)
                joins = Join.objects.filter(dataset =  dataset)
                model_fields = [f.name for f in model._meta.get_fields() if f.name is not 'id']
                model_data = []
                data = []  
                r.config_set('dbfilename', '{}.rdb'.format(user.organization_id))
                r.config_rewrite()
                try:
                    self.load_data(os.path.join(BASE_DIR, '{}.rdb'.format(user.organization_id)))
                except:
                    pass
                for t in tables:
                    if user.organization_id not in connections.databases:
                        connections.databases[user.organization_id] = {
                            'ENGINE' : 'django.db.backends.mysql',
                            'NAME' : database_name[0],
                            'OPTIONS' : {
                                'read_default_file' : os.path.join(BASE_DIR, 'cred_dynamic.cnf'),
                            }
                        }
                    with connections[user.organization_id].cursor() as cursor:
                        cursor.execute('select SQL_NO_CACHE * from `%s`'%(t.name))
                        table_data = dictfetchall(cursor)

                        table_model = get_model(t.name,model._meta.app_label,cursor, 'READ')
                        DynamicFieldsModelSerializer.Meta.model = table_model
                        
                        context = {
                            "request" : request,
                        }
                        
                        dynamic_serializer = DynamicFieldsModelSerializer(table_data,many = True,fields = set(model_fields))
                        model_data.append({ 'name' : t.name,'data' : dynamic_serializer.data})
                    del connections[user.organization_id]
                    call_command('makemigrations')
                    call_command('migrate', database = 'default',fake = True)
                        
                join_model_data=[]

                id_count = 0
                
                p = r.pipeline()

                if joins.count() == 0:
                    for x in model_data:
                        for a in x['data']:
                            id_count +=1
                            p.hmset('{}.{}.{}'.format(user.organization_id, dataset.dataset_id ,str(id_count)), {**dict(a)})
                    try:
                        p.execute()
                    except Exception as e:        
                        print(e)
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
                                                        p.hmset('{}.{}.{}'.format(user.organization_id, dataset.dataset_id ,str(id_count)), {**X,**z}) 
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
                                                        p.hmset('{}.{}.{}'.format(user.organization_id, dataset.dataset_id ,str(id_count)), {**X,**z})
                                                break       
                            continue
                        if join.type == 'Right-Join':
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
                                                    id_count += 1
                                                    join_model_data.append({**X, 'id' : id_count})
                                                else:
                                                    for z in check:
                                                        print({**z,**X})
                                                        id_count += 1
                                                        p.hmset('{}.{}.{}'.format(user.organization_id, dataset.dataset_id ,str(id_count)), {**z,**X})
                                                break
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
                                                    p.hmset('{}.{}.{}'.format(user.organization_id, dataset.dataset_id ,str(id_count)), {**X,**z})
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
                                            break
                                    if f == 0:
                                        id_count+=1
                                        p.hmset('{}.{}.{}'.format(user.organization_id, dataset.dataset_id ,str(id_count)), {**X})

                            continue
                    try:
                        p.execute()
                    except Exception as e:        
                        print(e)
                data = []
                for x in range(1,id_count+1):
                    for c in model_fields:
                        r.hsetnx('{}.{}.{}'.format(user.organization_id, dataset.dataset_id ,str(x)),c,"")
                    data.append(json.dumps(r.hgetall('{}.{}.{}'.format(user.organization_id, dataset.dataset_id ,str(x)))))
                r.save()
                try:
                    shutil.copy(os.path.join('/var/lib/redis/6379', '{}.rdb'.format(user.organization_id)),BASE_DIR)
                except Exception as e:
                    print(e)
                r.flushdb()
                r.config_set('dbfilename', 'dump.rdb')
                r.config_rewrite()   
                return Response(data,status=status.HTTP_200_OK)
        return Response({'message' : 'error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
class ReportGenerate(viewsets.ViewSet):

    permission_classes = (permissions.IsAuthenticated,)
    authentication_classes = (GridBackendAuthentication,)
    color_choices = ["#3e95cd", "#8e5ea2","#3cba9f","#e8c3b9","#c45850","#66FF66","#FB4D46", "#00755E", "#FFEB00", "#FF9933"]

    def report_options(self,request):

        report_type = request.data['type']
        if report_type == 'hor_bar':
            return Response({'options' : ['X_field','Y_field']})

    def get_object(self,dataset_id,user):
        try:
            return Dataset.objects.filter(user = user.username).get(dataset_id = dataset_id)

        except Dataset.DoesNotexist:
            raise Http404
    
    def func(self, pct, allvals):
        absolute = int(pct/100.*np.sum(allvals))
        return "{:.1f}%\n({:d})".format(pct, absolute)
    
    def load_data(self, location):
        subprocess.call('rdb --c protocol {} | redis-cli -n 0 --pipe'.format(location), shell=True)
    
    def check(self,options,request):
        decode_options = {k.decode('utf8').replace("'", '"'): v.decode('utf8').replace("'", '"') for k,v in options.items()}
        for k,v in decode_options.items():
            if decode_options[k] != request.data['options'][k]:
                return False
        return True

    def report_generate(self,request):

        report_type = request.data['type']
        data = []
        user = request.user
        r1 = redis.StrictRedis(host='127.0.0.1', port=6379, db=1)
        if r1.exists('df') != 0 and self.check(r1.hgetall('conf'),request):
            print('hellloo')
            df = pickle.loads(zlib.decompress(r1.get("df")))
            model_fields = [(k.decode('utf8').replace("'", '"'),v.decode('utf8').replace("'", '"')) for k,v in r1.hgetall('fields').items()]
        else:
            EXPIRATION_SECONDS = 600
            r = redis.Redis(host='127.0.0.1', port=6379, db=0)
            if request.data['op_table'] == 'dataset':
                dataset = request.data['dataset']
                dataset = self.get_object(dataset,request.user)
                model = dataset.get_django_model()
                model_fields = [(f.name, f.get_internal_type()) for f in model._meta.get_fields() if f.name is not 'id']
                r = redis.Redis(host='127.0.0.1', port=6379, db=0)
                try:
                    self.load_data(os.path.join(BASE_DIR,'{}.rdb'.format(user.organization_id)))
                except Exception as e:
                    print(e)
                    return Response(status=status.HTTP_204_NO_CONTENT)
                data = []
                print(r.dbsize())
                for x in range(1,r.dbsize()+1):
                    data.append({k.decode('utf8').replace("'", '"'): v.decode('utf8').replace("'", '"') for k,v in r.hgetall('{}.{}.{}'.format(user.organization_id, dataset.dataset_id, str(x))).items()})
                r.flushdb() 
            else:
                with connections['rds'].cursor() as cursor:
                    cursor.execute('select SQL_NO_CACHE * from "{}"'.format(dataset.name))
                    table_data = dictfetchall(cursor)
                    table_model = get_model(t.name,model._meta.app_label,cursor, 'READ')
                    model_fields = [(f.name, f.get_internal_type()) for f in table_model._meta.get_fields() if f.name is not 'id']
                    GeneralSerializer.Meta.model = table_model
                    
                    context = {
                        "request" : request,
                    }
                    
                    dynamic_serializer = GeneralSerializer(table_data,many = True)
                    call_command('makemigrations')
                    call_command('migrate', database = 'default',fake = True)
                serializer_data = dynamic_serializer.data
                p = r.pipeline()
                for a in serializer_data:
                    id_count +=1
                    p.hmset('{}.{}.{}'.format(user.organization_id, dataset.dataset_id ,str(id_count)), {**dict(a)})
                try:
                    p.execute()
                except Exception as e:        
                    print(e)
                del connections[user.organization_id]
                data = []
                for x in range(1,id_count+1):
                    for c in model_fields:
                        r.hsetnx('{}.{}.{}'.format(user.organization_id, dataset.dataset_id ,str(x)),c,"")
                    data.append({k.decode('utf8').replace("'", '"'): v.decode('utf8').replace("'", '"') for k,v in r.hgetall('{}.{}.{}'.format(user.organization_id, dataset.dataset_id, str(x))).items()})
                r.save()
                try:
                    shutil.copy(os.path.join('/var/lib/redis/6379', '{}.rdb'.format(user.organization_id)),BASE_DIR)
                except Exception as e:
                    print(e)
                r.flushdb()
                r.config_set('dbfilename', 'dump.rdb')
                r.config_rewrite() 

            df = pd.DataFrame(data)
            r1.setex("df", EXPIRATION_SECONDS, zlib.compress( pickle.dumps(df)))
            r1.hmset('conf',request.data['options'])
            r1.hmset('fields', { x[0] : x[1] for x in model_fields })
        
        for x in model_fields:
            if x[1] == 'FloatField':
                df = df.astype({ x[0] : 'float64'})
            if x[1] == 'IntegerField':
                df = df.astype({ x[0] : 'int64'})
            if x[1] == 'CharField' or x[1] == 'TextField':
                df = df.astype({ x[0] : 'object'})
            if x[1] == 'DateField':
                df = df.astype({ x[0] : 'datetime64'})

        print(df.dtypes)
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
            df_required = df.loc[:,df.columns.isin(all_fields)].dropna()
            print(df_required)
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

    permission_classes = (permissions.IsAuthenticated&GridBackendReportPermissions,)
    authentication_classes = (GridBackendAuthentication,)
    
    def get(self,request):
        if request.user.is_superuser:
            reports = Report.objects.filter(organization_id=request.user.organization_id).all()
        if request.user.role == 'Developer':
            reports = Report.objects.filter(organization_id=request.user.organization_id).filter(user = request.user.username) | Report.objects.filter(organization_id = request.user.organization_id).filter(shared__user_id__contains = request.user.username)
        else:
            reports =Report.objects.filter(organization_id = request.user.organization_id).filter(shared__user_id__contains = request.user.username)
        serializer = ReportSerializer(reports, many=True)

        return Response(serializer.data, status = status.HTTP_200_OK)
    
    def get_object(self,dataset_id,user):
        try:
            return Dataset.objects.filter(user = user.username).get(dataset_id = dataset_id)
        except:
            return Http404

    
    def get_report_object(self,request,report_id,user):
        try:
            obj = Report.objects.filter(organization_id=user.organization_id)
            if self.check_object_permissions(self, request, obj):
                return obj.filter(user=user.username).get(report_id=report_id) | obj.filter(shared__user_id__contains= user.username).get(report_id = report_id)
            else:
                return Response('Unauthorized', status = status.HTTP_401_UNAUTHORIZED)
        except Report.DoesNotExist:
            raise Http404

    def post(self, request):
        data = request.data
        data['organization_id'] = request.user.organization_id
        data['user'] = request.user.username
        if data['op_table'] == 'dataset':
            dataset = self.get_object(data['dataset_id'],request.user)
        serializer = ReportSerializer(data = data)

        if serializer.is_valid():
            if data['op_table'] == 'dataset':
                serializer.save(user = request.user.username, dataset = dataset)
            else:
                serializer.save(user_id = request.user.user_id, worksheet = data['worksheet_id'])

            return Response(serializer.data,status = status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)
    
    def put(self,request):

        data = request.data
        try:
            report = self.get_report_object(request,data['report_id'], request.user)
        except:
            return Response('Unauthorized', status=status.HTTP_401_UNAUTHORIZED)
        serializer = ReportSerializer(report, data = data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status = status.HTTP_202_ACCEPTED)
        
        return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)

    def delete(self,request):

        data = request.data
        try:
            report = self.get_report_object(request,data['report_id'], request.user)
        except:
            return Response('Unauthorized', status=status.HTTP_401_UNAUTHORIZED)
        serializer = ReportSerializer(report, data = data)

        if serializer.is_valid():
            serializer.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

class DashboardList(APIView):

    permission_classes = (permissions.IsAuthenticated&GridBackendDashboardPermissions,)
    authentication_classes = (GridBackendAuthentication,)

    def get(self,request):
        if request.is_superuser:
            dashboards = Dashboard.objects.filter(organization_id=request.user.organization_id).all()
        if request.user.role == 'Developer':
            dashboards = Dashboard.objects.filter(organization_id=request.user.organization_id).filter(user=request.user.username) | Dashboard.objects.filter(organization_id=organization_id).filter(reports__shared__user_id__contains = request.user.username)
        else:
            Dashboard.objects.filter(organization_id=request.user.organization_id).filter(reports__shared__user_id__contains=request.user.username)    
        serializer = DashboardSerializer(dashboards, many = True)
        return Response(serializer.data, status = status.HTTP_200_OK)
    
    def get_report_objects(self, organization_id, report_id_list):
        try: 
            return Report.objects.filter(organization_id=organization_id).filter(user = user.username).filter(report_id__in = report_id_list)
        except:
            return Http404

    def get_object(self, request, dashboard_id, user):
        try:
            obj = Dashboard.objects.filter(organization_id = user.organization_id)
            if self.check_object_permissions(self, request, obj):
                return obj.filter(user = user.username).get(report_id = report_id) | obj.filter(shared__user_id__contains = user.username).get(dashboard_id = dashboard_id)
            else:
                return Response('Unauthorized', status = status.HTTP_401_UNAUTHORIZED)
        except Dashboard.DoesNotExist:
            raise Http404

    def post(self, request):
        data = request.data
        data['organization_id'] = request.user.organization_id
        data['user'] = request.user.username
        reports = self.get_report_objects(request.user.organization_id, data['report_id_list'])
        serializer = DashboardSerializer(data=data)
        if serializer.is_valid:
            serializer.save(reports = reports)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request):

        data = request.data

        try:
            dashboard = self.get_object(request, data['dashboard_id'], request.user)
        except:
            return Response('Unauthorized', status=status.HTTP_401_UNAUTHORIZED)
        
        serializer = DashboardSerializer(dashboard,data=data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):

        data = request.data
        try:
            dashboard = self.get_object(request, data['dashboard_id'], request.user)
        except:
            return Response('Unauthorized', status=status.HTTP_401_UNAUTHORIZED)

        serializer = DashboardSerializer(dashboard, data= data)
        if serializer.is_valid():
            serializer.delete()
            return Response(status= status.HTTP_204_NO_CONTENT)
        return Response(serializer.errors, status= status.HTTP_400_BAD_REQUEST)

class SharingReports(viewsets.ViewSet):

    permission_classes=(permissions.IsAuthenticated&GridBackendDatasetPermissions,)
    authentication_classes=(GridBackendAuthentication,)

    def get_report_object(self, organization_id,report_id,user):
        try:
            obj = Report.objects.filter(organization_id = organization_id).filter(user = user.username).get(report_id = report_id)
            self.check_object_permissions(self, request, obj)
            return obj
        except:
            return Http404
    
    def users_list(self,request):
        try:
            status = requests.post('{}/user/allUsers'.format(os.environ['GRID_API']), headers={'Authorization':'Bearer {}'.format(request.user.token)})
            res_data = json.loads(status.text)['data']
            out_data = []
            if request.user.role == 'Developer':
                out_data = [i for i in res_data if (i['role'] == 'Developer')]
            if request.user.role == 'admin':
                out_data = res_data
            return Response(out_data, status=status.HTTP_200_OK)
        except:
            return Response('error', status=status.HTTP_400_BAD_REQUEST)

    def report_share(self, request):

        data = request.data
        report = self.get_report_object(request.user.organization_id,data['report_id'], request.user)
        for x in data['user_id_list']:
            serializer = SharedReportSerializer(data=data)
            if serializer.is_valid():
                serializer.save(report = report, shared_user_id=request.user.username, user_id = x)
            else:
                return Response('error', status=status.HTTP_400_BAD_REQUEST)
        return Response('success', status = status.HTTP_201_CREATED)
    
    def dashboard_share(self, request):
        
        data = request.data
        for x in data['report_id_list']:
            report = self.get_report_object(request.user.organization_id, x, request.user)
            for c in data['user_id_list']:
                serializer = SharedReportSerializer(data=data)
                if serializer.is_valid():
                    serializer.save(report = report, shared_user_id=request.user.username, user_id = x)
                else:
                    return Response('error', status=status.HTTP_400_BAD_REQUEST)
        return Response('success', status = status.HTTP_201_CREATED)