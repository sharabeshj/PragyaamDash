from django.db import connections,models

from app.utils import create_model


def get_model(table_name,app_name,cursor):

    fields = getColumns(table_name,cursor)

    attrs = {}

    for x,y in fields.items():
        fieldType = y['type']
        if x == 'id': ''
        elif fieldType == 'character varying': attrs[x] = models.CharField(max_length = y['length'],null = True)
        elif fieldType == 'date' : attrs[x] = models.CharField(max_length = 20,null = True)
        elif fieldType == 'timestamp without time zone': attrs[x] = models.CharField(max_length = 40, null= True)
        elif fieldType == 'float': attrs[x] = models.FloatField(max_length = y['length'],null = True)
        elif fieldType == 'integer': attrs[x] =  models.IntegerField(null = True)
        elif fieldType == 'text': attrs[x] = models.TextField(null = True)
        elif fieldType == 'numeric': attrs[x] = models.IntegerField(null=True)
        else: print ("Problem handling datatbase table",x,y['type'])

    
    return create_model(table_name,attrs,app_label=app_name,module='',options={'db_table' : table_name,'managed' : False})


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

def getColumnList(table_name, cursor):

    fields = getColumns(table_name, cursor)
    field_list = []

    for x,y in fields.items():
        field_list.append(x)
    
    return field_list