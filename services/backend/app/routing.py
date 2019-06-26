from django.conf.urls import url
from app import consumers

websocket_urlpatterns = [
    url(r'^socket/dataset/refresh',consumers.DatasetConsumer),
    url(r'^socket/report/generate',consumers.ReportGenerateConsumer),
    url(r'^socket/filter/options',consumers.FilterConsumer)
]