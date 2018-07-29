from django.shortcuts import render

from api.models import Profile

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import Http404

# Create your views here.

class ProfileDetail(APIView):

    def get_object(self,user):
        try: 
            return Profile.objects.get(user = user)
        except Profile.DoesNotexist:
            raise Http404
    
    def get(self,request):
        
        profile = self.get_object(request.user)
        serializer = Profile(profile)
        return Response(serializer.data,status=status.HTTP_200_OK)
    
class Dataset(APIView):
    
    def post(self,request):

        pass