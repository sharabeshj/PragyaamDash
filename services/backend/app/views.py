from django.shortcuts import render

from app.models import Dataset,Field,Setting,Table,Join,Report
from app.serializers import DatasetSeraializer,FieldSerializer,SettingSerializer,GeneralSerializer,TableSerializer,JoinSerializer,DynamicFieldsModelSerializer,ReportSerializer, DashboardSerializer,SharedReportSerializer, FilterSerializer, DashboardReportOptions
from app.utils import get_model,dictfetchall, getColumnList
from app.tasks import datasetRefresh, load_data
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
# from rq import Queue,Worker
# from rq_scheduler import Scheduler
from datetime import timedelta

from django_celery_beat.models import CrontabSchedule, PeriodicTask

import collections
import simplejson as json
import time
from django_pandas.io import read_frame
# from django_rq import get_scheduler,get_queue
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

# @job

class DatasetList(viewsets.ViewSet):

    permission_classes = (permissions.IsAuthenticated&GridBackendDatasetPermissions,)
    authentication_classes = (GridBackendAuthentication,)
    
    def get_object(self,dataset_id,user):
        try:
            return Dataset.objects.filter(user = user.username).get(dataset_id = dataset_id)

        except Dataset.DoesNotexist:
            raise Http404

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
        with connections['rds'].cursor() as cursor:
            cursor.execute('SELECT database_name from organizations where organization_id="{}"'.format(request.user.organization_id))
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

    def add_refresh(self,request,id):
        dataset = self.get_object(id,request.user)
        user = request.user
        data = request.data
        # # queue = Queue(user.organization_id, connection=redis.StrictRedis(host='127.0.0.1', port=6379, db=3))
        # # start_worker(user.organization_id)
        # scheduler = get_scheduler('default')
        # # scheduler = Scheduler(queue=queue, connection=redis.Redis(host='127.0.0.1', port=6379, db=3))
        # job = scheduler.cron(
        #     data['cron'],
        #     func = datasetRefresh,
        #     args = [user.organization_id,'{}'.format(dataset.dataset_id)],
        #     repeat=None,
        #     queue_name='default'
        # )
        # # job = scheduler.enqueue_in(timedelta(minutes=1), datasetRefreshCron,user.organization_id,'{}'.format(dataset.dataset_id))
        # data['job_id'] = job.id

        schedule,_ = CrontabSchedule.objects.get_or_create(
            minute=data['minute'],
            hour=data['hour'],
            day_of_week=data['day_of_week'],
            month_of_year=data['month_of_year']
        )
        periodic_task = PeriodicTask.objects.create(
            crontab=schedule,
            name='{}.{}'.format(user.organization_id, dataset.dataset_id),
            task='app.tasks.datasetRefresh',
            args=json.dumps([user.organization_id, '{}'.format(dataset.dataset_id)])
        )
        data['scheduler'] = periodic_task
        serializer = DatasetSeraializer(dataset,data = data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status = status.HTTP_202_ACCEPTED)
        
        return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)        

    def edit_refresh(self,request,id):
        dataset = self.get_object(id,request.user)
        data = request.data
        job_id = dataset.job_id
        scheduler = PeriodicTask.objects.get(name = dataset.scheduler.name)
        schedule,_ = CrontabSchedule.objects.get_or_create(
            minute=data['minute'],
            hour=data['hour'],
            day_of_week=data['day_of_week'],
            month_of_year=data['month_of_year']
        )
        scheduler.update(crontab = schedule)

        serializer = DatasetSeraializer(dataset,data = data)
        if serializer.is_valid():
            serializer.save(scheduler = scheduler)
            return Response(serializer.data, status = status.HTTP_202_ACCEPTED)
        
        return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)

    def delete_refresh(self,request,id):
        dataset = self.get_object(id,request.user)
        job_id = dataset.job_id
        scheduler = PeriodicTask.objects.get(name = dataset.scheduler.name)
        scheduler.delete()
        return Response(status=HTTP_204_NO_CONTENT)

