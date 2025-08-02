from django.contrib import admin
from django.urls import path, include
from dj_rest_auth.registration.views import SocialLoginView
from django.conf import settings
from users.views import GoogleLogin 


api_routes = [
    path('', include('users.urls')),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(api_routes)),

    # dj-rest-auth endpoints
    path('api/auth/', include('dj_rest_auth.urls')),
    path('api/auth/registration/', include('dj_rest_auth.registration.urls')),
    path('api/auth/social/login/', SocialLoginView.as_view(), name='social_login'),

    # allauth urls
    path('accounts/', include('allauth.urls')),

    # Google login endpoint
    path('api/auth/google/', GoogleLogin.as_view(), name='google_login'),
]

#DRF GUI Interface Login
if settings.DEBUG:
    urlpatterns += [
        path('api/gui-auth/', include('rest_framework.urls')),
    ]