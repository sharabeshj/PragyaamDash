from django.db import connections,models

from app.utils import create_model
import re

def get_model(table_name,app_name,cursor, req_type, sql=''):

    if(req_type == 'READ'):
        fields = getColumnsRead(table_name,cursor)
        attrs = {}
        for x,y in fields.items():
            fieldType = y['type']
            if x == 'id': ''
            elif fieldType == 'varchar': attrs[x] = models.CharField(max_length = y['length'],null = True)
            elif fieldType == 'date' : attrs[x] = models.DateField(null = True)
            elif fieldType == 'datetime' : attrs[x] = models.DateTimeField(null = True)    
            elif fieldType == 'time': attrs[x] = models.TimeField(null= True)
            elif fieldType == 'float': attrs[x] = models.FloatField(null = True)
            elif fieldType == 'varchar(max)': attrs[x] = models.TextField(null = True)
            elif fieldType == 'text': attrs[x] = models.TextField(null = True)
            elif fieldType == 'longtext': attrs[x] = models.TextField(null = True)
            elif fieldType == 'int': attrs[x] = models.IntegerField(null=True)
            else: print ("Problem handling datatbase table",x,y['type'])
        return create_model(table_name,attrs,app_label=app_name,module='',options={'db_table' : table_name,'managed' : False})

    if(req_type == 'READ_POSTGRES'):
        fields = getColumns(table_name,cursor)

        attrs = {}

        for x,y in fields.items():
            fieldType = y['type']
            if x == 'id': ''
            elif fieldType == 'character varying': attrs[x] = models.CharField(max_length = y['length'],null = True)
            elif fieldType == 'date' : attrs[x] = models.DateField(null = True)
            elif fieldType == 'timestamp without time zone': attrs[x] = models.TimeField(null= True)
            elif fieldType == 'float': attrs[x] = models.FloatField(max_length = y['length'],null = True)
            elif fieldType == 'integer': attrs[x] =  models.IntegerField(null = True)
            elif fieldType == 'text': attrs[x] = models.TextField(null = True)
            elif fieldType == 'numeric': attrs[x] = models.IntegerField(null=True)
        return create_model(table_name,attrs,app_label=app_name,module='',options={'db_table' : table_name,'managed' : False})

    else:
        fields = getColumnsCreate(table_name, cursor, sql)
        attrs = {}
        print("cam  e")
        for x,y in fields.items():
            fieldType = y['type']
            if x == 'id': ''
            elif fieldType == 'varchar': attrs[x] = models.CharField(max_length = y['length'],null = True)
            elif fieldType == 'date' : attrs[x] = models.DateField(null = True)
            elif fieldType == 'datetime' : attrs[x] = models.DateTimeField(null = True)    
            elif fieldType == 'time': attrs[x] = models.TimeField(null= True)
            elif fieldType == 'float': attrs[x] = models.FloatField(null = True)
            elif fieldType == 'varchar(max)': attrs[x] = models.TextField(null = True)
            elif fieldType == 'text': attrs[x] = models.TextField(null = True)
            elif fieldType == 'longtext': attrs[x] = models.TextField(null = True)
            elif fieldType == 'int': attrs[x] = models.IntegerField(null=True)
            elif fieldType == 'decimal': attrs[x] = models.FloatField(null=True)
            else: print ("Problem handling datatbase table",x,y['type'])
            
        return create_model(table_name,attrs,app_label=app_name,module='',options={'db_table' : table_name})

def getColumns(name,cursor):

    #for redshift
    #cursor.execute("select column_name,data_type,character_maximum_length from information_schema.columns where table_name = '"+name.lower()    +"';")
     #for local 
    cursor.execute("select column_name, data_type, character_maximum_length from information_schema.columns where table_schema = 'public' and table_name = '%s';" %(name))
    info = cursor.fetchall()
    print(info)
    fields = {}
    for item in info:
        fields[item[0]] = {'type' : item[1],'length' : item[2]}
    return fields

def getColumnsRead(name,cursor):

    #for redshift
    #cursor.execute("select column_name,data_type,character_maximum_length from information_schema.columns where table_name = '"+name.lower()    +"';")
     #for local 
    # cursor.execute("select column_name, data_type, character_maximum_length from information_schema.columns where table_schema = 'public' and table_name = '%s';" %(name))
    cursor.execute('DESCRIBE `{}`'.format(name))
    info = cursor.fetchall()
    print(info)
    fields = {}
    pattern = re.compile(r"\((\d+)\)")
    for item in info:
        num_str = pattern.findall(item[1])
        num = 0
        if len(num_str) > 0:
            num = int(num_str[0])
        if num > 0: 
            print(item[1].split('(')[0])
            item_type = item[1].split('(')[0]
            fields[item[0]] = {'type' : item_type, 'length' : num}
        else:
            item_type = item[1].split('(')[0]
            fields[item[0]] = { 'type' : item_type, 'length' : 0}
    return fields

def getColumnsCreate(name, cursor, sql):
    
    print('CREATE TEMPORARY TABLE exportTable AS ({})'.format(sql))
    cursor.execute('CREATE TEMPORARY TABLE exportTable AS ({})'.format(sql))
    cursor.execute('DESCRIBE exportTable')
    info = cursor.fetchall()
    print(info)
    fields = {}
    pattern = re.compile(r"\((\d+)\)")
    for item in info:
        num_str = pattern.findall(item[1])
        num = 0
        if len(num_str) > 0:
            num = int(num_str[0])
        if num > 0: 
            print(item[1].split('(')[0])
            item_type = item[1].split('(')[0]
            fields[item[0]] = {'type' : item_type, 'length' : num}
        else:
            item_type = item[1].split('(')[0]
            fields[item[0]] = { 'type' : item_type}
    return fields

def getColumnList(table_name, cursor):

    fields = getColumns(table_name, cursor)
    field_list = []

    for x,y in fields.items():
        field_list.append(x)
    
    return field_list