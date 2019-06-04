from __future__ import unicode_literals
from django.db import models
from rest_framework import authentication, exceptions, permissions
from app.models import Report, Dashboard
from django.contrib.auth.base_user import AbstractBaseUser
from django.utils.translation import ugettext_lazy as _
from django.http import parse_cookie
import time
import requests
import json

class Profile(AbstractBaseUser):
    username = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(_('active'), default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    organization_id = models.CharField(max_length = 50)
    role = models.CharField(max_length = 10)
    token = models.TextField()

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
        print(request.headers)
        # cookies = requests.utils.dict_parse_cookie(request_data)
        # cookies = {}
        # for key,morsel in cookie.items():
        #     cookies[key] = morsel.value
        # print(cookies)
        # data = {
        #     'key' : 'wd33ry8r7',
        #     'token' : request_data['token'],
        #     'organization_id' : request_data['organizationId']
        # }
        data = json.loads(request.headers['Authorization'])
        data = { 'organization_id': data['organization_id'], 'email': data['username'], 'password': '*Shara1234', 'source' : 'web', 'timestamp' : time.time() }
        status = requests.post('http://dev-blr-b.pragyaam.in/api/login', data = data)
        if status.status_code != 200:
            raise exceptions.AuthenticationFailed('UnAuthorized')
        print(json.loads(status.text))
        res_data = json.loads(status.text)['data']
        user = Profile(username = res_data['userId'],organization_id=res_data['organizationId'], role = res_data['role'])
        # res_data['role'] = res_data['role']
        if res_data['role'] == 'Admin':
            user.is_superuser = True
        else:
            user.is_staff = True
            user.is_active = True
        user.token = res_data['token']
        return (user, None) 
    
class GridBackendDatasetPermissions(permissions.BasePermission):

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        else:
            if request.user.is_superuser or request.user.role == 'Developer':
                return True
        return False

class GridBackendReportPermissions(permissions.BasePermission):

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            if request.user.is_superuser:
                return True
            elif request.user.role == 'Developer':
                shared = Report.objects.filter(organization_id = request.user.organization_id).filter(user = request.user.username).exists() or Report.objects.filter(organization_id = request.user.organization_id).filter(shared__user_id__contains = request.user.username).exists()
                return shared
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
                if obj.filter(user = request.user.username).exists():
                    return True
                if obj.filter(shared__user_id = request.user.username).exists():
                    try:
                        if obj.get(shared__user_id = request.user.username).edit:
                            return True
                    except:
                        pass
            return False

        elif request.method == 'DELETE':
            
            if request.user.is_superuser:
                True
            elif request.user.role == 'Developer':
                if obj.filter(user = request.user.username).exists():
                    return True
                if obj.filter(shared__user_id = request.user.username).exists():
                    try:
                        if obj.get(shared__user_id = request.user.username).delete:
                            return True
                    except:
                        pass
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
                if obj.filter(user = request.user.username).exists():
                    return True
                if obj.filter(shared__user_id = request.user.username).exists():
                    try:
                        if obj.get(shared__user_id = request.user.username).edit:
                            return True
                        if obj.get(shared__user_id = request.user.username).delte:
                            return True
                    except:
                        pass
        return False
        

class GridBackendDashboardPermissions(permissions.BasePermission):

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            if request.user.is_superuser:
                return True
            elif request.user.role == 'Developer':
                shared = Dashboard.objects.filter(organization_id = request.user.organization_id).filter(user = request.user.username).exists() or Dashbaord.objects.filter(organization_id = request.user.organization_id).filter(shared__user_id__contains = request.user.username).exists()
                return shared
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
                    try:
                        if obj.get(shared__user_id = request.user.username).edit:
                            return True
                    except:
                        pass
            return False

        elif request.method == 'PUT':
            
            if request.user.is_superuser:
                True
            elif request.user.role == 'Developer':
                if obj.filter(user = request.user.username).exists():
                    return True
                if obj.filter(shared__user_id = request.user.username).exists():
                    try:
                        if obj.get(shared__user_id = request.user.username).delete:
                            return True
                    except:
                        pass
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
                if obj.filter(shared__user_id = request.user.username).exists():
                    try:
                        if obj.get(shared__user_id = request.user.username).edit:
                            return True
                        if obj.get(shared__user_id = request.user.username).delte:
                            return True
                    except:
                        pass
        return False