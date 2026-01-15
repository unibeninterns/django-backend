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
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from django.utils import timezone
from .serializers import OTPVerificationSerializer, TutorInvitationCreateSerializer
from core.email_utils import send_html_email
from .models import CustomUser, EmailOTP
from dj_rest_auth.registration.views import RegisterView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from datetime import timedelta
from .serializers import CustomRegisterSerializer, UserSettingsSerializer
from rest_framework.permissions import IsAdminUser
from users.models import (
    TutorProfile,
    TutorInvitation,
    TutorCourseAssignment,
    CustomUser,
    TutorCourse
)
from users.serializers import (
    TutorProfileSerializer,
    TutorInvitationSerializer,
    TutorCourseAssignmentSerializer
)
from module.models import Course
import csv
from django.http import HttpResponse
from openpyxl import Workbook



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
    serializer_class = CustomRegisterSerializer

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

        user = self.perform_create(serializer)

        return Response(
            {"detail": "Registration successful. Please verify your email with the OTP.",
             "email": user.email},
            status=status.HTTP_201_CREATED
        )

    def perform_create(self, serializer):
        return serializer.save(request=self.request)

        #
        # return super().create(request, *args, **kwargs)

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

class UserSettingsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Get current user settings"""
        serializer = UserSettingsSerializer(request.user)
        return Response(serializer.data)

    def update(self, request):
        """Update user info and settings"""
        serializer = UserSettingsSerializer(instance=request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def change_password(self, request):
        """Endpoint specifically for changing password"""
        user = request.user
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")

        if not user.check_password(old_password):
            return Response({"detail": "Old password is incorrect."}, status=400)

        user.set_password(new_password)
        user.save()
        return Response({"detail": "Password updated successfully."})


class AdminTutorViewSet(viewsets.ViewSet):
    permission_classes = [IsAdminUser]

    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        total_tutors = TutorProfile.objects.count()
        active_tutors = TutorProfile.objects.filter(is_active=True).count()
        pending_invitations = TutorInvitation.objects.filter(
            status=TutorInvitation.PENDING
        ).count()

        courses_with_tutors = (
            TutorCourseAssignment.objects
            .values('course')
            .distinct()
            .count()
        )

        return Response({
            "total_tutors": total_tutors,
            "active_tutors": active_tutors,
            "pending_invitations": pending_invitations,
            "courses_assigned_tutors": courses_with_tutors,
        })

    def list(self, request):
        tutors = TutorProfile.objects.select_related('user').all()
        serializer = TutorProfileSerializer(tutors, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='invite')
    def invite(self, request):
        email = request.data.get('email')
        course_id = request.data.get('course')

        if not email:
            return Response(
                {"detail": "Email is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        course = None
        if course_id:
            course = Course.objects.filter(id=course_id).first()

        invitation = TutorInvitation.objects.create(
            email=email,
            course=course
        )

        serializer = TutorInvitationSerializer(invitation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='assign')
    def assign(self, request):
        tutor_id = request.data.get('tutor')
        course_id = request.data.get('course')

        if not tutor_id or not course_id:
            return Response(
                {"detail": "Tutor and course are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        tutor = TutorProfile.objects.get(id=tutor_id)
        course = Course.objects.get(id=course_id)

        assignment, created = TutorCourseAssignment.objects.update_or_create(
            tutor=tutor,
            defaults={
                "course": course,
                "status": TutorCourseAssignment.ACTIVE,
                "assigned_at": timezone.now(),
                "completed_at": None,
            }
        )

        serializer = TutorCourseAssignmentSerializer(assignment)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='export/csv')
    def export_csv(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="tutors.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Tutor Name',
            'Email',
            'Tutor Status',
            'Course',
            'Assignment Status',
            'Assigned At',
            'Completed At',
        ])

        tutors = TutorProfile.objects.select_related('user')

        for tutor in tutors:
            assignments = TutorCourseAssignment.objects.filter(tutor=tutor)

            if assignments.exists():
                for a in assignments:
                    writer.writerow([
                        tutor.user.get_full_name(),
                        tutor.user.email,
                        'Active' if tutor.is_active else 'Inactive',
                        a.course.title if a.course else '',
                        a.status,
                        a.assigned_at,
                        a.completed_at,
                    ])
            else:
                writer.writerow([
                    tutor.user.get_full_name(),
                    tutor.user.email,
                    'Active' if tutor.is_active else 'Inactive',
                    '',
                    '',
                    '',
                    '',
                ])

        return response

    @action(detail=False, methods=['post'], url_path='invite')
    def invite_tutor(self, request):
        serializer = TutorInvitationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']

        # Prevent duplicate active invites
        if TutorInvitation.objects.filter(
                email=email,
                status=TutorInvitation.STATUS_PENDING
        ).exists():
            return Response(
                {"detail": "An active invitation already exists for this email."},
                status=400
            )

        invitation = TutorInvitation.objects.create(
            email=email,
            invited_by=request.user,
            expires_at=timezone.now() + timedelta(days=7)
        )

        # TODO: send email with invite link
        # link: /tutor/accept/{invitation.token}

        return Response({
            "message": "Tutor invitation sent.",
            "token": str(invitation.token)
        }, status=201)


@api_view(['POST'])
@permission_classes([AllowAny])
def accept_tutor_invitation(request, token):
    try:
        invitation = TutorInvitation.objects.select_related('course').get(token=token)
    except TutorInvitation.DoesNotExist:
        return Response(
            {"detail": "Invalid invitation token."},
            status=status.HTTP_404_NOT_FOUND
        )

    # Expired
    if invitation.is_expired():
        if invitation.status == TutorInvitation.STATUS_PENDING:
            invitation.status = TutorInvitation.STATUS_EXPIRED
            invitation.save(update_fields=['status'])
        return Response(
            {"detail": "Invitation expired."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Already used
    if invitation.status != TutorInvitation.STATUS_PENDING:
        return Response(
            {"detail": "Invitation already processed."},
            status=status.HTTP_400_BAD_REQUEST
        )

    password = request.data.get('password')
    if not password:
        return Response(
            {"detail": "Password is required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Create or reuse user safely
    user, created = CustomUser.objects.get_or_create(
        email=invitation.email,
        defaults={
            "role": "tutor",
            "is_active": True
        }
    )

    if created:
        user.set_password(password)
        user.save()
    else:
        # If user exists, ensure role is tutor
        if user.role != 'tutor':
            user.role = 'tutor'
            user.save(update_fields=['role'])

    # Optional course assignment
    if invitation.course:
        TutorCourse.objects.get_or_create(
            tutor=user,
            course=invitation.course
        )

    invitation.tutor = user
    invitation.status = TutorInvitation.STATUS_ACCEPTED
    invitation.accepted_at = timezone.now()
    invitation.save(update_fields=['tutor', 'status', 'accepted_at'])

    return Response(
        {
            "detail": "Invitation accepted successfully.",
            "tutor_id": user.id,
            "course_assigned": invitation.course.id if invitation.course else None
        },
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def reject_tutor_invitation(request, token):
    try:
        invitation = TutorInvitation.objects.get(token=token)
    except TutorInvitation.DoesNotExist:
        return Response({"detail": "Invalid invitation."}, status=404)

    if invitation.status != TutorInvitation.STATUS_PENDING:
        return Response({"detail": "Invitation already processed."}, status=400)

    invitation.status = TutorInvitation.STATUS_REJECTED
    invitation.rejected_at = timezone.now()
    invitation.save(update_fields=['status', 'rejected_at'])

    return Response({"message": "Invitation rejected."})

