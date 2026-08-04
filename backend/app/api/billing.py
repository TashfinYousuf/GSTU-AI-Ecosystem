from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.security import get_current_user

router = APIRouter(tags=["Enterprise Billing"])

class BkashRequest(BaseModel):
    trx_id: str
    amount: float = 99.0

# Mock DB for demonstration (Pro User Logic)
MOCK_USER_DB = {
    "subscription_tier": "free", # 'free' or 'pro_scholar'
    "lifetime_messages": 142,
    "lifetime_pdfs": 12,
    "reward_credits": 50
}

@router.get("/status")
def get_billing_status(current_user: dict = Depends(get_current_user)):
    """ইউজারের বর্তমান সাবস্ক্রিপশন টায়ার এবং লিমিট চেক করা"""
    if not current_user.get("sub"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    return {"status": "success", "data": MOCK_USER_DB}

@router.post("/bkash/submit")
def submit_manual_bkash(
    request: BkashRequest,
    current_user: dict = Depends(get_current_user)
):
    """bKash এর ম্যানুয়াল TrxID সাবমিট করা"""
    if not current_user.get("sub"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if len(request.trx_id) < 8:
        raise HTTPException(status_code=400, detail="Invalid TrxID format.")
        
    # প্রোডাকশনে এটি Supabase-এর "manual_payments" টেবিলে সেভ হবে
    return {"message": "Request Sent! Admin will verify and upgrade your account shortly.", "status": "pending"}

@router.post("/sslcommerz/initiate")
def initiate_ssl_payment(current_user: dict = Depends(get_current_user)):
    """SSLCommerz পেমেন্ট গেটওয়ে লিংক জেনারেট করা"""
    if not current_user.get("sub"):
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    # প্রোডাকশনে SSLCommerz API কল করে URL জেনারেট হবে
    dummy_payment_url = "https://sandbox.sslcommerz.com/gwprocess/v4/api.php?..."
    
    return {"payment_url": dummy_payment_url}