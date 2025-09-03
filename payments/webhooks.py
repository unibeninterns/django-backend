import json
import hmac
import hashlib
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from .models import Payment, Enrollment
from .utils import verify_flutterwave_payment, verify_flutterwave_webhook_signature

@csrf_exempt
@require_POST
def flutterwave_webhook(request):
    """
    Handle Flutterwave webhook for package payment notifications
    """
    # Verify webhook signature for security
    signature_valid, message = verify_flutterwave_webhook_signature(request)
    if not signature_valid:
        return HttpResponse(status=401)
    
    try:
        payload = json.loads(request.body)
        event = payload.get('event')
        data = payload.get('data', {})
        
        if event == 'charge.completed':
            return _handle_charge_completed(data)
        elif event == 'charge.failed':
            return _handle_charge_failed(data)
        else:
            # Acknowledge other events but take no action
            return JsonResponse({'status': 'success', 'message': 'Event acknowledged'})
            
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