from django.conf.urls import url
from api_v4 import views

urlpatterns = [
    url(r'^datasets/$',views.DatasetList.as_view()),
    url(r'^dataset_detail/$',views.DatasetDetail.as_view()),
]