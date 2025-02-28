from flask import current_app, render_template
from flask_mail import Message, Mail
from datetime import datetime

class EmailService:
    def __init__(self, app=None):
        self._mail = None
        if app:
            self.init_app(app)

    def init_app(self, app):
        self._mail = Mail(app)

    def send_order_confirmation(self, order_data):
        """
        Send order confirmation email
        
        Args:
            order_data (dict): Dictionary containing:
                - email: Customer's email address
                - items: List of ordered items
                - total: Total order amount
                - shipping_details: Shipping information
                - order_number: Order number
        """
        try:
            msg = Message(
                'Order Confirmation - Thank you for your purchase!',
                sender=current_app.config['MAIL_DEFAULT_SENDER'],
                recipients=[order_data['email']]
            )

            # Prepare template data
            template_data = {
                'items': order_data['items'],
                'total': order_data['total'],
                'shipping_details': order_data['shipping_details'],
                'order_number': order_data['order_number'],
                'order_date': datetime.now().strftime('%B %d, %Y')
            }

            # Render both HTML and plain-text versions
            msg.html = render_template('email/order_confirmation.html', **template_data)
            msg.body = render_template('email/order_confirmation.txt', **template_data)

            if self._mail is None:
                raise RuntimeError("EmailService not properly initialized")
                
            self._mail.send(msg)
            current_app.logger.info(f"Order confirmation email sent to {order_data['email']}")
            return True

        except Exception as e:
            current_app.logger.error(f"Failed to send order confirmation email: {str(e)}")
            return False 