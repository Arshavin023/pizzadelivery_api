import hmac
import hashlib
import json
from fastapi import APIRouter, Request, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from Models.models import Order, Payment, User
from database_connection.database import get_async_db

payment_router = APIRouter()

# In production, move this to your .env file
PAYSTACK_SECRET_KEY = "sk_live_xxxxxxx" 

@payment_router.post("/webhook/paystack")
async def paystack_webhook(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    x_paystack_signature: str = Header(None)
    ):
    """
    Production-level Webhook: Validates signature and updates Order/Payment status.
    """
    # 1. Security: Verify the signature to ensure the request actually came from Paystack
    payload = await request.body()
    
    if not x_paystack_signature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No signature")

    hash_check = hmac.new(
        PAYSTACK_SECRET_KEY.encode('utf-8'),
        payload,
        hashlib.sha512
    ).hexdigest()

    if hash_check != x_paystack_signature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    # 2. Parse the data
    event_data = json.loads(payload)
    
    # We only care about successful charges
    if event_data['event'] == 'charge.success':
        # Use the 'reference' which we should have mapped to our Transaction ID or Order ID
        transaction_ref = event_data['data']['reference']
        
        # 3. Update Database
        # Find the Payment record associated with this reference
        result = await db.execute(
            select(Payment).where(Payment.transaction_id == transaction_ref)
        )
        payment_record = result.scalar_one_or_none()

        if payment_record:
            # Update Payment to COMPLETED
            payment_record.status = 'COMPLETED'
            payment_record.gateway_response = event_data['data'] # Store full JSON for audit

            # Update associated Order to CONFIRMED
            result_order = await db.execute(
                select(Order).where(Order.id == payment_record.order_id)
            )
            order_record = result_order.scalar_one_or_none()
            if order_record:
                order_record.status = 'CONFIRMED' # Kitchen can now start cooking!

            await db.commit()

    return {"status": "success"}