import json
import hmac
import hashlib
from datetime import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from .models import Payment, Enrollment
from .utils import verify_flutterwave_payment, verify_flutterwave_webhook_signature
from module.models import CertificatePayment, CertificateRequest
from payments.models import Payout, Package, AddOn
from module.models import CapstoneFeedbackRequest, ResearchClinic, Course, CapstoneProject
from django.contrib.auth import get_user_model


User = get_user_model()


@csrf_exempt
@require_POST
def flutterwave_webhook(request):
    """
    Handle Flutterwave webhook for payment notifications
    """
    signature_valid, message = verify_flutterwave_webhook_signature(request)
    if not signature_valid:
        return HttpResponse(status=401)

    try:
        payload = json.loads(request.body)
        event = payload.get('event')
        data = payload.get('data', {})

        if event == 'charge.completed':
            tx_ref = data.get('tx_ref', '')
            print(f"Event Received: '{event}'")
            print(f"TX Ref Received: '{tx_ref}'")

            if tx_ref.startswith('COURSE_'):
                return _handle_charge_completed(data)

            elif tx_ref.startswith('CERT-'):
                return _handle_certificate_charge_completed(data)

            elif tx_ref.startswith('ADDON-'):
                print('addon')
                return _handle_addon_charge_completed(data)

            else:
                print(f"⚠️ Unhandled TX Ref: {tx_ref}")
                # Unknown payment reference — acknowledge but log later
                return JsonResponse({
                    'status': 'success',
                    'message': 'Unknown tx_ref type, ignored'
                })

        elif event == 'charge.failed':
            tx_ref = data.get('tx_ref', '')

            if tx_ref.startswith('COURSE_'):
                return _handle_charge_failed(data)

            elif tx_ref.startswith('CERT_'):
                return _handle_certificate_charge_failed(data)

            else:
                return JsonResponse({
                    'status': 'success',
                    'message': 'Unknown tx_ref type, ignored'
                })

        elif event == 'transfer.completed':
            transfer_id = data.get('id')
            status = data.get('status')

            try:
                # Find the payout using the ID we stored earlier
                payout = Payout.objects.get(flutterwave_id=transfer_id)

                if status == 'SUCCESSFUL':
                    payout.status = 'completed'
                    payout.completed_at = timezone.now()
                    payout.notes += "\nwebhook: Transfer Confirmed."
                elif status == 'FAILED':
                    payout.status = 'failed'
                    payout.notes += f"\nwebhook: Bank Rejected - {data.get('complete_message')}"

                payout.save()

            except Payout.DoesNotExist:
                print(f"Payout with FW-ID {transfer_id} not found.")

        else:
            return JsonResponse({
                'status': 'success',
                'message': 'Event acknowledged'
            })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON payload'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Internal server error: {str(e)}'}, status=500)


