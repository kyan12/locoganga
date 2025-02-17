from typing import Dict, List, Optional
from datetime import datetime
import uuid
from ..models import Order, OrderItem, User, ProductSKU, db
from .winit_api import WinitAPI

class OrderService:
    def __init__(self, winit_api: WinitAPI):
        self.winit_api = winit_api

    def create_order(self, user: User, cart_items: List[Dict], shipping_info: Dict) -> Order:
        """Create a new order from cart items"""
        # Create order in local database
        order = Order(
            user=user,
            order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
            status='pending',
            shipping_name=shipping_info['name'],
            shipping_address=shipping_info['address'],
            shipping_city=shipping_info['city'],
            shipping_state=shipping_info['state'],
            shipping_country=shipping_info['country'],
            shipping_zipcode=shipping_info['zipcode'],
            shipping_phone=shipping_info['phone'],
            shipping_email=shipping_info['email'],
            delivery_method=shipping_info['delivery_method']
        )

        total_amount = 0
        order_items = []
        package_items = []

        # Process each cart item
        for cart_item in cart_items:
            sku = ProductSKU.query.filter_by(sku=cart_item['sku']).first()
            if not sku or sku.supply_inventory < cart_item['quantity']:
                raise ValueError(f"Insufficient inventory for SKU: {cart_item['sku']}")

            # Create order item
            order_item = OrderItem(
                order=order,
                sku=sku.sku,
                quantity=cart_item['quantity'],
                price=sku.settle_price,
                title=sku.product.title,
                spu=sku.product.spu
            )
            order_items.append(order_item)
            total_amount += order_item.price * order_item.quantity

            # Prepare package item for Winit API
            package_items.append({
                'productCode': sku.random_sku,
                'productNum': cart_item['quantity']
            })

        order.total_amount = total_amount
        order.items = order_items

        # Prepare data for Winit API
        winit_order_data = {
            'repeatable': 'N',
            'isAuto': 'Y',
            'sellerOrderNo': order.order_number,
            'recipientName': shipping_info['name'],
            'phoneNum': shipping_info['phone'],
            'zipCode': shipping_info['zipcode'],
            'emailAddress': shipping_info['email'],
            'state': shipping_info['country'],
            'region': shipping_info['state'],
            'city': shipping_info['city'],
            'address1': shipping_info['address'],
            'packageList': [{
                'warehouseCode': sku.product.warehouse_code,
                'deliveryWayCode': shipping_info['delivery_method'],
                'productList': package_items
            }]
        }

        try:
            # Create order in Winit
            winit_response = self.winit_api.create_order(winit_order_data)
            if winit_response and 'orderNums' in winit_response:
                order.winit_order_number = winit_response['orderNums'][0]['orderNo']
                order.status = 'processing'
            else:
                raise Exception("Failed to create order in Winit")

            # Save order to database
            db.session.add(order)
            db.session.commit()

            return order

        except Exception as e:
            db.session.rollback()
            raise Exception(f"Failed to create order: {str(e)}")

    def get_order(self, order_number: str) -> Optional[Order]:
        """Get order by order number"""
        return Order.query.filter_by(order_number=order_number).first()

    def get_user_orders(self, user: User, page: int = 1, per_page: int = 20) -> List[Order]:
        """Get paginated list of user's orders"""
        return Order.query.filter_by(user=user)\
            .order_by(Order.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)

    def sync_order_status(self, order: Order) -> bool:
        """Sync order status from Winit"""
        if not order.winit_order_number:
            return False

        try:
            winit_order = self.winit_api.get_order_detail(order.winit_order_number)
            if not winit_order:
                return False

            # Update tracking information
            order.tracking_number = winit_order.get('trackingNum', '')
            
            # Map Winit status to local status
            status_map = {
                'DR': 'pending',
                'PHI': 'processing',
                'SHP': 'shipped',
                'DLV': 'delivered',
                'VO': 'cancelled'
            }
            winit_status = winit_order.get('status')
            if winit_status in status_map:
                order.status = status_map[winit_status]

            db.session.commit()
            return True

        except Exception:
            return False

    def cancel_order(self, order: Order) -> bool:
        """Cancel an order"""
        if order.status not in ['pending', 'processing']:
            raise ValueError("Order cannot be cancelled in current status")

        try:
            if order.winit_order_number:
                # Cancel order in Winit
                self.winit_api.cancel_order([order.winit_order_number])

            order.status = 'cancelled'
            db.session.commit()
            return True

        except Exception as e:
            db.session.rollback()
            raise Exception(f"Failed to cancel order: {str(e)}")

    def get_delivery_methods(self, warehouse_code: str) -> List[Dict]:
        """Get available delivery methods for a warehouse"""
        return self.winit_api.get_delivery_methods(warehouse_code) 