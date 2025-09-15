from .models import CustomUser
from rest_framework import generics
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.permissions import BasePermission
from rest_framework import exceptions
from .serializers import UserSerializer, AdminLoginSerializer
from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from rest_framework import viewsets
from rest_framework.decorators import action
from django.utils import timezone
from rest_framework import status
from .serializers import OTPVerificationSerializer
from core.email_utils import send_html_email
from .models import CustomUser, EmailOTP
from dj_rest_auth.registration.views import RegisterView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    callback_url = f"{settings.SITE_URL}/accounts/google/login/callback/"
    client_class = OAuth2Client

    @swagger_auto_schema(
        operation_summary="Google Social Login",
        operation_description="Authenticate users via Google OAuth2 access token.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["access_token"],
            properties={
                "access_token": openapi.Schema(type=openapi.TYPE_STRING, description="Google OAuth2 access token"),
                "code": openapi.Schema(type=openapi.TYPE_STRING, description="Optional authorization code"),
            },
        ),
        responses={
            200: openapi.Response(
                description="Login success",
                examples={
                    "application/json": {
                        "key": "jwt_token_here"
                    }
                }
            ),
            400: openapi.Response(description="Invalid token or authentication failed")
        },
        tags=["Auth"]
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
    

class UserListView(generics.ListAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and user.role == 'admin':
            return CustomUser.objects.all()
        return CustomUser.objects.filter(id=user.id)
    
    @swagger_auto_schema(
        operation_summary="List Users",
        operation_description="Returns all users for admins, or only the current user for others.",
        responses={
            200: openapi.Response(
                description="List of users",
                schema=UserSerializer(many=True)
            ),
            403: openapi.Response(description="Forbidden")
        },
        tags=["Users"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    

class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.request.method == 'DELETE':
            return [IsOwnerOrAdmin()]
        return [IsAuthenticated() if self.request.method in ['PATCH', 'PUT'] else AllowAny()]

    @swagger_auto_schema(
        operation_summary="Retrieve, update, or delete a user",
        responses={
            200: UserSerializer(),
            403: openapi.Response(description="Forbidden"),
            404: openapi.Response(description="User not found")
        },
        tags=["Users"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update a user",
        request_body=UserSerializer,
        responses={
            200: UserSerializer(),
            400: openapi.Response(description="Validation error"),
            403: openapi.Response(description="Forbidden"),
            404: openapi.Response(description="User not found")
        },
        tags=["Users"]
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Delete a user",
        responses={
            204: openapi.Response(description="User deleted"),
            403: openapi.Response(description="Forbidden"),
            404: openapi.Response(description="User not found")
        },
        tags=["Users"]
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)
    

@method_decorator(csrf_exempt, name='dispatch')
class AdminLoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Admin login",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email", "password"],
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, format="email", description="Admin email"),
                "password": openapi.Schema(type=openapi.TYPE_STRING, format="password", description="Admin password"),
            },
        ),
        responses={
            200: openapi.Response(
                description="Login successful",
                examples={
                    "application/json": {
                        "refresh": "refresh_token",
                        "access": "access_token",
                        "user": {
                            "email": "admin@example.com",
                            "role": "admin",
                            "first_name": "John",
                            "last_name": "Doe"
                        }
                    }
                }
            ),
            401: openapi.Response(description="Invalid credentials"),
            403: openapi.Response(description="Access denied. Not an admin."),
            400: openapi.Response(description="Validation error")
        },
        tags=["Auth"]
    )
    def post(self, request):
        serializer = AdminLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        user = authenticate(request, email=email, password=password)

        if user is None:
            return Response({"detail": "Invalid credentials"}, status=401)

        if user.role != "admin":
            return Response({"detail": "Access denied. Not an admin."}, status=403)

        refresh = RefreshToken.for_user(user)
        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "email": user.email,
                "role": user.role,
                "first_name": user.first_name,
                "last_name": user.last_name,
            }
        })

class IsOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        return obj == request.user or request.user.role == 'admin'

class UserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['destroy']:
            return [IsOwnerOrAdmin()]
        return [IsAuthenticated]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not self.get_permissions()[0].has_object_permission(request, self, instance):
            raise exceptions.PermissionDenied("You do not have permission to delete this user.")
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and user.role == 'admin':
            return CustomUser.objects.all()
        return CustomUser.objects.filter(id=user.id)
    
    @swagger_auto_schema(
        operation_summary="List users with today's signups count",
        responses={
            200: openapi.Response(
                description="User list with signups_today count",
                examples={
                    "application/json": {
                        "signups_today": 5,
                        "users": [
                            {
                                "id": 1,
                                "username": "user1",
                                "email": "user1@example.com",
                                "role": "admin"
                            }
                        ]
                    }
                }
            )
        },
        tags=["Users"]
    )

    def list(self, request, *args, **kwargs):
        """Override list to include signups_today count."""
        response = super().list(request, *args, **kwargs)
        today = timezone.now().date()
        signups_today = CustomUser.objects.filter(start_date__date=today).count()
        response.data = {
            "signups_today": signups_today,
            "users": response.data
        }
        return response

    @action(detail=False, methods=['get'])
    def signups_today(self, request):
        today = timezone.now().date()
        signups_today = CustomUser.objects.filter(start_date__date=today).count()
        return Response({"signups_today": signups_today})


class CustomRegisterView(RegisterView):

    @swagger_auto_schema(
        operation_summary="Register a new user",
        operation_description="Create a new user account. If inactive, OTP verification is required.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email", "password1", "password2", "first_name", "last_name"],
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, format="email", description="User email"),
                "password1": openapi.Schema(type=openapi.TYPE_STRING, format="password", description="Password"),
                "password2": openapi.Schema(type=openapi.TYPE_STRING, format="password", description="Password confirmation"),
                "first_name": openapi.Schema(type=openapi.TYPE_STRING, description="First name"),
                "last_name": openapi.Schema(type=openapi.TYPE_STRING, description="Last name"),
            },
        ),
        responses={
            201: openapi.Response(
                description="Registration successful; OTP verification required if inactive.",
                examples={
                    "application/json": {
                        "detail": "Registration successful. Please verify your email with the OTP."
                    }
                }
            ),
            400: openapi.Response(description="Validation errors or user already exists"),
        },
        tags=["Auth"]
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save(self.request)

        if not user.is_active:
            return Response(
                {"detail": "Registration successful. Please verify your email with the OTP."},
                status=status.HTTP_201_CREATED
            )

        return super().create(request, *args, **kwargs)
    


class OTPVerificationView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Verify OTP",
        request_body=OTPVerificationSerializer,
        responses={
            200: openapi.Response(description="OTP verified successfully"),
            400: openapi.Response(description="Invalid OTP or validation error"),
        },
        tags=["Auth"]
    )
    def post(self, request):
        serializer = OTPVerificationSerializer(data=request.data)
        if serializer.is_valid():
            tokens = serializer.save()
            return Response(tokens, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class ResendOTPView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Resend OTP to user email",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email"],
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, format="email", description="User email"),
            },
        ),
        responses={
            200: openapi.Response(description="OTP resent successfully"),
            400: openapi.Response(description="Email is required or user already verified"),
            404: openapi.Response(description="User not found"),
        },
        tags=["Auth"]
    )
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if user.is_active:
            return Response({"detail": "User is already verified."}, status=status.HTTP_400_BAD_REQUEST)

        otp_obj, _ = EmailOTP.objects.get_or_create(user=user)
        otp_obj.generate_otp()

        # Send OTP email
        send_html_email(
            subject="Your new verification code",
            template_name="email/otp_email.html",
            context={'user': user, 'otp_code': otp_obj.otp_code},
            recipient_list=[user.email],
        )

        return Response({"detail": "A new OTP has been sent."}, status=status.HTTP_200_OK)
