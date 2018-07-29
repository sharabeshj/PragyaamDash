from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import ValidationError

from api.utils 

# Create your models here.

class Profile(models.Model):
    user = models.OneToOneField(User,on_delete=models.PROTECT)
    
@receiver(post_save,sender = User)
def create_user_profile(sender,instance,created,**kwargs):
    if created:
        Profile.objects.create(user = instance)

@receiver(post_save,sender = True)
def save_user_profile(sender,instance,**kwargs):
    instance.profile.save()


class Dataset(models.Model):
     
    user = models.ForeignKey(Profile,related_name='datasets')
    name = models.CharField(max_length = 50)

    def __str__(self):
         return self.name

    def get_django_model(self):

        fields = [(f.name, f.get_django_field()) for f in self.fields.all()]

        return create_model(self.name, dict(fields), self.user.user)

    class Meta:
        unique_together = (('user','name'),)
    
def is_valid_field(self, field_data, all_data):

    if hasattr(models,field_data) and issubclass(getattr(models, field_data), models.Field):
        return
    raise ValidationError("This is not a valid field type.")

class Field(models.Model):
    
    dataset = models.ForeignKey(Dataset, related_name = 'fields')
    name = models.CharField(max_length =  50)
    type = models.CharField(max_length = 50, validators = [is_valid_field])

    def get_django_field(self):

        settings = [(s.name,s.value) for s in self.settings.all()]

        return getattr(models, self.type)(**dict(settings))
    
    class Meta:
        unique_together = (('dataset','name'),)
    
class Setting(models.Model):

    field = models.ForeignKey(Field, related_name = 'settings')
    name = models.CharField(max_length = 50)
    value = models.CharField(max_lenght = 50)

    class Meta:
        unique_together = (('field','name'))
