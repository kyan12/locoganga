from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db, login

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    name = db.Column(db.String(100))
    address = db.Column(db.String(200))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    country = db.Column(db.String(100))
    zipcode = db.Column(db.String(20))
    phone = db.Column(db.String(20))
    orders = db.relationship('Order', backref='user', lazy=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_shipping_info(self):
        return {
            'name': self.name,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'country': self.country,
            'zipcode': self.zipcode,
            'phone': self.phone,
            'email': self.email
        }

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    spu = db.Column(db.String(50), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer)
    sale_type_id = db.Column(db.String(20))
    warehouse_code = db.Column(db.String(20))
    thumbnail = db.Column(db.String(500))
    total_inventory = db.Column(db.Integer)
    skus = db.relationship('ProductSKU', backref='product', lazy=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ProductSKU(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    random_sku = db.Column(db.String(50), unique=True, nullable=False)
    supply_inventory = db.Column(db.Integer)
    supply_price = db.Column(db.Float)
    settle_price = db.Column(db.Float)
    min_retail_price = db.Column(db.Float)
    retail_price_code = db.Column(db.String(10))
    weight = db.Column(db.Float)
    length = db.Column(db.Float)
    width = db.Column(db.Float)
    height = db.Column(db.Float)
    specification = db.Column(db.String(200))

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False)
    sku = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    title = db.Column(db.String(200))
    price = db.Column(db.Float)
    thumbnail = db.Column(db.String(500))
    spu = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    order_number = db.Column(db.String(50), unique=True, nullable=False)
    winit_order_number = db.Column(db.String(50), unique=True)
    status = db.Column(db.String(20), default='pending')
    total_amount = db.Column(db.Float)
    shipping_address = db.Column(db.String(200))
    shipping_city = db.Column(db.String(100))
    shipping_state = db.Column(db.String(100))
    shipping_country = db.Column(db.String(100))
    shipping_zipcode = db.Column(db.String(20))
    shipping_phone = db.Column(db.String(20))
    shipping_email = db.Column(db.String(120))
    shipping_name = db.Column(db.String(100))
    delivery_method = db.Column(db.String(50))
    tracking_number = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    items = db.relationship('OrderItem', backref='order', lazy=True)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    sku = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    title = db.Column(db.String(200))
    spu = db.Column(db.String(50))