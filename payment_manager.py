import streamlit as st
import uuid
import requests
from auth_manager import supabase

SSLCOMMERZ_STORE_ID = st.secrets["sslcommerz"]["SSLCOMMERZ_STORE_ID"]
SSLCOMMERZ_STORE_PASS = st.secrets["sslcommerz"]["SSLCOMMERZ_STORE_PASS"]
SSLCOMMERZ_IS_SANDBOX = st.secrets["sslcommerz"]["SSLCOMMERZ_IS_SANDBOX"]

BASE_URL = "https://sandbox.sslcommerz.com" if SSLCOMMERZ_IS_SANDBOX else "https://securepay.sslcommerz.com"

def initiate_real_sslcommerz_payment(user_id, user_name, user_email, plan_name="Pro Scholar", amount=500.00):
    # 🔴 Generate a strict standard UUID for both Database and SSLCommerz
    transaction_uuid = str(uuid.uuid4())
    tran_id = transaction_uuid 
    
    # 1. Save Pending Transaction
    try:
        supabase.table("transactions").insert({
            "id": transaction_uuid, # Now passing a valid UUID format
            "user_id": user_id,
            "amount": amount,
            "gateway": "sslcommerz",
            "status": "pending"
        }).execute()
    except Exception as e:
        return False, f"Transaction init failed: {e}"

    # 2. Setup SSLCommerz Payload
    # 🔴 FastAPI ব্যাকএন্ডের লিংক (যদি লোকালহোস্টে রান তবে http://127.0.0.1:8000, লাইভ হলে Render লিংক)
    BACKEND_API_URL = "https://gstu-ai-backend.onrender.com" 
    
    post_body = {
        'store_id': SSLCOMMERZ_STORE_ID,
        'store_pass': SSLCOMMERZ_STORE_PASS,
        'total_amount': amount,
        'currency': "BDT",
        'tran_id': tran_id,
        # 🔴 Updated URLs
        'success_url': f"{BACKEND_API_URL}/api/payment/success", 
        'fail_url': f"{BACKEND_API_URL}/api/payment/fail",
        'cancel_url': f"{BACKEND_API_URL}/api/payment/cancel",
        'cus_name': user_name,
        'cus_email': user_email,
        'cus_phone': "01700000000",
        'cus_add1': "GSTU Campus",
        'cus_city': "Gopalganj",
        'cus_country': "Bangladesh",
        'shipping_method': "NO",
        'product_name': plan_name,
        'product_category': "Subscription",
        'product_profile': "non-physical-goods"
    }

    # 3. Call SSLCommerz API
    try:
        response = requests.post(f"{BASE_URL}/gwprocess/v4/api.php", data=post_body)
        res_data = response.json()
        
        if res_data.get('status') == 'SUCCESS':
            return True, res_data.get('GatewayPageURL')
        else:
            return False, res_data.get('failedreason', 'Gateway Error')
    except Exception as e:
        return False, str(e)

def check_subscription_status(user_id):
    """চেক করবে ইউজারের প্রো টায়ার অ্যাকটিভ কি না"""
    try:
        response = supabase.table("subscriptions").select("plan, status").eq("user_id", user_id).execute()
        if response.data and response.data[0]['status'] == 'active':
            return response.data[0]['plan']
    except:
        pass
    return "free"