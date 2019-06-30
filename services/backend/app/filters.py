from rest_framework.filters import BaseFilterBackend

class DatasetFilterBackend(BaseFilterBackend):

    def filter_queryset(self,request,queryset,view):
        if request.user.is_superuser:
            return queryset.filter(organization_id = request.user.organization_id)
        elif request.user['role'] == 'Developer':
            return queryset.filter(organization_id = request.user.organization_id).filter(userId = request.user.username)
        else:
            return None

class ReportFilterBackend(BaseFilterBackend):

    def filter_queryset(self,request,queryset,view):
        if request.user.is_superuser:
            return queryset.filter(organization_id=request.user.organization_id)
        elif request.user.role == 'Developer':
            return queryset.filter(organization_id=request.user.organization_id).filter(userId = request.user.username) | queryset.filter(organization_id = request.user.organization_id).filter(shared__user_id__contains = request.user.username)
        else:
            return queryset.filter(organization_id = request.user.organization_id).filter(shared__user_id__contains = request.user.username)

class DashboardFilterBackend(BaseFilterBackend):

    def filter_queryset(self,request,queryset,view):
        if request.user.is_superuser:
            return queryset.filter(organization_id=request.user.organization_id).all()
        if request.user.role == 'Developer':
            return queryset.filter(organization_id=request.user.organization_id).filter(userId=request.user.username) | queryset.filter(organization_id=request.user.organization_id).filter(reports__shared__user_id__contains = request.user.username)
        else:
            return queryset.filter(organization_id=request.user.organization_id).filter(reports__shared__user_id__contains=request.user.username)