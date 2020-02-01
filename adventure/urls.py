from django.conf.urls import url,include,re_path
from rest_framework.authtoken import views
from . import api
urlpatterns = [
    url('init', api.initialize),
    url('move', api.move),
    url('say', api.say),
    url('shout',api.shout),
    url('pm',api.pm),
    url('whois',api.whois),
    url('who',api.who),
    url('look', api.look),
    url('pickup', api.pickup),
    url('drop', api.drop),
    url('inv', api.inv),
    re_path(r'^api-token-auth/', views.obtain_auth_token)
]