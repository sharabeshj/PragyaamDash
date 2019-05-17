from __future__ import unicode_literals
from django.db import models
from rest_framework import authentication, exceptions, permissions
from app.models import Report, Dashboard
from django.contrib.auth.base_user import AbstractBaseUser
from django.utils.translation import ugettext_lazy as _

import time
import requests
import json

class Profile(AbstractBaseUser):
    username = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(_('active'), default=True)
    is_staff = models.BooleanField(default=False)
    is_super_user = models.BooleanField(default=False)
    organization_id = models.CharField(max_length = 50)
    role = models.CharField(max_length = 10)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    def get_full_name(self):
        '''
        Returns the first_name plus the last_name, with a space in between.
        '''
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        '''
        Returns the short name for the user.
        '''
        return self.first_name
    

class GridBackendAuthentication(authentication.BaseAuthentication):

    def authenticate(self,request):
        # request_data = request.COOKIES.get('info')
        # data = {
        #     'key' : 'wd33ry8r7',
        #     'token' : request_data['token'],
        #     'organization_id' : request_data['organizationId']
        # }
        data = { 'organization_id': 'pragyaamdbtest', 'email': 'sharabeshjayaraman@gmail.com', 'password': '*Shara1234', 'source' : 'web', 'timestamp' : time.time() }
        status = requests.post('http://dev-blr-b.pragyaam.in/api/login', data = data)
        if status.status_code != 200:
            raise exceptions.AuthenticationFailed('UnAuthorized')
        res_data = json.loads(status.text)['data']
        user = Profile(username = 'sharabesh',organization_id='pragyaamdbtest', role = 'admin')
        res_data['role'] = 'admin'
        if res_data['role'] == 'admin':
            user.is_superuser = True
        else:
            user.is_staff = True
            user.is_active = True
        return (user, None) 
    
class GridBackendDatasetPermissions(permissions.BasePermission):

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        else:
            if request.user.is_superuser or request.user.role == 'developer':
                return True
        return False

class GridBackendReportPermissions(permissions.BasePermission):

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            if request.user.user.is_superuser:
                return True
            elif request.user.role == 'developer':
                shared = Report.objects.filter(user = request.user.username).exists() or Dashbaord.objects.filter(organization_id = request.user.organization_id).filter(shared__user_id__contains = request.user.username).exists()
                return shared
            else:
                shared = Report.objects.filter(organization_id = request.user.organization_id).filter(shared__user_id__contains = request.user.username).exists()
                return shared
        else:
            if request.user.is_superuser or request.user.role == 'developer':
                return True
            return False
    
    def has_object_permission(self, request, view, obj):

        if request.method == 'POST':
            
            if request.user.is_superuser or request.user.role == 'developer':
                return True
            return False
        
        elif request.method == 'PUT':
            
            if request.user.user.is_superuser:
                True
            elif request.user.role == 'developer':
                return obj.filter(user = request.user.username).exists() or obj.get(shared__user_id = request.user.username).edit
            return False

        elif request.method == 'DELETE':

            if request.user.user.is_superuser:
                return True
            elif request.user.role == 'developer':
                return obj.filter(user = request.user.username).exists() or obj.get(shared__user_id=request.user.username).delete
            else: 
                return False
        else:
            return False

class GridBackendDashboardPermissions(permissions.BasePermission):

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            if request.user.is_superuser:
                return True
            elif request.user.role == 'developer':
                shared = Dashboard.objects.filter(user = request.user.username).exists() or Dashbaord.objects.filter(organization_id = request.user.organization_id).filter(reports__shared__user_id__contains = request.user.username).exists()
                return shared
            else:
                shared = Dashbaord.objects.filter(organization_id = request.user.organization_id).filter(reports__shared__user_id__contains = request.user.username).exists()
                return shared
        else:
            if request.user.is_superuser or request.user.role == 'developer':
                return True
            return False
        
    
    def has_object_permission(self, request, view, obj):

        if request.method == 'POST':
            
            if request.user.is_superuser or request.role == 'developer':
                return True
            return False
        
        elif request.method == 'PUT':
            
            if request.user.is_superuser:
                True
            elif request.user.role == 'developer':
                return obj.filter(user = request.user.username).exists() or obj.get(reports__shared__user_id = request.user.username).edit
            return False

        elif request.method == 'DELETE':

            if request.user.is_superuser:
                return True
            elif request.user.role == 'developer':
                return obj.filter(user = request.user.username).exists() or obj.get(reports__shared__user_id=request.user.username).delete
            else: 
                return False
        else:
            return False
