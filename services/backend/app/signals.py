from celery.signals import after_task_publish,task_failure,task_postrun
from asgiref.sync import async_to_sync
from django.dispatch import receiver
from channels.layers import get_channel_layer

import ast

@task_failure.connect
def task_failure_receiver(task_id=None, exception=None, *args,**kwargs):
    

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        '{}_dataset'.format(kwargs['args'][0]),
            {
                'type' : 'send_status',
                'data' : {
                    'type' : 'task_failure',
                    'exception' : exception
                }
            }
        )
    
@task_postrun.connect
def task_postrun_receiver(task_id=None, task=None, state=None, *args,**kwargs):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        '{}_dataset'.format(kwargs['args'][0]),
            {
                'type' : 'send_status',
                'data' : {
                    'type' : 'task_success',
                    'channel_name' : kwargs['args'][2],
                    'dataset_id' : kwargs['args'][1]
                }
            }
        )