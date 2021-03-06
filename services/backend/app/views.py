from django.shortcuts import render

from app.models import (Dataset,Field,Setting,
                                Table,Join,Report, Dashboard, 
                                SharedDashboard, SharedReport,
                                Filter,DashboardReportOptions)
from app.serializers import (DatasetSerializer,
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
                                SharedDashboardSerializer,
                                PeriodicTaskSerializer,
                                DatasetUpdateSerializer,
                                ReportUpdateSerializer,
                                FilterUpdateSerializer,
                                DashboardUpdateSerializer)
from app.utils import get_model,dictfetchall, getColumnList
from app.tasks import datasetRefresh, load_data
from app.Authentication import (GridBackendAuthentication,  
                                GridBackendDatasetPermissions, 
                                GridBackendReportPermissions, 
                                GridBackendDashboardPermissions,
                                GridBackendShareReportPermissions,
                                GridBackendShareDashboardPermissions)
from app.filters import DatasetFilterBackend, ReportFilterBackend,DashboardFilterBackend

from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import Http404
from rest_framework import permissions,exceptions,viewsets,status
from rest_framework.decorators import action

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
import arrow
import datetime
import boto3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Create your views here.

# @job

class DatasetViewSet(viewsets.GenericViewSet):

    permission_classes = (permissions.IsAuthenticated&GridBackendDatasetPermissions,)
    authentication_classes = (GridBackendAuthentication,)
    filter_backends = (DatasetFilterBackend,)

    queryset = Dataset.objects.all()
    # lookup_field = 'dataset_id'
    serializer_class = DatasetSerializer

    field_type = {
        0: 'DECIMAL',
        1: 'TINY',
        2: 'SHORT',
        3: 'LONG',
        4: 'FLOAT',
        5: 'DOUBLE',
        6: 'NULL',
        7: 'TIMESTAMP',
        8: 'LONGLONG',
        9: 'INT24',
        10: 'DATE',
        11: 'TIME',
        12: 'DATETIME',
        13: 'YEAR',
        14: 'NEWDATE',
        15: 'VARCHAR',
        16: 'BIT',
        246: 'NEWDECIMAL',
        247: 'INTERVAL',
        248: 'SET',
        249: 'TINY_BLOB',
        250: 'MEDIUM_BLOB',
        251: 'LONG_BLOB',
        252: 'BLOB',
        253: 'VAR_STRING',
        254: 'STRING',
        255: 'GEOMETRY' }

    def convert(self,col):
        if col in [15,249,250,251,252,253,254]: 
            return 'CharField'
        elif col in [10,13,14] : 
            return 'DateField'
        elif col in [7,11,12] : 
            return 'DateTimeField'    
        elif col in [0,4,5,246]: 
            return 'FloatField'
        elif col in [249,250,251]: 
            return 'TextField'
        elif col in [1,2,3,8, 9,16]: 
            return 'IntegerField'
        else:
            return 'CharField'

    def list(self,request):
        
        datasets = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(datasets, many = True)
        for x in serializer.data:
            if x['mode'] == 'SQL':
                with connections['rds'].cursor() as cursor:
                    cursor.execute('select database_name from organizations where organization_id="{}";'.format(request.user.organization_id))
                    database_name = cursor.fetchone()[0]
                if request.user.organization_id not in connections.databases:
                    connections.databases[request.user.organization_id] = {
                        'ENGINE' : 'django.db.backends.mysql',
                        'NAME' : database_name,
                        'OPTIONS' : {
                            'read_default_file' : os.path.join(BASE_DIR, 'cred_dynamic.cnf'),
                        }
                    }
                with connections[request.user.organization_id].cursor() as cur:
                    cur.execute(x['sql'])
                    x['fields'] = [{'name' : col[0], 'type' : self.convert(col[1]) } for col in cur.description]
            if x['scheduler'] != None:
                periodic_task = PeriodicTask.objects.get(id = x['scheduler'])
                periodic_task_serializer = PeriodicTaskSerializer(periodic_task)
                x['scheduler'] = periodic_task_serializer.data
        return Response(serializer.data,status = status.HTTP_200_OK)

    def create(self,request):
        data = request.data
        data['organization_id'] = request.user.organization_id
        data['user'] = request.user.user_alias
        data['userId'] = request.user.username
        if request.data['mode'] == 'VIZ':
            # -- Role Authorization -- #
            
            serializer = self.get_serializer(data = data)
            if serializer.is_valid():
                serializer.save()
                dataset = Dataset.objects.get(dataset_id = serializer.data['dataset_id'])
                for f in data['fields']:
                    field_serializer = FieldSerializer(data = f)
                    if field_serializer.is_valid():
                        field_serializer.save(dataset = dataset)
                    else:
                        return Response(field_serializer.errors, status = status.HTTP_400_BAD_REQUEST)
                    for s in f['settings']:
                        field = Field.objects.filter(dataset__dataset_id = serializer.data['dataset_id']).filter(worksheet = f['worksheet']).get(name = f['name'])
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
                
            data['mode'] = 'SQL'
            data['user'] = request.user.username
            serializer = self.get_serializer(data = data)
            if serializer.is_valid():
                serializer.save()
            return Response({'message' : 'success'},status=status.HTTP_201_CREATED)

        return Response(serializer.errors,status = status.HTTP_400_BAD_REQUEST)

    def update(self, request,pk=None):
        data = request.data
        dataset = self.get_object()
        print("id",dataset.dataset_id)
        user = request.user
        data['organization_id'] = request.user.organization_id
        data['user'] = request.user.username
        data['userId'] = request.user.username
        required_fields = ['organization_id','user','userId','name','dataset_id','sql','mode','model','scheduler','last_refreshed_at']
        dataupdate = {key:value for key,value in data.items() if key in required_fields}
        serializer = DatasetUpdateSerializer(dataset, data = dataupdate)
        # if serializer.is_valid():
        #     serializer.save()
        #     print(serializer.data)
        #     return Response(serializer.data, status = status.HTTP_202_ACCEPTED) 
        if dataset.mode == 'VIZ':
            if serializer.is_valid():
                serializer.save()
                worksheets = [f['worksheet'] for f in data['fields']]
                Field.objects.filter(dataset__dataset_id = dataset.dataset_id).filter(~Q(name__in = [f['name'] for f in data['fields']]) & ~Q(worksheet__in = worksheets)).delete()
                for f in data['fields']:
                    if not Field.objects.filter(dataset__dataset_id = dataset.dataset_id).filter(worksheet = f['worksheet']).filter(name = f['name']).exists():
                        field_serializer = FieldSerializer(data = f)
                        if field_serializer.is_valid():
                            field_serializer.save(dataset = dataset)
                        else:
                            return Response(field_serializer.errors, status = status.HTTP_400_BAD_REQUEST)
                    field = Field.objects.filter(dataset__dataset_id = dataset.dataset_id).filter(worksheet = f['worksheet']).get(name = f['name'])
                    for s in f['settings']:
                        if not Field.objects.filter(dataset__dataset_id  = dataset.dataset_id).filter(settings__name = s['name']).exists():
                            settings_serializer = SettingSerializer(data = s)
                            if settings_serializer.is_valid():
                                settings_serializer.save(field = field)
                            else:
                                return Response(settings_serializer.errors, status = status.HTTP_400_BAD_REQUEST)
                Table.objects.filter(dataset__dataset_id = dataset.dataset_id).filter(~Q(name__in = [t['key'] for t in data['tables']])).delete()
                for t in data['tables']:
                    if not Table.objects.filter(dataset__dataset_id = dataset.dataset_id).filter(name = t['key']).exists():
                        table_serializer = TableSerializer(data = t)
                        if table_serializer.is_valid():
                            table_serializer.save(dataset = dataset)
                        else:
                            return Response(table_serializer.errors, status = status.HTTP_400_BAD_REQUEST)
                fields_1 = [t['field_1'] for t in data['joins']]
                fields_2 = [t['field_2'] for t in data['joins']]
                worksheet_1 = [t['worksheet_1'] for t in data['joins']]
                worksheet_2 = [t['worksheet_2'] for t in data['joins']]
                Join.objects.filter(dataset__dataset_id = dataset.dataset_id).filter(~Q(type__in = data['joins']) | ~Q(field_1__in = fields_1) | ~Q(field_2__in = fields_2) | ~Q(worksheet_1__in = worksheet_1) | ~Q(worksheet_2__in = worksheet_2 )).delete()
                for t in data['joins']:
                    if not Join.objects.filter(dataset__dataset_id = dataset.dataset_id).filter(Q(type = t['type']) & Q(field_1 = t['field_1']) & Q(field_2 = t['field_2']) & Q(worksheet_1 = t['worksheet_1']) & Q(worksheet_2 = t['worksheet_2'])).exists():
                        join_serializer = JoinSerializer(data = t)
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
    
    def retrieve(self,request,pk=None):
        dataset = self.get_object()
        dataset_id = dataset.dataset_id
        user = request.user
        r1 = redis.StrictRedis(host='127.0.0.1', port=6379, db=1)
        if r1.exists('{}.{}'.format(user.organization_id,dataset_id)) != 0:
            print("from redis")
            df = pickle.loads(zlib.decompress(r1.get("{}.{}".format(user.organization_id,dataset_id))))
            print("data",df)
            try:
                model_fields = [(k.decode('utf8').replace("'", '"'),v.decode('utf8').replace("'", '"')) for k,v in r1.hgetall('{}.fields'.format(dataset_id)).items()]
            except:
                pass
            count,_ = df.shape
        else:
            s3_resource= boto3.resource('s3')
            with connections['rds'].cursor() as cursor:
                cursor.execute('select database_name from organizations where organization_id="{}";'.format(request.user.organization_id))
                database_name = cursor.fetchone()
            model = dataset.get_django_model()
            print("Model",model)
            model_fields = [(f.name, f.get_internal_type()) for f in model._meta.get_fields() if f.name is not 'id']
            r = redis.Redis(host='127.0.0.1', port=6379, db=0)
            try:
                s3_resource.Object('pragyaam-dash-dev','{}/{}.rdb'.format(user.organization_id,str(dataset_id))).download_file(f'/tmp/{dataset_id}.rdb')
            except Exception as e:
                print(e,flush=True)
            try:
                load_data('/tmp/{}.rdb'.format(dataset_id),'127.0.0.1',6379,0) 
            except Exception as e:
                print(e,flush=True)
                return Response(status=status.HTTP_204_NO_CONTENT)
            data = []
            if dataset.mode == 'SQL':
                data = pickle.loads(zlib.decompress(r.get('data')))
            else:
                for x in range(int(request.GET['start']),int(request.GET['end'])+1):
                    if r.get('edit.{}.{}.{}'.format(user.organization_id, dataset_id, str(x))) != None:
                        data.append({k.decode('utf8').replace("'", '"'): v.decode('utf8').replace("'", '"') for k,v in r.hgetall('edit.{}.{}.{}'.format(user.organization_id, dataset_id, str(x))).items()})
                    else:
                        data.append({k.decode('utf8').replace("'", '"'): v.decode('utf8').replace("'", '"') for k,v in r.hgetall('{}.{}.{}'.format(user.organization_id, dataset_id, str(x))).items()})
                    
            print("dictdata",data)
            count = r.dbsize()
            r.flushdb()  
            os.remove('/tmp/{}.rdb'.format(dataset_id))
            del(model)  
            df = pd.DataFrame(data)
            # if join columns in not having equal data the join returns null so here it is catched and sent as 204_NO_CONTENT
            if df.empty:
                return Response({"error":"empty datafarame"},status=status.HTTP_204_NO_CONTENT)
            r1.setex("{}.{}".format(user.organization_id,dataset_id), 600, zlib.compress( pickle.dumps(df)))
            if dataset.mode != 'SQL':
                r1.hmset('{}.fields'.format(dataset_id), { x[0] : x[1] for x in model_fields })
        for x in model_fields:
            if x[0] not in df.columns:
        
                if x[1] == 'FloatField':
                    df[x[0]] = 0
                if x[1] == 'IntegerField':
                    df[x[0]] = 0
                if x[1] == 'CharField' or x[1] == 'TextField':
                    df[x[0]] = ''
                if x[1] == 'DateField' or x[1] == 'DateTimeField':
                    df[x[0]] = arrow.get('01-01-1990').datetime
            else:
                if x[1] == 'FloatField':
                    df[x[0]] = df[x[0]].apply(pd.to_numeric,errors='coerce')
                    df.fillna(0,downcast='infer')
                if x[1] == 'IntegerField':
                    df[x[0]] = df[x[0]].apply(pd.to_numeric,errors='coerce')
                    df.fillna(0,downcast='infer')
                if x[1] == 'CharField' or x[1] == 'TextField':
                    df = df.astype({ x[0] : 'object'})
                    df.fillna('')
                if x[1] == 'DateField':
                    df = df.astype({ x[0] : 'datetime64'})
                    df.fillna(arrow.get('01-01-1990').datetime)
        if dataset.mode == 'SQL':
            count = df.size
            df = df[int(request.GET['start']):int(request.GET['end'])+1]
        print("size",df)
        
        return Response({'data' : df.fillna('').to_dict(orient='records'), 'length': count},status=status.HTTP_200_OK)
        # return Response({'data' : df.dropna().to_json(), 'length': count},status=status.HTTP_200_OK)
        

    @action(methods=['POST'],detail=True)
    def add_data(self,request,pk=None):
        data = request.data
        dataset = self.get_object()
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

    @action(methods=["PUT"],detail=True)
    def add_refresh(self,request,pk=None):
        dataset = self.get_object()
        user = request.user
        data = request.data

        schedule,_ = CrontabSchedule.objects.get_or_create(
            minute=data['minute'],
            hour=data['hour'],
            day_of_week=data['day_of_week'],
            day_of_month=data['day_of_month'],
            month_of_year=data['month_of_year']
        )
        periodic_task = PeriodicTask.objects.create(
            crontab=schedule,
            name='{}.{}'.format(user.organization_id, dataset.dataset_id),
            task='app.tasks.datasetRefresh',
            args=json.dumps([user.organization_id, str(dataset.dataset_id)])
        )

        serializer = DatasetSerializer(dataset,data = data)
        if serializer.is_valid():
            serializer.save(scheduler = periodic_task)
            return Response(serializer.data, status = status.HTTP_202_ACCEPTED)
        
        return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)        

    @action(methods=["PUT"],detail=True)
    def edit_refresh(self,request,pk=None):
        dataset = self.get_object()
        data = request.data
        scheduler = PeriodicTask.objects.get(name = dataset.scheduler.name)
        schedule,_ = CrontabSchedule.objects.get_or_create(
            minute=data['minute'],
            hour=data['hour'],
            day_of_week=data['day_of_week'],
            day_of_month=data['day_of_month'],
            month_of_year=data['month_of_year']
        )
        scheduler.crontab = schedule
        scheduler.save()

        serializer = self.get_serializer(dataset,data = data)
        if serializer.is_valid():
            serializer.save(scheduler = scheduler)
            return Response(serializer.data, status = status.HTTP_202_ACCEPTED)
        
        return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)

    @action(methods=["DELETE"],detail=True)
    def delete_refresh(self,request,pk=None):
        dataset = self.get_object(id,request.user)
        scheduler = PeriodicTask.objects.get(name = dataset.scheduler.name)
        scheduler.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
        
    def destroy(self,request,pk=None):

        dataset = self.get_object()
        dataset.delete()
        s3_resource= boto3.resource('s3')
        dataset_s3= s3_resource.Object('pragyaam-dash-dev','{}/{}.rdb'.format(request.user.organization_id,str(pk)))
        val = dataset_s3.delete()
        return Response({'messge':'success'},status=status.HTTP_204_NO_CONTENT)

