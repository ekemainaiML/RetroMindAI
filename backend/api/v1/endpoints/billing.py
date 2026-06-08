from datetime import datetime, timezone

import sqlalchemy
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.auth import get_current_workshop_obj
from core.config import settings
from core.database import get_db
from core.models import PricingPlan, UsageMetering, Workshop

router = APIRouter()

stripe.api_key = settings.stripe_secret_key
STRIPE_ENABLED = bool(settings.stripe_secret_key)


class PlanResponse(BaseModel):
    id: str
    tier: str
    name: str
    price_monthly: int
    price_yearly: int
    max_users: int | None
    max_assessments: int | None
    max_storage_mb: int | None
    features: list


class SubscriptionResponse(BaseModel):
    plan: PlanResponse | None
    status: str
    billing_period_start: str | None
    billing_period_end: str | None
    cancel_at_period_end: bool


class CreateCheckoutRequest(BaseModel):
    price_id: str
    success_url: str
    cancel_url: str


class CreateCheckoutResponse(BaseModel):
    url: str
    session_id: str


def _plan_to_response(plan: PricingPlan) -> PlanResponse:
    return PlanResponse(
        id=str(plan.id),
        tier=plan.tier,
        name=plan.name,
        price_monthly=plan.price_monthly,
        price_yearly=plan.price_yearly,
        max_users=plan.max_users,
        max_assessments=plan.max_assessments,
        max_storage_mb=plan.max_storage_mb,
        features=plan.features or [],
    )


@router.get("/billing/plans")
def list_plans(db: Session = Depends(get_db)):
    plans = db.query(PricingPlan).filter(PricingPlan.is_active.is_(True)).order_by(PricingPlan.price_monthly).all()
    return {"plans": [_plan_to_response(p) for p in plans]}


@router.get("/billing/subscription", response_model=SubscriptionResponse)
def get_subscription(
    workshop: Workshop = Depends(get_current_workshop_obj),
    db: Session = Depends(get_db),
):
    plan = db.query(PricingPlan).filter(PricingPlan.tier == workshop.tier).first()

    cancel_at_period_end = False
    if workshop.stripe_subscription_id and STRIPE_ENABLED:
        try:
            sub = stripe.Subscription.retrieve(workshop.stripe_subscription_id)
            cancel_at_period_end = sub.cancel_at_period_end
        except Exception:
            pass

    return SubscriptionResponse(
        plan=_plan_to_response(plan) if plan else None,
        status=workshop.subscription_status or "active",
        billing_period_start=workshop.billing_period_start.isoformat() if workshop.billing_period_start else None,
        billing_period_end=workshop.billing_period_end.isoformat() if workshop.billing_period_end else None,
        cancel_at_period_end=cancel_at_period_end,
    )


@router.post("/billing/create-checkout", response_model=CreateCheckoutResponse)
def create_checkout(
    body: CreateCheckoutRequest,
    workshop: Workshop = Depends(get_current_workshop_obj),
    db: Session = Depends(get_db),
):
    if not STRIPE_ENABLED:
        raise HTTPException(status_code=501, detail="Billing not configured")

    try:
        if not workshop.stripe_customer_id:
            customer = stripe.Customer.create(
                email=workshop.email or "",
                metadata={"workshop_id": str(workshop.id)},
            )
            workshop.stripe_customer_id = customer.id
            db.commit()

        session = stripe.checkout.Session.create(
            customer=workshop.stripe_customer_id,
            mode="subscription",
            line_items=[{"price": body.price_id, "quantity": 1}],
            success_url=body.success_url,
            cancel_url=body.cancel_url,
            metadata={"workshop_id": str(workshop.id)},
        )

        return CreateCheckoutResponse(url=session.url, session_id=session.id)
    except stripe.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


class CreatePortalRequest(BaseModel):
    return_url: str


@router.post("/billing/portal")
def create_portal_session(
    body: CreatePortalRequest,
    workshop: Workshop = Depends(get_current_workshop_obj),
):
    if not STRIPE_ENABLED or not workshop.stripe_customer_id:
        raise HTTPException(status_code=501, detail="Billing not configured")

    try:
        session = stripe.billing_portal.Session.create(
            customer=workshop.stripe_customer_id,
            return_url=body.return_url,
        )
        return {"url": session.url}
    except stripe.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/billing/stripe-webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    if not STRIPE_ENABLED:
        raise HTTPException(status_code=501, detail="Billing not configured")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")

    event_type = event.get("type")
    data = event.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        workshop_id = data.get("metadata", {}).get("workshop_id")
        if workshop_id:
            workshop = db.query(Workshop).filter(Workshop.id == workshop_id).first()
            if workshop:
                workshop.stripe_subscription_id = data.get("subscription")
                workshop.subscription_status = "active"
                db.commit()

    elif event_type == "invoice.paid":
        subscription_id = data.get("subscription")
        if subscription_id:
            workshop = db.query(Workshop).filter(
                Workshop.stripe_subscription_id == subscription_id
            ).first()
            if workshop:
                workshop.subscription_status = "active"
                period_start = data.get("period_start")
                period_end = data.get("period_end")
                if period_start:
                    workshop.billing_period_start = datetime.fromtimestamp(period_start, tz=timezone.utc)
                if period_end:
                    workshop.billing_period_end = datetime.fromtimestamp(period_end, tz=timezone.utc)
                db.commit()

    elif event_type == "invoice.payment_failed":
        subscription_id = data.get("subscription")
        if subscription_id:
            workshop = db.query(Workshop).filter(
                Workshop.stripe_subscription_id == subscription_id
            ).first()
            if workshop:
                workshop.subscription_status = "past_due"
                db.commit()

    elif event_type == "customer.subscription.updated":
        subscription_id = data.get("id")
        status = data.get("status")
        if subscription_id and status:
            workshop = db.query(Workshop).filter(
                Workshop.stripe_subscription_id == subscription_id
            ).first()
            if workshop:
                workshop.subscription_status = status
                if status == "canceled" or status == "incomplete_expired":
                    workshop.tier = "free"
                db.commit()

    elif event_type == "customer.subscription.deleted":
        subscription_id = data.get("id")
        if subscription_id:
            workshop = db.query(Workshop).filter(
                Workshop.stripe_subscription_id == subscription_id
            ).first()
            if workshop:
                workshop.subscription_status = "canceled"
                workshop.tier = "free"
                workshop.stripe_subscription_id = None
                db.commit()

    return {"received": True}


class UsageResponse(BaseModel):
    metric: str
    total: int
    limit: int | None


@router.get("/billing/usage")
def get_usage(
    workshop: Workshop = Depends(get_current_workshop_obj),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    plan = db.query(PricingPlan).filter(PricingPlan.tier == workshop.tier).first()

    usage_rows = (
        db.query(
            UsageMetering.metric,
            sqlalchemy.func.sum(UsageMetering.amount).label("total"),
        )
        .filter(
            UsageMetering.workshop_id == workshop.id,
            UsageMetering.recorded_at >= month_start,
        )
        .group_by(UsageMetering.metric)
        .all()
    )

    metric_limits = {
        "assessments_completed": plan.max_assessments if plan else None,
        "images_uploaded": None,
        "storage_bytes": plan.max_storage_mb * 1024 * 1024 if plan and plan.max_storage_mb else None,
        "api_calls": None,
    }

    usage_map = {row.metric: row.total for row in usage_rows}

    results = []
    for metric, limit in metric_limits.items():
        results.append(UsageResponse(
            metric=metric,
            total=int(usage_map.get(metric, 0)),
            limit=limit,
        ))

    return {"usage": results}
