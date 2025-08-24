import requests
import json
import time
import hmac
import hashlib
from django.conf import settings

def create_flutterwave_payment(user, package, amount, redirect_url):
    """
    Create a Flutterwave payment link for package enrollment
    """
    # Generate unique transaction reference for package
    tx_ref = f"PKG_{user.id}_{package.id}_{int(time.time())}"
    
    url = "https://api.flutterwave.com/v3/payments"
    headers = {
        "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "tx_ref": tx_ref,
        "amount": str(amount),
        "currency": "NGN",
        "redirect_url": redirect_url,
        "customer": {
            "email": user.email,
            "name": f"{user.first_name} {user.last_name}",
        },
        "customizations": {
            "title": "Learning Management System",
            "description": f"Payment for {package.name} package",
        }
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response_data = response.json()
        
        if response.status_code == 200 and response_data['status'] == 'success':
            return response_data['data']['link'], tx_ref
        else:
            error_msg = response_data.get('message', 'Unknown error')
            print(f"Flutterwave API error: {error_msg}")
            return None, None
            
    except requests.exceptions.RequestException as e:
        print(f"Network error while connecting to Flutterwave: {e}")
        return None, None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None, None


def verify_flutterwave_payment(transaction_id):
    """
    Verify a Flutterwave payment transaction
    """
    url = f"https://api.flutterwave.com/v3/transactions/{transaction_id}/verify"
    
    headers = {
        "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response_data = response.json()
        
        if response.status_code == 200 and response_data['status'] == 'success':
            # Check if transaction was successful
            transaction_data = response_data['data']
            if transaction_data['status'] == 'successful':
                return True, response_data
            else:
                return False, response_data
        else:
            return False, response_data
            
    except requests.exceptions.RequestException as e:
        print(f"Network error while verifying Flutterwave payment: {e}")
        return False, None
    except Exception as e:
        print(f"Unexpected error during verification: {e}")
        return False, None


def verify_flutterwave_webhook_signature(request):
    """
    Verify Flutterwave webhook signature for security
    """
    signature = request.headers.get('x-flutterwave-signature')
    if not signature:
        return False, "Missing signature header"
    
    # Verify HMAC signature
    secret = settings.FLUTTERWAVE_SECRET_KEY.encode()
    expected_signature = hmac.new(
        secret, request.body, hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(signature, expected_signature):
        return False, "Invalid signature"
    
    return True, "Signature verified"


def handle_flutterwave_webhook(payload):
    """
    Process Flutterwave webhook payload for package payments
    """
    event = payload.get('event')
    data = payload.get('data', {})
    
    if event == 'charge.completed':
        transaction_id = data.get('id')
        tx_ref = data.get('tx_ref')
        status = data.get('status')
        
        try:
            from .models import Payment
            payment = Payment.objects.get(flutterwave_ref=tx_ref)
            
            if status == 'successful':
                # Verify the transaction
                success, verification_data = verify_flutterwave_payment(transaction_id)
                
                if success:
                    payment.status = 'completed'
                    payment.transaction_id = transaction_id
                    payment.save()
                    
                    # Update enrollment status
                    from .models import Enrollment
                    enrollment = Enrollment.objects.get(payment=payment)
                    enrollment.status = 'active'
                    enrollment.save()
                    
                    return True, "Payment completed successfully"
            
            elif status == 'failed':
                payment.status = 'failed'
                payment.save()
                
                # Update enrollment status
                from .models import Enrollment
                enrollment = Enrollment.objects.get(payment=payment)
                enrollment.status = 'dropped'
                enrollment.save()
                
                return True, "Payment failed"
        
        except Payment.DoesNotExist:
            return False, "Payment not found"
        except Enrollment.DoesNotExist:
            return False, "Enrollment not found"
        except Exception as e:
            return False, f"Error processing webhook: {str(e)}"
    
    return True, "Webhook processed successfully"


def calculate_package_total(package, add_ons=None):
    """
    Calculate total amount for a package including add-ons
    """
    total = package.price
    
    if add_ons:
        for add_on in add_ons:
            total += add_on.price
    
    return total


def generate_transaction_id(user, package):
    """
    Generate a unique transaction ID for package payments
    """
    timestamp = int(time.time())
    return f"PKG_{user.id}_{package.id}_{timestamp}"