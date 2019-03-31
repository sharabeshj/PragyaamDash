from django.conf.urls import url
from app import views

urlpatterns = [
    url(r'^datasets/$',views.DatasetList.as_view()),
    url(r'^dataset_detail/$',views.DatasetDetail.as_view()),
    url(r'^report_options/$',views.ReportGenerate.as_view({ 'post' : 'report_options' })),
    url(r'^report_generate/$',views.ReportGenerate.as_view({ 'post' : 'report_generate' })),
    url(r'^reports/$',views.ReportList.as_view()),
    url(r'^login/$',views.LoginView.as_view()),
]