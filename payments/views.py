import time
import csv
from io import BytesIO
from django.contrib import admin, messages
from rest_framework.generics import get_object_or_404

from core.common.utils.progress_aggregates import get_course_completion_percentage
from core.common.utils.progress_states import ContentState
from .services import initiate_flutterwave_transfer, initiate_addon_payment
from openpyxl import Workbook
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
from .utils import create_flutterwave_payment, verify_flutterwave_payment
from .models import Package, AddOn, Payment, Enrollment, Payout
from .serializers import (
    PaymentSerializer, EnrollmentSerializer, PackageSerializer, AddOnSerializer,
    PackageSelectionSerializer, PaymentDetailSerializer, EnrollmentDetailSerializer, PayoutSerializer,
    AdminPayoutSerializer,
)
from django.db import transaction
from django.contrib.auth import get_user_model
from .permissions import IsStudent, IsOwnerOrAdmin
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from django.db.models import Sum, Q, Count, F, Avg, OuterRef, Subquery, IntegerField
from rest_framework.request import Request
from django.db.models.functions import TruncMonth, TruncWeek, Coalesce
from module.models import LiveSessionAttendance, Course, Certificate, CertificatePayment, CertificateRequest
from progresse.models import ModuleCompletion
from module.serializers import (
    CertificateRequestSerializer,
    CertificateSerializer
)
from module.services import generate_certificate_pdf, send_certificate_email ,generate_certificate_preview_pdf

User = get_user_model()

def month_range(dt):
    start = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if dt.month == 12:
        end = start.replace(year=dt.year + 1, month=1)
    else:
        end = start.replace(month=dt.month + 1)
    return start, end

def export_csv(filename, headers, rows):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'

    writer = csv.writer(response)
    writer.writerow(headers)

    for row in rows:
        writer.writerow(row)

    return response

def export_excel(filename, headers, rows):
    wb = Workbook()
    ws = wb.active
    ws.append(headers)

    for row in rows:
        ws.append(row)

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    response = HttpResponse(
        buffer,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
    return response

def get_month_range(year, month):
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)
    return start, end

def get_week_ranges(year, month):
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)

    weeks = []
    current = start
    week_number = 1

    while current < end:
        week_end = min(current + timedelta(days=7), end)
        weeks.append({
            "week": week_number,
            "start": current,
            "end": week_end
        })
        current = week_end
        week_number += 1

    return weeks

def get_course_completion_queryset(course_id=None):
    qs = (
        ModuleCompletion.objects
        .select_related('module__course', 'student')
        .values(
            'student_id',
            'module__course_id',
            'module__course__title'
        )
        .annotate(
            total_modules=Count('module', distinct=True),
            completed_modules=Count(
                'module',
                filter=Q(state='completed'),
                distinct=True
            ),
            started_modules=Count(
                'module',
                filter=Q(state__in=['in_progress', 'completed']),
                distinct=True
            ),
        )
    )

    if course_id:
        qs = qs.filter(module__course_id=course_id)

    return qs

