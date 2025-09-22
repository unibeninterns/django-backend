from django.contrib import admin
from django.urls import path, include, re_path
from dj_rest_auth.registration.views import SocialLoginView
from django.conf import settings
from users.views import GoogleLogin 
from users.views import CustomRegisterView
from rest_framework.permissions import AllowAny
from drf_yasg.views import get_schema_view
from drf_yasg import openapi


schema_view = get_schema_view(
   openapi.Info(
      title="My API",
      default_version='v1',
      description="API documentation for my Django project",
      terms_of_service="https://www.example.com/terms/",
      contact=openapi.Contact(email="your@email.com"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=[AllowAny]
)



api_routes = [
    path('', include('users.urls')),
    path('module/', include('module.urls')),
    path('assessments/', include('assessments.urls')),
    path('progresse/', include('progresse.urls')),
    path('payments/', include('payments.urls')),
    path('v1/', include('finance.urls')),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(api_routes)),

    # dj-rest-auth endpoints
    path('api/auth/registration/', CustomRegisterView.as_view(), name='rest_register'),
    path('api/auth/', include('dj_rest_auth.urls')),
    # path('api/auth/registration/', include('dj_rest_auth.registration.urls')),
    path('api/auth/social/login/', SocialLoginView.as_view(), name='social_login'),

    # allauth urls
    path('accounts/', include('allauth.urls')),

    # Google login endpoint
    path('api/auth/google/', GoogleLogin.as_view(), name='google_login'),

    # 🔥 Swagger & ReDoc routes
    re_path(r'^swagger(?P<format>\.json|\.yaml)$',
            schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0),
         name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0),
         name='schema-redoc'),
]

#DRF GUI Interface Login
if settings.DEBUG:
    urlpatterns += [
        path('api/gui-auth/', include('rest_framework.urls')),
    ]