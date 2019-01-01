from django.shortcuts import render
from django.contrib.auth.models import User

from app.models import Dataset,Field,Setting,Table,Join,Profile,Report
from app.serializers import DatasetSeraializer,FieldSerializer,SettingSerializer,GeneralSerializer,TableSerializer,JoinSerializer,DynamicFieldsModelSerializer,ProfileSerializer,ReportSerializer
from app.utils import get_model,dictfetchall

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import Http404
from rest_framework import permissions
from rest_framework import viewsets,generics

from django.contrib import admin
from django.core.management import call_command
from django.db import connections
from django.core.cache import caches
from django.db.migrations.recorder import MigrationRecorder
from django.core.management.commands import sqlmigrate

import collections
import json
from django_pandas.io import read_frame
# import matplotlib.pyplot as plt
# import mpld3
import numpy as np
import random

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
            dataset = Dataset.objects.get(name = data['name'])
            for f in data['fields']:
                field_serializer = FieldSerializer(data = f)
                if field_serializer.is_valid():
                    field_serializer.save(dataset = dataset)
                for s in f['settings']:
                    field = Field.objects.filter(dataset__name = data['name']).filter(worksheet = f['worksheet']).get(name = f['name'])
                    print(s)
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
            call_command('migrate',fake = True)
            last_migration = MigrationRecorder.Migration.objects.latest('id')
            last_migration_object = sqlmigrate.Command()
            last_migration_sql = last_migration_object.handle(app_label = last_migration.app, migration_name = last_migration.name,database = 'default', backwards = False)
            print(last_migration_sql)
            for item in last_migration_sql.split('\n'):
                if item.split(' ')[0] == 'CREATE':
                    with connections['default'].cursor() as cursor:
                        cursor.execute(item)
            return Response({'message' : 'success'},status=status.HTTP_201_CREATED)
        return Response(serializer.errors,status = status.HTTP_400_BAD_REQUEST)