class ReportViewSet(viewsets.GenericViewSet):

    permission_classes = (permissions.IsAuthenticated&GridBackendReportPermissions,)
    authentication_classes = (GridBackendAuthentication,)
    filter_backends = (ReportFilterBackend,)

    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    
    def list(self,request):
        
        reports = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(reports, many=True)
        return Response(serializer.data, status = status.HTTP_200_OK)
    
    def get_dataset_object(self,dataset_id,user):
        try:
            return Dataset.objects.filter(userId = user.username).get(dataset_id = dataset_id)
        except Dataset.DoesNotExist:
            return Http404

    def create(self, request):
        data = request.data
        data['organization_id'] = request.user.organization_id
        data['user'] = request.user.user_alias
        data['userId'] = request.user.username
        if data['op_table'] == 'dataset':
            dataset = self.get_dataset_object(data['dataset_id'],request.user)
        serializer = self.get_serializer(data = data)

        if serializer.is_valid():
            if data['op_table'] == 'dataset':
                serializer.save(dataset = dataset)
            else:
                serializer.save()
            for x in data['filters']:
                x['user'] = request.user.user_alias
                x['organization_id'] = request.user.organization_id
                report = Report.objects.get(report_id=serializer.data['report_id'])
                filter_serializer = FilterSerializer(data = x)
                if filter_serializer.is_valid():
                    filter_serializer.save(report = report)
                else:
                    return Response(filter_serializer.errors, status = status.HTTP_400_BAD_REQUEST)
            return Response(serializer.data,status = status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)
    
    def update(self,request,pk=None):
        print("dataaa",request.data)
        data = request.data
        data['organization_id'] = request.user.organization_id
        data['user'] = request.user.user_alias
        data['userId'] = request.user.username
        print("data",data)
        report = self.get_object()
        required_fields = ['organization_id','dataset','worksheet','user','userId','report_id','data','last_updated_at']
        dataupdate = {key:value for key,value in data.items() if key in required_fields}
        serializer = ReportUpdateSerializer(report, data = dataupdate)
       
        # serializer = ReportSerializer(report, data = data)

        if serializer.is_valid():
            serializer.save()
            for x in data['filters']:
                if 'filter_id' in x:
                    x['user'] = request.user.user_alias
                    x['organization_id'] = request.user.organization_id
                    if x['filter_id'] != None and Filter.objects.filter(organization_id=x['organization_id']).filter(filter_id = x['filter_id']).exists():
                        fil = Filter.objects.filter(organization_id=x['organization_id']).get(filter_id = x['filter_id'])
                        print("x",x)
                        filter_serializer = FilterUpdateSerializer(fil,data = x)
                        if filter_serializer.is_valid():
                            filter_serializer.save()
                        else:
                            return Response(filter_serializer.errors, status = status.HTTP_400_BAD_REQUEST)
                else:                    
                    x['user'] = request.user.user_alias
                    x['organization_id'] = request.user.organization_id
                    report = Report.objects.get(report_id=serializer.data['report_id'])
                    filter_serializer = FilterSerializer(data = x)
                    if filter_serializer.is_valid():
                        filter_serializer.save(report = report)
                    else:
                        return Response(filter_serializer.errors, status = status.HTTP_400_BAD_REQUEST)
                    return Response(serializer.data,status =  status.HTTP_202_ACCEPTED)
                    


            return Response(serializer.data, status = status.HTTP_202_ACCEPTED)
        
        return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)

    def destroy(self,request,pk=None):

        report = self.get_object()
        report.delete()
        return Response({'messge':'success'},status=status.HTTP_204_NO_CONTENT)

