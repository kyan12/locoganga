from . import db

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    session_id = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(200))
    price = db.Column(db.Float)
    thumbnail = db.Column(db.String(500))
    spu = db.Column(db.String(50))