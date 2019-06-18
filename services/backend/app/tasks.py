from django.core.management import call_command
from django.db import connections
from app.utils import get_model,dictfetchall  
from celery.task.schedules import crontab
from celery.decorators import task
from celery.utils.log import get_task_logger

from app.models import Dataset,Table,Join
from app.serializers import DynamicFieldsModelSerializer

import simplejson as json
import os
import redis
import shutil
import subprocess
import datetime
import timestring

logger = get_task_logger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_data(location, host, port, db):
    subprocess.call('rdb --c protocol {} | redis-cli -h {} -p {} -n {} --pipe'.format(location,host,port,db), shell=True)

def check_equal(field_1,type_1,field_2,type_2):

    if type_1 == 'DateField' and type_2 == 'DateField':
        return timestring.Date(field_1) == timestring.Date(field_2)
    else:
        return field_1 == field_2

@task
def datasetRefresh(organization_id,dataset_id):
    id_count = 0
    logger.info('hii')
    with connections['rds'].cursor() as cursor:
        cursor.execute('select database_name from organizations where organization_id="{}";'.format(organization_id))
        database_name = cursor.fetchone()
    r = redis.Redis(host='127.0.0.1', port=6379, db=0)
    dataset = Dataset.objects.get(dataset_id = dataset_id)
    if dataset.mode == 'SQL':
        
        r.config_set('dbfilename', '{}.rdb'.format(organization_id))
        r.config_rewrite()
        try:
            load_data(os.path.join(BASE_DIR, '{}.rdb'.format(organization_id)),'127.0.0.1',6379,0)
        except:
            pass
        if organization_id not in connections.databases:
            connections.databases[profile.organization_id] = {
                'ENGINE' : 'django.db.backends.mysql',
                'NAME' : database_name,
                'OPTIONS' : {
                    'read_default_file' : os.path.join(BASE_DIR, 'cred_dynamic.cnf'),
                }
            }
        with connections[organization_id].cursor() as cur:
            cur.execute(dataset.sql)
            dataset_data = dictfetchall(cur)
            serializer = GeneralSerializer(data = dataset_data, many = True)
        table_data = serializer.data
        p = r.pipeline()
        for a in table_data:
            id_count +=1
            p.hmset('{}.{}.{}'.format(organization_id, dataset_id ,str(id_count)), {**dict(a)})
        try:
            p.execute()
        except Exception as e:        
            logger.info(e)
        del connections[organization_id]
        for x in range(1,id_count+1):
            for c in model_fields:
                r.hsetnx('{}.{}.{}'.format(organization_id, dataset_id ,str(x)),c[0],"")
        r.save()
        dataset.last_refreshed = datetime.datetime.now()
        dataset.save()
        try:
            shutil.copy(os.path.join('/var/lib/redis/6379', '{}.rdb'.format(organization_id)),BASE_DIR)
        except Exception as e:
            logger.info(e)
        r.flushdb()
        r.config_set('dbfilename', 'dump.rdb')
        r.config_rewrite()   
    else:
        logger.info('check1')
        tables = Table.objects.filter(dataset = dataset)
        joins = Join.objects.filter(dataset =  dataset) 
        model = dataset.get_django_model()
        model_fields = [(f.name,f.get_internal_type()) for f in model._meta.get_fields() if f.name is not 'id']
        model_data = []
        data = []  
        r.config_set('dbfilename', '{}.rdb'.format(organization_id))
        r.config_rewrite()
        try:
            load_data(os.path.join(BASE_DIR, '{}.rdb'.format(organization_id)),'127.0.0.1',6379,0)
        except Exception as e:
            logger.info(e)
            pass
        
        for t in tables:
            if organization_id not in connections.databases:
                connections.databases[organization_id] = {
                    'ENGINE' : 'django.db.backends.mysql',
                    'NAME' : database_name[0],
                    'OPTIONS' : {
                        'read_default_file' : os.path.join(BASE_DIR, 'cred_dynamic.cnf'),
                    }
                }
            with connections[organization_id].cursor() as cursor:
                cursor.execute('select SQL_NO_CACHE * from `%s`'%(t.key))
                table_data = dictfetchall(cursor)

                table_model = get_model(t.key,model._meta.app_label,cursor, 'READ')
                DynamicFieldsModelSerializer.Meta.model = table_model                
                dynamic_serializer = DynamicFieldsModelSerializer(table_data,many = True,fields = set([x[0] for x in model_fields]))
                model_data.append({ 'name' : t.key,'data' : dynamic_serializer.data})
            del connections[organization_id]
            call_command('makemigrations',interactive=False)
            call_command('migrate', database = 'default',fake = True,interactive=False)
             
        join_model_data=[]
        p = r.pipeline()

        if joins.count() == 0:
            for x in model_data:
                for a in x['data']:
                    id_count +=1
                    p.hmset('{}.{}.{}'.format(organization_id, dataset.dataset_id ,str(id_count)),{**dict(a)})

        else:
            for join in joins:

                logger.info(join.type)
                field_1_type = ''
                field_2_type = ''
                for x in model_fields:
                    if x[0] == join.field_1 and field_1_type == '':
                        field_1_type = x[1]
                    if x[0] == join.field_2 and field_2_type == '':
                        field_2_type = x[1]
                if join.type == 'Inner-Join':
                    for d in model_data:
                        if d['name'] == join.worksheet_1:
                            
                            for x in d['data']:
                                check = []
                                for a in model_data:
                                    if a['name'] == join.worksheet_2:
                                        X = dict(x)
                                        for c in a['data']:
                                            C = dict(c)
                                            if check_equal(C[join.field_2],field_2_type,X[join.field_1],field_1_type):
                                                check.append(C)
                                        if check != []:
                                            for z in check:
                                                id_count += 1
                                                p.hmset('{}.{}.{}'.format(organization_id, dataset.dataset_id ,str(id_count)),{**X,**z}) 
                                        break
                    
                    continue
                if join.type == 'Left-Join':
                    for d in model_data:
                        if d['name'] == join.worksheet_1:
                            
                            for x in d['data']:
                                check = []
                                for a in model_data:
                                    if a['name'] == join.worksheet_2:
                                        X = dict(x)
                                        for c in a['data']:
                                            C = dict(c)
                                            if check_equal(C[join.field_2],field_2_type,X[join.field_1],field_1_type):
                                                check.append(C)
                                        if check == []:
                                            id_count += 1
                                            p.hmset('{}.{}.{}'.format(organization_id, dataset.dataset_id ,str(id_count)), {**X})
                                        else:
                                            for z in check:
                                                id_count += 1
                                                p.hmset('{}.{}.{}'.format(organization_id, dataset.dataset_id ,str(id_count)),{**X,**z})
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
                                            if check_equal(C[join.field_1],field_1_type,X[join.field_2],field_2_type):
                                                check.append(C)
                                        if check == []:
                                            id_count += 1
                                            p.hmset('{}.{}.{}'.format(organization_id, dataset.dataset_id ,str(id_count)), {**X})
                                        else:
                                            for z in check:
                                                id_count += 1
                                                p.hmset('{}.{}.{}'.format(organization_id, dataset.dataset_id ,str(id_count)), {**X,**z})
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
                                            if check_equal(C[join.field_2],field_2_type,X[join.field_1],field_1_type):
                                                check.append(C)
                                        
                                        for z in check:
                                            id_count += 1
                                            p.hmset('{}.{}.{}'.format(organization_id, dataset.dataset_id ,str(id_count)), {**X,**z})
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
                                if check_equal(C[join.field_2],field_2_type,X[join.field_1],field_1_type):
                                    f = 1
                                    break
                            if f == 0:
                                id_count+=1
                                p.hmset('{}.{}.{}'.format(organization_id, dataset.dataset_id ,str(id_count)), {**X})

                    continue
        try:
            p.execute()
        except Exception as e:
            logger.info(e)
    
        r.save()
        try:
            shutil.copy(os.path.join('/var/lib/redis/6379', '{}.rdb'.format(organization_id)),BASE_DIR)
        except Exception as e:
            logger.info(e)
        r.flushdb()
        r.config_set('dbfilename', 'dump.rdb')
        r.config_rewrite()
    logger.info("Complete")