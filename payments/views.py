import time
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from .utils import create_flutterwave_payment, verify_flutterwave_payment
from .models import Package, AddOn, Payment, Enrollment
from .serializers import (
    PaymentSerializer, EnrollmentSerializer, PackageSerializer, AddOnSerializer,
    PackageSelectionSerializer, PaymentDetailSerializer, EnrollmentDetailSerializer
)
from .permissions import IsStudent, IsOwnerOrAdmin
from rest_framework.permissions import AllowAny, IsAuthenticated


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
                transaction_id = f"PKG_{user.id}_{package.id}_{int(time.time())}"
                payment = Payment.objects.create(
                    user=user,
                    package=package,
                    total_amount=total_amount,
                    payment_option='card',  # Default payment option
                    transaction_id=transaction_id,
                    status='pending'
                )

                if add_ons:
                    payment.add_ons.set(add_ons)

                redirect_url = request.build_absolute_uri(
                    reverse('payment-verify', kwargs={'pk': payment.id})
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
                        'payment_id': payment.id,
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
                    {'error': 'An unexpected error occurred. Please try again.'},
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
                    'enrollment_id': enrollment.id if enrollment else None,
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


class AddOnViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AddOn.objects.filter(is_active=True)
    serializer_class = AddOnSerializer
    permission_classes = [AllowAny]