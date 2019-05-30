from django.conf.urls import url
from app import views

urlpatterns = [
    url(r'^datasets/$',views.DatasetList.as_view({'get' : 'get', 'post' : 'post'})),
    url(r'^datasets/(?P<id>[-\w\d]+)/add_refresh/$', views.DatasetList.as_view({ 'put' : 'add_refresh' })),
    url(r'^datasets/(?P<id>[-\w\d]+)/edit_refresh/$', views.DatasetList.as_view({ 'put' : 'edit_refresh'})),
    url(r'^datasets/(?P<id>[-\w\d]+)/delete_refresh/$', views.DatasetList.as_view({ 'put' : 'delete_refresh'})),
    url(r'^dataset_detail/$',views.DatasetDetail.as_view()),
    url(r'^report_options/$',views.ReportGenerate.as_view({ 'post' : 'report_options' })),
    url(r'^report_generate/$',views.ReportGenerate.as_view({ 'post' : 'report_generate' })),
    url(r'^reports/$',views.ReportList.as_view()),
    url(r'^dashboards/$', views.DashboardList.as_view()),
    url(r'^report_share_users/$',views.SharingReports.as_view({ 'post' : 'users_list' })),
    url(r'^report_share_to/$', views.SharingReports.as_view({ 'post' : 'report_share' })),
    url(r'^dashboard_share_to/$', views.SharingReports.as_view({ 'post' : 'dashboard_share'})),
]