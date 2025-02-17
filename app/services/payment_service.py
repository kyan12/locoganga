import stripe
from typing import Dict
from flask import current_app
from ..models import Order

class PaymentService:
    def __init__(self, stripe_secret_key: str):
        stripe.api_key = stripe_secret_key

    def create_payment_intent(self, order: Order) -> Dict:
        """Create a payment intent for an order"""
        try:
            # Create a payment intent
            intent = stripe.PaymentIntent.create(
                amount=int(order.total_amount * 100),  # Convert to cents
                currency='usd',
                metadata={
                    'order_number': order.order_number
                }
            )
            
            return {
                'client_secret': intent.client_secret,
                'payment_intent_id': intent.id
            }
        except stripe.error.StripeError as e:
            raise Exception(f"Failed to create payment intent: {str(e)}")

    def handle_webhook(self, payload: Dict, sig_header: str) -> bool:
        """Handle Stripe webhook events"""
        webhook_secret = current_app.config.get('STRIPE_WEBHOOK_SECRET')
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except ValueError as e:
            raise Exception('Invalid payload')
        except stripe.error.SignatureVerificationError as e:
            raise Exception('Invalid signature')

        # Handle the event
        if event.type == 'payment_intent.succeeded':
            payment_intent = event.data.object
            order_number = payment_intent.metadata.get('order_number')
            
            # Update order status or trigger order fulfillment
            # This should be handled by the order service
            return True
            
        return False

    @classmethod
    def from_app(cls, app):
        """Create PaymentService instance from Flask app config"""
        stripe_key = app.config.get('STRIPE_SECRET_KEY')
        if not stripe_key:
            raise ValueError("Stripe secret key not configured")
        return cls(stripe_key) 