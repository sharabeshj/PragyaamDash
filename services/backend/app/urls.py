from django.conf.urls import url
from rest_framework import routers
from app import views

routers = routers.SimpleRouter()

routers.register(r'datasets',views.DatasetViewSet)
routers.register(r'reports',views.ReportViewSet)
routers.register(r'dashboards',views.DashboardViewSet)

urlpatterns = [
    url(r'^report/filters/$', views.FilterList.as_view({ 'get': 'get_for_report' })),
    url(r'^dashboard/filters/$', views.FilterList.as_view({ 'get' : 'get_for_dashboard' })),
    url(r'^filters/$', views.FilterList.as_view({ 'put' : 'edit', 'delete' : 'delete' })),
    url(r'^users_list/$',views.SharingReports.as_view({ 'get' : 'users_list' })),
    url(r'^report_shared_users/$', views.SharingReports.as_view({ 'post' : 'get_shared_users' })),
    url(r'^report_share_to/$', views.SharingReports.as_view({ 'post' : 'report_share', 'put' :  'edit_share', 'delete' : 'remove_share' })),
    url(r'^dashboard_share_to/$', views.SharedDashboards.as_view({ 'post' : 'dashboard_share', 'put' :  'edit_share', 'delete' : 'remove_share' })),
    url(r'^dashboard_shared_users/$', views.SharedDashboards.as_view({ 'post' : 'get_shared_users' })),
]

urlpatterns += routers.urls