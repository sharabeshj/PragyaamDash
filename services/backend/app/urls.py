from django.conf.urls import url
from app import views

urlpatterns = [
    url(r'^datasets/$',views.DatasetList.as_view({'get' : 'get', 'post' : 'post', 'put' : 'edit'})),
    url(r'^datasets/(?P<id>[-\w\d]+)/add_refresh/$', views.DatasetList.as_view({ 'put' : 'add_refresh' })),
    url(r'^datasets/(?P<id>[-\w\d]+)/edit_refresh/$', views.DatasetList.as_view({ 'put' : 'edit_refresh'})),
    url(r'^datasets/(?P<id>[-\w\d]+)/delete_refresh/$', views.DatasetList.as_view({ 'put' : 'delete_refresh'})),
    url(r'^dataset_detail/$',views.DatasetDetail.as_view()),
    url(r'^report_generate/$',views.ReportGenerate.as_view({ 'post' : 'report_generate' })),
    url(r'^reports/$',views.ReportList.as_view({ 'get' : 'get', 'post' : 'post', 'put' : 'edit', 'delete' : 'delete' })),
    url(r'^report/filters/$', views.FilterList.as_view({ 'get': 'get_for_report' })),
    url(r'^report/add_filter/$', views.ReportList.as_view({ 'put' : 'add_filter'})),
    url(r'^dashboards/$', views.DashboardList.as_view({ 'get' : 'get', 'post' : 'post', 'put' : 'put' })),
    url(r'^dashboard/filters/$', views.FilterList.as_view({ 'get' : 'get_for_dashboard' })),
    url(r'^dashboard/add_filter/$', views.DashboardList.as_view({ 'put' : 'add_filter' })),
    url(r'^filters/$', views.FilterList.as_view({ 'put' : 'edit', 'delete' : 'delete' })),
    url(r'^users_list/$',views.SharingReports.as_view({ 'get' : 'users_list' })),
    url(r'^report_shared_users/$', views.SharingReports.as_view({ 'post' : 'get_shared_users' })),
    url(r'^report_share_to/$', views.SharingReports.as_view({ 'post' : 'report_share', 'put' :  'edit_share', 'delete' : 'remove_share' })),
    url(r'^dashboard_share_to/$', views.SharingReports.as_view({ 'post' : 'dashboard_share'})),
]