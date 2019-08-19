from channels.generic.websocket import AsyncJsonWebsocketConsumer,AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db import connections
from celery.signals import after_task_publish,task_failure,task_success
from asgiref.sync import async_to_sync, sync_to_async
from django.dispatch import receiver
from channels.layers import get_channel_layer
from django_celery_beat.models import PeriodicTask
from django.core.management import call_command
from django.db import connections
from django.core.serializers.json import DjangoJSONEncoder


from app.utils import get_model,dictfetchall, getColumnList
from app.tasks import datasetRefresh, load_data
from app.models import Dataset,Report,Dashboard
from app.serializers import DynamicFieldsModelSerializer, GeneralSerializer

from django_pandas.io import read_frame
import numpy as np
import random
import pandas as pd
import redis
import pickle
import zlib
import arrow
import datetime
import ast
import collections
import simplejson as json
import time
import os
import boto3
import asyncio
from  django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, Http404

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

async def async_load_data(location,host,port,db):
    process = await asyncio.create_subprocess_shell(cmd='/home/ubuntu/grid_dashboarding/services/backend/env/bin/rdb --c protocol {} | redis-cli -h {} -p {} -n {} --pipe'.format(location,host,port,db))
    await process.wait()

# class NumpyEncoder(json.JSONEncoder):
#     def default(self, obj):
#         if isinstance(obj, np.ndarray):
#             return obj.tolist()
#         return json.JSONEncoder.default(self, obj)
class NumpyEncoder(json.JSONEncoder):
    """ Special json encoder for numpy types """
    #Changed the json encoder so that table generate will work properly
    def default(self, obj):
        if isinstance(obj, (np.int_, np.intc, np.intp, np.int8,
            np.int16, np.int32, np.int64, np.uint8,
            np.uint16, np.uint32, np.uint64)):
            return int(obj)
        elif isinstance(obj, (np.float_, np.float16, np.float32, 
            np.float64)):
            return float(obj)
        elif isinstance(obj,(np.ndarray,)):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)


class DatasetConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):
        if self.scope['user'] == None:
            await self.close()

        self.group_name = '{}_dataset'.format(self.scope['user'].organization_id)

        await self.channel_layer.group_add(self.group_name,self.channel_name)

        await self.accept()
    
    def get_object(self,dataset_id,user):
        try:
            return Dataset.objects.filter(userId = user.username).get(dataset_id = dataset_id)

        except Dataset.DoesNotexist:
            raise Http404
    
    def get_database_name(self,organization_id):
        with connections['rds'].cursor() as cursor:
            cursor.execute('select database_name from organizations where organization_id="{}";'.format(organization_id))
            return cursor.fetchone()
    
    def update_periodic_task(self,dataset):
        PeriodicTask.objects.get(id = dataset__scheduler__id).update(last_run_at = datetime.datetime.now())
        return PeriodicTask.get(id = dataset__scheduler__id).last_run_at

    async def refresh_now(self,dataset,user):
        database_name = await database_sync_to_async(self.get_database_name)(user.organization_id)
        datasetRefresh.delay(user.organization_id, dataset.dataset_id,self.channel_name)
    
    async def receive_json(self,data):
        if 'status' in data.keys():
            if data['status']:
                self.close()
            else:
                self.close(1011)
        else:
            self.data = data
            dataset = await database_sync_to_async(self.get_object)(data['dataset_id'],self.scope['user'])
            user = self.scope['user']
            await self.refresh_now(dataset,user)
    
    async def send_status(self,event):
        data = event['data']
        if data['channel_name'] == self.channel_name:
            if data['type'] == 'task_failure':
                await self.send_json(data['exception'])
            elif data['type'] == 'task_success':
                dataset = await database_sync_to_async(self.get_object)(data['dataset_id'], self.scope['user'])
                dataset.last_refreshed_at = datetime.datetime.now()
                await database_sync_to_async(dataset.save)()
                await self.send_json({ 'status' : 'success' })
            else:
                pass
        else:
            pass

class ReportGenerateConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):
        if self.scope['user'] == None:
            await self.close(1011)
        
        self.group_name = '{}_report_generate'.format(self.scope['user'].organization_id)

        await self.channel_layer.group_add(self.group_name,self.channel_name)

        await self.accept()

    # color_choices = ["#3e95cd", "#8e5ea2","#3cba9f","#e8c3b9","#c45850","#66FF66","#FB4D46", "#00755E", "#FFEB00", "#FF9933"]
    color_choices = ["#4B9FD4","#FFD739","#00A86B","#EC6767","#F88747"]

    def get_object(self,dataset_id,user):
        try:
            return Dataset.objects.filter(userId = user.username).get(dataset_id = dataset_id)

        except Dataset.DoesNotExist:
            raise Http404
    
    def check_filter_value_condition(self, df, condition,value):
        if condition == 'Equals':
            return df == value
        if condition == 'Does not equal':
            return df != value
        if condition == 'Greater than':
            return df > value
        if condition == 'Less than':
            return df < value
        if condition == '"Greater than or equal to"':
            return df >= value
        if condition == 'Less than or equal to':
            return df <= value
        if condition == 'Between':
            return (df >= value[0]) & (df <= value[1])
        if condition in ["By Date","By Month","By Week"]:
            return df == value
        if condition == 'By Date Range':
            return (df >= value[0]) & (df <= value[1])
    
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
    
    def sql_mode_fields(self,organization_id, sql):
        with connections['rds'].cursor() as cursor:
            cursor.execute('select database_name from organizations where organization_id="{}";'.format(organization_id))
            database_name = cursor.fetchone()[0]
        if organization_id not in connections.databases:
            connections.databases[organization_id] = {
                'ENGINE' : 'django.db.backends.mysql',
                'NAME' : database_name,
                'OPTIONS' : {
                    'read_default_file' : os.path.join(BASE_DIR, 'cred_dynamic.cnf'),
                }
            }
        with connections[organization_id].cursor() as cur:
            cur.execute(sql)
            return [(col[0], self.convert(col[1])) for col in cur.description]

    async def dataFrameGenerate(self, request_data, user):
        data = []
        r1 = redis.StrictRedis(host='127.0.0.1', port=6379, db=1)
        dataset_id = request_data['dataset_id'] or request_data['worksheet']
        
        model_fields = []
        if r1.exists('{}.{}'.format(user.organization_id,dataset_id)) != 0:
            print("data from redis")
            df = await sync_to_async(pickle.loads)(zlib.decompress(r1.get("{}.{}".format(user.organization_id,dataset_id))))
            model_fields = [(k.decode('utf8').replace("'", '"'),v.decode('utf8').replace("'", '"')) for k,v in r1.hgetall('{}.fields'.format(dataset_id)).items()]

        else:
            EXPIRATION_SECONDS = 600
            r = redis.Redis(host='127.0.0.1', port=6379, db=0)
            if request_data['op_table'] == 'dataset':
                dataset = await database_sync_to_async(self.get_object)(dataset_id,user)
                r = redis.Redis(host='127.0.0.1', port=6379, db=0)
                s3_resource= boto3.resource('s3',aws_access_key_id=os.environ.get('AWS_ACCESS_KEY'),aws_secret_access_key=os.environ.get('AWS_SECRET_KEY'))
                try:
                    s3_resource.Object('pragyaam-dash-dev','{}/{}.rdb'.format(user.organization_id,str(dataset.dataset_id))).download_file(f'/tmp/{dataset.dataset_id}.rdb')
                    # loop = asyncio.get_event_loop()
                    # task = loop.create_task(async_load_data('/tmp/{}.rdb'.format(dataset.dataset_id),'127.0.0.1',6379,0))
                    # asyncio.get_event_loop().run_until_complete(task)
                    # loop.close()
                except Exception as e:
                    print(e,flush=True)
                try:
                    load_data('/tmp/{}.rdb'.format(dataset.dataset_id),'127.0.0.1',6379,0) 
                except Exception as e:
                    print(e,flush=True)
                if dataset.mode == 'VIZ':
                    model = dataset.get_django_model()
                    model_fields = [(f.name, f.get_internal_type()) for f in model._meta.get_fields() if f.name is not 'id']
                    for x in range(1,r.dbsize()+1):
                        if r.get('edit.{}.{}.{}'.format(user.organization_id, dataset.dataset_id, str(x))) != None:
                            data.append({k.decode('utf8').replace("'", '"'): v.decode('utf8').replace("'", '"') for k,v in r.hgetall('edit.{}.{}.{}'.format(user.organization_id, dataset_id, str(x))).items()})
                        else:
                            data.append({k.decode('utf8').replace("'", '"'): v.decode('utf8').replace("'", '"') for k,v in r.hgetall('{}.{}.{}'.format(user.organization_id, dataset_id, str(x))).items()})
                else:
                    model_fields = await sync_to_async(self.sql_mode_fields)(user.organization_id,dataset.sql)
                    data = pickle.loads(zlib.decompress(r.get('data')))
                    
                r.flushdb(True) 
            else:
                with connections['rds'].cursor() as cursor:
                    cursor.execute('SELECT database_name from organizations where organization_id="{}"'.format(user.organization_id))
                    database_name = cursor.fetchone()[0]
                    print('databasename:',database_name)
                if user.organization_id not in connections.databases:
                    connections.databases[user.organization_id] = {
                        'ENGINE' : 'django.db.backends.mysql',
                        'NAME' : database_name,
                        'OPTIONS' : {
                            'read_default_file' : os.path.join(BASE_DIR, 'cred_dynamic.cnf'),
                        }
                    }
                with connections[user.organization_id].cursor() as cursor:
                    await database_sync_to_async(cursor.execute)('select SQL_NO_CACHE * from `{}`'.format(dataset_id))
                    # print("cursor",cursor.description)
                    table_data = await sync_to_async(dictfetchall)(cursor)
                    table_model = get_model(dataset_id,Dataset._meta.app_label,cursor, 'READ')
                    model_fields = [(f.name, f.get_internal_type()) for f in table_model._meta.get_fields() if f.name is not 'id']
                    GeneralSerializer.Meta.model = table_model

                    dynamic_serializer = GeneralSerializer(table_data,many = True)
                    del table_model
                del connections[user.organization_id]
        
                serializer_data = dynamic_serializer.data
                # print("serialized data for dynamic model",serializer_data)
                p = r.pipeline()
                id_count = 0
                for a in serializer_data:
                    id_count +=1
                    p.hmset('{}.{}.{}'.format(user.organization_id, dataset_id ,str(id_count)), {k:v for k,v in dict(a).items() if v is not None})
                try:
                    await sync_to_async(p.execute)()
                except Exception as e:
                    print(e)
                data = []
                for x in range(1,id_count+1):
                    data.append({k.decode('utf8').replace("'", '"'): v.decode('utf8').replace("'", '"') for k,v in r.hgetall('{}.{}.{}'.format(user.organization_id, dataset_id, str(x))).items()})
    
                r.flushdb(True)
            # print("data to dataframe",data)
            df = await sync_to_async(pd.DataFrame)(data)
            r1.setex("{}.{}".format(user.organization_id,dataset_id), EXPIRATION_SECONDS, zlib.compress( pickle.dumps(df)))
            r1.hmset('{}.fields'.format(dataset_id), { x[0] : x[1] for x in model_fields })
        # print("test model fields:",model_fields)
        for x in model_fields:
            if x[0] not in df.columns:
                # print(x[1])
        
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
                    df[x[0]] = df[x[0]].fillna(0,downcast='infer')
                if x[1] == 'IntegerField':
                    df[x[0]] = df[x[0]].apply(pd.to_numeric,errors='coerce')
                    df[x[0]] = df[x[0]].fillna(0,downcast='infer')
                if x[1] == 'CharField' or x[1] == 'TextField':
                    df = df.astype({ x[0] : 'object'})
                    df[x[0]] = df[x[0]].fillna(value='')
                if x[1] == 'DateField':
                    df = df.astype({ x[0] : 'datetime64'})
                    df.fillna(arrow.get('01-01-1990').datetime)
        return df,model_fields


        
    async def tableGenerate(self,df,field,value=None,group_by=None):
        data = {
            'column':[],
            'tableData':[]

        }
        if field['type'] in ["DateTimeField","DateField"]:
                df.loc[:,field['name']] = df[field['name']].map(pd.Timestamp.isoformat)
        
        if value == None:
            
            if group_by == None:
                data['column'] = [{'title':field['name'],'dataIndex':field['name']}]
                data_frame = df[field['name']].unique()
                tab_data = [{field['name']:value } for index,value in np.ndenumerate(data_frame)]
                data['tableData'] = tab_data
                serdata = json.dumps(data , cls=NumpyEncoder)
                # serdata = data.tojson()
            
            else:
                if group_by['type'] in ["DateTimeField","DateField"]:
                    df.loc[:,group_by['name']] = df[group_by['name']].map(pd.Timestamp.isoformat)
                data['column'] = [{'title':field['name'],'dataIndex':field['name']},{'title':group_by['name'],'dataIndex':group_by['name']}]
                data_frame = df.groupby([group_by['name'],field['name']]).agg(['count']).droplevel(0,axis=1)
                data['tableData']= [{ group_by['name']:index[0] ,field['name']:index[1] , 'count':int(row.iloc[0]) } for index , row in data_frame.iterrows()]
                serdata = json.dumps(data , cls=NumpyEncoder )
        else:

            if group_by == None:
                data['column'] = [{'title':field['name'],'dataIndex':field['name']},{'title':value['name'],'dataIndex': value['name']}]
                if value['aggregate']['value'] == 'none':
                    data_frame = df[[field['name'],value['name']]]
                    data['tableData']= [{field['name']:row[1].values[0] ,value['name']: row[1].values[1]} for row in data_frame.iterrows()]
                if value['aggregate']['value'] == 'sum':
                    data_frame = df.groupby(field['name'])[value['name']].sum()
                    data_dict = data_frame.to_dict()
                    data['tableData'] = [{field['name']:key , value['name']:val } for key,val in data_dict.items()]
                        
                if value['aggregate']['value'] == "count":
                    data_frame = df.groupby(field['name'])[value['name']].count()
                    data_dict = data_frame.to_dict()
                    data['tableData'] = [{field['name']:key , value['name']:val } for key,val in data_dict.items()]
                if value['aggregate']['value'] == "count distinct":
                    data_frame = df.groupby(field['name'])[value['name']].nunique()
                    data_dict = data_frame.to_dict()
                    data['tableData'] = [{field['name']:key , value['name']:val } for key,val in data_dict.items()]

                if value['aggregate']['value'] == "max":
                    data_frame = df.groupby(field['name'])[value['name']].max()
                    data_dict = data_frame.to_dict()
                    data['tableData'] = [{field['name']:key , value['name']:val } for key,val in data_dict.items()]

                if value['aggregate']['value'] == "min":
                    data_frame = df.groupby(field['name'])[value['name']].min()
                    data_dict = data_frame.to_dict()
                    data['tableData'] = [{field['name']:key , value['name']:val } for key,val in data_dict.items()]
                if value['aggregate']['value'] == "average":
                    data_frame = df.groupby(field['name'])[value['name']].mean()   
                    data_dict = data_frame.to_dict()
                    data['tableData'] = [{field['name']:key , value['name']:val } for key,val in data_dict.items()]
                serdata = json.dumps(data , cls=NumpyEncoder )
            else:
                if group_by['type'] in ["DateTimeField","DateField"]:
                    df.loc[:,group_by['name']] = df[group_by['name']].map(pd.Timestamp.isoformat)
                data['column'] = [{'title':group_by['name'],'dataIndex':group_by['name']},{'title':field['name'],'dataIndex':field['name']},{'title':value['name'],'dataIndex': value['name']}]
                if value['aggregate']['value'] == 'none':
                    # data_frame = df[[group_by['name'],field['name'],value['name']]]
                    # data['tableData']= [{group_by['name']:i[0],field['name']:i[1],value['name']:i[2]} for i,r in data_frame]
                    data_frame = df.sort_values(group_by['name'])[[group_by['name'],field['name'],value['name']]]
                    data['tableData'] = [{group_by['name']:r[0],field['name']:r[1],value['name']:r[2]} for i,r in data_frame.iterrows()]

                if value['aggregate']['value'] == 'sum':
                    data_frame = df.groupby([group_by['name'],field['name']])[value['name']].sum()
                    data_dict = data_frame.to_dict()
                    data['tableData'] = [{group_by['name']:key[0],field['name']:key[1] , value['name']:val } for key,val in data_dict.items()]
                        
                if value['aggregate']['value'] == "count":
                    data_frame = df.groupby([group_by['name'],field['name']])[value['name']].count()
                    data_dict = data_frame.to_dict()
                    data['tableData'] = [{group_by['name']:key[0],field['name']:key[1] , value['name']:val } for key,val in data_dict.items()]

                if value['aggregate']['value'] == "count distinct":
                    data_frame = df.groupby([group_by['name'],field['name']])[value['name']].nunique()
                    data_dict = data_frame.to_dict()
                    data['tableData'] = [{group_by['name']:key[0],field['name']:key[1] , value['name']:val } for key,val in data_dict.items()]

                if value['aggregate']['value'] == "max":
                    data_frame = df.groupby([group_by['name'],field['name']])[value['name']].max()
                    data_dict = data_frame.to_dict()
                    data['tableData'] = [{group_by['name']:key[0],field['name']:key[1] , value['name']:val } for key,val in data_dict.items()]

                if value['aggregate']['value'] == "min":
                    data_frame = df.groupby([group_by['name'],field['name']])[value['name']].min()
                    data_dict = data_frame.to_dict()
                    data['tableData'] = [{group_by['name']:key[0],field['name']:key[1] , value['name']:val } for key,val in data_dict.items()]
                if value['aggregate']['value'] == "average":
                    data_frame = df.groupby([group_by['name'],field['name']])[value['name']].mean()
                    data_dict = data_frame.to_dict()
                    data['tableData'] = [{group_by['name']:key[0],field['name']:key[1] , value['name']:val } for key,val in data_dict.items()]
                
                serdata = json.dumps(data , cls=NumpyEncoder )
                
        await self.send(serdata)
            
    async def graphDataGenerate(self,df,report_type,field,value=None,group_by=None):
        all_fields = []
        df = df.dropna()
        if report_type == "table":
            await self.tableGenerate(df,field,value,group_by)
            return True
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
                if report_type == "scatter" or field['type'] in ["DateField", "DateTimeField"]:
                    if report_type == 'scatter':
                        if field['type'] in ["DateTimeField","DateField"]:
                            df.loc[:,field['name']] = df[field['name']].map(pd.Timestamp.isoformat)    
                        else:
                            df = df.astype({ field['name'] : 'str' })
                        for d in np.unique(np.array(df.loc[:,field['name']])):
                            new_add.append({
                                'x' : d,
                                'y' : op_dict[d]})
                    else:
                        if report_type == 'horizontalBar':
                            for d in data['labels']:
                                new_add.append({
                                    'y' : d,
                                    'x' : op_dict[d]})
                        else:
                            for d in data['labels']:
                                new_add.append({
                                    'x' : d,
                                    'y' : op_dict[d]})
                elif report_type == "bubble":
                    background_colors = ['{}66'.format(x) for x in colors]
                    if field['type'] in ["DateTimeField","DateField"]:
                        df.loc[:,field['name']] = df[field['name']].map(pd.Timestamp.isoformat)
                    else:
                        df = df.astype({ field['name'] : 'str' })
                    for d in np.unique(np.array(df.loc[:,field['name']])):
                        new_add.append({
                            'x' : d,
                            'y' : op_dict[d],
                            'r' : random.randint(15,30)})
                elif report_type == "table": #handling table graph with only field name no value
                    for label in op_dict:
                        new_add.append(label)
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
                elif report_type == "table": #adding label and data to dataset
                    data['datasets'].append({ 'label': field['name'], 'data': new_add})
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
                # for index,row in df_group_count.iterrows():
                #     op_dict[row[group_by['name']]][[field['name']]] = row['count']
                for group in op_dict.keys():        
    
                    if report_type == "bubble":
                        border_color_chosen = random.choice(colors)
                        color_chosen = '{}66'.format(border_color_chosen)
                        r_chosen = random.randint(15,30)
                    elif report_type == "radar":
                        color_chosen = random.choice(colors)    
                        background_color = '{}66'.format(color_chosen)
                    else:
                        color_chosen = random.choice(colors)

                    new_add = []
                    if report_type == "scatter" or field['type'] in ["DateField", "DateTimeField"]:
                        if report_type != "scatter":
                            for x in data['labels']:
                                new_add.append({
                                    'x' : x,
                                    'y' : op_dict[group][x]})
                        else:
                            if field['type'] in ["DateTimeField","DateField"]:
                                df.loc[:,field['name']] = df[field['name']].map(pd.Timestamp.isoformat)
                            else:
                                df = df.astype({ field['name'] : 'str' })
                            for x in np.unique(np.array(df.loc[:,field['name']])):
                                new_add.append({
                                    'x' : x,
                                    'y' : op_dict[group][x]})
                    elif report_type == "bubble":
                        if field['type'] in ["DateTimeField","DateField"]:
                            df.loc[:,field['name']] = df[field['name']].map(pd.Timestamp.isoformat)
                        else:
                            df = df.astype({ field['name'] : 'str' })
                        for x in np.unique(np.array(df.loc[:,field['name']])):
                            new_add.append({
                                'x' : x,
                                'y' : op_dict[group][x],
                                'r' : r_chosen })
                    elif report_type == "table" : #handling report type table with field name and group by only no value
                        # for key,val in op_dict.items():
                        #     new_add.append({
                        #         'x' : key,
                        #         'y' : val
                        #     })
                        if field['type'] in ["DateTimeField","DateField"]:
                            df.loc[:,field['name']] = df[field['name']].map(pd.Timestamp.isoformat)
                        else:
                            df = df.astype({ field['name'] : 'str' })
                        for x in np.unique(np.array(df.loc[:,field['name']])):
                            new_add.append({
                                'x' : x,
                                'y' : op_dict[group][x],
                            })
                    else:
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                    if group_by in ["DateField","DateTimeField"]:
                        if report_type in ["horizontalBar","bar","pie","doughnut","scatter","polarArea"]:
                            data['datasets'].append({ 'label' : group.isoformat(), 'backgroundColor' : color_chosen, 'data' : new_add })
                        elif report_type in ["line"]:
                            data['datasets'].append({ 'label' : group.isoformat(), 'fill' : False,'borderColor' : color_chosen, 'data' : new_add })
                        elif report_type == "bubble":
                            data['datasets'].append({ 'label' : group.isoformat(), 'borderColor' : border_color_chosen,'hoverBackgroundColor' : color_chosen,'backgroundColor' : color_chosen, 'data' : new_add })
                        elif report_type == "radar":
                            data['datasets'].append({ 'label' : group.isoformat(), 'fill' : True,'backgroundColor' : background_color,'borderColor' : color_chosen, 'data' : new_add })
                        elif report_type == "bar_mix":
                            data['datasets'].append({ 'type' : 'bar','label' : group.isoformat(), 'backgroundColor' : color_chosen, 'data' : new_add })
                            data['datasets'].append({ 'type': 'line','label' : group.isoformat(), 'fill' : True,'backgroundColor' : '{}66'.format(color_chosen),'borderColor' : color_chosen, 'data' : new_add })
                        elif report_type == "table": # adding label groupby and dataset to data
                            data['datasets'].append({ 'label' : group.isoformat(), 'data' : new_add })
                        else:
                            pass
                    else:
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
                        elif report_type == "table": # adding label groupby and dataset to data
                            data['datasets'].append({ 'label' : group, 'data' : new_add })
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
                    if report_type == 'scatter':
                        if field['type'] in ["DateTimeField","DateField"]:
                            df.loc[:,field['name']] = df[field['name']].map(pd.Timestamp.isoformat)
                        else:
                            df = df.astype({ field['name'] : 'str' })
                        for d in np.unique(np.array(df.loc[:,field['name']])):
                            new_add.append({
                                'x' : d,
                                'y' : op_dict[d]})
                    else:
                        for d in data['labels']:
                            new_add.append({
                                'x' : d,
                                'y' : op_dict[d]})
                elif report_type == "bubble":
                    background_colors = ['{}66'.format(x) for x in colors]
                    if field['type'] in ["DateTimeField","DateField"]:
                        df.loc[:,field['name']] = df[field['name']].map(pd.Timestamp.isoformat)
                    else:
                        df = df.astype({ field['name'] : 'str' })
                    for d in np.unique(np.array(df.loc[:,field['name']])):
                        new_add.append({
                            'x' : d,
                            'y' : op_dict[d],
                            'r' : random.randint(15,30)})
                
                elif report_type == "table": # if value is there and no groupby 
                    if field['type'] in ["DateTimeField","DateField"]:
                        df.loc[:,field['name']] = df[field['name']].map(pd.Timestamp.isoformat)
                    else:
                        df = df.astype({ field['name'] : 'str' })
                    for d in np.unique(np.array(df.loc[:,field['name']])):
                        new_add.append({
                            'x' : d,
                            'y' : op_dict[d]
                        })
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
                elif report_type == "table" : # adding to data
                    data['datasets'].append({' label' : value['name'], 'data' : new_add })
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
                        if report_type != "scatter":
                            for x in data['labels']:
                                new_add.append({
                                    'x' : x,
                                    'y' : op_dict[group][x]})
                        else:
                            if field['type'] in ["DateTimeField","DateField"]:
                                df.loc[:,field['name']] = df[field['name']].map(pd.Timestamp.isoformat)
                            else:
                                df = df.astype({ field['name'] : 'str' })
                            for x in np.unique(np.array(df.loc[:,field['name']])):
                                new_add.append({
                                    'x' : x,
                                    'y' : op_dict[group][x]})
                    elif report_type == "bubble":
                        if field['type'] in ["DateTimeField","DateField"]:
                            df.loc[:,field['name']] = df[field['name']].map(pd.Timestamp.isoformat)
                        else:
                            df = df.astype({ field['name'] : 'str' })
                        for x in np.unique(np.array(df.loc[:,field['name']])):
                            new_add.append({
                                'x' : x,
                                'y' : op_dict[group][x],
                                'r' : r_chosen })
                    elif report_type == "table": #adding table report type
                        if field['type'] in ["DateTimeField","DateField"]:
                            df.loc[:,field['name']] = df[field['name']].map(pd.Timestamp.isoformat)
                        else:
                            df = df.astype({ field['name'] : 'str' })
                        for x in np.unique(np.array(df.loc[:,field['name']])):
                            new_add.append({
                                'x' : x,
                                'y' : op_dict[group][x]
                            })
                    else:
                        for x in data['labels']:
                            new_add.append(op_dict[group][x])
                    if group_by['type'] in ["DateField","DateTimeField"]:
                        if report_type in ["horizontalBar","bar","pie","doughnut","scatter","polarArea"]:
                            data['datasets'].append({ 'label' : group.isoformat(), 'backgroundColor' : color_chosen, 'data' : new_add })
                        elif report_type in ["line"]:
                            data['datasets'].append({ 'label' : group.isoformat(), 'fill' : False,'borderColor' : color_chosen, 'data' : new_add })
                        elif report_type == "bubble":
                            data['datasets'].append({ 'label' : group.isoformat(), 'borderColor' : border_color_chosen,'hoverBackgroundColor' : color_chosen,'backgroundColor' : color_chosen, 'data' : new_add })
                        elif report_type == "radar":
                            data['datasets'].append({ 'label' : group.isoformat(), 'fill' : True,'backgroundColor' : background_color,'borderColor' : color_chosen, 'data' : new_add })
                        elif report_type == "bar_mix":
                            data['datasets'].append({ 'type' : 'bar','label' : group.isoformat(), 'backgroundColor' : color_chosen, 'data' : new_add })
                            data['datasets'].append({ 'type': 'line','label' : group.isoformat(), 'fill' : True,'backgroundColor' : '{}66'.format(color_chosen),'borderColor' : color_chosen, 'data' : new_add })
                        elif report_type == "table" : # adding to data
                            data['datasets'].append({ 'label' : group.isoformat(), 'data' : new_add })
                        else:
                            pass
                    else:
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
                        elif report_type == "table" : # adding to data
                            data['datasets'].append({ 'label' : group, 'data' : new_add })
                        else:
                            pass

                    if len(colors) > 1:
                        colors.remove(color_chosen)
        await self.send(json.dumps(data, cls=NumpyEncoder))

    async def receive_json(self,data):
        try:
            report_type = data['type']
            df, model_fields= await self.dataFrameGenerate(data, self.scope['user'])
            # df.to_csv("hell.csv")
            dict_fields = dict(model_fields)
            for fil in data['filters']:
                if fil['activate']:
                    options = fil['options']
                    if options['type'] in ['CharField','TextField']:
                        if options['mode'] == 'pick':
                            
                            if options['field_aggregate'] == 'No Aggregate':
                                df = df[df[fil['field_name']].isin(options['values'])]

                            if options['field_aggregate'] == 'Count':
                                if options['value_aggregate'] == 'Select Values':
                                    # agg = df.groupby(fil['field_name'],sort=False).count()
                                    # condition = agg.isin(options['values'])
                                    # df = df[agg[condition].index]
                                    df = df.groupby(fil['field_name']).filter(lambda x: x[fil['field_name']].count() in options['values'])
                    

                                if options['value_aggregate'] == 'Ranges':
                                    df_ranges = []
                                    agg = df.groupby(fil['field_name'],sort=False).count()
                                    for x in options['values']:
                                        df_ranges.append(df[agg[self.check_fil_value_condition(agg,'between', x)].index])
                                    df = pd.concat(df_ranges, ignore_index=True)

                                if options['value_aggregate'] == 'Top/Bottom':
                                    if options['value_aggregate'] == 'Top 5':
                                        df = df.groupby(fil['field_name'],sort=False).count().sort_values(by=[options['value_aggregate_field']],ascending=False).head(5)
                                    if options['value_aggregate'] == 'Top 10':
                                        df = df.groupby(fil['field_name'],sort=False).count().sort_values(by=[options['value_aggregate_field']],ascending=False).head(10)
                                    if options['value_aggregate'] == 'Bottom 5':
                                        df = df.groupby(fil['field_name'],sort=False).count().sort_values(by=[options['value_aggregate_field']]).head(5)
                                    if options['value_aggregate'] == 'Bottom 10':
                                        df = df.groupby(fil['field_name'],sort=False).count().sort_values(by=[options['value_aggregate_field']]).head(10)

                                if options['value_aggregate'] == 'Top/Bottom %':
                                    n = len(df.index)
                                    if options['value_aggregate'] == 'Top 5%':
                                        df = df.groupby(fil['field_name'],sort=False).count().sort_values(by=[options['value_aggregate_field']],ascending=False).head(int(0.05*n))
                                    if options['value_aggregate'] == 'Top 10%':
                                        df = df.groupby(fil['field_name'],sort=False).count().sort_values(by=[options['value_aggregate_field']],ascending=False).head(int(0.1*n))
                                    if options['value_aggregate'] == 'Bottom 5%':
                                        df = df.groupby(fil['field_name'],sort=False).count().sort_values(by=[options['value_aggregate_field']]).head(int(0.05*n))
                                    if options['value_aggregate'] == 'Bottom 10%':
                                        df = df.groupby(fil['field_name'],sort=False).count().sort_values(by=[options['value_aggregate_field']]).head(int(0.1*n))
                            
                            if options['field_aggregate'] == 'Count Distinct':
                                if options['value_aggregate'] == 'Select Values':
                                    # agg = df.groupby(fil['field_name'],sort=False).nunique()
                                    # condition = agg.isin(options['values'])
                                    # df = df[agg[condition].index]
                                    df = df.groupby(fil['field_name']).filter(lambda x: x[fil['field_name']].nunique() in options['values'])
                                    print('df',df)
                                if options['value_aggregate'] == 'Ranges':
                                    df_ranges = []
                                    agg = df.groupby(fil['field_name'],sort=False).nunique()
                                    for x in options['values']:
                                        df_ranges.append(df[agg[self.check_fil_value_condition(agg,'between', x)].index])
                                    df = pd.concat(df_ranges, ignore_index=True)

                                if options['value_aggregate'] == 'Top/Bottom':
                                    if options['value_aggregate'] == 'Top 5':
                                        df = df.groupby(fil['field_name'],sort=False).nunique().sort_values(by=[options['value_aggregate_field']],ascending=False).head(5)
                                    if options['value_aggregate'] == 'Top 10':
                                        df = df.groupby(fil['field_name'],sort=False).nunique().sort_values(by=[options['value_aggregate_field']],ascending=False).head(10)
                                    if options['value_aggregate'] == 'Bottom 5':
                                        df = df.groupby(fil['field_name'],sort=False).nunique().sort_values(by=[options['value_aggregate_field']]).head(5)
                                    if options['value_aggregate'] == 'Bottom 10':
                                        df = df.groupby(fil['field_name'],sort=False).nunique().sort_values(by=[options['value_aggregate_field']]).head(10)

                                if options['value_aggregate'] == 'Top/Bottom %':
                                    n = len(df.index)
                                    if options['value_aggregate'] == 'Top 5%':
                                        df = df.groupby(fil['field_name'],sort=False).nunique().sort_values(by=[options['value_aggregate_field']],ascending=False).head(int(0.05*n))
                                    if options['value_aggregate'] == 'Top 10%':
                                        df = df.groupby(fil['field_name'],sort=False).nunique().sort_values(by=[options['value_aggregate_field']],ascending=False).head(int(0.1*n))
                                    if options['value_aggregate'] == 'Bottom 5%':
                                        df = df.groupby(fil['field_name'],sort=False).nunique().sort_values(by=[options['value_aggregate_field']]).head(int(0.05*n))
                                    if options['value_aggregate'] == 'Bottom 10%':
                                        df = df.groupby(fil['field_name'],sort=False).nunique().sort_values(by=[options['value_aggregate_field']]).head(int(0.1*n))
                        if options['mode'] == 'range':

                            if options['field_aggregate'] == 'Count':
                                agg = df[fil['field_name']].count()
                                df = df[agg[self.check_filter_value_condition(agg, options['rangeBy'], options['rangeValue'])].index]
                            
                            if options['field_aggregate'] == 'Count Distinct':
                                agg = df[fil['field_name']].nunique()
                                df = df[agg[self.check_filter_value_condition(agg, options['rangeBy'], options['rangeValue'])].index]

                    if options['type'] in ['FloatField','IntegerField']:
                        if options['mode'] == 'pick':
                            if options['field_aggregate'] == 'No Aggregate':
                                if options['value_aggregate'] == 'Select Values':
                                    condition = df[fil['field_name']].isin(options['values'])
                                    df = df[condition]

                                if options['value_aggregate'] == 'Ranges':
                                    df_ranges = []
                                    for x in options['values']:
                                        df_ranges.append(df[self.check_fil_value_condition(df[fil['field_name']],'between', x)])
                                    df = pd.concat(df_ranges, ignore_index=True)

                                if options['value_aggregate'] == 'Top/Bottom':
                                    if options['value_aggregate'] == 'Top 5':
                                        df = df.sort_values(by=[options['value_aggregate_field']],ascending=False).head(5)
                                    if options['value_aggregate'] == 'Top 10':
                                        df = df.sort_values(by=[options['value_aggregate_field']],ascending=False).head(10)
                                    if options['value_aggregate'] == 'Bottom 5':
                                        df = df.sort_values(by=[options['value_aggregate_field']]).head(5)
                                    if options['value_aggregate'] == 'Bottom 10':
                                        df = df.sort_values(by=[options['value_aggregate_field']]).head(10)

                                if options['value_aggregate'] == 'Top/Bottom %':
                                    n = len(df.index)
                                    if options['value_aggregate'] == 'Top 5%':
                                        df = df.sort_values(by=[options['value_aggregate_field']],ascending=False).head(int(0.05*n))
                                    if options['value_aggregate'] == 'Top 10%':
                                        df = df.sort_values(by=[options['value_aggregate_field']],ascending=False).head(int(0.1*n))
                                    if options['value_aggregate'] == 'Bottom 5%':
                                        df = df.sort_values(by=[options['value_aggregate_field']]).head(int(0.05*n))
                                    if options['value_aggregate'] == 'Bottom 10%':
                                        df = df.sort_values(by=[options['value_aggregate_field']]).head(int(0.1*n))
                            
                            if options['field_aggregate'] == 'Sum':
                                if options['value_aggregate'] == 'Select Values':
                                    agg = df.groupby(fil['field_name'],sort=False).sum()
                                    condition = agg.isin(options['values'])
                                    df = df[agg[condition].index]

                                if options['value_aggregate'] == 'Ranges':
                                    df_ranges = []
                                    agg = df.groupby(fil['field_name'],sort=False).sum()
                                    for x in options['values']:
                                        df_ranges.append(df[agg[self.check_fil_value_condition(agg,'between', x)].index])
                                    df = pd.concat(df_ranges, ignore_index=True)

                                if options['value_aggregate'] == 'Top/Bottom':
                                    if options['value_aggregate'] == 'Top 5':
                                        df = df.groupby(fil['field_name'],sort=False).sum().sort_values(by=[options['value_aggregate_field']],ascending=False).head(5)
                                    if options['value_aggregate'] == 'Top 10':
                                        df = df.groupby(fil['field_name'],sort=False).sum().sort_values(by=[options['value_aggregate_field']],ascending=False).head(10)
                                    if options['value_aggregate'] == 'Bottom 5':
                                        df = df.groupby(fil['field_name'],sort=False).sum().sort_values(by=[options['value_aggregate_field']]).head(5)
                                    if options['value_aggregate'] == 'Bottom 10':
                                        df = df.groupby(fil['field_name'],sort=False).sum().sort_values(by=[options['value_aggregate_field']]).head(10)

                                if options['value_aggregate'] == 'Top/Bottom %':
                                    n = len(df.index)
                                    if options['value_aggregate'] == 'Top 5%':
                                        df = df.groupby(fil['field_name'],sort=False).sum().sort_values(by=[options['value_aggregate_field']],ascending=False).head(int(0.05*n))
                                    if options['value_aggregate'] == 'Top 10%':
                                        df = df.groupby(fil['field_name'],sort=False).sum().sort_values(by=[options['value_aggregate_field']],ascending=False).head(int(0.1*n))
                                    if options['value_aggregate'] == 'Bottom 5%':
                                        df = df.groupby(fil['field_name'],sort=False).sum().sort_values(by=[options['value_aggregate_field']]).head(int(0.05*n))
                                    if options['value_aggregate'] == 'Bottom 10%':
                                        df = df.groupby(fil['field_name'],sort=False).sum().sort_values(by=[options['value_aggregate_field']]).head(int(0.1*n))

                            if options['field_aggregate'] == 'Min':
                                if options['value_aggregate'] == 'Select Values':
                                    agg = df.groupby(fil['field_name'],sort=False).min()
                                    condition = agg.isin(options['values'])
                                    df = df[agg[condition].index]

                                if options['value_aggregate'] == 'Ranges':
                                    df_ranges = []
                                    agg = df.groupby(fil['field_name'],sort=False).min()
                                    for x in options['values']:
                                        df_ranges.append(df[agg[self.check_fil_value_condition(agg,'between', x)].index])
                                    df = pd.concat(df_ranges, ignore_index=True)

                                if options['value_aggregate'] == 'Top/Bottom':
                                    if options['value_aggregate'] == 'Top 5':
                                        df = df.groupby(fil['field_name'],sort=False).min().sort_values(by=[options['value_aggregate_field']],ascending=False).head(5)
                                    if options['value_aggregate'] == 'Top 10':
                                        df = df.groupby(fil['field_name'],sort=False).min().sort_values(by=[options['value_aggregate_field']],ascending=False).head(10)
                                    if options['value_aggregate'] == 'Bottom 5':
                                        df = df.groupby(fil['field_name'],sort=False).min().sort_values(by=[options['value_aggregate_field']]).head(5)
                                    if options['value_aggregate'] == 'Bottom 10':
                                        df = df.groupby(fil['field_name'],sort=False).min().sort_values(by=[options['value_aggregate_field']]).head(10)

                                if options['value_aggregate'] == 'Top/Bottom %':
                                    n = len(df.index)
                                    if options['value_aggregate'] == 'Top 5%':
                                        df = df.groupby(fil['field_name'],sort=False).min().sort_values(by=[options['value_aggregate_field']],ascending=False).head(int(0.05*n))
                                    if options['value_aggregate'] == 'Top 10%':
                                        df = df.groupby(fil['field_name'],sort=False).min().sort_values(by=[options['value_aggregate_field']],ascending=False).head(int(0.1*n))
                                    if options['value_aggregate'] == 'Bottom 5%':
                                        df = df.groupby(fil['field_name'],sort=False).min().sort_values(by=[options['value_aggregate_field']]).head(int(0.05*n))
                                    if options['value_aggregate'] == 'Bottom 10%':
                                        df = df.groupby(fil['field_name'],sort=False).min().sort_values(by=[options['value_aggregate_field']]).head(int(0.1*n))
                            
                            if options['field_aggregate'] == 'Max':
                                if options['value_aggregate'] == 'Select Values':
                                    agg = df.groupby(fil['field_name'],sort=False).max()
                                    condition = agg.isin(options['values'])
                                    df = df[agg[condition].index]

                                if options['value_aggregate'] == 'Ranges':
                                    df_ranges = []
                                    agg = df.groupby(fil['field_name'],sort=False).max()
                                    for x in options['values']:
                                        df_ranges.append(df[agg[self.check_fil_value_condition(agg,'between', x)].index])
                                    df = pd.concat(df_ranges, ignore_index=True)

                                if options['value_aggregate'] == 'Top/Bottom':
                                    if options['value_aggregate'] == 'Top 5':
                                        df = df.groupby(fil['field_name'],sort=False).max().sort_values(by=[options['value_aggregate_field']],ascending=False).head(5)
                                    if options['value_aggregate'] == 'Top 10':
                                        df = df.groupby(fil['field_name'],sort=False).max().sort_values(by=[options['value_aggregate_field']],ascending=False).head(10)
                                    if options['value_aggregate'] == 'Bottom 5':
                                        df = df.groupby(fil['field_name'],sort=False).max().sort_values(by=[options['value_aggregate_field']]).head(5)
                                    if options['value_aggregate'] == 'Bottom 10':
                                        df = df.groupby(fil['field_name'],sort=False).max().sort_values(by=[options['value_aggregate_field']]).head(10)

                                if options['value_aggregate'] == 'Top/Bottom %':
                                    n = len(df.index)
                                    if options['value_aggregate'] == 'Top 5%':
                                        df = df.groupby(fil['field_name'],sort=False).max().sort_values(by=[options['value_aggregate_field']],ascending=False).head(int(0.05*n))
                                    if options['value_aggregate'] == 'Top 10%':
                                        df = df.groupby(fil['field_name'],sort=False).max().sort_values(by=[options['value_aggregate_field']],ascending=False).head(int(0.1*n))
                                    if options['value_aggregate'] == 'Bottom 5%':
                                        df = df.groupby(fil['field_name'],sort=False).max().sort_values(by=[options['value_aggregate_field']]).head(int(0.05*n))
                                    if options['value_aggregate'] == 'Bottom 10%':
                                        df = df.groupby(fil['field_name'],sort=False).max().sort_values(by=[options['value_aggregate_field']]).head(int(0.1*n))
                            
                            if options['field_aggregate'] == 'Average':
                                if options['value_aggregate'] == 'Select Values':
                                    agg = df.groupby(fil['field_name'],sort=False).mean()
                                    condition = agg.isin(options['values'])
                                    df = df[agg[condition].index]

                                if options['value_aggregate'] == 'Ranges':
                                    df_ranges = []
                                    agg = df.groupby(fil['field_name'],sort=False).mean()
                                    for x in options['values']:
                                        df_ranges.append(df[agg[self.check_fil_value_condition(agg,'between', x)].index])
                                    df = pd.concat(df_ranges, ignore_index=True)

                                if options['value_aggregate'] == 'Top/Bottom':
                                    if options['value_aggregate'] == 'Top 5':
                                        df = df.groupby(fil['field_name'],sort=False).mean().sort_values(by=[options['value_aggregate_field']],ascending=False).head(5)
                                    if options['value_aggregate'] == 'Top 10':
                                        df = df.groupby(fil['field_name'],sort=False).mean().sort_values(by=[options['value_aggregate_field']],ascending=False).head(10)
                                    if options['value_aggregate'] == 'Bottom 5':
                                        df = df.groupby(fil['field_name'],sort=False).mean().sort_values(by=[options['value_aggregate_field']]).head(5)
                                    if options['value_aggregate'] == 'Bottom 10':
                                        df = df.groupby(fil['field_name'],sort=False).mean().sort_values(by=[options['value_aggregate_field']]).head(10)

                                if options['value_aggregate'] == 'Top/Bottom %':
                                    n = len(df.index)
                                    if options['value_aggregate'] == 'Top 5%':
                                        df = df.groupby(fil['field_name'],sort=False).mean().sort_values(by=[options['value_aggregate_field']],ascending=False).head(int(0.05*n))
                                    if options['value_aggregate'] == 'Top 10%':
                                        df = df.groupby(fil['field_name'],sort=False).mean().sort_values(by=[options['value_aggregate_field']],ascending=False).head(int(0.1*n))
                                    if options['value_aggregate'] == 'Bottom 5%':
                                        df = df.groupby(fil['field_name'],sort=False).mean().sort_values(by=[options['value_aggregate_field']]).head(int(0.05*n))
                                    if options['value_aggregate'] == 'Bottom 10%':
                                        df = df.groupby(fil['field_name'],sort=False).mean().sort_values(by=[options['value_aggregate_field']]).head(int(0.1*n))
                    
                            if options['field_aggregate'] == 'Std Dev':
                                if options['value_aggregate'] == 'Select Values':
                                    agg = df.groupby(fil['field_name'],sort=False).std()
                                    condition = agg.isin(options['values'])
                                    df = df[agg[condition].index]

                                if options['value_aggregate'] == 'Ranges':
                                    df_ranges = []
                                    agg = df.groupby(fil['field_name'],sort=False).std()
                                    for x in options['values']:
                                        df_ranges.append(df[agg[self.check_fil_value_condition(agg,'between', x)].index])
                                    df = pd.concat(df_ranges, ignore_index=True)

                                if options['value_aggregate'] == 'Top/Bottom':
                                    if options['value_aggregate'] == 'Top 5':
                                        df = df.groupby(fil['field_name'],sort=False).std().sort_values(by=[options['value_aggregate_field']],ascending=False).head(5)
                                    if options['value_aggregate'] == 'Top 10':
                                        df = df.groupby(fil['field_name'],sort=False).std().sort_values(by=[options['value_aggregate_field']],ascending=False).head(10)
                                    if options['value_aggregate'] == 'Bottom 5':
                                        df = df.groupby(fil['field_name'],sort=False).std().sort_values(by=[options['value_aggregate_field']]).head(5)
                                    if options['value_aggregate'] == 'Bottom 10':
                                        df = df.groupby(fil['field_name'],sort=False).std().sort_values(by=[options['value_aggregate_field']]).head(10)

                                if options['value_aggregate'] == 'Top/Bottom %':
                                    n = len(df.index)
                                    if options['value_aggregate'] == 'Top 5%':
                                        df = df.groupby(fil['field_name'],sort=False).std().sort_values(by=[options['value_aggregate_field']],ascending=False).head(int(0.05*n))
                                    if options['value_aggregate'] == 'Top 10%':
                                        df = df.groupby(fil['field_name'],sort=False).std().sort_values(by=[options['value_aggregate_field']],ascending=False).head(int(0.1*n))
                                    if options['value_aggregate'] == 'Bottom 5%':
                                        df = df.groupby(fil['field_name'],sort=False).std().sort_values(by=[options['value_aggregate_field']]).head(int(0.05*n))
                                    if options['value_aggregate'] == 'Bottom 10%':
                                        df = df.groupby(fil['field_name'],sort=False).std().sort_values(by=[options['value_aggregate_field']]).head(int(0.1*n))

                            if options['field_aggregate'] == 'Median':
                                if options['value_aggregate'] == 'Select Values':
                                    agg = df.groupby(fil['field_name'],sort=False).median()
                                    condition = agg.isin(options['values'])
                                    df = df[agg[condition].index]

                                if options['value_aggregate'] == 'Ranges':
                                    df_ranges = []
                                    agg = df.groupby(fil['field_name'],sort=False).median()
                                    for x in options['values']:
                                        df_ranges.append(df[agg[self.check_fil_value_condition(agg,'between', x)].index])
                                    df = pd.concat(df_ranges, ignore_index=True)

                                if options['value_aggregate'] == 'Top/Bottom':
                                    if options['value_aggregate'] == 'Top 5':
                                        df = df.groupby(fil['field_name'],sort=False).median().sort_values(by=[options['value_aggregate_field']],ascending=False).head(5)
                                    if options['value_aggregate'] == 'Top 10':
                                        df = df.groupby(fil['field_name'],sort=False).median().sort_values(by=[options['value_aggregate_field']],ascending=False).head(10)
                                    if options['value_aggregate'] == 'Bottom 5':
                                        df = df.groupby(fil['field_name'],sort=False).median().sort_values(by=[options['value_aggregate_field']]).head(5)
                                    if options['value_aggregate'] == 'Bottom 10':
                                        df = df.groupby(fil['field_name'],sort=False).median().sort_values(by=[options['value_aggregate_field']]).head(10)

                                if options['value_aggregate'] == 'Top/Bottom %':
                                    n = len(df.index)
                                    if options['value_aggregate'] == 'Top 5%':
                                        df = df.groupby(fil['field_name'],sort=False).median().sort_values(by=[options['value_aggregate_field']],ascending=False).head(int(0.05*n))
                                    if options['value_aggregate'] == 'Top 10%':
                                        df = df.groupby(fil['field_name'],sort=False).median().sort_values(by=[options['value_aggregate_field']],ascending=False).head(int(0.1*n))
                                    if options['value_aggregate'] == 'Bottom 5%':
                                        df = df.groupby(fil['field_name'],sort=False).median().sort_values(by=[options['value_aggregate_field']]).head(int(0.05*n))
                                    if options['value_aggregate'] == 'Bottom 10%':
                                        df = df.groupby(fil['field_name'],sort=False).median().sort_values(by=[options['value_aggregate_field']]).head(int(0.1*n))
                            
                            if options['field_aggregate'] == 'Mode':  
                                if options['value_aggregate'] == 'Select Values':
                                    agg = df.groupby(fil['field_name'],sort=False).mode()
                                    condition = agg.isin(options['values'])
                                    df = df[agg[condition].index]

                                if options['value_aggregate'] == 'Ranges':
                                    df_ranges = []
                                    agg = df.groupby(fil['field_name'],sort=False).mode()
                                    for x in options['values']:
                                        df_ranges.append(df[agg[self.check_fil_value_condition(agg,'between', x)].index])
                                    df = pd.concat(df_ranges, ignore_index=True)

                                if options['value_aggregate'] == 'Top/Bottom':
                                    if options['value_aggregate'] == 'Top 5':
                                        df = df.groupby(fil['field_name'],sort=False).mode().sort_values(by=[options['value_aggregate_field']],ascending=False).head(5)
                                    if options['value_aggregate'] == 'Top 10':
                                        df = df.groupby(fil['field_name'],sort=False).mode().sort_values(by=[options['value_aggregate_field']],ascending=False).head(10)
                                    if options['value_aggregate'] == 'Bottom 5':
                                        df = df.groupby(fil['field_name'],sort=False).mode().sort_values(by=[options['value_aggregate_field']]).head(5)
                                    if options['value_aggregate'] == 'Bottom 10':
                                        df = df.groupby(fil['field_name'],sort=False).mode().sort_values(by=[options['value_aggregate_field']]).head(10)

                                if options['value_aggregate'] == 'Top/Bottom %':
                                    n = len(df.index)
                                    if options['value_aggregate'] == 'Top 5%':
                                        df = df.groupby(fil['field_name'],sort=False).mode().sort_values(by=[options['value_aggregate_field']],ascending=False).head(int(0.05*n))
                                    if options['value_aggregate'] == 'Top 10%':
                                        df = df.groupby(fil['field_name'],sort=False).mode().sort_values(by=[options['value_aggregate_field']],ascending=False).head(int(0.1*n))
                                    if options['value_aggregate'] == 'Bottom 5%':
                                        df = df.groupby(fil['field_name'],sort=False).mode().sort_values(by=[options['value_aggregate_field']]).head(int(0.05*n))
                                    if options['value_aggregate'] == 'Bottom 10%':
                                        df = df.groupby(fil['field_name'],sort=False).mode().sort_values(by=[options['value_aggregate_field']]).head(int(0.1*n))
                    
                            if options['field_aggregate'] == 'Variance':
                                if options['value_aggregate'] == 'Select Values':
                                    agg = df.groupby(fil['field_name'],sort=False).var()
                                    condition = agg.isin(options['values'])
                                    df = df[agg[condition].index]

                                if options['value_aggregate'] == 'Ranges':
                                    df_ranges = []
                                    agg = df.groupby(fil['field_name'],sort=False).var()
                                    for x in options['values']:
                                        df_ranges.append(df[agg[self.check_fil_value_condition(agg,'between', x)].index])
                                    df = pd.concat(df_ranges, ignore_index=True)

                                if options['value_aggregate'] == 'Top/Bottom':
                                    if options['value_aggregate'] == 'Top 5':
                                        df = df.groupby(fil['field_name'],sort=False).var().sort_values(by=[options['value_aggregate_field']],ascending=False).head(5)
                                    if options['value_aggregate'] == 'Top 10':
                                        df = df.groupby(fil['field_name'],sort=False).var().sort_values(by=[options['value_aggregate_field']],ascending=False).head(10)
                                    if options['value_aggregate'] == 'Bottom 5':
                                        df = df.groupby(fil['field_name'],sort=False).var().sort_values(by=[options['value_aggregate_field']]).head(5)
                                    if options['value_aggregate'] == 'Bottom 10':
                                        df = df.groupby(fil['field_name'],sort=False).var().sort_values(by=[options['value_aggregate_field']]).head(10)

                                if options['value_aggregate'] == 'Top/Bottom %':
                                    n = len(df.index)
                                    if options['value_aggregate'] == 'Top 5%':
                                        df = df.groupby(fil['field_name'],sort=False).var().sort_values(by=[options['value_aggregate_field']],ascending=False).head(int(0.05*n))
                                    if options['value_aggregate'] == 'Top 10%':
                                        df = df.groupby(fil['field_name'],sort=False).var().sort_values(by=[options['value_aggregate_field']],ascending=False).head(int(0.1*n))
                                    if options['value_aggregate'] == 'Bottom 5%':
                                        df = df.groupby(fil['field_name'],sort=False).var().sort_values(by=[options['value_aggregate_field']]).head(int(0.05*n))
                                    if options['value_aggregate'] == 'Bottom 10%':
                                        df = df.groupby(fil['field_name'],sort=False).var().sort_values(by=[options['value_aggregate_field']]).head(int(0.1*n))
                    
                            if options['field_aggregate'] == 'Count':
                                if options['value_aggregate'] == 'Select Values':
                                    agg = df.groupby(fil['field_name'],sort=False).count()
                                    condition = agg.isin(options['values'])
                                    df = df[agg[condition].index]

                                if options['value_aggregate'] == 'Ranges':
                                    df_ranges = []
                                    agg = df.groupby(fil['field_name'],sort=False).count()
                                    for x in options['values']:
                                        df_ranges.append(df[agg[self.check_fil_value_condition(agg,'between', x)].index])
                                    df = pd.concat(df_ranges, ignore_index=True)

                                if options['value_aggregate'] == 'Top/Bottom':
                                    if options['value_aggregate'] == 'Top 5':
                                        df = df.groupby(fil['field_name'],sort=False).count().sort_values(by=[options['value_aggregate_field']],ascending=False).head(5)
                                    if options['value_aggregate'] == 'Top 10':
                                        df = df.groupby(fil['field_name'],sort=False).count().sort_values(by=[options['value_aggregate_field']],ascending=False).head(10)
                                    if options['value_aggregate'] == 'Bottom 5':
                                        df = df.groupby(fil['field_name'],sort=False).count().sort_values(by=[options['value_aggregate_field']]).head(5)
                                    if options['value_aggregate'] == 'Bottom 10':
                                        df = df.groupby(fil['field_name'],sort=False).count().sort_values(by=[options['value_aggregate_field']]).head(10)

                                if options['value_aggregate'] == 'Top/Bottom %':
                                    n = len(df.index)
                                    if options['value_aggregate'] == 'Top 5%':
                                        df = df.groupby(fil['field_name'],sort=False).count().sort_values(by=[options['value_aggregate_field']],ascending=False).head(int(0.05*n))
                                    if options['value_aggregate'] == 'Top 10%':
                                        df = df.groupby(fil['field_name'],sort=False).count().sort_values(by=[options['value_aggregate_field']],ascending=False).head(int(0.1*n))
                                    if options['value_aggregate'] == 'Bottom 5%':
                                        df = df.groupby(fil['field_name'],sort=False).count().sort_values(by=[options['value_aggregate_field']]).head(int(0.05*n))
                                    if options['value_aggregate'] == 'Bottom 10%':
                                        df = df.groupby(fil['field_name'],sort=False).count().sort_values(by=[options['value_aggregate_field']]).head(int(0.1*n))
                    
                            if options['field_aggregate'] == 'Count Distinct':
                                if options['value_aggregate'] == 'Select Values':
                                    agg = df.groupby(fil['field_name'],sort=False).nunique()
                                    condition = agg.isin(options['values'])
                                    df = df[agg[condition].index]

                                if options['value_aggregate'] == 'Ranges':
                                    df_ranges = []
                                    agg = df.groupby(fil['field_name'],sort=False).nunique()
                                    for x in options['values']:
                                        df_ranges.append(df[agg[self.check_fil_value_condition(agg,'between', x)].index])
                                    df = pd.concat(df_ranges, ignore_index=True)

                                if options['value_aggregate'] == 'Top/Bottom':
                                    if options['value_aggregate'] == 'Top 5':
                                        df = df.groupby(fil['field_name'],sort=False).nunique().sort_values(by=[options['value_aggregate_field']],ascending=False).head(5)
                                    if options['value_aggregate'] == 'Top 10':
                                        df = df.groupby(fil['field_name'],sort=False).nunique().sort_values(by=[options['value_aggregate_field']],ascending=False).head(10)
                                    if options['value_aggregate'] == 'Bottom 5':
                                        df = df.groupby(fil['field_name'],sort=False).nunique().sort_values(by=[options['value_aggregate_field']]).head(5)
                                    if options['value_aggregate'] == 'Bottom 10':
                                        df = df.groupby(fil['field_name'],sort=False).nunique().sort_values(by=[options['value_aggregate_field']]).head(10)

                                if options['value_aggregate'] == 'Top/Bottom %':
                                    n = len(df.index)
                                    if options['value_aggregate'] == 'Top 5%':
                                        df = df.groupby(fil['field_name'],sort=False).nunique().sort_values(by=[options['value_aggregate_field']],ascending=False).head(int(0.05*n))
                                    if options['value_aggregate'] == 'Top 10%':
                                        df = df.groupby(fil['field_name'],sort=False).nunique().sort_values(by=[options['value_aggregate_field']],ascending=False).head(int(0.1*n))
                                    if options['value_aggregate'] == 'Bottom 5%':
                                        df = df.groupby(fil['field_name'],sort=False).nunique().sort_values(by=[options['value_aggregate_field']]).head(int(0.05*n))
                                    if options['value_aggregate'] == 'Bottom 10%':
                                        df = df.groupby(fil['field_name'],sort=False).nunique().sort_values(by=[options['value_aggregate_field']]).head(int(0.1*n))
                        
                        if options['mode'] == 'range':

                            if options['field_aggregate'] == 'Sum':
                                agg = df[fil['field_name']].sum()
                                df = df[agg[self.check_filter_value_condition(agg, options['rangeBy'], options['rangeValue'])].index]

                            if options['field_aggregate'] == 'Max':
                                agg = df[fil['field_name']].max()
                                df = df[agg[self.check_filter_value_condition(agg, options['rangeBy'], options['rangeValue'])].index]
                            
                            if options['field_aggregate'] == 'Min':
                                agg = df[fil['field_name']].min()
                                df = df[agg[self.check_filter_value_condition(agg, options['rangeBy'], options['rangeValue'])].index]                 
                            
                            if options['field_aggregate'] == 'Average':
                                agg = df[fil['field_name']].mean()
                                df = df[agg[self.check_filter_value_condition(agg, options['rangeBy'], options['rangeValue'])].index]                  
                            
                            if options['field_aggregate'] == 'Std Dev':
                                agg = df[fil['field_name']].std()
                                df = df[agg[self.check_filter_value_condition(agg, options['rangeBy'], options['rangeValue'])].index]                 
                            
                            if options['field_aggregate'] == 'Median':
                                agg = df[fil['field_name']].median()
                                df = df[agg[self.check_filter_value_condition(agg, options['rangeBy'], options['rangeValue'])].index]
                            
                            if options['field_aggregate'] == 'Mode':
                                agg = df[fil['field_name']].mode()
                                df = df[agg[self.check_filter_value_condition(agg, options['rangeBy'], options['rangeValue'])].index]                   
                            
                            if options['field_aggregate'] == 'Variance':
                                agg = df[fil['field_name']].var()
                                df = df[agg[self.check_filter_value_condition(agg, options['rangeBy'], options['rangeValue'])].index]                  
                            
                            if options['field_aggregate'] == 'Count':
                                agg = df[fil['field_name']].count()
                                df = df[agg[self.check_filter_value_condition(agg, options['rangeBy'], options['rangeValue'])].index]                   
                            
                            if options['field_aggregate'] == 'Count Distinct':
                                agg = df[fil['field_name']].nunique()
                                df = df[agg[self.check_filter_value_condition(agg, options['rangeBy'], options['rangeValue'])].index]
                    
                    if options['type'] in ['DateField','DateTimeField']:
                        if options['mode'] == 'pick':
                            if options['field_aggregate'] == 'No Aggregate':
                                
                                if options['value_aggregate'] == 'Date&Time':
                                    condition = df[fil['field_name']].map(lambda x: x.strftime('%-d %b %Y %H %M %S')).isin(options['values'])
                                    df = df[condition]
                                
                                if options['value_aggregate'] == 'Year':
                                    condition = df[fil['field_name']].map(lambda x: x.strftime("%Y")).isin(options['values'])
                                    df = df[condition]
                                
                                if options['value_aggregate'] == 'Quarter':
                                    df['temp'] = pd.to_datetime(df[fil['field_name']])
                                    # condition = df[fil['field_name']].map(lambda x: 'Q{} {}'.format(pd.DatetimeIndex(x).quarter,x.strftime('%Y'))).isin(options['values'])
                                    condition = df['temp'].map(lambda x: 'Q{} {}'.format(x.quarter,x.year)).isin(options['values'])
                                    df = df.drop(['temp'],axis=1)
                                    df = df[condition]
                                
                                if options['value_aggregate'] == 'Month':
                                    condition = df[fil['field_name']].map(lambda x: x.strftime('%b %Y')).isin(options['values'])
                                    df = df[condition]
                                
                                if options['value_aggregate'] == 'Weeks':
                                    condition = df[fil['field_name']].map(lambda x: x.strftime('W%U %Y')).isin(options['values'])
                                    df = df[condition]
                                
                                if options['value_aggregate'] == 'Date':
                                    condition = df[fil['field_name']].map(lambda x: x.strftime('%-d %b %Y')).isin(options['values'])
                                    df = df[condition]

                            if options['field_aggregate'] == 'Seasonal':
                                
                                if options['value_aggregate'] == 'Quarter':
                                    df['temp'] = pd.to_datetime(df[fil['field_name']])
                                    # condition = df[fil['field_name']].map(lambda x: 'Q{}'.format(pd.DatetimeIndex(x))).isin(options['values'])
                                    condition = df['temp'].map(lambda x: 'Q{} {}'.format(x.quarter,x.year)).isin(options['values'])
                                    df = df.drop(['temp'],axis=1)
                                    df = df[condition]
                                
                                if options['value_aggregate'] == 'Month':
                                    condition = df[fil['field_name']].map(lambda x: x.strftime('%b')).isin(options['values'])
                                    df = df[condition]
                                
                                if options['value_aggregate'] == 'Weeks':
                                    condition = df[fil['field_name']].map(lambda x: x.strftime('Week %U')).isin(options['values'])
                                    df = df[condition]
                                
                                if options['value_aggregate'] == 'Week Day':
                                    condition = df[fil['field_name']].map(lambda x: x.strftime('%a')).isin(options['values'])
                                    df = df[condition]
                                
                                if options['value_aggregate'] == 'Day of Month':
                                    condition = df[fil['field_name']].map(lambda x: x.strftime('%-d')).isin(options['values'])
                                    df = df[condition]
                                
                                if options['value_aggregate'] == 'Hour':
                                    condition = df[fil['field_name']].map(lambda x: x.strftime('%-H')).isin(options['values'])
                                    df = df[condition]

                            if options['field_aggregate'] == 'Relative':

                                pass

                        else:
                            df = df[self.check_filter_value_condition(df[fil['field_name']], options['rangeBy'], options['rangeValue'])]
                
            field = data['field']
            value = data['value']
            group_by = data['groupBy']
            # print("down")
            try:
                # print("hi")
                await self.graphDataGenerate(df,report_type, field, value, group_by)
            except Exception as e:
                print(e)
        except Exception as e:
            print(e)
            pass

class FilterConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):
        if self.scope['user'] == None:
            await self.close(1011)
        
        self.group_name = '{}_filter_create'.format(self.scope['user'].organization_id)

        await self.channel_layer.group_add(self.group_name, self.channel_name)

        await self.accept()

    def get_object(self,dataset_id,user):
        try:
            return Dataset.objects.filter(userId = user.username).get(dataset_id = dataset_id)

        except Dataset.DoesNotexist:
            raise Http404

    async def dataFrameGenerate(self, request_data, user):
        data = []
        r1 = redis.StrictRedis(host='127.0.0.1', port=6379, db=1)
        dataset_id = request_data['dataset_id'] or request_data['worksheet']
        model_fields = []
        if r1.exists('{}.{}'.format(user.organization_id,dataset_id)) != 0:
            df = await sync_to_async(pickle.loads)(zlib.decompress(r1.get("{}.{}".format(user.organization_id,dataset_id))))
            model_fields = [(k.decode('utf8').replace("'", '"'),v.decode('utf8').replace("'", '"')) for k,v in r1.hgetall('{}.fields'.format(dataset_id)).items()]

        else:
            EXPIRATION_SECONDS = 600
            r = redis.Redis(host='127.0.0.1', port=6379, db=0)
            s3_resource= boto3.resource('s3')
            if request_data['op_table'] == 'dataset':
                dataset = await database_sync_to_async(self.get_object)(dataset_id,user)
                model = dataset.get_django_model()
                model_fields = [(f.name, f.get_internal_type()) for f in model._meta.get_fields() if f.name is not 'id']
                r = redis.Redis(host='127.0.0.1', port=6379, db=0)
                try:
                    s3_resource.Object('pragyaam-dash-dev','{}/{}.rdb'.format(user.organization_id,str(dataset.dataset_id))).download_file(f'/tmp/{dataset.dataset_id}.rdb')
                    load_data('/tmp/{}.rdb'.format(dataset.dataset_id),'127.0.0.1',6379,0)
                     
                except Exception as e:
                    print(e)
                for x in range(1,r.dbsize()+1):
                    if r.get('edit.{}.{}.{}'.format(user.organization_id, dataset.dataset_id, str(x))) != None:
                        data.append({k.decode('utf8').replace("'", '"'): v.decode('utf8').replace("'", '"') for k,v in r.hgetall('edit.{}.{}.{}'.format(user.organization_id, dataset_id, str(x))).items()})
                    else:
                        data.append({k.decode('utf8').replace("'", '"'): v.decode('utf8').replace("'", '"') for k,v in r.hgetall('{}.{}.{}'.format(user.organization_id, dataset_id, str(x))).items()})
                    
                r.flushdb(True) 
                os.remove('/tmp/{}.rdb'.format(dataset_id))
            else:
                with connections['rds'].cursor() as cursor:
                    cursor.execute('SELECT database_name from organizations where organization_id="{}"'.format(user.organization_id))
                    database_name = cursor.fetchone()[0]
                if user.organization_id not in connections.databases:
                    connections.databases[user.organization_id] = {
                        'ENGINE' : 'django.db.backends.mysql',
                        'NAME' : database_name,
                        'OPTIONS' : {
                            'read_default_file' : os.path.join(BASE_DIR, 'cred_dynamic.cnf'),
                        }
                    }
                with connections[user.organization_id].cursor() as cursor:
                    await database_sync_to_async(cursor.execute)('select SQL_NO_CACHE * from `{}`'.format(dataset_id))
                    table_data = await sync_to_async(dictfetchall)(cursor)
                    table_model = get_model(dataset_id,Dataset._meta.app_label,cursor, 'READ')
                    model_fields = [(f.name, f.get_internal_type()) for f in table_model._meta.get_fields() if f.name is not 'id']
                    GeneralSerializer.Meta.model = table_model

                    dynamic_serializer = GeneralSerializer(table_data,many = True)
                    del(table_model)
                
                del connections[user.organization_id]
        
                serializer_data = dynamic_serializer.data
                p = r.pipeline()
                id_count = 0
                for a in serializer_data:
                    id_count +=1
                    p.hmset('{}.{}.{}'.format(user.organization_id, dataset_id ,str(id_count)), {k:v for k,v in dict(a).items() if v is not None})
                try:
                    await sync_to_async(p.execute)()
                except Exception as e:        
                    print(e)
                data = []
                for x in range(1,id_count+1):
                    data.append({k.decode('utf8').replace("'", '"'): v.decode('utf8').replace("'", '"') for k,v in r.hgetall('{}.{}.{}'.format(user.organization_id, dataset_id, str(x))).items()})
    
                r.flushdb(True)
    
            df = await sync_to_async(pd.DataFrame)(data)
            r1.setex("{}.{}".format(user.organization_id,dataset_id), EXPIRATION_SECONDS, zlib.compress( pickle.dumps(df)))
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
                    df[x[0]] = df[x[0]].fillna(0,downcast='infer')
                if x[1] == 'IntegerField':
                    df[x[0]] = df[x[0]].apply(pd.to_numeric,errors='coerce')
                    df[x[0]] = df[x[0]].fillna(0,downcast='infer')
                if x[1] == 'CharField' or x[1] == 'TextField':
                    df = df.astype({ x[0] : 'object'})
                    df[x[0]] = df[x[0]].fillna('')
                if x[1] == 'DateField':
                    df = df.astype({ x[0] : 'datetime64'})
                    df[x[0]] = df[x[0]].fillna(arrow.get('01-01-1990').datetime)
           
        return df,model_fields

    async def filter_options_generate(self,request_data):
        
        df,model_fields = await self.dataFrameGenerate(request_data,self.scope['user'])

        if request_data['operationRequested'] == 'fields':
            await self.send_json({ 'type' : 'fieldsList','fields' : model_fields })

        if request_data['operationRequested'] == 'field_options':
            if request_data['mode'] == 'pick':

                if df[request_data['field']].dtypes == 'object':
                    if request_data['field_aggregate'] == 'No Aggregate':
                        await self.send(json.dumps({ 'type' : 'fieldOptions', 'data' : df[request_data['field']].unique()},cls=NumpyEncoder))
                    if request_data['field_aggregate'] == 'Count':
                        await self.send_json({ 'type' : 'fieldOptions', 'data' : df.groupby(request_data['field'])[request_data['field']].count().tolist()})
                    if request_data['field_aggregate'] == 'Count Distinct':
                        await self.send_json({ 'type' : 'fieldOptions', 'data' : df.groupby(request_data['field'])[request_data['field']].nunique().tolist()})

                elif df[request_data['field']].dtypes == 'float64' or df[request_data['field']].dtypes == 'int64':
                    if request_data['field_aggregate'] == 'No Aggregate':
                        await self.send(json.dumps({ 'type' : 'fieldOptions', 'data' : df[request_data['field']].unique()},cls=NumpyEncoder))
                    if request_data['field_aggregate'] == 'Sum':
                        await self.send_json({ 'type' : 'fieldOptions', 'data' : df.groupby(request_data['field'])[request_data['field']].sum().tolist() })
                    if request_data['field_aggregate'] == 'Max':
                        await self.send_json({ 'type' : 'fieldOptions', 'data' : df.groupby(request_data['field'])[request_data['field']].max().tolist() })
                    if request_data['field_aggregate'] == 'Min':
                        await self.send_json({ 'type' : 'fieldOptions', 'data' : df.groupby(request_data['field'])[request_data['field']].min().tolist() })
                    if request_data['field_aggregate'] == 'Average':
                        await self.send_json({ 'type' : 'fieldOptions', 'data' : df.groupby(request_data['field'])[request_data['field']].mean().tolist() })
                    if request_data['field_aggregate'] == 'Std_dev':
                        await self.send_json({ 'type' : 'fieldOptions', 'data' : df.groupby(request_data['field'])[request_data['field']].std().tolist() })
                    if request_data['field_aggregate'] == 'Median':
                        await self.send_json({ 'type' : 'fieldOptions', 'data' : df.groupby(request_data['field'])[request_data['field']].median().tolist() })
                    if request_data['field_aggregate'] == 'Mode':
                        await self.send_json({ 'type' : 'fieldOptions', 'data' : df.groupby(request_data['field'])[request_data['field']].mode().tolist() })
                    if request_data['field_aggregate'] == 'Var':
                        await self.send_json({ 'type' : 'fieldOptions', 'data' : df.groupby(request_data['field'])[request_data['field']].var().tolist() })
                    if request_data['field_aggregate'] == 'Count':
                        await self.send_json({ 'type' : 'fieldOptions', 'data' : df.groupby(request_data['field'])[request_data['field']].count().tolist() })
                    if request_data['field_aggregate'] == 'Count distinct':
                        await self.send_json({ 'type' : 'fieldOptions', 'data' : df.groupby(request_data['field'])[request_data['field']].nunique().tolist() })
                
                elif df[request_data['field']].dtypes == 'datetime64[ns]':
                    if request_data['field_aggregate'] == 'Seasonal' or request_data['field_aggregate'] == 'Relative' or  request_data['field_aggregate'] == 'No Aggregate':
                        if request_data['value_aggregate'] == 'Year':
                            await self.send(json.dumps({ 'type' : 'fieldOptions', 'data' : df[request_data['field']].apply(lambda x: x.strftime('%Y')).unique()},cls=NumpyEncoder))
                        if request_data['value_aggregate'] == 'Quarter':
                            df[request_data['field']] = pd.to_datetime(df[request_data['field']])
                            await self.send_json({ 'type' : 'fieldOptions', 'data' : df[request_data['field']].apply(lambda x: 'Q{} {}'.format(x.quarter,x.year)).unique().tolist()})
                            # await self.send(json.dumps({ 'type' : 'fieldOptions', 'data' : df[request_data['field']].apply(lambda x: 'Q{} {}'.format((quarter(x.strftime('%m'))),x.strftime('%Y'))).unique()},cls=NumpyEncoder))
                            # await self.send(json.dumps({ 'type' : 'fieldOptions', 'data' : df[request_data['field']].apply(lambda x: 'Q{} {}'.format(datetime.datetime.strptime(x, '%Y-%m-%d %H:%M:%S.%f').quarter,x.strftime('%Y'))).unique()},cls=NumpyEncoder))                   
                        if request_data['value_aggregate'] == 'Month':
                            await self.send(json.dumps({ 'type' : 'fieldOptions', 'data' : df[request_data['field']].apply(lambda x: x.strftime('%b %Y')).unique()},cls=NumpyEncoder))
                        if request_data['value_aggregate'] == 'Weeks':
                            await self.send(json.dumps({ 'type' : 'fieldOptions', 'data' : df[request_data['field']].apply(lambda x: x.strftime('W%U %Y')).unique()},cls=NumpyEncoder))
                        if request_data['value_aggregate'] == 'Date':
                            await self.send(json.dumps({ 'type' : 'fieldOptions', 'data' : df[request_data['field']].apply(lambda x: x.strftime('%-d %b %Y')).unique()},cls=NumpyEncoder))
                        if request_data['field_aggregate'] == 'Date&Time':
                            await self.send(json.dumps({ 'type' : 'fieldOptions', 'data' : df[request_data['field']].apply(lambda x: x.strftime('%-d %b %Y %H %M %S')).unique()},cls=NumpyEncoder))
                        if request_data['value_aggregate'] == 'Week Day':
                            df['temp'] = pd.to_datetime(df[request_data['field']])
                            data = df['temp'].map(lambda x: x.strftime('%a')).unique()
                            await self.send(json.dumps({ 'type' : 'fieldOptions', 'data': data.tolist()}))
                        if request_data['value_aggregate'] == 'Day of Month':
                            df['temp'] = pd.to_datetime(df[request_data['field']])
                            data = df['temp'].map(lambda x: x.strftime('%-d')).unique()
                            await self.send(json.dumps({ 'type' : 'fieldOptions', 'data': data.tolist()}))
                    if request_data['value_aggregate'] == 'Hour':
                            df['temp'] = pd.to_datetime(df[request_data['field']])
                            data = df['temp'].map(lambda x: x.strftime('%-H')).unique()
                            await self.send(json.dumps({ 'type' : 'fieldOptions', 'data': data.tolist()}))
                

            else:
                await self.send(json.dumps({ 'type' : 'fieldRange', 'data' : { 'min' : df[request_data['field']].min(), 'max' : df[request_data['field']].max() }}, sort_keys=True, indent=1, cls=DjangoJSONEncoder))

    async def receive_json(self,data):
        await self.filter_options_generate(data)

class DashboardConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):
        await self.channel_layer.group_add('dashboard', self.channel_name)
        await self.accept()
    
    async def disconnect(self,close_code):
        await self.channel_layer.group_discard('dashboard', self.channel_name)
    
    async def receive_json(self,data):
        
        command = data["command"]

        try:
            if command == 'group_by':
                await self.group_by(data["data"])
        
        except ClientError as e:
            await self.send_json({"error" : e})
        
    async def group_by(self,data):
        pass
