from django.contrib.auth.models import User

class GridBackend:

    def authenticate(self,request,token=None, email=None, organization_id=None, password=None):
        status = requests.post('/api/login', data = data)
        if status.status_code == 200:
            res_data = json.loads(status.text)['data']