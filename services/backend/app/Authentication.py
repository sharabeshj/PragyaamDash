from __future__ import unicode_literals
from django.db import models
from rest_framework import authentication, exceptions, permissions
from app.models import Report, Dashboard, SharedReport
from django.contrib.auth.base_user import AbstractBaseUser
from django.utils.translation import ugettext_lazy as _
from django.http import parse_cookie
from django.db import close_old_connections
from urllib.parse import urlparse,parse_qs

import time
import requests
import json

class Profile(AbstractBaseUser):
    username = models.CharField(max_length=50, unique=True)
    user_alias = models.CharField(max_length=100)
    is_active = models.BooleanField(_('active'), default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    organization_id = models.CharField(max_length = 50)
    role = models.CharField(max_length = 10)
    team=models.CharField(max_length=30)
    token=models.TextField()

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

    def socket_authentication(self, scope):
        data = parse_qs(scope['query_string'].decode('UTF-8'))
        login_data = { 'organization_id': data['orgId'], 'token' : data['token'] }
        status = requests.post('http://dev-blr-b.pragyaam.in/api/validate_token', json = { "organization_id" : login_data['organization_id'][0]}, headers = {'Content-Type' : 'application/json','Authorization' : 'Bearer {}'.format(login_data['token'][0])})
        if status.status_code != 200:
            raise exceptions.AuthenticationFailed('UnAuthorized')
        res_data = json.loads(status.text)
        user = Profile(username = res_data['userid'],user_alias = res_data['username'],organization_id=login_data['organization_id'][0], role = res_data['role'],team=res_data['team'])
        if res_data['role'] == 'Admin':
            user.is_superuser = True
        else:
            user.is_staff = True
            user.is_active = True
        user.token = login_data['token'][0]
        return user


    def authenticate(self,request):
        
        data = json.loads(request.headers['Authorization'])
        login_data = { 'organization_id': data['organization_id'], 'token' : data['token'] }
        status = requests.post('http://dev-blr-b.pragyaam.in/api/validate_token', json = { "organization_id" : login_data['organization_id']}, headers={'Content-Type' : 'application/json', 'Authorization' : 'Bearer {}'.format(data['token'])})
        if status.status_code != 200:
            raise exceptions.AuthenticationFailed('UnAuthorized')
        res_data = json.loads(status.text)
        user = Profile(username = res_data['userid'],user_alias = res_data['username'],organization_id=login_data['organization_id'], role = res_data['role'],team=res_data['team'])
        # res_data['role'] = res_data['role']
        if res_data['role'] == 'Admin':
            user.is_superuser = True
        else:
            user.is_staff = True
            user.is_active = True
        user.token = login_data['token']
        return (user, None) 
    
class GridBackendDatasetPermissions(permissions.BasePermission):

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            if request.user.is_superuser or request.user.role == 'Developer':
                return True
        else:
            if request.user.is_superuser or request.user.role == 'Developer':
                return True
        return False

class GridBackendReportPermissions(permissions.BasePermission):

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            if request.user.is_superuser or request.user.role == 'Developer':
                return True
            else:
                shared = Report.objects.filter(organization_id = request.user.organization_id).filter(shared__user_id__contains = request.user.username).exists()
                return shared
        else:
            if request.user.is_superuser or request.user.role == 'Developer':
                return True
            return False
    
    def has_object_permission(self, request, view, obj):

        if request.method == 'POST':
            
            if request.user.is_superuser or request.user.role == 'Developer':
                return True
            return False
        
        elif request.method == 'PUT':
            
            if request.user.is_superuser:
                True
            elif request.user.role == 'Developer':
                if obj.user == request.user.username:
                    return True
                if obj.filter(shared__user_id = request.user.username).exists():
                    if obj.get(shared__user_id = request.user.username).edit:
                        return True
            return False

        elif request.method == 'DELETE':
            
            if request.user.is_superuser:
                True
            elif request.user.role == 'Developer':
                if obj.filter(user = request.user.username).exists():
                    return True
                if obj.filter(shared__user_id = request.user.username).exists():
                    if obj.get(shared__user_id = request.user.username).delete:
                        return True
            return False
        else:
            return False

class GridBackendShareReportPermissions(permissions.BasePermission):

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        else:
            if request.user.is_superuser or request.user.role == 'Developer':
                return True
        return False
    
    def has_object_permission(self, request, view, obj):

        if request.method == 'POST':
            
            if request.user.is_superuser: 
                return True
            if request.user.role == 'Developer':
                if obj.user == request.user.username:
                    return True
        return False
        
class GridBackendDashboardPermissions(permissions.BasePermission):

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            if request.user.is_superuser or request.user.role == 'Developer':
                return True
            else:
                shared = Dashbaord.objects.filter(organization_id = request.user.organization_id).filter(shared__user_id__contains = request.user.username).exists()
                return shared
        else:
            if request.user.is_superuser or request.user.role == 'Developer':
                return True
            return False
        
    
    def has_object_permission(self, request, view, obj):

        if request.method == 'POST':
            
            if request.user.is_superuser or request.user.role == 'Developer':
                return True
            return False
        
        elif request.method == 'PUT':
            
            if request.user.is_superuser:
                True
            elif request.user.role == 'Developer':
                if obj.filter(user = request.user.username).exists():
                    return True
                if obj.filter(shared__user_id = request.user.username).exists():
                    if obj.get(shared__user_id = request.user.username).edit:
                        return True
            return False

        elif request.method == 'DELETE':
            
            if request.user.is_superuser:
                True
            elif request.user.role == 'Developer':
                if obj.filter(user = request.user.username).exists():
                    return True
                if obj.filter(shared__user_id = request.user.username).exists():
                    if obj.get(shared__user_id = request.user.username).delete:
                        return True
            return False
        else:
            return False

class GridBackendShareDashboardPermissions(permissions.BasePermission):

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        else:
            if request.user.is_superuser or request.user.role == 'Developer':
                return True
        return False
    
    def has_object_permission(self, request, view, obj):

        if request.method == 'POST':
            
            if request.user.is_superuser: 
                return True
            if request.user.role == 'Developer':
                if obj.filter(user = request.user.username).exists():
                    return True
        return False


class GridAuthMiddleware:

    def __init__(self,inner):
        self.inner = inner
    
    def __call__(self,scope):
        close_old_connections()
        auth = GridBackendAuthentication()
        user = auth.socket_authentication(scope)
        return self.inner(dict(scope,user = user))