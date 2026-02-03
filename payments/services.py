import requests
import uuid
from django.conf import settings

domain = "https://uneasily-avulsed-tawnya.ngrok-free.dev"  # Replace with your REAL live domain
webhook_path = "/api/payments/webhooks/flutterwave/"

def initiate_flutterwave_transfer(payout_obj):
    """
    Takes a Payout model instance and sends funds via Flutterwave.
    """
    url = "https://api.flutterwave.com/v3/transfers"

    headers = {
        "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    # Generate a unique reference if one doesn't exist
    if not payout_obj.reference:
        payout_obj.reference = f"PAY-{uuid.uuid4().hex[:12]}"
        payout_obj.save()

    payload = {
        "account_bank": payout_obj.bank_code,  # e.g., "044"
        "account_number": payout_obj.account_number,  # e.g., "069..."
        "amount": int(payout_obj.amount),  # Ensure it's a number
        "currency": "NGN",
        "narration": f"Payout for {payout_obj.course.title if payout_obj.course else 'Course Earnings'}",
        "reference": payout_obj.reference,
        "callback_url": f"{domain}{webhook_path}"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()

        if response.status_code == 200 and data.get('status') == 'success':
            # The transfer is QUEUED (not necessarily completed yet)
            payout_obj.status = 'pending'
            payout_obj.flutterwave_id = data['data']['id']
            payout_obj.notes += f"\nTransfer Initiated: {data['message']}"
            payout_obj.save()
            return True, data
        else:
            # The API call failed (e.g., insufficient balance)
            payout_obj.status = 'failed'
            payout_obj.notes += f"\nFailed: {data.get('message', 'Unknown Error')}"
            payout_obj.save()
            return False, data

    except Exception as e:
        payout_obj.status = 'failed'
        payout_obj.notes += f"\nSystem Error: {str(e)}"
        payout_obj.save()
        return False, str(e)


def initiate_addon_payment(user, addon, course):
    """
    Generates a Flutterwave payment link for an Add-on purchase.
    Returns: (bool, dict/str) -> (Success?, Data or Error Message)
    """
    url = "https://api.flutterwave.com/v3/payments"

    headers = {
        "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    # Generate unique reference
    tx_ref = f"ADDON-{addon.id}-{course.id}-{user.id}-{uuid.uuid4().hex[:8]}"

    # FIX 1: Construct name manually to avoid 'CustomUser has no attribute get_full_name'
    customer_name = f"{user.first_name} {user.last_name}".strip()

    payload = {
        "tx_ref": tx_ref,
        "amount": str(addon.price),
        "currency": "NGN",
        "redirect_url": "https://uneasily-avulsed-tawnya.ngrok-free.dev/api/payments/payment-success/",  # Update this to your real frontend URL
        "customer": {
            "email": user.email,
            "name": customer_name
        },
        "customizations": {
            "title": f"Purchase: {addon.feature.name}",
            "description": f"Add-on for {course.title}",
            # "logo": "https://your-logo-url.com/logo.png"  # Optional
        },
        "meta": {
            "addon_id": addon.id,
            "course_id": course.id,
            "feature_name": addon.feature.name,
            "type": "addon_purchase"  # Helps identify this in Webhooks
        }
    }

    try:
        # FIX 2: Actually send the request (this was missing)
        response = requests.post(url, json=payload, headers=headers)
        response_json = response.json()

        if response.status_code == 200 and response_json.get('status') == 'success':
            # 1. Get the inner dictionary (the actual payload)
            inner_data = response_json['data']

            # 2. Add the tx_ref INSIDE this inner dictionary
            inner_data['tx_ref'] = tx_ref

            # 3. Now return it
            return True, inner_data  # Contains the 'link' needed for redirection
        else:
            return False, response_json.get('message', 'Payment initialization failed')

    except Exception as e:
        # FIX 3: Return a Tuple (False, error_message)
        print(f"Addon Payment Error: {e}")
        return False, str(e)