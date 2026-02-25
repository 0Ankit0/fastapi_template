import logging
import stripe
from fastapi import APIRouter, Request, Header, HTTPException, Depends
from app.core.config import settings
from app.services.subscriptions import SubscriptionService
from app.api import deps
from app.db.session import AsyncSession
# Import models via alias if needed, or just rely on service layer
# from app.models.finances import ...

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/stripe/")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    db: AsyncSession = Depends(deps.get_db) # Webhooks usually need DB access
):
    """
    Handle Stripe Webhooks.
    """
    payload = await request.body()
    sig_header = stripe_signature
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.DJSTRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle the event
    event_type = event["type"]
    data_object = event["data"]["object"]
    
    if event_type == "invoice.payment_succeeded":
        logger.info(f"Payment succeeded: {data_object.get('id')}")
        # In a full sync, we would update the Subscription status to active if it was past_due
        pass
        
    elif event_type == "customer.subscription.deleted":
        logger.info(f"Subscription deleted: {data_object.get('id')}")
        # Mark local subscription as inactive/canceled
        # sub = await db.get(Subscription, data_object.get("id"))
        # if sub: ...
        pass
        
    elif event_type == "invoice.payment_failed":
        logger.info(f"Invoice payment failed: {data_object.get('id')}")
        # Send email
        # customer_id = data_object.get("customer")
        # customer = await db.get(Customer, customer_id)
        # if customer:
        #      await EmailService.send_payment_failed_email(customer.email)
        pass
        
    elif event_type == "customer.subscription.trial_will_end":
        logger.info(f"Trial ending for subscription: {data_object.get('id')}")
        # Send email
        pass

    return {"status": "success"}
