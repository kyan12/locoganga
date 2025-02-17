from typing import Dict, List, Optional
from ..models import CartItem, ProductSKU, db

class CartService:
    def add_item(self, session_id: str, sku: str, quantity: int = 1) -> CartItem:
        """Add an item to the cart"""
        # Get product SKU
        product_sku = ProductSKU.query.filter_by(sku=sku).first()
        if not product_sku:
            raise ValueError(f"Product SKU not found: {sku}")

        if product_sku.supply_inventory < quantity:
            raise ValueError("Insufficient inventory")

        # Check if item already exists in cart
        cart_item = CartItem.query.filter_by(
            session_id=session_id,
            sku=sku
        ).first()

        if cart_item:
            # Update quantity if item exists
            cart_item.quantity += quantity
        else:
            # Create new cart item
            cart_item = CartItem(
                session_id=session_id,
                sku=sku,
                quantity=quantity,
                title=product_sku.product.title,
                price=product_sku.settle_price,
                thumbnail=product_sku.product.thumbnail,
                spu=product_sku.product.spu
            )

        db.session.add(cart_item)
        db.session.commit()
        return cart_item

    def update_quantity(self, session_id: str, sku: str, quantity: int) -> Optional[CartItem]:
        """Update item quantity in cart"""
        cart_item = CartItem.query.filter_by(
            session_id=session_id,
            sku=sku
        ).first()

        if not cart_item:
            return None

        # Check inventory
        product_sku = ProductSKU.query.filter_by(sku=sku).first()
        if not product_sku or product_sku.supply_inventory < quantity:
            raise ValueError("Insufficient inventory")

        if quantity <= 0:
            db.session.delete(cart_item)
        else:
            cart_item.quantity = quantity

        db.session.commit()
        return cart_item

    def remove_item(self, session_id: str, sku: str) -> bool:
        """Remove item from cart"""
        cart_item = CartItem.query.filter_by(
            session_id=session_id,
            sku=sku
        ).first()

        if cart_item:
            db.session.delete(cart_item)
            db.session.commit()
            return True
        return False

    def get_cart(self, session_id: str) -> List[CartItem]:
        """Get all items in cart"""
        return CartItem.query.filter_by(session_id=session_id).all()

    def get_cart_total(self, session_id: str) -> float:
        """Calculate cart total"""
        cart_items = self.get_cart(session_id)
        return sum(item.price * item.quantity for item in cart_items)

    def clear_cart(self, session_id: str) -> None:
        """Remove all items from cart"""
        CartItem.query.filter_by(session_id=session_id).delete()
        db.session.commit()

    def validate_cart(self, session_id: str) -> List[Dict]:
        """Validate cart items against current inventory"""
        cart_items = self.get_cart(session_id)
        issues = []

        for item in cart_items:
            sku = ProductSKU.query.filter_by(sku=item.sku).first()
            if not sku:
                issues.append({
                    'sku': item.sku,
                    'issue': 'Product no longer available'
                })
            elif sku.supply_inventory < item.quantity:
                issues.append({
                    'sku': item.sku,
                    'issue': 'Insufficient inventory',
                    'available': sku.supply_inventory
                })

        return issues 