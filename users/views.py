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
from django.core.mail import send_mail
from .models import CustomUser, EmailOTP
from dj_rest_auth.registration.views import RegisterView

class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    callback_url = f"{settings.SITE_URL}/accounts/google/login/callback/"
    client_class = OAuth2Client

class UserListView(generics.ListAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and user.role == 'admin':
            return CustomUser.objects.all()
        return CustomUser.objects.filter(id=user.id)

class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.request.method == 'DELETE':
            return [IsOwnerOrAdmin()]
        return [IsAuthenticated() if self.request.method in ['PATCH', 'PUT'] else AllowAny()]

@method_decorator(csrf_exempt, name='dispatch')
class AdminLoginView(APIView):
    permission_classes = [AllowAny]
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
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save(self.request)  # ✅ This is where the user is created

        if not user.is_active:
            return Response(
                {"detail": "Registration successful. Please verify your email with the OTP."},
                status=status.HTTP_201_CREATED
            )

        return super().create(request, *args, **kwargs)
    


class OTPVerificationView(APIView):
    def post(self, request):
        serializer = OTPVerificationSerializer(data=request.data)
        if serializer.is_valid():
            tokens = serializer.save()
            return Response(tokens, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class ResendOTPView(APIView):
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

        send_mail(
            subject="Your new verification code",
            message=f"Your new OTP code is: {otp_obj.otp_code}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        return Response({"detail": "A new OTP has been sent."}, status=status.HTTP_200_OK)