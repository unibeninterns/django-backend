import requests
import uuid
from django.conf import settings


def initiate_flutterwave_transfer(payout_obj):
    """
    Takes a Payout model instance and sends funds via Flutterwave.
    """
    url = "https://api.flutterwave.com/v3/transfers"

    headers = {
        "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    domain = "https://uneasily-avulsed-tawnya.ngrok-free.dev"  # Replace with your REAL live domain
    webhook_path = "/api/payments/webhooks/flutterwave/"

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
    # addon is the specific AddOn instance they clicked
    tx_ref = f"ADDON-{addon.id}-{course.id}-{user.id}-{uuid.uuid4().hex[:8]}"

    payload = {
        "tx_ref": tx_ref,
        "amount": str(addon.price),
        "currency": "NGN",
        "redirect_url": "https://your-frontend.com/payment-success",
        "customer": {
            "email": user.email,
            "name": user.get_full_name()
        },
        "meta": {
            "addon_id": addon.id,
            "course_id": course.id,
            "feature_name": addon.feature.name  # Helps debug
        }
    }