class DashboardViewSet(viewsets.GenericViewSet): 

    permission_classes = (permissions.IsAuthenticated&GridBackendDashboardPermissions,)
    authentication_classes = (GridBackendAuthentication,)
    filter_backends = (DashboardFilterBackend,)

    queryset = Dashboard.objects.all()
    serializer_class = DashboardSerializer

    def list(self,request):
        
        dashboards = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(dashboards,many = True)
        return Response(serializer.data, status = status.HTTP_200_OK)
    
    def get_report_objects(self, user, reports):
        try:
            report_id_list = [x['report_id'] for x in reports]
            return Report.objects.filter(organization_id=user.organization_id).filter(userId = user.username).filter(report_id__in = report_id_list)
        except Report.DoesNotExist:
            raise Http404
    
    def get_report_object(self,report_id,user):
        try:
            return Report.objects.filter(organization_id=user.organization_id).filter(userId = user.username).get(report_id = report_id)
        except Report.DoesNotExist:
            raise Http404

    # def get_dashboard_report_options_objects(self, dashboard, reports):
    #     try:
    #         report_id_list =[ x['report_id'] for x in reports]
    #         return DashboardReportOptions.objects.filter(dashboard = dashboard).filter(report__in = report_id_list)
    #     except DashboardReportOptions.DoesNotExist:
    #         raise Http404
    def update_report_list(self,reports,dashboard_id):
        try:
            reports_dashboard = DashboardReportOptions.objects.filter(dashboard = dashboard_id)
            report_ids_dashboard = [str(x.report_id) for x in reports_dashboard]
            reports_for_update = [x for x in reports if x['report_id'] not in report_ids_dashboard]
            return reports_for_update
        except DashboardReportOptions.DoesNotExist:
            raise Http404


    def get_dashboard_report_options_object(self,dashboard_id, report_id):
        try:
            return DashboardReportOptions.objects.filter(dashboard = dashboard_id).get(report = report_id)
        except DashboardReportOptions.DoesNotExist:
            raise Http404


    def create(self, request):
        data = request.data
        data['organization_id'] = request.user.organization_id
        data['user'] = request.user.user_alias
        data['userId'] = request.user.username
        reports = self.get_report_objects(request.user, data['reports'])
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            serializer.save(reports = reports)
            dashboard = Dashboard.objects.get(dashboard_id = serializer.data['dashboard_id'])
            for x in data['reports']:
                report = self.get_report_object(x['report_id'],request.user)
                dashboard_report_serializer = DashboardReportOptionsSerializer(data = x['dashReportOptions'])
                if dashboard_report_serializer.is_valid():
                    dashboard_report_serializer.save(report = report, dashboard = dashboard)
                else:
                    return Response(dashboard_report_serializer.errors,status=status.HTTP_400_BAD_REQUEST)
            for f in data['dashReportFilters']:
                f['user'] = request.user.user_alias
                f['organization_id'] = request.user.organization_id
                filter_serializer = FilterSerializer(data = f)
                if filter_serializer.is_valid():
                    filter_serializer.save(dashboard = dashboard)
                else:
                    return Response(filter_serializer.errors, status = status.HTTP_400_BAD_REQUEST)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def update(self, request, pk=None):

        data = request.data
        data['organization_id'] = request.user.organization_id
        data['user'] = request.user.user_alias
        data['userId'] = request.user.username
        dashboard = self.get_object()
        serializer = DashboardUpdateSerializer(dashboard,data=data)
        reports_for_update = self.update_report_list(data['reports'],dashboard.dashboard_id)
        reports = self.get_report_objects(request.user, data['reports'])

        if serializer.is_valid():
            serializer.save(reports = reports)
            for x in reports_for_update:
                report = self.get_report_object(x['report_id'],request.user)
                dashboard_report_serializer = DashboardReportOptionsSerializer(data = x['dashReportOptions'])
                if dashboard_report_serializer.is_valid():
                    dashboard_report_serializer.save(report = report, dashboard=dashboard)
            for f in data['dashReportFilters']:
                f['user'] = request.user.user_alias
                f['organization_id'] = request.user.organization_id
                if f['filter_id'] == None and not Filter.objects.filter(organization_id=f['organization_id']).filter(filter_id = f['filter_id']).exists():
                    filter_serializer = FilterSerializer(data = f)
                    if filter_serializer.is_valid():
                        filter_serializer.save(dashboard = dashboard)
                    else:
                        return Response(filter_serializer.errors, status = status.HTTP_400_BAD_REQUEST)
 
            return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self,request,pk=None):

        # data = request.data
        dashboard = self.get_object()
        dashboard.delete()
        return Response({'messge':'success'},status=status.HTTP_204_NO_CONTENT)