def derive_course_status(row):
    if row['started_modules'] == 0:
        return 'not_started'
    if row['completed_modules'] == row['total_modules']:
        return 'completed'
    return 'in_progress'

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all().select_related('user', 'package').prefetch_related('add_ons')
    serializer_class = PaymentSerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Payment.objects.all().select_related('user', 'package').prefetch_related('add_ons')
        return Payment.objects.filter(user=user).select_related('user', 'package').prefetch_related('add_ons')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PaymentDetailSerializer
        return PaymentSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['post'], permission_classes=[IsStudent], url_path='initiate-package')
    def initiate_package(self, request):
        """
        Initiate payment for a package (Basic, Premium, or Add-ons)
        """
        serializer = PackageSelectionSerializer(data=request.data)
        if serializer.is_valid():
            package_id = serializer.validated_data['package_id']
            add_on_ids = serializer.validated_data.get('add_on_ids', [])

            try:
                package = Package.objects.get(id=package_id, is_active=True)
                add_ons = AddOn.objects.filter(id__in=add_on_ids, is_active=True) if add_on_ids else []

                user = request.user

                # Calculate total amount
                total_amount = package.price
                for add_on in add_ons:
                    total_amount += add_on.price

                # Check if user already has an active package enrollment
                existing_enrollment = Enrollment.objects.filter(
                    user=user,
                    package=package,
                    status__in=['active', 'pending_payment']
                ).first()

                if existing_enrollment:
                    if existing_enrollment.status == 'active':
                        return Response(
                            {'error': 'You already have an active subscription for this package'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    elif existing_enrollment.status == 'pending_payment' and existing_enrollment.payment:
                        # Resume existing pending payment
                        payment = existing_enrollment.payment
                        redirect_url = request.build_absolute_uri(
                            reverse('payment-verify', kwargs={'pk': payment.id})
                        )

                        payment_link, flutterwave_ref = create_flutterwave_payment(
                            user=user,
                            package=package,
                            amount=payment.total_amount,
                            redirect_url=redirect_url
                        )

                        if payment_link:
                            payment.flutterwave_ref = flutterwave_ref
                            payment.save()

                            return Response({
                                'payment_id': payment.id,
                                'payment_link': payment_link,
                                'transaction_id': payment.transaction_id,
                                'amount': str(payment.total_amount),
                                'currency': 'NGN',
                                'package': package.name,
                                'add_ons': [add_on.name for add_on in payment.add_ons.all()],
                                'message': 'Existing package payment resumed'
                            })

                # Create new payment
                transaction_id = f"PKG_{user.id}_{package.pk}_{int(time.time())}"
                payment = Payment.objects.create(
                    user=user,
                    package=package,
                    course=package.course,
                    total_amount=total_amount,
                    payment_option='card',  # Default payment option
                    transaction_id=transaction_id,
                    status='pending'
                )

                if add_ons:
                    payment.add_ons.set(add_ons)

                redirect_url = request.build_absolute_uri(
                    reverse('payment-verify', kwargs={'pk': payment.pk})
                )

                payment_link, flutterwave_ref = create_flutterwave_payment(
                    user=user,
                    package=package,
                    amount=total_amount,
                    redirect_url=redirect_url
                )

                if payment_link and flutterwave_ref:
                    payment.flutterwave_ref = flutterwave_ref
                    payment.save()

                    # Create or update enrollment
                    enrollment, created = Enrollment.objects.get_or_create(
                        user=user,
                        package=package,
                        defaults={
                            'payment': payment,
                            'status': 'pending_payment'
                        }
                    )

                    if not created:
                        enrollment.payment = payment
                        enrollment.status = 'pending_payment'
                        enrollment.expires_at = None
                        enrollment.save()

                    if add_ons:
                        enrollment.add_ons.set(add_ons)

                    return Response({
                        'payment_id': payment.pk,
                        'payment_link': payment_link,
                        'transaction_id': transaction_id,
                        'amount': str(total_amount),
                        'currency': 'NGN',
                        'package': package.name,
                        'add_ons': [add_on.name for add_on in add_ons],
                        'message': 'Package payment initiated successfully'
                    })
                else:
                    payment.status = 'failed'
                    payment.save()
                    return Response(
                        {'error': 'Failed to initialize payment gateway. Please try again.'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )

            except Package.DoesNotExist:
                return Response(
                    {'error': 'Package not found or inactive'},
                    status=status.HTTP_404_NOT_FOUND
                )
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        return Response(
            {
                'error': 'Invalid data provided',
                'details': serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, methods=['get'], permission_classes=[IsStudent], url_path='verify')
    def verify(self, request, pk=None):
        payment = self.get_object()

        transaction_id = request.query_params.get('transaction_id')
        status_param = request.query_params.get('status')

        if payment.status != 'pending':
            return Response(
                {'error': 'Payment already processed'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if status_param == 'cancelled':
            payment.status = 'abandoned'
            payment.save()

            # Update enrollment status
            enrollment = Enrollment.objects.filter(payment=payment).first()
            if enrollment:
                enrollment.status = 'dropped'
                enrollment.save()

            return Response({
                'status': 'cancelled',
                'message': 'Payment was cancelled',
                'payment_id': payment.id
            })

        if transaction_id:
            success, response = verify_flutterwave_payment(transaction_id)

            if success:
                payment.status = 'completed'
                payment.transaction_id = transaction_id
                payment.save()

                enrollment = Enrollment.objects.filter(payment=payment).first()
                if enrollment:
                    enrollment.status = 'active'
                    enrollment.save()

                response_data = {
                    'status': 'completed',
                    'message': 'Payment verified successfully',
                    'payment_id': payment.id,
                    'enrollment_id': enrollment.pk if enrollment else None,
                    'package_name': payment.package.name if payment.package else None
                }

                return Response(response_data)
            else:
                payment.status = 'failed'
                payment.save()

                enrollment = Enrollment.objects.filter(payment=payment).first()
                if enrollment:
                    enrollment.status = 'dropped'
                    enrollment.save()

                return Response({
                    'status': 'failed',
                    'error': 'Payment verification failed',
                    'payment_id': payment.id
                }, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {'error': 'Transaction ID is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='my-payments')
    def user_payments(self, request):
        payments = Payment.objects.filter(user=request.user).select_related('package').prefetch_related('add_ons')
        serializer = self.get_serializer(payments, many=True)
        return Response(serializer.data)

    def get_permissions(self):
        if self.action in ['create', 'initiate_package', 'user_payments']:
            return [IsStudent()]
        elif self.action in ['list']:
            return [IsAuthenticated()]
        elif self.action in ['retrieve', 'update', 'partial_update', 'destroy', 'verify']:
            return [IsAuthenticated(), IsOwnerOrAdmin()]
        return [AllowAny()]

class EnrollmentViewSet(viewsets.ModelViewSet):
    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Enrollment.objects.all().select_related('user', 'package', 'payment').prefetch_related('add_ons')
        return Enrollment.objects.filter(user=user).select_related('user', 'package', 'payment').prefetch_related(
            'add_ons')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return EnrollmentDetailSerializer
        return EnrollmentSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def user_enrollments(self, request):
        enrollments = Enrollment.objects.filter(user=request.user).select_related('package',
                                                                                  'payment').prefetch_related('add_ons')
        serializer = self.get_serializer(enrollments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        monthly_revenue = Payment.get_monthly_revenue()
        return Response({
            "monthly_revenue": monthly_revenue,
            # add other stats here
        })

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def total_enrolled(self, request):
        """
        Returns total number of active enrollments.
        Staff/admins see all, normal users only see their own.
        """
        qs = self.get_queryset().filter(status="active")
        count = qs.count()
        return Response({"total_enrolled": count})

    @action(detail=True, methods=['post'], permission_classes=[IsStudent])
    def cancel(self, request, pk=None):
        enrollment = self.get_object()

        if enrollment.status == 'active':
            enrollment.status = 'dropped'
            enrollment.save()

            return Response({
                'message': 'Enrollment cancelled successfully',
                'enrollment_id': enrollment.id
            })
        else:
            return Response(
                {'error': 'Cannot cancel this enrollment'},
                status=status.HTTP_400_BAD_REQUEST
            )

    def get_permissions(self):
        if self.action in ['create', 'cancel']:
            return [IsStudent()]
        elif self.action in ['list', 'user_enrollments']:
            return [IsAuthenticated()]
        elif self.action in ['retrieve', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsOwnerOrAdmin()]
        return [AllowAny()]

class PackageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Package.objects.filter(is_active=True)
    serializer_class = PackageSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = Package.objects.filter(is_active=True)
        course_id = self.request.query_params.get('course')

        if course_id:
            queryset = queryset.filter(course_id=course_id)

        return queryset


class AddOnViewSet(viewsets.ReadOnlyModelViewSet):
    # Fix: Show Active features, not Inactive ones
    queryset = AddOn.objects.filter(is_active=True)
    serializer_class = AddOnSerializer

    def get_permissions(self):
        """
        Allow anyone to view the list, but only logged-in users to buy.
        """
        if self.action == 'purchase':
            return [IsAuthenticated, IsStudent]
        return [AllowAny]

    @action(detail=True, methods=['post'])
    def purchase(self, request, pk=None):
        """
        Endpoint: POST /api/addons/{id}/purchase/
        Body: {"course_id": 12}
        """
        addon = self.get_object()
        user = request.user

        # 1. Get the specific course they want this Add-on for
        course_id = request.data.get('course_id')
        if not course_id:
            return Response(
                {"error": "course_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        course = get_object_or_404(Course, pk=course_id)

        # 2. Prevent Double Buying (Optional but recommended)
        # e.g., If they are already Premium, don't let them buy Premium again
        if 'premium' in addon.feature.name.lower():
            enrollment = user.enrollments.filter(course=course).first()
            if enrollment and enrollment.package.package_type == 'premium':
                return Response(
                    {"error": "You are already a Premium student for this course."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # 3. Initiate Flutterwave Payment
        try:
            # call the service function we wrote earlier
            success, data = initiate_addon_payment(user, addon, course)

            if success:
                return Response({
                    "message": "Payment initiated",
                    "payment_link": data['link'],  # URL from Flutterwave
                    "tx_ref": data['tx_ref']
                })
            else:
                return Response(
                    {"error": "Could not initiate payment", "details": data},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            return Response({"error": str(e)}, status=500)

class AdminPaymentStatsViewSet(viewsets.ViewSet):
    permission_classes = [IsAdminUser]

    @action(detail=False, methods=['get'], url_path='monthly-comparison')
    def monthly_comparison(self, request):
        now = timezone.now()

        # Current month range
        current_start, current_end = month_range(now)

        # Previous month range
        last_month = (current_start - timedelta(days=1))
        previous_start, previous_end = month_range(last_month)

        # ─────────────────────────────
        # Revenue (Payments)
        # ─────────────────────────────
        current_revenue = Payment.objects.filter(
            status='completed',
            created_at__gte=current_start,
            created_at__lt=current_end
        ).aggregate(total=Sum('total_amount'))['total'] or 0

        previous_revenue = Payment.objects.filter(
            status='completed',
            created_at__gte=previous_start,
            created_at__lt=previous_end
        ).aggregate(total=Sum('total_amount'))['total'] or 0

        # Percentage change
        if previous_revenue > 0:
            revenue_change = (
                            (current_revenue - previous_revenue) / previous_revenue
                             ) * 100
        else:
            revenue_change = 100 if current_revenue > 0 else 0

        # ─────────────────────────────
        # Payouts (optional but useful)
        # ─────────────────────────────
        current_payouts = Payout.objects.filter(
            status='completed',
            created_at__gte=current_start,
            created_at__lt=current_end
        ).aggregate(total=Sum('amount'))['total'] or 0

        previous_payouts = Payout.objects.filter(
            status='completed',
            created_at__gte=previous_start,
            created_at__lt=previous_end
        ).aggregate(total=Sum('amount'))['total'] or 0

        return Response({
            "current_month": {
                "revenue": current_revenue,
                "payouts": current_payouts,
                "net": current_revenue - current_payouts
            },
            "previous_month": {
                "revenue": previous_revenue,
                "payouts": previous_payouts,
                "net": previous_revenue - previous_payouts
            },
            "revenue_change_percentage": round(revenue_change, 2)
        })

    @action(detail=False, methods=['get'], url_path='overview')
    def overview(self, request):
        now = timezone.now()

        total_revenue = Payment.objects.filter(
            status='completed'
        ).aggregate(total=Sum('total_amount'))['total'] or 0

        monthly_revenue = Payment.objects.filter(
            status='completed',
            created_at__year=now.year,
            created_at__month=now.month
        ).aggregate(total=Sum('total_amount'))['total'] or 0

        monthly_payouts = Payout.objects.filter(
            status='completed',
            created_at__year=now.year,
            created_at__month=now.month
        ).aggregate(total=Sum('amount'))['total'] or 0

        total_payouts = Payout.objects.filter(
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0

        pending_payouts = Payout.objects.filter(
            status='pending'
        ).aggregate(total=Sum('amount'))['total'] or 0

        return Response({
            "total_revenue": total_revenue,
            "revenue_this_month": monthly_revenue,
            "total_payouts": total_payouts,
            "pending_payouts": pending_payouts,
            "net_revenue": monthly_revenue - total_payouts
        })

class AdminPayoutViewSet(viewsets.ModelViewSet):
    """
    Admin-only payout management
    """
    queryset = Payout.objects.select_related('recipient').order_by('-created_at')
    serializer_class = PayoutSerializer
    permission_classes = [IsAdminUser]

    @action(detail=True, methods=['post'])
    def process_payout(self, request, pk=None):
        """
        Endpoint: POST /api/payouts/{id}/process_payout/
        """
        payout = self.get_object()

        if payout.status != 'pending':
            return Response(
                {'error': 'Payout is not pending'},
                status=status.HTTP_400_BAD_REQUEST
            )

        success, data = initiate_flutterwave_transfer(payout)

        if success:
            return Response({'status': 'Payout Initiated', 'data': data})
        else:
            return Response(
                {'error': 'Payout Failed', 'details': data},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='mark-completed')
    def mark_completed(self, request, pk=None):
        payout = self.get_object()

        if payout.status != 'pending':
            return Response(
                {'detail': 'Only pending payouts can be completed.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        payout.status = 'completed'
        payout.completed_at = timezone.now()
        payout.save(update_fields=['status', 'completed_at'])

        return Response({'detail': 'Payout marked as completed.'})

    @action(detail=True, methods=['post'], url_path='mark-failed')
    def mark_failed(self, request, pk=None):
        payout = self.get_object()

        if payout.status != 'pending':
            return Response(
                {'detail': 'Only pending payouts can be failed.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        payout.status = 'failed'
        payout.notes = request.data.get('notes', payout.notes)
        payout.save(update_fields=['status', 'notes'])

        return Response({'detail': 'Payout marked as failed.'})

    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        total = Payout.objects.count()

        aggregates = Payout.objects.aggregate(
            total_amount=Sum('amount'),
            completed_amount=Sum('amount', filter=Q(status='completed')),
            pending_amount=Sum('amount', filter=Q(status='pending')),
            failed_amount=Sum('amount', filter=Q(status='failed'))
        )


        return Response({
            'total_payouts': total,
            'total_amount': aggregates['total_amount'] or 0,
            'completed_amount': aggregates['completed_amount'] or 0,
            'pending_amount': aggregates['pending_amount'] or 0,
            'failed_amount': aggregates['failed_amount'] or 0,
        })

    def get_queryset(self):
        request = self.request
        queryset = super().get_queryset()
        status_param = request.query_params.get('status')
        recipient_param = request.query_params.get('recipient')

        if status_param:
            queryset = queryset.filter(status=status_param)
        if recipient_param:
            queryset = queryset.filter(recipient__id=recipient_param)
        return queryset

class AdminAnalyticsViewSet(viewsets.ViewSet):
    """
    Admin analytics for Revenue, Students and Expenses
    """
    permission_classes = [IsAdminUser]

    @action(detail=False, methods=['get'], url_path='revenue/summary')
    def revenue_summary(self, request: Request):
        total_revenue = Payment.objects.filter(
            status='completed'
        ).aggregate(total=Sum('total_amount'))['total'] or 0

        total_payouts = Payout.objects.filter(
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0

        return Response({
            'total_revenue': total_revenue,
            'total_payouts': total_payouts,
            'profit': total_revenue - total_payouts
        })

    @action(detail=False, methods=['get'], url_path='revenue/by-course')
    def revenue_by_course(self, request: Request):
        search = request.query_params.get('search')
        month = request.query_params.get('month')  # YYYY-MM

        payments = Payment.objects.filter(status='completed').select_related('course')

        if month:
            year, m = map(int, month.split('-'))
            payments = payments.filter(
                created_at__year=year,
                created_at__month=m
            )

        if search:
            payments = payments.filter(course__title__icontains=search)

        revenue_data = (
            payments
            .values('course_id', 'course__title')
            .annotate(revenue=Sum('total_amount'))
        )

        results = []

        for row in revenue_data:
            payouts = Payout.objects.filter(
                status='completed'
            ).aggregate(total=Sum('amount'))['total'] or 0

            profit = row['revenue'] - payouts
            margin = (profit / row['revenue'] * 100) if row['revenue'] else 0

            results.append({
                'course': row['course__title'],
                'revenue': row['revenue'],
                'tutor_payout': payouts,
                'profit': profit,
                'profit_margin': round(margin, 2)
            })

        return Response(results)

    @action(detail=False, methods=['get'], url_path='students/summary')
    def students_summary(self, request: Request):
        return Response({
            'total_students': User.objects.filter(role='student').count(),
            'active_students': Enrollment.objects.filter(status='active')
            .values('user').distinct().count(),
            'total_enrollments': Enrollment.objects.count(),
        })

    @action(detail=False, methods=['get'], url_path='students/course-completion')
    def course_completion(self, request: Request):
        course_id = request.query_params.get('course')

        qs = Enrollment.objects.all()
        if course_id:
            qs = qs.filter(package__course_id=course_id)

        return Response({
            'completed': qs.filter(status='completed').count(),
            'in_progress': qs.filter(status='active').count(),
            'not_started': qs.filter(status='pending_payment').count(),
        })

    @action(detail=False, methods=['get'], url_path='students/engagement')
    def student_engagement(self, request: Request):
        period = request.query_params.get('period', 'month')

        trunc = TruncWeek if period == 'week' else TruncMonth

        data = (
            Enrollment.objects.filter(status='active')
            .annotate(period=trunc('enrolled_at'))
            .values('period')
            .annotate(active_students=Count('user', distinct=True))
            .order_by('period')
        )

        return Response(data)

    @action(detail=False, methods=['get'], url_path='students/progress')
    def student_progress(self, request):
        course_id = request.query_params.get('course_id')
        search = request.query_params.get('search')

        qs = (
            ModuleCompletion.objects
            .select_related('student', 'module__course')
            .values(
                'student_id',
                'student__first_name',
                'student__last_name',
                'student__email',
                'module__course_id',
                'module__course__title',
            )
            .annotate(
                total_modules=Count('module', distinct=True),
                completed_modules=Count(
                    'module',
                    filter=Q(state='completed'),
                    distinct=True
                ),
                started_modules=Count(
                    'module',
                    filter=Q(state__in=[
                        ContentState.IN_PROGRESS.value,
                        ContentState.COMPLETED.value
                    ]),
                    distinct=True
                ),
                avg_progress=Avg('completion_percentage'),
            )
        )


        # Optional filters
        if course_id:
            qs = qs.filter(module__course_id=course_id)

        if search:
            qs = qs.filter(
                Q(student__first_name__icontains=search) |
                Q(student__last_name__icontains=search) |
                Q(student__email__icontains=search)
            )

        # Build response
        results = []
        for row in qs:
            if row['started_modules'] == 0:
                status = 'not_started'
            elif row['completed_modules'] == row['total_modules']:
                status = 'completed'
            else:
                status = 'in_progress'

            progress = (
                round((row['completed_modules'] / row['total_modules']) * 100, 2)
                if row['total_modules'] > 0 else 0
            )

            results.append({
                'student': {
                    'id': row['student_id'],
                    'name': f"{row['student__first_name']} {row['student__last_name']}",
                    'email': row['student__email'],
                },
                'course': {
                    'id': row['module__course_id'],
                    'title': row['module__course__title'],
                },
                'progress_percentage': progress,
                'status': status,
            })

        return Response(results)

    @action(detail=False, methods=['get'], url_path='expenses/revenue-vs-expenses')
    def revenue_vs_expenses(self, request: Request):
        period = request.query_params.get('period', 'month')
        trunc = TruncWeek if period == 'week' else TruncMonth

        revenue = (
            Payment.objects.filter(status='completed')
            .annotate(period=trunc('created_at'))
            .values('period')
            .annotate(amount=Sum('total_amount'))
        )

        expenses = (
            Payout.objects.filter(status='completed')
            .annotate(period=trunc('created_at'))
            .values('period')
            .annotate(amount=Sum('amount'))
        )

        return Response({
            'revenue': revenue,
            'expenses': expenses
        })

    @action(detail=False, methods=['get'], url_path='expenses/breakdown')
    def expenses_breakdown(self, request: Request):
        month = request.query_params.get('month')

        qs = Payout.objects.all()

        if month:
            year, m = map(int, month.split('-'))
            qs = qs.filter(created_at__year=year, created_at__month=m)

        return Response(qs.values(
            'created_at',
            'payment_method',
            'notes',
            'amount',
            'status'
        ))

    # come back to this
    @action(detail=False, methods=['get'], url_path='revenue/by-course/export')
    def export_revenue_by_course(self, request: Request):
        export_format = request.query_params.get('format', 'csv')

        data = (
            Payment.objects
            .filter(status='completed')
            .values('course__title')
            .annotate(revenue=Sum('total_amount'))
        )

        rows = []
        for row in data:
            payouts = Payout.objects.filter(status='completed').aggregate(
                total=Sum('amount')
            )['total'] or 0

            profit = row['revenue'] - payouts
            margin = (profit / row['revenue'] * 100) if row['revenue'] else 0

            rows.append([
                row['course__title'],
                row['revenue'],
                payouts,
                profit,
                round(margin, 2)
            ])

        headers = [
            'Course',
            'Revenue Earned',
            'Tutor Payouts',
            'Profit',
            'Profit Margin (%)'
        ]

        if export_format == 'excel':
            return export_excel('revenue_by_course', headers, rows)

        return export_csv('revenue_by_course', headers, rows)

    @action(detail=False, methods=['get'], url_path='students-progress-export')
    def export_student_progress(self, request: Request):
        export_format = request.query_params.get('format', 'csv')
        user = request.user

        # 1. Define a Subquery to count COMPLETED modules for each student/course pair
        #    This asks: "Count ModuleCompletion rows where student=current_user
        #    AND course=current_course AND state='completed'"
        completed_modules_sq = ModuleCompletion.objects.filter(
            student=OuterRef('user'),
            module__course=OuterRef('package__course'),
            state=ContentState.COMPLETED.value
        ).values('student').annotate(
            cnt=Count('id')
        ).values('cnt')

        # 2. Fetch Enrollments with all necessary data annotated in one go
        #    - select_related: Grabs User and Course data
        #    - total_modules: Counts how many modules exist in the course
        #    - completed_count: Runs the subquery above
        qs = Enrollment.objects.select_related(
            'user',
            'package__course'
        ).annotate(
            total_modules=Count('package__course__modules', distinct=True),
            completed_count=Coalesce(Subquery(completed_modules_sq, output_field=IntegerField()), 0)
        )

        rows = []

        # 3. Iterate and Calculate Percentage in Python
        for enrollment in qs:
            # Safety check: avoid dividing by zero if a course has 0 modules
            course = enrollment.package.course if (enrollment.package and enrollment.package.course) else None

            if course:
                # 2. Pass it to your helper function
                percentage = get_course_completion_percentage(enrollment.user, course)
            else:
                percentage = 0.0

            # Handle N/A cases for course title
            course_title = enrollment.package.course.title if enrollment.package and enrollment.package.course else "N/A"

            rows.append([
                enrollment.user.username,
                course_title,
                percentage,
                enrollment.status
            ])

        headers = ['Student', 'Course', 'Progress (%)', 'Status']

        if export_format == 'excel':
            return export_excel('student_progress', headers, rows)

        return export_csv('student_progress', headers, rows)

    @action(detail=False, methods=['get'], url_path='expenses/export')
    def export_expenses(self, request: Request):
        export_format = request.query_params.get('format', 'csv')

        qs = Payout.objects.select_related('recipient')

        rows = qs.values_list(
            'created_at',
            'recipient__email',
            'payment_method',
            'amount',
            'status'
        )

        headers = [
            'Date',
            'Recipient',
            'Payment Method',
            'Amount',
            'Status'
        ]

        if export_format == 'excel':
            return export_excel('expenses', headers, rows)

        return export_csv('expenses', headers, rows)

    @action(detail=False, methods=['get'], url_path='payouts/export')
    def export_payouts(self, request: Request):
        export_format = request.query_params.get('format', 'csv')

        qs = Payout.objects.select_related('recipient')

        rows = qs.values_list(
            'reference',
            'recipient__email',
            'amount',
            'payment_method',
            'status',
            'created_at'
        )

        headers = [
            'Reference',
            'Recipient',
            'Amount',
            'Payment Method',
            'Status',
            'Date'
        ]

        if export_format == 'excel':
            return export_excel('payouts', headers, rows)

        return export_csv('payouts', headers, rows)


    @action(
        detail=False,
        methods=['get'],
        url_path='revenue/monthly',
        permission_classes=[IsAdminUser]
    )
    def monthly_revenue_comparison(self, request):
        # Parse month (YYYY-MM)
        month_param = request.query_params.get('month')

        now = timezone.now()
        if month_param:
            year, month = map(int, month_param.split('-'))
        else:
            year, month = now.year, now.month

        # Current month range
        start, end = get_month_range(year, month)

        # Previous month
        prev_date = start - timedelta(days=1)
        prev_start, prev_end = get_month_range(prev_date.year, prev_date.month)

        # ---- CURRENT MONTH ----
        current_revenue = (
                Payment.objects.filter(
                    status='completed',
                    created_at__gte=start,
                    created_at__lt=end
                ).aggregate(total=Sum('total_amount'))['total'] or 0
        )

        current_payouts = (
                Payout.objects.filter(
                    status='completed',
                    created_at__gte=start,
                    created_at__lt=end
                ).aggregate(total=Sum('amount'))['total'] or 0
        )

        # ---- PREVIOUS MONTH ----
        prev_revenue = (
                Payment.objects.filter(
                    status='completed',
                    created_at__gte=prev_start,
                    created_at__lt=prev_end
                ).aggregate(total=Sum('total_amount'))['total'] or 0
        )

        prev_payouts = (
                Payout.objects.filter(
                    status='completed',
                    created_at__gte=prev_start,
                    created_at__lt=prev_end
                ).aggregate(total=Sum('amount'))['total'] or 0
        )

        # ---- CALCULATIONS ----
        current_profit = current_revenue - current_payouts
        prev_profit = prev_revenue - prev_payouts

        revenue_change = (
            ((current_revenue - prev_revenue) / prev_revenue) * 100
            if prev_revenue else 0
        )

        payout_change = (
            ((current_payouts - prev_payouts) / prev_payouts) * 100
            if prev_payouts else 0
        )

        profit_change = (
            ((current_profit - prev_profit) / prev_profit) * 100
            if prev_profit else 0
        )

        weekly_trend = (
            Payment.objects
            .filter(status='completed', created_at__gte=start, created_at__lt=end)
            .annotate(week=TruncWeek('created_at'))
            .values('week')
            .annotate(revenue=Sum('total_amount'))
            .order_by('week')
        )

        weekly_payouts = (
            Payout.objects
            .filter(status='completed', created_at__gte=start, created_at__lt=end)
            .annotate(week=TruncWeek('created_at'))
            .values('week')
            .annotate(payouts=Sum('amount'))
        )

        return Response({
            "current_month": {
                "revenue": current_revenue,
                "payouts": current_payouts,
                "profit": current_profit,
            },
            "previous_month": {
                "revenue": prev_revenue,
                "payouts": prev_payouts,
                "profit": prev_profit,
            },
            "comparison": {
                "revenue_change_percent": round(revenue_change, 2),
                "payout_change_percent": round(payout_change, 2),
                "profit_change_percent": round(profit_change, 2),
            },
            "weekly_trend": {
                "revenue": list(weekly_trend),
                "payouts": list(weekly_payouts)
            }
        })

    @action(
        detail=False,
        methods=['get'],
        url_path='revenue/per-course',
        permission_classes=[IsAdminUser]
    )
    def revenue_vs_payouts_per_course(self, request):
        month_param = request.query_params.get('month')
        search = request.query_params.get('search')

        now = timezone.now()
        if month_param:
            year, month = map(int, month_param.split('-'))
        else:
            year, month = now.year, now.month

        start, end = get_month_range(year, month)

        # ---- REVENUE PER COURSE ----
        payments = (
            Payment.objects
            .filter(
                status='completed',
                created_at__gte=start,
                created_at__lt=end
            )
            .select_related('course')
        )

        if search:
            payments = payments.filter(course__title__icontains=search)

        revenue_per_course = (
            payments
            .values('course_id', 'course__title')
            .annotate(revenue=Sum('total_amount'))
            .order_by('course__title')
        )

        # ---- TOTAL PAYOUTS (GLOBAL for now) ----
        total_payouts = (
                Payout.objects
                .filter(
                    status='completed',
                    created_at__gte=start,
                    created_at__lt=end
                )
                .aggregate(total=Sum('amount'))['total'] or 0
        )

        # ---- BUILD RESPONSE ----
        results = []
        total_revenue = sum(item['revenue'] for item in revenue_per_course) or 1

        for item in revenue_per_course:
            revenue = item['revenue']

            # TEMP: proportional payout distribution
            payout_estimate = (revenue / total_revenue) * total_payouts if total_payouts else 0

            profit = revenue - payout_estimate
            margin = (profit / revenue) * 100 if revenue else 0

            results.append({
                "course_id": item['course_id'],
                "course": item['course__title'],
                "revenue_earned": round(revenue, 2),
                "payouts": round(payout_estimate, 2),
                "profit": round(profit, 2),
                "profit_margin_percent": round(margin, 2),
            })

        return Response({
            "month": f"{year}-{month:02d}",
            "results": results,
            "totals": {
                "total_revenue": round(total_revenue, 2),
                "total_payouts": round(total_payouts, 2),
                "total_profit": round(total_revenue - total_payouts, 2),
            }
        })

    @action(detail=False, methods=['get'], url_path='revenue-vs-payouts')
    def revenue_vs_payouts(self, request):
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        search = request.query_params.get('search')

        payment_filter = Q(status='completed')
        payout_filter = Q(status='completed')

        if month and year:
            payment_filter &= Q(created_at__month=month, created_at__year=year)
            payout_filter &= Q(created_at__month=month, created_at__year=year)

        courses = Course.objects.all()

        if search:
            courses = courses.filter(title__icontains=search)

        data = []

        for course in courses:
            revenue = (
                    Payment.objects
                    .filter(payment_filter, course=course)
                    .aggregate(total=Sum('total_amount'))['total']
                    or 0
            )

            payouts = (
                    Payout.objects
                    .filter(payout_filter, course=course)
                    .aggregate(total=Sum('amount'))['total']
                    or 0
            )

            profit = revenue - payouts
            profit_margin = (
                round((profit / revenue) * 100, 2)
                if revenue > 0 else 0
            )

            data.append({
                'course': {
                    'id': course.id,
                    'title': course.title,
                },
                'revenue_earned': revenue,
                'tutor_payouts': payouts,
                'profit': profit,
                'profit_margin': profit_margin,
            })

        return Response(data)

    @action(
        detail=False,
        methods=['get'],
        url_path='revenue/weekly',
        permission_classes=[IsAdminUser]
    )
    def revenue_vs_payouts_weekly(self, request):
        month_param = request.query_params.get('month')
        now = timezone.now()

        if month_param:
            year, month = map(int, month_param.split('-'))
        else:
            year, month = now.year, now.month

        weeks = get_week_ranges(year, month)

        data = []

        for w in weeks:
            revenue = (
                    Payment.objects
                    .filter(
                        status='completed',
                        created_at__gte=w['start'],
                        created_at__lt=w['end']
                    )
                    .aggregate(total=Sum('total_amount'))['total'] or 0
            )

            payouts = (
                    Payout.objects
                    .filter(
                        status='completed',
                        created_at__gte=w['start'],
                        created_at__lt=w['end']
                    )
                    .aggregate(total=Sum('amount'))['total'] or 0
            )

            data.append({
                "week": f"Week {w['week']}",
                "revenue": round(revenue, 2),
                "payouts": round(payouts, 2),
                "profit": round(revenue - payouts, 2)
            })

        return Response({
            "month": f"{year}-{month:02d}",
            "data": data
        })

    @action(
        detail=False,
        methods=['get'],
        url_path='students/engagement',
        permission_classes=[IsAdminUser]
    )
    def student_engagement_weekly(self, request):
        month_param = request.query_params.get('month')
        now = timezone.now()

        if month_param:
            year, month = map(int, month_param.split('-'))
        else:
            year, month = now.year, now.month

        weeks = get_week_ranges(year, month)
        results = []

        for w in weeks:
            attendances = LiveSessionAttendance.objects.filter(
                joined_at__gte=w['start'],
                joined_at__lt=w['end']
            ).select_related('live_session')

            active_students = set()

            for attendance in attendances:
                session = attendance.live_session

                # Enforce minimum attendance if mandatory
                if session.is_mandatory:
                    if attendance.attended_minutes < session.minimum_attendance_minutes:
                        continue

                active_students.add(attendance.student_id)

            results.append({
                "week": f"Week {w['week']}",
                "active_students": len(active_students)
            })

        return Response({
            "month": f"{year}-{month:02d}",
            "weekly_engagement": results
        })

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAdminUser],
        url_path='analytics/course-completion'
    )
    def course_completion_overview(self, request):
        course_id = request.query_params.get('course_id')

        rows = get_course_completion_queryset(course_id)

        summary = {}

        for row in rows:
            course_key = (
                row['module__course_id'],
                row['module__course__title']
            )

            if course_key not in summary:
                summary[course_key] = {
                    'course_id': row['module__course_id'],
                    'course_title': row['module__course__title'],
                    'completed': 0,
                    'in_progress': 0,
                    'not_started': 0,
                    'total_students': 0
                }

            status = derive_course_status(row)

            summary[course_key][status] += 1
            summary[course_key]['total_students'] += 1

        return Response({
            'filters': {
                'course_id': course_id or 'all'
            },
            'results': list(summary.values())
        })

class AdminCertificateRequestViewSet(viewsets.ModelViewSet):
    """
    Admin management of certificate requests
    """
    queryset = CertificateRequest.objects.select_related(
        'student', 'course'
    ).order_by('-requested_at')

    serializer_class = CertificateRequestSerializer
    permission_classes = [IsAdminUser]


    def get_queryset(self):
        qs = super().get_queryset()

        status_param = self.request.query_params.get('status')
        course_id = self.request.query_params.get('course')
        search = self.request.query_params.get('search')

        if status_param:
            qs = qs.filter(status=status_param)

        if course_id:
            qs = qs.filter(course_id=course_id)

        if search:
            qs = qs.filter(
                student__email__icontains=search
            ) | qs.filter(
                student__first_name__icontains=search
            )

        return qs

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        cert_request = self.get_object()

        if cert_request.status != CertificateRequest.STATUS_PENDING:
            return Response(
                {'detail': 'Only pending requests can be approved.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Optional: ensure payment completed
        payment = CertificatePayment.objects.filter(
            certificate_request=cert_request,
            status='paid'
        ).first()

        if not payment:
            return Response(
                {'detail': 'Certificate payment not completed.'},
                status=status.HTTP_400_BAD_REQUEST
            )

            # ---- Prevent duplicate issuance ----
        if Certificate.objects.filter(certificate_request=cert_request).exists():
            return Response(
                {'detail': 'Certificate already issued for this request.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        cert_request.last_previewed_at = timezone.now()
        cert_request.last_previewed_by = request.user
        cert_request.save(update_fields=['last_previewed_at', 'last_previewed_by'])

        if not cert_request.last_previewed_at:
            return Response(
                {'detail': 'Certificate must be previewed before approval.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Issue certificate
        with transaction.atomic():
            certificate = Certificate.objects.create(
                certificate_request=cert_request,
                student=cert_request.student,
                course=cert_request.course,
                issued_at=timezone.now()
            )

            # Generate and attach PDF
            generate_certificate_pdf(certificate)

            # Send email (non-blocking logic)
            send_certificate_email(certificate)

            # Update request
            cert_request.status = CertificateRequest.STATUS_APPROVED
            cert_request.approved_at = timezone.now()
            cert_request.approved_by = request.user
            cert_request.save(
                update_fields=['status', 'approved_at', 'approved_by']
            )

        return Response({
            'detail': 'Certificate approved and issued.',
            'certificate_id': certificate.id
        })

    @action(detail=True, methods=['post'], url_path='deny')
    def deny(self, request, pk=None):
        cert_request = self.get_object()
        reason = request.data.get('reason')

        if not reason:
            return Response(
                {'detail': 'Denial reason is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        cert_request.status = CertificateRequest.STATUS_DENIED
        cert_request.reason = reason
        cert_request.save(update_fields=['status', 'reason'])

        return Response({'detail': 'Certificate request denied.'})

    @action(detail=True, methods=['post'], url_path='reissue')
    def reissue(self, request, pk=None):
        cert_request = self.get_object()

        if cert_request.status != CertificateRequest.STATUS_APPROVED:
            return Response(
                {'detail': 'Only approved certificates can be re-issued.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not cert_request.last_previewed_at:
            return Response(
                {'detail': 'Certificate must be previewed before approval.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        certificate = Certificate.objects.create(
            certificate_request=cert_request,
            student=cert_request.student,
            course=cert_request.course,
            issued_at=timezone.now()
        )

        from module.services import generate_certificate_pdf
        generate_certificate_pdf(certificate)

        return Response({
            'detail': 'Certificate re-issued successfully.',
            'certificate_id': certificate.id
        })

    @action(detail=True, methods=['post'], url_path='reissue-preview')
    def reissue_preview(self, request, pk=None):
        cert_request = self.get_object()

        cert_request.last_previewed_at = timezone.now()
        cert_request.last_previewed_by = request.user
        cert_request.save(update_fields=['last_previewed_at', 'last_previewed_by'])

        if cert_request.status != CertificateRequest.STATUS_APPROVED:
            return Response(
                {'detail': 'Only approved certificates can be re-issued.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from module.services import generate_certificate_reissue_preview_pdf
        return generate_certificate_reissue_preview_pdf(cert_request)

    @action(detail=True, methods=['post'], url_path='preview')
    def preview(self, request, pk=None):
        cert_request = self.get_object()

        cert_request.last_previewed_at = timezone.now()
        cert_request.last_previewed_by = request.user
        cert_request.save(update_fields=['last_previewed_at', 'last_previewed_by'])

        if cert_request.status != CertificateRequest.STATUS_PENDING:
            return Response(
                {'detail': 'Only pending requests can be previewed.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return generate_certificate_preview_pdf(cert_request)

class AdminCertificateViewSet(viewsets.ModelViewSet):
    queryset = Certificate.objects.select_related('student', 'course')
    serializer_class = CertificateSerializer
    permission_classes = [IsAdminUser]

    @action(detail=True, methods=['post'], url_path='revoke')
    def revoke(self, request, pk=None):
        certificate = self.get_object()
        reason = request.data.get('reason', '')

        # FIX: Update the status field instead of a non-existent boolean
        certificate.status = 'revoked'
        certificate.revoked_at = timezone.now()

        # Save the specific fields
        certificate.save(update_fields=['status', 'revoked_at'])

        return Response({
            'detail': 'Certificate revoked successfully.',
            'status': certificate.status,
            'reason': reason
        })

class AdminCertificatePaymentViewSet(viewsets.ModelViewSet):
        queryset = CertificatePayment.objects.select_related('student', 'course')
        permission_classes = [IsAdminUser]

        @action(detail=True, methods=['post'], url_path='mark-paid')
        def mark_paid(self, request, pk=None):
            payment = self.get_object()

            if payment.status == 'paid':
                return Response(
                    {'detail': 'Payment is already marked as paid.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            with transaction.atomic():
                # 1. Update Payment
                payment.status = 'paid'
                payment.save(update_fields=['status'])

                # FIX 2: Find the request manually using Student + Course
                # Since you can't do payment.certificate_request, we look it up.
                cert_request = CertificateRequest.objects.filter(
                    student=payment.student,
                    course=payment.course
                ).first()

                # 3. Update the Request if found
                if cert_request and cert_request.status == 'payment_pending':
                    cert_request.status = 'issued'
                    cert_request.save(update_fields=['status'])

                    # Optional: You can trigger the PDF generation here if you want

            return Response({
                'detail': 'Payment marked as paid and request status updated.',
                'status': payment.status
            })

        @action(detail=False, methods=['get'], url_path='stats')
        def stats(self, request):
            return Response({
                'total_requests': CertificateRequest.objects.count(),

                # FIX 1: Use status='issued' instead of is_revoked=False
                'issued': Certificate.objects.filter(status='issued').count(),

                'pending': CertificateRequest.objects.filter(status='pending').count(),
                'denied': CertificateRequest.objects.filter(status='denied').count(),

                # FIX 2: Use status='revoked' instead of is_revoked=True
                'revoked': Certificate.objects.filter(status='revoked').count(),
            })
