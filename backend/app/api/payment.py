from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user

router = APIRouter(tags=["Enterprise Billing"])

class BkashRequest(BaseModel):
    trx_id: str
    amount: float = 99.0

# 🔴 1. Manual bKash Submission
@router.post("/bkash/submit")
def submit_manual_bkash(
    request: BkashRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """স্টুডেন্ট bKash TrxID সাবমিট করবে, যা ডাটাবেসে Pending হিসেবে সেভ হবে"""
    if not current_user.get("sub"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # প্রোডাকশনে এখানে SQLAlchemy মডেল দিয়ে Database Insert হবে
    # Example: new_txn = Transaction(user_id=current_user["sub"], trx_id=request.trx_id, status="pending")
    
    return {"message": "Transaction submitted successfully. Waiting for Admin approval."}

# 🔴 2. SSLCommerz Headless Initiation
@router.post("/sslcommerz/initiate")
def initiate_ssl_payment(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """ফ্রন্টএন্ড বা মোবাইল অ্যাপ থেকে হিট করলে SSLCommerz-এর পেমেন্ট URL জেনারেট করে পাঠাবে।"""
    if not current_user.get("sub"):
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    # SSLCommerz API Integration Logic here
    # dummy_url = "https://sandbox.sslcommerz.com/gwprocess/v4/api.php?..."
    
    return {"payment_url": "https://securepay.sslcommerz.com/..."}

# 🔴 3. Payment Webhooks (Cross-Platform Redirects)
@router.post("/callback/success")
async def payment_success_webhook(request: Request):
    form_data = await request.form()
    client_platform = form_data.get("value_a", "web")
    tran_id = form_data.get("tran_id")
    
    # ডাটাবেসে ইউজারকে "Pro Scholar" টায়ারে আপগ্রেড করার লজিক
    
    # Cross-Platform Routing
    if client_platform == "mobile":
        return RedirectResponse(url=f"gstuapp://payment/success?tran_id={tran_id}", status_code=303)
    return RedirectResponse(url=f"http://localhost:3000/dashboard?payment=success", status_code=303)