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
from rest_framework import viewsets

from django.contrib import admin
from django.core.management import call_command
from django.db import connections
from django.core.cache import caches
from django.db.migrations.recorder import MigrationRecorder
from django.core.management.commands import sqlmigrate

import collections
import json
from django_pandas.io import read_frame
import matplotlib.pyplot as plt
import mpld3
import numpy as np

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
                    with connections['redshift'].cursor() as cursor:
                        cursor.execute(item)
            return Response({'message' : 'success'},status=status.HTTP_201_CREATED)
        return Response(serializer.errors,status = status.HTTP_400_BAD_REQUEST)


class DatasetDetail(APIView):

    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    def get_object(self,name,user):
        try:
            return Dataset.objects.filter(profile = user.profile).get(name = name)

        except Dataset.DoesNotexist:
            return Http404


    def post(self,request):
        
        dataset = self.get_object(request.data['name'],request.user)
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
            print(model_fields)
            model_data = []
            data = []


            for t in tables:
                with connections['redshift'].cursor() as cursor:
                    cursor.execute('select * from "%s"'%(t.name))
                    table_data = dictfetchall(cursor)


                    table_model = get_model(t.name,model._meta.app_label,cursor)
                    DynamicFieldsModelSerializer.Meta.model = table_model
                    
                    context = {
                        "request" : request,
                    }
                    
                    dynamic_serializer = DynamicFieldsModelSerializer(table_data,many = True,fields = set(model_fields))
                    model_data.append({ 'name' : t.name,'data' : dynamic_serializer.data})
                    call_command('makemigrations')
                    call_command('migrate',fake = True)
                    # del table_model
                    # try:
                    #     del caches[model._meta.app_label][t.name]
                    # except KeyError:
                    #     pass
            join_model_data=[]
            
            if joins.count() == 0:
                print('hi2')
                for x in model_data:
                    for a in x['data']:
                        print(a)
                        join_model_data.append({**dict(a)})

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
                                                    join_model_data.append({**X,**z})
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
                                                join_model_data.append({**X})
                                            else:
                                                for z in check:
                                                    join_model_data.append({**X,**z})
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
                                                join_model_data.append({**X})
                                            else:
                                                for z in check:
                                                    print({**z,**X})
                                                    join_model_data.append({**z,**X})  
                                            break
                        # print(join_model_data)     
                        continue
                    if join.type == 'Outer-Join':
                        for x in model_data:
                            for c in x['data']:

                                join_model_data.append({**dict(c)})
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
                return Response('error',status=status.HTTP_400_BAD_REQUEST)
            data_subset = model.objects.all()
            data_serializer = GeneralSerializer(data_subset,many = True)
            return Response(data_serializer.data,status=status.HTTP_200_OK)
        return Response({'message' : 'error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
class ReportGenerate(viewsets.ViewSet):

    def report_options(self,request):

        report_type = request.data['type']
        if report_type == 'hor_bar':
            return Response({'options' : ['X_field','Y_field']})

    def get_object(self,name,user):
        try:
            return Dataset.objects.filter(profile = user.profile).get(name = name)

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

        if report_type == 'hor_bar':
            X_field = request.data['options']['Y_field']
            Y_field = request.data['options']['X_field']
            all_fields = []
            all_fields.extend([Y_field])
            all_fields.extend(X_field)
            df_required = df.loc[:,all_fields]
            df_required = df_required.dropna()
            print(df_required)
            plt.rcdefaults()
            fig,ax = plt.subplots()
            width = 0.35
            y_pos = np.arange(len(np.unique(df_required.loc[:,Y_field])))
            nx = len(X_field)
            i = -(nx-1)*width/2
            x = 0
            while i <= (nx-1)*width/2:
                ax.barh(y_pos-i,df_required.loc[:,X_field[x]],width,align='center',color = 'green',label = X_field[x])
                i = i + width
                x = x + 1
            
            ax.invert_yaxis()
            label = 'fields-'
            ax.set_ylabel(Y_field)
            for x in X_field:
                label = label + x
            ax.set_xlabel(label)
            ax.legend()
            # plt.show()

            return Response({'data' : mpld3.fig_to_dict(fig)}, status = status.HTTP_200_OK)
        
        if report_type == 'line_graph':
            X_field = request.data['options']['X_field']
            Y_field = request.data['options']['Y_field']
            all_fields = []
            all_fields.extend(Y_field)
            all_fields.extend([X_field])
            df_required = df.loc[:,all_fields]
            df_required = df_required.dropna()
            print(df_required)
            plt.rcdefaults()
            fig,ax = plt.subplots()
            nx = np.arange(0,len(np.unique(df_required.loc[:,X_field])),1)
            arg_list = []
            for y in Y_field:
                arg_list.append(nx)
                arg_list.append(df_required.loc[:,y])
            print(*arg_list)
            ax.plot(*arg_list)
            ax.set_xlabel(X_field)
            label = 'fields-'
            for y in Y_field:
                label = label + y
            ax.set_ylabel(label)

            return Response({ 'data' : mpld3.fig_to_dict(fig)}, status = status.HTTP_200_OK)
        
        if report_type == 'bar_graph':
            X_field = request.data['options']['X_field']
            Y_field = request.data['options']['Y_field']
            all_fields = []
            all_fields.extend(Y_field)
            all_fields.extend([X_field])
            print(all_fields)
            df_required = df.loc[:,df.columns.isin(all_fields)]
            df_required = df_required.dropna()
            print(df_required)
            plt.rcdefaults()
            fig,ax = plt.subplots()
            width = 0.35
            nx = np.arange(len(np.unique(df_required.loc[:,X_field])))
            ny = len(Y_field)
            i = -(ny-1)*width/2
            y = 0
            j = 0
            while i <= (ny-1)*width/2:
                ax.bar(nx-i,df_required.loc[:,Y_field[y]],width,label=Y_field[y])
                i = i + width
                y = y + 1
            
            ax.set_xlabel(X_field)
            label = 'fields-'
            for y in Y_field:
                label = label + y
            ax.set_ylabel(label)
            ax.legend()

            return Response({ 'data' : mpld3.fig_to_dict(fig)}, status = status.HTTP_200_OK)
        
        if report_type == 'stacked_hor_bar':
            X_field = request.data['options']['Y_field']
            Y_field = request.data['options']['X_field']
            all_fields = []
            all_fields.extend([Y_field])
            all_fields.extend(X_field)
            df_required = df.loc[:,all_fields]
            df_required = df_required.dropna()
            print(df_required)
            plt.rcdefaults()
            fig,ax = plt.subplots()
            width = 0.35
            y_pos = np.arange(len(np.unique(df_required.loc[:,Y_field])))
            nx = len(X_field)
            x = 0
            while x<nx:
                ax.barh(y_pos,df_required.loc[:,X_field[x]],width,align='center',color = 'green',label = X_field[x])
                x = x + 1
            
            ax.invert_yaxis()
            label = 'fields-'
            ax.set_ylabel(Y_field)
            for x in X_field:
                label = label + x
            ax.set_xlabel(label)
            ax.legend()
            # plt.show()

            return Response({'data' : mpld3.fig_to_dict(fig)}, status = status.HTTP_200_OK)

        if report_type == 'stacked_bar_graph':
            X_field = request.data['options']['X_field']
            Y_field = request.data['options']['Y_field']
            all_fields = []
            all_fields.extend(Y_field)
            all_fields.extend([X_field])
            print(all_fields)
            df_required = df.loc[:,df.columns.isin(all_fields)]
            df_required = df_required.dropna()
            print(df_required)
            plt.rcdefaults()
            fig,ax = plt.subplots()
            width = 0.35
            nx = np.arange(len(np.unique(df_required.loc[:,X_field])))
            ny = len(Y_field)
            y = 0
            j = 0
            while y < ny:
                ax.bar(nx,df_required.loc[:,Y_field[y]],width,label=Y_field[y])
                y = y + 1
            
            ax.set_xlabel(X_field)
            label = 'fields-'
            for y in Y_field:
                label = label + y
            ax.set_ylabel(label)
            ax.legend()

            return Response({ 'data' : mpld3.fig_to_dict(fig)}, status = status.HTTP_200_OK)

        if report_type == 'pie_graph':
            X_field = request.data['options']['X_field']
            all_fields = []
            all_fields.extend([X_field])
            print(all_fields)
            df_required = df.loc[:,df.columns.isin(all_fields)]
            df_required = df_required.dropna()
            print(df_required)
            plt.rcdefaults()
            fig,ax = plt.subplots()
            wedges, texts, autotexts = ax.pie(df_required.loc[:,X_field],autopct = lambda pct : self.func(pct, df_required.loc[:,X_field]),textprops = dict(color = 'w'))
            ax.legend(wedges, df_required.loc[:,X_field], title = X_field)
            ax.set_title(request.data['report_title'])

            return Response({ 'data' : mpld3.fig_to_dict(fig)}, status = status.HTTP_200_OK)

        if report_type == 'donut_graph':
            X_field = request.data['options']['X_field']
            all_fields = []
            all_fields.extend([X_field])
            print(all_fields)
            df_required = df.loc[:,df.columns.isin(all_fields)]
            df_required = df_required.dropna()
            print(df_required)
            plt.rcdefaults()
            fig,ax = plt.subplots()
            data = df_required.loc[:,X_field]
            wedges, texts = ax.pie(data, wedgeprops=dict(width=0.5), startangle=-40)

            bbox_props = dict(boxstyle="square,pad=0.3", fc="w", ec="k", lw=0.72)
            kw = dict(xycoords='data', textcoords='data', arrowprops=dict(arrowstyle="-"),
                    bbox=bbox_props, zorder=0, va="center")

            for i, p in enumerate(wedges):
                ang = (p.theta2 - p.theta1)/2. + p.theta1
                y = np.sin(np.deg2rad(ang))
                x = np.cos(np.deg2rad(ang))
                horizontalalignment = {-1: "right", 1: "left"}[int(np.sign(x))]
                connectionstyle = "angle,angleA=0,angleB={}".format(ang)
                kw["arrowprops"].update({"connectionstyle": connectionstyle})
                ax.annotate(data[i], xy=(x, y), xytext=(1.35*np.sign(x), 1.4*y),
                            horizontalalignment=horizontalalignment, **kw)

            ax.set_title(request.data['report_title'])

            return Response({ 'data' : mpld3.fig_to_dict(fig)}, status = status.HTTP_200_OK)

        return Response('error',status = status.HTTP_400_BAD_REQUEST)
