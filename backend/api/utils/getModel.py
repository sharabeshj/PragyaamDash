from django.db import connections,models

from api.utils import create_model


def get_model(table_name,app_name,cursor):

    fields = getColumns(table_name,cursor)

    attrs = {}

    for x,y in fields.items():
        fieldType = y['type']
        if x == 'id': ''
        elif fieldType == 'character varying': attrs[x] = models.CharField(max_length = y['length'],null = True)
        elif fieldType == 'date' : attrs[x] = models.CharField(max_length = 20,null = True)
        elif fieldType == 'float': attrs[x] = models.FloatField(max_length = y['length'],null = True)
        elif fieldType == 'integer': attrs[x] =  models.IntegerField(null = True)
        elif fieldType == 'text': attrs[x] = models.TextField(null = True)
        else: print ("Problem handling datatbase table",x,y['type'])

    
    return create_model(table_name,attrs,app_label=app_name,module='',options={'db_table' : table_name})

def getColumns(name,cursor):

    cursor.execute("select column_name,data_type,character_maximum_length from information_schema.columns where table_name = '"+name.lower()    +"';")
    info = cursor.fetchall()
    print(info)
    fields = {}
    for item in info:
        fields[item[0]] = {'type' : item[1],'length' : item[2]}
    return fields