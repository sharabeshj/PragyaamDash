from django.shortcuts import render

from app.models import Dataset,Field,Setting,Table,Join,Report
from app.serializers import (DatasetSeraializer,
                                FieldSerializer,
                                SettingSerializer,
                                GeneralSerializer,
                                TableSerializer,
                                JoinSerializer,
                                DynamicFieldsModelSerializer,
                                ReportSerializer, 
                                DashboardSerializer,
                                SharedReportSerializer, 
                                FilterSerializer, 
                                DashboardReportOptionsSerializer,
                                SharedDashboardSerializer)
from app.utils import get_model,dictfetchall, getColumnList
from app.tasks import datasetRefresh, load_data
from app.Authentication import (GridBackendAuthentication,  
                                GridBackendDatasetPermissions, 
                                GridBackendReportPermissions, 
                                GridBackendDashboardPermissions,
                                GridBackendShareReportPermissions,
                                GridBackendShareDashboardPermissions)

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
from django.db.models import Q
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
                    else:
                        return Response(field_serializer.errors, status = status.HTTP_400_BAD_REQUEST)
                    for s in f['settings']:
                        field = Field.objects.filter(dataset__name = data['name']).filter(worksheet = f['worksheet']).get(name = f['name'])
                        settings_serializer = SettingSerializer(data = s)
                        if settings_serializer.is_valid():
                            settings_serializer.save(field = field)
                        else:
                            return Response(settings_serializer.errors, status = status.HTTP_400_BAD_REQUEST)
                for t in data['tables']:
                    table_serializer = TableSerializer(data = t)
                    if table_serializer.is_valid():
                        table_serializer.save(dataset = dataset)
                    else:
                        return Response(table_serializer.errors, status = status.HTTP_400_BAD_REQUEST)
                for j in data['joins']:
                    join_serializer = JoinSerializer(data = j)
                    if join_serializer.is_valid():
                        join_serializer.save(dataset = dataset)
                    else:
                        return Response(join_serializer.errors, status = status.HTTP_400_BAD_REQUEST)
                # model = dataset.get_django_model()
                # admin.site.register(model)
                # call_command('makemigrations')
                # call_command('migrate', database = 'default',fake = True)
                # last_migration = MigrationRecorder.Migration.objects.latest('id')
                # last_migration_object = sqlmigrate.Command()
                # last_migration_sql = last_migration_object.handle(app_label = last_migration.app, migration_name = last_migration.name,database = 'default', backwards = False)
                # for item in last_migration_sql.split('\n'):
                #     if item.split(' ')[0] == 'CREATE':
                #         with connections['default'].cursor() as cursor:
                #             cursor.execute(item)
                return Response(serializer.data,status=status.HTTP_201_CREATED)

        else:
            # with connections['rds'].cursor() as cursor:
            #     cursor.execute('SELECT database_name from organizations where organization_id="{}"'.format(request.user.organization_id))
            #     database_name = cursor.fetchone()
            # try:
            #     # -- Role Authorization -- #
            #     if request.user.organization_id not in connections.databases:
            #         connections.databases[user.organization_id] = {
            #             'ENGINE' : 'django.db.backends.mysql',
            #             'NAME' : database_name,
            #             'OPTIONS' : {
            #                 'read_default_file' : os.path.join(BASE_DIR, 'cred_dynamic.cnf'),
            #             }
            #         }
            #     with connections[request.user.organization_id].cursor() as cursor:
                    # sql = data['sql'][:-1]
                    # createSql = 'CREATE TABLE "{}" AS select * from dblink({}dbname={}{}, {}{}{});'.format(data['name'], "'",os.environ['RDS_DB_NAME'], "'","'",sql.replace('`','"'),"'")
                    # cursor.execute(data['sql'][:-1])
                    # print(resolve(request.path).app_name)
                #     dataset_model = get_model(data['name'],Dataset._meta.app_label,cursor, 'CREATE', data['sql'][:-1])
                #     admin.site.register(dataset_model)
                # del connections[user.organization_id]
                # call_command('makemigrations')
                # call_command('migrate', database='default', fake=True)
                # last_migration = MigrationRecorder.Migration.objects.latest('id')
                # last_migration_object = sqlmigrate.Command()
                # last_migration_sql = last_migration_object.handle(app_label = last_migration.app, migration_name = last_migration.name, database = 'default', backwards = False)
                # for item in last_migration_sql.split('\n'):
                #     if item.split(' ')[0] == 'CREATE':
                #        with connections['default'].cursor() as cur:
                #             cur.execute(item)
            # except Exception as e:
            #     return Response("error", status = status.HTTP_400_BAD_REQUEST)
                
            user = user.objects.get(user = request.user)
            data['mode'] = 'SQL'
            serializer = DatasetSeraializer(data = data)
            if serializer.is_valid():
                serializer.save(user = user)
            return Response({'message' : 'success'},status=status.HTTP_201_CREATED)

        return Response(serializer.errors,status = status.HTTP_400_BAD_REQUEST)

    def edit(self, request, id):
        dataset = self.get_object(id,request.user)
        user = request.user
        data = request.data
        serializer = DatasetSerializer(dataset, data = data)
        if dataset.mode == 'VIZ':
            if serializer.is_valid():
                serializer.save()
                worksheets = [f['worksheet'] for f in data['fields'] if f['worksheet'] not in worksheets]
                dataset.field_set.filter(~Q(name__in = data['fields']) & ~Q(worksheet__in = worksheets)).delete()
                for f in data['fields']:
                    if not dataset.field_set.filter(worksheet = f['worksheet']).filter(name = f['name']).exists():
                        field_serializer = FieldSerializer(data = f)
                        if field_serializer.is_valid():
                            field_serializer.save(dataset = dataset)
                        else:
                            return Response(field_serializer.errors, status = status.HTTP_400_BAD_REQUEST)
                    field = dataset.field_set.filter(worksheet = f['worksheet']).get(name = f['name'])
                    for s in f['settings']:
                        if not field.setting_set.filter(name = s['name']).exists():
                            settings_serializer = SettingSerializer(data = s)
                            if settings_serializer.is_valid():
                                settings_serializer.save(field = field)
                            else:
                                return Response(settings_serializer.errors, status = status.HTTP_400_BAD_REQUEST)
                dataset.table_set.filter(~Q(name__in = data['tables'])).delete()
                for t in data['tables']:
                    if not dataset.table_set.filter(name = t['name']).exists():
                        table_serializer = TableSerializer(data = f)
                        if table_serializer.is_valid():
                            table_serializer.save(dataset = dataset)
                        else:
                            return Response(table_serializer.errors, status = status.HTTP_400_BAD_REQUEST)
                return Response(serializer.data, status = status.HTTP_202_ACCEPTED)
                fields = [t['field'] for t in data['tables']]
                worksheet_1 = [t['worksheet_1'] for t in data['tables']]
                worksheet_2 = [t['worksheet_2'] for t in data['tables']]
                dataset.join_set.filter(~Q(type__in = data['joins']) | ~Q(field__in = fields) | ~Q(worksheet_1__in = worksheet_1) | ~Q(worksheet_2__in = worksheet_2 )).delete()
                for t in data['joins']:
                    if not dataset.join_set.filter(Q(type = t['type']) & Q(field = t['field']) & Q(worksheet_1 = t['worksheet_1']) & Q(worksheet_2 = t['worksheet_2'])).exists():
                        join_serializer = JoinSerializer(data = f)
                        if join_serializer.is_valid():
                            join_serializer.save(dataset = dataset)
                        else:
                            return Response(table_serializer.errors, status = status.HTTP_400_BAD_REQUEST)
                return Response(serializer.data, status = status.HTTP_202_ACCEPTED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status = status.HTTP_202_ACCEPTED)   
            return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)
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
        #     args = [user.organization_id,dataset.dataset_id],
        #     repeat=None,
        #     queue_name='default'
        # )
        # # job = scheduler.enqueue_in(timedelta(minutes=1), datasetRefreshCron,user.organization_id,dataset.dataset_id)
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
            args=json.dumps([user.organization_id, dataset.dataset_id])
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
        return Response(status=status.HTTP_204_NO_CONTENT)

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
                datasetRefresh(user.organization_id, dataset.dataset_id)
                return Response(status=status.HTTP_201_CREATED)

        else:
            if request.data['view_mode'] == 'view':
                r = redis.Redis(host='127.0.0.1', port=6379, db=0)
                try:
                    load_data(os.path.join(BASE_DIR,'{}.rdb'.format(user.organization_id)),'127.0.0.1', 6379, 0)
                except Exception as e:
                    print(e)
                    return Response(status=status.HTTP_204_NO_CONTENT)
                data = []
                edit = 1
                for x in range(request.data['start'],request.data['end']+1):
                    if r.get('edit.{}.{}.{}'.format(user.organization_id, dataset.dataset_id, str(x))) != None:
                        data.append(json.dumps(r.hgetall('edit.{}.{}.{}'.format(user.organization_id, dataset.dataset_id, str(x)))))
                    else:
                        data.append(json.dumps(r.hgetall('{}.{}.{}'.format(user.organization_id, dataset.dataset_id, str(x)))))
                count = r.dbsize()
                r.flushdb()  
                return Response({'data' : data, 'length': count},status=status.HTTP_200_OK)
            else:
                datasetRefresh(user.organization_id, dataset.dataset_id)
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

    def dataFrameGenerate(self, request, user):
        data = []
        user = request.user
        r1 = redis.StrictRedis(host='127.0.0.1', port=6379, db=1)
        if r1.exists('{}.{}'.format(user.organization_id,request.data['dataset'])) != 0:
            print('hellloo')
            df = pickle.loads(zlib.decompress(r1.get("{}.{}".format(user.organization_id,request.data['dataset']))))
            model_fields = [(k.decode('utf8').replace("'", '"'),v.decode('utf8').replace("'", '"')) for k,v in r1.hgetall('{}.fields'.format(request.data['dataset'])).items()]

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
            r1.hmset('{}.fields'.format(dataset.dataset_id), { x[0] : x[1] for x in model_fields })
        for x in model_fields:
            if x[1] == 'FloatField':
                df = df.astype({ x[0] : 'float64'})
            if x[1] == 'IntegerField':
                df = df.astype({ x[0] : 'int64'})
            if x[1] == 'CharField' or x[1] == 'TextField':
                df = df.astype({ x[0] : 'object'})
            if x[1] == 'DateField':
                df = df.astype({ x[0] : 'datetime64'})
        
        return df,model_fields
    
    def filter_options_generate(self,request):
        
        df,model_fields = self.dataFrameGenerate(request, request.user)

        if request.data['optionRequested'] == 'fields':
            return Response({ 'fields' : model_fields }, status = status.HTTP_200_OK )

        if request.data['optionrequested'] == 'field_options':
            
            if type(df[request.data['field']]) == 'object':
                return Response({ 'data' : df[request.data['field']].unique().toList()}, status = status.HTTP_200_OK )
            else:
                return Response({ 'data' : { 'min' : df[request.data['field']].min(), 'max' : df[request.data['field']].max() }}, status = status.HTTP_200_OK )
            
    def graphDataGenerate(self,df,report_type,field,value=None,group_by=None):
        all_fields = []
        df = df.dropna()
        if report_type in ["scatter","bubble"]:
            data = {
                'datasets' : []
            }
        else:
            if field['type'] in ["DateTimeField","DateField"]:
                df.loc[:,field['name']] = df[field['name']].map(pd.Timestamp.isoformat)
                data = {
                    'labels' : np.unique(np.array(df.loc[:,field['name']])),
                    'datasets' : []
                }
            else:
                df = df.astype({ field['name'] : 'str' })
                data = {
                    'labels' : np.unique(np.array(df.loc[:,field['name']])),
                    'datasets' : []
                }
        add = []
        curr = []
        if value == None:
            
            colors=[]
            if report_type in ["bubble","scatter"]:
                colors.extend([random.choice(self.color_choices) for _ in range(len(np.unique(np.array(df.loc[:,field['name']]))))])  
            elif report_type == "radar":
                border_color_chosen = random.choice(self.color_choices)
                background_color = '{}66'.format(border_color_chosen)
            else:
                colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])
            if group_by == None:
                op_dict = collections.defaultdict(int)
                op_dict.update(df.groupby([field['name']])[field['name']].count().to_dict())
                new_add = []
                if report_type == "scatter" or field['type'] in ["DateField","DateTimeField"]:
                    for d in np.unique(np.array(df.loc[:,field['name']])):
                        new_add.append({
                            'x' : d,
                            'y' : op_dict[d]})
                elif report_type == "bubble":
                    background_colors = ['{}66'.format(x) for x in colors]
                    for d in np.unique(np.array(df.loc[:,field['name']])):
                        new_add.append({
                            'x' : d,
                            'y' : op_dict[d],
                            'r' : random.randint(15,30)})
                else:
                    for d in data['labels']:
                        new_add.append(op_dict[d])

                if report_type in ["horizontalBar","bar","pie","doughnut","scatter","polarArea"]:
                    data['datasets'].append({ 'label' : field['name'], 'backgroundColor' : colors, 'data' : new_add })
                elif report_type in ["line"]:
                    data['datasets'].append({ 'label' : field['name'], 'fill' : False,'borderColor' : random.choice(self.color_choices), 'data' : new_add })
                elif report_type == "bubble":
                    data['datasets'].append({ 'label' : field['name'], 'borderColor' : colors,'hoverBackgroundColor' : background_colors,'backgroundColor' : background_colors, 'data' : new_add })
                elif report_type == "radar":
                    data['datasets'].append({ 'label' : field['name'], 'fill' : True,'borderColor' : border_color_chosen, 'backgroundColor' : background_color , 'data' : new_add })
                elif report_type == "bar_mix":
                    color_chosen = random.choice(self.color_choices)
                    data['datasets'].append({ 'type' : 'bar','label' : field['name'], 'backgroundColor' : color_chosen, 'data' : new_add })
                    data['datasets'].append({ 'type' : 'line','label' : field['name'], 'fill' : True,'backgroundColor' : '{}66'.format(color_chosen),'borderColor' : color_chosen , 'data' : new_add })  
                else:
                    pass  
            else:
                op_dict = collections.defaultdict(lambda: collections.defaultdict(int))
                df_required = df.groupby([group_by['name'], field['name']]).agg({
                    field['name'] : {
                        "count" : "count"
                    }
                })
                df_required.columns = df_required.columns.droplevel(0)
                df_group_count = df_required.reset_index()
                for x in df_group_count.groupby([group_by['name']]).groups.keys():
                    
                    curr = np.array(df_group_count[[field['name'],'count',group_by['name']]])
                    for c in curr:
                        op_dict[c[2]][c[0]] = c[1]
                for group in op_dict.keys():        
    
                    if report_type == "bubble":
                        border_color_chosen = random.choice(colors)
                        color_chosen = '{}66'.format(border_color_chosen)
                        r_chosen = random.choice(r)
                    elif report_type == "radar":
                        color_chosen = random.choice(colors)    
                        background_color = '{}66'.format(color_chosen)
                    else:
                        color_chosen = random.choice(colors)

                    new_add = []
                    if report_type == "scatter" or field['type'] in ["DateField", "DateTimeField"]:
                        for x in data['labels']:
                            new_add.append({
                                'x' : x,
                                'y' : op_dict[group][x]})
                    elif report_type == "bubble":
                        for x in np.unique(np.array(df.loc[:,field['name']])):
                            new_add.append({
                                'x' : x,
                                'y' : op_dict[group][x],
                                'r' : r_chosen })
                    else:
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                    print(new_add)
                    if report_type in ["horizontalBar","bar","pie","doughnut","scatter","polarArea"]:
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                    elif report_type in ["line"]:
                        data['datasets'].append({ 'label' : group, 'fill' : False,'borderColor' : color_chosen, 'data' : new_add })
                    elif report_type == "bubble":
                        data['datasets'].append({ 'label' : group, 'borderColor' : border_color_chosen,'hoverBackgroundColor' : color_chosen,'backgroundColor' : color_chosen, 'data' : new_add })
                    elif report_type == "radar":
                        data['datasets'].append({ 'label' : group, 'fill' : True,'backgroundColor' : background_color,'borderColor' : color_chosen, 'data' : new_add })
                    elif report_type == "bar_mix":
                        data['datasets'].append({ 'type' : 'bar','label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                        data['datasets'].append({ 'type': 'line','label' : group, 'fill' : True,'backgroundColor' : '{}66'.format(color_chosen),'borderColor' : color_chosen, 'data' : new_add })
                    else:
                        pass

                    if len(colors) > 1:
                        colors.remove(color_chosen)    
        else:
            if group_by == None:
                op_dict = collections.defaultdict(int)
                colors=[]
                if report_type in ["bubble","scatter"]:
                    colors.extend([random.choice(self.color_choices) for _ in range(len(np.unique(np.array(df_required.loc[:,field['name']]))))])  
                elif report_type == "radar":
                    border_color_chosen = random.choice(self.color_choices)
                    background_color = '{}66'.format(border_color_chosen)
                else:
                    colors.extend([random.choice(self.color_choices) for _ in range(len(data['labels']))])  
                if value['aggregate']['value'] == 'none':
                    curr = []
                    curr.extend(df.loc[:,[field['name'],value['name']]].values)

                    for c in curr:
                        op_dict[c[0]] = c[1]
            
                if value['aggregate']['value'] == 'sum':
                    curr = []
                    curr.extend(df.groupby([field['name']])[value['name']].sum().reset_index().values)
                    
                    for c in curr:
                        op_dict[c[0]] = c[1]
                        
                    data['datasets'].append({ 'label' : Y_field['name'], 'backgroundColor' : colors, 'data' : new_add })

                if value['aggregate']['value'] == "count":
                    curr = []
                    curr.extend(df.groupby([field['name']])[value['name']].count().reset_index().values)
                    for c in curr:
                        op_dict['{}'.format(c[0])] = c[1]

                if value['aggregate']['value'] == "count distinct":
                    curr = []
                    curr.extend(df.groupby([field['name']])[value['name']].nunique().reset_index().values)
                    for c in curr:
                        op_dict['{}'.format(c[0])] = c[1]

                if value['aggregate']['value'] == "max":
                    curr = []
                    curr.extend(df.groupby([field['name']])[value['name']].max().reset_index().values)
                    for c in curr:
                        op_dict[c[0]] = c[1]

                if value['aggregate']['value'] == "min":
                    curr = []
                    curr.extend(df.groupby([field['name']])[value['name']].min().reset_index().values)
                    for c in curr:
                        op_dict[c[0]] = c[1]

                if value['aggregate']['value'] == "average":
                    curr = []
                    curr.extend(df.groupby([field['name']])[value['name']].mean().reset_index().values)
                    for c in curr:
                        op_dict[c[0]] = c[1]
                      
                new_add = []
                if report_type == "scatter" or field['type'] in ["DateTimeField","DateField"]:
                    for d in np.unique(np.array(df.loc[:,field['name']])):
                        new_add.append({
                            'x' : d,
                            'y' : op_dict[d]})
                elif report_type == "bubble":
                    background_colors = ['{}66'.format(x) for x in colors]
                    for d in np.unique(np.array(df.loc[:,field['name']])):
                        new_add.append({
                            'x' : d,
                            'y' : op_dict[d],
                            'r' : random.randint(15,30)})
                else:
                    for d in data['labels']:
                        new_add.append(op_dict[d])

                if report_type in ["horizontalBar","bar","pie","doughnut","scatter","polarArea"]:
                    data['datasets'].append({ 'label' : value['name'], 'backgroundColor' : colors, 'data' : new_add })
                elif report_type in ["line"]:
                    data['datasets'].append({ 'label' : value['name'], 'fill' : False,'borderColor' : random.choice(self.color_choices), 'data' : new_add })
                elif report_type == "bubble":
                    data['datasets'].append({ 'label' : value['name'], 'borderColor' : colors,'hoverBackgroundColor' : background_colors,'backgroundColor' : background_colors, 'data' : new_add })
                elif report_type == "radar":
                    data['datasets'].append({ 'label' : value['name'], 'fill' : True,'borderColor' : border_color_chosen, 'backgroundColor' : background_color , 'data' : new_add })
                elif report_type == "bar_mix":
                    color_chosen = random.choice(self.color_choices)
                    data['datasets'].append({ 'type' : 'bar','label' : value['name'], 'backgroundColor' : color_chosen, 'data' : new_add })
                    data['datasets'].append({ 'type' : 'line','label' : value['name'], 'fill' : True,'backgroundColor' : '{}66'.format(color_chosen),'borderColor' : color_chosen , 'data' : new_add })  
                else:
                    pass          
                
            else:
                op_dict = collections.defaultdict(lambda: collections.defaultdict(int))
                colors=[]
                colors.extend([random.choice(self.color_choices) for _ in range(len(df.groupby([group_by['name']]).groups.keys()))])
                if report_type == "bubble":
                    r = []
                    r.extend([random.randint(15,30) for _ in range(len(df.groupby([group_by['name']]).groups.keys()))])
                if value['aggregate']['value'] == 'none':
                    for x in df.groupby([group_by['name']]).groups.keys():
                        
                        df_group = df.groupby([group_by['name']]).get_group(x)
                        
                        curr = np.array(df_group[[field['name'],value['name'],group_by['name']]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                if value['aggregate']['value'] == 'sum':
                    df_group_sum = df.groupby([group_by['name'], field['name']],as_index=False)[value['name']].sum()
                    for x in df_group_sum.groupby([group_by['name']]).groups.keys():
                        
                        curr = np.array(df_group_sum[[field['name'],value['name'],group_by['name']]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                    
                
                    for group in op_dict.keys():        
                        color_chosen = random.choice(colors)    
                        new_add = []
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                        if len(colors) > 1:
                            colors.remove(color_chosen)
                
                if value['aggregate']['value'] == "count":
                    df_group_sum = df.groupby([group_by['name'], field['name']],as_index=False)[value['name']].count()
                    for x in df_group_sum.groupby([group_by['name']]).groups.keys():
                        
                        curr = np.array(df_group_sum[[field['name'],value['name'],group_by['name']]])
                        for c in curr:
                            op_dict['{}'.format(c[2])]['{}'.format(c[0])] = c[1]

                if value['aggregate']['value'] == "count distinct":
                    df_group_sum = df.groupby([group_by['name'], field['name']],as_index=False).agg({ value['name'] : pd.Series.nunique})
                    for x in df_group_sum.groupby([group_by['name']]).groups.keys():
                        curr = np.array(df_group_sum[[field['name'],value['name'],group_by['name']]])
                        for c in curr:
                            op_dict['{}'.format(c[2])]['{}'.format(c[0])] = c[1]

                if value['aggregate']['value'] == "max":
                    df_group_sum = df.groupby([group_by['name'], field['name']],as_index=False)[value['name']].max()
                    for x in df_group_sum.groupby([group_by['name']]).groups.keys():
                        
                        curr = np.array(df_group_sum[[field['name'],value['name'],group_by['name']]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]

                if value['aggregate']['value'] == "min":
                    df_group_sum = df.groupby([group_by['name'], field['name']],as_index=False)[value['name']].min()
                    for x in df_group_sum.groupby([group_by['name']]).groups.keys():    
                        curr = np.array(df_group_sum[[field['name'],value['name'],group_by['name']]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]

                if value['aggregate']['value'] == "average":
                    df_group_sum = df.groupby([group_by['name'], field['name']],as_index=False)[value['name']].mean()
                    for x in df_group_sum.groupby([group_by['name']]).groups.keys():
                        curr = np.array(df_group_sum[[field['name'],value['name'],group_by['name']]])
                        for c in curr:
                            op_dict[c[2]][c[0]] = c[1]
                for group in op_dict.keys():        
    
                    if report_type == "bubble":
                        border_color_chosen = random.choice(colors)
                        color_chosen = '{}66'.format(border_color_chosen)
                        r_chosen = random.choice(r)
                    elif report_type == "radar":
                        color_chosen = random.choice(colors)    
                        background_color = '{}66'.format(color_chosen)
                    else:
                        color_chosen = random.choice(colors)

                    new_add = []
                    if report_type == "scatter" or field['type'] in ["DateTimeField","DateField"]:
                        for x in np.unique(np.array(df.loc[:,field['name']])):
                            new_add.append({
                                'x' : x,
                                'y' : op_dict[group][x]})
                    elif report_type == "bubble":
                        for x in np.unique(np.array(df.loc[:,field['name']])):
                            new_add.append({
                                'x' : x,
                                'y' : op_dict[group][x],
                                'r' : r_chosen })
                    else:
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                    if report_type in ["horizontalBar","bar","pie","doughnut","scatter","polarArea"]:
                        data['datasets'].append({ 'label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                    elif report_type in ["line"]:
                        data['datasets'].append({ 'label' : group, 'fill' : False,'borderColor' : color_chosen, 'data' : new_add })
                    elif report_type == "bubble":
                        data['datasets'].append({ 'label' : group, 'borderColor' : border_color_chosen,'hoverBackgroundColor' : color_chosen,'backgroundColor' : color_chosen, 'data' : new_add })
                    elif report_type == "radar":
                        data['datasets'].append({ 'label' : group, 'fill' : True,'backgroundColor' : background_color,'borderColor' : color_chosen, 'data' : new_add })
                    elif report_type == "bar_mix":
                        data['datasets'].append({ 'type' : 'bar','label' : group, 'backgroundColor' : color_chosen, 'data' : new_add })
                        data['datasets'].append({ 'type': 'line','label' : group, 'fill' : True,'backgroundColor' : '{}66'.format(color_chosen),'borderColor' : color_chosen, 'data' : new_add })
                    else:
                        pass

                    if len(colors) > 1:
                        colors.remove(color_chosen)
        return Response({ 'data' : data }, status = status.HTTP_200_OK)

    def report_generate(self,request):

        report_type = request.data['type']
        
        df, model_fields= self.dataFrameGenerate(request, request.user)
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
        
        field = request.data['options']['X_field']
        value = request.data['options']['Y_field']
        group_by = request.data['options']['group_by']

        try:
            return self.graphDataGenerate(df,report_type, field, value, group_by)
        except Exception as e:
            print(e)
            return Response('error',status = status.HTTP_400_BAD_REQUEST)

class ReportList(viewsets.ViewSet):

    permission_classes = (permissions.IsAuthenticated&GridBackendReportPermissions,)
    authentication_classes = (GridBackendAuthentication,)
    
    def get(self,request):
        if request.user.is_superuser:
            reports = Report.objects.filter(organization_id=request.user.organization_id)
        elif request.user.role == 'Developer':
            reports = Report.objects.filter(organization_id=request.user.organization_id).filter(user = request.user.username) | Report.objects.filter(organization_id = request.user.organization_id).filter(shared__user_id__contains = request.user.username)
        else:
            reports =Report.objects.filter(organization_id = request.user.organization_id).filter(shared__user_id__contains = request.user.username)
        serializer = ReportSerializer(reports, many=True)
        print(reports)
        return Response(serializer.data, status = status.HTTP_200_OK)
    
    def get_object(self,dataset_id,user):
        try:
            return Dataset.objects.filter(user = user.username).get(dataset_id = dataset_id)
        except:
            return Http404

    
    def get_report_object(self,request,report_id,user):
        try:
            obj = Report.objects.filter(organization_id=user.organization_id).get(report_id = report_id)
            if self.check_object_permissions(self, request, obj):
                return obj
            else:
                return Response('Unauthorized', status = status.HTTP_401_UNAUTHORIZED)
        except Report.DoesNotExist:
            raise Http404
    
    def report_list(self,request):
        if request.is_superuser:
            reports = Report.objects.filter(organization_id=request.user.organization_id).all()
        if request.user.role == 'Developer':
            reports = Report.objects.filter(organization_id=request.user.organization_id).filter(user=request.user.username)
        else:
            return Response(status = status.HTTP_204_NO_CONTENT)
        serializer = ReportSerializer(reports, many = True)
        return Response(serializer.data, status = status.HTTP_200_OK)

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
    
    def edit(self,request):

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
    
    def add_filter(self,request):
        data = request.data
        data['organization_id'] = request.user.organization_id
        data['user'] = request.user.username
        try:
            report = self.get_report_object(request,data['report_id'], request.user)
        except:
            return Response('Unauthorized', status=status.HTTP_401_UNAUTHORIZED)
        serializer = FilterSerializer(data = data)

        if serializer.is_valid():
            serializer.save(report = report)
            return Response(serializer.data,status = status.HTTP_201_CREATED)
        
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

class DashboardList(viewsets.ViewSet): 

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
    
    def get_report_objects(self, organization_id, reports):
        try:
            report_id_list = [x['id'] for x in reports]
            return Report.objects.filter(organization_id=organization_id).filter(user = user.username).filter(report_id__in = report_id_list)
        except Report.DoesNotExist:
            raise Http404

    def get_object(self, request, dashboard_id, user):
        try:
            obj = Dashboard.objects.filter(organization_id = user.organization_id),get(dashboard_id = dashboard_id)
            if self.check_object_permissions(self, request, obj):
                return obj
    
        except Dashboard.DoesNotExist:
            raise Http404

    def get_dashboard_report_options_objects(self, dashboard, user):
        try:
            return DashboardReportOptions.objects.filter(organization_id = user.organization_id).filter(dashboard = dashboard)
        except DashboardReportOptions.DoesNotExist:
            raise Http404

    def get_dashboard_report_options_object(self,dashboard_id, report_id):
        try:
            return DashboardReportOptions.objects.filter(dashboard = dashboard_id).get(report_id = report_id)
        except DashboardreportOptions.DoesNotExist:
            raise Http404

    def dashboard_list(self,request):
        if request.is_superuser:
            dashboards = Dashboard.objects.filter(organization_id=request.user.organization_id).all()
        if request.user.role == 'Developer':
            dashboards = Dashboard.objects.filter(organization_id=request.user.organization_id).filter(user=request.user.username)
        else:
            return Response(status = status.HTTP_204_NO_CONTENT)
        serializer = DashboardSerializer(dashboards, many = True)
        return Response(serializer.data, status = status.HTTP_200_OK)

    def post(self, request):
        data = request.data
        data['organization_id'] = request.user.organization_id
        data['user'] = request.user.username
        reports = self.get_report_objects(request.user.organization_id, data['reports'])
        serializer = DashboardSerializer(data=data)
        if serializer.is_valid:
            serializer.save(reports = reports)
            for x in reports:
                dashboard_report_serilaizer = DashboardReportOptionsSerializer(data = data)
                if dashboard_report_serilaizer.is_valid():
                    dashboard_report_serilaizer.save(report = x)
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
            for x in self.get_dashboard_report_options_objects(dashboard, request.user):
                dashboard_report_serilaizer = DashboardReportOptionsSerializer(x, data = data['reports'])
                if dashboard_report_serilaizer.is_valid():
                    dashboard_report_serializer.save()
            return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def dashboard_filter(self, request):
        data = request.data
        data['organization_id'] = request.user.organization_id
        data['user'] = request.user.username
        try:
            dashboard = self.get_object(request, data['dashboard_id'], request.user)
        except:
            return Response('Unauthorized', status=status.HTTP_401_UNAUTHORIZED)
        
        for x in data['report_ids']:
            dashboard_report = self.get_dashboard_report_options_object(data['dashboard_id'], x)
            serializer = FilterSerializer(data = data)

            if serializer.is_valid():
                serializer.save(dashboard_report = dashboard_report)
            else:
                return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)
        return Response(serializer.data,status = status.HTTP_201_CREATED)

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

    permission_classes=(permissions.IsAuthenticated&GridBackendShareReportPermissions,)
    authentication_classes=(GridBackendAuthentication,)

    def get_report_object(self,request,report_id,user):
        try:
            obj = Report.objects.filter(organization_id=user.organization_id)
            if self.check_object_permissions(self, request, obj):
                return obj.filter(user=user.username).get(report_id=report_id)
            else:
                return Response('Unauthorized', status = status.HTTP_401_UNAUTHORIZED)
        except Report.DoesNotExist:
            return Response('Unauthorized', status = status.HTTP_401_UNAUTHORIZED)
    
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
            data['view'] = True
            if x['edit']:
                data['edit'] = True
            if x['delete']:
                data['delete'] = True
            serializer = SharedReportSerializer(data=data)
            if serializer.is_valid():
                serializer.save(report = report, shared_user_id=request.user.username, user_id = x)
            else:
                return Response('error', status=status.HTTP_400_BAD_REQUEST)
            data['edit'] = False
            data['delete'] = False
        return Response('success', status = status.HTTP_201_CREATED)

class SharedDashboards(viewsets.ViewSet):

    permission_classes = (permissions.IsAuthenticated&GridBackendShareDashboardPermissions,)
    authentication_classes = (GridBackendAuthentication,)
    
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


    def get_report_object(self,request,report_id,user):
        try:
            return Report.objects.filter(organization_id=user.organization_id).filter(user=user.username).get(report_id=report_id)
        except Report.DoesNotExist:
            raise Http404
    def get_object(self, request, dashboard_id, user):
        try:
            obj = Dashboard.objects.filter(organization_id = user.organization_id)
            if self.check_object_permissions(self, request, obj):
                return obj.filter(user = user.username).get(dashboard_id = dashboard_id)
            else:
                return Response('Unauthorized', status = status.HTTP_401_UNAUTHORIZED)
        except Dashboard.DoesNotExist:
            raise Http404
    
    def dashboard_share(self, request):
        
        data = request.data
        dashbaord = self.get_object(request,data['dashboard_id'], request.user)
        
        for c in data['user_id_list']:
            data['view'] = True
            if c['edit']:
                data['edit'] = True
            if c['delete']:
                data['delete'] = True
            share_serializer = SharedDashboardSerializer(data = data)
            if share_serializer.is_valid():
                share_serializer.save(dashbaord = dashbaord,shared_user_id = request.user.username, user_id = c['id'])
                if share_serializer.data['edit'] or share_serializer.data['delete']: 

                    for x in dashbaord.report_set.all():
                        report = self.get_report_object(request.user.organization_id, x.report_id, request.user)
                        serializer = SharedReportSerializer(data=data)
                        if serializer.is_valid():
                            serializer.save(report = report, shared_user_id=request.user.username, user_id = c['id'])
                        else:
                            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            data['edit'] = False
            data['delete'] = False
        return Response('success', status = status.HTTP_201_CREATED)
        return Response(share_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class FilterList(viewsets.ViewSet):

    authentication_classes = (GridBackendAuthentication, )
    permission_classes = (permissions.IsAuthenticated,)
    
    
    def get_object(self,filter_id, user):
        try:
            return Filter.objects.filter(organization_id = user.organization_id).filter(user = user.username).get(filter_id = filter_id)
        except Filter.DoesNotExist:
            raise Http404

    def get_for_reports(self,request):
        filters = Filter.objects.filter(organization_id = request.user.organization_id).filter(user = request.user.username).filter(reports__report_id = request.data['report_id'])
        serializer  = FilterSerializer(filters, many = True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_for_dashboard(self,request):
        filters = Filter.objects.filter(organization_id = request.user.organization_id).filter(user = request.user.username).filter(dashboard_reports__dashboard__dashboard_id = request.data['dashboard'])
        serializer = FilterSerializer(filters, many = True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
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