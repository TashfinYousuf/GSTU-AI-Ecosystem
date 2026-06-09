import os
import uuid
import requests
import streamlit as st

def _get_credentials():
    # 🔴 SDK ছাড়াই সরাসরি .env বা secrets থেকে ফ্রেশ ডাটা রিড করা
    store_id = os.environ.get("SSLCOMMERZ_STORE_ID") or st.secrets.get("SSLCOMMERZ_STORE_ID", "testbox")
    store_pass = os.environ.get("SSLCOMMERZ_STORE_PASS") or st.secrets.get("SSLCOMMERZ_STORE_PASS", "testpass")
    
    # Check if sandbox mode is active (default is True for safety)
    is_sandbox = os.environ.get("SSLCOMMERZ_IS_SANDBOX", "true").lower() in ['true', '1', 't', 'yes']
    return store_id, store_pass, is_sandbox

def initiate_real_sslcommerz_payment(user_id, user_name, user_email):
    try:
        store_id, store_pass, is_sandbox = _get_credentials()

        # 🔴 Direct API Endpoints
        base_url = "https://sandbox.sslcommerz.com" if is_sandbox else "https://securepay.sslcommerz.com"
        api_url = f"{base_url}/gwprocess/v4/api.php"

        # App URL for success/fail redirects
        app_url = os.environ.get("APP_URL") or st.secrets.get("APP_URL", "http://localhost:8501")
        
        # Unique Transaction ID
        tran_id = f"GSTU_{user_id}_{uuid.uuid4().hex[:8]}"

        # 🔴 The exact JSON payload SSLCommerz API demands!
        payload = {
            "store_id": store_id,
            "store_passwd": store_pass, # Exact API field name
            "total_amount": 500,
            "currency": "BDT",
            "tran_id": tran_id,
            "success_url": f"{app_url}?payment=success",
            "fail_url": f"{app_url}?payment=fail",
            "cancel_url": f"{app_url}?payment=cancel",
            "cus_name": user_name,
            "cus_email": user_email,
            "cus_phone": "01700000000",
            "cus_add1": "GSTU Campus",
            "cus_city": "Gopalganj",
            "cus_country": "Bangladesh",
            "shipping_method": "NO",
            "product_name": "Pro Scholar Subscription",
            "product_category": "EdTech",
            "product_profile": "non-physical-goods"
        }

        # 🔴 Send Raw HTTP Request (Bypassing the buggy SDK)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        response = requests.post(api_url, data=payload, headers=headers, timeout=15)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "SUCCESS":
                return True, result.get("GatewayPageURL")
            else:
                return False, result.get("failedreason", "Unknown Gateway Error")
        else:
            return False, f"HTTP {response.status_code}: Could not reach SSLCommerz server."

    except Exception as e:
        return False, f"Exception: {str(e)}"

def check_subscription_status(user_id):
    from auth_logic import supabase
    try:
        res = supabase.table("user_profiles").select("subscription_tier").eq("id", user_id).execute()
        if res.data:
            return res.data[0].get("subscription_tier", "free")
    except:
        pass
    return "free"