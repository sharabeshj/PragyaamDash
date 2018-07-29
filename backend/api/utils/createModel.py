from django.db import models
from django.contrib import admin

def create_model(name,fields = None, app_label = '',module = '', options = None, admin_opts = None):

    '''

        Create specified model

    '''

    class Meta:
        pass

    if app_label:

        setattr(Meta, 'app_label', app_label)

    if options is not None:

        for key, value in options.iteritems():
            setattr(Meta, key, value)
        
    attrs = { '__module__' : module, 'Meta' : Meta }

    if fields:
        attrs.update(fields)

    model = type(name, (models.Model,), attrs)

    if admin_opts is not None:
        class Admin(admin.ModelAdmin):
            pass
        
        for key, value in admin_opts:
            setattr(Admin, key, value)
        
        admin.site.register(model, Admin)
    
    return model