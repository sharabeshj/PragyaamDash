from app.models import *
from django.contrib.auth.models import User
from django.db.migrations.recorder import MigrationRecorder


class Router:

    def db_for_read(self,model,**hints):
        
        if model not in [Dataset,Field,Setting,Table,Join,Profile,User,MigrationRecorder.Migration,Report]:
            return 'redshift'
        return 'default'
    
    def db_for_write(self,model,**hints):

        if model not in [Dataset,Field,Setting,Table,Join,Profile,User,MigrationRecorder.Migration,Report]:
            return 'redshift'
        return 'default'
    
    def allow_relation(self,obj1,obj2,**hints):

        return True

    def allow_migrate(self,db,app_label,model_name = None,**hints):

        return True