class DatasetDetail(APIView):

    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    def get_object(self,dataset_id,user):
        try:
            return Dataset.objects.filter(profile = user.profile).get(dataset_id = dataset_id)

        except Dataset.DoesNotexist:
            return Http404


    def post(self,request):
        
        dataset = self.get_object(request.data['dataset_id'],request.user)
        model = dataset.get_django_model()
        GeneralSerializer.Meta.model = model
        print(model)
        
        if request.data['view_mode'] == 'view':
            data_subset = model.objects.all()
            data_serializer = GeneralSerializer(data_subset,many = True)
            return Response(data_serializer.data,status=status.HTTP_200_OK)
        else:
            tables = Table.objects.filter(dataset = dataset)
            joins = Join.objects.filter(dataset =  dataset)
            model_fields = [f.name for f in model._meta.get_fields() if f.name is not 'id']
            print(model_fields)
            model_data = []
            data = []
            model.objects.all().delete()

            for t in tables:
                with connections['default'].cursor() as cursor:
                    cursor.execute('select * from "%s"'%(t.name))
                    table_data = dictfetchall(cursor)
                    # print(table_data)

                    table_model = get_model(t.name,model._meta.app_label,cursor)
                    DynamicFieldsModelSerializer.Meta.model = table_model
                    
                    context = {
                        "request" : request,
                    }
                    
                    dynamic_serializer = DynamicFieldsModelSerializer(table_data,many = True,fields = set(model_fields))
                    # print(dynamic_serializer.data)
                    model_data.append({ 'name' : t.name,'data' : dynamic_serializer.data})
                    call_command('makemigrations')
                    call_command('migrate',fake = True)
                    # del table_model
                    # try:
                    #     del caches[model._meta.app_label][t.name]
                    # except KeyError:
                    #     pass
            join_model_data=[]

            id_count = 0
            
            if joins.count() == 0:
                print('hi2')
                for x in model_data:
                    for a in x['data']:
                        print(a)
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
            print(json.dumps(join_model_data))
            serializer = GeneralSerializer(data = join_model_data,many = True)
            if serializer.is_valid(raise_exception = True):
                print('hi')
                serializer.save()
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
        dataset = request.data['dataset']
        dataset_detail = self.get_object(dataset,request.user)
        model = dataset_detail.get_django_model()
        data = model.objects.all()
        print(data)
        df = read_frame(data)

        if report_type == 'horizontalBar':
            X_field = request.data['options']['Y_field']
            Y_field = request.data['options']['X_field']
            group_by = request.data['options']['group_by']
            measure_operation = request.data['options']['measure_operation']

            all_fields = []
            all_fields.extend([X_field,Y_field])
            if len(group_by) > 0:
                all_fields.extend([group_by])
            df_required = df.loc[:,all_fields]
            df_required = df.loc[:,df.columns.isin(all_fields)]
            # all_fields = []
            # all_fields.extend([Y_field])
            # all_fields.extend(X_field)
            # df_required = df.loc[:,all_fields]
            # df_required = df_required.dropna()
            # print(df_required)
            # plt.rcdefaults()
            # fig,ax = plt.subplots()
            # width = 0.35
            # y_pos = np.arange(len(np.unique(df_required.loc[:,Y_field])))
            # nx = len(X_field)
            # i = -(nx-1)*width/2
            # x = 0
            # while i <= (nx-1)*width/2:
            #     ax.barh(y_pos-i,df_required.loc[:,X_field[x]],width,align='center',color = 'green',label = X_field[x])
            #     i = i + width
            #     x = x + 1

            df_num = df_required.select_dtypes(exclude = [np.number])
            all_columns = list(df_num)
            all_columns.remove(X_field)
            df_num[all_columns] = df_num[all_columns].astype('category')
            df_num[all_columns] = df_num[all_columns].apply(lambda x: x.cat.codes+1)
            df_required.update(df_num)
            
            # ax.invert_yaxis()
            # label = 'fields-'
            # ax.set_ylabel(Y_field)
            # for x in X_field:
            #     label = label + x
            # ax.set_xlabel(label)
            # ax.legend()
            # # plt.show()

            data = {
                'labels' : np.unique(np.array(df_required.loc[:,X_field])),
                'datasets' : []
            }

            add = []
            curr = []
            op_dict = collections.defaultdict(list)

            if len(group_by) > 0:
                if measure_operation == "LAST":

                    for x in df_required.groupby([group_by]).groups.keys():
                        
                        df_group = df_required.groupby([group_by]).get_group(x)
                        curr.append(np.array(df_group[[X_field,Y_field,group_by]]))

                        for d in np.array(df_group.loc[:,X_field]):
                            if d not in op_dict.keys():
                                op_dict[d] = []

                    colors = random.sample(set(self.color_choices),len(df_required.groupby([group_by]).groups.keys()))

                    for x in curr:
                        
                        for l in data['labels']:
                            op_dict[l] = []

                        group_by = ""

                        for c in x:
                            
                            
                            group_by = c[2]

                            if c[1] not in op_dict[c[0]]:
                                
                                op_dict[c[0]].append(c[1])

                        tl = 0        
                        
                        for d in data['labels']:
                            if len(op_dict[d]) > tl:
                                tl = len(op_dict[d])

                        for key,value in op_dict.items():
                            if len(value) < tl:
                                t = len(value)
                                while t < tl:
                                    op_dict[key].append(None)
                                    t += 1
                        
                        k = 0
                
                        total_length = 0

                        for d in data['labels']:
                            if len(op_dict[d]) > total_length:
                                total_length = len(op_dict[d])

                        color_chosen = random.choice(colors)    
                        while k < total_length:
                            
                            new_add = []
                            for d in data['labels']:
                                new_add.append(op_dict[d][k])
                            
                            data['datasets'].append({ 'label' : [group_by], 'backgroundColor' : color_chosen, 'data' : new_add })
                            k += 1
                            print(colors)
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "SUM":
                    print(df_required.group_by([group_by, X_field, Y_field])[Y_field].sum())

                
                
            else:
                if measure_operation == "LAST":

                    curr = []

                    curr.extend(df_required.loc[:,[X_field,Y_field]].values)

                    for c in curr:
                        if c[1] not in op_dict[c[0]]:
                            op_dict[c[0]].append(c[1])
                
                    tl = 0        
                        
                    for d in data['labels']:
                        if len(op_dict[d]) > tl:
                            tl = len(op_dict[d])

                    color_count = 0
                    for key,value in op_dict.items():
                        color_count += 1
                        if len(value) < tl:
                            t = len(value)
                            while t < tl:
                                op_dict[key].append(None)
                                t += 1
                    if color_count < len(self.color_choices):            
                        colors = random.sample(set(self.color_choices),color_count)
                    else:
                        colors = self.color_choices                        
                    k = 0
            
                    total_length = 0

                    for d in data['labels']:
                        if len(op_dict[d]) > total_length:
                            total_length = len(op_dict[d])

                    
                    while k < total_length:
                        new_add = []
                        for d in data['labels']:
                            new_add.append(op_dict[d][k])
                            
                        data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })
                        k += 1
                    
                
                if measure_operation == "SUM":
                    print(df_required.group_by([X_field, Y_field])[Y_field].sum())
            
            
            

            return Response({ 'data' : data }, status = status.HTTP_200_OK)

            # return Response({'data' : mpld3.fig_to_dict(fig)}, status = status.HTTP_200_OK)
        
        if report_type == 'line':
            X_field = request.data['options']['X_field']
            Y_field = request.data['options']['Y_field']
            group_by = request.data['options']['group_by']
            measure_operation = request.data['options']['measure_operation']

            all_fields = []
            all_fields.extend([X_field,Y_field])
            if len(group_by) > 0:
                all_fields.extend([group_by])
            print(all_fields)
            df_required = df.loc[:,all_fields]
            # plt.rcdefaults()
            # fig,ax = plt.subplots()
            # nx = np.arange(len(df_required.loc[:,X_field])) 
            # arg_list = []
            # for y in Y_field:
            #     arg_list.append(nx)
            #     arg_list.append(df_required.loc[:,y])
            # print(*arg_list)
            # ax.plot(*arg_list)
            # ax.set_xlabel(X_field)
            # label = 'fields-'
            df_num = df_required.select_dtypes(exclude = [np.number])
            all_columns = list(df_num)
            all_columns.remove(X_field)
            df_num[all_columns] = df_num[all_columns].astype('category')
            df_num[all_columns] = df_num[all_columns].apply(lambda x: x.cat.codes)
            df_required.update(df_num)

            data = {
                'labels' : np.unique(np.array(df_required.loc[:,X_field])),
                'datasets' : []
            }

            add = []
            curr = []
            op_dict = collections.defaultdict(list)

            if len(group_by) > 0:
                if measure_operation == "LAST":

                    
                    for x in df_required.groupby([group_by]).groups.keys():
                        
                        df_group = df_required.groupby([group_by]).get_group(x)
                        curr.append(np.array(df_group[[X_field,Y_field, group_by]]))

                        for d in np.array(df_group.loc[:,X_field]):
                            if d not in op_dict.keys():
                                op_dict[d] = []

                    colors = random.sample(set(self.color_choices),len(df_required.groupby([group_by]).groups.keys()))

                    for x in curr:
                        
                        for l in data['labels']:
                            op_dict[l] = []
                        
                        group_by = ""

                        for c in x:
                            
                            group_by = c[2]

                            if c[1] not in op_dict[c[0]]:
                                
                                op_dict[c[0]].append(c[1])

                        tl = 0        
                        
                        for d in data['labels']:
                            if len(op_dict[d]) > tl:
                                tl = len(op_dict[d])

                        for key,value in op_dict.items():
                            if len(value) < tl:
                                t = len(value)
                                while t < tl:
                                    op_dict[key].append(None)
                                    t += 1
                        
                        k = 0
                
                        total_length = 0
                        
                        for d in data['labels']:
                            if len(op_dict[d]) > total_length:
                                total_length = len(op_dict[d])
                        
                        while k < total_length:
                            new_add = []
                            for d in data['labels']:
                                new_add.append(op_dict[d][k])

                            data['datasets'].append({ 'label' : group_by, 'fill' : False,'borderColor' : colors[k], 'data' : new_add })
                            k += 1
                          
                    
                        
                if measure_operation == "SUM":
                    print(df_required.group_by([group_by, X_field, Y_field])[Y_field].sum())

                
                
            else:
                if measure_operation == "LAST":

                    curr = []

                    curr.extend(df_required.loc[:,[X_field,Y_field]].values)
                    print(curr)
                    for c in curr:
                        if c[1] not in op_dict[c[0]]:
                            op_dict[c[0]].append(c[1])
                
                    tl = 0        
                        
                    for d in data['labels']:
                        if len(op_dict[d]) > tl:
                            tl = len(op_dict[d])

                    for key,value in op_dict.items():
                        if len(value) < tl:
                            t = len(value)
                            while t < tl:
                                op_dict[key].append(None)
                                t += 1
                        
                    k = 0
            
                    total_length = 0

                    for d in data['labels']:
                        if len(op_dict[d]) > total_length:
                            total_length = len(op_dict[d])

                    colors = random.sample(set(self.color_choices),total_length)       
                    while k < total_length:
                        
                        new_add = []
                        for d in data['labels']:
                            new_add.append(op_dict[d][k])
                        data['datasets'].append({ 'label' : Y_field, 'fill' : False,'borderColor' : colors[k], 'data' : new_add })
                        k += 1
                    

                if measure_operation == "SUM":
                    print(df_required.group_by([X_field, Y_field])[Y_field].sum())

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
            df_required = df.loc[:,all_fields]
            df_required = df.loc[:,df.columns.isin(all_fields)]
            # df_required = df_required.dropna()
            # plt.rcdefaults()
            # fig,ax = plt.subplots()
            # width = 1
            # nx = np.arange(len(df_required.loc[:,X_field]))
            # X = df_required.loc[:,X_field]
            # ny = len(Y_field)

            

            df_num = df_required.select_dtypes(exclude = [np.number])
            all_columns = list(df_num)
            all_columns.remove(X_field)
            df_num[all_columns] = df_num[all_columns].astype('category')
            df_num[all_columns] = df_num[all_columns].apply(lambda x: x.cat.codes+1)
            df_required.update(df_num)
                    
            # print(df_required)
            # i = -(ny-1)*width/2
            # y = 0
            # j = 0
            # while i <= (ny-1)*width/2:
            #     print(len(nx-i),len(df_required.loc[:,Y_field[y]]))
            #     ax.bar(nx-i,df_required.loc[:,Y_field[y]],width,label=Y_field[y])
            #     i = i + width
            #     y = y + 1
            
            # ax.set_xticks(nx)
            # ax.set_xticklabels(tuple(np.array(df_required.loc[:,X_field])))    
            # label = 'fields-'
            # for y in Y_field:
            #     label = label + y
            # ax.set_ylabel(label)
            # ax.set_title(request.data['report_title'], size = '20')
            # ax.legend()

            data = {
                'labels' : np.unique(np.array(df_required.loc[:,X_field])),
                'datasets' : []
            }

            add = []
            curr = []
            op_dict = collections.defaultdict(list)

            if len(group_by) > 0:
                if measure_operation == "LAST":

                    for x in df_required.groupby([group_by]).groups.keys():
                        
                        df_group = df_required.groupby([group_by]).get_group(x)
                        curr.append(np.array(df_group[[X_field,Y_field,group_by]]))

                        for d in np.array(df_group.loc[:,X_field]):
                            if d not in op_dict.keys():
                                op_dict[d] = []

                    colors = random.sample(set(self.color_choices),len(df_required.groupby([group_by]).groups.keys()))

                    for x in curr:
                        
                        for l in data['labels']:
                            op_dict[l] = []

                        group_by = ""

                        for c in x:
                            
                            
                            group_by = c[2]

                            if c[1] not in op_dict[c[0]]:
                                
                                op_dict[c[0]].append(c[1])

                        tl = 0        
                        
                        for d in data['labels']:
                            if len(op_dict[d]) > tl:
                                tl = len(op_dict[d])

                        for key,value in op_dict.items():
                            if len(value) < tl:
                                t = len(value)
                                while t < tl:
                                    op_dict[key].append(None)
                                    t += 1
                        
                        k = 0
                
                        total_length = 0

                        for d in data['labels']:
                            if len(op_dict[d]) > total_length:
                                total_length = len(op_dict[d])

                        color_chosen = random.choice(colors)    
                        while k < total_length:
                            
                            new_add = []
                            for d in data['labels']:
                                new_add.append(op_dict[d][k])
                            
                            data['datasets'].append({ 'label' : [group_by], 'backgroundColor' : color_chosen, 'data' : new_add })
                            k += 1
                            print(colors)
                        if len(colors) > 1:
                            colors.remove(color_chosen)

                if measure_operation == "SUM":
                    print(df_required.group_by([group_by, X_field, Y_field])[Y_field].sum())

                
                
            else:
                if measure_operation == "LAST":

                    curr = []

                    curr.extend(df_required.loc[:,[X_field,Y_field]].values)

                    for c in curr:
                        if c[1] not in op_dict[c[0]]:
                            op_dict[c[0]].append(c[1])
                
                    tl = 0        
                        
                    for d in data['labels']:
                        if len(op_dict[d]) > tl:
                            tl = len(op_dict[d])

                    color_count = 0
                    for key,value in op_dict.items():
                        color_count += 1
                        if len(value) < tl:
                            t = len(value)
                            while t < tl:
                                op_dict[key].append(None)
                                t += 1
                    if color_count < len(self.color_choices):            
                        colors = random.sample(set(self.color_choices),color_count)
                    else:
                        colors = self.color_choices                        
                    k = 0
            
                    total_length = 0

                    for d in data['labels']:
                        if len(op_dict[d]) > total_length:
                            total_length = len(op_dict[d])

                    
                    while k < total_length:
                        new_add = []
                        for d in data['labels']:
                            new_add.append(op_dict[d][k])
                            
                        data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : colors, 'data' : new_add })
                        k += 1
                    
                
                if measure_operation == "SUM":
                    print(df_required.group_by([X_field, Y_field])[Y_field].sum())
            
            
            

            return Response({ 'data' : data }, status = status.HTTP_200_OK)
        
        if report_type == 'stacked_hor_bar':
            X_field = request.data['options']['X_field']
            Y_field = request.data['options']['Y_field']
            group_by = request.data['options']['group_by']
            measure_operation = request.data['options']['measure_operation']

            all_fields = []
            all_fields.extend([X_field,Y_field])
            if len(group_by) > 0:
                all_fields.extend([group_by])
          
            df_required = df.loc[:,df.columns.isin(all_fields)]
            # df_required = df.loc[:,all_fields]
            # df_required = df_required.dropna()
            # print(df_required)
            # plt.rcdefaults()
            # fig,ax = plt.subplots()
            # width = 0.35
            # y_pos = np.arange(len(np.unique(df_required.loc[:,Y_field])))
            # nx = len(X_field)
            # x = 0
            # while x<nx:
            #     ax.barh(y_pos,df_required.loc[:,X_field[x]],width,align='center',color = 'green',label = X_field[x])
            #     x = x + 1
            
            # ax.invert_yaxis()
            # label = 'fields-'
            # ax.set_ylabel(Y_field)
            # for x in X_field:
            #     label = label + x
            # ax.set_xlabel(label)
            # ax.legend()
            # plt.show()

            df_num = df_required.select_dtypes(exclude = [np.number])
            all_columns = list(df_num)
            all_columns.remove(X_field)
            df_num[all_columns] = df_num[all_columns].astype('category')
            df_num[all_columns] = df_num[all_columns].apply(lambda x: x.cat.codes+1)
            df_required.update(df_num)

            data = {
                'labels' : np.unique(np.array(df_required.loc[:,X_field])),
                'series' : []
            }

            add = []
            curr = []
            op_dict = collections.defaultdict(list)

            if len(group_by) > 0:
                if measure_operation == "LAST":

                    
                    for x in df_required.groupby([group_by]).groups.keys():
                        
                        df_group = df_required.groupby([group_by]).get_group(x)
                        curr.append(np.array(df_group[[X_field,Y_field]]))

                        for d in np.array(df_group.loc[:,X_field]):
                            if d not in op_dict.keys():
                                op_dict[d] = []


                    for x in curr:
                        
                        for l in data['labels']:
                            op_dict[l] = []

                        for c in x:
                            
                            print(c)

                            if c[1] not in op_dict[c[0]]:
                                
                                op_dict[c[0]].append(c[1])

                        tl = 0        
                        
                        for d in data['labels']:
                            if len(op_dict[d]) > tl:
                                tl = len(op_dict[d])

                        for key,value in op_dict.items():
                            if len(value) < tl:
                                t = len(value)
                                while t < tl:
                                    op_dict[key].append(None)
                                    t += 1
                        
                        k = 0
                
                        total_length = 0

                        for d in data['labels']:
                            if len(op_dict[d]) > total_length:
                                total_length = len(op_dict[d])
                            
                        print(op_dict)
                        while k < total_length:
                            
                            new_add = []
                            for d in data['labels']:
                                new_add.append(op_dict[d][k])
                            data['series'].append([{ 'meta' : Y_field, 'value' : i} for i in new_add])
                            k += 1
                            
                    
                        
                if measure_operation == "SUM":
                    print(df_required.group_by([group_by, X_field, Y_field])[Y_field].sum())

                
                
            else:
                if measure_operation == "LAST":

                    curr = []

                    curr.extend(df_required.loc[:,[X_field,Y_field]].values)
                    print(curr)
                    for c in curr:
                        if c[1] not in op_dict[c[0]]:
                            op_dict[c[0]].append(c[1])
                
                    tl = 0        
                        
                    for d in data['labels']:
                        if len(op_dict[d]) > tl:
                            tl = len(op_dict[d])

                    for key,value in op_dict.items():
                        if len(value) < tl:
                            t = len(value)
                            while t < tl:
                                op_dict[key].append(None)
                                t += 1
                        
                    k = 0
            
                    total_length = 0

                    for d in data['labels']:
                        if len(op_dict[d]) > total_length:
                            total_length = len(op_dict[d])
                            
                    print(op_dict)
                    while k < total_length:
                        
                        new_add = []
                        for d in data['labels']:
                            new_add.append(op_dict[d][k])
                        data['series'].append([{ 'meta' : Y_field, 'value' : i} for i in new_add])
                        k += 1
                    

                if measure_operation == "SUM":
                    print(df_required.group_by([X_field, Y_field])[Y_field].sum())
            
            
            

            return Response({ 'data' : data}, status = status.HTTP_200_OK)

        if report_type == 'StackedBar':
            X_field = request.data['options']['X_field']
            Y_field = request.data['options']['Y_field']
            group_by = request.data['options']['group_by']
            measure_operation = request.data['options']['measure_operation']

            all_fields = []
            all_fields.extend([X_field,Y_field])
            if len(group_by) > 0:
                all_fields.extend([group_by])
          
            df_required = df.loc[:,df.columns.isin(all_fields)]
            # df_required = df_required.dropna()
            # print(df_required)
            # plt.rcdefaults()
            # fig,ax = plt.subplots()
            # width = 0.35
            # nx = np.arange(len(np.unique(df_required.loc[:,X_field])))
            # ny = len(Y_field)
            # y = 0
            # j = 0
            # while y < ny:
            #     ax.bar(nx,df_required.loc[:,Y_field[y]],width,label=Y_field[y])
            #     y = y + 1
            
            # ax.set_xlabel(X_field)
            # label = 'fields-'
            # for y in Y_field:
            #     label = label + y
            # ax.set_ylabel(label)
            # ax.legend()

            df_num = df_required.select_dtypes(exclude = [np.number])
            all_columns = list(df_num)
            all_columns.remove(X_field)
            df_num[all_columns] = df_num[all_columns].astype('category')
            df_num[all_columns] = df_num[all_columns].apply(lambda x: x.cat.codes+1)
            df_required.update(df_num)

            data = {
                'labels' : np.unique(np.array(df_required.loc[:,X_field])),
                'series' : []
            }

            add = []
            curr = []
            op_dict = collections.defaultdict(list)

            if len(group_by) > 0:
                if measure_operation == "LAST":

                    
                    for x in df_required.groupby([group_by]).groups.keys():
                        
                        df_group = df_required.groupby([group_by]).get_group(x)
                        curr.append(np.array(df_group[[X_field,Y_field]]))

                        for d in np.array(df_group.loc[:,X_field]):
                            if d not in op_dict.keys():
                                op_dict[d] = []


                    for x in curr:
                        
                        for l in data['labels']:
                            op_dict[l] = []

                        for c in x:
                            
                            print(c)

                            if c[1] not in op_dict[c[0]]:
                                
                                op_dict[c[0]].append(c[1])

                        tl = 0        
                        
                        for d in data['labels']:
                            if len(op_dict[d]) > tl:
                                tl = len(op_dict[d])

                        for key,value in op_dict.items():
                            if len(value) < tl:
                                t = len(value)
                                while t < tl:
                                    op_dict[key].append(None)
                                    t += 1
                        
                        k = 0
                
                        total_length = 0

                        for d in data['labels']:
                            if len(op_dict[d]) > total_length:
                                total_length = len(op_dict[d])
                            
                        print(op_dict)
                        while k < total_length:
                            
                            new_add = []
                            for d in data['labels']:
                                new_add.append(op_dict[d][k])
                            data['series'].append([{ 'meta' : Y_field, 'value' : i} for i in new_add])
                            k += 1
                            
                    
                        
                if measure_operation == "SUM":
                    print(df_required.group_by([group_by, X_field, Y_field])[Y_field].sum())

                
                
            else:
                if measure_operation == "LAST":

                    curr = []

                    curr.extend(df_required.loc[:,[X_field,Y_field]].values)
                    print(curr)
                    for c in curr:
                        if c[1] not in op_dict[c[0]]:
                            op_dict[c[0]].append(c[1])
                
                    tl = 0        
                        
                    for d in data['labels']:
                        if len(op_dict[d]) > tl:
                            tl = len(op_dict[d])

                    for key,value in op_dict.items():
                        if len(value) < tl:
                            t = len(value)
                            while t < tl:
                                op_dict[key].append(None)
                                t += 1
                        
                    k = 0
            
                    total_length = 0

                    for d in data['labels']:
                        if len(op_dict[d]) > total_length:
                            total_length = len(op_dict[d])
                            
                    print(op_dict)
                    while k < total_length:
                        
                        new_add = []
                        for d in data['labels']:
                            new_add.append(op_dict[d][k])
                        data['series'].append([{ 'meta' : Y_field, 'value' : i} for i in new_add])
                        k += 1
                    

                if measure_operation == "SUM":
                    print(df_required.group_by([X_field, Y_field])[Y_field].sum())
            
            
            

            return Response({ 'data' : data}, status = status.HTTP_200_OK)
        

            # return Response({ 'data' : mpld3.fig_to_dict(fig)}, status = status.HTTP_200_OK)

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
            # X_field = request.data['options']['X_field']
            # all_fields = []
            # all_fields.extend([X_field])
            # print(all_fields)
            # df_required = df.loc[:,df.columns.isin(all_fields)]
            # df_required = df_required.dropna()
            # print(df_required)
            # df_num = df_required.select_dtypes(exclude = [np.number])
            # all_columns = list(df_num)
            # df_num[all_columns] = df_num[all_columns].astype('category')
            # df_num[all_columns] = df_num[all_columns].apply(lambda x: x.cat.codes)
            # print(df_num.dtypes)
            # df_required.update(df_num)
            # print(df_required)
            # plt.rcdefaults()
            # fig,ax = plt.subplots()
            # wedges, texts  = ax.pie(df_required.loc[:,X_field],textprops = dict(color = 'w'))
            # ax.legend(wedges, df_required.loc[:,X_field], title = X_field)
            # ax.set_title(request.data['report_title'])


            data = {
                'labels' : [],
                'datasets' : []
            }

            add = []
            curr = []
            op_dict = collections.defaultdict(list)

            df_non_num = df_required.select_dtypes(exclude = [np.number])
            non_num_columns = list(df_non_num)

            background_color = random.sample(set(self.color_choices), len(np.unique(np.array(df_required.loc[:,X_field]))))
            if measure_operation == 'LAST':
                if len(group_by) > 0:
                    
                    for x in df_required.groupby([group_by]).groups.keys():
                        
                        df_group = df_required.groupby([group_by]).get_group(x)
                        curr.append(np.array(df_group[[X_field,Y_field,group_by]]))

                        for d in np.array(df_group.loc[:,X_field]):
                            if d not in op_dict.keys():
                                op_dict[d] = []
                    
                    for x in curr:
                        for l in data['labels']:
                            op_dict[l] = []

                        group_by = ""

                        for c in x:
                            
                            
                            group_by = c[2]

                            if c[1] not in op_dict[c[0]]:
                                
                                op_dict[c[0]].append(c[1])

                        tl = 0        
                        
                        for d in data['labels']:
                            if len(op_dict[d]) > tl:
                                tl = len(op_dict[d])

                        if Y_field in non_num_columns:
                        
                            count_data = []
                            for key,value in op_dict.items():
                                count = sum(collections.Counter(value).values())
                                if key not in data['labels']:
                                    data['labels'].append(key)
                                count_data.append(count)                

                            data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : background_color, 'data' : count_data })
                            print(data)
                        else:
    
                            count_data = []
                            for key,value in op_dict.items():
                                count = value[-1]
                                if key not in data['labels']:
                                    data['labels'].append(key)
                                count_data.append(count)                

                            data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : background_color, 'data' : count_data })
                else:
                
                    curr.extend(df_required.loc[:,[X_field,Y_field]].values)

                    for c in curr:
                        op_dict[c[0]].append(c[1])

                    if Y_field in non_num_columns:
                        
                        count_data = []
                        for key,value in op_dict.items():
                            count = sum(collections.Counter(value).values())
                            data['labels'].append(key)
                            count_data.append(count)                

                        data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : background_color, 'data' : count_data })
                    
                    else:
   
                        count_data = []
                        for key,value in op_dict.items():
                            count = value[-1]
                            data['labels'].append(key)
                            count_data.append(count)                

                        data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : background_color, 'data' : count_data })
            return Response({ 'data' : data }, status = status.HTTP_200_OK)
            # return Response({ 'data' : mpld3.fig_to_dict(fig)}, status = status.HTTP_200_OK)

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
            # X_field = request.data['options']['X_field']
            # all_fields = []
            # all_fields.extend([X_field])
            # print(all_fields)
            # df_required = df.loc[:,df.columns.isin(all_fields)]
            # df_required = df_required.dropna()
            # print(df_required)
            # plt.rcdefaults()
            # fig,ax = plt.subplots()
            # data = np.array(df_required.loc[:,X_field])
            # wedges, texts = ax.pie(data, wedgeprops=dict(width=0.5), startangle=-40)

            # bbox_props = dict(boxstyle="square,pad=0.3", fc="w", ec="k", lw=0.72)
            # kw = dict(xycoords='data', textcoords='data', arrowprops=dict(arrowstyle="-"),
            #         bbox=bbox_props, zorder=0, va="center")

            # for i, p in enumerate(wedges):
            #     ang = (p.theta2 - p.theta1)/2. + p.theta1
            #     y = np.sin(np.deg2rad(ang))
            #     x = np.cos(np.deg2rad(ang))
            #     horizontalalignment = {-1: "right", 1: "left"}[int(np.sign(x))]
            #     connectionstyle = "angle,angleA=0,angleB={}".format(ang)
            #     kw["arrowprops"].update({"connectionstyle": connectionstyle})
            #     print(data[i])
            #     ax.annotate(data[i], xy=(x, y), xytext=(1.35*np.sign(x), 1.4*y),
            #                 horizontalalignment=horizontalalignment, **kw)

            # ax.set_title(request.data['report_title'])

            data = {
                'labels' : [],
                'datasets' : []
            }

            add = []
            curr = []
            op_dict = collections.defaultdict(list)

            df_non_num = df_required.select_dtypes(exclude = [np.number])
            non_num_columns = list(df_non_num)

            background_color = random.sample(set(self.color_choices), len(np.unique(np.array(df_required.loc[:,X_field]))))
            if measure_operation == 'LAST':
                if len(group_by) > 0:
                    
                    for x in df_required.groupby([group_by]).groups.keys():
                        
                        df_group = df_required.groupby([group_by]).get_group(x)
                        curr.append(np.array(df_group[[X_field,Y_field,group_by]]))

                        for d in np.array(df_group.loc[:,X_field]):
                            if d not in op_dict.keys():
                                op_dict[d] = []
                    
                    for x in curr:
                        for l in data['labels']:
                            op_dict[l] = []

                        group_by = ""

                        for c in x:
                            
                            
                            group_by = c[2]

                            if c[1] not in op_dict[c[0]]:
                                
                                op_dict[c[0]].append(c[1])

                        tl = 0        
                        
                        for d in data['labels']:
                            if len(op_dict[d]) > tl:
                                tl = len(op_dict[d])

                        if Y_field in non_num_columns:
                        
                            count_data = []
                            for key,value in op_dict.items():
                                count = sum(collections.Counter(value).values())
                                if key not in data['labels']:
                                    data['labels'].append(key)
                                count_data.append(count)                

                            data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : background_color, 'data' : count_data })
                            print(data)
                        else:
    
                            count_data = []
                            for key,value in op_dict.items():
                                count = value[-1]
                                if key not in data['labels']:
                                    data['labels'].append(key)
                                count_data.append(count)                

                            data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : background_color, 'data' : count_data })
                
                else:
                
                    curr.extend(df_required.loc[:,[X_field,Y_field]].values)

                    for c in curr:
                        op_dict[c[0]].append(c[1])

                    if Y_field in non_num_columns:
                        
                        count_data = []
                        for key,value in op_dict.items():
                            count = sum(collections.Counter(value).values())
                            data['labels'].append(key)
                            count_data.append(count)                

                        data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : background_color, 'data' : count_data })
                    
                    else:
   
                        count_data = []
                        for key,value in op_dict.items():
                            count = value[-1]
                            data['labels'].append(key)
                            count_data.append(count)                

                        data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : background_color, 'data' : count_data })
            return Response({ 'data' : data }, status = status.HTTP_200_OK)

            # return Response({ 'data' : mpld3.fig_to_dict(fig)}, status = status.HTTP_200_OK)
        
        if report_type == 'scatter_graph':
            X_field = request.data['options']['X_field']
            Y_field = request.data['options']['Y_field']
            group_by = request.data['options']['group_by']
            measure_operation = request.data['options']['measure_operation']

            all_fields = []
            all_fields.extend([X_field,Y_field])
            if len(group_by) > 0:
                all_fields.extend([group_by])
          
            df_required = df.loc[:,df.columns.isin(all_fields)]
        
            df_required = df_required.dropna()
            # plt.rcdefaults()
            # fig,ax = plt.subplots()
            # nx = np.arange(len(df_required.loc[:,X_field]))
            # for y in Y_field:
            #     ax.scatter(df_required.loc[:,X_field],df_required.loc[:,y])
    
            # ax.set_xlabel(X_field)
            # label = 'fields-'
            # for y in Y_field:
            #     label = label + y
            # ax.set_ylabel(label)
            # ax.set_title(request.data['report_title'])

            

            return Response({ 'data' : mpld3.fig_to_dict(fig)}, status = status.HTTP_200_OK)

        if report_type == "radar":
            X_field = request.data['options']['X_field']
            Y_field = request.data['options']['Y_field']
            group_by = request.data['options']['group_by']
            measure_operation = request.data['options']['measure_operation']

            all_fields = []
            all_fields.extend([X_field,Y_field])
            if len(group_by) > 0:
                all_fields.extend([group_by])
            print(all_fields)
            df_required = df.loc[:,all_fields]
            # plt.rcdefaults()
            # fig,ax = plt.subplots()
            # nx = np.arange(len(df_required.loc[:,X_field])) 
            # arg_list = []
            # for y in Y_field:
            #     arg_list.append(nx)
            #     arg_list.append(df_required.loc[:,y])
            # print(*arg_list)
            # ax.plot(*arg_list)
            # ax.set_xlabel(X_field)
            # label = 'fields-'
            df_num = df_required.select_dtypes(exclude = [np.number])
            all_columns = list(df_num)
            all_columns.remove(X_field)
            df_num[all_columns] = df_num[all_columns].astype('category')
            df_num[all_columns] = df_num[all_columns].apply(lambda x: x.cat.codes)
            df_required.update(df_num)

            data = {
                'labels' : np.unique(np.array(df_required.loc[:,X_field])),
                'datasets' : []
            }

            add = []
            curr = []
            op_dict = collections.defaultdict(list)

            if len(group_by) > 0:
                if measure_operation == "LAST":

                    
                    for x in df_required.groupby([group_by]).groups.keys():
                        
                        df_group = df_required.groupby([group_by]).get_group(x)
                        curr.append(np.array(df_group[[X_field,Y_field, group_by]]))

                        for d in np.array(df_group.loc[:,X_field]):
                            if d not in op_dict.keys():
                                op_dict[d] = []

                    colors = random.sample(set(self.color_choices),len(df_required.groupby([group_by]).groups.keys()))

                    for x in curr:
                        
                        for l in data['labels']:
                            op_dict[l] = []
                        
                        group_by = ""

                        for c in x:
                            
                            group_by = c[2]

                            if c[1] not in op_dict[c[0]]:
                                
                                op_dict[c[0]].append(c[1])

                        tl = 0        
                        
                        for d in data['labels']:
                            if len(op_dict[d]) > tl:
                                tl = len(op_dict[d])

                        for key,value in op_dict.items():
                            if len(value) < tl:
                                t = len(value)
                                while t < tl:
                                    op_dict[key].append(None)
                                    t += 1
                        
                        k = 0
                
                        total_length = 0
                        
                        for d in data['labels']:
                            if len(op_dict[d]) > total_length:
                                total_length = len(op_dict[d])
                        
                        while k < total_length:
                            new_add = []
                            for d in data['labels']:
                                new_add.append(op_dict[d][k])
                            data['datasets'].append({ 'label' : group_by, 'fill' : True, 'backgroundColor' : colors[k] + "33",'borderColor' : colors[k],'pointBorderColor' : "#FFF", 'pointBackgroundColor' : colors[k], 'data' : new_add })
                            k += 1
                          
                    
                        
                if measure_operation == "SUM":
                    print(df_required.group_by([group_by, X_field, Y_field])[Y_field].sum())

                
                
            else:
                if measure_operation == "LAST":

                    curr = []

                    curr.extend(df_required.loc[:,[X_field,Y_field]].values)
                    print(curr)
                    for c in curr:
                        if c[1] not in op_dict[c[0]]:
                            op_dict[c[0]].append(c[1])
                
                    tl = 0        
                        
                    for d in data['labels']:
                        if len(op_dict[d]) > tl:
                            tl = len(op_dict[d])

                    for key,value in op_dict.items():
                        if len(value) < tl:
                            t = len(value)
                            while t < tl:
                                op_dict[key].append(None)
                                t += 1
                        
                    k = 0
            
                    total_length = 0

                    for d in data['labels']:
                        if len(op_dict[d]) > total_length:
                            total_length = len(op_dict[d])

                    colors = random.sample(set(self.color_choices),total_length)       
                    while k < total_length:
                        
                        new_add = []
                        for d in data['labels']:
                            new_add.append(op_dict[d][k])
                        data['datasets'].append({ 'label' : Y_field, 'fill' : True, 'backgroundColor' : colors[k] + "33",'borderColor' : colors[k],'pointBorderColor' : "#FFF", 'pointBackgroundColor' : colors[k], 'data' : new_add })
                        k += 1
                    

                if measure_operation == "SUM":
                    print(df_required.group_by([X_field, Y_field])[Y_field].sum())

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
            # X_field = request.data['options']['X_field']
            # all_fields = []
            # all_fields.extend([X_field])
            # print(all_fields)
            # df_required = df.loc[:,df.columns.isin(all_fields)]
            # df_required = df_required.dropna()
            # print(df_required)
            # df_num = df_required.select_dtypes(exclude = [np.number])
            # all_columns = list(df_num)
            # df_num[all_columns] = df_num[all_columns].astype('category')
            # df_num[all_columns] = df_num[all_columns].apply(lambda x: x.cat.codes)
            # print(df_num.dtypes)
            # df_required.update(df_num)
            # print(df_required)
            # plt.rcdefaults()
            # fig,ax = plt.subplots()
            # wedges, texts  = ax.pie(df_required.loc[:,X_field],textprops = dict(color = 'w'))
            # ax.legend(wedges, df_required.loc[:,X_field], title = X_field)
            # ax.set_title(request.data['report_title'])


            data = {
                'labels' : [],
                'datasets' : []
            }

            add = []
            curr = []
            op_dict = collections.defaultdict(list)

            df_non_num = df_required.select_dtypes(exclude = [np.number])
            non_num_columns = list(df_non_num)

            background_color = random.sample(set(self.color_choices), len(np.unique(np.array(df_required.loc[:,X_field]))))
            if measure_operation == 'LAST':
                if len(group_by) > 0:
                    pass
                    
                    # for x in df_required.groupby([group_by]).groups.keys():
                        
                    #     df_group = df_required.groupby([group_by]).get_group(x)
                    #     curr.append(np.array(df_group[[X_field,Y_field,group_by]]))

                    #     for d in np.array(df_group.loc[:,X_field]):
                    #         if d not in op_dict.keys():
                    #             op_dict[d] = []
                    
                    # for x in curr:
                    #     for l in data['labels']:
                    #         op_dict[l] = []

                    #     group_by = ""

                    #     for c in x:
                            
                            
                    #         group_by = c[2]

                    #         if c[1] not in op_dict[c[0]]:
                                
                    #             op_dict[c[0]].append(c[1])

                    #     tl = 0        
                        
                    #     for d in data['labels']:
                    #         if len(op_dict[d]) > tl:
                    #             tl = len(op_dict[d])

                    #     if Y_field in non_num_columns:
                        
                    #         count_data = []
                    #         for key,value in op_dict.items():
                    #             count = sum(collections.Counter(value).values())
                    #             if key not in data['labels']:
                    #                 data['labels'].append(key)
                    #             count_data.append(count)                

                    #         data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : background_color, 'data' : count_data })
                    #         print(data)
                    #     else:
    
                    #         count_data = []
                    #         for key,value in op_dict.items():
                    #             count = value[-1]
                    #             if key not in data['labels']:
                    #                 data['labels'].append(key)
                    #             count_data.append(count)                

                    #         data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : background_color, 'data' : count_data })
                
                else:
                
                    curr.extend(df_required.loc[:,[X_field,Y_field]].values)

                    for c in curr:
                        op_dict[c[0]].append(c[1])

                    if Y_field in non_num_columns:
                        
                        count_data = []
                        for key,value in op_dict.items():
                            count = sum(collections.Counter(value).values())
                            data['labels'].append(key)
                            count_data.append(count)                

                        data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : background_color, 'data' : count_data })
                    
                    else:
   
                        count_data = []
                        for key,value in op_dict.items():
                            count = value[-1]
                            data['labels'].append(key)
                            count_data.append(count)                

                        data['datasets'].append({ 'label' : Y_field, 'backgroundColor' : background_color, 'data' : count_data })
            return Response({ 'data' : data }, status = status.HTTP_200_OK)
            # return Response({ 'data' : mpld3.fig_to_dict(fig)}, status = status.HTTP_200_OK)

        if report_type == 'bar_mix':
            X_field = request.data['options']['X_field']
            Y_field = request.data['options']['Y_field']
            group_by = request.data['options']['group_by']
            measure_operation = request.data['options']['measure_operation']

            all_fields = []
            all_fields.extend([X_field,Y_field])
            if len(group_by) > 0:
                all_fields.extend([group_by])
            print(all_fields)
            df_required = df.loc[:,all_fields]
            # plt.rcdefaults()
            # fig,ax = plt.subplots()
            # nx = np.arange(len(df_required.loc[:,X_field])) 
            # arg_list = []
            # for y in Y_field:
            #     arg_list.append(nx)
            #     arg_list.append(df_required.loc[:,y])
            # print(*arg_list)
            # ax.plot(*arg_list)
            # ax.set_xlabel(X_field)
            # label = 'fields-'
            df_num = df_required.select_dtypes(exclude = [np.number])
            all_columns = list(df_num)
            all_columns.remove(X_field)
            df_num[all_columns] = df_num[all_columns].astype('category')
            df_num[all_columns] = df_num[all_columns].apply(lambda x: x.cat.codes)
            df_required.update(df_num)

            data = {
                'labels' : np.unique(np.array(df_required.loc[:,X_field])),
                'datasets' : []
            }

            add = []
            curr = []
            op_dict = collections.defaultdict(list)

            if len(group_by) > 0:
                if measure_operation == "LAST":

                    
                    for x in df_required.groupby([group_by]).groups.keys():
                        
                        df_group = df_required.groupby([group_by]).get_group(x)
                        curr.append(np.array(df_group[[X_field,Y_field, group_by]]))

                        for d in np.array(df_group.loc[:,X_field]):
                            if d not in op_dict.keys():
                                op_dict[d] = []

                    colors = random.sample(set(self.color_choices),len(df_required.groupby([group_by]).groups.keys()))

                    for x in curr:
                        
                        for l in data['labels']:
                            op_dict[l] = []
                        
                        group_by = ""

                        for c in x:
                            
                            group_by = c[2]

                            if c[1] not in op_dict[c[0]]:
                                
                                op_dict[c[0]].append(c[1])

                        tl = 0        
                        
                        for d in data['labels']:
                            if len(op_dict[d]) > tl:
                                tl = len(op_dict[d])

                        for key,value in op_dict.items():
                            if len(value) < tl:
                                t = len(value)
                                while t < tl:
                                    op_dict[key].append(None)
                                    t += 1
                        
                        k = 0
                
                        total_length = 0
                        
                        for d in data['labels']:
                            if len(op_dict[d]) > total_length:
                                total_length = len(op_dict[d])
                        
                        while k < total_length:
                            new_add = []
                            for d in data['labels']:
                                new_add.append(op_dict[d][k])

                            data['datasets'].append({ 'label' : group_by, 'type' : 'line', 'fill' : False,'borderColor' : colors[k], 'data' : new_add })
                            k += 1
                        
                    for x in curr:
                        
                        for l in data['labels']:
                            op_dict[l] = []
                        
                        group_by = ""

                        for c in x:
                            
                            group_by = c[2]

                            if c[1] not in op_dict[c[0]]:
                                
                                op_dict[c[0]].append(c[1])

                        tl = 0        
                        
                        for d in data['labels']:
                            if len(op_dict[d]) > tl:
                                tl = len(op_dict[d])

                        for key,value in op_dict.items():
                            if len(value) < tl:
                                t = len(value)
                                while t < tl:
                                    op_dict[key].append(None)
                                    t += 1
                        
                        k = 0
                
                        total_length = 0
                        
                        for d in data['labels']:
                            if len(op_dict[d]) > total_length:
                                total_length = len(op_dict[d])
                        
                        while k < total_length:
                            new_add = []
                            for d in data['labels']:
                                new_add.append(op_dict[d][k])

                            data['datasets'].append({ 'label' : group_by, 'type' : 'bar','backgroundColor' : colors[k], 'data' : new_add })
                            k += 1
                                               
                          
                    
                        
                if measure_operation == "SUM":
                    print(df_required.group_by([group_by, X_field, Y_field])[Y_field].sum())

                
                
            else:
                if measure_operation == "LAST":

                    curr = []

                    curr.extend(df_required.loc[:,[X_field,Y_field]].values)
                    print(curr)
                    for c in curr:
                        if c[1] not in op_dict[c[0]]:
                            op_dict[c[0]].append(c[1])
                
                    tl = 0        
                        
                    for d in data['labels']:
                        if len(op_dict[d]) > tl:
                            tl = len(op_dict[d])

                    for key,value in op_dict.items():
                        if len(value) < tl:
                            t = len(value)
                            while t < tl:
                                op_dict[key].append(None)
                                t += 1
                        
                    k = 0
            
                    total_length = 0

                    for d in data['labels']:
                        if len(op_dict[d]) > total_length:
                            total_length = len(op_dict[d])

                    colors = random.sample(set(self.color_choices),total_length)       
                    while k < total_length:
                        
                        new_add = []
                        for d in data['labels']:
                            new_add.append(op_dict[d][k])
                        
                        data['datasets'].append({ 'label' : Y_field, 'type' : 'line','fill' : False,'borderColor' : colors[k], 'data' : new_add })
                        k += 1

                    k = 0
                    while k < total_length:
                        
                        new_add = []
                        for d in data['labels']:
                            new_add.append(op_dict[d][k])
                        
                        data['datasets'].append({ 'label' : Y_field, 'type' : 'bar','backgroundColor' : colors[k], 'data' : new_add })
                        k += 1
                        
                if measure_operation == "SUM":
                    print(df_required.group_by([X_field, Y_field])[Y_field].sum())

            return Response({ 'data' : data}, status = status.HTTP_200_OK)
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
        dataset = self.get_object(data['dataset_id'],request.user)
        serializer = ReportSerializer(data = data)

        if serializer.is_valid():
            serializer.save(profile = request.user.profile, dataset = dataset)

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