class SharingReports(viewsets.ViewSet):

    permission_classes=(permissions.IsAuthenticated&GridBackendShareReportPermissions,)
    authentication_classes=(GridBackendAuthentication,)

    def get_report_object(self,report_id):
        obj = Report.objects.filter(organization_id=self.request.user.organization_id).get(report_id = report_id)
        # self.check_object_permissions(self.request, obj)
        return obj
    
    def get_shared_users(self,request):
        data = request.data
        report = self.get_report_object(data['report_id'])
        shared_users = SharedReport.objects.select_related().filter(report = report)
        serializer = SharedReportSerializer(shared_users, many=True)
        return Response(data=serializer.data,status= status.HTTP_200_OK)
    
    def users_list(self,request):
        
        try:
            data = json.dumps({ 'organization_id' : request.user.organization_id })
            status = requests.post('{}/user/view'.format(os.environ['GRID_API']),headers={ 'Content-Type' : 'application/json' , 'Authorization':'Bearer {}'.format(request.user.token)},  data = data)
            res_data = json.loads(status.text)['data']
            return Response(res_data)
        except:
            return Response('error', status=status.HTTP_400_BAD_REQUEST)
            
    def list_users(self,request):
        
        try:
            data = json.dumps({ 'organization_id' : request.user.organization_id })
            status = requests.post('{}/user/view'.format(os.environ['GRID_API']),headers={ 'Content-Type' : 'application/json' , 'Authorization':'Bearer {}'.format(request.user.token)},  data = data)
            # res_data = json.loads(status.text)['data']
            return status.json()['data']
        except:
            return False

    def get_report_object_permissions(self,user,userlist,data):
        print("user",user,"userlist",userlist)
        for users in userlist:
            if user == users['userid']:
                if users['role'] == 'User':
                    return data['view'] and not data['edit'] and not data['delete']
                else:
                    return True

    def report_share(self, request):

        data = request.data
        report = self.get_report_object(data['report_id'])
        userlist = self.list_users(request)
        for x in data['user_id_list']:
            if self.get_report_object_permissions(x,userlist,data):
                data['view'] = True
                if data['delete']:
                    data['edit'] = True
                data['shared_user_id'] = request.user.username
                data['user_id'] = x
                serializer = SharedReportSerializer(data=data)
                if serializer.is_valid():
                    serializer.save(report = report)
                else:
                    return Response('error', status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response('error', status=status.HTTP_401_UNAUTHORIZED)

        return Response('success', status = status.HTTP_201_CREATED)
    
    def edit_share(self, request):

        data = request.data
        data['view'] = True
        if data['delete']:
            data['edit'] = True
        userlist = self.list_users(request)
        report = self.get_report_object(data['report_id'])
        if self.get_report_object_permissions(data['user_id'],userlist,data):
            
            shared_report_object = SharedReport.objects.filter(report = report).get(user_id = data['user_id'])
            serializer = SharedReportSerializer(shared_report_object, data = data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
            else:
                return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)
        else:
            return Response('error', status=status.HTTP_401_UNAUTHORIZED)

    
    def remove_share(self, request):

        data = request.data
        shared_report_object = SharedReport.objects.filter(report = data['report_id']).filter(user_id = data['user_id'])
        shared_report_object.delete()
        return Response(status = status.HTTP_204_NO_CONTENT)

class SharedDashboards(viewsets.ViewSet):

    permission_classes = (permissions.IsAuthenticated&GridBackendShareDashboardPermissions,)
    authentication_classes = (GridBackendAuthentication,)


    def get_dashboard_object(self,dashboard_id):
        obj = Dashboard.objects.filter(organization_id=self.request.user.organization_id).get(dashboard_id = dashboard_id)
        # self.check_object_permissions(self.request, obj)
        return obj
    
    def get_shared_users(self,request):
        data = request.data
        dashboard = self.get_report_object(data['dashboard_id'])
        shared_users = SharedDashboard.objects.select_related().filter(dashboard = dashboard)
        serializer = SharedDashboardSerializer(shared_users, many=True)
        return Response(data=serializer.data,status= status.HTTP_200_OK)
    
    # def users_list(self,request):
        
    #     try:
    #         data = json.dumps({ 'organization_id' : request.user.organization_id })
    #         status = requests.post('{}/user/view'.format(os.environ['GRID_API']),headers={ 'Content-Type' : 'application/json' , 'Authorization':'Bearer {}'.format(request.user.token)},  data = data)
    #         res_data = json.loads(status.text)['data']
    #         return Response(res_data)
    #     except:
    #         return Response('error', status=status.HTTP_400_BAD_REQUEST)

    def list_users(self,request):
        
        try:
            data = json.dumps({ 'organization_id' : request.user.organization_id })
            status = requests.post('{}/user/view'.format(os.environ['GRID_API']),headers={ 'Content-Type' : 'application/json' , 'Authorization':'Bearer {}'.format(request.user.token)},  data = data)
            # res_data = json.loads(status.text)['data']
            return status.json()['data']
        except:
            return False

    def get_dashboard_object_permissions(self,user,userlist,data):
        print("user",user,"userlist",userlist)
        for users in userlist:
            if user == users['userid']:
                if users['role'] == 'User':
                    return data['view'] and not data['edit'] and not data['delete']
                else:
                    return True

    def dashboard_share(self, request):

        data = request.data
        dashboard = self.get_dashboard_object(data['report_id'])
        userlist = self.list_users(request)
        for x in data['user_id_list']:
            if self.get_dashboard_object_permissions(x,userlist,data):
                data['view'] = True
                if data['delete']:
                    data['edit'] = True
                data['shared_user_id'] = request.user.username
                data['user_id'] = x
                serializer = SharedDashboardSerializer(data=data)
                if serializer.is_valid():
                    serializer.save(report = report)
                else:
                    return Response('error', status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response('error', status=status.HTTP_401_UNAUTHORIZED)

        return Response('success', status = status.HTTP_201_CREATED)
    
    def edit_share(self, request):

        data = request.data
        data['view'] = True
        if data['delete']:
            data['edit'] = True
        userlist = self.list_users(request)
        dashboard = self.get_dashboard_object(data['report_id'])
        if self.get_report_object_permissions(data['user_id'],userlist,data):
            
            shared_report_object = SharedDashboard.objects.filter(dashboard = dashboard).get(user_id = data['user_id'])
            serializer = SharedDashboardSerializer(shared_report_object, data = data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
            else:
                return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)
        else:
            return Response('error', status=status.HTTP_401_UNAUTHORIZED)


        
    
    def remove_share(self, request):

        data = request.data
        shared_dashboard_object = SharedDashboard.objects.filter(dashboard = data['dashboard_id']).filter(user_id = data['user_id'])
        shared_dashboard_object.delete()
        return Response(status = status.HTTP_204_NO_CONTENT)
    
    # def users_list(self,request):
    #     try:
    #         status = requests.post('{}/user/allUsers'.format(os.environ['GRID_API']), headers={'Authorization':'Bearer {}'.format(request.user.token)})
    #         res_data = json.loads(status.text)['data']
    #         out_data = []
    #         if request.user.role == 'Developer':
    #             out_data = [i for i in res_data if (i['role'] == 'Developer')]
    #         if request.user.role == 'admin':
    #             out_data = res_data
    #         return Response(out_data, status=status.HTTP_200_OK)
    #     except:
    #         return Response('error', status=status.HTTP_400_BAD_REQUEST)


    # def get_report_object(self,request,report_id,user):
    #     try:
    #         return Report.objects.filter(organization_id=user.organization_id).filter(user=user.username).get(report_id=report_id)
    #     except Report.DoesNotExist:
    #         raise Http404
    # def get_object(self, request, dashboard_id, user):
    #     try:
    #         obj = Dashboard.objects.filter(organization_id = user.organization_id)
    #         if self.check_object_permissions(self, request, obj):
    #             return obj.filter(userId = user.username).get(dashboard_id = dashboard_id)
    #         else:
    #             return Response('Unauthorized', status = status.HTTP_401_UNAUTHORIZED)
    #     except Dashboard.DoesNotExist:
    #         raise Http404
    
    # def dashboard_share(self, request):
        
    #     data = request.data
    #     dashbaord = self.get_object(request,data['dashboard_id'], request.user)
        
    #     for c in data['user_id_list']:
    #         data['view'] = True
    #         if c['edit']:
    #             data['edit'] = True
    #         if c['delete']:
    #             data['delete'] = True
    #         share_serializer = SharedDashboardSerializer(data = data)
    #         if share_serializer.is_valid():
    #             share_serializer.save(dashbaord = dashbaord,shared_user_id = request.user.username, user_id = c['id'])
    #             if share_serializer.data['edit'] or share_serializer.data['delete']: 

    #                 for x in dashbaord.report_set.all():
    #                     report = self.get_report_object(request.user.organization_id, x.report_id, request.user)
    #                     serializer = SharedReportSerializer(data=data)
    #                     if serializer.is_valid():
    #                         serializer.save(report = report, shared_user_id=request.user.username, user_id = c['id'])
    #                     else:
    #                         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    #         data['edit'] = False
    #         data['delete'] = False
    #     return Response('success', status = status.HTTP_201_CREATED)
    #     return Response(share_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class FilterList(viewsets.ViewSet):

    authentication_classes = (GridBackendAuthentication, )
    permission_classes = (permissions.IsAuthenticated,)
    
    def get_object(self,filter_id, user):
        try:
            return Filter.objects.filter(organization_id = user.organization_id).filter(userId = user.username).get(filter_id = filter_id)
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