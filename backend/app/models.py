from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import ValidationError

from app.utils import create_model

# Create your models here.

class Profile(models.Model):
    user = models.OneToOneField(User,related_name = 'profile',on_delete=models.CASCADE)
    
@receiver(post_save,sender = User)
def create_user_profile(sender,instance,created,**kwargs):
    if created:
        Profile.objects.create(user = instance)

@receiver(post_save,sender = True)
def save_user_profile(sender,instance,**kwargs):
    instance.profile.save()


class Dataset(models.Model):
     
    profile = models.ForeignKey(Profile,related_name='datasets',on_delete = models.CASCADE)
    name = models.CharField(max_length = 50)

    def __str__(self):
         return self.name

    def get_django_model(self):

        fields = [(f.name, f.get_django_field()) for f in self.fields.all()]

        return create_model(self.name, dict(fields), self._meta.app_label)

    class Meta:
        unique_together = (('profile','name'),)
    
def is_valid_field(field_data):

    if hasattr(models,field_data) and issubclass(getattr(models, field_data), models.Field):
        return
    raise ValidationError("This is not a valid field type.")

class Field(models.Model):
    
    dataset = models.ForeignKey(Dataset, related_name = 'fields',on_delete = models.CASCADE)
    name = models.CharField(max_length =  50)
    type = models.CharField(max_length = 50, validators = [is_valid_field])
    worksheet = models.CharField(max_length = 50)

    def get_django_field(self):

        settings = [(s.name,s.value) for s in self.settings.all()]
        settings.append(tuple(('blank',True)))
        settings.append(tuple(('null',True)))

        return getattr(models, self.type)(**dict(settings))
    
    class Meta:
        unique_together = (('dataset','name','worksheet'),)
    
class Setting(models.Model):

    field = models.ForeignKey(Field, related_name = 'settings',on_delete = models.CASCADE)
    name = models.CharField(max_length = 50)
    value = models.IntegerField()

    class Meta:
        unique_together = (('field','name'))


class Table(models.Model):

    dataset = models.ForeignKey(Dataset,related_name = 'tables',on_delete = models.CASCADE)
    name = models.CharField(max_length = 50)

    def __str__(self):
        return self.name

class Join(models.Model):

    dataset = models.ForeignKey(Dataset,related_name = 'joins',on_delete = models.CASCADE)
    type = models.CharField(max_length = 50)
    field = models.CharField(max_length = 50)
    worksheet_1 = models.CharField(max_length = 50)
    worksheet_2 = models.CharField(max_length = 50)