class DatasetDetail(APIView):

    permission_classes = (permissions.IsAuthenticated&GridBackendDatasetPermissions,)
    authentication_classes = (GridBackendAuthentication,)

    def get_object(self,dataset_id,user):
        try:
            return Dataset.objects.filter(user = user.username).get(dataset_id = dataset_id)

        except Dataset.DoesNotexist:
            raise Http404

    def post(self,request):
        
        # -- Role Authorization -- #
        dataset = self.get_object(request.data['dataset_id'],request.user)
        user = request.user
        with connections['rds'].cursor() as cursor:
            cursor.execute('select database_name from organizations where organization_id="{}";'.format(request.user.organization_id))
            database_name = cursor.fetchone()
        
        if dataset.mode == 'SQL':
            
            if request.data['view_mode'] == 'view':
                r = redis.Redis(host='127.0.0.1', port=6379, db=0)
                try:
                    load_data(os.path.join(BASE_DIR,'{}.rdb'.format(user.organization_id)),'127.0.0.1', 6379, 0)
                except Exception as e:
                    print(e)
                    return Response(status=status.HTTP_204_NO_CONTENT)
                data = []
                print(r.dbsize())
                for x in range(1,r.dbsize()+1):
                    if r.get('edit.{}.{}.{}'.format(user.organization_id, dataset.dataset_id, str(x))) != None:
                        data.append(json.dumps(r.hgetall('edit.{}.{}.{}'.format(user.organization_id, dataset.dataset_id, str(x)))))
                    else:
                        data.append(json.dumps(r.hgetall('{}.{}.{}'.format(user.organization_id, dataset.dataset_id, str(x)))))
                r.flushdb()  
                return Response(data,status=status.HTTP_200_OK)
            else:
                datasetRefresh(user, dataset)
                return Response(status=status.HTTP_201_CREATED)

        else:
            if request.data['view_mode'] == 'view':
                try:
                    load_data(os.path.join(BASE_DIR,'{}.rdb'.format(user.organization_id)),'127.0.0.1', 6379, 0)
                except Exception as e:
                    print(e)
                    return Response(status=status.HTTP_204_NO_CONTENT)
                data = []
                print(r.dbsize())
                edit = 1
                for x in range(1,r.dbsize()+1):
                    if r.get('edit.{}.{}.{}'.format(user.organization_id, dataset.dataset_id, str(x))) != None:
                        data.append(json.dumps(r.hgetall('edit.{}.{}.{}'.format(user.organization_id, dataset.dataset_id, str(x)))))
                    else:
                        data.append(json.dumps(r.hgetall('{}.{}.{}'.format(user.organization_id, dataset.dataset_id, str(x)))))
                r.flushdb()  
                return Response(data,status=status.HTTP_200_OK)
            else:
                tables = Table.objects.filter(dataset = dataset)
                joins = Join.objects.filter(dataset =  dataset)  
                datasetRefresh(user, dataset, tables,joins) 
                return Response(status=status.HTTP_201_CREATED)
        return Response({'message' : 'error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self,request):
        data = request.data
        dataset = self.get_object(request.data['dataset_id'],request.user)
        r = redis.Redis(host='127.0.0.1', port=6379, db=0)
        r.config_set('dbfilename', '{}.rdb'.format(user.organization_id))
        r.config_rewrite()
        try:
            load_data(os.path.join(BASE_DIR, '{}.rdb'.format(user.organization_id)), '127.0.0.1', 6379, 0)
        except:
            pass
        edit_data = json.loads(data['data'])
        p = r.pipeline()
        id_count = 0
        for a in edit_data:
            id_count +=1
            p.hmset('edit.{}.{}.{}'.format(user.organization_id, dataset.dataset_id ,str(id_count)), a)
        try:
            p.execute()
        except Exception as e:        
            print(e)
        r.save()
        dataset.last_refreshed = datetime.datetime.now()
        dataset.save()
        try:
            shutil.copy(os.path.join('/var/lib/redis/6379', '{}.rdb'.format(user.organization_id)),BASE_DIR)
        except Exception as e:
            print(e)
        r.flushdb()
        r.config_set('dbfilename', 'dump.rdb')
        r.config_rewrite()

class ReportGenerate(viewsets.ViewSet):

    permission_classes = (permissions.IsAuthenticated,)
    authentication_classes = (GridBackendAuthentication,)
    color_choices = ["#3e95cd", "#8e5ea2","#3cba9f","#e8c3b9","#c45850","#66FF66","#FB4D46", "#00755E", "#FFEB00", "#FF9933"]

    def get_object(self,dataset_id,user):
        try:
            return Dataset.objects.filter(user = user.username).get(dataset_id = dataset_id)

        except Dataset.DoesNotexist:
            raise Http404
    
    def func(self, pct, allvals):
        absolute = int(pct/100.*np.sum(allvals))
        return "{:.1f}%\n({:d})".format(pct, absolute)
    
    def check(self,options,request):
        decode_options = {k.decode('utf8').replace("'", '"'): v.decode('utf8').replace("'", '"') for k,v in options.items()}
        for k,v in decode_options.items():
            if decode_options[k] != request.data['options'][k]:
                return False
        return True
    
    def check_filter_value_condition(self, df, condition,value_1, value_2=0):
        if condition == 'equals':
            return df == value_1
        if condition == 'greater_than':
            return df > value_1
        if condition == 'less than':
            return df < value_1
        if condition == 'greater_than_or_equals':
            return df >= value_1
        if condition == 'less_than_or_equals':
            return df <= value_1
        if condition == 'between':
            return (df >= value_1) & (df <= value_2)

    def report_generate(self,request):

        report_type = request.data['type']
        data = []
        user = request.user
        r1 = redis.StrictRedis(host='127.0.0.1', port=6379, db=1)
        if r1.exists('{}.{}'.format(user.organization_id,dataset.dataset_id)) != 0 and self.check(r1.hgetall('conf'),request) and request.data['dataset'] == r1.get('id'):
            print('hellloo')
            df = pickle.loads(zlib.decompress(r1.get("{}.{}".format(user.organization_id,dataset.dataset_id))))
            model_fields = [(k.decode('utf8').replace("'", '"'),v.decode('utf8').replace("'", '"')) for k,v in r1.hgetall('fields').items()]

        else:
            EXPIRATION_SECONDS = 600
            r = redis.Redis(host='127.0.0.1', port=6379, db=0)
            if request.data['op_table'] == 'dataset':
                dataset_id = request.data['dataset']
                dataset = self.get_object(dataset_id,request.user)
                model = dataset.get_django_model()
                model_fields = [(f.name, f.get_internal_type()) for f in model._meta.get_fields() if f.name is not 'id']
                r = redis.Redis(host='127.0.0.1', port=6379, db=0)
                try:
                    load_data(os.path.join(BASE_DIR,'{}.rdb'.format(user.organization_id)),'127.0.0.1', 6379, 0)
                except Exception as e:
                    print(e)
                    return Response(status=status.HTTP_204_NO_CONTENT)
                data = []
                print(r.dbsize())
                for x in range(1,r.dbsize()+1):
                    if r.get('edit.{}.{}.{}'.format(user.organization_id, dataset.dataset_id, str(x))) != None:
                        data.append({k.decode('utf8').replace("'", '"'): v.decode('utf8').replace("'", '"') for k,v in r.hgetall('edit.{}.{}.{}'.format(user.organization_id, dataset.dataset_id, str(x))).items()})
                    else:
                        data.append({k.decode('utf8').replace("'", '"'): v.decode('utf8').replace("'", '"') for k,v in r.hgetall('{}.{}.{}'.format(user.organization_id, dataset.dataset_id, str(x))).items()})
                    
                r.flushdb() 
            else:
                with connections['rds'].cursor() as cursor:
                    cursor.execute('select SQL_NO_CACHE * from "{}"'.format(request.data['dataset']))
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
    
                r.flushdb()
                r.config_set('dbfilename', 'dump.rdb')
                r.config_rewrite() 

            df = pd.DataFrame(data)
            r1.setex("{}.{}".format(user.organization_id,dataset.dataset_id), EXPIRATION_SECONDS, zlib.compress( pickle.dumps(df)))
            r1.hmset('conf',request.data['options'])
            r1.set('id', request.data['dataset'])
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
        
        dict_fields = dict(model_fields)
        for filter in request.data['filters']:
            options = json.loads(filter.options)
            if filter.field_operation == 'filter_by_name':
                condition = df[filter.field_name] in options['values']
                df = df[condition]
            if filter.field_operation == 'filter_by_date':
                df = df[(df[filter.field_name] > options['start_date']) & (df[filter.field_name] < options['end_date'])]
            if filter.field_operation == 'last':
                df = df[self.check_filter_value_condition(df[filter.field_name], options['condition'], options['value'])]
            if filter.field_operation == 'sum':
                df = df[self.check_filter_value_condition(df[filter.field_name].sum(), options['condition'], options['value'])]
            if filter.field_operation == 'count':
                df = df[self.check_filter_value_condition(df[filter.field_name].count(), options['condition'], options['value'])]
            if filter.field_operation == 'min':
                df = df[self.check_filter_value_condition(df[filter.field_name].max(), options['condition'], options['value'])]
            if filter.field_operation == 'max':
                df = df[self.check_filter_value_condition(df[filter.field_name].min(), options['condition'], options['value'])]
        
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

    permission_classes=(permissions.IsAuthenticated&GridBackendDatasetPermissions|GridBackendReportPermissions,)
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

class FilterList(viewsets.ViewSet):

    authentication_classes = (GridBackendAuthentication, )
    permission_classes = (permissions.IsAuthenticated|GridBackendReportPermissions|GridBackendDashboardPermissions,)

    def get_report_object(self,reqeust,report_id, user):
        try:
            obj = Report.objects.filter(organization_id=user.organization_id)
            if self.check_object_permissions(self, request, obj):
                return obj.filter(user=user.username).get(report_id=report_id) | obj.filter(shared__user_id__contains= user.username).get(report_id = report_id)
            else:
                return Response('Unauthorized', status = status.HTTP_401_UNAUTHORIZED)
        except Report.DoesNotExist:
            raise Http404
    
    def get_dashboard_object(self, request, dashboard_id, user):
        try:
            obj = Dashboard.objects.filter(organization_id = user.organization_id)
            if self.check_object_permissions(self, request, obj):
                return obj.filter(user = user.username).get(dashboard_id = dashboard_id) | obj.filter(shared__user_id__contains = user.username).get(dashboard_id = dashboard_id)
            else:
                return Response('Unauthorized', status = status.HTTP_401_UNAUTHORIZED)
        except Dashboard.DoesNotExist:
            raise Http404
    
    def get_dashboard_report_options_object(self,dashboard_id, report_id):
        try:
            return DashboardReportOptions.objects.filter(dashboard = dashboard_id).get(report_id = report_id)
        except DashboardreportOptions.DoesNotExist:
            raise Http404

    def get_object(self,filter_id, user):
        try:
            return Filter.objects.filter(organization_id = user.organization_id).filter(user = user.username).get(filter_id = filter_id)
        except Filter.DoesNotExist:
            raise Http404

    def get_for_reports(self,request):
        filters = Filter.objects.filter(organization_id = request.user.organization_id).filter(user = request.user.username).filter(dataset = request.data['dataset_id'])
        serializer  = FilterSerializer(filters, many = True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_for_dashboard(self,request):
        filters = Filter.objects.filter(organization_id = request.user.organization_id).filter(user = request.user.username).filter(dashboard_reports__dashboard = request.data['dashboard'])
        serializer = FilterSerializer(filters, many = True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create_for_report(self,request):
        data = request.data
        data['organization_id'] = request.user.organization_id
        data['user'] = request.user.username
        report = self.get_report_object(request, data['report_id'], request.user)
        serializer = FilterSerializer(data = data)

        if serializer.is_valid():
            serializer.save(report = report)
            return Response(serializer.data,status = status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)
    
    def create_for_dashboard(self, request):
        data = request.data
        data['organization_id'] = request.user.organization_id
        data['user'] = request.user.username
        dashboard = self.get_dashboard_object(request, data['dashboard_id'],request.user)
        for x in data['report_ids']:
            dashboard_report = self.get_dashboard_report_options_object(data['dashboard_id'], x)
            serializer = FilterSerializer(data = data)

            if serializer.is_valid():
                serializer.save(dashboard_report = dashboard_report)
            else:
                return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)
        return Response(serializer.data,status = status.HTTP_201_CREATED)
        
    def edit(self, request):
        data = request.data
        filter = self.get_object(data['filter_id'], request.user)
        serializer = FilterSerializer(filter, data = data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status = status.HTTP_202_ACCEPTED)
        
        return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)

    def delete(self,request):
        data = request.data
        filter = self.get_object(data['filter_id'], request.user)
        filter.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)