def _handle_charge_completed(data):
    """
    Handle successful charge completion webhook
    """
    transaction_id = data.get('id')
    tx_ref = data.get('tx_ref')
    status = data.get('status')
    
    try:
        payment = Payment.objects.get(flutterwave_ref=tx_ref)
        
        if payment.status != 'pending':
            return JsonResponse({
                'status': 'success', 
                'message': 'Payment already processed'
            })
        
        if status == 'successful':
            # Verify the transaction for additional security
            success, verification_data = verify_flutterwave_payment(transaction_id)
            
            if success:
                payment.status = 'completed'
                payment.transaction_id = transaction_id
                payment.save()
                
                # Update enrollment status
                enrollment = Enrollment.objects.get(payment=payment)
                enrollment.status = 'active'
                enrollment.save()
                
                return JsonResponse({
                    'status': 'success', 
                    'message': 'Payment completed and enrollment activated'
                })
            else:
                payment.status = 'failed'
                payment.save()
                
                enrollment = Enrollment.objects.get(payment=payment)
                enrollment.status = 'dropped'
                enrollment.save()
                
                return JsonResponse({
                    'status': 'success', 
                    'message': 'Payment verification failed, marked as failed'
                })
        
        elif status == 'failed':
            payment.status = 'failed'
            payment.save()
            
            enrollment = Enrollment.objects.get(payment=payment)
            enrollment.status = 'dropped'
            enrollment.save()
            
            return JsonResponse({
                'status': 'success', 
                'message': 'Payment failed, enrollment dropped'
            })
            
    except Payment.DoesNotExist:
        return JsonResponse({'error': 'Payment not found'}, status=404)
    except Enrollment.DoesNotExist:
        return JsonResponse({'error': 'Enrollment not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'Error processing webhook: {str(e)}'}, status=500)


def _handle_charge_failed(data):
    """
    Handle charge failure webhook
    """
    tx_ref = data.get('tx_ref')
    
    try:
        payment = Payment.objects.get(flutterwave_ref=tx_ref)
        
        if payment.status == 'pending':
            payment.status = 'failed'
            payment.save()
            
            # Update enrollment status if exists
            try:
                enrollment = Enrollment.objects.get(payment=payment)
                enrollment.status = 'dropped'
                enrollment.save()
            except Enrollment.DoesNotExist:
                pass  # Enrollment might not exist yet
            
            return JsonResponse({
                'status': 'success', 
                'message': 'Payment marked as failed'
            })
        else:
            return JsonResponse({
                'status': 'success', 
                'message': 'Payment already processed'
            })
            
    except Payment.DoesNotExist:
        return JsonResponse({'error': 'Payment not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'Error processing failed charge: {str(e)}'}, status=500)


def _handle_certificate_charge_completed(data):
    """
    Handle successful certificate payment webhook
    """
    transaction_id = data.get('id')
    tx_ref = data.get('tx_ref')
    status = data.get('status')

    try:

        payment = CertificatePayment.objects.select_related(
            'course', 'student'
        ).get(reference=tx_ref)

        # Idempotency check
        if payment.status == 'paid':
            return JsonResponse({'status': 'success', 'message': 'Already processed'})

        if status == 'successful':
            # Verify transaction with Flutterwave
            success, verification_data = verify_flutterwave_payment(transaction_id)

            if not success:
                payment.status = 'failed'
                payment.save(update_fields=['status'])

                return JsonResponse({
                    'status': 'success',
                    'message': 'Certificate payment verification failed'
                })

            # Mark payment completed
            payment.status = 'paid'
            payment.paid_at = timezone.now()
            payment.save()

            # Move certificate request forward
            from module.models import CertificateRequest
            cert_request = CertificateRequest.objects.get(
                student=payment.student,
                course=payment.course
            )
            cert_request.status = CertificateRequest.STATUS_APPROVED  # or 'awaiting_approval'
            cert_request.save()

            return JsonResponse({
                'status': 'success',
                'message': 'Certificate payment completed, awaiting admin approval'
            })

        elif status == 'failed':
            payment.status = 'failed'
            payment.save(update_fields=['status'])

            return JsonResponse({
                'status': 'success',
                'message': 'Certificate payment failed'
            })

    except CertificatePayment.DoesNotExist:
        return JsonResponse({'error': 'Certificate payment not found'}, status=404)

    except Exception as e:
        return JsonResponse({
            'error': f'Error processing certificate payment: {str(e)}'
        }, status=500)


def _handle_addon_charge_completed(data):
    print('started add on')
    tx_ref = data.get('tx_ref')
    # Format: ADDON-{addon_id}-{course_id}-{user_id}-{uuid}
    try:
        parts = tx_ref.split('-')
        addon_id = int(parts[1])
        course_id = int(parts[2])
        user_id = int(parts[3])

        user = User.objects.get(id=user_id)
        course = Course.objects.get(id=course_id)
        addon = AddOn.objects.get(id=addon_id)  # The addon they bought

        # --- ACTION 1: ONE-ON-ONE CLINIC ---
        if 'one-on-one' in addon.feature.name.lower():
            ResearchClinic.objects.create(
                student=user,
                course=course,
                status='active'
            )
            # Send email: "Your clinic is active, wait for tutor assignment."

        # --- ACTION 2: CAPSTONE FEEDBACK ---
        elif 'feedback' in addon.feature.name.lower():
            # Create the entitlement record
            CapstoneFeedbackRequest.objects.create(
                student=user,
                course=course,
                status='paid'  # Ready to be used once project is submitted
            )

            # If they ALREADY submitted a project, link it now
            existing_project = CapstoneProject.objects.filter(student=user, instructions__course=course).first()
            if existing_project:
                req = CapstoneFeedbackRequest.objects.get(student=user, course=course)
                req.project = existing_project
                req.status = 'requested'  # Auto-request if project exists
                req.save()

        # --- ACTION 3: PREMIUM UPGRADE ---
        elif 'premium' in addon.feature.name.lower():
            print('premium')
            # 1. Find the Premium Package for this specific course
            premium_package = Package.objects.filter(
                course=course,
                package_type='premium', # change this to premium 2 to differentiate between regular and add on payment
                is_active = True
            ).first()

            if premium_package:
                print(f"premium package found {premium_package.id}, name:{premium_package.id}")
                # FIX: Use 'package__course' and 'student' (or whatever your user field is named)
                enrollment = Enrollment.objects.filter(
                    student=user,
                    package__course=course
                ).first()

                if enrollment:
                    print(f"Enrollment ID is {enrollment.id}")
                    enrollment.package = premium_package
                    enrollment.save()
                    print(f"Upgrade Successful: {user.email} -> Premium")
            else:
                print(f"Error: No Premium package found for course {course.title}")

        return JsonResponse({'status': 'success', 'message': 'Add-on processed'})

    except Exception as e:
        print(f"Add-on Error: {str(e)}")
        return JsonResponse({'status': 'failed', 'message': str(e)}, status=500)


def _handle_certificate_charge_failed(data):
    """
    Handle failed certificate payment webhook
    """
    tx_ref = data.get('tx_ref')

    try:
        from module.models import CertificatePayment, CertificateRequest

        payment = CertificatePayment.objects.select_related(
            'certificate_request'
        ).get(flutterwave_ref=tx_ref)

        # Idempotency check
        if payment.status != 'pending':
            return JsonResponse({
                'status': 'success',
                'message': 'Certificate payment already processed'
            })

        # Mark payment as failed
        payment.status = 'failed'
        payment.save(update_fields=['status'])

        # Update certificate request
        cert_request = payment.certificate_request
        cert_request.status = CertificateRequest.STATUS_PAYMENT_FAILED
        cert_request.save(update_fields=['status'])

        return JsonResponse({
            'status': 'success',
            'message': 'Certificate payment failed and request updated'
        })

    except CertificatePayment.DoesNotExist:
        return JsonResponse(
            {'error': 'Certificate payment not found'},
            status=404
        )

    except Exception as e:
        return JsonResponse(
            {'error': f'Error handling certificate payment failure: {str(e)}'},
            status=500
        )