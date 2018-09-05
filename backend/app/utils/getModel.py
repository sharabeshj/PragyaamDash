from django.db import connection,models

from app.utils import create_model


def get_model(table_name,app_name):

    fields = getColumns(table_name)

    attrs = {}

    for x,y in fields.items():
        fieldType = y['type']
        if x == 'id': ''
        elif fieldType == 'character varying': attrs[x] = models.CharField(max_length = y['length'])
        elif fieldType == 'float': attrs[x] = models.FloatField(max_length = y['length'])
        elif fieldType == 'integer': attrs[x] =  models.IntegerField()
        elif fieldType == 'text': attrs[x] = models.TextField()
        else: print ("Problem handling datatbase table",x,y['type'])

    
    return create_model(table_name,attrs,app_label=app_name,module='',options={'db_table' : table_name})

def getColumns(name):

    cursor = connection.cursor()
    cursor.execute("select column_name,data_type,character_maximum_length from information_schema.columns where table_name = '%s'"%(name))
    info = cursor.fetchall()
    fields = {}
    for item in info:
        if len(item) == 3:
            fields[item[0]] = {'type' : item[1],'length' : item[2]}
        if len(item) == 2:
            fields[item[0]] = {'type' : item[1]}
    return fields